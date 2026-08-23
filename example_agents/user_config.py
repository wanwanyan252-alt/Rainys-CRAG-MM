# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。


def get_agent_from_model_name(model_name: str):
    """
    根据模型名称懒加载对应 Agent。

    这样在本地只跑 random 时，不会提前导入 vllm / anthropic / google 等重依赖。
    """
    model_name_lower = model_name.lower()

    if "random" in model_name_lower:
        from .random_agent import RandomAgent
        return RandomAgent

    if "debug" in model_name_lower:
        from .debug_agent import DebugAgent
        return DebugAgent

    if "rule" in model_name_lower:
        from .rule_agent import RuleAgent
        return RuleAgent

    if "idk" in model_name_lower:
        from .idk_agent import IdkAgent
        return IdkAgent

    if "claude" in model_name_lower:
        from .closed_model_agents import ClaudeAgent
        return ClaudeAgent

    if "gpt" in model_name_lower:
        from .closed_model_agents import GPTAgent
        return GPTAgent

    if "gemini" in model_name_lower:
        from .closed_model_agents import GeminiAgent
        return GeminiAgent

    if "llama" in model_name_lower:
        from .open_source_model_agents import LlamaAgent
        return LlamaAgent

    if "pixtral" in model_name_lower:
        from .open_source_model_agents import PixtralAgent
        return PixtralAgent

    if "internvl" in model_name_lower:
        from .open_source_model_agents import InternVLAgent
        return InternVLAgent

    if "qwen" in model_name_lower:
        from .open_source_model_agents import QwenAgent
        return QwenAgent

    supported_keywords = "random, debug, rule, idk, claude, gpt, gemini, llama, pixtral, internvl, qwen"
    raise ValueError(
        f"Cannot find a corresponding agent for model '{model_name}'. "
        f"Model name must contain one of the following keywords: {supported_keywords}"
    )
