# P5 LoRA Adapter

Base model: `Llama-3.2-11B-Vision-Instruct`

Training:

- 4-bit NF4 QLoRA;
- rank 16, alpha 32, dropout 0.05;
- 2 epochs, 136 optimizer steps;
- train loss 0.6608, eval loss 0.5792;
- vision encoder frozen.

Adapter SHA-256:

```text
763eb3b1adee0f7aa1ff163a2a0db3d1f2961ae76052be9686157055efdbde7b
```

The `.safetensors` file is stored with Git LFS.

See `docs/p5_qlora_completion_2026-11-25.md` and
`docs/final_multiquery_reranker_completion_2026-11-25.md`.
