"""Validate P5 JSONL files, split integrity, image refs, leakage, and hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid JSON in {path.name}:{line_number}: {error}") from error
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    manifest_path = args.data_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    all_records = []
    split_by_session: dict[str, str] = {}
    ids = set()
    for file_name, expected in manifest["files"].items():
        path = args.data_dir / file_name
        if not path.is_file():
            raise SystemExit(f"Missing file: {path}")
        if sha256(path) != expected["sha256"]:
            raise SystemExit(f"SHA-256 mismatch: {file_name}")
        records = read_jsonl(path)
        if len(records) != expected["count"]:
            raise SystemExit(f"Count mismatch: {file_name}")
        expected_split = "train" if "_train." in file_name else "dev"
        for record in records:
            if record["id"] in ids:
                raise SystemExit(f"Duplicate record id: {record['id']}")
            ids.add(record["id"])
            if record["split"] != expected_split:
                raise SystemExit(f"Split mismatch in {file_name}: {record['id']}")
            position = int(record["position"])
            if not 0 <= position <= 399:
                raise SystemExit(f"Out-of-scope position: {position}")
            if 400 <= position <= 599:
                raise SystemExit(f"Held-out leakage: {position}")
            session_id = record["session_id"]
            prior_split = split_by_session.setdefault(session_id, record["split"])
            if prior_split != record["split"]:
                raise SystemExit(f"Session split leakage: {session_id}")
            image = args.repo_root / record["image"]
            if not image.is_file():
                raise SystemExit(f"Missing image ref: {record['image']}")
            if "ground_truth" in record:
                raise SystemExit(f"Explicit ground_truth field leaked: {record['id']}")
            serialized = json.dumps(record, ensure_ascii=False)
            if "DEEPSEEK_API_KEY" in serialized or "OPENAI_API_KEY" in serialized:
                raise SystemExit(f"Secret-like field found: {record['id']}")
            if "messages" in record:
                assistant = record["messages"][-1]
                if assistant.get("role") != "assistant":
                    raise SystemExit(f"Missing assistant target: {record['id']}")
                target = assistant.get("content") or []
                if not target or not (target[0].get("text") or "").strip():
                    raise SystemExit(f"Empty assistant target: {record['id']}")
            if "chosen" in record and record["chosen"].strip() == record["rejected"].strip():
                raise SystemExit(f"Identical preference pair: {record['id']}")
        all_records.extend(records)
    print(
        json.dumps(
            {
                "valid": True,
                "records": len(all_records),
                "unique_ids": len(ids),
                "sessions": len(split_by_session),
                "train_sessions": sum(value == "train" for value in split_by_session.values()),
                "dev_sessions": sum(value == "dev" for value in split_by_session.values()),
                "heldout_leakage": 0,
                "missing_images": 0,
                "hash_mismatches": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
