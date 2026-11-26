#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/root/CRAG-MM}"
TRAIN_ENV="${TRAIN_ENV:-cragmm-train}"
CONFIG="${CONFIG:-training/p5_qlora_config.json}"

source /root/miniconda3/etc/profile.d/conda.sh
conda activate "$TRAIN_ENV"
cd "$REPO_ROOT"

python tools/validate_p5_training_data.py \
  --data-dir artifacts/crag_v0.1.2_p5_training \
  --repo-root "$REPO_ROOT"

python tools/train_p5_qlora.py --config "$CONFIG" --dry-run

if [[ "${RUN_TRAINING:-0}" != "1" ]]; then
  echo "Dry-run complete. Set RUN_TRAINING=1 to start QLoRA."
  exit 0
fi

RESUME_ARG=()
if [[ "${RESUME_TRAINING:-0}" == "1" ]]; then
  RESUME_ARG+=(--resume)
fi

python tools/train_p5_qlora.py --config "$CONFIG" "${RESUME_ARG[@]}"
