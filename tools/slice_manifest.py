"""Create a manifest containing one exact contiguous global-position range."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-position", type=int, required=True)
    parser.add_argument("--end-position", type=int, required=True)
    args = parser.parse_args()
    entries = json.loads(args.input.read_text(encoding="utf-8"))
    selected = [
        entry for entry in entries
        if args.start_position <= entry.get("index", -1) <= args.end_position
    ]
    expected = list(range(args.start_position, args.end_position + 1))
    actual = [entry.get("index") for entry in selected]
    if actual != expected:
        raise SystemExit(
            f"Expected exact global positions {args.start_position}--"
            f"{args.end_position}, found {actual[:3]}...{actual[-3:]}"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved {len(selected)} positions: {actual[0]}--{actual[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
