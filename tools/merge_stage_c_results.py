"""Merge the fixed Stage B v2 first 50 with a new 50--99 result batch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-first50", type=Path, required=True)
    parser.add_argument("--new-tail", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def is_abstention(value: str) -> bool:
    text = value.strip().lower().replace("’", "'")
    return "i don't know" in text or "i do not know" in text


def main() -> int:
    args = parse_args()
    fixed_bytes = args.fixed_first50.read_bytes()
    fixed = json.loads(fixed_bytes)
    tail = json.loads(args.new_tail.read_text(encoding="utf-8"))
    first_results = fixed["results"]
    tail_results = tail["results"]
    if [item["position"] for item in first_results] != list(range(50)):
        raise SystemExit("Fixed baseline must contain exactly positions 0--49")
    if [item["position"] for item in tail_results] != list(range(50, 100)):
        raise SystemExit("New batch must contain exactly positions 50--99")
    results = first_results + tail_results
    count = len(results)
    payload = dict(tail)
    payload["stage_c_merge"] = {
        "fixed_first50": str(args.fixed_first50),
        "fixed_first50_sha256": hashlib.sha256(fixed_bytes).hexdigest(),
        "new_tail": str(args.new_tail),
    }
    payload["proxy_metrics"] = {
        "count": count,
        "abstention_count": sum(is_abstention(x["agent_response"]) for x in results),
        "abstention_rate": round(sum(is_abstention(x["agent_response"]) for x in results) / count, 4),
        "entity_rewrite_count": sum(bool(x.get("web_query_entity")) for x in results),
        "entity_rewrite_rate": round(sum(bool(x.get("web_query_entity")) for x in results) / count, 4),
        "mean_token_f1": round(sum(x["proxy_token_f1"] for x in results) / count, 4),
        "mean_retrieval_seconds": round(sum(x["retrieval_seconds"] for x in results) / count, 4),
        "mean_generation_seconds": round(sum(x["generation_seconds"] for x in results) / count, 4),
    }
    payload["results"] = results
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["proxy_metrics"], ensure_ascii=False))
    print(f"Saved {count} results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
