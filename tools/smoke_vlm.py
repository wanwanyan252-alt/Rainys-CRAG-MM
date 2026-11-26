"""Run one image/question through a CUDA VLM without retrieval or evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-name",
        default="meta-llama/Llama-3.2-11B-Vision-Instruct",
    )
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--query", default="Describe the main subject in this image.")
    parser.add_argument("--rag-context", default="")
    parser.add_argument("--max-tokens", type=int, default=128)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.image.is_file():
        raise SystemExit(f"Image does not exist: {args.image}")
    if args.max_tokens < 1:
        raise SystemExit("--max-tokens must be at least 1")

    repository_root = Path(__file__).resolve().parents[1]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))

    import torch
    from PIL import Image
    from example_agents.user_config import get_agent_from_model_name

    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is not available. Run this smoke test in the cloud environment."
        )

    agent_class = get_agent_from_model_name(args.model_name)
    agent = agent_class(model_name=args.model_name, max_gen_len=args.max_tokens)
    with Image.open(args.image) as source_image:
        image = source_image.convert("RGB")
    response = agent.batch_generate_response(
        queries=[args.query],
        images=[image],
        message_histories=[[]],
        rag_context_list=[args.rag_context],
    )[0]
    print("\n=== VLM smoke response ===")
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
