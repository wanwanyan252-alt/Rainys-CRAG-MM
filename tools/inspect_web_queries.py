"""Inspect ranked results for several existing CRAG-MM web-index queries."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", required=True)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--hf-home", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.environ["HF_HOME"] = str(args.hf_home)
    os.environ["HF_HUB_CACHE"] = str(args.hf_home / "hub")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    repository_root = Path(__file__).resolve().parents[1]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))

    from utils.search_pipeline_compat import UnifiedSearchPipeline

    search = UnifiedSearchPipeline(
        text_model_name="BAAI/bge-large-en-v1.5",
        web_hf_dataset_id="crag-mm-2025/web-search-index-public-test",
        image_model_name=None,
        image_hf_dataset_id=None,
        report_timings=True,
    )
    for query in args.query:
        print(f"\n=== QUERY: {query} ===")
        for rank, result in enumerate(search(query, k=args.top_k), 1):
            title = str(result.get("page_name", "")).replace("\n", " ")
            snippet = str(result.get("page_snippet", "")).replace("\n", " ")
            print(f"[{rank}] {title}\n{snippet[:500]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
