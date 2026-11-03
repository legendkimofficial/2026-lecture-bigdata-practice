# Week 07 제출 결과

실행일: 2026-11-03 KST. Python 3.13.15, Windows 11, AMD Ryzen 7 9800X3D에서 측정했다. 모든 구현과 측정 스크립트는 Python 표준 라이브러리만 사용한다.

## 제출 파일과 근거

| 파일 | 내용 |
|---|---|
| [observation.md](observation.md) | 과제별 3개 항목의 관찰 기록 |
| [curse.json](curse.json), [curse.md](curse.md) | 차원 14개, d=100의 n 비교 25회, 고정 query 보완 실험 25개 행과 A1–A8 답변 |
| [bench.txt](bench.txt) | 수정하지 않은 공식 benchmark, 거리 계산 88.8% 감소, `strong` |
| [task1_results.json](task1_results.json), [initialization.md](initialization.md) | 40개 seed 초기화 비교, 빈 군집 정책, k 선택 근거 |
| [pruning_results.json](pruning_results.json), [pruning.md](pruning.md) | 경계 증명, 실제 거리 계수, 기준과 labels·centroids·SSE 완전 일치 확인 |
| [task1_verify.txt](task1_verify.txt), [test_results.txt](test_results.txt) | 제공된 구현 검증과 전체 검사 결과 |
| [bounds_tests.txt](bounds_tests.txt) | 무작위·반복 제한·동률·중복·빈 군집 등을 비교한 추가 검사 |
| [submission_check.txt](submission_check.txt) | 필수 제출 파일 형식 검사 |

코드는 상위 폴더의 `task1_kmeans.py`, `task2_curse.py`, `task3_fewer.py`에 있다. `bench.py`, `test_tasks.py`, 저장소의 `check.py`, Task 3의 `NaiveKMeans`와 `_means`는 변경하지 않았다.

## 확인한 결과

- Task 1: random 27/40, k-means++ 40/40의 정확한 blob 복구. 평균 SSE 31.31325 대 0.12.
- Task 2: n=1,000의 측정 격자에서 contrast가 처음 1 미만인 차원은 50, 0.5 미만인 차원은 150. 표본 극값의 임계값이며 보편적 상수는 아니다.
- Task 3: 거리 계산 10,320,000 → 1,150,986회(88.8470% 감소). 공식 실행 17.47 → 2.87초. 43회 반복과 최종 SSE 10,737,882.944550687이 동일하다.
- 전체 검사: **8 passed, 0 failed, 1 skipped**. skipped는 자동 채점기가 사람의 평가로 남겨 둔 R5 설명 항목이며 [관찰 기록](observation.md)과 [경계 설명](pruning.md)에 답했다.
- 추가 차등 검사: 6개 테스트 통과. 제출 파일 형식 검사도 통과했다.

## 재현 방법

저장소 루트에서 실행한다. `python3` 명령을 쓰는 환경에서는 `python`을 `python3`으로 바꾸면 된다.

```bash
cd w07-kmeans
python measure_initialization.py
python measure_curse.py
python bench.py --yours > out/bench.txt
python measure_pruning.py
python summarize_results.py
python test_bounds.py
python test_tasks.py
python ../check.py w07
```

측정 스크립트는 해당 JSON을 교체한다. 소요 시간은 실행 환경에 따라 달라지며 `bench.txt`와 `pruning_results.json`은 서로 다른 두 실행의 시간이다. `summarize_results.py`는 원시 수치에서 보고서 표를 재생성한다. 관찰 기록의 공식 시간 예시는 제출 당시 `bench.txt` 수치다.

LMS의 website URL 입력에는 이 결과를 포함한 본인 저장소 URL을 제출한다:

[https://github.com/legendkimofficial/2026-lecture-bigdata-practice](https://github.com/legendkimofficial/2026-lecture-bigdata-practice)
