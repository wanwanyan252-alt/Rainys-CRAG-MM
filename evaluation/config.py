# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

"""
CRAG-MM 评测的配置常量。

本模块集中管理整个评测流程中使用的所有配置参数，
包括模型设置、批大小、token 限制和数据集常量。
"""

import os

# 模型配置
DEFAULT_EVAL_MODEL = "gpt-4o"
MAX_API_RETRIES = 3
DEFAULT_NUM_WORKERS = 1

# 批大小配置
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = int(
    os.environ.get("MAX_BATCH_SIZE", "16")
)  # 默认为 16，可通过环境变量配置

# 令牌限制
MAX_RESPONSE_LENGTH_IN_TOKENS = 75
MAX_EVAL_TOKENS = 1024

# 数据集常量 - 需要跳过的会话
SESSIONS_TO_SKIP = {
    "single-turn": [
        "04d98259-27af-41b1-a7be-5798fd1b8e95",
        "695b4b5c-7c65-4f7b-8968-50fe10482a16",
    ],
    "multi-turn": [
        "04d98259-27af-41b1-a7be-5798fd1b8e95",
        "695b4b5c-7c65-4f7b-8968-50fe10482a16",
    ],
}

# 数据集常量 - 需要更新的会话
SESSIONS_TO_UPDATE = {
    "single-turn": {
        "0df99a9a-6a5d-4ff4-b8e4-e3ee90209dfe": {
            "image_url": "https://web.archive.org/web/20250521025904/https://upload.wikimedia.org/wikipedia/commons/1/13/BMW_5_SERIES_LWB_SEDAN_(G30)_China_(82).jpg"
        }
    }
}
