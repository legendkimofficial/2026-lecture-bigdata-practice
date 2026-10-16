#!/usr/bin/env python3
"""Week 6 · Task 3 — Make pass two fit.

Textbook §6.3 (PCY), §6.3.2 - §6.3.4.

`PlainApriori` does what Task 1 asked: use pass one to drop infrequent items,
then count every pair of surviving items. That is already much better than
counting all pairs. It is still not enough, because the surviving items are the
common ones, and the common ones appear together constantly.

The harness measures **the peak number of pair counters you held**, because
that is the thing that decides whether the algorithm runs at all. §6.3 is about
spending pass one's spare memory to shrink it.

    python3 bench.py
    python3 bench.py --yours

Correctness first: you must find exactly the same frequent pairs. Finding fewer
is not an optimisation.
"""
from array import array
from collections import Counter
from itertools import combinations
from operator import index
from sys import getsizeof


class PlainApriori:
    """Pass one drops infrequent items. Pass two counts every surviving pair."""

    def __init__(self, support):
        self.support = support
        self.peak_counters = 0

    def run(self, baskets):
        counts = Counter()
        for basket in baskets:
            counts.update(basket)
        frequent = {i for i, c in counts.items() if c >= self.support}

        pair_counts = Counter()
        for basket in baskets:
            items = sorted(basket & frequent)
            for pair in combinations(items, 2):
                pair_counts[pair] += 1
            self.peak_counters = max(self.peak_counters, len(pair_counts))

        return {frozenset(p): c for p, c in pair_counts.items()
                if c >= self.support}


class YourAlgorithm:
    """Your frequent-pair finder.

        __init__(support)
        run(baskets) -> {frozenset({a, b}): count}
        .peak_counters -> the most pair counters you ever held at once

    Same pairs as the baseline. Fewer counters.

    Pass one only needs one integer per item, and there are not many items. The
    rest of your memory is sitting idle while you do it. §6.3 spends it: hash
    every pair you see in pass one into a fixed array of buckets, and count the
    buckets rather than the pairs.

    A bucket whose total is below the support threshold cannot contain a
    frequent pair. In pass two you skip every pair landing in such a bucket -
    and the bucket array collapses to a bitmap, one bit each, before you need
    the memory for counters.

    Two things to be careful of:

      * a bucket being frequent does not make its pairs frequent. It is a
        filter, not an answer
      * `peak_counters` is on your honour. Count the pair counters you hold at
        the same time. The bitmap is not a pair counter, but if you keep the
        full bucket counts alive into pass two, that is not free either -
        observation.md asks about it
    """

    def __init__(self, support, bucket_count=1 << 20):
        self.support = index(support)
        self.bucket_count = index(bucket_count)
        if self.support <= 0 or self.bucket_count <= 0:
            raise ValueError("support and bucket_count must be positive integers")
        self.peak_counters = 0
        self.bucket_array_bytes = 0
        self.bitmap_bytes = 0
        self.frequent_bucket_count = 0

    def run(self, baskets):
        # As with PlainApriori, baskets must be iterable twice. IDs are assigned
        # in first-encounter order: arbitrary hashable items need not be sortable.
        self.peak_counters = 0
        support, bucket_count = self.support, self.bucket_count
        item_ids, original_items, item_counts = {}, [], []
        # A packed unsigned integer array, not a million Python integer objects.
        # Saturating at support preserves the only question PCY asks of a bucket.
        typecode = "I" if support <= 0xffffffff else "Q"
        buckets = array(typecode, [0]) * bucket_count
        self.bucket_array_bytes = getsizeof(buckets)

        for basket in baskets:
            ids = []
            for item in set(basket):  # support counts baskets, not duplicate rows
                item_id = item_ids.get(item)
                if item_id is None:
                    item_id = len(original_items)
                    item_ids[item] = item_id
                    original_items.append(item)
                    item_counts.append(0)
                item_counts[item_id] += 1
                ids.append(item_id)
            ids.sort()
            for left, right in combinations(ids, 2):
                bucket = ((left * 0x9e3779b1) ^ (right * 0x85ebca77)) % bucket_count
                if buckets[bucket] < support:
                    buckets[bucket] += 1

        frequent = {i for i, count in enumerate(item_counts) if count >= support}
        bitmap = bytearray((bucket_count + 7) // 8)
        frequent_buckets = 0
        for bucket, count in enumerate(buckets):
            if count >= support:
                bitmap[bucket >> 3] |= 1 << (bucket & 7)
                frequent_buckets += 1
        self.bitmap_bytes = getsizeof(bitmap)
        self.frequent_bucket_count = frequent_buckets
        # Crucially, free the integer array before allocating any pair counters.
        del buckets, item_counts

        pair_counts = {}
        for basket in baskets:
            ids = sorted({item_ids[item] for item in basket
                          if item_ids[item] in frequent})
            for left, right in combinations(ids, 2):
                bucket = ((left * 0x9e3779b1) ^ (right * 0x85ebca77)) % bucket_count
                if bitmap[bucket >> 3] & (1 << (bucket & 7)):
                    pair = (left, right)
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1
            self.peak_counters = max(self.peak_counters, len(pair_counts))

        # Transfer entries instead of holding two complete support dictionaries.
        # len(pair_counts) + len(result) never exceeds peak_counters, including
        # during output construction; the bitmap is memory but is not a counter.
        result = {}
        while pair_counts:
            (left, right), count = pair_counts.popitem()
            if count >= support:
                result[frozenset((original_items[left], original_items[right]))] = count
        return result
