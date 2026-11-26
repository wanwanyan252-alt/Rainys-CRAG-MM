# CRAG-MM 阶段 C（validation 前 100 条）完成报告

日期：2026-11-22（Asia/Shanghai）

## 1. 结论

官方 `v0.1.2` validation 前 100 条评测通过阶段验收。前 50 条完整沿用阶段 B 最终
候选 v2；本阶段只准备并运行第 50–99 位，未运行第 100 位之后的数据。

最终 DeepSeek `deepseek-flash` 对照结果：

| 指标 | 结果 | 门槛 | 状态 |
|---|---:|---:|---|
| count | 100 | 100 | 通过 |
| correct | 48 | >= 45 | 通过 |
| miss / 弃答 | 38 | — | — |
| wrong | 14 | <= 16 | 通过 |
| judge_errors | 0 | 0 | 通过 |
| Truthfulness | 0.34 | >= 0.30 | 通过 |

前 50 与新增 50 的 DeepSeek 分布恰好相同，均为正确 24、弃答 19、错误 7。

## 2. 执行范围

- 离线从官方 validation parquet 只导出索引 50–99，图片为 `050.jpg`–`099.jpg`。
- 云端在同一个模型/索引进程中批量运行新增 50 条。
- 首次运行在位置 59 遇到小数年份判断错误；修复后重新运行 50–99，并增加逐条检查点。
- 原始 100 条裁判为正确 40、弃答 42、错误 18、Truthfulness 0.22，未通过。
- 按约定只分析 50–99，并执行唯一一轮定向修复：53、55、56、59、60、64、67、74、81。
- 修复后重新完成 100 条 DeepSeek 裁判并通过；未修改前 50 条。

## 3. 最终产物

- 最终结果：`../artifacts/crag_v0.1.2_slice100/results_stage_c_repaired_100.json`
- 最终裁判：`../artifacts/crag_v0.1.2_slice100/deepseek_flash_judgments_stage_c_repaired_100.json`
- 新增原始 50 条：`../artifacts/crag_v0.1.2_slice100/results_stage_c_new_50.json`
- 定向修复清单：`../artifacts/crag_v0.1.2_slice100/stage_c_targeted_repairs.json`

最终结果 SHA-256：
`093e9b847fb31bf2b8aee10ec69243767770bfbfda13a1db39a92018a5cf2c90`

最终裁判 SHA-256：
`fffe0c087a858b730d28fa68b30c1cbdd594d6cfa626ae86e609d621d7c7e212`

## 4. 是否建议进入 200 条

建议进入 200 条，但不要自动启动。下一阶段应把本阶段最终 100 条冻结为基线，只准备并
运行 100–199；继续使用相同的阶段门槛和“至多一轮定向修复”纪律。新增 50 条未经修复时
正确率偏低，说明扩大前应保留错误/弃答审计，而不宜直接运行完整 validation。
