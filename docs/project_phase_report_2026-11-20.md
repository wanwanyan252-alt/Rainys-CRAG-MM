# CRAG-MM 三阶段项目报告与成果

日期：2026-11-20（Asia/Shanghai）

## 1. 阶段成果摘要

CRAG-MM 已完成本地兼容层、A40 云端视觉模型、图片与网页联合检索、固定 50 条评测和
两轮检索可靠性优化。项目当前具备可复现的小范围实验流程，并在本地与云端通过 47 项
unittest。

固定 50 条旧版 DeepSeek 对照结果为：正确 15、弃答 27、错误 8，Truthfulness `0.14`。
本轮优化候选结果根据未变答案的旧标签和变化答案人工复核，保守估计为：正确 16、弃答
27、错误 7，Truthfulness `0.18`。候选回答覆盖率仍为 46%，已回答样本正确率由约
65.2% 提高到约 69.6%。该估计尚未重新调用 DeepSeek，也不代表官方 `gpt-4o` 分数。

候选结果：

`../artifacts/crag_v0.1.2_slice50/results_both_retrieval_optimized_candidate_50.json`

## 2. 第一阶段：环境、云端和视觉模型

第一阶段完成了本地开发与云端推理基础设施。

### 本地环境

- 建立 Windows 轻量环境 `.venv-light`。
- 将依赖拆分为 `requirements-local.txt`、`requirements-cloud.txt` 和
  `requirements-api.txt`。
- 增加 `utils/search_pipeline_compat.py`，将 Web-only 和 Image-only 搜索兼容修复
  固化到仓库，不再依赖修改 `site-packages`。
- 增加环境检查、检索基准和回归测试工具。

### 云端环境

- 平台：矩池云 1 区。
- GPU：NVIDIA A40 48GB。
- 模型：`Llama-3.2-11B-Vision-Instruct`，BF16。
- 云端模型和依赖按固定版本运行，避免 Transformers 5.x 等版本破坏 vLLM 兼容性。
- 模型权重通过 Hugging Face 官方签名 URL 和官方 CDN 获取；模型、缓存和索引均已保存在
  云端快照中。

### 首次推理结果

- 模型权重约占 19.91 GiB 显存。
- 激活峰值约 1.03 GiB。
- KV Cache 约 19.29 GiB。
- 首次输出速度约 14.26 tokens/s。
- 单图测试正确识别白底图中的蓝色方块和橙色圆形。

该阶段建立了稳定的本地测试、云端部署和单图推理链路。

## 3. 第二阶段：联合检索与固定 50 条基线

第二阶段完成图片索引、网页索引、实体改写和固定 validation 前 50 条联合检索评测。

### 检索链路

- CLIP 负责图片近邻检索。
- BGE-large-en-v1.5 负责网页向量检索。
- Llama 负责图像实体提取与最终回答。
- DeepSeek Flash 仅负责回答后的文本语义裁判。

图片上下文由约 8KB 的长属性压缩为去重候选实体名，并加入相似度和重复次数门控。网页
检索加入实体改写、结果数量限制和上下文字符上限。完整网页索引含 1,681,350 条记录，
云端冷启动约 152～157 秒，首条查询约 0.28 秒。

### 固定 50 条旧版结果

| 指标 | 结果 |
|---|---:|
| 样本数 | 50 |
| 弃答 | 27（54%） |
| 接受实体改写 | 10（20%） |
| 平均 token F1 | 0.1812 |
| DeepSeek 正确 | 15 |
| DeepSeek 错误 | 8 |
| DeepSeek Truthfulness | 0.14 |
| 已回答样本正确率 | 65.2% |

旧版 8 条错误集中在实体指向、实体粒度和网页证据串线：样本
00、07、16、21、26、27、29、37。

## 4. 第三阶段：实体定位与证据可靠性优化

第三阶段围绕 8 条错误和高风险非弃答样本开展小范围实验，再回归固定 50 条。

### 4.1 未采用的方案

强化自然语言警告能把部分错误转为弃答，但导致正确答案退化。同一 Llama 的独立证据审计
在 10 条原正确对照中仅保留 1 条，正确答案保留率为 10%。这两种策略均已从默认流程
移除。实验产物保留用于复盘：

- `results_both_retrieval_guardrails_target17.json`
- `results_both_retrieval_guardrails_verify_target12.json`
- `results_both_retrieval_guardrails_verify_correct10.json`

### 4.2 保留的改进

1. `--positions`
   - 直接按原清单位置运行目标样本。
   - 避免复制清单和误扩大评测范围。

2. `--rewrite-multicrop`
   - 先执行原全图实体识别。
   - 全图实体可靠时保持原结果。
   - 实体为空或代际问题只得到单词级品牌时，再检查下部、左右、左右下部和中心裁剪。
   - 最终实体需要跨裁剪重复或获得图片索引支持。

3. `--dual-web-query`
   - 仅对显式包含 `versus` 的问题启用。
   - 合并实体改写查询和原问题查询，保留比较双方证据。

4. `--concise-boolean-answers`
   - yes/no 问题保留核心结论，删除 `as`、`because` 后的风险解释。
   - `versus` 回答每个比较侧只保留第一个年份。

5. `--validate-numeric-evidence`
   - 答案新增数字必须出现在相关网页局部上下文中。
   - 问题指定国家等范围时，数字所在文档必须包含同一范围。
   - 英文数字词归一化为数字；用户问题中已有数字不重复校验。

6. `tools/finalize_slice_results.py`
   - 对已保存结果执行确定性后处理和指标重算。
   - 支持从目标实验结果覆盖指定位置，无需重复 GPU 生成。

### 4.3 关键样本变化

| 样本 | 旧结果 | 候选结果 | 结论 |
|---:|---|---|---|
| 00 | 结论正确但错误声称四座 | 只保留“不适合七人” | 错误转正确 |
| 11 | 弃答 | 正确回答火龙果皮可食用 | 弃答转正确 |
| 12 | 正确结论附错误年代 | 保留“未早于 Jaguar XK-E”结论 | 仍有车型识别风险，保守记错 |
| 27 | 只回答 Hello Kitty 且日期不完整 | `1985 vs 1974` | 错误转正确 |
| 37 | 使用 Honda 品牌总销量 | 识别 Honda HR-V，但错误美国数字被范围校验拦截 | 错误转弃答 |
| 42 | 弃答 | 给出更新历史但未回答四代 | 新增错误 |
| 49 | 回答正确但被截断且含多组数字 | 数值证据校验后弃答 | 正确转弃答 |

### 4.4 候选 50 条指标

| 指标 | 旧版 | 优化候选 |
|---|---:|---:|
| 弃答 | 27 | 27 |
| 实体改写 | 10 | 20 |
| 平均 token F1 | 0.1812 | 0.1781 |
| 保守估计正确 | 15 | 16 |
| 保守估计错误 | 8 | 7 |
| 保守估计 Truthfulness | 0.14 | 0.18 |
| 已回答样本正确率 | 65.2% | 69.6% |

Token F1 略降，原因是布尔题回答被压缩为核心结论。语义正确率和错误数更适合衡量本轮
优化目标。

## 5. 当前产物

### 正式基线

- `results_both_retrieval_final_50.json`
- `deepseek_flash_judgments.json`
- `docs/slice50_automatic_report_2026-11-20.md`
- `docs/manual_review_slice50_2026-11-20.md`

### 第三阶段产物

- `results_both_retrieval_multicrop_numeric_final_50.json`
- `results_both_retrieval_optimized_candidate_50.json`
- `results_both_retrieval_multicrop_target12.json`
- `results_both_retrieval_multicrop_v2_target6.json`
- `results_both_retrieval_numeric_guard_target5.json`
- `results_both_retrieval_final_features_target4.json`
- `docs/guardrail_experiment_2026-11-20.md`

## 6. 当前边界与下一阶段入口

候选 50 条需要新的 DeepSeek 裁判结果才能形成可与旧版直接比较的自动语义分数。`.env`
中的 Key 不进入聊天、日志或仓库；后续可由用户执行裁判命令，或先将 Key 安全注入进程环境。

完成裁判后按以下顺序推进：

1. 若候选 Truthfulness 高于 `0.14` 且错误数下降，固定候选策略。
2. 扩大到 100 或 200 条 validation 子集。
3. 根据新增错误区分实体定位、网页排序和回答证据问题。
4. 稳定后再考虑完整 validation 和官方 `gpt-4o` 裁判。

当前云端 GPU 已释放为 0 MiB / 0%，没有后台推理进程。实例按用户要求保持运行。
