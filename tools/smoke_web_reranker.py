"""Offline smoke test for the independent web cross-encoder reranker."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

repository_root = Path(__file__).resolve().parents[1]
if str(repository_root) not in sys.path:
    sys.path.insert(0, str(repository_root))

from utils.web_reranker import CrossEncoderWebReranker


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    reranker = CrossEncoderWebReranker(args.model, device="cpu")
    documents = [
        {"page_name": "Museums", "page_snippet": "Berlin is known for museums."},
        {"page_name": "Population", "page_snippet": "Berlin has 3.5 million people."},
    ]
    ranked = reranker.rank("How many people live in Berlin?", documents)
    if ranked[0]["page_name"] != "Population":
        raise SystemExit(f"Unexpected reranker order: {ranked}")
    print([(item["page_name"], item["reranker_score"]) for item in ranked])
    print("Web reranker smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
