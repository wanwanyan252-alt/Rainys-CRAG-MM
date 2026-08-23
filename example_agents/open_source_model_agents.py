# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

import os
from itertools import zip_longest
from typing import Any

import torch
import vllm
from mistral_common.protocol.instruct.request import ChatCompletionRequest
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from PIL import Image
from qwen_vl_utils import process_vision_info
from transformers import AutoProcessor, AutoTokenizer
from vllm.multimodal.utils import encode_image_base64
from vllm.sampling_params import GuidedDecodingParams

from .base_agent import BaseAgent
from .prompt_constants import (
    KEY_MESSAGE_HISTORY_PROMPT,
    KEY_RAG_PROMPT,
    KEY_USER_PROMPT,
    QUERY_REWRITE_PROMPT,
    QUERY_REWRITE_STEP_1,
    QUERY_REWRITE_SYSTEM,
    QueryAnalysis,
)

# GPU 利用率设置
# 本地运行时，请根据可用 GPU 数量调整 VLLM_TENSOR_PARALLEL_SIZE
# 例如，如果服务器上有 2 张 GPU，则设置 VLLM_TENSOR_PARALLEL_SIZE=2。
# 如需使用 VLLM_TENSOR_PARALLEL_SIZE>1 进行本地评测，
# 可能需要取消下方这一行的注释。

#### 请确保提交时 VLLM_TENSOR_PARALLEL_SIZE=1。
VLLM_TENSOR_PARALLEL_SIZE = torch.cuda.device_count()

if VLLM_TENSOR_PARALLEL_SIZE > 1:
    os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

VLLM_GPU_MEMORY_UTILIZATION = 0.85

# 这些是让模型在单张 NVIDIA L40s GPU 上运行的模型专用参数
MAX_MODEL_LEN = 30000
MAX_NUM_SEQS = 2

MAX_GENERATION_TOKENS = 1000


class VlmAgent(BaseAgent):
    """使用 vllm 库加载 LLM/VLM 模型的基础智能体。"""

    def __init__(
        self,
        model_name="meta-llama/Llama-3.2-11B-Vision-Instruct",
        max_gen_len=64,
        **kwargs,
    ):
        """
        初始化智能体。

        参数:
            model_name (str): 用于视觉语言处理的 Hugging Face 模型名称。
            max_gen_len (int): 模型输出的最大生成长度。
        """
        super().__init__()
        self.model_name = model_name
        self.max_gen_len = max_gen_len

        self.llm = self._initialize_models()
        self.tokenizer = self._get_tokenizer()
        self.sampling_params = self._get_sampling_params()

    def _get_tokenizer(self):
        return AutoTokenizer.from_pretrained(self.model_name)

    def _initialize_models(self):
        """使用适当设置初始化 vLLM 模型和分词器。"""
        # 使用 vLLM 初始化模型
        return vllm.LLM(
            self.model_name,
            tensor_parallel_size=VLLM_TENSOR_PARALLEL_SIZE,
            gpu_memory_utilization=VLLM_GPU_MEMORY_UTILIZATION,
            max_model_len=MAX_MODEL_LEN,
            max_num_seqs=MAX_NUM_SEQS,
            trust_remote_code=True,
            dtype="bfloat16",
            enforce_eager=True,
            limit_mm_per_prompt={"image": 1},
        )

    def get_batch_size(self) -> int:
        return 16

    def _build_image_content(self, image: Image.Image) -> list[dict[str, str]]:
        return [{"type": "image"}]

    def _get_prompt_summary(self, rag_context: str, message_history: str) -> str:
        user_prompt = ""
        if rag_context:
            user_prompt += KEY_RAG_PROMPT
        if message_history:
            user_prompt += KEY_MESSAGE_HISTORY_PROMPT
        user_prompt += KEY_USER_PROMPT
        return user_prompt

    def _process_messages(
        self, messages: list, image: Image.Image
    ) -> dict[str, str | dict[str, Image.Image]]:
        # 应用聊天模板
        formatted_prompt = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
        )
        return {
            "prompt": formatted_prompt,
            "multi_modal_data": {"image": image} if image is not None else {},
        }

    def _prepare_formatted_prompts(
        self,
        queries: list[str],
        images: list[Image.Image],
        message_histories: list[list[dict[str, Any]]],
        rag_context_list: list[str],
    ) -> list[dict[str, str | dict[str, Image.Image]]]:
        formatted_prompts = []

        for query, image, history, rag_context in zip_longest(
            queries, images, message_histories, rag_context_list
        ):
            messages = self._prepare_messages(
                query=query, image=image, history=history, rag_context=rag_context
            )
            formatted_prompts.append(self._process_messages(messages, image))

        return formatted_prompts

    def _get_sampling_params(self):
        return vllm.SamplingParams(
            temperature=0,
            top_p=1,
            max_tokens=MAX_GENERATION_TOKENS,
            skip_special_tokens=True,
        )

    def batch_generate_response(
        self,
        queries: list[str],
        images: list[Image.Image],
        message_histories: list[list[dict[str, Any]]],
        rag_context_list: list[str],
        **kwargs,
    ) -> list[str]:
        """为一批查询及其关联图像生成回答。"""
        # 准备提示和图像数据
        inputs = self._prepare_formatted_prompts(
            queries, images, message_histories, rag_context_list
        )

        # 生成回答
        outputs = self.llm.generate(inputs, sampling_params=self.sampling_params)

        responses = [output.outputs[0].text for output in outputs]
        return responses


class LlamaAgent(VlmAgent):
    def _get_tokenizer(self):
        return self.llm.get_tokenizer()


class PixtralAgent(VlmAgent):
    def _initialize_models(self):
        # 使用 vLLM 初始化模型
        return vllm.LLM(
            self.model_name,
            max_model_len=MAX_MODEL_LEN,
            limit_mm_per_prompt={
                "image": 1
            },  # 在 CRAG-MM 数据集中，每个对话最多有 1 张图像
        )

    def _build_image_content(self, image: Image.Image) -> str:
        return "[IMG]"

    def _process_messages(
        self, messages: list, image: Image.Image
    ) -> dict[str, str | dict[str, Image.Image]]:
        tokenizer = MistralTokenizer.v3(is_tekken=True)
        completion_request = ChatCompletionRequest.from_openai(messages)
        prompt = tokenizer.encode_chat_completion(completion_request).text
        return {"prompt": prompt, "multi_modal_data": {"image": image}}

    def _get_sampling_params(self):
        return vllm.SamplingParams(
            temperature=0,
            top_p=1,
            max_tokens=MAX_GENERATION_TOKENS,
        )


class QwenAgent(VlmAgent):
    def _build_text_content(self, text: str) -> list[dict[str, str]]:
        return [{"type": "text", "text": text}]

    def _build_image_content(self, image: Image.Image) -> list[dict[str, str]]:
        return [
            {
                "type": "image",
                "image": f"data:image/jpeg;base64,{encode_image_base64(image)}",
                "min_pixels": 256 * 28 * 28,
                "max_pixels": 1280 * 960,
            }
        ]

    def _process_messages(
        self, messages: list, image: Image.Image
    ) -> dict[str, str | dict[str, Image.Image]]:
        processor = AutoProcessor.from_pretrained(self.model_name)
        prompt = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, _ = process_vision_info(messages)
        mm_data = {"image": image_inputs} if image_inputs is not None else {}

        return {
            "prompt": prompt,
            "multi_modal_data": mm_data,
        }


class InternVLAgent(VlmAgent):
    def _build_image_content(self, image: Image.Image) -> str:
        return "<image>"


class QueryRewrite(VlmAgent):
    def _get_tokenizer(self):
        return self.llm.get_tokenizer()

    def batch_generate_response(
        self,
        queries: list[str],
        images: list[Image.Image],
        message_histories: list[list[dict[str, Any]]],
        **kwargs,
    ) -> list[str]:
        """为一批查询及其关联图像生成回答。"""
        formatted_prompts = []
        for query in queries:
            formatted_prompt = self.tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": QUERY_REWRITE_SYSTEM},
                    {"role": "user", "content": [{"type": "image"}]},
                    {
                        "role": "user",
                        "content": QUERY_REWRITE_STEP_1.format(question=query),
                    },
                ],
                add_generation_prompt=True,
                tokenize=False,
            )
            formatted_prompts.append(formatted_prompt)

        # 创建包含多模态数据的输入列表
        inputs = [
            {"prompt": formatted_prompt, "multi_modal_data": {"image": img}}
            for img, formatted_prompt in zip(images, formatted_prompts)
        ]

        outputs = self.llm.generate(
            inputs,
            sampling_params=vllm.SamplingParams(
                temperature=0,
                top_p=1,
                max_tokens=MAX_GENERATION_TOKENS,
                skip_special_tokens=True,
            ),
        )

        analysis_responses = [output.outputs[0].text for output in outputs]

        # 第二阶段：格式化输出
        prompts = []
        for query, response in zip(queries, analysis_responses):
            prompt = self.tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": QUERY_REWRITE_SYSTEM},
                    {"role": "user", "content": [{"type": "image"}]},
                    {
                        "role": "user",
                        "content": QUERY_REWRITE_STEP_1.format(question=query),
                    },
                    {"role": "assistant", "content": response},
                    {
                        "role": "user",
                        "content": QUERY_REWRITE_PROMPT.format(question=query),
                    },
                ],
                add_generation_prompt=True,
                tokenize=False,
            )
            prompts.append(prompt)

        # 生成回答
        json_schema = QueryAnalysis.model_json_schema()
        guided_decoding_params_json = GuidedDecodingParams(json=json_schema)
        outputs = self.llm.generate(
            prompts,
            sampling_params=vllm.SamplingParams(
                guided_decoding=guided_decoding_params_json,
                temperature=0,
                top_p=1,
                max_tokens=MAX_GENERATION_TOKENS,
                skip_special_tokens=True,
            ),
        )

        responses = [output.outputs[0].text for output in outputs]
        return responses
