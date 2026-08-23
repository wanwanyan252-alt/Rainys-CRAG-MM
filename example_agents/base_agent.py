# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

from abc import abstractmethod
from typing import Any, TypeAlias

from PIL import Image
from utils.utils import resize_image_if_needed

from .prompt_constants import SYSTEM_MULTI_PROMPT, SYSTEM_PROMPT


Message: TypeAlias = dict[str, Any]
Messages: TypeAlias = list[Message]


class BaseAgent:
    """
    BaseAgent 是所有 CRAG-MM 基准智能体的抽象基类。

    任何 CRAG-MM 基准智能体实现都应继承此类并实现必需方法。
    智能体负责生成用户查询的回答，并可使用图像和对话历史作为上下文。

    CRAG-MM 评测框架会在单轮和多轮对话任务上评测智能体。
    """

    def __init__(self, **kwargs: Any):
        pass

    @abstractmethod
    def get_batch_size(self) -> int:
        """
        确定评测器调用 batch_generate_response 时使用的批大小。

        评测器使用该值决定每个批次发送多少查询。
        有效值为 1 到 16 之间的整数。

        返回:
            int: 批大小，表示单个批次中应一起处理多少个查询。
        """
        raise NotImplementedError("Subclasses must implement this method")

    def _build_text_content(self, text: str) -> Any:
        return text

    def _build_image_content(self, image: Image.Image) -> Any:
        raise NotImplementedError("Subclasses must implement this method")

    def _build_message(self, role: str, content: Any) -> Message:
        return {"role": role, "content": content}

    def _add_message(self, messages: Messages, message: Message) -> None:
        messages.append(message)

    def _add_system_message(self, messages: Messages, content: str) -> None:
        self._add_message(messages, self._build_message("system", content))

    def _add_user_message(self, messages: Messages, content: Any) -> None:
        self._add_message(messages, self._build_message("user", content))

    def _add_user_text_message(self, messages: Messages, content: str) -> None:
        self._add_user_message(messages, self._build_text_content(content))

    def _prepare_messages(
        self,
        query: str,
        image: Image.Image,
        history: Messages,
        rag_context: str | None = None,
        resize_image: bool = False,
    ) -> Messages:
        """按标准顺序准备消息：系统提示、图像、RAG、历史记录、查询。"""
        messages: Messages = []
        # 1. 系统提示在 API 调用中单独处理
        system_prompt = SYSTEM_MULTI_PROMPT if history else SYSTEM_PROMPT
        self._add_system_message(messages, self._build_text_content(system_prompt))
        # 2. 图像（如有）
        if image is not None:
            if resize_image:
                image = resize_image_if_needed(
                    image, max_size_mb=5.0, max_dimension_px=8000
                )
            self._add_user_message(messages, self._build_image_content(image))
        # 3. RAG 上下文（如有）
        if rag_context:
            self._add_user_text_message(messages, rag_context)
        # 4. 历史记录（如有）
        if history:
            if hasattr(self, "_get_prompt_summary"):
                self._add_user_text_message(messages, "<conversation_history>")
            for message in history:
                self._add_message(messages, message)
            if hasattr(self, "_get_prompt_summary"):
                self._add_user_text_message(messages, "</conversation_history>")
        # 5. 给 VlmAgent 的关键消息
        if hasattr(self, "_get_prompt_summary"):
            self._add_user_text_message(
                messages, self._get_prompt_summary(rag_context, history)
            )
        # 6. 查询
        self._add_user_text_message(messages, query)
        return messages

    @abstractmethod
    def batch_generate_response(
        self,
        queries: list[str],
        images: list[Image.Image],
        message_histories: list[Messages],
        rag_context_list: list[str],
        **kwargs,
    ) -> list[str]:
        """
        为一批查询生成回答。

        这是评测器调用的主方法。它会并行处理多个查询以提升效率。
        对于多轮对话，message_histories 参数包含截至当前的对话内容。

        参数:
            queries (list[str]): 用户问题或提示列表。
            images (list[Image.Image]): PIL Image 对象列表，每个查询对应一个。
                评测器会确保仅包含 image_url 的数据集行已填充关联图像。
            message_histories (list[list[dict[str, Any]]]): 对话历史列表，
                每个查询对应一条历史。每条历史都是消息字典列表，
                包含 'role' 和 'content' 键，格式如下：

                - 单轮对话：空列表 []
                - 多轮对话：此前消息轮次列表，格式为：
                    [
                        {"role": "user", "content": "first user message"},
                        {"role": "assistant", "content": "first assistant response"},
                        {"role": "user", "content": "follow-up question"},
                        {"role": "assistant", "content": "follow-up response"},
                        ...
                    ]
            rag_context_list (list[str]): 包含已检索图像搜索和/或网页搜索结果的额外提示。

        返回:
            list[str]: 生成的回答列表，每个输入查询对应一个回答。
        """
        raise NotImplementedError("Subclasses must implement this method")
