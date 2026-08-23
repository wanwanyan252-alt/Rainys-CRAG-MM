# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

import pandas as pd
import numpy as np


def calculate_scores(turn_evaluation_results_df: pd.DataFrame) -> dict[str, float]:
    """
    计算单轮和多轮对话的得分。

    参数:
        turn_evaluation_results_df: 包含各轮评测结果的 DataFrame。
    返回:
        计算得到的各项指标字典。
    """
    multi_turn_conversation_score_map: dict[str, float] = {}

    def _set_is_correct_false_after_consecutive(
        group: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        在连续答错后将后续各轮标记为 is_miss，
        并为每段对话计算多轮对话得分。
        """
        group_copy = group.copy().reset_index(drop=True)
        for i in range(1, len(group_copy)):
            if (
                not group_copy.loc[i - 1, "is_correct"]
                and not group_copy.loc[i, "is_correct"]
            ):
                group_copy.loc[i + 1 :, "is_correct"] = False
                group_copy.loc[i + 1 :, "is_exact_match"] = False
                group_copy.loc[i + 1 :, "is_miss"] = True
                group_copy.loc[i + 1 :, "is_semantically_correct"] = False
                break

        group_copy["is_hallucination"] = (
            ~group_copy["is_correct"] & ~group_copy["is_miss"]
        )
        multi_turn_conversation_score = (
            group_copy["is_correct"].mean() - group_copy["is_hallucination"].mean()
        )
        group_copy["multi_turn_conversation_score"] = multi_turn_conversation_score
        session_id = group_copy.iloc[0]["session_id"]
        multi_turn_conversation_score_map[session_id] = multi_turn_conversation_score
        return group_copy

    total = len(turn_evaluation_results_df)
    correct_exact = turn_evaluation_results_df["is_exact_match"].sum()
    correct = turn_evaluation_results_df["is_correct"].sum()
    miss = turn_evaluation_results_df["is_miss"].sum()
    hallucination = total - (correct + miss)

    turn_evaluation_results_df = turn_evaluation_results_df.groupby(
        "session_id", group_keys=False
    )[turn_evaluation_results_df.columns].apply(_set_is_correct_false_after_consecutive)

    exact_match = correct_exact / total
    accuracy = correct / total
    missing = miss / total
    hallucination_rate = hallucination / total
    truthfulness_score = ((2 * correct + miss) / total) - 1 if total > 1 else 0.0
    mean_multi_turn_conversation_score = np.mean(
        list(multi_turn_conversation_score_map.values())
    )

    scores_dictionary = {
        "total": float(total),
        "correct_exact": float(correct_exact),
        "correct": float(correct),
        "miss": float(miss),
        "hallucination": float(hallucination),
        "exact_match": float(exact_match),
        "accuracy": float(accuracy),
        "missing": float(missing),
        "hallucination_rate": float(hallucination_rate),
        "truthfulness_score": float(truthfulness_score),
        "mean_multi_turn_conversation_score": float(mean_multi_turn_conversation_score),
    }

    return scores_dictionary

