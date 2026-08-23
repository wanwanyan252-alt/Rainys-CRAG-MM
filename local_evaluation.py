# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

"""
CRAG-MM 数据集评测脚本

本脚本在 CRAG-MM 数据集上评测智能体（使用 `agents/user_config.py` 中配置的用户提供的 `UserAgent`）。
它会生成回答、评测回答（可选通过 OpenAI API 使用语义评测模型）、
计算多轮对话指标，并可选择保存结果。

这是一个轻量级 CLI 包装器，会从 evaluation 模块导入评测逻辑。
"""

import argparse
import os

# 首先加载环境变量
import pandas as pd
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from utils.utils import display_results, ensure_crag_cache_dir_is_configured

load_dotenv()

# 在导入任何 HF 库之前设置分词器并行选项
os.environ["TOKENIZERS_PARALLELISM"] = "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", None)


from example_agents.user_config import get_agent_from_model_name
from cragmm_search.search import UnifiedSearchPipeline
from datasets import load_dataset
from evaluation import CRAGEvaluator, DEFAULT_EVAL_MODEL, DEFAULT_NUM_WORKERS

CACHE_DIR = ensure_crag_cache_dir_is_configured()
console = Console()


def setup_eval_model(eval_model: str) -> str | None:
    """设置评测模型的辅助函数；若禁用则显示警告。"""
    if eval_model.lower() == "none":
        console.print(
            Panel(
                "[bold red]WARNING: SEMANTIC EVALUATION IS DISABLED[/bold red]\n\n"
                "No calls to LLM-as-a-Judge will be made!\n"
                "Results will rely only on exact string matching.",
                title="[bold red]ATTENTION[/bold red]",
                border_style="red",
                width=100,
                padding=(2, 5),
                expand=False,
            )
        )
        return None
    return eval_model


def display_and_save_results(
    evaluator: CRAGEvaluator,
    turn_evaluation_results: dict[str, pd.DataFrame],
    score_dictionaries: dict[str, dict[str, float]],
    args: argparse.Namespace,
) -> None:
    """展示结果并按需保存的辅助函数。"""
    # 展示全部结果
    display_results(
        console,
        turn_evaluation_results["all"],
        score_dictionaries["all"],
        display_conversations=args.display_conversations,
        is_ego=False,
        is_multi_turn=getattr(args, "dataset_type", "multi-turn") == "multi-turn",
    )

    # 如有第一人称结果，则展示
    if len(turn_evaluation_results["ego"]) > 0:
        display_results(
            console,
            turn_evaluation_results["ego"],
            score_dictionaries["ego"],
            display_conversations=args.display_conversations,
            is_ego=True,
            is_multi_turn=getattr(args, "dataset_type", "multi-turn") == "multi-turn",
        )

    # 若指定了输出目录，则保存结果
    if args.output_dir:
        evaluator.save_results(
            turn_evaluation_results, score_dictionaries, args.output_dir
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate an agent on the CRAG-MM dataset"
    )
    parser.add_argument(
        "--dataset-type",
        type=str,
        default="single-turn",
        choices=["single-turn", "multi-turn"],
        help="Dataset type to load",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="validation",
        help="Dataset split to use ('validation', 'public_test')",
    )
    parser.add_argument(
        "--num-conversations",
        type=int,
        default=-1,
        help=(
            "Number of conversations to evaluate (default: -1). -1 evaluates all"
            " conversations, while a positive number evaluates that many conversations."
        ),
    )
    parser.add_argument(
        "--suppress-web-search-api",
        action="store_true",
        help="Suppress web search API when calling the agent",
    )
    parser.add_argument(
        "--suppress-image-search-api",
        action="store_true",
        help="Suppress image search API when calling the agent",
    )
    parser.add_argument(
        "--display-conversations",
        type=int,
        default=10,
        help="Number of evaluation examples to show",
    )
    parser.add_argument(
        "--eval-model",
        type=str,
        default=DEFAULT_EVAL_MODEL,
        help=(
            "OpenAI model for semantic evaluation. Pass 'None' to disable semantic"
            " evaluation."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./results",
        help="Path to save turn evaluation results, scores dictionary, and generated responses (response.jsonl)",
    )
    parser.add_argument(
        "--no_progress", action="store_true", help="Disable progress bar"
    )
    parser.add_argument(
        "--revision",
        type=str,
        default="v0.1.2",
        help="Dataset revision/version to use when loading from HuggingFace",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=DEFAULT_NUM_WORKERS,
        help=(
            "Number of worker processes for parallel evaluation (default:"
            f" {DEFAULT_NUM_WORKERS})"
        ),
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default="meta-llama/Llama-3.2-11B-Vision-Instruct",
        help="Model name to feed into vllm. The agent type is automatically inferred from the model name (e.g., 'llama', 'claude', 'gpt', 'gemini', 'pixtral', 'internvl', 'qwen').",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="both",
        choices=["generate", "evaluate", "both"],
        help=(
            "Mode to run: 'generate' (generation only), 'evaluate' (evaluation only),"
            " or 'both' (default: both)"
        ),
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help=(
            "Path to load turn data from (JSONL format). Required for --mode evaluate."
        ),
    )
    parser.add_argument(
        "--full-query-path",
        type=str,
        default=None,
        help="Path to the saved full-query path, required to update web search query.",
    )
    args = parser.parse_args()

    # 若输出目录不存在，则创建
    os.makedirs(args.output_dir, exist_ok=True)

    # 定义回答文件路径
    response_file = os.path.join(args.output_dir, "response.jsonl")

    # 校验各模式专用参数
    if args.mode == "generate" and os.path.exists(response_file):
        raise ValueError(
            f"Error: {response_file} already exists and will be overwritten in generate mode. "
            "Please remove it or use a different output directory."
        )
    if args.mode == "evaluate" and not args.input_file:
        console.print(
            "[red]Error: --input-file is required when using --mode evaluate[/red]"
        )
        return

    if args.mode != "generate":
        if OPENAI_API_KEY is None:
            raise ValueError("OPENAI_API_KEY environment variable is not set!")

    # 在仅评测模式下，无需加载数据集或初始化智能体
    if args.mode == "evaluate":
        console.print("[bold blue]Running evaluation-only mode...[/bold blue]")

        # 按需设置评测模型并显示警告
        args.eval_model = setup_eval_model(args.eval_model)

        # 为仅评测模式创建最小评测器
        evaluator = CRAGEvaluator(
            dataset=None,
            agent=None,
            eval_model_name=args.eval_model,
            eval_api_key=OPENAI_API_KEY,
            num_conversations=None,
            show_progress=not args.no_progress,
            num_workers=args.num_workers,
            dataset_type=args.dataset_type,
        )

        # 加载轮次数据并进行评测
        turn_data = evaluator.load_turn_data(args.input_file)
        turn_evaluation_results, score_dictionaries = (
            evaluator.evaluate_agent_responses(turn_data)
        )

        # 使用辅助函数展示并保存结果
        display_and_save_results(
            evaluator, turn_evaluation_results, score_dictionaries, args
        )
        return

    # 在生成模式或双模式下，需要数据集和智能体
    console.print(f"[bold blue]Loading {args.dataset_type} dataset...[/bold blue]")
    repo_name = f"crag-mm-2025/crag-mm-{args.dataset_type}-public"
    console.print(
        f"[bold green]Loading from HuggingFace:[/bold green] {repo_name} (revision:"
        f" {args.revision})"
    )
    dataset = load_dataset(repo_name, revision=args.revision, cache_dir=CACHE_DIR)
    available_splits = list(dataset.keys())
    split_to_use = args.split if args.split in available_splits else available_splits[0]
    console.print(
        f"[bold green]Using split:[/bold green] '{split_to_use}' with"
        f" {len(dataset[split_to_use])} examples"
    )

    # 按需设置评测模型并显示警告
    args.eval_model = setup_eval_model(args.eval_model)

    if args.num_conversations == -1:
        args.num_conversations = len(dataset[split_to_use])

    # 如果设置了标志，则禁用网页搜索 API，这对任务 1（单源增强）很有用
    search_api_text_model_name = "BAAI/bge-large-en-v1.5"
    search_api_image_model_name = "openai/clip-vit-large-patch14-336"
    search_api_web_hf_dataset_id = "crag-mm-2025/web-search-index-public-test"
    search_api_image_hf_dataset_id = "crag-mm-2025/image-search-index-public-test"

    if args.suppress_web_search_api and args.suppress_image_search_api:
        search_pipeline = None
    else:
        if args.suppress_web_search_api:
            search_api_web_hf_dataset_id = None
            search_api_text_model_name = None

        if args.suppress_image_search_api:
            search_api_image_hf_dataset_id = None
            search_api_image_model_name = None

        search_pipeline = UnifiedSearchPipeline(
            text_model_name=search_api_text_model_name,
            image_model_name=search_api_image_model_name,
            web_hf_dataset_id=search_api_web_hf_dataset_id,
            image_hf_dataset_id=search_api_image_hf_dataset_id,
        )

    UserAgent = get_agent_from_model_name(args.model_name)

    evaluator = CRAGEvaluator(
        dataset=dataset[split_to_use],
        agent=UserAgent(
            model_name=args.model_name, is_multi_turn=args.dataset_type == "multi-turn"
        ),
        image_search=not args.suppress_image_search_api,
        web_search=not args.suppress_web_search_api,
        search_pipeline=search_pipeline,
        eval_model_name=args.eval_model,
        eval_api_key=OPENAI_API_KEY,
        num_conversations=args.num_conversations,
        show_progress=not args.no_progress,
        num_workers=args.num_workers,
        dataset_type=args.dataset_type,
        full_query_path=args.full_query_path,
    )

    if args.mode == "generate":
        # 仅生成模式
        console.print("[bold blue]Running generation-only mode...[/bold blue]")
        evaluator.initialize_for_generation()
        evaluator.generate_agent_responses()
        evaluator.save_turn_data(response_file)
        console.print(
            f"[green]Generation complete. Results saved to {response_file}[/green]"
        )
        return

    # 双模式（默认行为）
    console.print("[bold blue]Running both generation and evaluation...[/bold blue]")
    turn_evaluation_results, score_dictionaries = evaluator.evaluate_agent()

    # 保存中间轮次数据
    evaluator.save_turn_data(response_file)

    # 使用辅助函数展示并保存结果
    display_and_save_results(
        evaluator, turn_evaluation_results, score_dictionaries, args
    )


if __name__ == "__main__":
    main()
