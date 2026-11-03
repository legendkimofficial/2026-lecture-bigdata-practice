#!/usr/bin/env python3
"""Week 7 · Task 2 — Watch distance stop meaning anything.

Textbook §7.1.3, the curse of dimensionality.

In two dimensions "nearest" is obvious. In two hundred, every point is roughly
the same distance from every other point, and a method built on "nearest" has
nothing left to stand on.

That is usually stated as a fact to accept. Here you measure it, on your own
machine, and find the dimension where it starts to bite for **your** data size.

    python3 task2_curse.py --dims 2,5,10,20,50,100,200
    python3 task2_curse.py --dims 500,1000 --points 2000

The contrast ratio is the number to watch.
"""
import argparse, json, math, os, platform, random, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def machine():
    processor = platform.processor() or platform.machine()
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                processor = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    return {"platform": platform.platform(), "processor": processor,
            "logical_cpus": os.cpu_count(), "python": platform.python_version()}


def euclid(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def sample_distances(n, dim, pairs, seed=246):
    if n < 2 or dim < 1 or pairs < 1:
        raise ValueError("need n >= 2, dim >= 1 and pairs >= 1")
    rng = random.Random(seed + dim)
    pts = [tuple(rng.random() for _ in range(dim)) for _ in range(n)]
    ds = []
    for _ in range(pairs):
        i, j = rng.randrange(n), rng.randrange(n)
        if i != j:
            ds.append(euclid(pts[i], pts[j]))
    return ds


def summarize(ds):
    """Population statistics of the observed distances (not a variance estimate)."""
    if not ds:
        raise ValueError("no distinct-point pairs were sampled; increase pairs")
    lo, hi = min(ds), max(ds)
    mean = sum(ds) / len(ds)
    stdev = math.sqrt(sum((d - mean) ** 2 for d in ds) / len(ds))
    return {"pairs": len(ds), "min": lo, "max": hi, "mean": mean,
            "stdev": stdev, "contrast": (hi - lo) / lo if lo else None,
            "relative_stdev": stdev / mean if mean else None}


def measure(n, dim, pairs=20000, seed=246):
    """Time data generation and pair distances; keep the original sampling rule."""
    t0 = time.perf_counter()
    ds = sample_distances(n, dim, pairs, seed)
    elapsed = time.perf_counter() - t0
    return {"dim": dim, "points": n, "attempted_pairs": pairs, "seed": seed,
            **summarize(ds), "seconds": elapsed}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dims", default="2,5,10,20,50,100,200")
    p.add_argument("--points", type=int, default=1000)
    p.add_argument("--pairs", type=int, default=20000)
    p.add_argument("--seed", type=int, default=246)
    a = p.parse_args()
    try:
        dims = [int(x) for x in a.dims.split(",")]
        if not dims or min(dims) < 1 or a.points < 2 or a.pairs < 1:
            raise ValueError
    except ValueError:
        p.error("dims must be positive integers; points >= 2 and pairs >= 1")
    os.makedirs(OUT, exist_ok=True)

    rows = []
    for dim in dims:
        row = measure(a.points, dim, a.pairs, a.seed)
        rows.append(row)
        print(f"  dim {dim:>5}   mean {row['mean']:>7.3f}   min {row['min']:>7.3f}   "
              f"max {row['max']:>7.3f}   contrast {row['contrast']:>7.3f}   "
              f"rel.sd {row['relative_stdev']:>6.3f}")

    path = os.path.join(OUT, "curse.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            prior = json.load(f)
    else:
        prior = {"runs": []}
    prior["machine"] = machine()
    prior["runs"].extend(rows)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(prior, f, indent=2)
    print(f"\n  -> out/curse.json  ({len(prior['runs'])} measurement(s))")


if __name__ == "__main__":
    main()
