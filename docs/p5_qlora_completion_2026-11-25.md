# CRAG-MM P5 QLoRA 微调与 Held-out 完成报告

日期：2026-11-25（Asia/Shanghai）

## 1. 结论

P5 多任务 QLoRA 已完成，并在未参与训练的 400–599 held-out 上通过验收。

最终候选：

```text
Llama 3.2 11B Vision Instruct
+ P5 4-bit QLoRA adapter
+ 快速 2×2 contact-sheet
+ 结构化 entity/OCR/route/confidence
+ 保留网页检索
+ adapter 专属拒答门控
+ 75-token 限制
```

Held-out 400–599：正确 45、弃答 130、错误 25、Truthfulness `0.100`，已回答准确率
64.29%。对照旧慢速策略 + 0.415 门控为 `0.085`，因此提升 `0.015`；错误数从 34 降至 25。

## 2. 训练数据

- 来源位置：0–399。
- 外部 held-out：400–599，训练泄漏 0。
- SFT：1,413 条，其中 train 1,087、dev 326。
- Preference：368 条。
- Hard negatives：91 条。
- 训练数据报告：`p5_training_data_preparation_2026-11-24.md`。

## 3. 训练配置

| 项目 | 配置 |
|---|---|
| GPU | NVIDIA A40 48GB |
| 基座 | Llama-3.2-11B-Vision-Instruct |
| 量化 | 4-bit NF4 + double quant |
| LoRA rank / alpha | 16 / 32 |
| Dropout | 0.05 |
| Epochs | 2 |
| Batch / accumulation | 1 / 16 |
| Learning rate | 2e-4 |
| Vision encoder | frozen |
| Target modules | q/k/v/o、gate/up/down projections |

训练环境从稳定推理环境克隆为独立 `cragmm-train`，只新增 PEFT 0.17.1 与 bitsandbytes 0.46.1，
没有修改原 `cragmm` 推理环境。

## 4. 训练结果

单步冒烟：

```text
1 training step passed
loss 4.4347
约 2.12s/step
峰值 GPU allocated 10.31 GiB
```

正式训练：

```text
136/136 optimizer steps
2 epochs
train runtime 5120.36s（约 85.3 分钟）
final train loss 0.6608
eval loss 0.5792
```

checkpoint-100、checkpoint-136 与 final_adapter 均成功生成。LoRA adapter 大小约 242MB。

Adapter 权重 SHA-256：

```text
763eb3b1adee0f7aa1ff163a2a0db3d1f2961ae76052be9686157055efdbde7b
```

## 5. 合并与推理

Adapter 已安全合并到 BF16 基座，并由 vLLM 成功加载。单图冒烟正确回答测试图片为
`Subaru WRX`。

微调模型在 200–599 的端到端速度：

| 区间 | Mean | P50 | P95 | Max | >10s |
|---|---:|---:|---:|---:|---:|
| Held-out 400–599 | 3.992s | 4.045s | 4.920s | 5.925s | 0 |

满足官方 10 秒限制。

## 6. DeepSeek 原始结果

| 区间 | 正确 | 弃答 | 错误 | Truthfulness | 覆盖率 | 已回答准确率 |
|---|---:|---:|---:|---:|---:|---:|
| 开发 200–399 | 79 | 48 | 73 | 0.030 | 76.0% | 51.97% |
| Held-out 400–599 | 74 | 46 | 80 | -0.030 | 77.0% | 48.05% |

微调模型明显更愿意回答，但未门控时错误同步上升，因此不能直接提交原始输出。

## 7. Adapter 专属门控

门控仅在 200–399 训练和选阈值，然后冻结应用到 400–599。

| 区间 | 正确 | 弃答 | 错误 | Truthfulness | 覆盖率 | 已回答准确率 |
|---|---:|---:|---:|---:|---:|---:|
| 开发 200–399 | 60 | 129 | 11 | 0.245 | 35.5% | 84.51% |
| Held-out 400–599 | 45 | 130 | 25 | 0.100 | 35.0% | 64.29% |

五折 OOF 仅为 `0.0925`，与 held-out `0.100` 接近，未出现此前结构化门控那样的严重崩塌。

## 8. 对照

400–599：

| 方案 | 正确 | 弃答 | 错误 | Truthfulness |
|---|---:|---:|---:|---:|
| 原慢速策略 | 66 | 69 | 65 | 0.005 |
| 原慢速 + 旧门控 0.415 | 51 | 115 | 34 | 0.085 |
| 未微调 hybrid + 新门控 | 40 | 130 | 30 | 0.050 |
| P5 QLoRA hybrid + adapter 门控 | 45 | 130 | 25 | 0.100 |

P5 最终候选相对原始慢速系统：

- Truthfulness `0.005 → 0.100`；
- 错误 `65 → 25`；
- P95 `>13s → 4.92s`；
- 超过 10 秒 `大量 → 0`。

## 9. 最终产物

```text
checkpoints/p5_lora/
artifacts/crag_v0.1.2_p5_training/p5_qlora_train.log
artifacts/crag_v0.1.2_p5_training/outputs/llama32_11b_p5_qlora/trainer_state.json
artifacts/crag_v0.1.2_p5_training/results_p5_merged_hybrid_200_599.json
artifacts/crag_v0.1.2_p5_training/deepseek_flash_judgments_p5_merged_hybrid_200_599.json
artifacts/crag_v0.1.2_p5_training/p5_adapter_gate_200_399.json
artifacts/crag_v0.1.2_p5_training/results_p5_merged_hybrid_200_599_gated.json
artifacts/crag_v0.1.2_p5_training/deepseek_flash_judgments_p5_merged_hybrid_200_599_gated.json
```

## 10. 边界与下一步

- DeepSeek 仍是对照裁判，不是官方 GPT-4o 或人工最终成绩。
- 400–599 已用于本次最终 held-out；不能继续针对该区间调参并再次称其为未见数据。
- 若继续，应该在新的独立数据或 multi-turn split 上验证，不应继续修改当前 validation 答案。
- 正式提交应携带基座模型、LoRA adapter 或合并权重、adapter 专属门控和快速推理路径。
