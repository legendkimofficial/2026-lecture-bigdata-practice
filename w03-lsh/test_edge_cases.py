"""Additional algorithm and measurement regressions; standard library only."""
import random
import unittest

from task1_minhash import jaccard, lsh_candidates, minhash_signatures
from task2_crossover import build_documents
from task3_scale import YourFinder
import bench


class EdgeCases(unittest.TestCase):
    def test_sparse_signatures_and_single_evaluation_per_active_row(self):
        rng = random.Random(7)
        columns = [set(rng.sample(range(29), 8)) for _ in range(6)]
        visits = []
        def tracking_hash(row):
            visits.append(row)
            return (7 * row + 3) % 31
        signatures = minhash_signatures(columns, [tracking_hash], 29)
        expected = [[min((7 * row + 3) % 31 for row in column)] for column in columns]
        self.assertEqual(signatures, expected)
        self.assertEqual(len(visits), len(set().union(*columns)))
        self.assertEqual(len(visits), len(set(visits)))

    def test_empty_sets(self):
        self.assertEqual(jaccard(set(), set()), 0)
        self.assertEqual(minhash_signatures([set()], [lambda r: r], 0), [[float("inf")]])
        self.assertEqual(YourFinder(0.6).find([set(), set(), {1}], bench.Counter()), set())

    def test_bands_are_separate_and_remainders_rejected(self):
        self.assertEqual(lsh_candidates([[1, 2], [2, 3]], 2), set())
        with self.assertRaises(ValueError):
            lsh_candidates([[1, 2, 3], [1, 2, 3]], 2)
        with self.assertRaises(ValueError):
            lsh_candidates([[1]], 0)

    def test_candidate_deduplication_and_order(self):
        docs = [{1, 2, 3} for _ in range(5)]
        counter = bench.Counter()
        found = YourFinder(0.6).find(docs, counter)
        self.assertEqual(found, {(i, j) for i in range(5) for j in range(i + 1, 5)})
        self.assertEqual(counter.calls, 10)

    def test_zero_threshold_includes_empty_documents(self):
        docs = [set(), {1}, {2}]
        self.assertEqual(YourFinder(0).find(docs, bench.Counter()), {(0, 1), (0, 2), (1, 2)})

    def test_measurements_use_real_requested_sizes(self):
        self.assertEqual(len(build_documents(4000)), 4000)
        self.assertEqual(build_documents(12), build_documents(12))


if __name__ == "__main__":
    unittest.main()
