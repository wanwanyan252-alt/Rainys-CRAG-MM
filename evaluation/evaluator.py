# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

"""
CRAG-MM 数据集的主评测器类。

本模块包含用于编排评测流程的 CRAGEvaluator 类，
包括回答生成、语义评测和结果计算。
"""

import json
import os
import time
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime
from typing import Callable

import numpy as np
import pandas as pd
import tqdm
from example_agents.base_agent import BaseAgent
from utils.retriever import get_rag_context
from utils.crag_batch_iterator import CRAGTurnBatchIterator
from cragmm_search.search import UnifiedSearchPipeline
from datasets import Dataset

from evaluation.config import (
    MAX_BATCH_SIZE,
    MAX_RESPONSE_LENGTH_IN_TOKENS,
    MIN_BATCH_SIZE,
    SESSIONS_TO_SKIP,
    SESSIONS_TO_UPDATE,
)
from evaluation.dataset_utils import (
    clean_text,
    convert_domain_indices_to_names,
    prepare_feature_vocabularies,
)
from evaluation.llm_judge import LLMJudge
from evaluation.evaluation_utils import calculate_scores
from rich.console import Console
from tokenizers import Tokenizer

console = Console()


class _WhitespaceEncoding:
    def __init__(self, text: str, max_length: int) -> None:
        self.ids = text.split()[:max_length]


class _WhitespaceTokenizer:
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length

    def encode_batch(self, texts: list[str]) -> list[_WhitespaceEncoding]:
        return [_WhitespaceEncoding(text, self.max_length) for text in texts]

    def decode(self, ids: list[str]) -> str:
        return " ".join(ids)


def _load_response_tokenizer() -> Tokenizer | _WhitespaceTokenizer:
    tokenizer_name = os.environ.get("CRAG_RESPONSE_TOKENIZER")
    if not tokenizer_name:
        return _WhitespaceTokenizer(MAX_RESPONSE_LENGTH_IN_TOKENS)

    try:
        tokenizer = Tokenizer.from_pretrained(tokenizer_name)
    except Exception as exc:
        console.print(
            "[yellow]Response tokenizer could not be loaded from Hugging Face; "
            "using local whitespace truncation for this run.[/yellow]"
        )
        console.print(f"[dim]{exc}[/dim]")
        return _WhitespaceTokenizer(MAX_RESPONSE_LENGTH_IN_TOKENS)

    tokenizer.enable_truncation(max_length=MAX_RESPONSE_LENGTH_IN_TOKENS)
    return tokenizer


class CRAGEvaluator:
    """
    用于在 CRAG-MM 数据集上评测智能体的类。

    该评测器会生成回答、评测回答（可选使用语义评测模型）、
    计算多轮对话指标，并可选择保存结果。
    """

    def __init__(
        self,
        dataset: Dataset | None,
        agent: BaseAgent | None,
        eval_model_name: str | None = None,
        eval_api_key: str | None = None,
        num_conversations: int | None = None,
        image_search: bool = False,
        web_search: bool = False,
        search_pipeline: UnifiedSearchPipeline | None = None,
        show_progress: bool = True,
        num_workers: int = 1,
        dataset_type: str = "single-turn",
        full_query_path: str | None = None,
    ) -> None:
        self.dataset = dataset
        self.agent = agent
        self.eval_model_name = eval_model_name
        self.eval_api_key = eval_api_key
        self.num_conversations = num_conversations
        self.image_search = image_search
        self.web_search = web_search
        self.search_pipeline = search_pipeline
        self.show_progress = show_progress
        self.num_workers = num_workers
        self.elasped_time = None
        self.dataset_type = dataset_type
        self.full_query_file = full_query_path

        # 评测所需的内部状态；这些值会在初始化阶段设置
        self.batch_iterator: CRAGTurnBatchIterator | None = None
        self.conversations_count: int = 0
        self.agent_response_map: dict[str, str] = {}
        self.all_turn_data: list[dict[str, any]] = []
        self.session_ids_evaluated: set[str] = set()

        self.tokenizer = _load_response_tokenizer()

        # 若提供了评测模型，则初始化 LLM 裁判
        self.llm_judge: LLMJudge | None = None
        if self.eval_model_name and self.eval_api_key:
            self.llm_judge = LLMJudge(self.eval_api_key, self.eval_model_name)

    def evaluate_response(self, crag_turn_data: dict[str, any]) -> dict[str, any]:
        """
        评测单条回答并返回评测结果。

        参数:
            crag_turn_data: 包含查询、标准答案和智能体回答的字典。

        返回:
            添加了评测结果的 crag_turn_data 字典。
        """
        agent_response = crag_turn_data["agent_response"]
        ground_truth = crag_turn_data["ground_truth"]
        query = crag_turn_data["query"]

        agent_response_clean = clean_text(agent_response)

        is_idk = (
            "i dont know" in agent_response_clean
            or "i do not know" in agent_response_clean
        )

        is_exact_match = agent_response.strip().lower() == ground_truth.strip().lower()
        is_semantically_correct = False
        api_response = None

        # 先假设精确匹配结果即为正确性结果
        is_correct = is_exact_match

        # 若不是精确匹配且提供了评测模型，则使用语义评测
        if not is_idk and not is_exact_match and self.llm_judge:
            api_response = self.llm_judge.evaluate(query, ground_truth, agent_response)
            if api_response:
                is_semantically_correct = api_response["accuracy"]
                is_correct = is_semantically_correct
        if is_exact_match:
            is_semantically_correct = True

        return {
            **crag_turn_data,
            "is_exact_match": is_exact_match,
            "is_correct": is_correct,
            "is_miss": is_idk,
            "is_semantically_correct": is_semantically_correct,
            "api_response": api_response if api_response else None,
        }

    def initialize_for_generation(self) -> None:
        """
        初始化仅生成模式所需的变量。

        这是 initialize_evaluation() 的轻量版本，只设置回答生成所需的内容。
        """
        if self.dataset is None or self.agent is None:
            raise ValueError("Dataset and agent are required for generation")

        console.print("[blue]Starting generation mode[/blue]")

        self.conversations_count = (
            len(self.dataset)
            if self.num_conversations is None
            else min(self.num_conversations, len(self.dataset))
        )
        batch_size = int(
            np.clip(self.agent.get_batch_size(), MIN_BATCH_SIZE, MAX_BATCH_SIZE)
        )
        self.agent_response_map = {}
        self.all_turn_data = []
        self.session_ids_evaluated = set()

        # 实例化基于 CRAG 轮次的批迭代器
        self.batch_iterator = CRAGTurnBatchIterator(
            dataset=self.dataset,
            batch_size=batch_size,
            full_query_file=self.full_query_file,
            shuffle=False,
            sessions_to_skip=SESSIONS_TO_SKIP.get(self.dataset_type, []),
            sessions_to_update=SESSIONS_TO_UPDATE.get(self.dataset_type, {}),
        )

        # 保存用于领域映射的特征词表
        self.feature_vocabularies = prepare_feature_vocabularies(self.dataset)

    def initialize_evaluation(self) -> None:
        """
        初始化完整评测（生成 + 评测）所需的变量。

        此方法会设置内部状态，包括批迭代器、对话数量、
        智能体回答映射和轮次数据列表。
        """
        console.print(
            f"[blue]Starting evaluation with {self.num_workers} workers[/blue]"
        )
        if self.eval_model_name:
            console.print(
                f"[blue]Using semantic evaluation with model: {self.eval_model_name}[/blue]"
            )

        # 使用与生成模式相同的初始化逻辑
        self.initialize_for_generation()

    def generate_agent_responses(
        self, progress_callback: Callable[[int, int], None] = None
    ) -> None:
        """
        阶段 1：为数据集中的每个轮次生成智能体回答。

        此方法使用内部批迭代器遍历数据集批次，并用智能体回答和轮次数据
        更新评测器状态。
        """
        start_time = time.time()
        if self.batch_iterator is None:
            raise ValueError(
                "Batch iterator is not initialized. Please call initialize_evaluation() first."
            )
        if self.agent is None:
            raise ValueError("Agent is required for generate_agent_responses()")

        for batch_idx, batch in enumerate(
            tqdm.tqdm(
                self.batch_iterator,
                desc="Generating responses",
                disable=not self.show_progress,
            )
        ):
            interaction_ids = batch["interaction_ids"]
            queries = batch["queries"]
            images = batch["images"]
            conversation_histories = batch["conversation_histories"]
            full_queries = batch["full_queries"]

            message_histories = []
            interaction_id_histories = []
            # 构建多轮对话的消息历史
            for conversation_history in conversation_histories:
                message_history = []
                interaction_id_history = []
                for turn in conversation_history:
                    turn_interaction_id = turn["interaction_id"]
                    turn_agent_response = self.agent_response_map.get(
                        turn_interaction_id
                    )
                    if not turn_agent_response:
                        raise AssertionError(
                            f"Agent response not found for turn {turn_interaction_id}. "
                            "Did you shuffle the multi-turn conversations by mistake?"
                        )
                    message_history.append({"role": "user", "content": turn["query"]})
                    message_history.append(
                        {"role": "assistant", "content": turn_agent_response}
                    )
                    interaction_id_history.append(turn_interaction_id)
                message_histories.append(message_history)
                interaction_id_histories.append(interaction_id_history)

            # 传给智能体前，将领域索引转换为领域名称
            domain_names = convert_domain_indices_to_names(
                batch["domains"], self.feature_vocabularies
            )

            rag_context_list = [
                get_rag_context(
                    query,
                    image,
                    self.search_pipeline,
                    self.image_search,
                    self.web_search,
                    full_query,
                )
                for query, image, full_query in zip(queries, images, full_queries)
            ]

            # 为当前批次生成回答
            agent_responses = self.agent.batch_generate_response(
                queries,
                images,
                message_histories,
                rag_context_list=rag_context_list,
                domains=domain_names,
            )
            agent_responses = self.truncate_agent_responses(
                agent_responses
            )  # 将每条回答截断到允许的最大长度（75 个令牌）

            # 收集回答并添加评测数据
            for idx, interaction_id in enumerate(interaction_ids):
                agent_response = agent_responses[idx]
                self.agent_response_map[interaction_id] = agent_response
                self.all_turn_data.append(
                    {
                        "session_id": batch["session_ids"][idx],
                        "interaction_id": interaction_id,
                        "turn_idx": batch["turn_idxs"][idx],
                        "is_ego": batch["image_urls"][idx] is None,
                        "image_quality": batch["image_qualities"][idx],
                        "query_category": batch["query_categories"][idx],
                        "domain": batch["domains"][idx],
                        "dynamism": batch["dynamisms"][idx],
                        "query": queries[idx],
                        "ground_truth": batch["answers"][idx],
                        "agent_response": agent_response,
                        "total_turn_count": batch["total_turn_counts"][idx],
                        "interaction_id_history": interaction_id_histories[idx],
                    }
                )
                self.session_ids_evaluated.add(batch["session_ids"][idx])

            if progress_callback:
                conversations_evaluated = len(self.session_ids_evaluated)
                progress_callback(conversations_evaluated, self.conversations_count)

            if len(self.session_ids_evaluated) > self.conversations_count:
                console.print(
                    f"[yellow]Already evaluated {len(self.session_ids_evaluated)} conversations. Abruptly stopping evaluation.[/yellow]"
                )
                break

        end_time = time.time()
        self.elasped_time = end_time - start_time
        print(f"Elasped time: Function ran for {self.elasped_time:.4f} seconds")

    def evaluate_agent_responses(
        self,
        turn_data: list[dict[str, any]],
        progress_callback: Callable[[int, int], None] = None,
    ) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, float]]]:
        """
        阶段 2：评测智能体回答并计算分数。

        此方法使用基于线程的并行执行器，以避免 pickle 问题。
        参数:
            turn_data: 包含智能体回答的轮次数据列表。
        返回:
            包含轮次评测结果和分数字典的元组。
        """
        results = []
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [
                executor.submit(self.evaluate_response, data) for data in turn_data
            ]
            for future_idx, future in tqdm.tqdm(
                enumerate(as_completed(futures)),
                total=len(futures),
                desc="Evaluating responses",
                disable=not self.show_progress,
            ):
                results.append(future.result())
                if progress_callback is not None:
                    progress_callback(future_idx, len(turn_data))

        # 将中间评测结果转换为 pandas 数据帧
        turn_evaluation_results_df = pd.DataFrame(results)
        turn_evaluation_results_df = turn_evaluation_results_df.sort_values(
            by=["session_id", "turn_idx"]
        )

        ego_turn_evaluation_results_df = turn_evaluation_results_df[
            turn_evaluation_results_df["is_ego"] == True
        ]

        all_scores_dictionary = calculate_scores(turn_evaluation_results_df)
        ego_scores_dictionary = calculate_scores(ego_turn_evaluation_results_df)

        turn_evaluation_results = {
            "all": turn_evaluation_results_df,
            "ego": ego_turn_evaluation_results_df,
        }
        score_dictionaries = {
            "all": all_scores_dictionary,
            "ego": ego_scores_dictionary,
        }

        return turn_evaluation_results, score_dictionaries

    def save_results(
        self,
        turn_evaluation_results: dict[str, any],
        scores_dictionary: dict[str, any],
        output_dir: str,
    ) -> None:
        """
        将评测结果保存到指定目录。

        参数:
            turn_evaluation_results: 要保存的评测结果。
            scores_dictionary: 要保存的分数字典。
            output_dir: 保存结果的路径。
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_dir)), exist_ok=True)
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = f"{output_dir}/{timestamp}"
        os.makedirs(output_dir, exist_ok=True)

        turn_evaluation_results["all"].to_csv(
            os.path.join(output_dir, "turn_evaluation_results_all.csv"), index=False
        )
        turn_evaluation_results["ego"].to_csv(
            os.path.join(output_dir, "turn_evaluation_results_ego.csv"), index=False
        )
        with open(os.path.join(output_dir, "scores_dictionary.json"), "w") as f:
            json.dump(scores_dictionary, f, indent=2)

        if self.elasped_time is not None:
            try:
                time_str = (
                    f"Elasped time: Function ran for {self.elasped_time:.4f} seconds"
                )
                time_file = os.path.join(output_dir, "elasped_time.txt")
                with open(time_file, "w+") as file:
                    file.write(time_str)
            except Exception as e:
                print(f"Elasped time did not write successfully {e}")

    def save_turn_data(self, output_file: str) -> None:
        """
        将轮次数据保存到 JSONL 文件，供后续评测使用。

        参数:
            output_file: 以 JSONL 格式保存轮次数据的路径。
        """
        output_dir = os.path.dirname(os.path.abspath(output_file))
        os.makedirs(output_dir, exist_ok=True)
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = f"{output_dir}/{timestamp}"
        os.makedirs(output_dir, exist_ok=True)

        base_file = os.path.basename(output_file)
        output_file = f"{output_dir}/{base_file}"

        with open(output_file, "w") as f:
            for turn_data in self.all_turn_data:
                f.write(json.dumps(turn_data) + "\n")
        console.print(
            f"[green]Saved {len(self.all_turn_data)} turns to {output_file}[/green]"
        )

        if self.elasped_time is not None:
            try:
                time_str = (
                    f"Elasped time: Function ran for {self.elasped_time:.4f} seconds"
                )
                time_file = os.path.join(output_dir, "elasped_time.txt")
                with open(time_file, "w+") as file:
                    file.write(time_str)
            except Exception as e:
                print(f"Elasped time did not write successfully {e}")

    def load_turn_data(self, input_file: str) -> list[dict[str, any]]:
        """
        从 JSONL 文件加载轮次数据。

        参数:
            input_file: 包含轮次数据的 JSONL 文件路径。

        返回:
            轮次数据字典列表。
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")

        turn_data = []
        with open(input_file, "r") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    # 校验必需字段是否存在
                    required_fields = [
                        "session_id",
                        "interaction_id",
                        "query",
                        "ground_truth",
                        "agent_response",
                    ]
                    missing_fields = [
                        field for field in required_fields if field not in data
                    ]
                    if missing_fields:
                        raise ValueError(f"Missing required fields: {missing_fields}")
                    turn_data.append(data)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON on line {line_num}: {e}")
                except ValueError as e:
                    raise ValueError(f"Error on line {line_num}: {e}")

        console.print(f"[green]Loaded {len(turn_data)} turns from {input_file}[/green]")
        return turn_data

    def evaluate_agent(self) -> tuple[dict[str, any], dict[str, any]]:
        """
        在数据集上评测智能体并返回性能指标。

        返回:
            包含轮次评测结果字典和分数字典的元组。
        """
        # 阶段 0：初始化评测状态
        self.initialize_evaluation()

        # 阶段 1：生成智能体回答（会更新内部状态）
        def _generation_progress_callback(
            conversations_evaluated: int, total_conversations: int
        ) -> None:
            # 可用于跟踪评测进度
            pass

        self.generate_agent_responses(_generation_progress_callback)

        # 阶段 2：使用已保存的轮次数据评测回答

        def _evaluation_progress_callback(
            turn_evaluated: int, total_turns: int
        ) -> None:
            # 可用于跟踪评测进度
            pass

        turn_evaluation_results, score_dictionaries = self.evaluate_agent_responses(
            self.all_turn_data, _evaluation_progress_callback
        )
        return turn_evaluation_results, score_dictionaries

    def truncate_agent_responses(self, agent_responses: list[str]) -> list[str]:
        """
        将每条智能体回答截断到允许的最大长度。
        """
        encodings = self.tokenizer.encode_batch(agent_responses)
        trimmed_agent_responses = [self.tokenizer.decode(enc.ids) for enc in encodings]
        return trimmed_agent_responses
