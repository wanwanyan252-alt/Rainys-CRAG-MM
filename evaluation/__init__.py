# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

"""
CRAG-MM 数据集评测模块。

本模块为 CRAG-MM 基准提供模块化评测框架，
包含配置、数据集工具、基于 LLM 的裁判和评测编排等组件。
"""

from .config import (
    DEFAULT_EVAL_MODEL,
    DEFAULT_NUM_WORKERS,
    MAX_API_RETRIES,
    MAX_BATCH_SIZE,
    MAX_EVAL_TOKENS,
    MAX_RESPONSE_LENGTH_IN_TOKENS,
    MIN_BATCH_SIZE,
    SESSIONS_TO_SKIP,
    SESSIONS_TO_UPDATE,
)
from .dataset_utils import (
    clean_text,
    convert_domain_indices_to_names,
    prepare_feature_vocabularies,
)
from .evaluator import CRAGEvaluator
from .llm_judge import LLMJudge

__all__ = [
    # 评测器
    "CRAGEvaluator",
    "LLMJudge",
    # 配置
    "DEFAULT_EVAL_MODEL",
    "DEFAULT_NUM_WORKERS",
    "MAX_API_RETRIES",
    "MAX_BATCH_SIZE",
    "MAX_EVAL_TOKENS",
    "MAX_RESPONSE_LENGTH_IN_TOKENS",
    "MIN_BATCH_SIZE",
    "SESSIONS_TO_SKIP",
    "SESSIONS_TO_UPDATE",
    # 数据集工具
    "clean_text",
    "convert_domain_indices_to_names",
    "prepare_feature_vocabularies",
]
