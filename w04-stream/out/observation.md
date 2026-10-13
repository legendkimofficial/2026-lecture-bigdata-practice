# Week 04 observations

## Task 1
Bloom insertion only sets bits and lookup checks the same positions, so inserted items cannot be false negatives (lecture 12:56-13:41). For m=8,192 bits, k=5, n=800 keys, predicted FP=(1-exp(-kn/m))^k=0.860%, measured 0.900%; the difference reflects finite sampling/hash occupancy. The lecture reverses the m,n symbols but uses the same formula.
For 19,953 distinct keys, mean(2^R) gave 70,720 (3.544x), median gave 16,384 (0.821x), and the lecture's median of group arithmetic means gave 71,680 (3.592x). I used the explicitly different median of group geometric means: 27,554 (1.381x), limiting large 2^R outliers; lecture 24:46 also shows arithmetic grouping can overshoot.
Reservoir selects stream positions uniformly: `rng.randrange(count)` and `slot < k` admit with k/t, followed by survival t/n, giving k/n using only k stored items; the 4,000-trial check passed (8.9% spread). For a typical-user statistic, instead sample user IDs by a consistent hash so related records stay together (lecture 07:12-09:26).

## Task 2
Four completed sizes from 100,000 to 6,400,000 span 64x; exact peak allocations rose 3.926->188.288 MB (47.96x, exponent 0.931, approximately O(n)), while FM stayed 4,727-4,897 bytes (O(64), fixed memory). Ratios 1.210x, 1.318x, 1.438x, 1.061x did not improve monotonically.
The larger exact-only 50,000,000-item attempt stopped after 40.767s because available system RAM fell below 512 MiB; peak child RSS was 2432.461 MiB. This is a documented practical limit rather than a claimed hard OOM boundary; the completed comparisons, environment, thresholds, and stopped-attempt evidence are in limits.md and the JSON files.
A factor of two can be acceptable for an approximate daily visitor trend, but not for unique-user billing or a hard capacity threshold; on this implementation the 64-hash FM also ran slower than the exact set despite using much less memory.

## Task 3
For f(k)=(1-exp(-kn/m))^k, differentiating log f gives log(1-exp(-x))+x/(exp(x)-1)=0 at x=ln 2, where x=kn/m; therefore k*=(m/n)ln 2=6.931 for m/n=10, so I chose k=7 instead of the baseline's one hash. The ideal minimum is (1/2)^(10 ln 2)=0.8193%.
The filter bit-packs its state and counts all retained instance/bytearray/seed allocation: 80,000 bits total, with 79,192 usable Bloom positions after Python/seed overhead on this runtime. Its adjusted prediction is 0.8605%, measured 0.8680% (1,736/200,000), versus baseline 9.5115%; reduction is 90.87%, false negatives are zero, and the strong threshold <=0.9% is met.
If n is unknown, start with an explicit expected capacity and monitor bit occupancy; growing/scalable filters require additional memory. Guessing n too low overloads the planned capacity and raises FP; too high allocates unnecessary memory when sizing m, or selects too few hashes when m is fixed. An unbounded stream cannot keep a fixed low FP forever, and deleting old bits would break the no-false-negative contract.
