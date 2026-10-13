# Week 3 Lab · Finding Similar Items

**Theory** — 3-1 Jaccard, shingling, minhashing (§3.1 – §3.3) · 3-2 LSH, distance measures (§3.4 – §3.5)
**Submit to** — `w03-lsh/out/`

Comparing every pair of things is quadratic, and quadratic stops being possible
long before "big data" starts. This week is the standard way out, and the price
it charges.

```bash
cd w03-lsh
```

| | Task | You build |
|---|---|---|
| 1 | Minhash and LSH from the matrix up | signatures and banding, checked against the textbook's own example |
| 2 | Find the crossover on your machine | a timing and memory curve, and the size where it hurts |
| 3 | Find the same pairs, comparing far less | a finder scored on comparisons and recall |

Details and requirements are in **`task1.md`**, **`task2.md`**, **`task3.md`**.

## Running everything

```bash
python3 task1_minhash.py --verify
python3 task2_crossover.py --sizes 250,500,1000,2000
python3 bench.py --yours
python3 test_tasks.py
```

## What to submit

| File | From |
|---|---|
| `task1_minhash.py` | your minhash and LSH |
| `out/crossover.json` · `out/curve.md` | the timing curve and where it broke |
| `task3_scale.py` · `out/bench.txt` | your finder and its numbers |
| `out/observation.md` | 2–3 lines per task |

```bash
python3 ../check.py w03
```

## No download needed

Tasks 1 and 3 run on synthetic data with a fixed seed, so everybody's numbers
are comparable. Task 2 is about **your** machine, so its numbers are not
supposed to match anybody else's — that is the point of it.

## Reproduce this submission

Only the Python standard library is needed. On Windows, use `python` instead
of `python3`; `-X utf8` makes the Korean write-ups portable.

```bash
python -X utf8 task1_minhash.py --verify
python -X utf8 task2_crossover.py --sizes 125,250,500,1000,2000,4000,8000 --stop-after 60
python -X utf8 task2_crossover.py --sizes 625,750
python -X utf8 bench.py --yours
python -X utf8 parameter_sweep.py
python -X utf8 test_edge_cases.py
python -X utf8 test_tasks.py
python -X utf8 ../check.py w03
```

The timing script now generates **exactly the requested number of documents**;
the starter's `bench.build()[:n]` capped every larger input at 2,120.
It writes completed measurements immediately and stops after a completed size
if either method exceeds `--stop-after`. Runs append to `out/crossover.json`.
The curve uses wall time with `tracemalloc` enabled; memory is additional traced
allocation during the search, excluding the already-created input documents.
Use `--output out/crossover-repeat.json` to keep the submitted measurements
and write a new experiment separately. Each row includes its measurement time.

`parameter_sweep.py` changes only the band count to reproduce the recall loss
discussed in `out/observation.md`. `bench.py` and the supplied tests are unchanged.
`w03-lsh/out/` is explicitly included in version control.

## 실행 결과 읽기

- [observation.md](out/observation.md): 과제별 핵심 관찰과 S-curve 계산
- [curve.md](out/curve.md): 실제 실행 환경, 시간·메모리 표, 교차점과 중단 지점
- [bench.txt](out/bench.txt): 수정하지 않은 공식 벤치마크의 실행 결과
- [parameters.json](out/parameters.json): 밴드 수를 바꾼 비교 실험 원자료
- [test_results.txt](out/test_results.txt), [submission_check.txt](out/submission_check.txt): 공식 검사 결과
