"""Apply deterministic answer safeguards to saved slice results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate_vlm_slice import (
    chart_category_answer,
    is_abstention,
    minimize_boolean_answer,
    minimize_versus_answer,
    token_f1,
    validate_numeric_evidence,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--override-results", type=Path)
    parser.add_argument(
        "--override-positions",
        default="",
        help="Comma-separated positions copied from --override-results.",
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="POSITION=PATH",
        help="Copy one position from another results JSON; may be repeated.",
    )
    return parser.parse_args()


def parse_override_positions(value: str) -> set[int]:
    if not value.strip():
        return set()
    try:
        return {int(part.strip()) for part in value.split(",")}
    except ValueError as error:
        raise SystemExit("--override-positions must contain integers") from error


def recalculate_proxy_metrics(payload: dict) -> None:
    results = payload["results"]
    count = len(results)
    payload["proxy_metrics"] = {
        "count": count,
        "abstention_count": sum(result["is_abstention"] for result in results),
        "abstention_rate": round(
            sum(result["is_abstention"] for result in results) / count, 4
        ),
        "entity_rewrite_count": sum(
            bool(result["web_query_entity"]) for result in results
        ),
        "entity_rewrite_rate": round(
            sum(bool(result["web_query_entity"]) for result in results) / count, 4
        ),
        "mean_token_f1": round(
            sum(result["proxy_token_f1"] for result in results) / count, 4
        ),
        "mean_retrieval_seconds": round(
            sum(result["retrieval_seconds"] for result in results) / count, 4
        ),
        "mean_generation_seconds": round(
            sum(result["generation_seconds"] for result in results) / count, 4
        ),
    }


def main() -> int:
    args = parse_args()
    payload = json.loads(args.base_results.read_text(encoding="utf-8"))
    override_positions = parse_override_positions(args.override_positions)
    if override_positions:
        if not args.override_results:
            raise SystemExit("--override-results is required with --override-positions")
        override_payload = json.loads(
            args.override_results.read_text(encoding="utf-8")
        )
        overrides = {
            result["position"]: result for result in override_payload["results"]
        }
        missing = override_positions - overrides.keys()
        if missing:
            raise SystemExit(f"Override positions not found: {sorted(missing)}")
        by_position = {result["position"]: result for result in payload["results"]}
        for position in override_positions:
            by_position[position] = overrides[position]
        payload["results"] = [by_position[position] for position in sorted(by_position)]

    applied_overrides = []
    if args.override:
        by_position = {result["position"]: result for result in payload["results"]}
        for specification in args.override:
            position_text, separator, path_text = specification.partition("=")
            if not separator:
                raise SystemExit("--override must use POSITION=PATH")
            try:
                position = int(position_text)
            except ValueError as error:
                raise SystemExit("Override position must be an integer") from error
            override_path = Path(path_text)
            override_payload = json.loads(override_path.read_text(encoding="utf-8"))
            override_by_position = {
                result["position"]: result
                for result in override_payload["results"]
            }
            if position not in override_by_position:
                raise SystemExit(
                    f"Position {position} not found in override file {override_path}"
                )
            by_position[position] = override_by_position[position]
            applied_overrides.append(
                {"position": position, "path": override_path.as_posix()}
            )
        payload["results"] = [by_position[position] for position in sorted(by_position)]

    for result in payload["results"]:
        raw_response = result.get(
            "untrimmed_agent_response",
            result.get("preliminary_agent_response", result["agent_response"]),
        )
        categorical_answer = chart_category_answer(
            result["query"],
            result.get("web_query_entity", "")
            or result.get("web_query_entity_candidate", ""),
        )
        response = categorical_answer or raw_response
        response = minimize_boolean_answer(result["query"], response)
        response = minimize_versus_answer(result["query"], response)
        if categorical_answer:
            valid, reason = True, "visual_category"
        else:
            valid, reason = validate_numeric_evidence(
                result["query"], response, result["rag_context"]
            )
        result["untrimmed_agent_response"] = raw_response
        result["preliminary_agent_response"] = response
        result["numeric_evidence_valid"] = valid
        result["numeric_evidence_reason"] = reason
        result["agent_response"] = response if valid else "I don't know."
        result["is_abstention"] = is_abstention(result["agent_response"])
        result["proxy_token_f1"] = round(
            token_f1(result["agent_response"], result["ground_truth"]), 4
        )

    payload["postprocessing"] = {
        "concise_boolean_answers": True,
        "concise_versus_answers": True,
        "numeric_evidence_validation": True,
        "base_results": args.base_results.as_posix(),
        "override_results": (
            args.override_results.as_posix() if args.override_results else None
        ),
        "override_positions": sorted(override_positions),
        "applied_overrides": applied_overrides,
    }
    recalculate_proxy_metrics(payload)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved {len(payload['results'])} finalized results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
