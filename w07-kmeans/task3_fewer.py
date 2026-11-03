#!/usr/bin/env python3
"""Week 7 · Task 3 — The same clustering, with far fewer distances.

Textbook §7.3, and §7.1.3 for why distance is the expensive part.

`NaiveKMeans` does what the definition says: every iteration, compare every
point with every centroid. That is n x k distance computations per pass, and on
a real dataset the distance computation is almost the entire cost.

Most of that work is wasted. After the first couple of iterations, most points
do not change cluster, and most centroids barely move. The triangle inequality
lets you prove a point cannot have changed cluster **without measuring it**.

    python3 bench.py
    python3 bench.py --yours

Correctness first: your final SSE must match the baseline's. Fewer distances
with a worse clustering is not an improvement, it is a different algorithm.
"""


class NaiveKMeans:
    """Every point against every centroid, every iteration."""

    def __init__(self, k, max_iter=50):
        self.k, self.max_iter = k, max_iter

    def run(self, points, initial_centroids, distance):
        centroids = list(initial_centroids)
        labels = [None] * len(points)
        for self.iterations in range(1, self.max_iter + 1):
            changed = False
            for i, p in enumerate(points):
                best, bi = None, 0
                for j, c in enumerate(centroids):
                    d = distance(p, c)
                    if best is None or d < best - 1e-12:
                        best, bi = d, j
                if labels[i] != bi:
                    labels[i] = bi
                    changed = True
            centroids = _means(points, labels, self.k, centroids)
            if not changed:
                break
        return labels, centroids


def _means(points, labels, k, previous):
    out = []
    for j in range(k):
        group = [p for p, l in zip(points, labels) if l == j]
        if group:
            out.append(tuple(sum(v) / len(group) for v in zip(*group)))
        else:
            out.append(previous[j])
    return out


class YourKMeans:
    """Exact Lloyd iterations with Hamerly's two bounds per point.

    ``upper[i]`` bounds the distance to the assigned centroid from above;
    ``lower[i]`` bounds every other centroid distance from below. Moving the
    assigned centroid by m increases upper by at most m, and moving any
    centroid by at most M decreases lower by at most M (triangle inequality).
    Half the distance to the nearest other centroid gives another safe test:
    if upper < half_separation, no other centroid can be nearer.

    A strict numerical margin makes uncertain cases use a full ordered scan,
    including ties within the baseline's 1e-12 comparison tolerance. The scan
    and centroid update preserve the baseline's order, so the answer is exact.
    Only two additional numbers per point are retained, plus O(k) bounds.
    Every actual distance, including centroid bookkeeping, uses the callback.
    """

    TIE_TOLERANCE = 1e-12

    def __init__(self, k, max_iter=50):
        if k < 1 or max_iter < 1:
            raise ValueError("k and max_iter must be positive")
        self.k, self.max_iter = k, max_iter

    def run(self, points, initial_centroids, distance):
        if len(initial_centroids) != self.k:
            raise ValueError("initial_centroids must contain exactly k points")
        centroids = list(initial_centroids)
        labels = [None] * len(points)
        upper = [float("inf")] * len(points)
        lower = [0.0] * len(points)
        self.distance_counts = {
            "initial_assignment": 0, "refresh": 0, "rescan": 0,
            "centroid_pairs": 0, "centroid_moves": 0,
        }
        self.pruning_counts = {"lower_bound": 0, "half_separation": 0}
        self.iteration_stats = []

        def safely_below(u, bound):
            # Leave a conservative floating-point margin. In a borderline case
            # the full scan, rather than a bound, decides the ordered winner.
            if bound == float("inf"):
                return u < bound
            margin = 1e-10 * max(1.0, abs(u), abs(bound))
            return u + self.TIE_TOLERANCE + margin < bound

        for self.iterations in range(1, self.max_iter + 1):
            calls_before = sum(self.distance_counts.values())
            pruned, refreshed, scanned, changed = 0, 0, 0, False
            separation = [float("inf")] * self.k
            if self.iterations > 1:
                for a in range(self.k):
                    for b in range(a + 1, self.k):
                        half = distance(centroids[a], centroids[b]) / 2
                        self.distance_counts["centroid_pairs"] += 1
                        separation[a] = min(separation[a], half)
                        separation[b] = min(separation[b], half)

            for i, point in enumerate(points):
                previous = labels[i]
                own_distance = None
                if previous is not None:
                    threshold = max(lower[i], separation[previous])
                    if not safely_below(upper[i], threshold):
                        own_distance = distance(point, centroids[previous])
                        self.distance_counts["refresh"] += 1
                        refreshed += 1
                        upper[i] = own_distance
                    if safely_below(upper[i], threshold):
                        pruned += 1
                        reason = ("lower_bound" if lower[i] >= separation[previous]
                                  else "half_separation")
                        self.pruning_counts[reason] += 1
                        continue

                # Reproduce the baseline's left-to-right, tolerance-aware scan.
                # A retained winner need not be the strict minimum within 1e-12,
                # so lower is computed over *all other* centroids afterwards.
                distances = []
                best, winner = None, 0
                for j, centroid in enumerate(centroids):
                    if j == previous and own_distance is not None:
                        d = own_distance
                    else:
                        d = distance(point, centroid)
                        category = ("initial_assignment" if previous is None
                                    else "rescan")
                        self.distance_counts[category] += 1
                    distances.append(d)
                    if best is None or d < best - self.TIE_TOLERANCE:
                        best, winner = d, j
                scanned += 1
                upper[i] = distances[winner]
                lower[i] = min((d for j, d in enumerate(distances) if j != winner),
                               default=float("inf"))
                if previous != winner:
                    labels[i] = winner
                    changed = True

            updated = _means(points, labels, self.k, centroids)
            if changed and self.iterations < self.max_iter:
                movement = [distance(old, new)
                            for old, new in zip(centroids, updated)]
                self.distance_counts["centroid_moves"] += self.k
                largest_move = max(movement)
                for i, label in enumerate(labels):
                    upper[i] += movement[label]
                    lower[i] = max(0.0, lower[i] - largest_move)
            centroids = updated
            self.iteration_stats.append({
                "iteration": self.iterations,
                "distance_calls": sum(self.distance_counts.values()) - calls_before,
                "points_pruned": pruned,
                "own_distances_refreshed": refreshed,
                "full_scans": scanned,
            })
            if not changed:
                break
        return labels, centroids
