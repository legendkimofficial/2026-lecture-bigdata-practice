#!/usr/bin/env python3
"""Reproduce the submitted Task 2 measurements, replacing out/curse.json.

The course sampler uses 20,000 attempted pairs and skips self-pairs. A separate
nested-query experiment isolates the effect of enlarging the search population.
Run: python measure_curse.py
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import time

from task2_curse import euclid, machine, measure, summarize

OUT = Path(__file__).resolve().parent / "out"
DIMS = (2, 5, 10, 20, 30, 40, 50, 75, 100, 125, 150, 200, 500, 1000)
COUNTS = (100, 500, 1000, 2000, 5000)
SEEDS = tuple(range(246, 251))


def nested_queries(dim=100):
    rows = []
    for seed in SEEDS:
        rng = random.Random(seed + dim)
        query = tuple(rng.random() for _ in range(dim))
        distances = []
        t0 = time.perf_counter()
        for n in COUNTS:
            while len(distances) < n:
                candidate = tuple(rng.random() for _ in range(dim))
                distances.append(euclid(query, candidate))
            rows.append({"dim": dim, "points": n, "seed": seed,
                         **summarize(distances),
                         "cumulative_seconds": time.perf_counter() - t0})
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    data = {"measured_at": datetime.now(timezone(timedelta(hours=9))).isoformat(),
            "machine": machine(),
            "protocol": {
                "distribution": "independent uniform coordinates in [0, 1)",
                "distance": "Euclidean",
                "pair_sampling": "20000 attempts with replacement; skip i == j",
                "timing": "runs[].seconds: point generation + sampling/distances; excludes statistics and I/O",
                "nested_query_timing": "cumulative_seconds includes candidate generation, distances and earlier prefix statistics; excludes query generation",
                "fixed_n_dimension_sweep": 1000,
                "point_sweep_dimension": 100,
                "seeds": list(SEEDS),
                "nested_query": "one fixed query per seed, identical nested candidate prefixes",
                "concurrency": "Task 1/3 small correctness checks may run concurrently; no parallel full benchmark"
            }, "runs": []}
    for dim in DIMS:
        # Keep the entire threshold curve at n=1000, including the largest d.
        row = {**measure(1000, dim), "experiment": "dimension_sweep"}
        data["runs"].append(row)
        print(f"d={dim:4} n=1000 contrast={row['contrast']:.4f} "
              f"relative_sd={row['relative_stdev']:.4f} time={row['seconds']:.3f}s",
              flush=True)
    for seed in SEEDS:
        for n in COUNTS:
            row = {**measure(n, 100, seed=seed), "experiment": "point_sweep"}
            data["runs"].append(row)
    data["nested_query_runs"] = nested_queries()
    (OUT / "curse.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("Saved 14 dimension runs, 25 fixed-d pair runs and 25 nested-query rows.")


if __name__ == "__main__":
    main()
