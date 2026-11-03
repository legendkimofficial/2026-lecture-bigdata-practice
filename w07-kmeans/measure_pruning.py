"""Reproduce exact-answer and distance-accounting diagnostics for Task 3.

The official, unmodified harness remains ``python bench.py --yours``.
This separate run additionally checks labels, centroids and every distance call.
"""
import json
import platform
from pathlib import Path
from time import perf_counter

import bench
from task3_fewer import NaiveKMeans, YourKMeans


def measure(cls, points, initial):
    algorithm = cls(bench.K)
    counter = bench.Distance()
    started = perf_counter()
    labels, centroids = algorithm.run(points, initial, counter)
    elapsed = perf_counter() - started
    return algorithm, labels, centroids, {
        'distance_calls': counter.calls,
        'sse': bench.sse(points, labels, centroids),
        'iterations': algorithm.iterations,
        'seconds': elapsed,
    }


def main():
    points, initial = bench.build()
    _, base_labels, base_centroids, base = measure(NaiveKMeans, points, initial)
    algorithm, labels, centroids, mine = measure(YourKMeans, points, initial)
    accounted = sum(algorithm.distance_counts.values())
    assert accounted == mine['distance_calls']
    assert labels == base_labels
    assert centroids == base_centroids
    assert mine['sse'] == base['sse']
    result = {
        'machine': {
            'platform': platform.platform(),
            'processor': platform.processor() or platform.machine(),
            'python': platform.python_version(),
        },
        'dataset': {'seed': bench.SEED, 'points': bench.N,
                    'dimensions': bench.DIM, 'clusters': bench.K},
        'timing_note': 'Separate diagnostics run; official timings are in bench.txt.',
        'baseline': base,
        'yours': mine,
        'labels_identical': labels == base_labels,
        'centroids_identical': centroids == base_centroids,
        'sse_difference': mine['sse'] - base['sse'],
        'distance_cut': 1 - mine['distance_calls'] / base['distance_calls'],
        'distance_counts': algorithm.distance_counts,
        'pruning_counts': algorithm.pruning_counts,
        'first_assignment_fraction': (
            algorithm.distance_counts['initial_assignment'] / mine['distance_calls']),
        'first_iteration_fraction': (
            algorithm.iteration_stats[0]['distance_calls'] / mine['distance_calls']),
        'extra_point_bound_numbers': 2 * len(points),
        'iteration_stats': algorithm.iteration_stats,
    }
    path = Path(__file__).with_name('out') / 'pruning_results.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('machine', 'iteration_stats')}, indent=2))
    print('Saved out/pruning_results.json')


if __name__ == '__main__':
    main()
