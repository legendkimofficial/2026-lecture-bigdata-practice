#!/usr/bin/env python3
"""Reproduce the PCY correctness, bucket-size and traced-memory experiments.

Run `python3 measure_pcy.py` from w06-apriori. Results go to
out/pcy_experiments.json. Traced runs are sequential and can take a few minutes;
their elapsed times must not be compared with the untraced bucket experiments.
"""
import argparse
import gc
import json
import platform
import random
import sys
import time
import tracemalloc
from array import array
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from bench import ITEMS, SEED, SUPPORT, build
from task3_pcy import PlainApriori, YourAlgorithm

OUT = Path(__file__).resolve().parent / "out" / "pcy_experiments.json"
SIZES = (1000, 2000, 3000, 5000, 20000)


def check_correctness():
    """Compare full support dictionaries against independent brute force."""
    cases = [
        ([], 1), ([set()], 1), ([{"a"}], 1),
        ([{"a", "b"}, {"a", "b"}, {"a"}], 2),
        ([{1, "one", (2, 3)}, {1, "one"}, {(2, 3)}], 1),
        ([{"x", "y"}, {"x", "y"}], 3),
        ([["a", "a", "b"], ["b", "b", "a"]], 2),
    ]
    rng = random.Random(606)
    for _ in range(200):
        n_items = rng.randint(1, 18)
        baskets = [set(rng.sample(range(n_items), rng.randint(0, n_items)))
                   for _ in range(rng.randint(0, 45))]
        cases.append((baskets, rng.randint(1, 48)))
    bucket_counts = [1, 7, 64, 257]
    checks = 0
    for baskets, support in cases:
        counts = {}
        for basket in baskets:
            for pair in combinations(set(basket), 2):
                key = frozenset(pair)
                counts[key] = counts.get(key, 0) + 1
        expected = {pair: count for pair, count in counts.items()
                    if count >= support}
        for bucket_count in bucket_counts:
            algo = YourAlgorithm(support, bucket_count)
            assert algo.run(baskets) == expected
            assert algo.peak_counters >= len(expected)
            assert algo.run([]) == {} and algo.peak_counters == 0
            checks += 1
    return {"random_seed": 606, "cases": len(cases),
            "bucket_counts": bucket_counts, "exact_dict_checks": checks,
            "repeated_run_reset_checks": checks,
            "mixed_hashable_and_duplicate_item_edges": True}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    correctness = check_correctness()
    baskets = build()  # All input allocation precedes tracemalloc.start().
    baseline = PlainApriori(SUPPORT)
    t0 = time.perf_counter()
    reference = baseline.run(baskets)
    elapsed = time.perf_counter() - t0
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "machine": {"platform": platform.platform(), "python": sys.version},
        "input": {"seed": SEED, "baskets": len(baskets), "items": ITEMS,
                  "support": SUPPORT},
        "notes": [
            "bench.py and PlainApriori remain unmodified. Every correctness comparison checks full support dictionaries, not keys alone.",
            "The integer bucket array is deleted before pass-two pair counters are created. The bitmap has one bit per bucket.",
            "Peak counters include output construction: popping entries before adding results prevents counter duplication.",
            "tracemalloc profiles run sequentially after input construction and GC; reported peak includes new algorithm allocations and output but excludes pre-existing baskets/reference.",
            "Wall times depend on concurrent system work; tracemalloc substantially slows execution.",
            "First-encounter internal integer IDs permit mixed hashable items without sorting or numerically hashing user items.",
        ],
        "correctness_checks": correctness,
        "baseline": {"frequent_pairs": len(reference),
                     "peak_counters": baseline.peak_counters, "seconds": elapsed},
        "bucket_experiments": [], "memory_profiles": [],
    }

    def save():
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")

    for size in (1 << 20, 1 << 16):
        algo = YourAlgorithm(SUPPORT, size)
        t0 = time.perf_counter()
        result = algo.run(baskets)
        elapsed = time.perf_counter() - t0
        assert result == reference
        row = {
            "bucket_count": size, "frequent_pairs": len(result),
            "exact_support_dictionary_equal": True,
            "peak_counters": algo.peak_counters,
            "counter_reduction": 1 - algo.peak_counters / baseline.peak_counters,
            "bucket_array_object_bytes": algo.bucket_array_bytes,
            "bitmap_object_bytes": algo.bitmap_bytes,
            "bucket_payload_bytes": array("I").itemsize * size,
            "bitmap_payload_bytes": (size + 7) // 8,
            "frequent_buckets": algo.frequent_bucket_count, "seconds": elapsed,
        }
        report["bucket_experiments"].append(row)
        del result, algo
        save()
        print("bucket_experiment", json.dumps(row), flush=True)

    for n in SIZES:
        subset = baskets[:n]  # Fixed first-N baskets; same support in every run.
        expected = reference if n == len(baskets) else PlainApriori(SUPPORT).run(subset)
        for label, cls in (("baseline", PlainApriori), ("PCY_1048576", YourAlgorithm)):
            gc.collect()
            tracemalloc.start()
            try:
                algo = cls(SUPPORT)
                t0 = time.perf_counter()
                result = algo.run(subset)
                elapsed = time.perf_counter() - t0
                current, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            assert result == expected  # Comparison occurs outside the measured region.
            row = {"baskets": n, "algorithm": label,
                   "peak_counters": algo.peak_counters, "frequent_pairs": len(result),
                   "traced_current_bytes": current, "traced_peak_bytes": peak,
                   "seconds_with_tracing": elapsed}
            if n == len(baskets):
                row["exact_support_dictionary_equal"] = True
            report["memory_profiles"].append(row)
            del result, algo
            save()
            print("memory_profile", json.dumps(row), flush=True)

    profiles = {(r["baskets"], r["algorithm"]): r for r in report["memory_profiles"]}
    base = profiles[(len(baskets), "baseline")]["traced_peak_bytes"]
    pcy = profiles[(len(baskets), "PCY_1048576")]["traced_peak_bytes"]
    bracket = None
    for left, right in zip(SIZES, SIZES[1:]):
        delta = lambda n: (profiles[(n, "PCY_1048576")]["traced_peak_bytes"]
                           - profiles[(n, "baseline")]["traced_peak_bytes"])
        if delta(left) >= 0 and delta(right) < 0:
            bracket = [left, right]
            break
    report["memory_summary"] = {
        "full_data_peak_reduction": 1 - pcy / base,
        "full_data_baseline_peak_MiB": base / (1 << 20),
        "full_data_PCY_peak_MiB": pcy / (1 << 20),
        "observed_crossover_basket_bracket": bracket,
        "crossover_conditions": "First n baskets of the fixed-seed benchmark; 2,000-item vocabulary, support 50, default 1,048,576 buckets. Bracket is inferred from the measured adjacent sample sizes.",
        "interpretation": "This is incremental traced Python memory including output, not whole-process RSS. PCY has a roughly 4.5 MB fixed first-pass cost; crossover varies with support, number and length of baskets, vocabulary and bucket collisions.",
    }
    save()
    print("saved", OUT)


if __name__ == "__main__":
    main()
