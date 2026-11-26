"""Audit saved answers against retrieval evidence without exposing ground truth."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import time

from dotenv import load_dotenv
from openai import OpenAI


SYSTEM_PROMPT = """You are a strict evidence auditor for a multimodal retrieval system.
You do not know the reference answer. Decide whether the proposed answer is fully supported by
the supplied recognized image entity and retrieved evidence. Reject answers that guess the image
identity, use evidence about a different entity, reverse a comparison or relationship, add an
unsupported number, answer a different question, or explicitly admit that the evidence does not
state the answer. When the question depends on words such as this/these/it and no reliable entity
was resolved, reject unless the supplied evidence unambiguously identifies the subject. Precision
is more important than coverage. End with exactly VERDICT: KEEP or VERDICT: ABSTAIN."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--start-position", type=int, default=0)
    parser.add_argument("--end-position", type=int)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def is_abstention(value: str) -> bool:
    text = value.strip().lower().replace("’", "'")
    return "i don't know" in text or "i do not know" in text


def parse_verdict(text: str) -> str | None:
    matches = re.findall(r"VERDICT:\s*(KEEP|ABSTAIN)", text.upper())
    return matches[-1] if matches else None


def main() -> int:
    args = parse_args()
    load_dotenv()
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Environment variable {args.api_key_env} is not set")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    end_position = args.end_position if args.end_position is not None else 10**9
    selected = [
        item for item in payload["results"]
        if args.start_position <= item["position"] <= end_position
    ]
    previous: dict[int, dict] = {}
    if args.resume and args.output.is_file():
        old = json.loads(args.output.read_text(encoding="utf-8"))
        previous = {item["position"]: item for item in old.get("audits", [])}
    client = OpenAI(api_key=api_key, base_url=args.base_url)
    audits = []
    for result in selected:
        position = result["position"]
        old = previous.get(position)
        if old and all(
            old.get(field) == result.get(field)
            for field in ("session_id", "query", "agent_response")
        ):
            audits.append(old)
            continue
        if is_abstention(result["agent_response"]):
            audit = {
                "position": position,
                "session_id": result["session_id"],
                "query": result["query"],
                "agent_response": result["agent_response"],
                "verdict": "ABSTAIN",
                "source": "already_abstained",
                "audit_response": None,
            }
        else:
            evidence = result.get("rag_context", "")[:9000]
            user_prompt = f"""Question: {result['query']}
Resolved image entity: {result.get('web_query_entity') or '[NONE]'}
Unverified image candidate: {result.get('web_query_entity_candidate') or '[NONE]'}
Search query: {result.get('web_search_query') or '[NONE]'}
Proposed answer: {result['agent_response']}

Retrieved evidence:
{evidence}

Audit the proposed answer. Do not infer missing facts from general plausibility."""
            response_text = ""
            verdict = None
            for attempt in range(3):
                try:
                    completion = client.chat.completions.create(
                        model=args.model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.0,
                        max_tokens=160,
                        extra_body={"thinking": {"type": "disabled"}},
                    )
                    response_text = completion.choices[0].message.content or ""
                    verdict = parse_verdict(response_text)
                    if verdict:
                        break
                except Exception as error:
                    response_text = f"{type(error).__name__}: {error}"
                time.sleep(2**attempt)
            audit = {
                "position": position,
                "session_id": result["session_id"],
                "query": result["query"],
                "agent_response": result["agent_response"],
                "verdict": verdict or "AUDIT_ERROR",
                "source": "deepseek_evidence_audit",
                "audit_response": response_text,
            }
        audits.append(audit)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps({"model": args.model, "audits": audits}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps({"position": position, "verdict": audit["verdict"]}), flush=True)
    summary = {
        "count": len(audits),
        "keep": sum(item["verdict"] == "KEEP" for item in audits),
        "abstain": sum(item["verdict"] == "ABSTAIN" for item in audits),
        "audit_errors": sum(item["verdict"] == "AUDIT_ERROR" for item in audits),
    }
    args.output.write_text(
        json.dumps({"model": args.model, "summary": summary, "audits": audits}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
