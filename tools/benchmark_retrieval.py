"""Measure CRAG-MM retrieval startup and first-query latency.

This script deliberately prints each completed initialization phase immediately.
That makes a slow or interrupted large-index startup diagnosable without waiting
for the whole constructor to return.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["web", "image", "both"], default="web")
    parser.add_argument(
        "--query", default="Washington DC to Baltimore driving distance"
    )
    parser.add_argument("--image", type=Path, help="Image path for image/both mode")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--hf-home", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--initialize-only", action="store_true")
    parser.add_argument("--output-json", type=Path)
    return parser.parse_args()


def configure_environment(args: argparse.Namespace) -> None:
    if args.hf_home:
        os.environ["HF_HOME"] = str(args.hf_home)
        os.environ["HF_HUB_CACHE"] = str(args.hf_home / "hub")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"


def main() -> int:
    args = parse_args()
    if (
        args.mode in {"image", "both"}
        and not args.initialize_only
        and not args.image
    ):
        raise SystemExit("--image is required for image or both mode")
    if args.top_k < 1:
        raise SystemExit("--top-k must be at least 1")

    configure_environment(args)
    repository_root = Path(__file__).resolve().parents[1]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))

    from PIL import Image
    from utils.search_pipeline_compat import UnifiedSearchPipeline

    web_enabled = args.mode in {"web", "both"}
    image_enabled = args.mode in {"image", "both"}
    print(f"Starting {args.mode} retrieval initialization...", flush=True)
    search = UnifiedSearchPipeline(
        text_model_name="BAAI/bge-large-en-v1.5" if web_enabled else None,
        web_hf_dataset_id=(
            "crag-mm-2025/web-search-index-public-test" if web_enabled else None
        ),
        image_model_name=(
            "openai/clip-vit-large-patch14-336" if image_enabled else None
        ),
        image_hf_dataset_id=(
            "crag-mm-2025/image-search-index-public-test"
            if image_enabled
            else None
        ),
        report_timings=True,
    )

    report: dict[str, object] = {
        "mode": args.mode,
        "initialization": search.timings,
        "queries": {},
    }
    if not args.initialize_only:
        if image_enabled:
            with Image.open(args.image) as source_image:
                image = source_image.convert("RGB")
            started = time.perf_counter()
            image_results = search(image, k=args.top_k)
            elapsed = time.perf_counter() - started
            print(f"[retrieval timing] first_image_query_seconds: {elapsed:.3f}s")
            report["queries"]["image"] = {
                "seconds": elapsed,
                "result_count": len(image_results),
            }

        if web_enabled:
            started = time.perf_counter()
            web_results = search(args.query, k=args.top_k)
            elapsed = time.perf_counter() - started
            print(f"[retrieval timing] first_web_query_seconds: {elapsed:.3f}s")
            report["queries"]["web"] = {
                "seconds": elapsed,
                "result_count": len(web_results),
            }

    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
