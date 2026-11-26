# CRAG-MM 阶段 A 完成说明

日期：2026-11-22（Asia/Shanghai）

## 1. 阶段目标

阶段 A 针对固定 50 条中的 27 条弃答，恢复已有实体或网页证据支持的答案，同时保持原有
正确答案不回退。

## 2. 最终候选

文件：

`../artifacts/crag_v0.1.2_slice50/results_stage_b_candidate_50.json`

代理指标：

| 指标 | 阶段 A 前 | 阶段 B 候选 |
|---|---:|---:|
| 样本数 | 50 | 50 |
| 弃答 | 27 | 19 |
| 回答覆盖率 | 46% | 62% |
| 平均 token F1 | 0.1781 | 0.2474 |

新回答位置：01、20、28、30、33、36、47、49。

## 3. 已合并结果

| 样本 | 阶段 A 结果 | 状态 |
|---:|---|---|
| 01 | Trailblazer 1.3L AWD 用 5 加仑可覆盖 DC 到 Baltimore | 合并，待 DeepSeek |
| 20 | 日本警察未在 1998 长野冬奥会使用 Nissan Z | 合并，人工判断正确 |
| 28 | 2015 Chevrolet Suburban 的 MyLink、蓝牙、设备连接等功能 | 合并，待 DeepSeek |
| 30 | 洋葱的抗氧化、消化、心血管和抗癌相关益处 | 合并，人工判断正确 |
| 33 | Space Needle 设计可承受 9.0 级地震 | 合并，人工判断正确 |
| 36 | Radio City Music Hall 举办过 basketball/WNBA 和 boxing | 合并，待 DeepSeek |
| 47 | Andrea della Robbia 出生于 1435 年 | 合并，人工判断正确 |
| 49 | `males aged 18-24` | 合并，人工判断正确 |

## 4. 未合并结果

| 样本 | 结果 | 处理 |
|---:|---|---|
| 02 | 错认食物来源为法国/比利时 | 保持原弃答 |
| 14 | 未得到 Toyota Yaris 2007/第二代完整证据 | 保持原弃答 |
| 22 | 错选 RAM 2500，回答 19,990 磅 | 保持原弃答 |
| 24 | 回答黄玫瑰可持续数周或 5–12 天 | 保持原弃答 |
| 38 | 回答公共换尿布台始于 1986，而参考为 1950s | 保持原弃答 |

## 5. 阶段 A 验证

- 本地与云端通过 57 项 unittest。
- 目标样本均在固定 validation 前 50 条内。
- 未运行完整 validation。
- 阶段 A 结束时 GPU 为 0 MiB / 0%，无后台推理进程。
- 新候选尚未运行 DeepSeek。正式语义成绩由阶段 B 产生。

## 6. 阶段 B 入口

阶段 B 直接使用 `results_stage_b_candidate_50.json`，不要重新运行 Llama 或检索。操作步骤见：

`stage_b_operator_guide_2026-11-22.md`
