# CRAG-MM 竞赛化改进接手指南：拒答门控、快速多裁剪、OCR、问题路由与实体一致性

日期：2026-11-24（Asia/Shanghai）

本指南用于从当前工作区继续改进 CRAG-MM Task 2（single-turn、多源检索）。当前工作停止在
“OCR、问题路由、实体一致性原型完成并跑完 200 条对照，但尚未正式进入主线”的位置。

## 1. 接手前必须知道的结论

当前最可靠、已经通过离线验证的竞赛化改进是：

1. 使用 2×2 contact sheet 代替八个串行裁剪；
2. 最终回答限制为 75 tokenizer tokens；
3. 使用只在位置 0–199 训练的轻量拒答门控；
4.
5. 比赛对齐阈值为 `0.415`。

当前推荐主线候选是“快速 contact-sheet + 阈值 0.415 的拒答门控”。

结构化 OCR/路由/实体一致性原型已经实现并完成 200 条评测，但它改变了特征分布，直接叠加旧
门控后的分数低于推荐主线，因此暂时只能视为实验分支，不能直接跑全量或覆盖最终结果。

## 2. 官方比赛约束

- 核心模型必须为允许的 Llama 系列；其他辅助模型参数量必须小于约 1.6B。
- 单轮严格 10 秒预算，任一轮超时可能导致整个提交失败。
- 自动评测只使用回答前 75 BPE token。
- 自动 Truthfulness 近似为 `Accuracy - Hallucination`。
- 正式排名按领域宏平均，而不是只看样本微平均。
- 高弃答率可能影响最终人工评审，因此不能简单全部输出 `I don't know.`。

## 3. 当前完整基线

完整 validation 共 1,938 条：

| 版本 | 正确 | 弃答 | 错误 | 微平均 Truthfulness | 领域宏平均 |
|---|---:|---:|---:|---:|---:|
| 原始全量 | 617 | 766 | 555 | 0.0320 | 0.0548 |
| 比赛对齐门控，阈值 0.415 | 473 | 1161 | 304 | 0.0872 | 0.1046 |

门控后错误率约为 `15.69%`，已接近“先降到 15% 左右”的第一阶段目标，但仍高于头部方案常见的
约 9%–13%。

完整产物：

```text
artifacts/crag_v0.1.2_full_blind_cloud/results_full_1938.json
artifacts/crag_v0.1.2_full_blind_cloud/deepseek_flash_judgments_full_1938.json
artifacts/crag_v0.1.2_full_blind_cloud/refusal_gate_calibration.json
artifacts/crag_v0.1.2_full_blind_cloud/results_full_1938_gated_official.json
artifacts/crag_v0.1.2_full_blind_cloud/deepseek_flash_judgments_full_1938_gated_official.json
artifacts/crag_v0.1.2_full_blind_cloud/refusal_gate_metrics_1938.json
docs/full_validation_report_2026-11-23.md
docs/refusal_gate_full_report_2026-11-23.md
```

## 4. 200 条速度与质量实验

实验区间为数据集位置 200–399。

### 4.1 原串行多裁剪

| 指标 | 结果 |
|---|---:|
| 正确 / 弃答 / 错误 | 60 / 81 / 59 |
| Truthfulness | 0.005 |
| 平均端到端时间 | 9.754s |
| P50 / P95 | 10.418s / 13.126s |
| 最大 | 27.192s |
| 超过 10 秒 | 138/200 |

该版本不满足比赛时间限制。

### 4.2 快速 contact-sheet

| 指标 | 原始 | 加阈值 0.415 门控 |
|---|---:|---:|
| 正确 | 63 | 56 |
| 弃答 | 82 | 107 |
| 错误 | 55 | 37 |
| Truthfulness | 0.040 | 0.095 |

速度：

```text
平均 3.427s
P50 3.177s
P95 5.024s
最大 8.359s
超过 10 秒：0/200
```

这是当前推荐主线。

产物：

```text
artifacts/crag_v0.1.2_full_blind_cloud/results_fast_contact_200_399.json
artifacts/crag_v0.1.2_full_blind_cloud/deepseek_flash_judgments_fast_contact_200_399.json
artifacts/crag_v0.1.2_full_blind_cloud/results_fast_contact_200_399_gated.json
artifacts/crag_v0.1.2_full_blind_cloud/deepseek_flash_judgments_fast_contact_200_399_gated.json
```

### 4.3 结构化 OCR、路由、实体一致性原型

| 指标 | 原始 | 加旧门控 |
|---|---:|---:|
| 正确 | 54 | 48 |
| 弃答 | 105 | 118 |
| 错误 | 41 | 34 |
| Truthfulness | 0.065 | 0.070 |

速度：

```text
平均 3.808s
P50 3.589s
P95 5.652s
最大 8.096s
超过 10 秒：0/200
```

结构化输出统计：

```text
route: identity 62, visual 54, lookup 49, ocr 24, comparison 9, chart 2
OCR 非空：9/200
实体一致性通过：95/200
启用网页检索：67/200
confidence: high 120, low 46, 未输出 34
```

解释：结构化路由把错误从 55 降到 41，但也把正确从 63 降到 54。最大问题是它只让 67/200
使用网页检索，路由过于激进；同时 Llama 自身 OCR 只在 9/200 条产生有用文本。旧门控基于原始
策略训练，不能直接适配这个新特征分布。

产物：

```text
artifacts/crag_v0.1.2_full_blind_cloud/results_structured_ocr_200_399.json
artifacts/crag_v0.1.2_full_blind_cloud/deepseek_flash_judgments_structured_ocr_200_399.json
artifacts/crag_v0.1.2_full_blind_cloud/results_structured_ocr_200_399_gated.json
artifacts/crag_v0.1.2_full_blind_cloud/deepseek_flash_judgments_structured_ocr_200_399_gated.json
```

## 5. 已修改的核心代码

### `tools/evaluate_vlm_slice.py`

新增：

- `--fast-multicrop`
- `--structured-visual-analysis`
- `--answer-token-limit`，默认 75
- `--refusal-gate-config`
- `--refusal-gate-threshold`
- 2×2 contact-sheet 生成
- 结构化 `<entity>`、`<ocr>`、`<route>`、`<confidence>` 解析
- 基础问题路由
- OCR—实体一致性检查
- 本地拒答门控接入
- JSONL 检查点与 `--resume`

### `tools/calibrate_refusal_gate.py`

- 从推理时可获得的实体、候选、证据覆盖、回答长度、数字、问题形式和耗时特征训练 NumPy
  logistic gate；
- 当前训练区间为位置 0–199；
- 五折 OOF 潜力 Truthfulness 为 `0.1109`，但不能当作真正盲测成绩。

### `tools/apply_refusal_gate.py`

- 可针对任意新结果重新提取特征，而不是复用旧位置的概率；
- 支持显式 `--threshold 0.415`。

## 6. OCR/路由门控工程（已完成）

本节三项任务已于 2026-11-24 完成：

- 已新增独立 `--route-web-retrieval`；`--structured-visual-analysis` 默认不再关闭网页检索；
- OCR、route、confidence、实体一致性和网页路由状态已加入拒答门控特征；
- 已新增 `--dev-start`，支持用 200–399 训练门控并用于后续区间；
- 已增加新旧特征 schema 对齐，旧门控配置仍可用于快速 contact-sheet；
- 已生成 `artifacts/crag_v0.1.2_full_blind_cloud/structured_gate_200_399.json`；
- 完整 65 项 unittest 通过。

结构化新门控在训练区间 200–399 的结果：

```text
正确 50
弃答 143
错误 7
Truthfulness 0.215
已回答准确率 87.72%
```

五折 OOF 结果：

```text
正确 40
弃答 134
错误 26
Truthfulness 0.070
```

训练内 `0.215` 明显包含过拟合，只能把 OOF `0.070` 作为当前泛化预警；必须继续执行第 7 节
400–599 held-out，不能直接用训练内成绩覆盖主线。

### 6.1 已完成：独立网页路由开关

不要直接把现有 `--structured-visual-analysis` 合并到主线。先把“视觉分析”和“网页开关”解耦。

### 6.1 增加单独的网页路由开关

在 `tools/evaluate_vlm_slice.py` 增加：

```python
parser.add_argument(
    "--route-web-retrieval",
    action="store_true",
    help="Allow the question router to disable web retrieval.",
)
```

把当前逻辑：

```python
if args.structured_visual_analysis:
    ...
    if question_route in {"identity", "visual", "chart"} or direct_ocr:
        use_web_retrieval = False
```

改为：

```python
if args.structured_visual_analysis and args.route_web_retrieval:
    ...
```

第一轮 hybrid 实验只使用结构化实体、OCR 和一致性，不关闭网页检索。原因是当前路由错误地使
133/200 条失去网页证据，正确答案损失过多。

### 6.2 已完成：结构化特征加入拒答门控

在 `tools/calibrate_refusal_gate.py::extract_features()` 增加：

```python
add("has_visible_text", bool(result.get("visible_text")))
add("visible_text_token_count", len(tokens(result.get("visible_text", ""))))
add("entity_consistency_valid", result.get("entity_consistency_valid", False))
add("web_retrieval_routed", result.get("web_retrieval_routed", True))
add("confidence_high", result.get("visual_confidence") == "high")
add("confidence_low", result.get("visual_confidence") == "low")
for route in ("identity", "visual", "ocr", "lookup", "comparison", "chart"):
    add(f"route_{route}", result.get("question_route") == route)
```

旧门控不能继续使用，因为增加特征后 schema 会变化，必须重新训练。

### 6.3 已完成：用 200–399 训练结构化门控

当前 `calibrate_refusal_gate.py` 默认只支持 `position < dev_count`。增加参数：

```python
parser.add_argument("--dev-start", type=int, default=0)
```

把：

```python
dev_mask = positions < args.dev_count
```

改为：

```python
dev_mask = (
    (positions >= args.dev_start)
    & (positions < args.dev_start + args.dev_count)
)
```

阈值选择也要使用对应位置 mask，不能继续切 `[:dev_count]`。

训练命令示意：

```powershell
.\.venv-light\Scripts\python.exe tools\calibrate_refusal_gate.py `
  --results artifacts\crag_v0.1.2_full_blind_cloud\results_structured_ocr_200_399.json `
  --judgments artifacts\crag_v0.1.2_full_blind_cloud\deepseek_flash_judgments_structured_ocr_200_399.json `
  --output artifacts\crag_v0.1.2_full_blind_cloud\structured_gate_200_399.json `
  --dev-start 200 `
  --dev-count 200
```

## 7. 独立验证区间 400–599（已完成，未通过）

2026-11-25 已完成本节。新 hybrid + 新门控在 held-out 400–599 得到：正确 40、弃答 130、
错误 30、Truthfulness `0.050`。对照旧策略 + 0.415 门控为 `0.085`，下降 `0.035`，超过允许
的 `0.01`，因此未进入主线。完整结论见 `stage7_hybrid_heldout_2026-11-25.md`。

结构化规则和新门控只能在 200–399 上开发。最终选择必须在未参与选择的位置 400–599 验证。

`crag_v0.1.2_full_blind_cloud/manifest.json` 的本地位置 0 对应数据集位置 200，因此数据集
400–599 对应 manifest positions 200–399。

### 7.1 云端准备

矩池云地址会变化，始终复制实例页面最新命令：

```powershell
$CragCloudHost = "当前主机"
$CragCloudPort = 12345
```

上传必要文件：

```powershell
scp -P $CragCloudPort `
  tools\evaluate_vlm_slice.py `
  tools\calibrate_refusal_gate.py `
  root@${CragCloudHost}:/root/CRAG-MM/tools/

scp -P $CragCloudPort `
  artifacts\crag_v0.1.2_full_blind_cloud\structured_gate_200_399.json `
  root@${CragCloudHost}:/root/CRAG-MM/artifacts/crag_v0.1.2_full_blind_cloud/
```

### 7.2 运行 hybrid held-out

```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate cragmm
cd /root/CRAG-MM

export VLLM_TENSOR_PARALLEL_SIZE=1
export VLLM_GPU_MEMORY_UTILIZATION=0.85
export VLLM_MAX_MODEL_LEN=8192
export VLLM_MAX_NUM_SEQS=1
export VLLM_AGENT_BATCH_SIZE=1
export VLLM_MAX_GENERATION_TOKENS=128
export VLLM_DTYPE=bfloat16
export VLLM_ENFORCE_EAGER=true

POSITIONS=$(seq -s, 200 399)

python tools/evaluate_vlm_slice.py \
  --manifest artifacts/crag_v0.1.2_full_blind_cloud/manifest.json \
  --positions "$POSITIONS" \
  --output artifacts/crag_v0.1.2_full_blind_cloud/results_hybrid_400_599.json \
  --model-name /root/models/Llama-3.2-11B-Vision-Instruct \
  --max-tokens 128 \
  --answer-token-limit 75 \
  --image-retrieval \
  --web-retrieval \
  --hf-home /root/hf_cache \
  --offline \
  --rewrite-web-query \
  --rewrite-multicrop \
  --fast-multicrop \
  --structured-visual-analysis \
  --validate-numeric-evidence \
  --concise-boolean-answers \
  --dual-web-query \
  --refusal-gate-config artifacts/crag_v0.1.2_full_blind_cloud/structured_gate_200_399.json \
  --refusal-gate-threshold 0.415
```

第一轮不要加 `--route-web-retrieval`，即保留网页检索，只使用 OCR/一致性和新门控。

### 7.3 下载与裁判

```powershell
scp -P $CragCloudPort `
  root@${CragCloudHost}:/root/CRAG-MM/artifacts/crag_v0.1.2_full_blind_cloud/results_hybrid_400_599.json `
  artifacts\crag_v0.1.2_full_blind_cloud\results_hybrid_400_599.json

.\.venv-light\Scripts\python.exe tools\judge_slice_results.py `
  --input artifacts\crag_v0.1.2_full_blind_cloud\results_hybrid_400_599.json `
  --output artifacts\crag_v0.1.2_full_blind_cloud\deepseek_flash_judgments_hybrid_400_599.json `
  --model deepseek-flash `
  --base-url https://api.deepseek.com
```

用户已经明确授权将完整公开 CRAG-MM 的问题、参考答案和模型回答发送给 DeepSeek 裁判。API Key
仍只从 `.env` 读取，不得写入命令、文档或 Git。

## 8. 接受标准

OCR/路由/一致性 hybrid 只有同时满足以下条件才能替代当前推荐主线：

```text
held-out count == 200
judge_errors == 0
P95 < 9s
max < 10s
超过 10 秒 == 0
Truthfulness >= 快速 contact-sheet + 旧门控基线 - 0.01
错误数 <= 对照错误数
已回答准确率不下降超过 3 个百分点
```

建议目标：

```text
Truthfulness >= 0.10
错误 <= 35/200
弃答率 <= 65%
```

若未通过：

- 保留快速 contact-sheet；
- 保留 75-token；
- 保留阈值 0.415 的旧门控；
- 结构化 OCR/路由只保留为消融实验，不再继续烧 GPU。

## 9. OCR 下一步建议

当前 Llama contact-sheet OCR 只有 9/200 条非空，能力不足。若继续提升 OCR，应使用小于 1.6B 的
独立 OCR，而不是继续强化自然语言提示。

推荐流程：

1. 只对 `ocr` route 或包含 brand/logo/label/calories/sugar/model/sign/book 的问题触发；
2. 对原图、下半部、中心和左右细节运行 OCR；
3. 去重并保留最高置信文本；
4. OCR 只作为实体一致性和 query rewrite 证据，不直接当事实答案；
5. OCR 文本与车型数字、年份或包装名冲突时，实体必须降级为 unresolved；
6. 单条 OCR 预算控制在 0.5–1.0 秒，确保 P95 仍低于 9 秒。

可考虑 PaddleOCR mobile/轻量模型，但需要把权重、版本和许可证固定并纳入提交包。不要在比赛运行时
访问外网。

## 10. 当前阶段之后的路线

完成本指南的 held-out 验证后，下一阶段才是：

1. 多查询召回；
2. 小于 1.6B 的 reranker；
3. 实体、国家、年份、单位和属性过滤；
4. 构造 hard negatives；
5. 对 Llama 做 LoRA/SFT/DPO 弃答训练；
6. 在新数据或 multi-turn split 上验证，避免继续对 validation 过拟合。

不要在 OCR/路由版本未通过 held-out 前开始全量重跑或 LoRA。

## 11. 测试与故障恢复

本地测试：

```powershell
.\.venv-light\Scripts\python.exe -m unittest discover -s tests -v
```

结构化相关测试当前为 37 项通过；完整测试应至少 65 项左右，具体随新增测试变化。

云端地址失效时：

- 按用户要求立即停止尝试；
- 不创建新空白实例；
- 等用户提供最新 SSH；
- JSONL 检查点使用 `--resume`；
- 不删除模型、索引、快照或已完成结果。

## 12. 工作区注意事项

- 工作区本来就有大量历史删除和未提交修改，不要 `git reset --hard`。
- `learning-plan.md` 在接手前已删除，不要恢复。
- `.matpool_known_hosts` 是临时 SSH host-key 文件，不应提交。
- 本地两个重复传输 tar 约 3.44 GiB，尚未获删除授权；不要擅自删除。
- DeepSeek 有轻微裁判波动，比较实验时尽量使用同一模型、同一提示和完整重跑。
- 原始全量结果和完整裁判必须永久保留，任何改进版都使用新文件名。

## 13. 当前云端状态

本轮最后使用过的地址：

```text
ssh -p 26897 root@hz-t3.matpool.com
```

该地址可能随暂停/恢复变化。结构化 200 条实验结束后 GPU 应为 0 MiB；接手时先检查，不要假设地址
或进程仍有效。

## 14. 最短接手清单

```text
[ ] 完整阅读本指南
[ ] 本地完整测试
[ ] 分析 route/OCR/confidence/consistency 的 paired delta
[x] 将网页路由开关从 structured analysis 中解耦
[x] 将结构化特征加入 refusal gate
[x] 支持 --dev-start 200 并重训 gate
[ ] 在 400–599 做 held-out hybrid
[ ] 验证 P95/max/超时数量
[ ] DeepSeek 裁判并对照接受标准
[ ] 通过才进入多查询和 reranker；未通过则回退 fast+旧 gate
```
