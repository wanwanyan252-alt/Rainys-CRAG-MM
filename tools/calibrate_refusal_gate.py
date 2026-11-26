"""Train and evaluate a lightweight refusal gate from inference-time-only features."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "had", "has", "have", "he", "her", "his", "how", "i", "in", "is",
    "it", "its", "of", "on", "or", "she", "that", "the", "their", "them", "there",
    "these", "they", "this", "those", "to", "was", "were", "what", "when", "where",
    "which", "who", "why", "with", "would", "you", "your",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dev-start", type=int, default=0)
    parser.add_argument("--dev-count", type=int, default=200)
    parser.add_argument("--folds", type=int, default=5)
    return parser.parse_args()


def tokens(text: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-z0-9]+", text.casefold())
        if len(token) > 1 and token not in STOPWORDS
    ]


def overlap_fraction(left: list[str], right_text: str) -> float:
    if not left:
        return 0.0
    right = set(tokens(right_text))
    return len(set(left) & right) / len(set(left))


def extract_features(result: dict) -> tuple[list[str], np.ndarray]:
    query = result["query"]
    response = result["agent_response"]
    rag = result.get("rag_context", "")
    entity = (result.get("web_query_entity") or "").strip()
    details = result.get("web_query_entity_details") or []
    observed = [
        (detail.get("entity") or "").strip()
        for detail in details
        if (detail.get("entity") or "").strip()
    ]
    normalized_observed = [value.casefold() for value in observed]
    selected_support = sum(value == entity.casefold() for value in normalized_observed) if entity else 0
    full_support = bool(
        entity
        and details
        and (details[0].get("entity") or "").strip().casefold() == entity.casefold()
    )
    candidate_matches = []
    for detail in details:
        context = detail.get("image_context") or ""
        if entity:
            pattern = re.compile(
                r"Candidate\s+\d+:\s+([^\n]+?)\s+\(visual similarity:\s*([0-9.]+);\s*occurrences:\s*(\d+)\)",
                re.IGNORECASE,
            )
            for name, score, occurrences in pattern.findall(context):
                if name.strip().casefold() == entity.casefold():
                    candidate_matches.append((float(score), int(occurrences)))
    response_tokens = tokens(response)
    query_tokens = tokens(query)
    entity_tokens = tokens(entity)
    web_docs = re.findall(r"<DOC>.*?</DOC>", rag, re.DOTALL | re.IGNORECASE)
    web_text = " ".join(web_docs)
    hedge_phrases = (
        "not explicitly", "however", "likely", "appears", "seems", "based on",
        "provided image", "search results", "cannot determine", "difficult to determine",
        "it is possible", "may be", "might be", "approximately",
    )
    question_prefixes = (
        "who", "what", "when", "where", "which", "how many", "how much", "how long",
        "how often", "is", "are", "does", "do", "did", "can", "was", "were",
    )
    names: list[str] = []
    values: list[float] = []

    def add(name: str, value: float | bool) -> None:
        names.append(name)
        values.append(float(value))

    add("has_entity", bool(entity))
    add("entity_token_count", len(entity_tokens))
    add("observed_entity_count", len(observed))
    add("observed_unique_count", len(set(normalized_observed)))
    add("selected_support_count", selected_support)
    add("selected_full_support", full_support)
    add("selected_candidate_match", bool(candidate_matches))
    add("selected_candidate_max_score", max((x[0] for x in candidate_matches), default=0.0))
    add("selected_candidate_max_occurrences", max((x[1] for x in candidate_matches), default=0))
    add("entity_in_response", overlap_fraction(entity_tokens, response))
    add("entity_in_web", overlap_fraction(entity_tokens, web_text))
    add("query_in_web", overlap_fraction(query_tokens, web_text))
    add("response_in_web", overlap_fraction(response_tokens, web_text))
    add("response_in_rag", overlap_fraction(response_tokens, rag))
    add("response_word_count", len(response.split()))
    add("response_sentence_count", len(re.findall(r"[.!?]+", response)))
    add("response_number_count", len(re.findall(r"\b\d+(?:\.\d+)?\b", response)))
    add("query_number_count", len(re.findall(r"\b\d+(?:\.\d+)?\b", query)))
    add("rag_chars", min(len(rag), 12000) / 12000)
    add("web_doc_count", len(web_docs))
    add("rewrite_seconds", min(result.get("rewrite_seconds", 0.0), 20.0) / 20.0)
    add("retrieval_seconds", min(result.get("retrieval_seconds", 0.0), 2.0) / 2.0)
    add("generation_seconds", min(result.get("generation_seconds", 0.0), 10.0) / 10.0)
    add("web_query_changed", result.get("web_search_query", query).strip().casefold() != query.strip().casefold())
    add("preliminary_changed", result.get("preliminary_agent_response", response) != response)
    add("numeric_checked", result.get("numeric_evidence_valid") is not None)
    add("numeric_valid", result.get("numeric_evidence_valid") is True)
    add("contains_hedge", any(phrase in response.casefold() for phrase in hedge_phrases))
    add("contains_search_meta", "search result" in response.casefold() or "provided" in response.casefold())
    add("contains_unknown_language", "unknown" in response.casefold() or "unsure" in response.casefold())
    add("deictic_query", bool(re.search(r"\b(this|these|those|it|one|ones)\b", query, re.IGNORECASE)))
    add("comparison_query", bool(re.search(r"\b(versus|compared|more than|less than|cheaper|higher|lower|difference)\b", query, re.IGNORECASE)))
    add("query_has_superlative", bool(re.search(r"\b(first|last|largest|smallest|highest|lowest|most|least)\b", query, re.IGNORECASE)))
    add("response_starts_yes", response.strip().casefold().startswith("yes"))
    add("response_starts_no", response.strip().casefold().startswith("no"))
    for prefix in question_prefixes:
        add(f"qprefix_{prefix.replace(' ', '_')}", query.strip().casefold().startswith(prefix + " ") or query.strip().casefold() == prefix)
    add("has_visible_text", bool(result.get("visible_text")))
    add(
        "visible_text_token_count",
        len(tokens(result.get("visible_text", ""))),
    )
    add(
        "entity_consistency_valid",
        result.get("entity_consistency_valid", False),
    )
    add("web_retrieval_routed", result.get("web_retrieval_routed", True))
    add("confidence_high", result.get("visual_confidence") == "high")
    add("confidence_low", result.get("visual_confidence") == "low")
    for route in ("identity", "visual", "ocr", "lookup", "comparison", "chart"):
        add(f"route_{route}", result.get("question_route") == route)
    return names, np.asarray(values, dtype=np.float64)


def align_feature_values(
    feature_names: list[str],
    feature_values: np.ndarray,
    expected_feature_names: list[str],
) -> np.ndarray:
    if feature_names == expected_feature_names:
        return feature_values
    if feature_names[: len(expected_feature_names)] == expected_feature_names:
        return feature_values[: len(expected_feature_names)]
    by_name = dict(zip(feature_names, feature_values))
    if all(name in by_name for name in expected_feature_names):
        return np.asarray(
            [by_name[name] for name in expected_feature_names], dtype=np.float64
        )
    missing = [name for name in expected_feature_names if name not in by_name]
    raise ValueError(f"Missing refusal-gate features: {missing}")


def fit_logistic(x: np.ndarray, y: np.ndarray, l2: float = 0.2) -> dict:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-6] = 1.0
    z = (x - mean) / scale
    design = np.column_stack([np.ones(len(z)), z])
    weights = np.zeros(design.shape[1])
    for step in range(1800):
        logits = np.clip(design @ weights, -30, 30)
        probs = 1.0 / (1.0 + np.exp(-logits))
        gradient = design.T @ (probs - y) / len(y)
        gradient[1:] += l2 * weights[1:] / len(y)
        rate = 0.15 / math.sqrt(1.0 + step / 300)
        weights -= rate * gradient
    return {"mean": mean, "scale": scale, "weights": weights}


def predict(model: dict, x: np.ndarray) -> np.ndarray:
    z = (x - model["mean"]) / model["scale"]
    design = np.column_stack([np.ones(len(z)), z])
    logits = np.clip(design @ model["weights"], -30, 30)
    return 1.0 / (1.0 + np.exp(-logits))


def stats(scores: np.ndarray) -> dict:
    count = len(scores)
    if count == 0:
        return {
            "count": 0,
            "correct": 0,
            "miss": 0,
            "wrong": 0,
            "truthfulness": 0.0,
            "coverage": 0.0,
            "answered_accuracy": 0.0,
        }
    correct = int(np.sum(scores == 1))
    wrong = int(np.sum(scores == -1))
    miss = count - correct - wrong
    return {
        "count": count,
        "correct": correct,
        "miss": miss,
        "wrong": wrong,
        "truthfulness": round(float(np.mean(scores)), 4),
        "coverage": round((correct + wrong) / count, 4),
        "answered_accuracy": round(correct / (correct + wrong), 4) if correct + wrong else 0.0,
    }


def choose_threshold(probabilities: np.ndarray, original_scores: np.ndarray, max_missing: float = 0.75) -> tuple[float, dict]:
    best = None
    for threshold in np.linspace(0.25, 0.9, 131):
        gated = np.where((original_scores != 0) & (probabilities >= threshold), original_scores, 0)
        result = stats(gated)
        if result["miss"] / result["count"] > max_missing:
            continue
        candidate = (result["truthfulness"], result["coverage"], float(threshold), result)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    if best is None:
        raise SystemExit("No threshold satisfies the missing-rate constraint")
    return best[2], best[3]


def main() -> int:
    args = parse_args()
    results = json.loads(args.results.read_text(encoding="utf-8"))["results"]
    judgments = json.loads(args.judgments.read_text(encoding="utf-8"))["judgments"]
    if len(results) != len(judgments):
        raise SystemExit("Results and judgments have different lengths")
    score_by_position = {item["position"]: item["score"] for item in judgments}
    answered = [item for item in results if score_by_position[item["position"]] != 0]
    feature_names, first = extract_features(answered[0])
    x = np.vstack([first] + [extract_features(item)[1] for item in answered[1:]])
    y = np.asarray([score_by_position[item["position"]] == 1 for item in answered], dtype=np.float64)
    positions = np.asarray([item["position"] for item in answered])
    scores = np.asarray([score_by_position[item["position"]] for item in results])

    dev_stop = args.dev_start + args.dev_count
    dev_mask = (positions >= args.dev_start) & (positions < dev_stop)
    if not np.any(dev_mask):
        raise SystemExit(
            f"No answered samples in dev range {args.dev_start}--{dev_stop - 1}"
        )
    dev_model = fit_logistic(x[dev_mask], y[dev_mask])
    all_answered_prob = predict(dev_model, x)
    full_probabilities = np.zeros(len(results))
    row_by_position = {
        item["position"]: row for row, item in enumerate(results)
    }
    for item, probability in zip(answered, all_answered_prob):
        full_probabilities[row_by_position[item["position"]]] = probability
    result_positions = np.asarray([item["position"] for item in results])
    dev_result_mask = (
        (result_positions >= args.dev_start) & (result_positions < dev_stop)
    )
    dev_threshold, dev_tuned_stats = choose_threshold(
        full_probabilities[dev_result_mask], scores[dev_result_mask]
    )
    gated_scores = np.where(
        (scores != 0) & (full_probabilities >= dev_threshold), scores, 0
    )

    folds = np.asarray([
        int(hashlib.sha256(item["session_id"].encode()).hexdigest()[:8], 16) % args.folds
        for item in answered
    ])
    oof = np.zeros(len(answered))
    for fold in range(args.folds):
        train = folds != fold
        test = folds == fold
        model = fit_logistic(x[train], y[train])
        oof[test] = predict(model, x[test])
    full_oof = np.zeros(len(results))
    for item, probability in zip(answered, oof):
        full_oof[row_by_position[item["position"]]] = probability
    oof_threshold, oof_stats = choose_threshold(full_oof, scores)

    output = {
        "feature_names": feature_names,
        "dev_start": args.dev_start,
        "dev_count": args.dev_count,
        "dev_trained_threshold": dev_threshold,
        "baseline": {
            "dev": stats(scores[dev_result_mask]),
            "non_dev": stats(scores[~dev_result_mask]),
            "full": stats(scores),
        },
        "dev_trained_gate": {
            "tuned_dev": dev_tuned_stats,
            "non_dev": stats(gated_scores[~dev_result_mask]),
            "full": stats(gated_scores),
        },
        "five_fold_oof_potential": {
            "threshold": oof_threshold,
            "full": oof_stats,
        },
        "model": {
            "mean": dev_model["mean"].tolist(),
            "scale": dev_model["scale"].tolist(),
            "weights": dev_model["weights"].tolist(),
        },
        "predictions": [
            {
                "position": item["position"],
                "original_score": score_by_position[item["position"]],
                "probability_correct": round(
                    float(full_probabilities[row_by_position[item["position"]]]), 6
                ),
                "keep": bool(
                    score_by_position[item["position"]] != 0
                    and full_probabilities[row_by_position[item["position"]]]
                    >= dev_threshold
                ),
            }
            for item in results
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["baseline"], ensure_ascii=False, indent=2))
    print(json.dumps(output["dev_trained_gate"], ensure_ascii=False, indent=2))
    print(json.dumps(output["five_fold_oof_potential"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
