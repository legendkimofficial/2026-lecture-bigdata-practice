#!/usr/bin/env python3
"""Reproduce the 40-seed initialisation comparison for Week 7 Task 1.

    python measure_initialization.py

Recovery means the partition is exactly the three consecutive triples in
BLOBS, regardless of centroid numbering. No success is inferred from SSE alone.
"""
import contextlib
import io
import json
from pathlib import Path

import task1_kmeans as task


OUT = Path(__file__).resolve().parent / "out"


def partition(labels):
    return sorted(sorted(i for i, label in enumerate(labels) if label == j)
                  for j in sorted(set(labels)))


def main():
    OUT.mkdir(exist_ok=True)
    expected = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    data = {
        "seeds": list(range(40)),
        "points": task.BLOBS,
        "k": 3,
        "recovery_definition": "partition equals [[0,1,2],[3,4,5],[6,7,8]]",
        "empty_cluster_policy": (
            "Reseed at points ranked by decreasing squared residual from their "
            "new own-cluster means; point index breaks ties and each empty "
            "cluster gets a different point index."
        ),
        "initializations": {},
    }
    for init in ("random", "++"):
        runs = []
        for seed in data["seeds"]:
            labels, centroids, sse = task.kmeans(task.BLOBS, 3, init=init, seed=seed)
            runs.append({"seed": seed, "sse": sse,
                         "iterations": task.kmeans.iterations,
                         "recovered": partition(labels) == expected,
                         "labels": labels, "centroids": centroids})
        values = [run["sse"] for run in runs]
        summary = {"recovered": sum(run["recovered"] for run in runs),
                   "runs": len(runs), "min_sse": min(values),
                   "max_sse": max(values), "mean_sse": sum(values) / len(values),
                   "mean_iterations": sum(run["iterations"] for run in runs) / len(runs)}
        data["initializations"][init] = {"summary": summary, "runs": runs}
        print(f"{init}: {json.dumps(summary)}")

    # The best of the same 40 starts is reported, not claimed to be a proof of
    # optimality. k=n does reach the trivial zero-SSE solution here.
    data["k_sweep"] = []
    for k in range(1, len(task.BLOBS) + 1):
        values = [task.kmeans(task.BLOBS, k, init="++", seed=seed)[2]
                  for seed in data["seeds"]]
        data["k_sweep"].append({"k": k, "best_sse_40_seeds": min(values)})
    (OUT / "task1_results.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8")

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        result = task.verify()
    (OUT / "task1_verify.txt").write_text(captured.getvalue(), encoding="utf-8")
    print(captured.getvalue(), end="")
    raise SystemExit(result)


if __name__ == "__main__":
    main()
