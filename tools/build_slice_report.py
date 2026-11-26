"""Build an automatic summary and a human-review checklist for slice results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--judgments", type=Path)
    parser.add_argument("--date", default="2026-11-20")
    return parser.parse_args()


def one_line(value: str) -> str:
    return " ".join(value.split())


def main() -> int:
    args = parse_args()
    payload = json.loads(args.results.read_text(encoding="utf-8"))
    results = payload["results"]
    metrics = payload["proxy_metrics"]
    judge_payload = (
        json.loads(args.judgments.read_text(encoding="utf-8"))
        if args.judgments
        else None
    )
    judge_by_position = (
        {item["position"]: item for item in judge_payload["judgments"]}
        if judge_payload
        else {}
    )
    risky = sorted(
        (
            result
            for result in results
            if not result["is_abstention"] and result["proxy_token_f1"] < 0.32
        ),
        key=lambda result: result["proxy_token_f1"],
    )
    strongest = sorted(
        results, key=lambda result: result["proxy_token_f1"], reverse=True
    )[:10]

    report_lines = [
        "# CRAG-MM 50 条联合检索自动报告",
        "",
        f"日期：{args.date}（Asia/Shanghai）",
        "",
        "模式：图片检索 + 网页检索 + VLM 实体改写。生成阶段未调用语义裁判。",
        "",
        "## 代理指标",
        "",
        f"- 样本数：{metrics['count']}",
        f"- 弃答数：{metrics['abstention_count']}（{metrics['abstention_rate']:.0%}）",
        f"- 接受实体改写：{metrics['entity_rewrite_count']}（{metrics['entity_rewrite_rate']:.0%}）",
        f"- 平均 token F1：{metrics['mean_token_f1']:.4f}",
        f"- 平均检索耗时：{metrics['mean_retrieval_seconds']:.4f} 秒",
        f"- 平均生成耗时：{metrics['mean_generation_seconds']:.4f} 秒",
        f"- 检索初始化：{payload['retrieval_init_seconds']:.3f} 秒",
        f"- 模型初始化：{payload['model_load_seconds']:.3f} 秒",
        f"- CUDA 峰值分配：{payload['cuda_peak_allocated_gib']:.3f} GiB",
        "",
        "> Token F1 只是词汇重叠代理指标。低分可能仍语义正确，高分也不能排除事实错误。",
        "",
        "## 高风险优先复核",
        "",
        "非弃答且 token F1 < 0.32：",
        "",
        "| 样本 | F1 | 实体改写 | 问题 | 回答 |",
        "|---:|---:|---|---|---|",
    ]
    for result in risky:
        report_lines.append(
            f"| {result['position']} | {result['proxy_token_f1']:.4f} | "
            f"{one_line(result['web_query_entity']) or '—'} | "
            f"{one_line(result['query'])} | {one_line(result['agent_response'])} |"
        )
    report_lines.extend(
        [
            "",
            "## Token F1 最高的 10 条",
            "",
            "| 样本 | F1 | 问题 | 回答 |",
            "|---:|---:|---|---|",
        ]
    )
    for result in strongest:
        report_lines.append(
            f"| {result['position']} | {result['proxy_token_f1']:.4f} | "
            f"{one_line(result['query'])} | {one_line(result['agent_response'])} |"
        )

    review_lines = [
        "# CRAG-MM 50 条联合检索人工复核清单",
        "",
        f"日期：{args.date}（Asia/Shanghai）",
        "",
        "本清单当前处于搁置状态。恢复人工任务时，优先检查自动报告中的高风险样本，",
        "再逐条按 CRAG-MM 规则勾选：正确 `1`、明确弃答 `0`、错误或误导 `-1`。",
        "",
        f"自动结果文件：`../{args.results.as_posix()}`",
        "",
    ]
    if judge_payload:
        judge_summary = judge_payload["summary"]
        answered = judge_summary["correct"] + judge_summary["wrong"]
        report_lines.extend(
            [
                "## DeepSeek 本地语义裁判",
                "",
                f"- 模型：`{judge_payload['judge_model']}`",
                f"- 正确：{judge_summary['correct']}",
                f"- 弃答：{judge_summary['miss']}",
                f"- 错误：{judge_summary['wrong']}",
                f"- 裁判错误：{judge_summary['judge_errors']}",
                f"- Truthfulness：`{judge_summary['truthfulness_score']:.4f}`",
                f"- 回答覆盖率：`{answered / judge_summary['count']:.1%}`",
                f"- 已回答样本正确率：`{judge_summary['correct'] / answered:.1%}`",
                "",
                "> 这是 DeepSeek 本地对照分，不等同于官方默认 gpt-4o 裁判分数。",
                "",
            ]
        )
    for result in results:
        judgment = judge_by_position.get(result["position"])
        judge_text = (
            f"`{judgment['score']}`（{judgment['source']}）"
            if judgment
            else "未运行"
        )
        review_lines.extend(
            [
                f"## 样本 {result['position']:02d}",
                "",
                f"![样本 {result['position']:02d}](../artifacts/crag_v0.1.2_slice50/{result['image']})",
                "",
                f"问题：{result['query']}",
                "",
                f"参考答案：{result['ground_truth']}",
                "",
                f"模型回答：{result['agent_response']}",
                "",
                f"接受的实体改写：{result['web_query_entity'] or '无'}",
                "",
                f"代理 token F1：`{result['proxy_token_f1']:.4f}`；弃答：`{result['is_abstention']}`",
                "",
                f"DeepSeek 建议标签：{judge_text}",
                "",
                "- [ ] `1` 正确",
                "- [ ] `0` 不知道/信息不足",
                "- [ ] `-1` 错误或无关",
                "",
                "人工备注：",
                "",
            ]
        )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.review.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    args.review.write_text("\n".join(review_lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.report}")
    print(f"Wrote {args.review}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
