#!/bin/bash

# 示例用法：
# ./run_task_generation.sh \
#   --task task-2 --model-name gpt-5-mini --output-dir ~/experiments/results

set -euo pipefail

print_usage() {
  cat <<EOF
Usage: $0 --task TASK --model-name MODEL --output-dir PATH [--num-conversations N]

Required:
  --task            one of: st-vanilla, task-1, task-2, mt-vanilla, task-3
  --model-name      model name (e.g., gpt-5-mini, gemini-2.5-flash, claude-3-7-sonnet-latest)
  --output-dir      directory to write output (may use ~)
Optional:
  --num-conversations  integer (default: -1)
EOF
  exit 1
}

# 默认值
num_conversations=-1

# 解析参数
while [[ $# -gt 0 ]]; do
  case "$1" in
  --task)
    task="$2"
    shift 2
    ;;
  --model-name)
    model_name="$2"
    shift 2
    ;;
  --output-dir)
    output_dir="$2"
    shift 2
    ;;
  --num-conversations)
    num_conversations="$2"
    shift 2
    ;;
  -*)
    echo "Unknown option: $1" >&2
    print_usage
    ;;
  *)
    echo "Unexpected argument: $1" >&2
    print_usage
    ;;
  esac
done

# 校验必需参数
if [[ -z "${task:-}" || -z "${model_name:-}" || -z "${output_dir:-}" ]]; then
  echo "Missing required arguments." >&2
  print_usage
fi

# 校验任务选项
case "$task" in
st-vanilla | task-1 | task-2 | mt-vanilla | task-3) ;;
*)
  echo "Invalid --task: $task" >&2
  print_usage
  ;;
esac

# 确定 task_args
if [[ "$task" == "st-vanilla" || "$task" == "mt-vanilla" ]]; then
  task_args=(--suppress-image-search-api --suppress-web-search-api)
elif [[ "$task" == "task-1" ]]; then
  task_args=(--suppress-web-search-api)
elif [[ "$task" == "task-2" || "$task" == "task-3" ]]; then
  task_args=(
    --full-query-path
    "$HOME/crag-mm-benchmarking/query_outputs/multi_turn_full_query.jsonl"
  )
fi

# 确定 dataset_type
if [[ "$task" == "st-vanilla" || "$task" == "task-1" || "$task" == "task-2" ]]; then
  dataset_type="single-turn"
elif [[ "$task" == "mt-vanilla" || "$task" == "task-3" ]]; then
  dataset_type="multi-turn"
fi

# 展开输出目录路径（处理开头的 ~）
if [[ "$output_dir" == ~* ]]; then
  output_dir="${HOME}${output_dir:1}"
fi

# 构建命令
cmd=(
  python3 "local_evaluation.py"
  --mode generate
  --split public_test
  --dataset-type "$dataset_type"
  --model-name "$model_name"
  "${task_args[@]}"
  --output-dir "$output_dir"
  --num-conversations "$num_conversations"
)

# 打印并运行
echo "Running: ${cmd[*]}"
exec "${cmd[@]}"
