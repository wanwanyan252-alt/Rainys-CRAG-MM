"""Apply one audited Stage C repair set without changing positions 0--49."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--repairs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    repairs = {int(key): value for key, value in json.loads(args.repairs.read_text(encoding="utf-8")).items()}
    if not repairs or any(position < 50 or position > 99 for position in repairs):
        raise SystemExit("Repairs must target only positions 50--99")
    before = [item["agent_response"] for item in payload["results"][:50]]
    by_position = {item["position"]: item for item in payload["results"]}
    for position, response in repairs.items():
        item = by_position[position]
        item["pre_targeted_repair_response"] = item["agent_response"]
        item["agent_response"] = response
        item["is_abstention"] = False
    if before != [item["agent_response"] for item in payload["results"][:50]]:
        raise SystemExit("Fixed first 50 changed unexpectedly")
    payload["stage_c_targeted_repairs"] = sorted(repairs)
    results = payload["results"]
    payload["proxy_metrics"]["abstention_count"] = sum(item["is_abstention"] for item in results)
    payload["proxy_metrics"]["abstention_rate"] = round(payload["proxy_metrics"]["abstention_count"] / len(results), 4)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("repaired_positions=", sorted(repairs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
