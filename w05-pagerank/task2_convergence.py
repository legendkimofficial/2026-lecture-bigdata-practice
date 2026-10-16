#!/usr/bin/env python3
"""Week 5 · Task 2 — How long does it take to converge, and on what?

Textbook §5.1, §5.2.

The textbook says PageRank converges. It does not say in how many iterations,
because the answer depends on beta, on the graph, and on what you are willing
to call "converged". Those three knobs are yours to turn, on your machine,
with a graph big enough that you can feel the cost.

    python3 task2_convergence.py --betas 0.5,0.7,0.85,0.95,0.99
    python3 task2_convergence.py --nodes 20000 --betas 0.85,0.95

Your timings are about your hardware. The iteration counts are not - those are
about the mathematics, and everybody should get the same ones.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import json
import math
import os
import platform
import statistics
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def machine(background):
    info = {"platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(),
            "background": background}
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
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=True, allow_nan=False)
        file.write("\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--betas", default="0.5,0.7,0.85,0.95,0.99")
    p.add_argument("--nodes", type=int, default=None,
                   help="graph size; default is the harness graph")
    p.add_argument("--tol", type=float, default=1e-10)
    p.add_argument("--sizes", help="comma-separated graph sizes; overrides --nodes")
    p.add_argument("--tols", help="comma-separated L1 tolerances; overrides --tol")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--max-iter", type=int, default=5000)
    p.add_argument("--background", default="Codex task; other running applications not verified")
    a = p.parse_args()
    try:
        betas = [float(x) for x in a.betas.split(",")]
        sizes = [int(x) for x in a.sizes.split(",")] if a.sizes else [a.nodes or 1200]
        tols = [float(x) for x in a.tols.split(",")] if a.tols else [a.tol]
    except ValueError:
        p.error("betas/tolerances must be numbers, and sizes must be integers")
    if any(not math.isfinite(b) or not 0 <= b < 1 for b in betas):
        p.error("each beta must satisfy 0 <= beta < 1")
    if any(n < 50 for n in sizes):
        p.error("use at least 50 nodes for the supplied synthetic graph generator")
    if any(not math.isfinite(t) or t <= 0 for t in tols):
        p.error("tolerances must be finite and positive")
    if a.repeats < 1 or a.max_iter < 1:
        p.error("repeats and max-iter must be positive")
    os.makedirs(OUT, exist_ok=True)

    import bench
    from task1_pagerank import pagerank
    path = os.path.join(OUT, "convergence.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    else:
        data = {"runs": []}
    batch_id = datetime.now(timezone.utc).isoformat()
    data["machine"] = machine(a.background)
    data["seed"] = bench.SEED
    data["measurement"] = (
        "Sequential perf_counter wall time for pagerank only, including its setup; "
        "graph generation, sorting and JSON writing excluded. No warm-up. "
        "Each row is one repetition; compare medians for identical parameters."
    )
    data["prediction_before_measurement"] = (
        "At fixed beta/tolerance, iteration count should depend mainly on the "
        "graph's mixing, not directly on n. Wall time should grow with nodes "
        "and edges. Larger beta and tighter tolerance should usually require "
        "more iterations; finite graph structure can alter that trend."
    )
    save(path, data)
    capped = False
    for size in sizes:
        bench.NODES = size  # configure the unmodified harness's generator
        graph = bench.build()
        edges = sum(map(len, graph.values()))
        for tol in tols:
            for beta in betas:
                rows = []
                for repeat in range(1, a.repeats + 1):
                    t0 = time.perf_counter()
                    ranks = pagerank(graph, beta=beta, iterations=a.max_iter, tol=tol)
                    elapsed = time.perf_counter() - t0
                    top = sorted(ranks, key=lambda node: (-ranks[node], node))[:10]
                    row = {"batch_id": batch_id, "repeat": repeat,
                           "beta": beta, "nodes": len(graph), "edges": edges, "tol": tol,
                           "max_iter": a.max_iter, "iterations": pagerank.iterations,
                           "seconds": elapsed, "l1_delta": pagerank.delta,
                           "converged": pagerank.converged, "rank_sum": sum(ranks.values()),
                           "top10": top, "top10_scores": [ranks[node] for node in top]}
                    rows.append(row)
                    data["runs"].append(row)
                    capped |= not row["converged"]
                    save(path, data)
                print(f"  n={size:>6} tol={tol:.0e} beta={beta:<4} "
                      f"{rows[0]['iterations']:>4} iterations  "
                      f"median {statistics.median(r['seconds'] for r in rows):.5f}s  "
                      f"converged={all(r['converged'] for r in rows)}", flush=True)
    print(f"\n  -> out/convergence.json  ({len(data['runs'])} run(s))")
    if capped:
        raise SystemExit("Iteration limit reached; increase --max-iter before reporting convergence")


if __name__ == "__main__":
    main()
