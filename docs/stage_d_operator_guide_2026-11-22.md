# CRAG-MM 阶段 D 操作指南：从 validation 前 100 条扩大到前 200 条

日期：2026-11-22（Asia/Shanghai）

本指南供后续接手者执行。阶段 D 尚未启动；不要因为阅读本指南而自动运行云端推理。

## 1. 唯一目标与固定基线

目标是评测官方 `v0.1.2` validation 前 200 条，但只新增准备和运行第 100–199 位。

必须冻结的前 100 条结果：

```text
artifacts/crag_v0.1.2_slice100/results_stage_c_repaired_100.json
```

对应 DeepSeek 裁判：

```text
artifacts/crag_v0.1.2_slice100/deepseek_flash_judgments_stage_c_repaired_100.json
```

阶段 C 最终指标：正确 48、弃答 38、错误 14、裁判错误 0、Truthfulness `0.34`。

基线 SHA-256：

```text
results:   093e9b847fb31bf2b8aee10ec69243767770bfbfda13a1db39a92018a5cf2c90
judgments: fffe0c087a858b730d28fa68b30c1cbdd594d6cfa626ae86e609d621d7c7e212
```

开始前先验证：

```powershell
Get-FileHash artifacts\crag_v0.1.2_slice100\results_stage_c_repaired_100.json -Algorithm SHA256
Get-FileHash artifacts\crag_v0.1.2_slice100\deepseek_flash_judgments_stage_c_repaired_100.json -Algorithm SHA256
```

若哈希不一致，先停止并确认原因。不要覆盖或“重新生成”前 100 条。

## 2. 执行纪律

- 不重新运行位置 0–99 的 Llama 推理。
- 只导出和上传 `100.jpg`–`199.jpg`。
- 第 100–199 位必须在同一个模型和索引进程中完成。
- 不运行位置 200 或更后的数据。
- 不重建 Conda、模型、网页索引或图片索引。
- 不进行大范围提示词实验或无关重构。
- 首轮失败时，只分析 100–199 的错误和弃答，最多进行一轮定向修复。
- 除非发现明确的数据损坏或回归，不修改已经冻结的前 100 条答案。
- 阶段结束时最多生成一份阶段 D 报告，并只更新一次 `HANDOFF.md`。

## 3. 本地环境检查

仓库：

```text
D:\CODE\Rainys-CRAG-MM
```

运行回归测试：

```powershell
cd D:\CODE\Rainys-CRAG-MM
.\.venv-light\Scripts\python.exe -m unittest discover -s tests -v
```

当前应至少通过 60 项测试。工作区本来就包含大量未提交的历史整理改动；不要清理、重置或
恢复这些文件，尤其不要恢复 `learning-plan.md` 和旧结果目录。

## 4. 只导出第 100–199 位

本机 Hugging Face 缓存内已有官方 validation parquet。先找到第一分片：

```powershell
Get-ChildItem "$env:USERPROFILE\.cache\huggingface\hub\datasets--crag-mm-2025--crag-mm-single-turn-public\snapshots\*\data\validation-00000-of-00005.parquet"
```

将实际路径代入 `$CragValidationParquet`，然后导出：

```powershell
$CragValidationParquet = "C:\Users\你的用户名\.cache\huggingface\hub\datasets--crag-mm-2025--crag-mm-single-turn-public\snapshots\实际快照ID\data\validation-00000-of-00005.parquet"
$env:HF_HOME = "D:\CODE\Rainys-CRAG-MM\.h"

.\.venv-light\Scripts\python.exe tools\export_crag_slice.py `
  --output-dir artifacts\crag_v0.1.2_slice200 `
  --start 100 `
  --count 100 `
  --parquet $CragValidationParquet
```

边界断言：

```powershell
$CragManifest = Get-Content -Raw artifacts\crag_v0.1.2_slice200\manifest.json | ConvertFrom-Json
$CragImages = Get-ChildItem artifacts\crag_v0.1.2_slice200 -Filter *.jpg | Sort-Object Name

"manifest_count=$($CragManifest.Count)"
"index_range=$($CragManifest[0].index)-$($CragManifest[-1].index)"
"image_count=$($CragImages.Count)"
"image_range=$($CragImages[0].Name)-$($CragImages[-1].Name)"
```

必须得到：

```text
manifest_count=100
index_range=100-199
image_count=100
image_range=100.jpg-199.jpg
```

任何一项不一致都不要上传。

## 5. 获取当前云端 SSH 地址

矩池云暂停/恢复后主机和端口会变化。不要复用文档中的旧地址。打开实例页面，复制当前
完整 SSH 命令，例如：

```text
ssh -p 当前端口 root@当前主机
```

以下命令使用占位变量：

```powershell
$CragCloudHost = "当前主机"
$CragCloudPort = 12345
```

只读检查云端：

```powershell
ssh -o BatchMode=yes -p $CragCloudPort root@$CragCloudHost `
  "hostname; nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv,noheader; test -d /root/CRAG-MM && echo repo_ok; pgrep -af 'evaluate_vlm_slice|python.*CRAG-MM' || true"
```

启动前应看到 A40、`repo_ok`、显存接近 0，且没有旧评测进程。

## 6. 上传新增数据和必要工具

```powershell
scp -P $CragCloudPort tools\evaluate_vlm_slice.py tools\export_crag_slice.py `
  root@${CragCloudHost}:/root/CRAG-MM/tools/

scp -P $CragCloudPort -r artifacts\crag_v0.1.2_slice200 `
  root@${CragCloudHost}:/root/CRAG-MM/artifacts/
```

云端边界检查：

```powershell
ssh -p $CragCloudPort root@$CragCloudHost
```

进入云端后：

```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate cragmm
cd /root/CRAG-MM

python - <<'PY'
import json
from pathlib import Path

p = Path("artifacts/crag_v0.1.2_slice200")
manifest = json.loads((p / "manifest.json").read_text())
images = sorted(p.glob("*.jpg"))
assert len(manifest) == 100
assert [item["index"] for item in manifest] == list(range(100, 200))
assert [item.name for item in images] == [f"{i:03d}.jpg" for i in range(100, 200)]
print("boundary_ok", len(manifest), manifest[0]["index"], manifest[-1]["index"])
PY

python -m unittest discover -s tests -v
```

## 7. 单进程运行第 100–199 位

继续在同一云端 shell 中：

```bash
export VLLM_TENSOR_PARALLEL_SIZE=1
export VLLM_GPU_MEMORY_UTILIZATION=0.85
export VLLM_MAX_MODEL_LEN=8192
export VLLM_MAX_NUM_SEQS=1
export VLLM_AGENT_BATCH_SIZE=1
export VLLM_MAX_GENERATION_TOKENS=128
export VLLM_DTYPE=bfloat16
export VLLM_ENFORCE_EAGER=true

python tools/evaluate_vlm_slice.py \
  --manifest artifacts/crag_v0.1.2_slice200/manifest.json \
  --output artifacts/crag_v0.1.2_slice200/results_stage_d_new_100.json \
  --model-name /root/models/Llama-3.2-11B-Vision-Instruct \
  --max-tokens 128 \
  --image-retrieval \
  --web-retrieval \
  --hf-home /root/hf_cache \
  --offline \
  --rewrite-web-query \
  --rewrite-multicrop \
  --validate-numeric-evidence \
  --concise-boolean-answers \
  --dual-web-query
```

预期冷启动：网页索引约 155 秒，检索总初始化约 163 秒，模型约 20–30 秒。脚本会写入：

```text
results_stage_d_new_100.json.partial.jsonl
```

该文件每完成一条增加一行。可在另一终端只读查看进度：

```powershell
ssh -p $CragCloudPort root@$CragCloudHost `
  "wc -l /root/CRAG-MM/artifacts/crag_v0.1.2_slice200/results_stage_d_new_100.json.partial.jsonl"
```

正常结束后检查点会删除，并生成 `results_stage_d_new_100.json`。必须确认：

```text
count == 100
positions == 100..199
max(position) == 199
```

### 已知故障

阶段 C 曾因小数 `2.75` 被错误当成年份而中止；当前代码已增加 `isdigit()` 判断和小数回归
测试。若再次异常，先保留 `.partial.jsonl`，直接说明影响，不要反复冷启动或删除检查点。

## 8. 下载新增结果

退出云端后在本地执行：

```powershell
scp -P $CragCloudPort `
  root@${CragCloudHost}:/root/CRAG-MM/artifacts/crag_v0.1.2_slice200/results_stage_d_new_100.json `
  artifacts/crag_v0.1.2_slice200/results_stage_d_new_100.json
```

## 9. 合并为 200 条时的强制要求

当前 `tools/merge_stage_c_results.py` 专门校验 `0–49 + 50–99`，不能直接用于阶段 D。
开始合并前，应先将其泛化或新增 `tools/merge_stage_d_results.py`。合并工具必须同时断言：

1. 基线结果位置严格为 `0..99`；
2. 新结果位置严格为 `100..199`；
3. 合并结果位置严格为 `0..199`，总数 200；
4. 合并后前 100 条 `agent_response` 与
   `results_stage_c_repaired_100.json` 逐字一致；
5. 输出记录基线文件 SHA-256；
6. 重新计算代理指标；
7. 不允许任何位置大于 199。

建议输出名：

```text
artifacts/crag_v0.1.2_slice200/results_stage_d_200.json
```

不要手工复制 JSON，不要用只按位置覆盖但不验证答案的脚本。

## 10. DeepSeek 200 条对照裁判

确认 `.env` 中存在 `DEEPSEEK_API_KEY`，不要打印 Key：

```powershell
"env_file=$(Test-Path .env)"
```

运行：

```powershell
.\.venv-light\Scripts\python.exe tools\judge_slice_results.py `
  --input artifacts\crag_v0.1.2_slice200\results_stage_d_200.json `
  --output artifacts\crag_v0.1.2_slice200\deepseek_flash_judgments_stage_d_200.json `
  --model deepseek-flash `
  --base-url https://api.deepseek.com
```

不要用现有 `--resume` 从另一个输出文件按位置盲目复用标签；当前实现只按位置复用，没有核验
问题、参考答案和模型答案是否完全一致。最安全做法是对最终 200 条重新运行一次裁判；若要
复用前 100 条，必须先修复复用逻辑并增加内容一致性测试。

## 11. 建议验收门槛

阶段 D 的正式门槛应由负责人在运行前确认。若继续沿用阶段 C 的比例，建议使用：

```text
count == 200
judge_errors == 0
correct >= 90
wrong <= 32
truthfulness_score >= 0.30
前 100 条答案与阶段 C 最终结果完全一致
没有运行第 200 条之后的数据
```

这些是建议值，不应在未确认时冒充既定要求。

## 12. 未通过时的唯一修复轮次

若未通过：

1. 不扩大到 400 或完整 validation；
2. 只列出位置 100–199 中的错误和弃答；
3. 优先处理可由图中文字、明确实体、确定性比较或可靠网页证据修复的条目；
4. 不用参考答案直接批量灌入回答；每条修复必须记录证据和原因；
5. 修复清单只能包含位置 100–199；
6. 最多应用一轮修复并重新裁判；
7. 前 100 条必须再次做逐字一致性断言。

## 13. 通过后的收尾

通过后立即停止，不自动扩大规模。只做以下工作：

- 生成一份 `docs/stage_d_completion_YYYY-MM-DD.md`；
- 更新一次 `HANDOFF.md`；
- 记录最终结果和裁判文件的 SHA-256；
- 本地运行完整 unittest 和 `git diff --check`；
- 云端确认 GPU `0 MiB / 0%`、无后台推理；
- 在矩池云控制台暂停实例以停止计费，不要释放或删除快照。

最终汇报应明确：是否通过、各项指标、是否使用定向修复、前 100 是否完全一致、最大运行
位置、是否建议继续扩大，以及云端实例是否已经暂停。
