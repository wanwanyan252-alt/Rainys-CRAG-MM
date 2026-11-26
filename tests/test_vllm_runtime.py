import os
import unittest
from unittest.mock import patch

from example_agents.vllm_runtime import VllmRuntimeConfig


class VllmRuntimeConfigTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_defaults_follow_visible_gpu_count(self):
        config = VllmRuntimeConfig.from_env(visible_gpu_count=2)
        self.assertEqual(config.tensor_parallel_size, 2)
        self.assertEqual(config.batch_size, config.max_num_seqs)
        self.assertEqual(config.max_generation_tokens, 1000)

    @patch.dict(
        os.environ,
        {
            "VLLM_TENSOR_PARALLEL_SIZE": "1",
            "VLLM_GPU_MEMORY_UTILIZATION": "0.7",
            "VLLM_MAX_MODEL_LEN": "8192",
            "VLLM_MAX_NUM_SEQS": "3",
            "VLLM_AGENT_BATCH_SIZE": "2",
            "VLLM_MAX_GENERATION_TOKENS": "128",
            "VLLM_DTYPE": "float16",
            "VLLM_ENFORCE_EAGER": "false",
        },
        clear=True,
    )
    def test_environment_overrides(self):
        config = VllmRuntimeConfig.from_env(visible_gpu_count=4)
        self.assertEqual(config.tensor_parallel_size, 1)
        self.assertEqual(config.gpu_memory_utilization, 0.7)
        self.assertEqual(config.max_model_len, 8192)
        self.assertEqual(config.max_num_seqs, 3)
        self.assertEqual(config.batch_size, 2)
        self.assertEqual(config.max_generation_tokens, 128)
        self.assertEqual(config.dtype, "float16")
        self.assertFalse(config.enforce_eager)

    @patch.dict(os.environ, {}, clear=True)
    def test_no_gpu_has_clear_runtime_error(self):
        config = VllmRuntimeConfig.from_env(visible_gpu_count=0)
        with self.assertRaisesRegex(RuntimeError, "No CUDA GPU"):
            config.validate_visible_gpus(0)

    @patch.dict(
        os.environ, {"VLLM_TENSOR_PARALLEL_SIZE": "2"}, clear=True
    )
    def test_parallel_size_cannot_exceed_visible_gpus(self):
        config = VllmRuntimeConfig.from_env(visible_gpu_count=1)
        with self.assertRaisesRegex(RuntimeError, "exceeds"):
            config.validate_visible_gpus(1)

    @patch.dict(
        os.environ, {"VLLM_GPU_MEMORY_UTILIZATION": "1.1"}, clear=True
    )
    def test_invalid_memory_utilization_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be in"):
            VllmRuntimeConfig.from_env(visible_gpu_count=1)


if __name__ == "__main__":
    unittest.main()
