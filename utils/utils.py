# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

import hashlib
import io
import itertools
import json
import os
import urllib.parse
from typing import Any

import pandas as pd
import requests
from PIL import Image
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def ensure_crag_cache_dir_is_configured():
    """
    确保 CRAG 图像缓存目录存在且配置正确。

    本函数执行以下操作：
    1. 检查是否设置了 CRAG_CACHE_DIR 环境变量
    2. 若未设置，则使用适合当前平台的默认缓存路径
    3. 若目录不存在则创建该目录
    4. 返回缓存目录路径

    返回:
        str: 缓存目录路径
    """
    # 首先检查用户是否显式设置了缓存目录
    cache_dir = os.environ.get("CRAG_CACHE_DIR")

    if not cache_dir:
        # 若未显式设置，则使用平台特定的默认路径
        if os.name == "nt":  # Windows
            cache_home = os.environ.get(
                "LOCALAPPDATA", os.path.expanduser("~/AppData/Local")
            )
        else:  # Unix/Linux/Mac
            cache_home = os.environ.get(
                "XDG_CACHE_HOME", os.path.expanduser("~/.cache")
            )

        cache_dir = os.path.join(cache_home, "cragmm_images_cache")

        # 仅在首次调用时打印提示信息
        if not hasattr(ensure_crag_cache_dir_is_configured, "_cache_location_shown"):
            print(f"Caching downloaded images in {cache_dir}")
            print(
                "You can override this by setting the CRAG_CACHE_DIR environment"
                " variable."
            )
            ensure_crag_cache_dir_is_configured._cache_location_shown = True

    # 若目录不存在则创建
    if not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Failed to create cache directory {cache_dir}: {e}")
            # 若无法创建默认目录，则回退使用临时目录
            import tempfile

            cache_dir = os.path.join(tempfile.gettempdir(), "cragmm_images_cache")
            os.makedirs(cache_dir, exist_ok=True)
            print(f"Using fallback cache directory: {cache_dir}")

    return cache_dir


def download_image_url(image_url):
    """从 URL 下载图像，并以确定性的文件名保存到缓存目录。
    成功则返回本地路径，否则抛出异常。

    参数:
        image_url: 待下载图像的 URL

    返回:
        str: 已下载或已缓存图像的本地路径

    异常:
        Exception: 当图像无法下载或无效时抛出
    """
    cache_dir = ensure_crag_cache_dir_is_configured()

    # 若缓存目录不存在则创建（冗余操作，用于保持向后兼容）
    os.makedirs(cache_dir, exist_ok=True)

    try:
        # 基于 URL 生成确定性的文件名
        url_hash = hashlib.md5(image_url.encode()).hexdigest()
        file_extension = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
        local_filename = f"{url_hash}{file_extension}"
        local_path = os.path.join(cache_dir, local_filename)

        # 若文件已存在于缓存中，则校验并返回
        if os.path.exists(local_path):
            if _is_valid_image(local_path):
                print(f"Using cached image from {local_path}")
                return local_path
            else:
                print(f"Cached image is invalid, re-downloading: {local_path}")
                # 缓存文件无效，继续执行下载

        # 下载图像
        headers = {"User-Agent": "CRAGBot/v0.0.1"}
        response = requests.get(image_url, stream=True, timeout=10, headers=headers)
        response.raise_for_status()

        # 先将图像保存到临时文件
        temp_path = f"{local_path}.temp"
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 校验已下载的图像
        if _is_valid_image(temp_path):
            # 若有效则移动到最终位置
            os.replace(temp_path, local_path)
            print(f"Downloaded and validated image_url to {local_path}")
            return local_path
        else:
            # 删除无效图像
            os.remove(temp_path)
            print(f"Downloaded image is not valid from URL: {image_url}")
            raise Exception(f"Downloaded image is not valid from URL {image_url}")

    except Exception as e:
        print(f"Error downloading image from {image_url}: {e}")
        raise Exception(f"Error downloading image from {image_url}: {e}")


def _is_valid_image(file_path):
    """使用 PIL 检查文件是否为有效图像。

    参数:
        file_path: 图像文件路径

    返回:
        bool: 有效则返回 True，否则返回 False
    """
    try:
        with Image.open(file_path) as img:
            # 通过加载来校验图像
            img.verify()

            # 通过访问图像属性做额外检查
            width, height = img.size
            if width <= 0 or height <= 0:
                return False

            return True
    except Exception as e:
        print(f"Invalid image file {file_path}: {e}")
        return False


def is_url(url):
    """检查该 URL 是否为有效的图像 URL。"""
    try:
        result = urllib.parse.urlparse(url)
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


def resize_image_if_needed(
    image: Image.Image, max_size_mb: float = 5.0, max_dimension_px: int = 8000
) -> Image.Image:
    """
    若图像超过允许的文件大小或尺寸上限，则对其进行缩放。
    缩小时保持宽高比不变。

    参数:
        image (Image.Image): 输入的 PIL 图像。
        max_size_mb (float): 允许的最大文件大小（单位：MB）。
        max_dimension_px (int): 允许的最大宽/高（单位：像素）。

    返回:
        Image.Image: 缩放后（或原始）的图像。
    """
    max_bytes = max_size_mb * 1024 * 1024

    def get_image_size_bytes(img: Image.Image, format="JPEG", quality=85) -> int:
        buf = io.BytesIO()
        img.save(buf, format=format, quality=quality, optimize=True)
        return buf.tell()

    # --- 第 1 步：若尺寸超过 max_dimension_px 则缩小 ---
    width, height = image.size
    if max(width, height) > max_dimension_px:
        scale = max_dimension_px / float(max(width, height))
        new_size = (int(width * scale), int(height * scale))
        image = image.resize(new_size, Image.LANCZOS)

    # --- 第 2 步：若文件大小超过 max_size_mb 则缩小 ---
    size_bytes = get_image_size_bytes(image)
    while size_bytes > max_bytes and (image.size[0] > 100 and image.size[1] > 100):
        # 缩小为原来的 90%
        new_size = (int(image.size[0] * 0.9), int(image.size[1] * 0.9))
        image = image.resize(new_size, Image.LANCZOS)
        size_bytes = get_image_size_bytes(image)

    return image


def display_results(
    console: Console,
    turn_evaluation_results_df: pd.DataFrame,
    scores_dictionary: dict[str, Any],
    display_conversations: int = 3,
    is_ego: bool = False,
    is_multi_turn: bool = False,
) -> None:
    """以格式化的方式展示评测结果"""

    ego_string = "Ego Only" if is_ego else "All"
    title = f"Evaluation Results :: {ego_string}"

    # 创建指标表格
    metrics_table = Table(show_header=True, header_style="bold magenta")
    metrics_table.add_column("Metric", style="dim")
    metrics_table.add_column("Value")

    metrics_table.add_row(
        "Total conversations", str(turn_evaluation_results_df["session_id"].nunique())
    )
    metrics_table.add_row(
        "Total turns", str(turn_evaluation_results_df["interaction_id"].nunique())
    )
    metrics_table.add_row(
        "Avg MT conversation score",
        "{:.2f}".format(scores_dictionary["mean_multi_turn_conversation_score"]),
    )
    metrics_table.add_row("Exact matches", str(scores_dictionary["correct_exact"]))
    metrics_table.add_row('"I don\'t know" responses', str(scores_dictionary["miss"]))
    metrics_table.add_row(
        "Hallucinated responses", str(scores_dictionary["hallucination"])
    )
    metrics_table.add_row("Exact accuracy", f"{scores_dictionary['exact_match']:.2%}")
    metrics_table.add_row("Accuracy", f"{scores_dictionary['accuracy']:.2%}")
    metrics_table.add_row("Missing rate", f"{scores_dictionary['missing']:.2%}")
    metrics_table.add_row(
        "Hallucination rate", f"{scores_dictionary['hallucination_rate']:.2%}"
    )
    metrics_table.add_row(
        "Truthfulness score", f"{scores_dictionary['truthfulness_score']:.4f}"
    )

    # 创建面板中要展示的可渲染对象列表
    renderables = [metrics_table]

    # 若有需要，添加示例对话表格
    if display_conversations > 0:

        def _init_conversation_table(title: str):
            table = Table(title=title)
            if is_multi_turn:
                table.add_column("Turn", style="dim")
            else:
                table.add_column("interaction_id", style="dim")
            table.add_column("Query", style="dim")
            table.add_column("Agent Response", style="dim")
            table.add_column("Ground Truth", style="dim")
            table.add_column("API Response", style="dim")
            table.add_column("Evaluation Result", style="dim")
            return table

        def _get_status_style_and_text(row: pd.Series):
            if row["is_exact_match"]:
                return "green", "[green]EXACT MATCH[/green]"
            elif row["is_semantically_correct"]:
                return "green", "[green]SEMANTICALLY CORRECT[/green]"
            elif row["is_miss"]:
                return "yellow", "[yellow]I DON'T KNOW[/yellow]"
            else:
                return "red", "[red]INCORRECT[/red]"

        # 添加示例结果的分节标题
        renderables.append(Text("\nSample Evaluation Results", style="bold cyan"))

        if is_multi_turn:
            conversation_groups = turn_evaluation_results_df.groupby("session_id")
            for session_id, group_df in itertools.islice(
                conversation_groups, display_conversations
            ):
                table = _init_conversation_table(f"Session ID: {session_id}")
                for idx, row in group_df.iterrows():
                    status_style, status_text = _get_status_style_and_text(row)
                    table.add_row(
                        f"{row['turn_idx']}",
                        f"[bold cyan]{row['query']}[/bold cyan]",
                        f"[bold yellow]{row['agent_response']}[/bold yellow]",
                        f"[bold green]{row['ground_truth']}[/bold green]",
                        f"[bold blue]{str(row['api_response'])[:100]}[/bold blue]",
                        f"[bold {status_style}]{status_text}[/bold {status_style}]",
                    )
                renderables.append(table)
        else:
            table = _init_conversation_table("Evaluation Results")
            for idx, row in itertools.islice(
                turn_evaluation_results_df.iterrows(), display_conversations
            ):
                status_style, status_text = _get_status_style_and_text(row)
                table.add_row(
                    f"{row['interaction_id'][:5]}",
                    f"[bold cyan]{row['query']}[/bold cyan]",
                    f"[bold yellow]{row['agent_response']}[/bold yellow]",
                    f"[bold green]{row['ground_truth']}[/bold green]",
                    f"[bold blue]{str(row['api_response'])[:100]}[/bold blue]",
                    f"[bold {status_style}]{status_text}[/bold {status_style}]",
                )
            renderables.append(table)

    # 使用 Group 组合所有可渲染对象，在单个面板中展示全部表格
    group = Group(*renderables)
    panel = Panel(
        group, title=f"[bold]{title}[/bold]", border_style="blue", padding=(1, 2)
    )
    console.print(panel)


def parse_jsonl_to_dict(file_path):
    """
    读取 .jsonl 文件并解析为字典。

    参数:
        file_path (str): .jsonl 文件路径

    返回:
        dict: 以 interaction_id 为键、full_query 为值的字典
    """
    result_dict = {}

    if file_path is None:
        return result_dict

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        interaction_id = data.get("interaction_id")
                        full_query = data.get("agent_response")

                        if interaction_id is not None and full_query is not None:
                            try:
                                full_query_parsed = json.loads(full_query)
                                result_dict[interaction_id] = full_query_parsed[
                                    "updated_question"
                                ]
                            except Exception:
                                result_dict[interaction_id] = data.get("query")

                    except json.JSONDecodeError as e:
                        print(f"Error parsing line: {line}")
                        print(f"Error: {e}")
                        continue
    except Exception:
        pass

    return result_dict
