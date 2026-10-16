#!/usr/bin/env python3
"""Measure falling support with checkpointed, bounded experiments.

python task2_explosion.py --supports 400,200,100,50,25,12,6,3,1
python task2_explosion.py --items 20000 --baskets 60000 --avg 30 --supports 3

Use the original generator and PlainApriori without editing their files.
An interrupted result is never presented as a completion or physical OOM.
"""
import argparse
from collections import Counter
import ctypes
from datetime import datetime, timezone
import json
import os
import platform
import time
import tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def machine(background):
    info = {"platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(), "background": background}
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                info["processor"] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass

        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                        ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                        ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                        ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                        ("avail_extended", ctypes.c_ulonglong)]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            info["ram_bytes"] = status.total_phys
            info["available_ram_bytes_at_start"] = status.avail_phys
    elif hasattr(os, "sysconf"):
        try:
            info["ram_bytes"] = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except (OSError, ValueError):
            pass
    return info


def save(path, data):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=True, allow_nan=False)
        file.write("\n")
    os.replace(temporary, path)


class ExperimentStopped(Exception):
    pass


class WatchedBaskets:
    """Sample limits between baskets, not during the final result comprehension.

    This is a comfort guard, not a hard process memory or time limit. A completed
    output can exceed the sampled budget; report that explicitly after the run.
    """

    def __init__(self, baskets, start, max_bytes, max_seconds):
        self.baskets = baskets
        self.start = start
        self.max_bytes = max_bytes
        self.max_seconds = max_seconds
        self.pass_number = 0
        self.processed = 0

    def __iter__(self):
        self.pass_number += 1
        for index, basket in enumerate(self.baskets):
            self.processed = index
            if index % 64 == 0:
                _, peak = tracemalloc.get_traced_memory()
                if peak >= self.max_bytes:
                    raise ExperimentStopped("traced Python allocation budget reached")
                if time.perf_counter() - self.start >= self.max_seconds:
                    raise ExperimentStopped("wall-time budget reached")
            yield basket
        self.processed = len(self.baskets)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--supports", default="400,200,100,50,25")
    p.add_argument("--items", type=int, default=2000)
    p.add_argument("--baskets", type=int, default=20000)
    p.add_argument("--avg", type=int, default=20)
    p.add_argument("--max-mib", type=float, default=256)
    p.add_argument("--max-seconds", type=float, default=60)
    p.add_argument("--background", default="Other running applications not inspected")
    a = p.parse_args()
    try:
        supports = [int(x) for x in a.supports.split(",")]
    except ValueError:
        p.error("supports must be comma-separated positive integers")
    if not supports or min(supports) < 1:
        p.error("each support must be at least one")
    if a.items < 300 or a.baskets < 1 or a.avg < 2:
        p.error("the supplied generator needs items >= 300, baskets >= 1, avg >= 2")
    if not (0 < a.max_mib < float("inf") and 0 < a.max_seconds < float("inf")):
        p.error("measurement budgets must be finite and positive")
    import bench
    from task3_pcy import PlainApriori
    bench.ITEMS, bench.BASKETS, bench.AVG = a.items, a.baskets, a.avg
    baskets = bench.build()
    singleton_counts = Counter(item for basket in baskets for item in basket)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "explosion.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    else:
        data = {"runs": []}
    environment = machine(a.background)
    data["machine"] = environment
    data["measurement"] = (
        "PlainApriori with tracemalloc active; perf_counter wall time includes tracing "
        "and limit checks every 64 baskets (not during final output construction). "
        "These are sampled comfort budgets, not strict process limits. "
        "Peak Python allocations exclude prebuilt "
        "input baskets, interpreter and native allocations; this is not process RSS. "
        "Completed peak counters include the baseline's pair-count dictionary only, "
        "as defined by the unmodified benchmark. Interrupted frequent_pairs is null."
    )
    batch_id = datetime.now(timezone.utc).isoformat()
    for support in supports:
        algo = PlainApriori(support)
        survivors = sum(count >= support for count in singleton_counts.values())
        row = {"batch_id": batch_id, "support": support,
               "dataset": {"seed": bench.SEED, "items": a.items,
                           "baskets": a.baskets, "avg": a.avg},
               "machine": environment,
               "max_bytes": int(a.max_mib * 1024 ** 2), "max_seconds": a.max_seconds,
               "frequent_singletons": survivors,
               "possible_survivor_pairs": survivors * (survivors - 1) // 2}
        tracemalloc.start()
        start = time.perf_counter()
        watched = WatchedBaskets(baskets, start, row["max_bytes"], a.max_seconds)
        pairs = None
        try:
            pairs = algo.run(watched)
            row.update(status="completed", frequent_pairs=len(pairs))
        except ExperimentStopped as error:
            row.update(status="stopped", frequent_pairs=None, stop_reason=str(error),
                       stopped_in_pass=watched.pass_number,
                       baskets_processed_in_pass=watched.processed)
        except MemoryError:
            row.update(status="memory_error", frequent_pairs=None,
                       stop_reason="Python raised MemoryError")
        finally:
            row["seconds"] = time.perf_counter() - start
            _, row["peak_bytes"] = tracemalloc.get_traced_memory()
            row["peak_counters"] = algo.peak_counters
            tracemalloc.stop()
        row["budget_exceeded_at_completion"] = (
            row["status"] == "completed" and
            (row["peak_bytes"] >= row["max_bytes"] or
             row["seconds"] >= row["max_seconds"]))
        data["runs"].append(row)
        save(path, data)
        pair_label = f"{len(pairs):,}" if pairs is not None else "incomplete"
        print(f"  support {support:>5}   pairs {pair_label:>10}   "
              f"counters {algo.peak_counters:>10,}   "
              f"{row['seconds']:>7.2f}s   {row['peak_bytes'] / 1024 ** 2:>8.1f} MiB   "
              f"{row['status']}", flush=True)
        del pairs, algo
        if row["status"] != "completed":
            print(f"  stopped: {row['stop_reason']}; progress saved", flush=True)
            break
    print(f"\n  -> out/explosion.json  ({len(data['runs'])} run(s))")


if __name__ == "__main__":
    main()
