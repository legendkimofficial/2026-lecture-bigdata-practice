#!/usr/bin/env python3
"""Build the Task 2 tables from the recorded runs, without timing anything."""
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics


def main():
    out = Path(__file__).resolve().parent / "out"
    data = json.loads((out / "convergence.json").read_text(encoding="utf-8"))
    runs = data["runs"]
    groups = defaultdict(list)
    for row in runs:
        if not row["converged"] or row["l1_delta"] >= row["tol"]:
            raise ValueError("Report requires converged measurements")
        groups[row["nodes"], row["tol"], row["beta"]].append(row)
    sizes = sorted({row["nodes"] for row in runs})
    betas = sorted({row["beta"] for row in runs})
    tols = sorted({row["tol"] for row in runs}, reverse=True)
    small, large, tight = sizes[0], sizes[-1], min(tols)

    def count(n, tol, beta):
        values = {r["iterations"] for r in groups[n, tol, beta]}
        if len(values) != 1:
            raise ValueError("Repeated iteration counts differ")
        return next(iter(values))

    def seconds(n, tol, beta):
        return statistics.median(r["seconds"] for r in groups[n, tol, beta])

    machine = data["machine"]
    lines = [
        "# Week 5 — PageRank 수렴 실험", "",
        "## A7. 환경과 측정 방법", "",
        f"- CPU: {machine['processor']} ({machine['logical_cpus']} logical CPUs)",
        f"- RAM: {machine['ram_bytes'] / 2**30:.2f} GiB "
        f"({machine['ram_bytes']:,} bytes); 시작 시 가용 "
        f"{machine['available_ram_bytes_at_start'] / 2**30:.2f} GiB",
        f"- OS / Python: {machine['platform']} / {machine['python']}",
        "- 실행 중인 프로그램: Codex/ChatGPT, Chrome, Edge/WebView2, Notion, Claude, "
        "Steam Web Helper, PowerToys, Windows 서비스. 읽기 전용 프로세스 조회로 확인했으며 "
        "CPU 점유율은 측정하지 않았고 앱을 종료하지 않았다.",
        f"- 측정 배치(UTC): `{runs[0]['batch_id']}`; seed={data['seed']}.",
        "- 변경하지 않은 `bench.build()`로 그래프를 만들었다. "
        "크기를 바꾸면 연결 구조도 달라지므로 동일 그래프를 단순 복제한 비교는 아니다.",
        "- 각 조건을 순차적으로 3회 실행했다. 시간은 `perf_counter()`로 잰 "
        "PageRank 호출 전체(준비 포함)의 중앙값이며, 그래프 생성·정렬·파일 저장은 제외했다. "
        "워밍업은 하지 않았다. 원시 반복별 결과는 `convergence.json`에 있다.",
        "- 최대 5,000회, L1 변화량 `< tol`일 때만 수렴으로 기록했다. "
        f"{len(runs)}회 모두 수렴했고 순위 합의 최대 1과의 차이는 "
        f"{max(abs(r['rank_sum'] - 1) for r in runs):.2e}였다.", "",
        "## A4. 측정 전 예측", "",
        "beta와 tol을 고정하면 반복 횟수는 노드 수 자체보다 그래프의 혼합 속도에 "
        "좌우될 것으로 예상했다. 한 번 반복할 때 모든 노드와 간선을 처리하므로, "
        "큰 그래프에서는 반복 횟수가 비슷해도 시간이 증가할 것으로 예상했다. "
        "이 예측은 측정을 시작하기 전에 JSON에 저장했다.", "",
        "## A1–A4. beta별 수렴과 크기 비교", "",
        f"tol={tight:.0e}. 두 그래프는 {large / small:g}배 차이이며, "
        f"간선 수는 각각 {groups[small, tight, betas[0]][0]['edges']:,}개와 "
        f"{groups[large, tight, betas[0]][0]['edges']:,}개다.", "",
        f"| beta | {small:,}개 반복 | 시간(s) | {large:,}개 반복 | 시간(s) | 시간 배율 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for beta in betas:
        t_small, t_large = seconds(small, tight, beta), seconds(large, tight, beta)
        lines.append(f"| {beta:g} | {count(small, tight, beta)} | {t_small:.6f} | "
                     f"{count(large, tight, beta)} | {t_large:.6f} | {t_large/t_small:.2f}× |")
    lines += ["",
        "beta가 0.5에서 0.99로 커질 때 반복 횟수는 증가했지만 이 그래프에서는 폭증하지 "
        "않았다. teleport 비율이 줄면 이전 rank의 영향이 더 오래 남는다. 확률 전이 "
        "연산의 L1 오차 수축률에는 beta라는 상한이 있지만, 실제 수렴 속도는 "
        "전이 구조와 초기 rank의 영향도 받으므로 그 최악의 상한과 같지는 않다. "
        "beta=1은 이번 실험에 포함하지 않았으며, 그때의 수렴·유일성을 보장하지 않는다.", "",
        "노드 수가 5배 늘어도 반복 횟수는 0–2회만 증가했다. beta=0.85에서는 "
        f"{count(small, tight, 0.85)}→{count(large, tight, 0.85)}회, 시간은 "
        f"{seconds(large, tight, 0.85)/seconds(small, tight, 0.85):.2f}배였다. "
        "반복당 O(n+E) 작업량과 실행 환경의 변동이 시간에 반영된다. "
        "노드 수가 반복 횟수를 선형적으로 결정한다는 증거는 아니다.", "",
        "## A5. 허용 오차와 추가 자릿수의 비용", "",
        "beta=0.85를 고정했다. 1e-3과 1e-10은 7자리 차이이며, 수치 차이도 "
        "1e-4보다 커서 과제의 허용 오차 간격 조건을 만족한다.", "",
        "| 노드 수 | tol 변화 | 반복 횟수 | 추가 자리 수 | 추가 반복 / 자리 |",
        "|---:|---|---:|---:|---:|",
    ]
    for n in sizes:
        for loose, strict in zip(tols, tols[1:]):
            digits = round(math.log10(loose / strict))
            before, after = count(n, loose, 0.85), count(n, strict, 0.85)
            lines.append(f"| {n:,} | {loose:.0e} → {strict:.0e} | {before} → {after} | "
                         f"{digits} | {(after-before)/digits:.2f} |")
    lines += ["",
        "허용 오차를 엄격하게 할수록 반복 횟수가 증가했다. 자리당 비용은 정수인 "
        "반복 횟수와 그래프의 수축 속도에 따라 달라지며 고정 상수는 아니다. "
        "엄밀히는 이 tol이 연속한 두 rank 벡터의 L1 차이 기준이며, "
        "정확한 고정점에 대한 오차 자체를 뜻하지는 않는다.", "",
        "## A6. 상위 10개 순위의 변화", "",
        "tol=1e-10. 각 행은 높은 rank부터 나열했다.", "",
        "| 노드 수 | beta | 상위 10개 |", "|---:|---|---|",
    ]
    for n in sizes:
        for beta in betas:
            top = groups[n, tight, beta][0]["top10"]
            lines.append(f"| {n:,} | {beta:g} | {', '.join(top)} |")
    lines += ["",
        "두 크기 모두 beta=0.5→0.7에서 `p00000`과 `p00004`의 7·8위가 뒤바뀌었다. "
        "처음 변한 **측정점**은 0.7이며, 정확한 교차 beta는 0.5와 0.7 사이에서 "
        "추가 측정해야 알 수 있다. 측정한 모든 beta에서 상위 10개 구성원은 같았고, "
        "0.7 이후의 순서는 유지되었다. 구성원이 안정적이어도 세부 순서는 beta에 "
        "의존하므로 발표된 순위를 비교할 때 beta·수렴 기준을 함께 확인해야 한다.", "",
        "## 전체 측정 조건", "",
        "시간은 조건당 3회 중앙값. 동일 조건의 반복 횟수는 3회 모두 같았다.", "",
        "| 노드 수 | tol | beta | 반복 | 중앙 시간(s) |",
        "|---:|---|---|---:|---:|",
    ]
    for n in sizes:
        for tol in tols:
            for beta in betas:
                lines.append(f"| {n:,} | {tol:.0e} | {beta:g} | {count(n, tol, beta)} | "
                             f"{seconds(n, tol, beta):.6f} |")
    lines += ["", "## 재현 명령", "", "```bash",
        "cd w05-pagerank",
        "python3 task2_convergence.py --sizes 1200,6000 --betas 0.5,0.7,0.85,0.95,0.99 "
        "--tols 1e-3,1e-6,1e-8,1e-10 --repeats 3 --background \"실행 당시 프로그램 기록\"",
        "python3 summarize_results.py", "```", "",
        "재실행하면 JSON에 결과를 추가한다. 같은 환경에서 다른 프로그램 부하로 "
        "시간은 달라질 수 있다. 새 실험을 별도로 보관하려면 기존 JSON을 다른 이름으로 "
        "보관한 뒤 실행한다.", "",
    ]
    (out / "convergence.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote out/convergence.md from recorded measurements")


if __name__ == "__main__":
    main()
