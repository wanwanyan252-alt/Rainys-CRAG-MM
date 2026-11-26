"""Merge a PEFT LoRA adapter into the Llama 3.2 Vision BF16 base model."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not (args.adapter / "adapter_config.json").is_file():
        raise SystemExit(f"Invalid adapter directory: {args.adapter}")

    import torch
    from peft import PeftModel
    from transformers import AutoProcessor, MllamaForConditionalGeneration

    model = MllamaForConditionalGeneration.from_pretrained(
        str(args.base_model),
        torch_dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True,
    )
    model = PeftModel.from_pretrained(model, str(args.adapter))
    merged = model.merge_and_unload(safe_merge=True)
    args.output.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(
        str(args.output), safe_serialization=True, max_shard_size="5GB"
    )
    processor = AutoProcessor.from_pretrained(str(args.base_model))
    processor.save_pretrained(str(args.output))
    print(f"Saved merged BF16 model to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
