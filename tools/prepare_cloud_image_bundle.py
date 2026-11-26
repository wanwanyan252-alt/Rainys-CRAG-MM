"""Prepare a compact, verified image bundle at the evaluator's effective resolution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--quality", type=int, default=90)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    manifest_path = args.source_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for completed, entry in enumerate(manifest, 1):
        source = args.source_dir / entry["image"]
        output = args.output_dir / entry["image"]
        if args.resume and output.is_file():
            continue
        with Image.open(source) as original:
            image = original.convert("RGB")
        if entry.get("image_url"):
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        else:
            image = image.resize((960, 1280), Image.Resampling.LANCZOS)
        image.save(
            output,
            format="JPEG",
            quality=args.quality,
            optimize=True,
            progressive=True,
        )
        if completed % 100 == 0 or completed == len(manifest):
            print(f"prepared {completed}/{len(manifest)}", flush=True)
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved compact bundle to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
