# CRAG-MM Final Release Artifacts

This directory contains the compact, Git-friendly outputs for the final system.

Included:

- final 200–599 gated results and DeepSeek comparison judgments in
  `final_outputs/`;
- final calibrated refusal gate;
- full-validation and P5 metric summaries;
- P5 training-data manifest and data card.

Excluded from normal Git history:

- CRAG-MM images and parquet shards;
- full raw RAG contexts and intermediate experiments;
- the upstream Llama base model;
- the upstream MiniLM reranker weights, which are reproducibly identified in
  `docs/final_multiquery_reranker_completion_2026-11-25.md`.

The unique P5 LoRA adapter is stored under `checkpoints/p5_lora/` using Git LFS.
