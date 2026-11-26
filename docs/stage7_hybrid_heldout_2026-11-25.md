# CRAG-MM 第 7 节 Hybrid Held-out 验证报告

日期：2026-11-25（Asia/Shanghai）

## 1. 目标

验证第 6 节完成的结构化 OCR、问题路由、实体一致性和新拒答门控，判断其能否替代当前推荐
主线“快速 contact-sheet + 旧门控 0.415”。

## 2. 数据边界

- 200–399：开发区间，只用于训练结构化新门控和选择阈值。
- 400–599：held-out，只进行一次最终验证，不参与训练或阈值选择。
- 独立 manifest：`manifest_200_599.json`，全局索引严格为 200–599。

## 3. 云端生成

结构化视觉分析与网页关闭逻辑已经解耦；本轮保留网页检索，只使用：

- 快速 2×2 contact-sheet；
- 75-token 限制；
- entity/OCR/route/confidence 结构化输出；
- OCR—实体—图片候选一致性；
- 数值证据检查。

速度：

| 区间 | Mean | P50 | P95 | Max | >10s |
|---|---:|---:|---:|---:|---:|
| 200–599 | 4.085s | 3.927s | 6.078s | 9.317s | 0 |
| 400–599 | 4.056s | 3.915s | 5.811s | 9.317s | 0 |

时间约束通过。

## 4. DeepSeek 原始结果

| 区间 | 正确 | 弃答 | 错误 | Truthfulness |
|---|---:|---:|---:|---:|
| 200–399 | 59 | 86 | 55 | 0.020 |
| 400–599 | 63 | 74 | 63 | 0.000 |
| 合计 | 122 | 160 | 118 | 0.010 |

## 5. 新结构化门控

门控只在 200–399 训练和选择阈值。

| 区间 | 正确 | 弃答 | 错误 | Truthfulness | 覆盖率 | 已回答准确率 |
|---|---:|---:|---:|---:|---:|---:|
| 开发 200–399 | 51 | 143 | 6 | 0.225 | 28.50% | 89.47% |
| Held-out 400–599 | 40 | 130 | 30 | 0.050 | 35.00% | 57.14% |

训练区间提升很高，但 held-out 只有 `0.050`，说明门控仍存在明显过拟合。

## 6. 对照与验收

400–599 对照：

| 方案 | 正确 | 弃答 | 错误 | Truthfulness |
|---|---:|---:|---:|---:|
| 原慢速策略 | 66 | 69 | 65 | 0.005 |
| 原慢速策略 + 旧门控 0.415 | 51 | 115 | 34 | 0.085 |
| 新 hybrid + 新门控 | 40 | 130 | 30 | 0.050 |

验收要求是 Truthfulness 不低于对照超过 `0.01`，且错误数不增加。新 hybrid 虽将错误从 34
降到 30，但 Truthfulness 下降 `0.035`，未通过验收。

## 7. 最终决策

结构化 OCR/问题路由 hybrid 不进入正式主线，也不进行全量重跑。

保留的正式候选：

```text
快速 2×2 contact-sheet
75-token 限制
旧拒答门控，阈值 0.415
不启用激进网页关闭路由
```

结构化 OCR/路由代码和结果仅作为消融实验保留。后续若进行 P5 QLoRA，应先训练 adapter，再用
400–599 之外的新独立数据验证；不得继续针对 400–599 调参并称其为 held-out。

## 8. 产物

```text
artifacts/crag_v0.1.2_full_blind_cloud/manifest_200_599.json
artifacts/crag_v0.1.2_full_blind_cloud/results_hybrid_raw_200_599.json
artifacts/crag_v0.1.2_full_blind_cloud/deepseek_flash_judgments_hybrid_raw_200_599.json
artifacts/crag_v0.1.2_full_blind_cloud/hybrid_gate_200_399.json
artifacts/crag_v0.1.2_full_blind_cloud/results_hybrid_gated_200_599.json
artifacts/crag_v0.1.2_full_blind_cloud/deepseek_flash_judgments_hybrid_gated_200_599.json
```

云端生成结束后 GPU 为 0 MiB；后续分析全部在本地完成。
