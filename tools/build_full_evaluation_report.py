"""Build the final full-validation CRAG-MM evaluation report and metrics JSON."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--metrics-json", type=Path, required=True)
    parser.add_argument("--evidence-audit", type=Path)
    parser.add_argument("--parquet", type=Path, nargs="+", required=True)
    return parser.parse_args()


def summarize(items: list[dict]) -> dict:
    count = len(items)
    correct = sum(item["score"] == 1 for item in items)
    miss = sum(item["score"] == 0 for item in items)
    wrong = sum(item["score"] == -1 for item in items)
    answered = correct + wrong
    return {
        "count": count,
        "correct": correct,
        "miss": miss,
        "wrong": wrong,
        "judge_errors": sum(item["source"] == "judge_error" for item in items),
        "truthfulness_score": round((correct - wrong) / count, 4),
        "coverage": round(answered / count, 4),
        "answered_accuracy": round(correct / answered, 4) if answered else 0.0,
    }


def table_row(label: str, stats: dict) -> str:
    return (
        f"| {label} | {stats['count']} | {stats['correct']} | {stats['miss']} | "
        f"{stats['wrong']} | {stats['truthfulness_score']:.4f} | "
        f"{stats['coverage']:.2%} | {stats['answered_accuracy']:.2%} |"
    )


def grouped_table(title: str, groups: dict[str, list[dict]]) -> list[str]:
    lines = [
        f"### {title}",
        "",
        "| 分组 | 数量 | 正确 | 弃答 | 错误 | Truthfulness | 覆盖率 | 已回答准确率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label in sorted(groups, key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value)):
        lines.append(table_row(label, summarize(groups[label])))
    lines.append("")
    return lines


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    results_payload = json.loads(args.results.read_text(encoding="utf-8"))
    judge_payload = json.loads(args.judgments.read_text(encoding="utf-8"))
    results = results_payload["results"]
    judgments = judge_payload["judgments"]
    if len(results) != 1938 or len(judgments) != 1938:
        raise SystemExit("Expected exactly 1,938 results and judgments")
    if [item["position"] for item in results] != list(range(1938)):
        raise SystemExit("Result positions must be exactly 0--1937")
    if [item["position"] for item in judgments] != list(range(1938)):
        raise SystemExit("Judgment positions must be exactly 0--1937")

    metadata = []
    for path in args.parquet:
        metadata.extend(
            pq.read_table(path, columns=["image_url", "turns"]).to_pylist()
        )
    if len(metadata) != 1938:
        raise SystemExit(f"Expected 1,938 parquet rows, found {len(metadata)}")

    enriched = []
    for judgment, row in zip(judgments, metadata):
        turns = row["turns"]
        enriched.append(
            {
                **judgment,
                "image_source": "web" if row.get("image_url") else "egocentric",
                "domain": str(turns["domain"][0]),
                "query_category": str(turns["query_category"][0]),
                "dynamism": str(turns["dynamism"][0]),
                "image_quality": str(turns["image_quality"][0]),
            }
        )

    ranges = {
        "阶段 C：0–99（含定向修复）": enriched[:100],
        "阶段 D 新增：100–199": enriched[100:200],
        "开发集：0–199": enriched[:200],
        "冻结盲测集：200–1937": enriched[200:],
        "完整 validation：0–1937": enriched,
    }
    range_stats = {label: summarize(items) for label, items in ranges.items()}
    group_fields = ["image_source", "domain", "query_category", "dynamism", "image_quality"]
    grouped_stats = {}
    grouped_items = {}
    for field in group_fields:
        groups: dict[str, list[dict]] = defaultdict(list)
        for item in enriched:
            groups[item[field]].append(item)
        grouped_items[field] = dict(groups)
        grouped_stats[field] = {label: summarize(items) for label, items in groups.items()}

    audit_stats = None
    if args.evidence_audit and args.evidence_audit.is_file():
        audit_payload = json.loads(args.evidence_audit.read_text(encoding="utf-8"))
        score_by_position = {item["position"]: item["score"] for item in judgments}
        answered_audits = [
            item for item in audit_payload["audits"]
            if score_by_position[item["position"]] != 0
        ]
        kept = [item for item in answered_audits if item["verdict"] == "KEEP"]
        audit_stats = {
            "correct_answered": sum(score_by_position[item["position"]] == 1 for item in answered_audits),
            "wrong_answered": sum(score_by_position[item["position"]] == -1 for item in answered_audits),
            "correct_kept": sum(score_by_position[item["position"]] == 1 for item in kept),
            "wrong_kept": sum(score_by_position[item["position"]] == -1 for item in kept),
            "kept_count": len(kept),
        }

    metrics = {
        "dataset": results_payload["dataset"],
        "revision": results_payload["revision"],
        "ranges": range_stats,
        "groups": grouped_stats,
        "proxy_metrics": results_payload["proxy_metrics"],
        "evidence_audit_experiment": audit_stats,
        "artifacts": {
            "results": str(args.results),
            "results_sha256": sha256(args.results),
            "judgments": str(args.judgments),
            "judgments_sha256": sha256(args.judgments),
        },
    }
    args.metrics_json.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    overall = range_stats["完整 validation：0–1937"]
    blind = range_stats["冻结盲测集：200–1937"]
    lines = [
        "# CRAG-MM v0.1.2 完整 validation 评测报告",
        "",
        "日期：2026-11-23（Asia/Shanghai）",
        "",
        "## 1. 结论摘要",
        "",
        f"本次完成官方 validation 全部 1,938 条推理和 DeepSeek 语义裁判。全量结果为正确 "
        f"{overall['correct']}、弃答 {overall['miss']}、错误 {overall['wrong']}、裁判错误 "
        f"{overall['judge_errors']}、Truthfulness `{overall['truthfulness_score']:.4f}`。",
        "",
        f"真正冻结的盲测区间 200–1937 共 1,738 条：正确 {blind['correct']}、弃答 "
        f"{blind['miss']}、错误 {blind['wrong']}、Truthfulness `{blind['truthfulness_score']:.4f}`。"
        "该结果显著低于前 100/200 条开发阶段，说明小样本定向优化没有稳定泛化到完整数据集。",
        "",
        "## 2. 方法与数据边界",
        "",
        "- 数据集：`crag-mm-2025/crag-mm-single-turn-public`，revision `v0.1.2`，validation 全部 1,938 条。",
        "- 0–199 为开发区间；其中 0–99 含一轮参考答案辅助的定向修复，不能视为纯盲测。",
        "- 200–1937 在冻结 Llama、检索、提示词和后处理策略后一次性运行，作为主要泛化结果。",
        "- 模型：Llama 3.2 11B Vision Instruct；检索：官方图片索引与 1,681,350 条网页索引。",
        "- 裁判：DeepSeek `deepseek-flash`；这是对照裁判，不是官方 `gpt-4o` 成绩。",
        "- 515 张仅含 URL 的公开 Wikimedia 图片使用官方 1280px 缩略图；其余 egocentric 图片按评测流程使用 960×1280。",
        "",
        "## 3. 主要指标",
        "",
        "| 区间 | 数量 | 正确 | 弃答 | 错误 | Truthfulness | 覆盖率 | 已回答准确率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, stats in range_stats.items():
        lines.append(table_row(label, stats))
    lines.extend(
        [
            "",
            "全量代理指标：平均 token F1 "
            f"`{results_payload['proxy_metrics']['mean_token_f1']:.4f}`，实体改写率 "
            f"`{results_payload['proxy_metrics']['entity_rewrite_rate']:.2%}`，平均检索 "
            f"`{results_payload['proxy_metrics']['mean_retrieval_seconds']:.4f}s`，平均生成 "
            f"`{results_payload['proxy_metrics']['mean_generation_seconds']:.4f}s`。",
            "",
            "## 4. 分组结果",
            "",
            "以下分类名称以官方 parquet 中的整数编码呈现；不推测未随 parquet 发布的标签名称。",
            "",
        ]
    )
    titles = {
        "image_source": "图像来源",
        "domain": "领域编码",
        "query_category": "问题类别编码",
        "dynamism": "动态性编码",
        "image_quality": "图像质量编码",
    }
    for field in group_fields:
        lines.extend(grouped_table(titles[field], grouped_items[field]))

    lines.extend(
        [
            "## 5. 证据审计消融实验",
            "",
        ]
    )
    if audit_stats:
        kept_precision = (
            audit_stats["correct_kept"] / audit_stats["kept_count"]
            if audit_stats["kept_count"] else 0
        )
        lines.extend(
            [
                "在开发区间 100–199 上，DeepSeek 只读取问题、识别实体、检索证据和候选回答，"
                "不读取参考答案，执行严格证据审计。",
                "",
                f"原已回答样本包含正确 {audit_stats['correct_answered']}、错误 {audit_stats['wrong_answered']}；"
                f"审计仅保留 {audit_stats['kept_count']} 条，其中正确 {audit_stats['correct_kept']}、错误 "
                f"{audit_stats['wrong_kept']}，保留答案精度 `{kept_precision:.2%}`。",
                "",
                "该审计能显著降低错误，但正确答案保留率过低，因此只作为高精度安全模式消融，未进入全量主线。",
                "",
            ]
        )
    else:
        lines.extend(["未提供证据审计产物。", ""])

    lines.extend(
        [
            "## 6. 失败结论与项目价值",
            "",
            "- 当前系统在小样本上可通过定向修复达到较好 Truthfulness，但在 1,738 条冻结盲测上接近零净得分，"
            "说明主要瓶颈是图像实体解析与检索证据串线，而不是简单的回答格式问题。",
            "- 全量结果不应再通过逐条参考答案修补来提高主指标；后续改进应更换或增强视觉实体模型、OCR、"
            "跨裁剪一致性和证据蕴含验证，并在新的留出集上验证。",
            "- 本项目的含金量来自完整数据覆盖、开发/盲测隔离、可断点复现、完整失败分布和诚实报告，"
            "而不是只展示经过人工修复的前 100 条高分。",
            "",
            "## 7. 最终产物",
            "",
            f"- 完整结果：`{args.results.as_posix()}`",
            f"- DeepSeek 裁判：`{args.judgments.as_posix()}`",
            f"- 指标 JSON：`{args.metrics_json.as_posix()}`",
            f"- 结果 SHA-256：`{metrics['artifacts']['results_sha256']}`",
            f"- 裁判 SHA-256：`{metrics['artifacts']['judgments_sha256']}`",
            "",
        ]
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(overall, ensure_ascii=False))
    print(json.dumps(blind, ensure_ascii=False))
    print(f"Saved report to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
