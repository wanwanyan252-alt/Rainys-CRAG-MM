# CRAG-MM 多查询 + 独立 Reranker 最终结项报告

日期：2026-11-25（Asia/Shanghai）

## 1. 最终结论

完整多查询召回、独立 cross-encoder reranker、实体/范围过滤已经实现，并在 400–599 held-out
上通过竞赛化验收。项目以该版本正式结项。

最终候选：

```text
Llama 3.2 11B Vision Instruct
+ P5 4-bit QLoRA adapter
+ 快速 2×2 contact-sheet
+ 结构化 entity/OCR/route/confidence
+ 3–5 路确定性 web query
+ URL 去重
+ 实体、国家/市场、年份过滤
+ 词法预筛 top 40
+ MiniLM 独立 cross-encoder reranker
+ top 5 web evidence
+ adapter/reranker 专属拒答门控
+ 75-token 限制
```

Held-out 400–599 最终结果：正确 56、弃答 111、错误 33、Truthfulness `0.115`，覆盖率
44.5%，已回答准确率 62.92%。P95 延迟 `5.381s`，最大 `6.132s`，超过 10 秒为 0。

## 2. 独立 Reranker

模型：[`cross-encoder/ms-marco-MiniLM-L6-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2)

```text
revision: 7e04a311ff05454833e7ff491d0f33c461c7e181
parameters: 22.7M
license: Apache-2.0
device: CPU
candidate cap: 40
final evidence: top 5
```

模型远低于比赛对辅助模型约 1.6B 参数的限制。权重在运行前固定并缓存，评测时完全离线。

模型权重 SHA-256：

```text
821d1aa69520101d6e0737f78a042ae25b19e5cb9160701909d10434f4aeb0ae
```

## 3. 多查询流程

每题根据已有视觉分析最多生成五路确定性查询，不增加额外 Llama 调用：

1. 原始问题；
2. 实体 + 问题属性的 focused query；
3. 明确标记实体的完整 query；
4. OCR 可见文本 + 原始问题；
5. 比较题的实体比较 query。

查询去重后，held-out 平均实际查询数为 `2.81`。每路最多召回 20 条，按 URL/页面内容去重；
实体、国家/市场和问题年份过滤后，以轻量词法相关性预筛到 40 条，再由 MiniLM cross-encoder
独立打分，最终只向 Llama 提供 top 5。

## 4. 原始结果

| 区间 | 正确 | 弃答 | 错误 | Truthfulness | 覆盖率 | 已回答准确率 |
|---|---:|---:|---:|---:|---:|---:|
| 开发 200–399 | 96 | 33 | 71 | 0.125 | 83.5% | 57.49% |
| Held-out 400–599 | 89 | 34 | 77 | 0.060 | 83.0% | 53.61% |
| 合计 | 185 | 67 | 148 | 0.0925 | 83.25% | 55.56% |

多查询与 reranker 显著提高了可回答样本和正确数，但原始错误仍高，不能在没有门控时提交。

## 5. 最终门控结果

门控只在 200–399 训练和选择阈值，冻结后应用到 400–599。

| 区间 | 正确 | 弃答 | 错误 | Truthfulness | 覆盖率 | 已回答准确率 |
|---|---:|---:|---:|---:|---:|---:|
| 开发 200–399 | 65 | 123 | 12 | 0.265 | 38.5% | 84.42% |
| Held-out 400–599 | 56 | 111 | 33 | 0.115 | 44.5% | 62.92% |
| 合计 | 121 | 234 | 45 | 0.190 | 41.5% | 72.89% |

五折 OOF 为 `0.155`，与 held-out `0.115` 同方向，没有出现训练集内完全失真的情况。

## 6. 方案对照

400–599：

| 方案 | 正确 | 弃答 | 错误 | Truthfulness |
|---|---:|---:|---:|---:|
| 原慢速策略 | 66 | 69 | 65 | 0.005 |
| 原慢速 + 旧门控 | 51 | 115 | 34 | 0.085 |
| 未微调 hybrid + 新门控 | 40 | 130 | 30 | 0.050 |
| P5 QLoRA + adapter 门控 | 45 | 130 | 25 | 0.100 |
| P5 + 多查询 + MiniLM + 最终门控 | 56 | 111 | 33 | **0.115** |

最终版本相对原始慢速系统：

- Truthfulness `0.005 → 0.115`；
- 正确 `66 → 56`，但错误 `65 → 33`；
- 净得分从 1 提升到 23；
- P95 从超过 13 秒降至 5.381 秒；
- 10 秒超时从大量出现降为 0。

相对不含 reranker 的 P5 版本：

- Truthfulness `0.100 → 0.115`；
- 正确 `45 → 56`；
- 错误 `25 → 33`；
- 覆盖率 `35.0% → 44.5%`。

## 7. 速度

| 区间 | Mean | P50 | P95 | Max | >10s |
|---|---:|---:|---:|---:|---:|
| 200–399 | 4.499s | 4.541s | 5.649s | 8.682s | 0 |
| 400–599 | 4.439s | 4.486s | 5.381s | 6.132s | 0 |

独立 CPU reranker 未破坏比赛的 10 秒限制。

## 8. 最终产物

```text
models/ms-marco-MiniLM-L6-v2/
utils/web_reranker.py
utils/retriever.py
tools/evaluate_vlm_slice.py
artifacts/crag_v0.1.2_p5_training/results_p5_multi_rerank_200_599.json
artifacts/crag_v0.1.2_p5_training/deepseek_flash_judgments_p5_multi_rerank_200_599.json
artifacts/crag_v0.1.2_p5_training/p5_multi_rerank_gate_200_399.json
artifacts/crag_v0.1.2_p5_training/results_p5_multi_rerank_200_599_gated.json
artifacts/crag_v0.1.2_p5_training/deepseek_flash_judgments_p5_multi_rerank_200_599_gated.json
```

产物 SHA-256：

```text
gated results: 3e152453d76dbf3868ef660edc82d139459090fba27a4ec618dbc7100160c7b0
gated judgments: a74b0cc60818174b41fe63d47ca4e8905d8aa05c6d76ddfcabc83cdea8c19a68
gate config: ab1772c08b789b0dbd2bb658fbd354eb6cf55f3c73d97deb2e14035e28a74e4c
```

## 9. 结项边界

- DeepSeek 为对照裁判，不是官方 GPT-4o 或人工最终成绩。
- 400–599 已作为最终 held-out，后续不得继续针对该区间调参并再次宣称未见。
- 当前版本已经完成完整数据基线、速度合规、连续拒答门控、OCR/路由消融、QLoRA、多查询、
  独立 reranker、held-out 和复现材料。
- 若未来继续研究，应改用新的 private/multi-turn 数据，而不是继续消耗当前 validation。

本项目至此结项。
