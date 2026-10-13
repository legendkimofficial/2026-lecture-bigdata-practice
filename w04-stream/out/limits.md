# Task 2 — Memory and practical limits

## A6: Machine and reproducibility

- Date: 2026-10-13, Asia/Seoul. CPU: Intel Core Ultra 5 225U (12 cores, 14 logical processors).
- OS: Windows 11 Home (build 26200); Python 3.12.14, 64-bit bundled runtime.
- OS-visible RAM: 16,605,634,560 bytes (15.465 GiB). Initially only 1,294,585,856 bytes (1.206 GiB) were available, with 92% system memory load.
- Other visible applications: ChatGPT, Chrome, Notion, Notepad, Snipping Tool, Windows Settings, Realtek Audio Console. Their memory use changed during the experiment; the larger probe records its own starting memory state.
- Command: `python task2_limits.py --sizes 100000,400000,1600000,6400000`. The provided measurement runner was not modified. It generates a fresh stream for each method using seed 246 and `distinct_ratio=0.4`; that ratio sets the key range, not the final number of unique keys.
- The algorithms do not accumulate the input stream. Both time and peak Python allocations are measured with `tracemalloc` active; reported MB means 1,000,000 bytes, not MiB. These allocation peaks are not whole-process RSS or total system RAM use.

## A1 and A3: Four completed sizes and the memory curve

Four distinct sizes span 64x, exceeding the required 16x range.

| Stream n | True distinct | Exact seconds | Exact peak MB | FM seconds | FM peak bytes | FM estimate | Estimate / truth |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100,000 | 36,702 | 0.351 | 3.926 | 1.865 | 4,897 | 44,417.9 | 1.210x |
| 400,000 | 146,970 | 1.289 | 11.591 | 5.325 | 4,727 | 193,752.2 | 1.318x |
| 1,600,000 | 587,625 | 3.726 | 46.648 | 12.035 | 4,729 | 845,153.2 | 1.438x |
| 6,400,000 | 2,349,909 | 15.123 | 188.288 | 102.591 | 4,730 | 2,493,948.1 | 1.061x |

## A2: Where I stopped and why

At 6,400,000 items the exact set already held 2,349,909 distinct strings and needed 188.288 MB of traced Python allocations. Its measured elapsed time was 15.123 seconds; FM was slower (102.591 seconds), so a small sketch does not automatically make the Python implementation faster.

I then attempted 25,000,000 items using the unchanged `exact_distinct` in an isolated child process. A first conservative probe stopped after 24.402 seconds at 769.324 MiB resident memory because of a chosen 768 MiB cap. That is a chosen cap, not an OS memory failure (`limit_probe.json`).

To go beyond that conservative cap, I attempted **50,000,000** items with a 2 GiB child-resident cap, a 512 MiB minimum available-system-RAM guard, and a 60-second time limit. The larger run was stopped after **40.767 seconds** because **available system RAM fell below 512 MiB**. Its recorded peak resident memory was **2432.461 MiB**, and the lowest sampled system-available RAM was **464.621 MiB**. Full thresholds and the stopping reason are saved in `limit_probe_50m.json`; `probe_limit.py` reproduces this protected attempt.

This is the practical stopping point under the explicitly recorded limits, not a claim that 50 million is the computer's absolute maximum or that Python raised `MemoryError`. The interrupted attempt has no completed distinct count, exact allocation peak, or FM ratio, so it is kept separate from the four completed comparisons in `limits.json` rather than inventing a fifth completed result.

The guard samples every 0.25 seconds. A sudden set resize can overshoot a resident-memory threshold before the next sample; that is why the recorded peak may exceed the chosen 2 GiB cap. The child was terminated as soon as a sampled stopping condition was observed.

## A4: Growth rates

When n grew 64x, exact-set peak allocations grew 47.96x (endpoint exponent 0.931, approximately linear). The larger three runs use roughly 29.42 bytes per stream item. The set needs O(D) memory for D distinct items, and this generated stream has D proportional to n, hence O(n). String sizes and discrete set resizing explain deviations from a perfectly straight line.

FM uses 64 one-byte maximum-rank registers plus a fixed 512-byte digest and small temporary objects. Its recorded peaks stayed between 4,727 and 4,897 bytes, changing by 0.966x over the same 64x input range (endpoint exponent -0.008, effectively zero). Thus its memory is O(h), or O(1) with fixed h=64, in the 64-bit-hash model. The small variation is temporary allocation/warm-up overhead, not stored stream items.

## A5: Accuracy and the tradeoff

FM ratios were 1.210x, 1.318x, 1.438x, 1.061x. Every completed size is inside the required [0.5, 2] interval. Error does not improve monotonically with n; adding items does not add registers or independently averaged estimates. The stable memory costs accuracy, and the 64 hash words per item also cost CPU time.

A factor-of-two estimate may suffice for a rough traffic-scale or trend dashboard, but is unsuitable for per-user billing, exact compliance counts, or a capacity decision near a hard threshold.

## Connection to the Week04-01 lecture

At 27:02-27:27, the lecture distinguishes the small counter memory from the CPU cost of applying many hashes. These measurements show the same distinction: a fixed-size FM sketch need not run faster than an exact set. At 43:19-43:43, the lecture asks us to declare what is preserved and what is sacrificed; here it is fixed memory versus an approximate distinct count, not a guarantee of improving accuracy with a longer stream.
