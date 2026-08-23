from typing import Any
from PIL import Image
from .base_agent import BaseAgent


class IdkAgent(BaseAgent):
    def __init__(self, **kwargs: Any):
        super().__init__()
        print("Initializing IdkAgent - conservative baseline")

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
        return ["I don't know" for _ in queries]