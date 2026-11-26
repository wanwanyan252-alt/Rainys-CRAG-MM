# Cloud CUDA runtime

This environment is separate from the Windows `.venv-light` environment. Its
first goal is one image/question response without retrieval; do not start a
full benchmark until that smoke test passes.

## Baseline assumptions

- Linux x86_64 with an NVIDIA CUDA GPU.
- Python 3.10 for the existing `vllm==0.10.1.1` stack.
- Enough GPU memory for the selected model and configured context length.
- Hugging Face access to the selected model. The existing default Llama model
  may require accepting its license and authenticating with Hugging Face.

The repository keeps `meta-llama/Llama-3.2-11B-Vision-Instruct` as its initial
compatibility baseline. This is not a claim that it is the best current model.

## Install

```bash
python3.10 -m venv .venv-cloud
source .venv-cloud/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-cloud.txt
```

Confirm CUDA before downloading model weights:

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.device_count())"
```

## Runtime configuration

All vLLM settings can be changed without editing source code:

```bash
export VLLM_TENSOR_PARALLEL_SIZE=1
export VLLM_GPU_MEMORY_UTILIZATION=0.85
export VLLM_MAX_MODEL_LEN=8192
export VLLM_MAX_NUM_SEQS=1
export VLLM_AGENT_BATCH_SIZE=1
export VLLM_MAX_GENERATION_TOKENS=128
export VLLM_DTYPE=bfloat16
export VLLM_ENFORCE_EAGER=true
```

The first smoke run intentionally uses a shorter context and batch size of one
to reduce memory risk. Increase them only after measuring peak GPU memory.

## First VLM smoke test

Use a local JPEG or PNG already present on the server:

```bash
python tools/smoke_vlm.py \
  --image /absolute/path/to/test-image.jpg \
  --query "What is the main subject in this image?" \
  --max-tokens 128
```

Success means the model loads, accepts one image, formats the prompt, and
returns non-empty text. It does not validate retrieval or benchmark quality.

## Staged integration

After the no-retrieval smoke test passes:

1. Run one evaluation sample with both search APIs suppressed.
2. Enable image retrieval only.
3. Enable web retrieval only and record index-open latency.
4. Enable both retrieval sources.
5. Run a fixed small slice before any full evaluation.

For retrieval timing, use:

```bash
python tools/benchmark_retrieval.py --mode web --hf-home /path/to/hf_cache --offline
```

The tool prints model-load and index-open timings as each phase completes, so a
slow large index can be distinguished from a model-loading failure.
