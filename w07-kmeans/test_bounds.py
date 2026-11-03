"""Differential checks for exact pruning; the supplied lab tests stay untouched."""
import random
import unittest

from bench import Distance, sse
from task3_fewer import NaiveKMeans, YourKMeans


class BoundsTests(unittest.TestCase):
    def compare(self, points, initial, max_iter=50):
        baseline = NaiveKMeans(len(initial), max_iter)
        yours = YourKMeans(len(initial), max_iter)
        expected = baseline.run(points, initial, Distance())
        counter = Distance()
        actual = yours.run(points, initial, counter)
        self.assertEqual(actual, expected)
        self.assertEqual(yours.iterations, baseline.iterations)
        self.assertEqual(sse(points, *actual), sse(points, *expected))
        self.assertEqual(sum(yours.distance_counts.values()), counter.calls)
        self.assertEqual(sum(r['distance_calls'] for r in yours.iteration_stats),
                         counter.calls)
        self.assertEqual(yours.distance_counts['initial_assignment'],
                         len(points) * len(initial))
        return yours

    def test_duplicate_centroids_and_empty_clusters(self):
        self.compare([(0.0,), (0.0,), (5.0,), (10.0,)],
                     [(0.0,), (0.0,), (100.0,), (100.0,)])
        self.compare([(2.0, 2.0)] * 8, [(2.0, 2.0)] * 5)

    def test_exact_and_near_ties(self):
        self.compare([(-1.0,), (0.0,), (1.0,)], [(-1.0,), (1.0,)])
        # The supplied comparator is tolerance-aware and ordered; retain it
        # even for a chain of near ties where the exact argmin differs.
        self.compare([(0.0,)], [(3e-12,), (2e-12,), (1.1e-12,), (0.3e-12,)], 1)
        self.compare([(0.0,), (1e-12,), (1.2e-12,), (2.4e-12,)],
                     [(3e-12,), (2e-12,), (1.1e-12,), (0.3e-12,)])

    def test_single_cluster_and_empty_points(self):
        algo = self.compare([(0.0, 1.0), (3.0, 4.0)], [(0.0, 1.0)])
        self.assertGreater(algo.pruning_counts['lower_bound'], 0)
        self.compare([], [(0.0,), (1.0,)])
        self.compare([(), (), ()], [(), ()])

    def test_randomized_and_truncated_runs(self):
        for seed in range(80):
            rng = random.Random(seed)
            dim = 1 + seed % 5
            points = [tuple(rng.randint(-5, 5) + rng.random() * 0.01
                            for _ in range(dim)) for _ in range(15 + seed % 20)]
            initial = rng.sample(points, 1 + seed % 7)
            for limit in (1, 2, 3, 50):
                with self.subTest(seed=seed, max_iter=limit):
                    self.compare(points, initial, limit)

    def test_scaled_coordinates(self):
        for scale in (1e-12, 1e12):
            for seed in range(20):
                rng = random.Random(seed)
                points = [tuple(scale * rng.uniform(-10, 10) for _ in range(3))
                          for _ in range(25)]
                with self.subTest(scale=scale, seed=seed):
                    self.compare(points, rng.sample(points, 4))

    def test_reuse_resets_diagnostics(self):
        algo = YourKMeans(2)
        points = [(0.0,), (1.0,), (9.0,), (10.0,)]
        initial = [(0.0,), (9.0,)]
        first = algo.run(points, initial, Distance())
        first_counts = dict(algo.distance_counts)
        second = algo.run(points, initial, Distance())
        self.assertEqual(second, first)
        self.assertEqual(algo.distance_counts, first_counts)


if __name__ == '__main__':
    unittest.main(verbosity=2)
