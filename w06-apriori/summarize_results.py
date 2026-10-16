#!/usr/bin/env python3
"""Regenerate the Week 06 measurement table and plot from raw JSON.

Only plotting requires matplotlib (already listed in ../requirements.txt).
python summarize_results.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
MIB = 1024 ** 2


def main():
    data = json.loads((OUT / "explosion.json").read_text(encoding="utf-8"))
    fixed = [row for row in data["runs"]
             if row["dataset"] == {"seed": 246, "items": 2000,
                                    "baskets": 20000, "avg": 20}
             and row["status"] == "completed"]
    # If the user repeats experiments, use the most recent run at each support.
    fixed = sorted({row["support"]: row for row in fixed}.values(),
                   key=lambda row: -row["support"])
    scaled = [row for row in data["runs"] if row["dataset"]["items"] != 2000]
    machine = data["machine"]
    lines = ["# Week 6 · Support 감소 실험", "",
             "## 측정 환경과 범위", "",
             f"- CPU: {machine['processor']} ({machine['logical_cpus']} logical CPUs).",
             f"- RAM: {machine['ram_bytes'] / 1024 ** 3:.2f} GiB; "
             f"마지막 batch 시작 시 여유 {machine['available_ram_bytes_at_start'] / 1024 ** 3:.2f} GiB.",
             f"- OS / Python: {machine['platform']} / {machine['python']}.",
             "- 실행일: 2026-10-17 KST. CIM으로 ChatGPT, Notion, Claude, Codex, "
             "Windows Defender, Explorer, Steam WebHelper 실행을 확인했다. 다른 Codex "
             "검증과 일부 겹쳤으므로 시간은 이 환경에서의 관측값이다.",
             "- seed=246, 기본 20,000 baskets / 2,000 items / AVG=20. "
             "AVG는 생성기 파라미터로 실제 set 크기는 중복 제거로 더 작을 수 있다.",
             "- 수정하지 않은 `PlainApriori`를 실행했다. 시간에는 tracemalloc 및 "
             "64개 바구니마다의 제한 확인이 포함되어 bench.txt 시간과 직접 비교하지 않는다.",
             "- peak bytes는 입력 생성 후 추적한 Python 할당량이며 결과 딕셔너리도 포함한다. "
             "기존 입력·인터프리터·native 메모리·tracemalloc 자체 비용을 포함한 RSS가 아니다.",
             "- peak counters는 기준 구현의 pass-two 카운터 수이다. 반환 결과를 만드는 동안 "
             "카운터와 결과가 공존하는 메모리는 peak bytes에 반영되지만 counter 지표에는 추가되지 않는다.",
             "", "## 기본 데이터: 같은 데이터에서 support만 변경", "",
             "| Support | Frequent items | Peak counters | Frequent pairs | Counters / answers | Peak MiB | Seconds |",
             "|---:|---:|---:|---:|---:|---:|---:|"]
    for row in fixed:
        lines.append(f"| {row['support']} | {row['frequent_singletons']:,} | "
                     f"{row['peak_counters']:,} | {row['frequent_pairs']:,} | "
                     f"{row['peak_counters'] / row['frequent_pairs']:.2f} | "
                     f"{row['peak_bytes'] / MIB:.2f} | {row['seconds']:.3f} |")
    lines += ["", "![Measured support curve](explosion.png)", "",
              "### A4 · counter 증가는 선형이 아니며, 이 데이터에서는 결국 포화된다", "",
              "| Support change | Counter multiplier | Answer multiplier |",
              "|---|---:|---:|"]
    for previous, row in zip(fixed, fixed[1:]):
        lines.append(f"| {previous['support']} → {row['support']} | "
                     f"{row['peak_counters'] / previous['peak_counters']:.3f}× | "
                     f"{row['frequent_pairs'] / previous['frequent_pairs']:.3f}× |")
    lines += ["", "400→200→100→50의 halving에서 counter는 약 5.54×, 4.67×, "
              "3.00×로 늘었다. 그러나 support 25에서 모든 2,000개 항목이 살아남아 "
              "관측된 쌍 893,456개를 이미 전부 센다. 25→1에서는 counter가 더 증가하지 않는다. "
              "이 고정 데이터에 무한한 explosion이나 OOM이 있다고 주장할 수 없다.", "",
              "### A5 · 답과 counter는 다르게 증가한다", "",
              "support 50에서는 820,259개 counter로 답 6,397개를 찾는다(128.23배). "
              "400→200에서는 counter 5.54배, 답 3.12배로 낭비가 커진다. 반대로 25→1에서는 "
              "counter가 같아도 답은 17,045→893,456개(52.42배)로 늘어나고 support 1에서 "
              "모든 관측 쌍이 답이 된다. 따라서 답이 항상 더 천천히 자란다는 결론은 성립하지 않는다. "
              "중간 support에서 적은 답을 얻기 위해 수십~수백 배의 후보를 보관하는 것이 문제다.", "",
              "## A2 · 실제로 중단한 확장 실험", "",
              "기본 데이터는 support 1까지 완료됐고 OS의 물리 메모리를 소진하지 않았다. "
              "support는 양의 정수라 더 낮출 수 없어, 별도 scale 실험을 했다. "
              "같은 seed/생성기에서 60,000 baskets / 20,000 items / AVG=30으로 늘린 뒤 "
              "400부터 차례로 낮췄다. 두 크기의 행을 하나의 support 곡선으로 섞지 않았다.", "",
              "실행 전 중단 예산을 새 Python 할당량 256 MiB 또는 실행 60초로 설정했다. "
              "기존 앱의 RAM 사용을 고려해 선택한 작업 예산이며 OS 메모리의 절대 한계는 아니다. "
              "검사는 바구니 사이에서만 하므로 dict resize와 최종 출력 생성 중에는 초과할 수 있다. "
              "실제로 기본 support 1도 최종 출력 생성으로 311.9 MiB가 되어 예산보다 컸지만 완료됐다.", "",
              "| Support | Status | Peak counters so far | Frequent pairs | Peak MiB | Seconds |",
              "|---:|---|---:|---:|---:|---:|"]
    for row in scaled:
        answer = f"{row['frequent_pairs']:,}" if row['frequent_pairs'] is not None else "미완료"
        lines.append(f"| {row['support']} | {row['status']} | {row['peak_counters']:,} | "
                     f"{answer} | {row['peak_bytes'] / MIB:.2f} | {row['seconds']:.3f} |")
    stopped = next(row for row in scaled if row['status'] != "completed")
    lines += ["", f"확장 데이터에서 처음 중단된 support는 **{stopped['support']}**이다. "
              f"pass {stopped['stopped_in_pass']}의 {stopped['baskets_processed_in_pass']:,}개 "
              f"바구니 처리 후 counter {stopped['peak_counters']:,}개, "
              f"추적 peak {stopped['peak_bytes'] / MIB:.2f} MiB, {stopped['seconds']:.2f}초에서 "
              "메모리 작업 예산을 초과해 중단했다. dict의 크기 확장 때문에 256 MiB보다 "
              "큰 값이 관측됐다. 시간 예산보다 메모리 예산이 먼저 걸렸으며, "
              "MemoryError나 시스템 전체 OOM은 발생하지 않았다. 미완료 행의 답 개수는 추정하지 않았다.", "",
              "## 재현", "", "```bash",
              "python task2_explosion.py --supports 400,200,100,50,25,12,6,3,1 --max-mib 256 --max-seconds 60 --background \"list your current apps\"",
              "python task2_explosion.py --items 20000 --baskets 60000 --avg 30 --supports 400,200,100,50,25,12,6,3,1 --max-mib 256 --max-seconds 60 --background \"list your current apps\"",
              "python summarize_results.py", "```", "",
              "새 실행은 explosion.json에 batch ID와 함께 추가되며, 각 행이 끝날 때 저장된다. "
              "재실행 시 중단 지점·시간·할당량은 달라질 수 있다. 원시 데이터는 explosion.json에 있다.", ""]
    (OUT / "explosion.md").write_text("\n".join(lines), encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import ScalarFormatter
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    supports = [row["support"] for row in fixed]
    axes[0].plot(supports, [row["peak_counters"] for row in fixed], "o-",
                 color="#2563eb", label="Peak pair counters")
    axes[0].plot(supports, [row["frequent_pairs"] for row in fixed], "s-",
                 color="#db4f29", label="Frequent pairs (answers)")
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Count (log scale)")
    axes[0].set_title("Candidates plateau; answers catch up")
    axes[0].legend(loc="lower right")
    axes[1].plot(supports, [row["peak_bytes"] / MIB for row in fixed], "o-",
                 color="#7c3aed", label="Traced peak incl. output")
    axes[1].axhline(256, color="#64748b", linestyle="--", label="Sampled budget: 256 MiB")
    axes[1].set_ylabel("Incremental Python allocation (MiB)")
    axes[1].set_title("Output construction also costs memory")
    axes[1].legend(loc="upper left")
    for ax in axes:
        ax.set_xscale("log", base=2)
        ax.set_xticks(supports)
        ax.xaxis.set_major_formatter(ScalarFormatter())
        ax.invert_xaxis()
        ax.set_xlabel("Support (decreasing →)")
        ax.grid(alpha=0.2)
    fig.suptitle("Week 06 · Fixed seed 246 · 20,000 baskets · 2,000 items", fontsize=13)
    fig.savefig(OUT / "explosion.png", dpi=180)
    fig.savefig(OUT / "explosion.svg")
    svg_path = OUT / "explosion.svg"
    svg_path.write_text("\n".join(line.rstrip() for line in
                        svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
                        encoding="utf-8")
    plt.close(fig)
    print("Wrote out/explosion.md, out/explosion.png and out/explosion.svg")


if __name__ == "__main__":
    main()
