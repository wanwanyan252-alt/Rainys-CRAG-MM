"""Small independent cross-encoder reranker for CRAG-MM web snippets."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class CrossEncoderWebReranker:
    def __init__(
        self,
        model_name_or_path: str | Path,
        device: str = "cpu",
        batch_size: int = 16,
        max_length: int = 512,
    ) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.device = torch.device(device)
        self.batch_size = batch_size
        self.max_length = max_length
        model_path = str(model_name_or_path)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()

    def rank(
        self,
        query: str,
        search_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not query or len(search_results) < 2:
            return search_results
        passages = [
            f"{result.get('page_name', '')}\n{result.get('page_snippet', '')}"
            for result in search_results
        ]
        scores: list[float] = []
        with self.torch.inference_mode():
            for start in range(0, len(passages), self.batch_size):
                batch = passages[start : start + self.batch_size]
                features = self.tokenizer(
                    [query] * len(batch),
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                )
                features = {
                    key: value.to(self.device) for key, value in features.items()
                }
                logits = self.model(**features).logits.squeeze(-1)
                scores.extend(float(value) for value in logits.detach().cpu())
        ranked = sorted(
            zip(search_results, scores), key=lambda item: item[1], reverse=True
        )
        output = []
        for result, score in ranked:
            annotated = dict(result)
            annotated["reranker_score"] = round(score, 6)
            output.append(annotated)
        return output
