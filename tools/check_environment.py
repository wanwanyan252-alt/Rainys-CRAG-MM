"""Read-only environment diagnostics for local CRAG-MM development."""

from __future__ import annotations

import importlib
import importlib.metadata
import platform
from pathlib import Path
import sys


PACKAGES = {
    "cragmm-search-pipeline": "0.5.1",
    "chromadb": "1.0.15",
    "torch": None,
    "transformers": None,
    "datasets": None,
    "python-dotenv": None,
}


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))

    errors = []
    warnings = []
    print(f"Python: {platform.python_version()} ({sys.executable})")

    for package, expected in PACKAGES.items():
        try:
            installed = importlib.metadata.version(package)
            suffix = f" (expected {expected})" if expected else ""
            print(f"{package}: {installed}{suffix}")
            if expected and installed != expected:
                warnings.append(
                    f"{package} is {installed}; the validated version is {expected}"
                )
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"{package} is not installed")

    try:
        torch = importlib.import_module("torch")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if not torch.cuda.is_available():
            warnings.append(
                "CUDA is unavailable; use this environment for lightweight local "
                "debugging, not local VLM inference"
            )
    except ImportError:
        pass

    try:
        importlib.import_module("utils.search_pipeline_compat")
        print("Project search compatibility layer: OK")
    except Exception as exc:
        errors.append(f"search compatibility layer failed to import: {exc}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"- {error}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")
    if errors:
        return 1

    print("\nEnvironment check passed with the warnings shown above." if warnings else "\nEnvironment check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
