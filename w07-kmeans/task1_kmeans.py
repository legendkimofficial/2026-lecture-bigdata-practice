#!/usr/bin/env python3
"""Week 7 · Task 1 — k-means, and the thing that decides the answer.

Textbook §7.1 (clustering, the curse of dimensionality), §7.3 (k-means).

k-means is four lines: pick centroids, assign every point to the nearest one,
move each centroid to the mean of its points, repeat. It always converges.

It converges to a **local** optimum, and which one depends entirely on where you
started. That is not a footnote - it is the difference between a clustering that
means something and one that does not, and you can watch it happen on nine points.

    python3 task1_kmeans.py --verify
"""
import argparse, math, random

# Three obvious blobs of three points each. Any sensible clustering finds them.
BLOBS = [(0.0, 0.0), (0.2, 0.1), (0.1, 0.2),
         (8.0, 8.0), (8.2, 8.1), (8.1, 8.2),
         (0.0, 8.0), (0.2, 8.1), (0.1, 8.2)]


def euclidean(a, b):
    """Distance between two points of any dimension."""
    return math.sqrt(_squared_distance(a, b))


def _squared_distance(a, b):
    if len(a) != len(b):
        raise ValueError("points must have the same dimension")
    return sum((x - y) ** 2 for x, y in zip(a, b))


def _check_points(points):
    if not points or not points[0]:
        raise ValueError("at least one nonempty point is required")
    dim = len(points[0])
    if any(len(point) != dim for point in points):
        raise ValueError("points must have the same dimension")


def assign(points, centroids):
    """Nearest centroid for each point. Return a list of centroid indices.

    Ties go to the lower index, so that everybody's answer is the same.
    """
    if not centroids:
        raise ValueError("at least one centroid is required")
    # min keeps the first index on equal keys. Squaring preserves distance order.
    return [min(range(len(centroids)),
                key=lambda j: _squared_distance(point, centroids[j]))
            for point in points]


def update(points, labels, k):
    """Move each centroid to the mean of its points.

    An empty cluster has no mean. Decide what you do - and say so, because the
    choice changes the result and there is more than one defensible answer.
    """
    _check_points(points)
    if not isinstance(k, int) or not 1 <= k <= len(points):
        raise ValueError("k must be an integer between 1 and the point count")
    if len(labels) != len(points):
        raise ValueError("each point needs one label")
    dim = len(points[0])
    sums = [[0.0] * dim for _ in range(k)]
    counts = [0] * k
    for point, label in zip(points, labels):
        if not isinstance(label, int) or not 0 <= label < k:
            raise ValueError("labels must be valid centroid indices")
        counts[label] += 1
        for axis, value in enumerate(point):
            sums[label][axis] += value
    centroids = [tuple(value / count for value in total) if count else None
                 for total, count in zip(sums, counts)]

    empty = [j for j, count in enumerate(counts) if count == 0]
    if empty:
        # The public signature has no previous centroids. Place empty centres at
        # the points with largest residuals from their newly computed own means.
        # Point index resolves residual ties; each empty centre uses a different
        # point index. Duplicate coordinates can still leave a cluster empty.
        ranked = sorted(range(len(points)),
                        key=lambda i: (-_squared_distance(
                            points[i], centroids[labels[i]]), i))
        for j, i in zip(empty, ranked):
            centroids[j] = tuple(points[i])
    return centroids


def kmeans(points, k, init="random", seed=246, max_iter=100):
    """Run to convergence. Return (labels, centroids, sse).

    `sse` is the sum over points of the squared distance to their own centroid.
    It is what k-means minimises, and it is how you compare two runs.

    `init` is either:
        "random"   pick k points at random as the starting centroids
        "++"       k-means++ (§7.3.2): pick the first at random, then pick each
                   next one with probability proportional to the squared distance
                   to the nearest centroid already chosen

    Set `kmeans.iterations` to how many passes you used.
    """
    kmeans.iterations = 0
    _check_points(points)
    if not isinstance(k, int) or not 1 <= k <= len(points):
        raise ValueError("k must be an integer between 1 and the point count")
    if not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError("max_iter must be a positive integer")
    if init not in ("random", "++"):
        raise ValueError('init must be "random" or "++"')
    rng = random.Random(seed)
    if init == "random":
        centroids = [tuple(point) for point in rng.sample(points, k)]
    else:
        selected = [rng.randrange(len(points))]
        nearest = [_squared_distance(point, points[selected[0]])
                   for point in points]
        while len(selected) < k:
            total = sum(nearest)
            if total == 0:
                # Fewer than k distinct coordinates: all D^2 weights are zero.
                # Select an unused index deterministically, without dividing by 0.
                chosen = next(i for i in range(len(points)) if i not in selected)
            else:
                target = rng.random() * total
                cumulative = 0.0
                chosen = max(i for i, weight in enumerate(nearest) if weight > 0)
                for i, weight in enumerate(nearest):
                    cumulative += weight
                    if target < cumulative:
                        chosen = i
                        break
            selected.append(chosen)
            if len(selected) < k:
                nearest = [min(old, _squared_distance(point, points[chosen]))
                           for old, point in zip(nearest, points)]
        centroids = [tuple(points[i]) for i in selected]

    labels = None
    for iteration in range(1, max_iter + 1):
        next_labels = assign(points, centroids)
        centroids = update(points, next_labels, k)
        kmeans.iterations = iteration
        if next_labels == labels:
            break
        labels = next_labels
    return next_labels, centroids, sse_of(points, next_labels, centroids)


kmeans.iterations = 0


def sse_of(points, labels, centroids):
    """Sum of squared distances from each point to its assigned centroid."""
    if len(points) != len(labels):
        raise ValueError("each point needs one label")
    if any(not isinstance(label, int) or not 0 <= label < len(centroids)
           for label in labels):
        raise ValueError("labels must be valid centroid indices")
    return sum(_squared_distance(point, centroids[label])
               for point, label in zip(points, labels))


# ------------------------------------------------------------------- harness
def verify():
    fails = 0

    def check(label, ok, detail=""):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<50} {detail}")
        fails += not ok

    try:
        check("distance in 2d", abs(euclidean((0, 0), (3, 4)) - 5) < 1e-9)
        check("distance in 5d",
              abs(euclidean((0,) * 5, (1,) * 5) - math.sqrt(5)) < 1e-9)
    except NotImplementedError:
        print("  euclidean is still a stub"); return 1

    try:
        labels, cents, sse = kmeans(BLOBS, 3, init="++", seed=1)
    except NotImplementedError:
        print("  kmeans is still a stub"); return 1

    groups = {}
    for p, l in zip(BLOBS, labels):
        groups.setdefault(l, []).append(p)
    check("three clusters of three", sorted(len(g) for g in groups.values()) == [3, 3, 3],
          sorted(len(g) for g in groups.values()))
    check("the three blobs were recovered",
          all(max(q[0] for q in g) - min(q[0] for q in g) < 1 and
              max(q[1] for q in g) - min(q[1] for q in g) < 1
              for g in groups.values()))
    check("sse is small when clusters are right", sse < 1.0, f"sse {sse:.4f}")

    # Bad luck with random starts should sometimes be visibly worse.
    randoms = [kmeans(BLOBS, 3, init="random", seed=s)[2] for s in range(40)]
    plusplus = [kmeans(BLOBS, 3, init="++", seed=s)[2] for s in range(40)]
    check("random init sometimes lands badly", max(randoms) > min(randoms) * 5,
          f"sse from {min(randoms):.3f} to {max(randoms):.3f}")
    check("k-means++ is more reliable than random",
          sum(plusplus) / len(plusplus) <= sum(randoms) / len(randoms),
          f"mean sse: ++ {sum(plusplus) / len(plusplus):.3f} vs "
          f"random {sum(randoms) / len(randoms):.3f}")

    print(f"\n  {'all ok' if not fails else str(fails) + ' failed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
