# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

"""
CRAG-MM 数据集处理模块

本模块提供处理和批量化 CRAG-MM 数据集的工具。
该数据集包含带有图像和文本的多轮对话。

主要组件：
1. CRAGTurnBatchIterator - 将数据集处理为对话轮次的批次
2. ImageLoader - 处理来自各种来源的图像加载
3. 用于调试和演示的主执行代码
"""

import random
from typing import Any

import tqdm
from datasets import Dataset, load_dataset
from loguru import logger
from PIL import Image
from .utils import download_image_url, parse_jsonl_to_dict


class ImageLoader:
    """处理从各种来源加载和缓存图像。"""

    @staticmethod
    def load_image(conversation_data: dict[str, Any]) -> Image.Image:
        """
        从对话数据中加载图像，必要时自动下载。

        参数:
            conversation_data: 包含图像数据或 URL 的字典

        返回:
            PIL Image 对象

        说明:
            - 数据集中会提供 'image' 或 'image_url' 之一
            - 当无法直接包含图像时，只提供 image_url
        """
        image = conversation_data.get("image")
        image_url = conversation_data.get("image_url")

        if image is None and image_url:
            # 从 URL 下载图像（带本地缓存）
            image_local_path = download_image_url(image_url)
            image = Image.open(image_local_path)

        return image


class CRAGTurnBatchIterator:
    """
    将 CRAG-MM 数据集处理为对话轮次的批次。

    本类处理 CRAG 数据集的复杂结构——该数据集包含带有图像的多轮对话，
    并将其转换为适合模型训练或评测的格式。
    """

    def __init__(
        self,
        dataset: Dataset,
        batch_size: int,
        full_query_file: str = None,
        shuffle: bool = False,
        sessions_to_skip: list = [],
        sessions_to_update: dict = {},
    ):
        """
        使用数据集和参数初始化批处理器。

        参数:
            dataset: 包含 CRAG 对话的 HuggingFace 数据集
            batch_size: 每个批次包含的对话轮次数量
            shuffle: 是否打乱对话顺序
        """
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.indices = list(range(len(dataset)))
        self.sessions_to_skip = sessions_to_skip
        self.sessions_to_update = sessions_to_update
        self.full_query_map = parse_jsonl_to_dict(full_query_file)

        if self.shuffle:
            random.shuffle(self.indices)

    def _extract_turn_data(
        self,
        conversation: dict[str, Any],
        turn_idx: int,
        turn: dict[str, Any],
        session_id: str,
        image: Image.Image,
        image_url: str,
        image_quality: str,
        answer_lookup: dict[str, str],
        total_turn_count: int,
    ) -> dict[str, Any]:
        """
        提取单个对话轮次的数据。

        参数:
            conversation: 完整的对话数据
            turn_idx: 当前轮次的索引
            turn: 当前轮次的数据
            session_id: 对话会话 ID
            image: 与对话关联的图像
            image_url: 图像的 URL
            image_quality: 图像质量评级
            answer_lookup: 将 interaction_id 映射到答案的字典
            total_turn_count: 对话中的总轮次数

        返回:
            包含已处理轮次数据的字典
        """
        # 提取基本轮次信息
        interaction_id = turn["interaction_id"]
        query = turn["query"]
        query_category = turn["query_category"]
        domain = turn["domain"]
        dynamism = turn["dynamism"]

        # 获取标准答案
        answer = answer_lookup.get(interaction_id, False)
        assert (
            answer is not False
        ), f"No answer found for interaction_id: {interaction_id}"

        # 提取到当前轮次为止的对话历史
        conversation_history = []
        answer_history = []
        if turn_idx > 0:
            conversation_history = conversation["turns"][:turn_idx]
            answer_history = [
                answer_lookup.get(a["interaction_id"], False)
                for a in conversation_history
            ]
            assert all(answer_history), (
                f"No answer found for turn history of interaction_id: {interaction_id}."
                f" session_id: {session_id}"
            )

        # 对第一人称帧进行缩放
        if image_url is None or len(image_url) == 0:
            image = image.resize((960, 1280))

        # 返回结构化的轮次数据

        return {
            "session_id": session_id,
            "interaction_id": interaction_id,
            "turn_idx": turn_idx,
            "image": image,
            "image_url": image_url,
            "image_quality": image_quality,
            "full_query": self.full_query_map.get(interaction_id, ""),
            "query": query,
            "answer": answer,
            "query_category": query_category,
            "domain": domain,
            "dynamism": dynamism,
            "conversation_history": conversation_history,
            "answer_history": answer_history,
            "total_turn_count": total_turn_count,
        }

    def _collate_batch(self, batch: list[dict[str, Any]]) -> dict[str, list[Any]]:
        """
        将单个轮次数据整理为批格式。

        参数:
            batch: 包含轮次数据的字典列表

        返回:
            批量化后的数据字典
        """
        # 初始化所有字段的列表
        batch_data = {
            "session_ids": [],
            "interaction_ids": [],
            "turn_idxs": [],
            "images": [],
            "image_urls": [],
            "image_qualities": [],
            "full_queries": [],
            "queries": [],
            "answers": [],
            "query_categories": [],
            "domains": [],
            "dynamisms": [],
            "conversation_histories": [],
            "answer_histories": [],
            "total_turn_counts": [],
        }

        # 从每个条目中收集数据
        for item in batch:
            batch_data["session_ids"].append(item["session_id"])
            batch_data["interaction_ids"].append(item["interaction_id"])
            batch_data["turn_idxs"].append(item["turn_idx"])

            batch_data["images"].append(item["image"])
            batch_data["image_urls"].append(item["image_url"])
            batch_data["image_qualities"].append(item["image_quality"])

            batch_data["full_queries"].append(item["full_query"])
            batch_data["queries"].append(item["query"])
            batch_data["answers"].append(item["answer"])

            batch_data["query_categories"].append(item["query_category"])
            batch_data["domains"].append(item["domain"])
            batch_data["dynamisms"].append(item["dynamism"])

            batch_data["conversation_histories"].append(item["conversation_history"])
            batch_data["answer_histories"].append(item["answer_history"])

            batch_data["total_turn_counts"].append(item["total_turn_count"])

        return batch_data

    def __iter__(self):
        """
        遍历数据集并产出轮次批次，确保任意对话的第 N+1 轮
        只会出现在比同一对话第 N 轮更晚的批次中。

        这对多轮对话的正确批处理策略至关重要，
        但也应适用于单轮对话。
        """
        from collections import deque

        # 对每个对话，跟踪下一次要产出的轮次：
        # next_turn_idx[i] = k 表示已消费轮次 [0..k-1]。
        next_turn_idx = [0] * len(self.dataset)

        # 初始化仍有剩余轮次的对话索引队列
        queue = deque(self.indices)

        # 对话数据、图像和答案的缓存
        self.conversation_cache = {}  # conv_id -> 对话字典
        self.answer_lookup_cache = {}  # conv_id -> {interaction_id -> ans_full}
        self.image_cache = {}  # conv_id -> 已加载的 PIL 图像

        # 每次迭代都会在 'batch' 中累积轮次数据
        batch = []

        while queue:
            current_convs = []
            # 从队列中弹出对话 ID，直到达到 batch_size
            while queue and len(current_convs) < self.batch_size:
                conv_id = queue.popleft()
                current_convs.append(conv_id)

            # 对 current_convs 中每个对话仅处理一个轮次
            for conv_id in current_convs:
                if self.dataset[conv_id]["session_id"] in self.sessions_to_skip:
                    logger.warning(
                        "Skipping session {}", self.dataset[conv_id]["session_id"]
                    )
                    continue

                conv_data = self.dataset[conv_id]
                if conv_data["session_id"] in self.sessions_to_update:
                    conv_data.update(self.sessions_to_update[conv_data["session_id"]])

                # ---------------------------
                # 1) 必要时惰性加载
                # ---------------------------
                if conv_id not in self.conversation_cache:
                    # 从数据集中加载一次
                    self.conversation_cache[conv_id] = conv_data

                    # 构建答案查找表
                    # 第 2 轮数据集中的 conv_data 形式如下
                    # {
                    #     "answers": {
                    #         "ans_full": [...],
                    #         "interaction_id": [...],
                    #     },
                    #     ...
                    # }
                    # 第 1 轮数据集中的 conv_data 形式如下
                    # {
                    #     "answers": [
                    #         {
                    #             "interaction_id": ...,
                    #             "ans_full": ...,
                    #         },
                    #         ...
                    #     ],
                    #     ...
                    # }
                    if isinstance(conv_data, dict):
                        answers = []
                        for idx in range(len(conv_data["answers"]["interaction_id"])):
                            answers.append(
                                {
                                    "interaction_id": conv_data["answers"][
                                        "interaction_id"
                                    ][idx],
                                    "ans_full": conv_data["answers"]["ans_full"][idx],
                                }
                            )
                        conv_data["answers"] = answers
                    ans_lookup = {
                        a["interaction_id"]: a["ans_full"] for a in conv_data["answers"]
                    }
                    self.answer_lookup_cache[conv_id] = ans_lookup

                    # 加载并缓存图像
                    self.image_cache[conv_id] = ImageLoader.load_image(conv_data)

                # -------------------------
                # 2) 从缓存中获取
                # -------------------------
                conversation = self.conversation_cache[conv_id]
                answer_lookup = self.answer_lookup_cache[conv_id]
                image = self.image_cache[conv_id]

                # 确定需要的轮次
                # 第 2 轮数据集中的 conv_data 形式如下
                # {
                #     "turns": {
                #         "interaction_id": [...],
                #         "query": [...],
                #         ...
                #     },
                #     ...
                # }
                # 第 1 轮数据集中的 conv_data 形式如下
                # {
                #     "turns": [
                #         {
                #             "interaction_id": ...,
                #             "query": ...,
                #         },
                #         ...
                #     ],
                #     ...
                # }
                if isinstance(conversation["turns"], dict):
                    turns = []
                    for idx in range(len(conversation["turns"]["interaction_id"])):
                        _sample = {}
                        for k, v in conversation["turns"].items():
                            _sample[k] = v[idx]
                        turns.append(_sample)
                    conversation["turns"] = turns

                turn_idx = next_turn_idx[conv_id]
                total_turn_count = len(conversation["turns"])
                turn = conversation["turns"][turn_idx]

                image_url = conversation.get("image_url", None)
                image_quality = conversation.get("image_quality", None)

                # 构建单个轮次的数据
                turn_data = self._extract_turn_data(
                    conversation=conversation,
                    turn_idx=turn_idx,
                    turn=turn,
                    session_id=conversation["session_id"],
                    image=image,
                    image_url=image_url,
                    image_quality=image_quality,
                    answer_lookup=answer_lookup,
                    total_turn_count=total_turn_count,
                )
                batch.append(turn_data)

                # ------------------------
                # 3) 更新轮次指针
                # ------------------------
                next_turn_idx[conv_id] += 1

                # 若该对话仍有剩余轮次，则重新加入队列（前端）
                if next_turn_idx[conv_id] < total_turn_count:
                    queue.appendleft(conv_id)
                    # 注意：追加到左侧有助于控制缓存大小
                else:
                    # 该对话没有更多轮次 => 从缓存中移除
                    del self.conversation_cache[conv_id]
                    del self.answer_lookup_cache[conv_id]
                    del self.image_cache[conv_id]

            # 将整个批次作为一个块产出
            yield self._collate_batch(batch)
            batch = []

        # 若 batch 中还有剩余内容，则产出
        if batch:
            yield self._collate_batch(batch)


def main():
    """
    用于演示和调试的主函数。

    加载 CRAG-MM 数据集，通过批处理器处理，
    并打印每个批次以验证实现。
    """
    # 加载数据集
    print("Loading CRAG-MM dataset...")
    from utils import ensure_crag_cache_dir_is_configured

    CACHE_DIR = ensure_crag_cache_dir_is_configured()

    dataset = load_dataset(
        "crag-mm-2025/crag-mm-single-turn-public",
        revision="v0.1.2",
        cache_dir=CACHE_DIR,
    )
    dataset_split = dataset["public_test"]

    # 创建批处理器
    print(f"Creating batcher for {len(dataset_split)} conversations...")
    batch_size = 16
    full_query_file = "full_query/single_turn_full_query.jsonl"
    crag_turn_batch_iterator = CRAGTurnBatchIterator(
        dataset=dataset_split,
        batch_size=batch_size,
        full_query_file=full_query_file,
        shuffle=True,
    )
    # 处理批次
    print(f"Processing dataset in batches of {batch_size}...")
    for batch in tqdm.tqdm(crag_turn_batch_iterator):
        # 仅为演示打印批大小
        num_examples = len(batch["session_ids"])
        print(f"Batch with {num_examples} examples")
        print(f"Cache size: {len(crag_turn_batch_iterator.conversation_cache)}")
        # 取消注释以打印完整批次详情：
        # print(batch)


if __name__ == "__main__":
    main()
