# CRAG-MM P5 本地训练数据准备报告

日期：2026-11-24（Asia/Shanghai）

## 1. 完成范围

本阶段只完成本地训练准备，没有启动云服务器、没有安装训练依赖、没有加载或训练 Llama。

已完成：

- 位置 0–399 的多任务 SFT JSONL；
- hard negatives；
- DPO/偏好训练 JSONL；
- 稳定 train/dev 划分；
- 400–599 外部 held-out 隔离；
- 去重、图片引用、显式参考答案字段、API Key、split 和 SHA-256 检查；
- QLoRA 配置；
- 独立训练依赖文件；
- dry-run 训练入口与 Bash 启动脚本。

## 2. 数据规模

| 类型 | 数量 |
|---|---:|
| 多任务 SFT | 1,413 |
| Preference | 368 |
| Hard negatives | 91 |
| SFT train | 1,087 |
| SFT dev | 326 |

多任务明细：

| 任务 | 数量 |
|---|---:|
| route | 400 |
| answer_or_abstain | 400 |
| evidence_selection | 316 |
| entity | 144 |
| query_rewrite | 144 |
| OCR 弱标签 | 9 |

回答训练目标中，345 条目标为事实答案，55 条目标为 `I don't know.`。

## 3. 数据划分

- 数据来源严格限制为位置 0–399。
- 400–599 被固定为外部 held-out，未进入任何 JSONL。
- train/dev 使用 `sha256(session_id) mod 10`：0–7 为 train，8–9 为 dev。
- 400 个 session 中，307 个进入 train，93 个进入 dev。
- 同一个 session 不会跨 split。

## 4. 标签策略

### 回答与弃答

- identity、visual、OCR、chart 类问题可使用图像监督目标。
- lookup、comparison 只有在保存的网页证据与参考答案存在足够词项/数字重合时才训练事实答案。
- 缺乏相关证据时目标统一为 `I don't know.`。
- 错误模型回答只作为 rejected 或 hard negative，不作为正标签。

### Entity

- 优先使用 `entity_consistency_valid` 通过的实体。
- 旧结果没有该字段时，只在 DeepSeek 判对样本中使用实体弱标签。

### OCR

- 当前只有 9 条 Llama OCR 弱标签。
- 这些标签已经标记为 `llama_weak_ocr`，正式训练前应人工抽查。
- 不建议把 9 条 OCR 数据视为足够的 OCR 微调数据；未来独立 OCR 数据应追加为新版本。

### Evidence selection

- 候选文档来自当时保存的 RAG context。
- 正标签由参考答案内容词和数字与文档的重合度生成。
- 这是弱监督标签，不等同于人工证据标注。

## 5. Hard negatives

| 类型 | 数量 |
|---|---:|
| unresolved_entity_guess | 51 |
| wrong_answer_or_evidence_mismatch | 32 |
| unsupported_or_meta_answer | 6 |
| comparison_or_direction_error | 2 |

这些记录保留原错误回答、推荐回答或弃答目标、route、实体和证据，可用于 SFT hard-negative
混合或后续 DPO。

## 6. Preference 数据

| 来源 | 数量 |
|---|---:|
| supported_answer_vs_miss | 137 |
| correct_answer_vs_over_refusal | 140 |
| unresolved_entity_guess | 51 |
| wrong_answer_or_evidence_mismatch | 32 |
| unsupported_or_meta_answer | 6 |
| comparison_or_direction_error | 2 |

Preference 文件当前只完成准备；首轮建议先运行 SFT，确认 adapter 不破坏视觉能力后再做 DPO。

## 7. 完整性检查

独立验证器结果：

```text
records: 1872
unique_ids: 1872
sessions: 400
train_sessions: 307
dev_sessions: 93
heldout_leakage: 0
missing_images: 0
hash_mismatches: 0
```

训练入口 dry-run：

```text
train_records: 1087
eval_records: 326
load_in_4bit: true
lora_r: 16
no model loaded
```

## 8. 产物

目录：`artifacts/crag_v0.1.2_p5_training/`

```text
DATA_CARD.md
manifest.json
multitask_train.jsonl
multitask_dev.jsonl
preferences_train.jsonl
preferences_dev.jsonl
hard_negatives_train.jsonl
hard_negatives_dev.jsonl
```

构建与验证：

```text
tools/build_p5_training_data.py
tools/validate_p5_training_data.py
```

训练准备：

```text
training/p5_qlora_config.json
training/run_p5_qlora.sh
tools/train_p5_qlora.py
requirements-train.txt
```

## 9. 文件 SHA-256

| 文件 | SHA-256 |
|---|---|
| multitask_train.jsonl | `08616ec81d10ce78a96eb576713d4c3a872673b45b55d6780bc719ab0b25b0e4` |
| multitask_dev.jsonl | `b403be0c8e9781eb3c517e7f5042fb5a784254611aff1048e1177b2f50c91d7a` |
| preferences_train.jsonl | `97b311134a5cf3254e871e4089c223ff4cdc49568700b800c626da06501a6eb7` |
| preferences_dev.jsonl | `1161d7b9c9919d42bb22d8adb768dcf8bc42bf1163b7aefa374978e7dd8e328e` |
| hard_negatives_train.jsonl | `a6db8072ce617c494014fc125f5450d28cb1888d3ac8eee443d7108ef64f3e28` |
| hard_negatives_dev.jsonl | `7ca756165c59f62c03f8883b837e8ad5071388618237eb21f1d8a335c6594f45` |

## 10. 复现命令

重新构建：

```powershell
.\.venv-light\Scripts\python.exe tools\build_p5_training_data.py `
  --full-results artifacts\crag_v0.1.2_full_blind_cloud\results_full_1938.json `
  --full-judgments artifacts\crag_v0.1.2_full_blind_cloud\deepseek_flash_judgments_full_1938.json `
  --structured-results artifacts\crag_v0.1.2_full_blind_cloud\results_hybrid_raw_200_599.json `
  --structured-judgments artifacts\crag_v0.1.2_full_blind_cloud\deepseek_flash_judgments_hybrid_raw_200_599.json `
  --output-dir artifacts\crag_v0.1.2_p5_training `
  --max-position 399 `
  --external-heldout-start 400 `
  --external-heldout-end 599
```

验证：

```powershell
.\.venv-light\Scripts\python.exe tools\validate_p5_training_data.py `
  --data-dir artifacts\crag_v0.1.2_p5_training `
  --repo-root .

.\.venv-light\Scripts\python.exe tools\train_p5_qlora.py `
  --config training\p5_qlora_config.json `
  --dry-run
```

## 11. 云端训练入口（本阶段未执行）

必须创建独立训练环境，不要修改已验证的 `cragmm` 推理环境：

```bash
conda create -n cragmm-train python=3.10 -y
conda activate cragmm-train
pip install -r requirements-train.txt

RUN_TRAINING=0 bash training/run_p5_qlora.sh
RUN_TRAINING=1 bash training/run_p5_qlora.sh
```

先保持 `RUN_TRAINING=0` 完成 dry-run；只有 dry-run、显存检查和训练依赖检查通过后才能设为 1。

## 12. 风险与后续边界

- 训练脚本已完成静态检查和数据 dry-run，但没有在 CUDA/PEFT/bitsandbytes 环境实际启动模型。
- OCR 数据过少且是弱标签，首轮 adapter 不应以 OCR 提升为主要目标。
- evidence selection 是自动弱标签，应避免给过高采样权重。
- 400–599 必须只用于 adapter 和阈值冻结后的最终 held-out。
- 不允许把 400–599 的错误重新加入当前训练包后再次宣称其为 held-out。
