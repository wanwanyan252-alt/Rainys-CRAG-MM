"""Apply a calibrated refusal gate to saved results and existing judgments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

repository_root = Path(__file__).resolve().parents[1]
if str(repository_root) not in sys.path:
    sys.path.insert(0, str(repository_root))

from tools.calibrate_refusal_gate import (
    align_feature_values,
    extract_features,
    predict,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--output-results", type=Path, required=True)
    parser.add_argument("--output-judgments", type=Path, required=True)
    args = parser.parse_args()
    results_payload = json.loads(args.results.read_text(encoding="utf-8"))
    judgment_payload = json.loads(args.judgments.read_text(encoding="utf-8"))
    gate_payload = json.loads(args.gate.read_text(encoding="utf-8"))
    threshold = (
        args.threshold
        if args.threshold is not None
        else gate_payload["dev_trained_threshold"]
    )
    model = {
        key: np.asarray(gate_payload["model"][key], dtype=np.float64)
        for key in ("mean", "scale", "weights")
    }
    expected_feature_names = gate_payload["feature_names"]
    judgment_by_position = {
        item["position"]: item for item in judgment_payload["judgments"]
    }
    changed = []
    new_results = []
    new_judgments = []
    for result in results_payload["results"]:
        position = result["position"]
        judgment = dict(judgment_by_position[position])
        updated = dict(result)
        feature_names, feature_values = extract_features(result)
        feature_values = align_feature_values(
            feature_names, feature_values, expected_feature_names
        )
        probability_correct = float(
            predict(model, feature_values.reshape(1, -1))[0]
        )
        keep = probability_correct >= threshold
        if not result["is_abstention"] and not keep:
            updated["pre_refusal_gate_response"] = result["agent_response"]
            updated["refusal_gate_probability_correct"] = round(
                probability_correct, 6
            )
            updated["agent_response"] = "I don't know."
            updated["is_abstention"] = True
            updated["proxy_token_f1"] = 0.0
            judgment["pre_refusal_gate_score"] = judgment["score"]
            judgment["pre_refusal_gate_source"] = judgment["source"]
            judgment["pre_refusal_gate_response"] = judgment["agent_response"]
            judgment["agent_response"] = "I don't know."
            judgment["score"] = 0
            judgment["source"] = "refusal_gate"
            judgment["judge_response"] = None
            changed.append(position)
        else:
            updated["refusal_gate_probability_correct"] = round(
                probability_correct, 6
            )
        new_results.append(updated)
        new_judgments.append(judgment)
    count = len(new_results)
    abstentions = sum(item["is_abstention"] for item in new_results)
    results_payload["results"] = new_results
    results_payload["refusal_gate"] = {
        "trained_on_positions": "0-199",
        "threshold": threshold,
        "changed_count": len(changed),
        "calibration_file": str(args.gate),
    }
    results_payload["proxy_metrics"] = {
        **results_payload["proxy_metrics"],
        "count": count,
        "abstention_count": abstentions,
        "abstention_rate": round(abstentions / count, 4),
        "mean_token_f1": round(
            sum(item["proxy_token_f1"] for item in new_results) / count, 4
        ),
    }
    summary = {
        "count": count,
        "correct": sum(item["score"] == 1 for item in new_judgments),
        "miss": sum(item["score"] == 0 for item in new_judgments),
        "wrong": sum(item["score"] == -1 for item in new_judgments),
        "judge_errors": sum(item["source"] == "judge_error" for item in new_judgments),
    }
    summary["truthfulness_score"] = round(
        (summary["correct"] - summary["wrong"]) / count, 4
    )
    judgment_payload["summary"] = summary
    judgment_payload["judgments"] = new_judgments
    judgment_payload["refusal_gate"] = results_payload["refusal_gate"]
    args.output_results.write_text(
        json.dumps(results_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.output_judgments.write_text(
        json.dumps(judgment_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    print(f"Converted {len(changed)} answers to abstentions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
