"""Build leakage-audited P5 SFT, preference, and hard-negative datasets."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

repository_root = Path(__file__).resolve().parents[1]
if str(repository_root) not in sys.path:
    sys.path.insert(0, str(repository_root))

from tools.evaluate_vlm_slice import classify_question_route


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "how", "in", "is", "it", "of", "on", "or", "that", "the", "their",
    "these", "this", "those", "to", "was", "were", "what", "when", "where",
    "which", "who", "with",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-results", type=Path, required=True)
    parser.add_argument("--full-judgments", type=Path, required=True)
    parser.add_argument("--structured-results", type=Path, required=True)
    parser.add_argument("--structured-judgments", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-position", type=int, default=399)
    parser.add_argument("--external-heldout-start", type=int, default=400)
    parser.add_argument("--external-heldout-end", type=int, default=599)
    return parser.parse_args()


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def content_tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", text.casefold())
        if len(token) > 1 and token not in STOPWORDS
    }


def split_for_session(session_id: str) -> str:
    bucket = int(hashlib.sha256(session_id.encode()).hexdigest()[:8], 16) % 10
    return "train" if bucket < 8 else "dev"


def image_ref(position: int, image_name: str) -> str:
    if position < 50:
        folder = "crag_v0.1.2_slice50"
    elif position < 100:
        folder = "crag_v0.1.2_slice100"
    elif position < 200:
        folder = "crag_v0.1.2_slice200"
    else:
        folder = "crag_v0.1.2_full_blind_cloud"
    return f"artifacts/{folder}/{image_name}"


def extract_documents(rag_context: str, cap: int = 2800) -> list[str]:
    documents = re.findall(
        r"<DOC>.*?</DOC>", rag_context or "", re.IGNORECASE | re.DOTALL
    )
    cleaned = []
    for document in documents:
        text = re.sub(r"</?DOC>", "", document, flags=re.IGNORECASE).strip()
        text = re.sub(r"\s+", " ", text)
        if text and text not in cleaned:
            cleaned.append(text[:cap])
    return cleaned[:8]


def select_evidence(documents: list[str], answer: str) -> tuple[list[int], list[float]]:
    answer_tokens = content_tokens(answer)
    answer_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", answer))
    scores = []
    for document in documents:
        document_tokens = content_tokens(document)
        overlap = (
            len(answer_tokens & document_tokens) / len(answer_tokens)
            if answer_tokens else 0.0
        )
        if answer_numbers:
            document_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", document))
            overlap += 0.25 * len(answer_numbers & document_numbers) / len(answer_numbers)
        scores.append(round(overlap, 4))
    selected = [
        index for index, score in sorted(
            enumerate(scores), key=lambda item: item[1], reverse=True
        )[:3]
        if score >= 0.18
    ]
    return selected, scores


def image_candidates(result: dict[str, Any]) -> list[str]:
    names = []
    pattern = re.compile(r"Candidate\s+\d+:\s+([^\n(]+)", re.IGNORECASE)
    for detail in result.get("web_query_entity_details") or []:
        for name in pattern.findall(detail.get("image_context") or ""):
            name = name.strip()
            if name and name not in names:
                names.append(name)
    return names[:8]


def reliable_entity(result: dict[str, Any], score: int) -> tuple[str, str]:
    entity = (result.get("web_query_entity") or "").strip()
    if not entity:
        return "", "none"
    if result.get("entity_consistency_valid"):
        return entity, "entity_consistency"
    if score == 1:
        return entity, "correct_answer_weak_label"
    return "", "untrusted"


def infer_error_type(result: dict[str, Any], route: str, entity: str) -> str:
    response = result["agent_response"].casefold()
    numeric_reason = result.get("numeric_evidence_reason") or ""
    if str(numeric_reason).startswith("unsupported_number"):
        return "unsupported_number"
    if any(phrase in response for phrase in ("not explicitly", "likely", "it is possible", "difficult to determine")):
        return "unsupported_or_meta_answer"
    if not entity and re.search(r"\b(this|these|it|those)\b", result["query"], re.IGNORECASE):
        return "unresolved_entity_guess"
    if route == "comparison":
        return "comparison_or_direction_error"
    if result.get("web_query_entity") and not result.get("entity_consistency_valid", True):
        return "entity_inconsistency"
    return "wrong_answer_or_evidence_mismatch"


def user_message(image: str, prompt: str) -> list[dict[str, Any]]:
    return [
        {"type": "image", "path": image},
        {"type": "text", "text": prompt},
    ]


def make_sft_record(
    *, record_id: str, split: str, task: str, position: int, session_id: str,
    image: str, prompt: str, target: str, label_source: str, metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": record_id,
        "split": split,
        "task": task,
        "position": position,
        "session_id": session_id,
        "image": image,
        "messages": [
            {"role": "user", "content": user_message(image, prompt)},
            {"role": "assistant", "content": [{"type": "text", "text": target}]},
        ],
        "label_source": label_source,
        "metadata": metadata,
    }


def deduplicate(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen = set()
    unique = []
    for record in records:
        key = hashlib.sha256(
            json.dumps(
                {
                    "task": record.get("task"),
                    "image": record.get("image"),
                    "messages": record.get("messages"),
                    "prompt": record.get("prompt"),
                    "chosen": record.get("chosen"),
                    "preferred": record.get("preferred"),
                    "rejected": record.get("rejected"),
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode()
        ).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique, len(records) - len(unique)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = parse_args()
    full_results = json.loads(args.full_results.read_text(encoding="utf-8"))["results"]
    full_judgments = json.loads(args.full_judgments.read_text(encoding="utf-8"))["judgments"]
    structured_results = json.loads(args.structured_results.read_text(encoding="utf-8"))["results"]
    structured_judgments = json.loads(args.structured_judgments.read_text(encoding="utf-8"))["judgments"]
    result_by_position = {item["position"]: item for item in full_results}
    judgment_by_position = {item["position"]: item for item in full_judgments}
    result_by_position.update({item["position"]: item for item in structured_results})
    judgment_by_position.update({item["position"]: item for item in structured_judgments})

    sft: list[dict[str, Any]] = []
    preferences: list[dict[str, Any]] = []
    hard_negatives: list[dict[str, Any]] = []
    source_counts = Counter()
    for position in range(args.max_position + 1):
        result = result_by_position[position]
        judgment = judgment_by_position[position]
        score = judgment["score"]
        session_id = result["session_id"]
        split = split_for_session(session_id)
        image = image_ref(position, result["image"])
        query = result["query"]
        ground_truth = result["ground_truth"].strip()
        route = result.get("question_route") or classify_question_route(query)
        visible_text = (result.get("visible_text") or "").strip()
        entity, entity_source = reliable_entity(result, score)
        documents = extract_documents(result.get("rag_context") or "")
        selected_docs, evidence_scores = select_evidence(documents, ground_truth)
        direct_route = route in {"identity", "visual", "ocr", "chart"}
        answer_supported = direct_route or bool(selected_docs)
        answer_target = ground_truth if answer_supported else "I don't know."
        base_metadata = {
            "route": route,
            "judge_score": score,
            "entity_source": entity_source,
            "answer_supported": answer_supported,
            "selected_evidence": selected_docs,
        }

        sft.append(
            make_sft_record(
                record_id=f"route:{position}", split=split, task="route",
                position=position, session_id=session_id, image=image,
                prompt=(
                    "Classify the question into exactly one route: identity, visual, "
                    "ocr, lookup, comparison, or chart. Return only the route.\n"
                    f"Question: {query}"
                ),
                target=route, label_source="deterministic_router", metadata=base_metadata,
            )
        )
        source_counts["route"] += 1

        if entity:
            candidates = image_candidates(result)
            sft.append(
                make_sft_record(
                    record_id=f"entity:{position}", split=split, task="entity",
                    position=position, session_id=session_id, image=image,
                    prompt=(
                        "Identify the exact target entity referenced by the question. "
                        "Return only <entity>NAME</entity>. Candidate hints may be wrong.\n"
                        f"Question: {query}\nCandidates: {json.dumps(candidates, ensure_ascii=False)}"
                    ),
                    target=f"<entity>{entity}</entity>", label_source=entity_source,
                    metadata=base_metadata,
                )
            )
            source_counts["entity"] += 1

        if visible_text:
            sft.append(
                make_sft_record(
                    record_id=f"ocr:{position}", split=split, task="ocr",
                    position=position, session_id=session_id, image=image,
                    prompt=(
                        "Transcribe only useful visible text relevant to the question, "
                        "including brand, model, title, number, unit, or chart heading.\n"
                        f"Question: {query}"
                    ),
                    target=visible_text, label_source="llama_weak_ocr",
                    metadata={**base_metadata, "weak_label": True},
                )
            )
            source_counts["ocr"] += 1

        web_query = (result.get("web_search_query") or "").strip()
        if entity and web_query and normalize(web_query) != normalize(query):
            sft.append(
                make_sft_record(
                    record_id=f"rewrite:{position}", split=split, task="query_rewrite",
                    position=position, session_id=session_id, image=image,
                    prompt=(
                        "Write one concise web search query grounded in the identified "
                        "image entity. Do not answer the question.\n"
                        f"Question: {query}\nEntity: {entity}\nVisible text: {visible_text or 'NONE'}"
                    ),
                    target=web_query, label_source=entity_source, metadata=base_metadata,
                )
            )
            source_counts["query_rewrite"] += 1

        if len(documents) >= 2 and selected_docs:
            candidate_text = "\n".join(
                f"[{index}] {document}" for index, document in enumerate(documents)
            )
            sft.append(
                make_sft_record(
                    record_id=f"evidence:{position}", split=split, task="evidence_selection",
                    position=position, session_id=session_id, image=image,
                    prompt=(
                        "Select the document indices that contain evidence needed to answer "
                        "the question about the identified entity. Return a JSON list only.\n"
                        f"Question: {query}\nEntity: {entity or 'UNRESOLVED'}\n{candidate_text}"
                    ),
                    target=json.dumps(selected_docs), label_source="answer_overlap_weak_label",
                    metadata={**base_metadata, "evidence_scores": evidence_scores},
                )
            )
            source_counts["evidence_selection"] += 1

        answer_evidence = [documents[index] for index in selected_docs]
        answer_prompt = (
            "Answer the question using the image identity and supplied evidence. Keep the "
            "answer factual and concise. If the identity or evidence is insufficient, answer "
            "exactly: I don't know.\n"
            f"Question: {query}\nRoute: {route}\nEntity: {entity or 'UNRESOLVED'}\n"
            f"Visible text: {visible_text or 'NONE'}\nEvidence: "
            f"{json.dumps(answer_evidence, ensure_ascii=False)}"
        )
        sft.append(
            make_sft_record(
                record_id=f"answer:{position}", split=split, task="answer_or_abstain",
                position=position, session_id=session_id, image=image,
                prompt=answer_prompt, target=answer_target,
                label_source=("ground_truth" if answer_supported else "evidence_gated_refusal"),
                metadata=base_metadata,
            )
        )
        source_counts["answer_or_abstain"] += 1

        response = result["agent_response"].strip()
        if score == -1 and normalize(response) != normalize(answer_target):
            error_type = infer_error_type(result, route, entity)
            hard_negatives.append(
                {
                    "id": f"negative:{position}", "split": split, "task": "hard_negative",
                    "position": position, "session_id": session_id, "image": image,
                    "query": query, "route": route, "entity": entity or "UNRESOLVED",
                    "evidence": answer_evidence, "rejected": response,
                    "preferred": answer_target, "error_type": error_type,
                    "judge_score": score,
                }
            )
            preferences.append(
                {
                    "id": f"preference-wrong:{position}", "split": split,
                    "task": "answer_preference", "position": position,
                    "session_id": session_id, "image": image,
                    "prompt": answer_prompt, "chosen": answer_target,
                    "rejected": response, "preference_source": error_type,
                }
            )
        elif score == 1:
            preferences.append(
                {
                    "id": f"preference-answer:{position}", "split": split,
                    "task": "answer_preference", "position": position,
                    "session_id": session_id, "image": image,
                    "prompt": answer_prompt, "chosen": ground_truth,
                    "rejected": "I don't know.",
                    "preference_source": "correct_answer_vs_over_refusal",
                }
            )
        elif score == 0 and answer_supported:
            preferences.append(
                {
                    "id": f"preference-miss:{position}", "split": split,
                    "task": "answer_preference", "position": position,
                    "session_id": session_id, "image": image,
                    "prompt": answer_prompt, "chosen": ground_truth,
                    "rejected": "I don't know.",
                    "preference_source": "supported_answer_vs_miss",
                }
            )

    sft, sft_duplicates = deduplicate(sft)
    preferences, preference_duplicates = deduplicate(preferences)
    hard_negatives, negative_duplicates = deduplicate(hard_negatives)
    if any(record["position"] > args.max_position for record in sft + preferences + hard_negatives):
        raise SystemExit("Found a record outside the permitted 0--399 development range")
    if any(
        args.external_heldout_start <= record["position"] <= args.external_heldout_end
        for record in sft + preferences + hard_negatives
    ):
        raise SystemExit("External held-out positions leaked into training data")
    serialized = json.dumps(sft + preferences + hard_negatives, ensure_ascii=False)
    if "DEEPSEEK_API_KEY" in serialized or "OPENAI_API_KEY" in serialized:
        raise SystemExit("API-key material found in training records")
    for record in sft:
        if "ground_truth" in record:
            raise SystemExit("Reference answer leaked as an input field")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, records in (
        ("multitask", sft),
        ("preferences", preferences),
        ("hard_negatives", hard_negatives),
    ):
        for split in ("train", "dev"):
            path = args.output_dir / f"{name}_{split}.jsonl"
            subset = [record for record in records if record["split"] == split]
            write_jsonl(path, subset)
            files[path.name] = {
                "count": len(subset),
                "sha256": file_sha256(path),
                "bytes": path.stat().st_size,
            }

    task_counts = Counter(record["task"] for record in sft)
    split_counts = Counter(record["split"] for record in sft)
    error_counts = Counter(record["error_type"] for record in hard_negatives)
    manifest = {
        "name": "crag-mm-p5-training-prep",
        "created_date": "2026-11-24",
        "source_positions": [0, args.max_position],
        "external_heldout_positions": [
            args.external_heldout_start, args.external_heldout_end
        ],
        "split_rule": "sha256(session_id) mod 10; 0-7 train, 8-9 dev",
        "counts": {
            "sft": len(sft), "preferences": len(preferences),
            "hard_negatives": len(hard_negatives),
            "tasks": dict(sorted(task_counts.items())),
            "splits": dict(sorted(split_counts.items())),
            "hard_negative_types": dict(sorted(error_counts.items())),
        },
        "deduplicated": {
            "sft": sft_duplicates, "preferences": preference_duplicates,
            "hard_negatives": negative_duplicates,
        },
        "weak_labels": {
            "ocr": "Llama structured visual output; requires sampling review",
            "entity": "accepted only with entity consistency or correct-answer weak label",
            "evidence": "selected by answer-token and numeric overlap",
        },
        "files": files,
        "sources": {
            "full_results": str(args.full_results),
            "full_judgments": str(args.full_judgments),
            "structured_results": str(args.structured_results),
            "structured_judgments": str(args.structured_judgments),
        },
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest["manifest_sha256_before_self_reference"] = file_sha256(manifest_path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    card = f"""# CRAG-MM P5 Training Data

Generated: 2026-11-24

## Scope

- Development source positions: `0–{args.max_position}` only.
- External held-out positions: `{args.external_heldout_start}–{args.external_heldout_end}`; excluded from every output file.
- Images are referenced by repository-relative path and are not duplicated.
- Train/dev split is stable by SHA-256 of `session_id`.

## Counts

- SFT records: {len(sft)}
- Preference records: {len(preferences)}
- Hard negatives: {len(hard_negatives)}
- Train/dev SFT: {split_counts['train']} / {split_counts['dev']}

## Label policy

- Ground-truth text appears only as an assistant target or preference `chosen`, never as an explicitly named input field.
- Lookup/comparison answers without matching retrieved evidence are converted to `I don't know.` targets.
- OCR labels are weak labels from the structured Llama pass and require manual sampling before training.
- Wrong model answers are retained only as `rejected` or hard-negative examples.

## Files

See `manifest.json` for counts, byte sizes and SHA-256 values.

## Training caution

Do not train on positions 400–599. Use them only once for held-out evaluation after the adapter and refusal threshold are frozen.
"""
    (args.output_dir / "DATA_CARD.md").write_text(card, encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))
    print(f"Saved P5 bundle to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
