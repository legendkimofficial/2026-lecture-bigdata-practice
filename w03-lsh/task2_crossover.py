#!/usr/bin/env python3
"""Week 3 Task 2: measure actual input sizes, including sizes above 2,120."""
import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
import platform
import random
import time
import tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def machine(background):
    info = {
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "python": platform.python_version(),
        "logical_cpus": os.cpu_count(),
        "background": background,
        "memory_measurement": (
            "tracemalloc peak allocations during find(); input document sets "
            "are generated before tracing and are excluded; not total process RSS"
        ),
    }
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            ) as key:
                info["processor"] = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            info["cpu_model_note"] = "Exact CPU model unavailable in this execution sandbox"
        try:
            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong), ("load", ctypes.c_ulong),
                    ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                    ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                    ("avail_extended", ctypes.c_ulonglong),
                ]
            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                info["ram_bytes"] = status.total_phys
                info["available_ram_bytes_at_start"] = status.avail_phys
        except (AttributeError, OSError):
            pass
    elif hasattr(os, "sysconf"):
        try:
            info["ram_bytes"] = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except (OSError, ValueError):
            pass
    return info


def build_documents(n, seed=246):
    """Same shingle/clone model as bench, but exactly n documents at every size."""
    if n < 2:
        raise ValueError("n must be at least 2")
    import bench
    rng = random.Random(seed)
    clone_count = round(n * bench.PLANTED / (bench.N_DOCS + bench.PLANTED))
    base_count = n - clone_count
    docs = [set(rng.sample(range(bench.VOCAB), bench.SHINGLES))
            for _ in range(base_count)]
    for _ in range(clone_count):
        clone = set(docs[rng.randrange(base_count)])
        for _ in range(rng.randint(4, 14)):
            clone.discard(rng.choice(list(clone)))
            clone.add(rng.randrange(bench.VOCAB))
        docs.append(clone)
    rng.shuffle(docs)
    assert len(docs) == n
    return docs


def timed(fn, *args):
    """Wall time and peak traced allocations of one call, including tracing overhead."""
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        result = fn(*args)
        elapsed = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, elapsed, peak


def save(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sizes", default="250,500,1000,2000")
    p.add_argument("--threshold", type=float, default=0.6)
    p.add_argument("--output", default=os.path.join(OUT, "crossover.json"),
                   help="JSON file to append measurements to")
    p.add_argument("--background", default=(
        "Measured during a ChatGPT Codex task; other background applications "
        "are not visible in the sandbox and were not verified"
    ))
    p.add_argument("--stop-after", type=float, default=None,
                   help="stop after a completed size if either method takes this many seconds")
    a = p.parse_args()
    sizes = [int(x) for x in a.sizes.split(",")]
    if not sizes or any(n < 2 for n in sizes):
        p.error("each document count must be at least 2")
    if not 0 <= a.threshold <= 1:
        p.error("threshold must be between 0 and 1")
    if a.stop_after is not None and a.stop_after <= 0:
        p.error("--stop-after must be positive")
    os.makedirs(OUT, exist_ok=True)

    import bench
    from task3_scale import BruteForce, YourFinder
    path = os.path.abspath(a.output)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    else:
        data = {"runs": []}
    data["machine"] = machine(a.background)
    data["seed"] = bench.SEED
    data["finder"] = {"num_hashes": 120, "bands": 30, "rows_per_band": 4}
    data["generator"] = "exact n; 60 shingles from vocabulary 5000; approximately 120/2120 clones"
    save(path, data)

    for n in sizes:
        docs = build_documents(n, seed=bench.SEED)
        sim = bench.Counter()
        print(f"  measuring n={n:,}: brute force...", flush=True)
        found_brute, t_brute, m_brute = timed(BruteForce(a.threshold).find, docs, sim)
        assert sim.calls == n * (n - 1) // 2
        print(f"  brute {t_brute:.2f}s; measuring LSH...", flush=True)
        sim2 = bench.Counter()
        found_lsh, t_lsh, m_lsh = timed(YourFinder(a.threshold).find, docs, sim2)
        hits = len(found_lsh & found_brute)
        row = {
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "n": n, "actual_docs": len(docs), "threshold": a.threshold,
            "brute_s": t_brute, "brute_calls": sim.calls,
            "brute_peak_bytes": m_brute, "brute_pairs": len(found_brute),
            "lsh_s": t_lsh, "lsh_calls": sim2.calls, "lsh_peak_bytes": m_lsh,
            "lsh_pairs": len(found_lsh),
            "lsh_recall": hits / len(found_brute) if found_brute else 1.0,
            "lsh_precision": hits / len(found_lsh) if found_lsh else 1.0,
        }
        data["runs"].append(row)
        save(path, data)  # preserve each completed measurement immediately
        print(f"  n={n:>6}  brute {t_brute:>8.2f}s {sim.calls:>12,} cmp"
              f" | lsh {t_lsh:>7.2f}s {sim2.calls:>9,} cmp", flush=True)
        if a.stop_after is not None and max(t_brute, t_lsh) >= a.stop_after:
            data["unpleasant"] = {
                "n": n, "reason": "wall time exceeded the requested waiting threshold",
                "limit_s": a.stop_after, "brute_s": t_brute, "lsh_s": t_lsh,
            }
            save(path, data)
            break

    print(f"\n  -> {path} ({len(data['runs'])} measurements)")


if __name__ == "__main__":
    main()
