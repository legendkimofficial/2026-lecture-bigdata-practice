"""Reproduce Task 1's combination comparison without changing the grader."""
import json
import random
import statistics
from pathlib import Path

from task1_sketches import _combine_fm, _fm_registers


def main():
    rng = random.Random(246)
    # This is a small diagnostic dataset, not storage inside the stream method.
    stream = [f"k{rng.randrange(20_000)}" for _ in range(120_000)]
    truth = len(set(stream))
    ranks, seen = _fm_registers(iter(stream))
    group_arithmetic_means = [statistics.mean(2.0 ** rank for rank in ranks[start:start + 8])
                              for start in range(0, len(ranks), 8)]
    estimates = {
        "arithmetic_mean_of_2_to_R": statistics.mean(2.0 ** rank for rank in ranks),
        "median_of_2_to_R": statistics.median(2.0 ** rank for rank in ranks),
        "median_of_group_arithmetic_means_lecture": statistics.median(group_arithmetic_means),
        "median_of_group_geometric_means_used": _combine_fm(ranks),
    }
    results = {
        "seed": 246,
        "stream_length": len(stream),
        "true_distinct": truth,
        "n_hashes": len(ranks),
        "group_size": 8,
        "registers": list(ranks),
        "group_arithmetic_means": group_arithmetic_means,
        "lecture_reference": {"title": "Week04-01", "timestamps": ["21:18", "23:27", "24:46"],
                              "rule": "Arithmetic mean of 2^R within groups, then median"},
        "estimates": {name: {"estimate": value, "ratio": value / truth}
                      for name, value in estimates.items()},
    }
    destination = Path(__file__).resolve().parent / "out" / "fm_comparison.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results["estimates"], indent=2))


if __name__ == "__main__":
    main()
