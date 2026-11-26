"""Export a deterministic CRAG-MM streaming slice to images plus a manifest."""

from __future__ import annotations

import argparse
from io import BytesIO
import json
from pathlib import Path
import time
from urllib.parse import urlparse, urlunparse

from datasets import load_dataset
from PIL import Image
import requests


MAX_REMOTE_IMAGE_BYTES = 50 * 1024 * 1024
REMOTE_REQUEST_INTERVAL_SECONDS = 1.0
_last_remote_request_at = 0.0
_remote_session = requests.Session()
_remote_session.headers.update(
    {
        "User-Agent": (
            "Rainys-CRAG-MM-Evaluator/1.0 "
            "(https://github.com/wanwanyan252-alt/Rainys-CRAG-MM; "
            "research dataset evaluation)"
        )
    }
)


def wikimedia_thumbnail_url(url: str, width: int = 1280) -> str:
    parsed = urlparse(url)
    marker = "/wikipedia/commons/"
    if marker not in parsed.path:
        return url
    if "/thumb/" in parsed.path:
        parent, _, original_filename = parsed.path.rpartition("/")
        source_filename = parent.rsplit("/", 1)[-1]
        suffix = source_filename.lower().rsplit(".", 1)[-1]
        thumbnail_name = f"{width}px-{source_filename}"
        if suffix in {"tif", "tiff", "svg"}:
            thumbnail_name += ".jpg" if suffix in {"tif", "tiff"} else ".png"
        return urlunparse(parsed._replace(path=f"{parent}/{thumbnail_name}"))
    prefix, relative = parsed.path.split(marker, 1)
    filename = relative.rsplit("/", 1)[-1]
    suffix = filename.lower().rsplit(".", 1)[-1]
    thumbnail_name = f"{width}px-{filename}"
    if suffix in {"tif", "tiff", "svg"}:
        thumbnail_name += ".jpg" if suffix in {"tif", "tiff"} else ".png"
    thumbnail_path = f"{prefix}{marker}thumb/{relative}/{thumbnail_name}"
    return urlunparse(parsed._replace(path=thumbnail_path))


def download_official_image(url: str) -> Image.Image:
    global _last_remote_request_at
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "upload.wikimedia.org":
        raise SystemExit(f"Refusing non-official image URL: {url}")
    last_error: Exception | None = None
    download_urls = [wikimedia_thumbnail_url(url), url]
    for download_url in dict.fromkeys(download_urls):
        for attempt in range(3):
            try:
                wait_seconds = REMOTE_REQUEST_INTERVAL_SECONDS - (
                    time.monotonic() - _last_remote_request_at
                )
                if wait_seconds > 0:
                    time.sleep(wait_seconds)
                response = _remote_session.get(
                    download_url, timeout=30, stream=True
                )
                _last_remote_request_at = time.monotonic()
                if response.status_code == 404:
                    response.close()
                    break
                response.raise_for_status()
                chunks = bytearray()
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    chunks.extend(chunk)
                    if len(chunks) > MAX_REMOTE_IMAGE_BYTES:
                        break
                response.close()
                data = bytes(chunks)
                if len(data) > MAX_REMOTE_IMAGE_BYTES:
                    raise ValueError("remote image exceeds 50 MiB")
                with Image.open(BytesIO(data)) as image:
                    return image.convert("RGB")
            except requests.HTTPError as error:
                _last_remote_request_at = time.monotonic()
                last_error = error
                if attempt < 2:
                    retry_after = (
                        error.response.headers.get("Retry-After")
                        if error.response is not None
                        else None
                    )
                    delay = int(retry_after) if retry_after and retry_after.isdigit() else 15 * (attempt + 1)
                    time.sleep(min(delay, 60))
            except Exception as error:
                _last_remote_request_at = time.monotonic()
                last_error = error
                if attempt < 2:
                    time.sleep(2**attempt)
    raise SystemExit(f"Failed to download official image after 3 attempts: {last_error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Zero-based dataset index of the first row to export.",
    )
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--split", default="validation")
    parser.add_argument("--revision", default="v0.1.2")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse already exported image files while rebuilding the manifest.",
    )
    parser.add_argument(
        "--download-missing-images",
        action="store_true",
        help="Download missing images only from official upload.wikimedia.org URLs.",
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        nargs="+",
        help="Use a local CRAG-MM parquet shard instead of Hugging Face streaming.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.start < 0:
        raise SystemExit("--start must be non-negative")
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.parquet:
        missing = [path for path in args.parquet if not path.is_file()]
        if missing:
            raise SystemExit(f"Parquet file does not exist: {missing[0]}")
        dataset = load_dataset(
            "parquet",
            data_files=[str(path) for path in args.parquet],
            split="train",
            streaming=True,
        )
    else:
        dataset = load_dataset(
            "crag-mm-2025/crag-mm-single-turn-public",
            revision=args.revision,
            split=args.split,
            streaming=True,
        )
    rows = []
    for index, example in enumerate(dataset):
        if index < args.start:
            continue
        if index >= args.start + args.count:
            break
        image_name = f"{index:03d}.jpg"
        image_path = args.output_dir / image_name
        if not (args.resume and image_path.is_file()):
            image = example.get("image")
            if image is None:
                image_url = example.get("image_url")
                if not args.download_missing_images or not image_url:
                    raise SystemExit(
                        f"Dataset index {index} has no embedded image; use "
                        "--download-missing-images when an official URL is available"
                    )
                image = download_official_image(image_url)
            image.convert("RGB").save(image_path, quality=95)
        rows.append(
            {
                "index": index,
                "session_id": example["session_id"],
                "image": image_name,
                "image_url": example.get("image_url"),
                "turns": example["turns"],
                "answers": example["answers"],
            }
        )
        print(f"exported {len(rows)}/{args.count} (dataset index {index})", flush=True)
    if len(rows) != args.count:
        raise SystemExit(f"Requested {args.count} rows, exported {len(rows)}")
    (args.output_dir / "manifest.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Saved manifest to {args.output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
