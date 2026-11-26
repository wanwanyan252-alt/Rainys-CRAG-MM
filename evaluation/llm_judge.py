# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

"""
用于语义评测的 LLM-as-a-Judge 实现。

本模块提供使用 OpenAI API 将智能体回答与标准答案进行语义评测的功能。
"""

import time
from typing import Tuple

from evaluation.config import MAX_API_RETRIES, MAX_EVAL_TOKENS
from evaluation.evaluation_prompt import CRAGMultiModalPrompts

from openai import OpenAI
from rich.console import Console

console = Console()


class LLMJudge:
    """用于智能体回答语义评测的 LLM-as-a-Judge。"""

    def __init__(
        self, api_key: str, model_name: str, base_url: str | None = None
    ):
        """初始化 LLM 裁判。

        参数:
            api_key: 用于身份认证的 OpenAI API key。
            model_name: 用于评测的模型名称（例如 "gpt-4o"）。
        """
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.request_extra_body = (
            {"thinking": {"type": "disabled"}}
            if base_url and "api.deepseek.com" in base_url
            else None
        )
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)
        self.prompt = CRAGMultiModalPrompts()

    def get_system_message(self) -> str:
        """获取评测器使用的系统消息。

        返回:
            结合说明和上下文示例的系统消息。
        """
        message_system = (
            self.prompt.get_instructions()
            + "\n\n"
            + self.prompt.get_in_context_examples()
        )
        return message_system

    def parse_response(self, eval_result: str) -> Tuple[bool | None, str]:
        """解析评测结果并返回 (is_correct, reason)。

        参数:
            eval_result: 来自 LLM 的评测结果。

        返回:
            (is_correct, reason) 元组，其中 is_correct 为 True/False/None，
            reason 为完整评测结果。
        """
        try:
            if "Result: WRONG" in eval_result or "WRONG" in eval_result.split("\n")[-1]:
                return (False, eval_result)
            elif (
                "Result: CORRECT" in eval_result
                or "CORRECT" in eval_result.split("\n")[-1]
            ):
                return (True, eval_result)
            else:
                return (None, eval_result)
        except Exception as e:
            return (None, eval_result)

    def attempt_api_call(
        self,
        messages: list,
        max_retries: int = MAX_API_RETRIES,
    ) -> dict[str, any] | None:
        """尝试调用 OpenAI API，并在失败时重试。

        参数:
            messages: 对话消息对象列表。
            max_retries: 放弃前的最大重试次数。

        返回:
            成功时返回包含评测结果的字典；所有尝试均失败时返回 None。
        """
        for attempt in range(max_retries):
            try:
                request_kwargs = dict(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=MAX_EVAL_TOKENS,
                )
                if self.request_extra_body:
                    request_kwargs["extra_body"] = self.request_extra_body
                completion = self.client.chat.completions.create(**request_kwargs)
                eval_result = completion.choices[0].message.content
                is_correct, reason = self.parse_response(eval_result)
                return {"accuracy": is_correct, "eval_result": reason}
            except Exception as e:
                error_message = (
                    f"API call failed on attempt {attempt + 1}/{max_retries}: {str(e)}"
                )
                if attempt == max_retries - 1:
                    console.print(
                        f"[red]Failed after {MAX_API_RETRIES} attempts: {str(e)}[/red]"
                    )
                else:
                    console.print(f"[yellow]{error_message}, retrying...[/yellow]")
                    time.sleep(2**attempt)

        return None

    def evaluate(
        self, query: str, ground_truth: str, agent_response: str
    ) -> dict[str, any] | None:
        """根据标准答案评测智能体回答。

        参数:
            query: 被询问的查询/问题。
            ground_truth: 期望的正确答案。
            agent_response: 要评测的智能体回答。

        返回:
            包含评测结果的字典；若评测失败则返回 None。
        """
        messages = [
            {"role": "system", "content": self.get_system_message()},
            {
                "role": "user",
                "content": f"Your task is to judge if the prediction is correct or not based on the ground truth answer. Now your turn:\n\nQuestion: {query}\nGround Truth: {ground_truth}\nPrediction: {agent_response}\nGive your output below:\n",
            },
        ]
        return self.attempt_api_call(messages)
