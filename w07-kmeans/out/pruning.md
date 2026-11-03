# Week 07 · 동일한 군집, 더 적은 거리 계산

## 공식 benchmark

bench.py, NaiveKMeans와 _means는 원본 그대로 유지했다. 공식 실행 출력은 bench.txt에 있다.

```text
20,000 points in 20 dimensions, k = 12

  baseline   distances   10,320,000   sse  10,737,882.94    43 iters    17.47s
  yours      distances    1,150,986   sse  10,737,882.94    43 iters     2.87s

   ok    sse matches to 0.0000%
   distance computations cut by 88.8%  (1,150,986 from 10,320,000)

   -> strong
```

## 별도 정확성·계수 진단

measure_pruning.py는 같은 입력에서 기준과 최적화를 다시 실행하고 단순 SSE 허용오차를 넘어 labels와 centroids의 원소별 완전 일치까지 assert한다. 아래 시간은 이 별도 실행의 관측값이며 bench.txt의 시간과 구분한다.

| Implementation | Distance calls | SSE | Iterations | Seconds |
|---|---:|---:|---:|---:|
| baseline | 10,320,000 | 10737882.944550687 | 43 | 17.4372 |
| Hamerly bounds | 1,150,986 | 10737882.944550687 | 43 | 2.8865 |

거리 계산 감소율은 **88.847035%**이고 SSE 차이는 **0.0**이다. labels 동일=True, centroids 동일=True.

## 경계가 정확한 이유

점 i의 현재 소속을 a라고 할 때 upper[i]는 d(x_i,c_a)의 상한이고 lower[i]는 다른 모든 중심까지 거리의 최솟값에 대한 하한이다. 중심 a가 m_a만큼 움직이면 삼각부등식으로 upper에 m_a를 더하고, lower에서는 모든 중심 이동량 중 최대 M을 빼고 0으로 자른다.

또한 separation[a]=min(j≠a) d(c_a,c_j)/2를 계산한다. upper가 이 값보다 작으면 다른 중심에 더 가까울 수 없다. 따라서 upper < max(lower, separation[a])이면 점의 소속을 유지한다. 실패하면 자기 중심까지 실제 거리를 재계산해 상한을 좁히고 같은 검사를 반복한다. 여전히 불확실하면 모든 중심을 원본과 같은 순서와 1e-12 비교 허용오차로 검사한다. 경계 검사에는 추가로 1e-10×max(1,|upper|,|bound|)의 보수적 여유를 둬 동률 근처는 전체 검사로 보낸다.

모든 할당이 기준과 같고 중심 평균의 덧셈 순서도 _means 그대로라 최종 labels·centroids가 동일하며 같은 SSE 합산도 정확히 일치한다. 거리 계산을 근사하거나 일부 좌표를 생략하지 않는다. 이동·중심 쌍·재검사를 포함한 모든 거리는 전달받은 distance callback으로 계산한다.

## 저장 공간과 유지 비용

점마다 upper/lower 두 값, 총 40,000개의 추가 수치를 보관한다. centroid separation과 movement는 O(k), 전체 추가 경계 저장량은 O(n+k)이다. 거리 전체 n×k 행렬은 저장하지 않는다. 이는 수치 개수이며 Python list/float 객체의 실제 바이트 수는 아니다.

매 반복 경계 갱신은 O(n), 중심 쌍은 k(k−1)/2개, 중심 이동은 k개의 거리 계산이다. 이 데이터에서는 66개+12개이며 첫 반복에는 중심 쌍 계산이 없고 종료 반복에는 이동 계산이 없다. _means의 원래 O(nk) grouping과 O(nd) 합산 비용은 그대로 남으므로 거리 계산 감소율과 wall time 감소율은 다르다.

| Distance category | Calls |
|---|---:|
| initial_assignment | 240,000 |
| refresh | 115,908 |
| rescan | 791,802 |
| centroid_pairs | 2,772 |
| centroid_moves | 504 |

계수 합은 1,150,986로 전달된 counter와 일치한다. pruning된 점-반복 중 lower가 더 큰 경우 481,499회, half-separation이 더 큰 경우 286,519회였다. 두 조건이 동시에 통과할 수도 있으므로 이는 더 큰 경계에 귀속한 횟수이며 각 경계 단독의 절감량은 아니다. 이 귀속 기준에서는 lower 쪽이 더 많은 일을 했다.

첫 assignment는 n×k=240,000회로 전체의 20.8517%다. 첫 반복 전체는 중심 이동 12회까지 포함해 240,012회, 20.8527%다. 시작할 때는 경계가 없으므로 첫 assignment를 pruning할 수 없다.

## 추가 검증과 재현

test_bounds.py는 360개 무작위/반복 제한/좌표 크기 조건과 동률·근접 동률·빈 군집·중복 중심·k=1·빈 입력을 기준 구현과 대조한다. 매 실행의 결과·반복 횟수·거리 계수 합을 확인한다.

```bash
python bench.py --yours
python measure_pruning.py
python test_bounds.py
```
