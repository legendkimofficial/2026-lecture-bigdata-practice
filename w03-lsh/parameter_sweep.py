#!/usr/bin/env python3
"""Reproduce the banding experiment requested by Task 3's observation."""
import json
import os
import time

import bench
from task3_scale import YourFinder


def main():
    docs = bench.build()
    true_pairs = bench.truth(docs)
    results = []
    for num_hashes, bands in [(120, 30), (120, 12)]:
        rows = num_hashes // bands
        sim = bench.Counter()
        start = time.perf_counter()
        found = YourFinder(bench.THRESHOLD, num_hashes, bands).find(docs, sim)
        elapsed = time.perf_counter() - start
        hit = len(found & true_pairs)
        row = {
            "num_hashes": num_hashes, "bands": bands, "rows_per_band": rows,
            "step": (1 / bands) ** (1 / rows),
            "candidate_probability_at_threshold": 1 - (1 - bench.THRESHOLD ** rows) ** bands,
            "true_pairs": len(true_pairs), "found_pairs": len(found),
            "comparisons": sim.calls, "recall": hit / len(true_pairs),
            "precision": hit / len(found) if found else 1.0, "elapsed_s": elapsed,
        }
        results.append(row)
        print(f"hashes={num_hashes}, bands={bands}, rows={rows}, "
              f"step={row['step']:.4f}, P(candidate | s=0.6)="
              f"{row['candidate_probability_at_threshold']:.4f}, "
              f"recall={row['recall']:.2%}, comparisons={sim.calls}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "parameters.json"), "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)
        file.write("\n")


if __name__ == "__main__":
    main()
