"""Strongly validate and merge a frozen result prefix with its next contiguous batch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--tail", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def is_abstention(value: str) -> bool:
    text = value.strip().lower().replace("’", "'")
    return "i don't know" in text or "i do not know" in text


def require_positions(results: list[dict], expected: range, label: str) -> None:
    positions = [item.get("position") for item in results]
    if positions != list(expected):
        raise SystemExit(
            f"{label} positions must be exactly {expected.start}--{expected.stop - 1}"
        )


def main() -> int:
    args = parse_args()
    baseline_bytes = args.baseline.read_bytes()
    baseline = json.loads(baseline_bytes)
    tail_bytes = args.tail.read_bytes()
    tail = json.loads(tail_bytes)
    baseline_results = baseline["results"]
    tail_results = tail["results"]
    if not baseline_results or not tail_results:
        raise SystemExit("Baseline and tail must both contain results")
    prefix_count = len(baseline_results)
    require_positions(baseline_results, range(prefix_count), "Baseline")
    require_positions(
        tail_results,
        range(prefix_count, prefix_count + len(tail_results)),
        "Tail",
    )
    for field in ("dataset", "revision", "split"):
        if baseline.get(field) != tail.get(field):
            raise SystemExit(f"Baseline and tail disagree on {field}")
    results = baseline_results + tail_results
    count = len(results)
    payload = dict(tail)
    payload["stage_merge"] = {
        "baseline": str(args.baseline),
        "baseline_count": prefix_count,
        "baseline_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
        "tail": str(args.tail),
        "tail_count": len(tail_results),
        "tail_sha256": hashlib.sha256(tail_bytes).hexdigest(),
    }
    abstentions = sum(is_abstention(item["agent_response"]) for item in results)
    entity_rewrites = sum(bool(item.get("web_query_entity")) for item in results)
    payload["proxy_metrics"] = {
        "count": count,
        "abstention_count": abstentions,
        "abstention_rate": round(abstentions / count, 4),
        "entity_rewrite_count": entity_rewrites,
        "entity_rewrite_rate": round(entity_rewrites / count, 4),
        "mean_token_f1": round(sum(item["proxy_token_f1"] for item in results) / count, 4),
        "mean_retrieval_seconds": round(sum(item["retrieval_seconds"] for item in results) / count, 4),
        "mean_generation_seconds": round(sum(item["generation_seconds"] for item in results) / count, 4),
    }
    payload["results"] = results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["proxy_metrics"], ensure_ascii=False))
    print(f"Saved {count} results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
