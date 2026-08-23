# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

import os
import time
from abc import abstractmethod
from concurrent.futures import as_completed, ThreadPoolExecutor
from itertools import zip_longest
from typing import Any

import openai
from anthropic import Anthropic
from google.generativeai import GenerativeModel, configure
from PIL import Image
from vllm.multimodal.utils import encode_image_base64

from .base_agent import BaseAgent, Message, Messages
from .prompt_constants import SYSTEM_MULTI_PROMPT, SYSTEM_PROMPT


class ClosedModelBaseAgent(BaseAgent):
    """
    封闭模型智能体（Claude、Gemini、GPT）的基类，包含通用功能。
    """

    def __init__(self, model_name: str, **kwargs):
        super().__init__(**kwargs)
        self.model_name = model_name
        api_key = os.environ.get(self.api_key_env_var, None)
        if api_key is None:
            raise ValueError(f"{self.api_key_env_var} environment variable is not set!")
        self._setup_client(api_key)

    @property
    @abstractmethod
    def api_key_env_var(self) -> str:
        """获取 API key 对应的环境变量名。"""
        pass

    @abstractmethod
    def _setup_client(self, api_key: str):
        """为特定模型提供方设置 API 客户端。"""
        pass

    def _build_image_content(self, image: Image.Image) -> list[dict[str, Any]]:
        """按模型提供方期望的格式生成图像内容。"""
        return [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encode_image_base64(image)}"
                },
            }
        ]

    @abstractmethod
    def _make_api_call(self, messages: Any) -> str:
        """调用模型提供方的 API。"""
        pass

    def get_batch_size(self) -> int:
        return 16

    def batch_generate_response(
        self,
        queries: list[str],
        images: list[Image.Image],
        message_histories: list[Messages],
        rag_context_list: list[str],
        **kwargs,
    ) -> list[str]:
        """
        为一批查询及其关联图像生成 RAG 增强回答。
        """
        responses = [None] * len(queries)  # 预分配回答列表

        def process_single_query(idx, query, image, history, rag_context):
            """结合 RAG 上下文处理单个查询。"""
            try:
                messages = self._prepare_messages(query, image, history, rag_context)

                # 使用优化后的重试逻辑和指数退避进行 API 调用
                last_exception = None
                # 指数退避延迟：0.1s、0.5s
                retry_delays = [0.1, 0.5]
                for attempt in range(3):
                    try:
                        response = self._make_api_call(messages)
                        return idx, response
                    except Exception as e:
                        error_str = str(e)
                        # 检查是否为图像大小错误
                        if (
                            isinstance(self, ClaudeAgent)
                            and "image exceeds" in error_str.lower()
                        ):
                            print(f"Claude API image size error: {error_str}")
                            # 若仍有原始查询参数，则使用缩放后的图像重试
                            print("Retrying with resized image...")
                            messages = self._prepare_messages(
                                query,
                                image,
                                history,
                                rag_context,
                                resize_image=True,
                            )
                            try:
                                response = self._make_api_call(messages)
                            except Exception as resize_e:
                                print(
                                    "Claude API error even after resizing: "
                                    f"{str(resize_e)}"
                                )
                                last_exception = resize_e
                                break
                        else:
                            print(f"API error (attempt {attempt + 1}/3): {e}")
                            last_exception = e
                            if attempt < 2:  # 最后一次尝试失败时不再等待
                                time.sleep(retry_delays[attempt])
                return (
                    idx,
                    f"[API error after 3 attempts: {str(last_exception)[:100]}...]",
                )
            except Exception as e:
                print(f"Error processing query {idx}: {e}")
                return idx, f"[Error processing query: {e}]"

        # 使用优化后的 ThreadPoolExecutor 并发执行 API 调用
        # 根据批大小确定并发数（批大小的 25%，最小 1，最大 8）
        batch_size = self.get_batch_size()
        max_workers = max(
            1,
            min(
                batch_size // 4,  # 批大小的 25%
                8,  # 上限为 8，避免 API 过载
                len(queries),  # 不创建超过查询数量的工作线程
            ),
        )
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_idx = {
                executor.submit(
                    process_single_query, idx, query, image, history, rag_context
                ): idx
                for idx, (query, image, history, rag_context) in enumerate(
                    zip_longest(queries, images, message_histories, rag_context_list)
                )
            }

            # 在任务完成时收集结果并跟踪进度
            for future in as_completed(future_to_idx):
                try:
                    idx, response = future.result(
                        timeout=120
                    )  # 每个查询 2 分钟超时
                    responses[idx] = response
                except Exception as e:
                    idx = future_to_idx[future]
                    responses[idx] = f"[Timeout or error: {e}]"

        return responses


class ClaudeAgent(ClosedModelBaseAgent):
    """
    Anthropic Claude 模型（Claude 3 系列等）的智能体。
    """

    def __init__(self, model_name: str = "claude-3-7-sonnet-latest", **kwargs):
        super().__init__(model_name, **kwargs)

    @property
    def api_key_env_var(self) -> str:
        """Anthropic API key 的环境变量名。"""
        return "ANTHROPIC_API_KEY"

    def _setup_client(self, api_key: str):
        """设置 Claude API 客户端。"""
        self.client = Anthropic(api_key=api_key)

    def _build_image_content(self, image: Image.Image) -> list[dict[str, Any]]:
        """按模型提供方期望的格式生成图像内容。"""
        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encode_image_base64(image),
                },
            }
        ]

    def _make_api_call(self, messages: list[dict]) -> str:
        """调用 Claude API。"""
        system_prompt = messages.pop(0)["content"]  # 提取系统提示
        response = self.client.messages.create(
            model=self.model_name,
            system=system_prompt,
            messages=messages,
            temperature=0.0,
            top_p=1.0,
            max_tokens=2048,
        )
        content = response.content
        if isinstance(content, list):
            return " ".join([c.text for c in content if c.type == "text"])
        else:
            return str(content)


class GeminiAgent(ClosedModelBaseAgent):
    """
    Google Gemini 模型（Gemini Pro、Gemini 2.5 Flash 等）的智能体。
    """

    def __init__(
        self, model_name: str = "gemini-2.5-flash", is_multi_turn: bool = False
    ):
        self.is_multi_turn = is_multi_turn
        super().__init__(model_name)

    @property
    def api_key_env_var(self) -> str:
        """Google API key 的环境变量名。"""
        return "GOOGLE_API_KEY"

    def _setup_client(self, api_key: str):
        """设置 Gemini API 客户端。"""
        configure(api_key=api_key)
        self.model = GenerativeModel(
            self.model_name,
            system_instruction=(
                f"{SYSTEM_MULTI_PROMPT if self.is_multi_turn else SYSTEM_PROMPT}"
                "\n\nIf the content appears to be from copyrighted sources (like "
                "Wikipedia), explain or summarize the idea instead of quoting "
                "directly."
            ),
        )

    def _build_text_content(self, text: str) -> dict[str, str]:
        return {"text": text}

    def _build_image_content(self, image: Image.Image) -> dict[str, dict[str, str]]:
        return {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": encode_image_base64(image),
            }
        }

    def _add_system_message(self, messages: Messages, content: str) -> None:
        pass

    def _add_message(self, messages: Messages, message: Message) -> None:
        role = "model" if message["role"] == "assistant" else "user"
        if messages and messages[-1]["role"] == role:
            # 追加到已有内容块
            messages[-1]["parts"].append(message["content"])
        else:
            # 创建新的内容块
            messages.append({"role": role, "parts": [message["content"]]})

    def _make_api_call(self, messages: Messages) -> str:
        """调用 Gemini API，并稳健处理 finish_reason。"""
        response = self.model.generate_content(
            contents=messages,
            generation_config={
                "temperature": 0.0,
                "top_p": 1.0,
                "top_k": 1,
            },
        )
        # 稳健检查首个候选项的 finish_reason
        candidate = None
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason == 4:
                return "[Gemini API blocked response due to copyrighted material.]"
        # 若没有有效的 Part/text，则返回回退值
        if not hasattr(response, "text") or not response.text:
            return "[Gemini API returned no valid text part.]"
        return response.text


class GPTAgent(ClosedModelBaseAgent):
    """
    OpenAI GPT 模型（GPT-4o、GPT-5、GPT-5-thinking、GPT-5-mini）的智能体。
    """

    def __init__(self, model_name: str = "gpt-5-mini", **kwargs):
        super().__init__(model_name, **kwargs)

    @property
    def api_key_env_var(self) -> str:
        """OpenAI API key 的环境变量名。"""
        return "OPENAI_API_KEY"

    def _setup_client(self, api_key: str):
        """设置 OpenAI API 客户端。"""
        self.client = openai.OpenAI(api_key=api_key)

    def _make_api_call(self, messages: list[dict]) -> str:
        """调用 GPT API。"""
        if self.model_name.startswith("gpt-5"):
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                top_p=1.0,
                n=1,
            )
        else:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.0,
                top_p=1.0,
                n=1,
            )
        return response.choices[0].message.content


class LlamaClosedAgent(ClosedModelBaseAgent):
    """
    通过 wearables API 使用 Llama 模型的智能体。
    """

    def __init__(self, model_name: str = "llama3.2-90b-instruct", **kwargs):
        super().__init__(model_name, **kwargs)

    @property
    def api_key_env_var(self) -> str:
        """Wearables API key 的环境变量名。"""
        return "WEARABLES_API_KEY"

    def _setup_client(self, api_key: str):
        """设置 OpenAI API 客户端。"""
        self.client = openai.OpenAI(
            api_key=api_key, base_url="https://api.wearables-ape.io/models/v1"
        )

    def _make_api_call(self, messages: list[dict]) -> str:
        """调用 GPT API。"""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0,
            top_p=1.0,
            n=1,
        )
        return response.choices[0].message.content

    def get_batch_size(self) -> int:
        return 1
