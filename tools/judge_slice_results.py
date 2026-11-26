"""Score saved slice results with an OpenAI-compatible LLM judge."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse completed judgments and retry only previous judge errors.",
    )
    return parser.parse_args()


def preliminary_score(response: str, ground_truth: str) -> tuple[int | None, str]:
    normalized = response.strip().lower().replace("’", "'")
    if "i don't know" in normalized or "i do not know" in normalized:
        return 0, "abstention"
    if response.strip().lower() == ground_truth.strip().lower():
        return 1, "exact_match"
    return None, "llm_judge"


def main() -> int:
    args = parse_args()
    load_dotenv()
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(
            f"Environment variable {args.api_key_env} is not set."
        )
    repository_root = Path(__file__).resolve().parents[1]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    from evaluation.llm_judge import LLMJudge

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    judge = LLMJudge(api_key, args.model, args.base_url)
    previous_by_position = {}
    checkpoint_path = args.output.with_suffix(args.output.suffix + ".partial.jsonl")
    if args.resume and args.output.is_file():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        previous_by_position = {item["position"]: item for item in previous.get("judgments", [])}
    elif args.resume and checkpoint_path.is_file():
        for line in checkpoint_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                previous_by_position[item["position"]] = item
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text("", encoding="utf-8")
    judgments = []
    for result in payload["results"]:
        previous_judgment = previous_by_position.get(result["position"])
        reusable = previous_judgment and previous_judgment.get("source") != "judge_error"
        if reusable:
            reusable = all(
                previous_judgment.get(field) == result.get(field)
                for field in ("session_id", "query", "ground_truth", "agent_response")
            )
        if reusable:
            judgments.append(previous_judgment)
            print(
                json.dumps(
                    {
                        "position": result["position"],
                        "score": previous_judgment["score"],
                        "source": "reused",
                    }
                ),
                flush=True,
            )
            continue
        score, source = preliminary_score(
            result["agent_response"], result["ground_truth"]
        )
        api_response = None
        if score is None:
            api_response = judge.evaluate(
                result["query"],
                result["ground_truth"],
                result["agent_response"],
            )
            if api_response is None or api_response["accuracy"] is None:
                score = 0
                source = "judge_error"
            else:
                score = 1 if api_response["accuracy"] else -1
        judgment = {
            "position": result["position"],
            "session_id": result["session_id"],
            "query": result["query"],
            "ground_truth": result["ground_truth"],
            "agent_response": result["agent_response"],
            "score": score,
            "source": source,
            "judge_response": api_response,
        }
        judgments.append(judgment)
        with checkpoint_path.open("a", encoding="utf-8") as checkpoint:
            checkpoint.write(json.dumps(judgment, ensure_ascii=False) + "\n")
            checkpoint.flush()
        print(
            json.dumps(
                {
                    "position": result["position"],
                    "score": score,
                    "source": source,
                }
            ),
            flush=True,
        )

    count = len(judgments)
    summary = {
        "count": count,
        "correct": sum(item["score"] == 1 for item in judgments),
        "miss": sum(item["score"] == 0 for item in judgments),
        "wrong": sum(item["score"] == -1 for item in judgments),
        "judge_errors": sum(item["source"] == "judge_error" for item in judgments),
        "truthfulness_score": round(
            sum(item["score"] for item in judgments) / count, 4
        ),
    }
    output = {
        "judge_model": args.model,
        "judge_base_url": args.base_url,
        "summary": summary,
        "judgments": judgments,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    checkpoint_path.unlink(missing_ok=True)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    print(f"Saved judgments to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
