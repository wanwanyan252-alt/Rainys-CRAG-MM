# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

"""
CRAG-MM 评测的数据集工具函数。

本模块提供数据集准备和处理相关工具，
包括领域映射、文本清洗和特征词表提取。
"""

import re
from typing import List


def prepare_feature_vocabularies(dataset_split):
    """从数据集中提取用于类别编码的特征词表。

    这些词表可用于在整数索引和字符串标签之间转换。

    参数:
        dataset_split: 要从中提取词表的数据集划分。

    返回:
        包含 domain、query_category、dynamism 和 image_quality
        特征词表的字典。
    """
    turns_feature = dataset_split.features["turns"]
    return {
        "domain": turns_feature["domain"],
        "query_category": turns_feature["query_category"],
        "dynamism": turns_feature["dynamism"],
        "image_quality": turns_feature["image_quality"],
    }


def convert_domain_indices_to_names(
    domain_indices: List[int], feature_vocabularies: dict
) -> List[str]:
    """使用特征词表将领域整数索引转换为字符串名称。

    参数:
        domain_indices: 领域整数索引列表
        feature_vocabularies: 包含领域特征映射的字典

    返回:
        领域名称字符串列表
    """
    domain_feature = feature_vocabularies["domain"].feature
    domain_names = []

    for domain_idx in domain_indices:
        if isinstance(domain_idx, list) and len(domain_idx) > 0:
            # 处理 domain 为列表的情况（取第一个元素）
            domain_idx = domain_idx[0]

        if domain_idx is not None and 0 <= domain_idx < len(domain_feature.names):
            domain_names.append(domain_feature.names[domain_idx])
        else:
            domain_names.append("other")  # 默认回退值

    return domain_names


def clean_text(text: str) -> str:
    """通过转小写并移除所有非字母数字字符来清洗文本。

    参数:
        text: 要清洗的文本。

    返回:
        仅包含小写字母数字字符和空格的清洗后文本。
    """
    # 转为小写并移除所有非字母数字字符（包括撇号）
    return re.sub(r"[^a-z0-9\s]", "", text.lower())
