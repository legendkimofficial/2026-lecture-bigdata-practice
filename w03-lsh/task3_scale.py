#!/usr/bin/env python3
"""Week 3 · Task 3 — Find the same pairs without comparing everything.

Textbook §3.4.

`BruteForce` compares every pair. On 3,000 documents that is 4.5 million
comparisons and it is completely correct. On 3 million documents it is 4.5
trillion and it is completely useless.

Beat it. Find the same near-duplicate pairs while making far fewer comparisons.

    python3 bench.py
    python3 bench.py --yours

The harness counts every call you make to `similarity()`. That is your score.
It also checks **recall** - which of the truly similar pairs you found. Skipping
comparisons is easy; skipping comparisons without losing the pairs is the task.
"""

import random

from task1_minhash import lsh_candidates, minhash_signatures


class BruteForce:
    """Correct, and quadratic."""

    def __init__(self, threshold):
        self.threshold = threshold

    def find(self, docs, similarity):
        """docs is [set_of_shingles, ...]. Return {(i, j), ...} with i < j."""
        out = set()
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                if similarity(docs[i], docs[j]) >= self.threshold:
                    out.add((i, j))
        return out


class YourFinder:
    """Your near-duplicate finder.

        __init__(threshold)
        find(docs, similarity) -> {(i, j), ...}

    `similarity(a, b)` is the only way to compare two documents, and every call
    is counted. Everything else - signatures, banding, bucketing - is free, in
    the sense that the harness does not charge you for it. That is deliberate:
    it is also roughly true at scale, where the comparison is the expensive
    part and the hashing is linear.

    Two knobs decide everything:

        the number of hashes in a signature
        how many bands you split it into

    §3.4.2 gives you the relationship between those and the probability that a
    pair at similarity s becomes a candidate. It is an S-curve, and where its
    step sits is something you choose. Choose it on purpose and be able to say
    why in observation.md - a threshold of 0.8 does not mean bands should be
    anything in particular until you have done the arithmetic.

    You may reuse your Task 1 code.
    """

    def __init__(self, threshold, num_hashes=120, bands=30, seed=246):
        if num_hashes <= 0 or bands <= 0 or num_hashes % bands:
            raise ValueError("num_hashes must be positive and divisible by bands")
        self.threshold = threshold
        self.num_hashes = num_hashes
        self.bands = bands
        self.seed = seed

    def find(self, docs, similarity):
        if len(docs) < 2:
            return set()
        if self.threshold <= 0:
            return BruteForce(self.threshold).find(docs, similarity)

        # Assign dense row numbers without sorting or revisiting the matrix.
        row_ids = {}
        columns = []
        for doc in docs:
            column = set()
            for shingle in doc:
                if shingle not in row_ids:
                    row_ids[shingle] = len(row_ids)
                column.add(row_ids[shingle])
            columns.append(column)

        # Independent affine hashes over a prime field, reproducible by seed.
        prime = (1 << 61) - 1
        rng = random.Random(self.seed)
        coefficients = [(rng.randrange(1, prime), rng.randrange(prime))
                        for _ in range(self.num_hashes)]
        hashes = [lambda row, a=a, b=b: (a * row + b) % prime
                  for a, b in coefficients]
        signatures = minhash_signatures(columns, hashes, len(row_ids))

        # Empty documents have Jaccard 0; exclude their all-infinity signature.
        nonempty = [i for i, doc in enumerate(docs) if doc]
        candidates = lsh_candidates([signatures[i] for i in nonempty], self.bands)
        out = set()
        for left, right in sorted(candidates):
            i, j = nonempty[left], nonempty[right]
            # Never compare the documents outside the supplied counted callback.
            if similarity(docs[i], docs[j]) >= self.threshold:
                out.add((i, j))
        return out
