# Local development and recovery

The local Windows environment is intended for dataset, retrieval, evaluation,
and lightweight-agent debugging. A CUDA cloud environment is required for the
full open-source VLM agents.

Install this environment with `python -m pip install -r requirements.txt` (or
`requirements-local.txt` directly). Do not install `requirements-cloud.txt` on
Windows; vLLM belongs in the separate Linux/CUDA environment.

## Verify the environment

From the repository root in PowerShell:

```powershell
.\.venv-light\Scripts\python.exe tools\check_environment.py
.\.venv-light\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-light\Scripts\python.exe local_evaluation.py --help
```

The diagnostic returns a non-zero status when required packages or the project
compatibility layer are unavailable. `CUDA available: False` is reported as a
warning and is expected in the lightweight local environment.

## Search modes

`utils/search_pipeline_compat.py` owns the compatibility fix required by
`cragmm-search-pipeline==0.5.1`. Do not patch files under `.venv-light`.

- Web only: pass `--suppress-image-search-api`.
- Image only: pass `--suppress-web-search-api`.
- Web and image: pass neither suppression flag.
- No retrieval: pass both suppression flags.

Set the Hugging Face cache variables before a real retrieval run so the known
working indexes are used:

```powershell
$env:HF_HOME = "D:\CODE\hf_cache"
$env:HF_HUB_CACHE = "D:\CODE\hf_cache\hub"
$env:HF_DATASETS_CACHE = "D:\CODE\hf_cache\datasets"
$env:OPENAI_API_KEY = "dummy"
$env:MAX_BATCH_SIZE = "1"
```

Use `--eval-model None` for an offline smoke run. That mode only performs exact
matching; its score must not be treated as semantic answer quality.

## Retrieval timing

The public web index is large enough that initialization can appear stalled.
Use the phase-timing tool instead of an uninstrumented evaluation run:

```powershell
.\.venv-light\Scripts\python.exe tools\benchmark_retrieval.py `
  --mode web `
  --hf-home D:\CODE\hf_cache `
  --offline
```

It prints model-load and index-open durations immediately after each phase.

On 2026-11-17, the cached image index completed an offline initialization on
the current CPU machine in 13.28 seconds (1.30 seconds model load and 11.97
seconds index open). The much larger web index should be measured separately.
