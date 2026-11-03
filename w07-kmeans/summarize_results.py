#!/usr/bin/env python3
"""Render the Week 07 reports from measured JSON, with no extra packages.

Run after measure_initialization.py, measure_curse.py and measure_pruning.py.
"""
import json
import math
from pathlib import Path
from statistics import mean

OUT = Path(__file__).resolve().parent / "out"


def write(name, lines):
    (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def curse_report():
    data = json.loads((OUT / "curse.json").read_text(encoding="utf-8"))
    rows = sorted((r for r in data["runs"] if r.get("experiment") == "dimension_sweep"),
                  key=lambda r: r["dim"])
    machine = data["machine"]
    crossings = {t: next(r for r in rows if r["contrast"] < t) for t in (1, 0.5)}
    largest = max(rows, key=lambda r: r["dim"])
    lines = ["# Week 07 · 차원과 거리 집중 현상", "", "## A1–A2 · 측정 방법과 표", "",
             f"- 실행 시각: {data['measured_at']} (KST).",
             f"- CPU: {machine['processor']}, logical CPUs {machine['logical_cpus']}.",
             f"- OS: {machine['platform']}; Python {machine['python']}.",
             "- 기본 차원 실험은 모든 d에서 n=1,000, seed=246, [0,1)의 독립 균등 좌표를 사용했다.",
             "- 제공된 표본 규칙을 유지했다: 20,000번 무작위 인덱스 쌍을 뽑고 i=j를 제외한다. "
             "중복 쌍은 허용하며 아래 Pairs는 실제 거리 수다. 전체 n(n−1)/2개 거리의 극값은 아니다.",
             "- Seconds는 점 생성과 거리 표본 계산의 wall time이며, 통계 계산·파일 저장은 제외한다. "
             "단일 실행 측정으로 OS/다른 앱 부하에 따라 달라진다. Task 3 전체 benchmark와 겹치지 않았다. "
             "보완 query 실험의 cumulative_seconds는 앞선 prefix의 통계 시간도 포함하는 별도 누적 시간이다.",
             "", "| d | n | Pairs | Min | Max | Mean | SD | Contrast | SD / Mean | Mean / √(d/6) | Seconds |",
             "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['dim']} | {r['points']:,} | {r['pairs']:,} | {r['min']:.5f} | "
                     f"{r['max']:.5f} | {r['mean']:.5f} | {r['stdev']:.5f} | "
                     f"{r['contrast']:.5f} | {r['relative_stdev']:.5f} | "
                     f"{r['mean'] / math.sqrt(r['dim'] / 6):.5f} | {r['seconds']:.4f} |")
    lines += ["", "## A3 · Contrast의 변화와 임계 구간", "",
              f"Contrast=(max−min)/min은 2차원의 {rows[0]['contrast']:.3f}에서 "
              f"1,000차원의 {largest['contrast']:.5f}로 감소했다. 이번 측정 격자에서 처음 "
              f"1 미만은 d={crossings[1]['dim']} ({crossings[1]['contrast']:.5f}), "
              f"0.5 미만은 d={crossings[0.5]['dim']} ({crossings[0.5]['contrast']:.5f})였다. "
              "각각 40–50차원, 125–150차원 사이에서 처음 관찰된 교차이며 보편적 임계 차원은 아니다. "
              "100→125차원에서는 극값의 표본 변동 때문에 contrast가 오히려 조금 증가했다.",
              "", "## A4 · 평균 거리는 d보다 √d에 비례한다", "",
              "독립 U,V~Uniform[0,1)에서 E[(U−V)²]=1/6이므로 E[D²]=d/6은 정확하다. "
              "E[D]≈√(d/6)은 근사이며 Jensen 부등식에 따라 모집단 E[D]≤√(d/6)이다. "
              "유한 표본의 Mean은 표본 변동으로 이 값보다 조금 클 수도 있다. "
              "표의 Mean/√(d/6)이 높은 차원에서 1에 가까워지는 것이 이 예측을 뒷받침한다.", ""]
    by_dim = {r["dim"]: r for r in rows}
    ratio = by_dim[200]["mean"] / by_dim[50]["mean"]
    lines += [f"50→200차원은 d가 4배지만 평균 거리는 {by_dim[50]['mean']:.5f}→"
              f"{by_dim[200]['mean']:.5f}로 {ratio:.3f}배였다. 선형이면 4배, √d이면 2배이므로 후자와 맞는다.",
              "", "## A5 · 상대 표준편차와 contrast의 차이", "",
              f"SD/Mean도 {rows[0]['relative_stdev']:.5f}→{largest['relative_stdev']:.5f}로 감소했다. "
              "절대 평균 거리는 커져도 평균 대비 거리 차이는 작아진다. 상대 표준편차는 분포 전체의 집중을 "
              "나타내고 극단적인 한 쌍과 표본 수에 덜 민감하므로 전반적인 거리 집중을 더 안정적으로 설명한다. "
              "반면 contrast는 관찰한 가장 가까운 거리와 먼 거리의 간격을 직접 보여 주므로 검색 극값에는 유용하다. "
              "어느 지표도 실제 군집 구조나 분류 성능의 붕괴를 단독으로 증명하지는 않는다.",
              "", "## A6 · 같은 d=100에서 n만 바꾸기", "",
              "각 n에 seed 246–250의 5회 측정을 했다. 20,000번의 쌍 추출 예산은 고정했다. "
              "seed+dim으로 생성기를 초기화하므로 같은 seed라도 n에 따라 표본 쌍과 RNG 진행 위치가 달라진다. "
              "이 표는 반복 실험의 요약이며 신뢰구간을 추정한 것은 아니다.", "",
              "| n | Mean contrast | Contrast range (5 seeds) | Mean relative SD |",
              "|---:|---:|---:|---:|"]
    counts = sorted({r["points"] for r in data["runs"] if r.get("experiment") == "point_sweep"})
    for n in counts:
        group = [r for r in data["runs"] if r.get("experiment") == "point_sweep" and r["points"] == n]
        contrasts = [r["contrast"] for r in group]
        lines.append(f"| {n:,} | {mean(contrasts):.5f} | {min(contrasts):.5f}–{max(contrasts):.5f} | "
                     f"{mean(r['relative_stdev'] for r in group):.5f} |")
    lines += ["", "이번 표에서 평균 contrast는 n=100의 약 0.533에서 n=5,000의 약 0.664로 늘었으나 "
              "500→1,000에서는 감소했다. 모든 쌍을 조사하지 않으므로 n의 증가만으로 관측 극값의 단조 변화를 "
              "보장할 수 없다. n=100에서는 가능한 unordered 쌍이 4,950개라 반복 표본이 많고, "
              "n=5,000에서는 가능한 쌍이 12,497,500개라 같은 예산으로 일부만 본다.",
              "", "### 보완 실험: 고정 query와 중첩 후보 집합", "",
              "각 seed마다 고정된 균등 query 하나를 만들고, 동일하게 생성한 후보들의 첫 n개와의 모든 거리를 측정했다. "
              "앞서 계산한 거리를 그대로 유지하므로 후보 n이 커지면 min은 증가할 수 없고 max는 감소할 수 없다. "
              "이는 전체 무작위 쌍 실험과 다른 측정이며 두 표의 contrast 수치를 직접 동일시하지 않는다.", "",
              "| Candidates n | Mean contrast (5 seeds) | Mean nearest | Mean farthest |",
              "|---:|---:|---:|---:|"]
    for n in counts:
        group = [r for r in data["nested_query_runs"] if r["points"] == n]
        lines.append(f"| {n:,} | {mean(r['contrast'] for r in group):.5f} | "
                     f"{mean(r['min'] for r in group):.5f} | {mean(r['max'] for r in group):.5f} |")
    lines += ["", "이 보완 실험의 평균 contrast는 0.31034→0.48969로 증가했고 각 seed에서도 단조 증가했다. "
              "따라서 거리 극값의 대비는 d만의 함수가 아니며 검색 대상 수와 측정 예산도 함께 명시해야 한다.",
              "", "## A7 · 가장 큰 실행", "",
              f"가장 높은 차원 실행은 n={largest['points']:,}, d={largest['dim']:,}, "
              f"유효 쌍 {largest['pairs']:,}개였고 {largest['seconds']:.4f}초가 걸렸다. "
              "해당 환경 정보와 모든 실행별 시간은 curse.json에 기록했다.",
              "", "## A8 · Week 3의 Jaccard LSH에도 적용되는가?", "",
              "이 실험만으로 Jaccard LSH가 실패한다고 결론 낼 수 없다. 여기서는 독립 균등 좌표의 유클리드 거리를 "
              "측정했지만 Week 3은 구조가 있는 문서 shingle 집합의 교집합/합집합 비율을 쓴다. "
              "MinHash의 두 집합 충돌 확률이 Jaccard similarity와 같다는 관계는 이 유클리드 실험으로 바뀌지 않는다. "
              "다만 실제 문서들의 Jaccard 유사도까지 비슷한 값, 예를 들어 대부분 0 근처에 몰리면 LSH도 이웃을 "
              "구별하기 어려워진다. 차원 수만 보고 판단하지 말고 해당 데이터의 유사도 분포와 후보·재현율을 측정해야 한다.",
              "", "## 재현", "", "```bash", "python measure_curse.py", "python summarize_results.py", "```",
              "", "첫 명령은 제출한 프로토콜 전체를 다시 실행해 curse.json을 교체한다. "
              "task2_curse.py의 기존 CLI는 개별 측정을 curse.json의 runs에 추가하며, "
              "이 보고서 생성기는 experiment 필드로 제출용 실험을 선택한다."]
    write("curse.md", lines)


def initialization_report():
    data = json.loads((OUT / "task1_results.json").read_text(encoding="utf-8"))
    lines = ["# Week 07 · k-means 초기화 실험", "",
             "BLOBS의 세 연속된 triple을 정확히 복구했는지 비교했다. centroid 번호는 무시하고 "
             "점 인덱스의 partition을 비교하며, SSE만으로 성공을 판정하지 않았다. seed는 0–39다.", "",
             "| Initialisation | Exact recoveries | Min SSE | Max SSE | Mean SSE | Mean passes |",
             "|---|---:|---:|---:|---:|---:|"]
    for init in ("random", "++"):
        r = data["initializations"][init]["summary"]
        lines.append(f"| {init} | {r['recovered']}/{r['runs']} | {r['min_sse']:.5f} | "
                     f"{r['max_sse']:.5f} | {r['mean_sse']:.5f} | {r['mean_iterations']:.3f} |")
    lines += ["", "## 빈 군집과 동률 처리", "",
              "update(points, labels, k)는 이전 centroid를 인수로 받지 않으므로, 비어 있지 않은 군집들의 새 평균을 "
              "먼저 구하고 자기 군집 평균까지의 제곱 잔차가 가장 큰 점에 빈 centroid를 놓았다. "
              "잔차 동률은 점 인덱스로 정하고 여러 빈 군집에는 서로 다른 점 인덱스를 배정한다. "
              "동일 좌표의 중복점 때문에 군집이 끝까지 비어 있을 수 있으며, k개의 비어 있지 않은 군집을 보장하지는 않는다. "
              "이전 centroid를 유지하는 대안은 이동과 재할당을 줄이지만 계속 비어 있는 군집을 남길 수 있다.", "",
              "assign은 제곱 거리를 비교하고 동률이면 낮은 centroid 인덱스를 택한다. "
              "k-means++는 D² 가중치를 직접 계산하고 모든 가중치가 0이면 미선택 점 인덱스로 결정한다. "
              "labels가 변하지 않으면 종료하며 max_iter는 안전한 상한이다. iterations는 실제 assignment/update pass 수다.",
              "", "## ++의 선행 거리 계산은 무엇을 사는가?", "",
              "이 구현은 최근접 D²를 캐시해 초기화에 O(nk) 계산과 O(n) 임시 저장 공간을 쓴다. "
              "n=9, k=3에서는 첫 중심 및 두 번째 중심까지 각각 9개씩, 총 18개 제곱 거리 계산을 한다. "
              "마지막 중심을 고른 뒤에는 더 갱신할 필요가 없다. 이 비용으로 이번 40회에서는 나쁜 local optimum을 "
              "피했지만 다른 데이터에서 성공을 보장하지는 않는다. 이미 좋은 초기 중심이 있거나 초기화 예산이 작고 "
              "여러 저렴한 재시작을 허용할 때는 random 또는 제공된 중심이 합리적일 수 있다.",
              "", "## SSE만으로 k를 정할 수 없는 이유", "",
              "최적 SSE는 k를 늘리면 감소하거나 유지된다. 군집을 나눌수록 같은 점들을 더 잘 맞출 수 있고 "
              "k=n이면 각 점 자체가 중심이 되어 SSE=0이므로, SSE 최소화만으로는 의미 있는 k를 고를 수 없다. "
              "개별 random restart 결과는 local optimum 때문에 단조적이지 않을 수도 있다. 아래는 각 k에서 "
              "동일한 40개 ++ 시작 중 최저값이며 전역 최적성의 증명은 아니다.", "",
              "| k | Best SSE (40 seeds) |", "|---:|---:|"]
    for r in data["k_sweep"]:
        lines.append(f"| {r['k']} | {r['best_sse_40_seeds']:.5f} |")
    lines += ["", "elbow, silhouette, 재시작 안정성, 또는 문제에서 필요한 군집 수를 함께 판단해야 한다.", "",
              "재현: `python measure_initialization.py` 후 `python summarize_results.py`."]
    write("initialization.md", lines)


def pruning_report():
    data = json.loads((OUT / "pruning_results.json").read_text(encoding="utf-8"))
    counts = data["distance_counts"]
    base, yours = data["baseline"], data["yours"]
    lines = ["# Week 07 · 동일한 군집, 더 적은 거리 계산", "",
             "## 공식 benchmark", "",
             "bench.py, NaiveKMeans와 _means는 원본 그대로 유지했다. 공식 실행 출력은 bench.txt에 있다.", "",
             "```text", (OUT / "bench.txt").read_text(encoding="utf-8").strip(), "```", "",
             "## 별도 정확성·계수 진단", "",
             "measure_pruning.py는 같은 입력에서 기준과 최적화를 다시 실행하고 단순 SSE 허용오차를 넘어 "
             "labels와 centroids의 원소별 완전 일치까지 assert한다. 아래 시간은 이 별도 실행의 관측값이며 "
             "bench.txt의 시간과 구분한다.", "",
             "| Implementation | Distance calls | SSE | Iterations | Seconds |",
             "|---|---:|---:|---:|---:|"]
    for name, r in (("baseline", base), ("Hamerly bounds", yours)):
        lines.append(f"| {name} | {r['distance_calls']:,} | {r['sse']:.9f} | {r['iterations']} | {r['seconds']:.4f} |")
    lines += ["", f"거리 계산 감소율은 **{data['distance_cut']:.6%}**이고 SSE 차이는 "
              f"**{data['sse_difference']:.1f}**이다. labels 동일={data['labels_identical']}, "
              f"centroids 동일={data['centroids_identical']}.",
              "", "## 경계가 정확한 이유", "",
              "점 i의 현재 소속을 a라고 할 때 upper[i]는 d(x_i,c_a)의 상한이고 lower[i]는 "
              "다른 모든 중심까지 거리의 최솟값에 대한 하한이다. 중심 a가 m_a만큼 움직이면 삼각부등식으로 "
              "upper에 m_a를 더하고, lower에서는 모든 중심 이동량 중 최대 M을 빼고 0으로 자른다.", "",
              "또한 separation[a]=min(j≠a) d(c_a,c_j)/2를 계산한다. upper가 이 값보다 작으면 "
              "다른 중심에 더 가까울 수 없다. 따라서 upper < max(lower, separation[a])이면 점의 소속을 "
              "유지한다. 실패하면 자기 중심까지 실제 거리를 재계산해 상한을 좁히고 같은 검사를 반복한다. "
              "여전히 불확실하면 모든 중심을 원본과 같은 순서와 1e-12 비교 허용오차로 검사한다. "
              "경계 검사에는 추가로 1e-10×max(1,|upper|,|bound|)의 보수적 여유를 둬 동률 근처는 전체 검사로 보낸다.", "",
              "모든 할당이 기준과 같고 중심 평균의 덧셈 순서도 _means 그대로라 최종 labels·centroids가 "
              "동일하며 같은 SSE 합산도 정확히 일치한다. 거리 계산을 근사하거나 일부 좌표를 생략하지 않는다. "
              "이동·중심 쌍·재검사를 포함한 모든 거리는 전달받은 distance callback으로 계산한다.",
              "", "## 저장 공간과 유지 비용", "",
              f"점마다 upper/lower 두 값, 총 {data['extra_point_bound_numbers']:,}개의 추가 수치를 보관한다. "
              "centroid separation과 movement는 O(k), 전체 추가 경계 저장량은 O(n+k)이다. "
              "거리 전체 n×k 행렬은 저장하지 않는다. 이는 수치 개수이며 Python list/float 객체의 실제 바이트 수는 아니다.", "",
              "매 반복 경계 갱신은 O(n), 중심 쌍은 k(k−1)/2개, 중심 이동은 k개의 거리 계산이다. "
              "이 데이터에서는 66개+12개이며 첫 반복에는 중심 쌍 계산이 없고 종료 반복에는 이동 계산이 없다. "
              "_means의 원래 O(nk) grouping과 O(nd) 합산 비용은 그대로 남으므로 거리 계산 감소율과 wall time 감소율은 다르다.", "",
              "| Distance category | Calls |", "|---|---:|"]
    for category, calls in counts.items():
        lines.append(f"| {category} | {calls:,} |")
    lines += ["", f"계수 합은 {sum(counts.values()):,}로 전달된 counter와 일치한다. "
              f"pruning된 점-반복 중 lower가 더 큰 경우 {data['pruning_counts']['lower_bound']:,}회, "
              f"half-separation이 더 큰 경우 {data['pruning_counts']['half_separation']:,}회였다. "
              "두 조건이 동시에 통과할 수도 있으므로 이는 더 큰 경계에 귀속한 횟수이며 각 경계 단독의 절감량은 아니다. "
              "이 귀속 기준에서는 lower 쪽이 더 많은 일을 했다.", "",
              f"첫 assignment는 n×k={counts['initial_assignment']:,}회로 전체의 "
              f"{data['first_assignment_fraction']:.4%}다. 첫 반복 전체는 중심 이동 12회까지 포함해 "
              f"{data['iteration_stats'][0]['distance_calls']:,}회, {data['first_iteration_fraction']:.4%}다. "
              "시작할 때는 경계가 없으므로 첫 assignment를 pruning할 수 없다.",
              "", "## 추가 검증과 재현", "",
              "test_bounds.py는 360개 무작위/반복 제한/좌표 크기 조건과 동률·근접 동률·빈 군집·" 
              "중복 중심·k=1·빈 입력을 기준 구현과 대조한다. 매 실행의 결과·반복 횟수·거리 계수 합을 확인한다.", "",
              "```bash", "python bench.py --yours", "python measure_pruning.py", "python test_bounds.py", "```"]
    write("pruning.md", lines)


def observation():
    task1 = json.loads((OUT / "task1_results.json").read_text(encoding="utf-8"))
    pruning = json.loads((OUT / "pruning_results.json").read_text(encoding="utf-8"))
    random = task1["initializations"]["random"]["summary"]
    plus = task1["initializations"]["++"]["summary"]
    write("observation.md", ["# Week 07 관찰 기록", "", "## Task 1 · 초기화가 바꾸는 답", "",
          "- 빈 군집은 새 자기 군집 평균에서 제곱 잔차가 큰 점으로 재배치했다(동률은 점 인덱스). "
          "이전 중심 유지보다 멀리 떨어진 점을 새 중심으로 삼을 수 있지만 중복 좌표에서는 빈 군집이 남을 수 있다.",
          f"- seed 0–39에서 세 blob을 정확히 복구한 횟수는 random {random['recovered']}/40, ++ {plus['recovered']}/40이고 "
          f"평균 SSE는 {random['mean_sse']:.5f} 대 {plus['mean_sse']:.5f}였다. ++는 이 예제에서 시작 전에 "
          "제곱 거리 18회를 더 계산해 나쁜 시작을 피했다. 이미 좋은 초기 중심이 있거나 초기화 예산이 작으면 이 비용을 생략할 수 있다.",
          "- 최적 SSE는 k가 늘면 감소하거나 유지되고 k=n이면 0이므로 SSE 최소화만으로 k를 정할 수 없다. "
          "이번 k=1/3/9의 40회 중 최저 SSE도 256.12/0.12/0이었다. elbow·안정성·문제의 목적을 함께 봐야 한다.",
          "", "## Task 2 · 차원과 점 개수의 영향", "",
          "- n=1,000, seed=246, 20,000번 쌍 추출에서 contrast는 측정 격자상 50차원에 처음 1 미만(0.98244), "
          "150차원에 처음 0.5 미만(0.46536)이었다. 보편적 임계값은 아니며 100→125차원에서는 표본 극값 때문에 작은 반등도 있었다.",
          "- d=100의 5개 seed 평균에서 n=100→5,000의 무작위 쌍 contrast는 0.53267→0.66421이지만 단조적이지 않았다. "
          "고정 query와 중첩 후보의 별도 실험은 0.31034→0.48969로 단조 증가해, 극값 대비에는 n과 표본 예산도 필요함을 확인했다.",
          "- 이는 균등 좌표의 유클리드 실험이라 구조 있는 shingle 집합의 Jaccard LSH를 직접 반박하지 않는다. "
          "실제 Jaccard 유사도 자체가 집중될 때 구별이 어려우므로 Week 3 데이터의 유사도 분포를 따로 확인해야 한다.",
          "", "## Task 3 · 삼각부등식으로 거리 계산 줄이기", "",
          f"- Hamerly의 점별 upper/lower 두 값({pruning['extra_point_bound_numbers']:,}개, O(n+k) 추가 경계 공간)을 저장했다. "
          "lower와 중심 사이 half-separation 중 큰 값으로 pruning했으며 더 큰 경계에 귀속한 통과 횟수는 lower 481,499회, separation 286,519회였다(중복 가능한 조건의 귀속이지 단독 효과 측정은 아니다).",
          "- 유지 비용은 매회 O(n) 경계 갱신과 중심 쌍 최대 66회·이동 최대 12회의 거리 계산이다. "
          f"첫 assignment는 240,000회({pruning['first_assignment_fraction']:.4%}), 이동을 포함한 첫 반복은 "
          f"240,012회({pruning['first_iteration_fraction']:.4%})로 시작 시 경계가 없다는 비용이 드러났다.",
          f"- 수정하지 않은 bench.py에서 거리 계산은 10,320,000→1,150,986회({pruning['distance_cut']:.4%} 감소, strong), "
          "시간은 17.47→2.87초였다. labels·centroids·43회 반복이 같고 SSE 10,737,882.944550687의 차이는 정확히 0이다. "
          "증명 가능한 할당만 생략하고 애매한 경우 원본 순서로 비교해 같은 평균을 계산했기 때문이다.",
          "", "상세 근거: [초기화](initialization.md), [거리 집중](curse.md), [경계와 계수](pruning.md)."])


if __name__ == "__main__":
    curse_report()
    initialization_report()
    pruning_report()
    observation()
    print("Wrote out/curse.md, initialization.md, pruning.md and observation.md")
