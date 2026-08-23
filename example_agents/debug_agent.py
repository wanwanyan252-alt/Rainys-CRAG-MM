import sys
from typing import Any
from PIL import Image
from .base_agent import BaseAgent

# Fix Windows GBK encoding issues when printing RAG context with special chars
_stdout_enc = sys.stdout.encoding or 'utf-8'


def _safe_str(s):
    """Replace characters that can't be encoded in the console code page."""
    return str(s).encode(_stdout_enc, errors='replace').decode(_stdout_enc)


class DebugAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__()
        print("Initializing DebugAgent - inspect inputs only")

    def get_batch_size(self) -> int:
        return 1

    def batch_generate_response(
        self,
        queries: list[str],
        images: list[Image.Image],
        message_histories: list[list[dict[str, Any]]],
        rag_context_list: list[str],
        **kwargs,
    ) -> list[str]:
        domains = kwargs.get("domains", [])

        for i, query in enumerate(queries):
            print("\n========== DEBUG SAMPLE ==========")
            print("Query:", _safe_str(query))
            print("Domain:", _safe_str(domains[i] if i < len(domains) else None))
            print("Has image:", images[i] is not None)
            print("History:", _safe_str(message_histories[i]))
            print("RAG context:", _safe_str(rag_context_list[i] if rag_context_list[i] else "[EMPTY]"))
            print("==================================\n")

        return ["I don't know" for _ in queries]