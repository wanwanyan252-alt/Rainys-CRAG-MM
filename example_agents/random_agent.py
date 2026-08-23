# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

import random
import string
from typing import Any

from PIL import Image

from .base_agent import BaseAgent


class RandomAgent(BaseAgent):
    """
    RandomAgent 是一个参考实现，用于展示 CRAG-MM 基准期望的接口。

    该智能体返回随机字符串作为回答，可作为理解智能体接口的基线。
    在真实实现中，应将其替换为能基于查询、图像和对话历史生成有意义回答的模型。

    该智能体接口设计为与 CRAG-MM 评测框架配合使用，
    后者会在单轮和多轮对话任务上评测智能体。
    """

    def __init__(self, **kwargs: Any):
        """
        初始化 RandomAgent。
        """
        super().__init__()
        print("Initializing RandomAgent - reference implementation")

    def get_batch_size(self) -> int:
        """
        确定评测器调用 batch_generate_response 时使用的批大小。

        评测器使用该值决定每个批次发送多少查询。
        有效值为 1 到 16 之间的整数。

        返回:
            int: 批大小，表示单个批次中应一起处理多少个查询。
        """
        # 该参考实现固定使用 16 作为批大小
        # 可根据智能体能力进行调整
        return 16

    def batch_generate_response(
        self,
        queries: list[str],
        images: list[Image.Image],
        message_histories: list[list[dict[str, Any]]],
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
        # 为了演示，此随机智能体只会生成随机字符串
        # 真实实现通常会：
        # 1. 必要时使用 self.search_pipeline 检索相关信息
        # 2. 处理每个查询及其对应图像（如有）
        # 3. 在多轮任务中考虑对话历史
        # 4. 基于检索信息生成有意义的回答

        return [
            "".join(
                random.choice(string.ascii_letters + " ")
                for _ in range(random.randint(2, 16))
            )
            for _ in range(len(queries))
        ]
