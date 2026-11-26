"""Environment-driven vLLM runtime configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    value = int(os.environ.get(name, default))
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}, got {value}")
    return value


def _env_float(name: str, default: float) -> float:
    value = float(os.environ.get(name, default))
    if not 0 < value <= 1:
        raise ValueError(f"{name} must be in (0, 1], got {value}")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    if raw.lower() in {"1", "true", "yes", "on"}:
        return True
    if raw.lower() in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value, got {raw!r}")


@dataclass(frozen=True)
class VllmRuntimeConfig:
    tensor_parallel_size: int
    gpu_memory_utilization: float
    max_model_len: int
    max_num_seqs: int
    batch_size: int
    max_generation_tokens: int
    dtype: str
    enforce_eager: bool

    @classmethod
    def from_env(cls, visible_gpu_count: int) -> "VllmRuntimeConfig":
        default_parallel_size = max(1, visible_gpu_count)
        max_num_seqs = _env_int("VLLM_MAX_NUM_SEQS", 2)
        return cls(
            tensor_parallel_size=_env_int(
                "VLLM_TENSOR_PARALLEL_SIZE", default_parallel_size
            ),
            gpu_memory_utilization=_env_float(
                "VLLM_GPU_MEMORY_UTILIZATION", 0.85
            ),
            max_model_len=_env_int("VLLM_MAX_MODEL_LEN", 30000),
            max_num_seqs=max_num_seqs,
            batch_size=_env_int("VLLM_AGENT_BATCH_SIZE", max_num_seqs),
            max_generation_tokens=_env_int("VLLM_MAX_GENERATION_TOKENS", 1000),
            dtype=os.environ.get("VLLM_DTYPE", "bfloat16"),
            enforce_eager=_env_bool("VLLM_ENFORCE_EAGER", True),
        )

    def validate_visible_gpus(self, visible_gpu_count: int) -> None:
        if visible_gpu_count < 1:
            raise RuntimeError(
                "No CUDA GPU is visible. Open-source VLM agents require a CUDA "
                "cloud runtime; use debug/rule/idk agents on the local CPU environment."
            )
        if self.tensor_parallel_size > visible_gpu_count:
            raise RuntimeError(
                "VLLM_TENSOR_PARALLEL_SIZE exceeds the number of visible CUDA GPUs: "
                f"{self.tensor_parallel_size} > {visible_gpu_count}"
            )
