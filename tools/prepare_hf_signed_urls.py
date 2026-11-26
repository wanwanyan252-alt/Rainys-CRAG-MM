"""Create an aria2 input file from official Hugging Face redirect URLs."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse

import requests


ALLOWED_DOWNLOAD_HOST_SUFFIXES = (
    ".hf.co",
    ".xethub.hf.co",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--repo-type", choices=["dataset", "model"], required=True)
    parser.add_argument("--revision", default="main")
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("files", nargs="+")
    return parser.parse_args()


def is_official_download_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    return hostname == "hf.co" or hostname.endswith(ALLOWED_DOWNLOAD_HOST_SUFFIXES)


def resolve_url(repo_id: str, repo_type: str, revision: str, file_path: str) -> str:
    prefix = "datasets/" if repo_type == "dataset" else ""
    encoded_path = quote(file_path, safe="/")
    source_url = (
        f"https://huggingface.co/{prefix}{repo_id}/resolve/"
        f"{quote(revision, safe='')}/{encoded_path}"
    )
    response = requests.get(
        source_url,
        allow_redirects=False,
        stream=True,
        timeout=120,
    )
    if response.status_code not in {301, 302, 303, 307, 308}:
        raise RuntimeError(
            f"Expected a redirect for {file_path}, got HTTP {response.status_code}"
        )
    location = response.headers.get("location")
    hostname = urlparse(location).hostname
    if not is_official_download_host(hostname):
        raise RuntimeError(
            f"Refusing non-Hugging-Face download host for {file_path}: {hostname}"
        )
    return location


def main() -> int:
    args = parse_args()
    blocks = []
    remote_root = PurePosixPath(args.remote_dir)
    for file_path in args.files:
        relative_path = PurePosixPath(file_path)
        signed_url = resolve_url(
            args.repo_id, args.repo_type, args.revision, file_path
        )
        remote_parent = remote_root / relative_path.parent
        blocks.append(
            f"{signed_url}\n"
            f"  dir={remote_parent}\n"
            f"  out={relative_path.name}\n"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(blocks), encoding="utf-8")
    print(f"Prepared {len(blocks)} official download entries in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
