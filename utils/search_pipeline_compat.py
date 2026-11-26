"""Project-owned compatibility wrapper for the CRAG-MM search pipeline.

cragmm-search-pipeline 0.5.1 assumes that image search is always enabled.
That breaks the supported web-only mode because it tries to load CLIP with a
``None`` model name and later passes ``model=None`` to Transformers' Pipeline.

Keeping the workaround here makes it survive virtual-environment rebuilds.
The retrieval and post-processing behavior still comes from the upstream
``UnifiedSearchPipeline``; only initialization is overridden.
"""

from __future__ import annotations

import time
from typing import Optional

import torch
from cragmm_search.image_search_mock_api.image_kg import CragImageKG
from cragmm_search.search import UnifiedSearchPipeline as _UpstreamSearchPipeline
from cragmm_search.utils import load_from_hf
from cragmm_search.web_search_mock_api.api.web_index import CragMockWeb
from transformers import AutoModel, AutoTokenizer, CLIPModel, CLIPProcessor, Pipeline


class UnifiedSearchPipeline(_UpstreamSearchPipeline):
    """Upstream pipeline with reliable web-only and image-only initialization."""

    def __init__(
        self,
        image_model_name: Optional[str],
        image_hf_dataset_id: Optional[str],
        image_hf_dataset_tag: Optional[str] = None,
        text_model_name: Optional[str] = None,
        web_hf_dataset_id: Optional[str] = None,
        web_hf_dataset_tag: Optional[str] = None,
        web_hf_dataset_id_private: Optional[str] = None,
        report_timings: bool = False,
        **kwargs,
    ) -> None:
        total_init_started = time.perf_counter()
        self.timings: dict[str, float] = {}
        self.report_timings = report_timings

        def record_timing(name: str, started: float) -> None:
            elapsed = time.perf_counter() - started
            self.timings[name] = elapsed
            if self.report_timings:
                print(f"[retrieval timing] {name}: {elapsed:.3f}s", flush=True)

        device_name = (
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
        device = torch.device(device_name)
        print(f"Using device: {device}")

        self.web_search = (
            web_hf_dataset_id is not None or web_hf_dataset_id_private is not None
        )
        self.is_private = web_hf_dataset_id_private is not None
        self.text_model = None
        self.text_tokenizer = None
        self.text_web = None

        if self.web_search:
            if not text_model_name:
                raise ValueError("text_model_name is required when web search is enabled")
            phase_started = time.perf_counter()
            self.text_model = AutoModel.from_pretrained(text_model_name).to(device)
            self.text_tokenizer = AutoTokenizer.from_pretrained(text_model_name)
            record_timing("web_model_load_seconds", phase_started)

            phase_started = time.perf_counter()
            self.text_web = CragMockWeb(
                self.text_model,
                self.text_tokenizer,
                web_hf_dataset_id,
                web_hf_dataset_tag,
            )
            record_timing("web_index_open_seconds", phase_started)
            if self.is_private:
                phase_started = time.perf_counter()
                self.web_content_private = load_from_hf(web_hf_dataset_id_private)
                record_timing("private_web_content_load_seconds", phase_started)

        self.image_search = image_hf_dataset_id is not None
        image_model = None
        image_processor = None
        self.crag_image_kg = None
        self.image_collection = None

        if self.image_search:
            if not image_model_name:
                raise ValueError(
                    "image_model_name is required when image search is enabled"
                )
            phase_started = time.perf_counter()
            image_model = CLIPModel.from_pretrained(image_model_name).to(device)
            image_processor = CLIPProcessor.from_pretrained(image_model_name)
            record_timing("image_model_load_seconds", phase_started)

            phase_started = time.perf_counter()
            self.crag_image_kg = CragImageKG(
                image_model,
                image_processor,
                image_hf_dataset_id,
                image_hf_dataset_tag,
            )
            self.image_collection = self.crag_image_kg.vector_db
            record_timing("image_index_open_seconds", phase_started)

        if not self.web_search and not self.image_search:
            raise ValueError("At least one of web search or image search must be enabled")

        base_model = image_model if image_model is not None else self.text_model
        phase_started = time.perf_counter()
        Pipeline.__init__(
            self,
            model=base_model,
            framework="pt",
            device=device,
            **kwargs,
        )
        record_timing("pipeline_init_seconds", phase_started)
        self.device = device
        self.image_model = image_model
        self.image_processor = image_processor
        record_timing("total_init_seconds", total_init_started)
