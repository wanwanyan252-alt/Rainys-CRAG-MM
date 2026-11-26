# CRAG-MM 阶段 B 自主操作指南

日期：2026-11-22（Asia/Shanghai）

## 1. 阶段 B 目标

阶段 B 对阶段 A 生成的 50 条候选答案运行 DeepSeek Flash 语义裁判，生成自动报告和人工
复核清单，并判断是否达到进入 100 条评测的门槛。

验收门槛：

- 正确答案不少于 24 条；
- 错误答案不超过 8 条；
- 裁判错误为 0；
- Truthfulness 不低于 `0.32`。

阶段 B 是 API 裁判任务，不需要 Llama、网页索引或 GPU。建议在 Windows 本地仓库执行。

## 2. 在哪里输入命令

阶段 B 涉及四个界面。不要混用。

| 界面 | 用途 | 输入内容 |
|---|---|---|
| Windows PowerShell | 执行阶段 B 的全部命令 | 本指南中的 PowerShell 代码块 |
| VS Code 或记事本 | 检查或编辑本地 `.env` | `DEEPSEEK_API_KEY=...` |
| Codex 对话框 | 汇报结果、粘贴错误信息、请求下一步 | summary、错误位置、命令报错；不发送 Key |
| 矩池云实例页面 | 查看最新 SSH 命令、暂停实例 | 不执行阶段 B 裁判 |

### 2.1 打开 PowerShell

在 Windows 中使用以下任一方式：

1. 按 `Win + X`，选择“终端（管理员）”或“Windows PowerShell”；
2. 在开始菜单搜索 `PowerShell`；
3. 在 VS Code 中选择“终端 → 新建终端”，确认终端类型为 PowerShell。

PowerShell 提示符通常类似：

```text
PS C:\Users\你的用户名>
```

先进入仓库：

```powershell
cd D:\CODE\Rainys-CRAG-MM
```

进入成功后提示符应类似：

```text
PS D:\CODE\Rainys-CRAG-MM>
```

本指南后续所有标有 `powershell` 的代码块均粘贴到这个窗口执行。

### 2.2 多行 PowerShell 命令的粘贴方式

命令末尾的反引号 `` ` `` 表示下一行仍属于同一条命令。直接复制整个代码块并一次性粘贴。
反引号后不能有空格。

如果多行粘贴失败，将命令整理成一行执行。例如：

```powershell
.\.venv-light\Scripts\python.exe tools\judge_slice_results.py --input artifacts\crag_v0.1.2_slice50\results_stage_b_candidate_50.json --output artifacts\crag_v0.1.2_slice50\deepseek_flash_judgments_stage_b_50.json --model deepseek-flash --base-url https://api.deepseek.com
```

### 2.3 Codex 对话框中输入什么

命令执行完成后，在当前 Codex 对话框发送：

```text
阶段 B 裁判完成
summary: （粘贴 summary）
judge_errors: （粘贴数量）
错误样本位置: （粘贴位置列表）
```

若命令失败，在对话框粘贴报错文本。发送前删除 API Key、Authorization 请求头和 `.env`
内容。

### 2.4 哪些内容不能输入到对话框

- `DEEPSEEK_API_KEY` 的实际值；
- `.env` 全文；
- 带 Key 的命令或截图；
- 矩池云密码、临时下载地址或访问令牌。

## 3. 输入与输出

### 输入

```text
artifacts/crag_v0.1.2_slice50/results_stage_b_candidate_50.json
```

该文件包含 50 条结果，预期代理指标：

```text
count: 50
abstention_count: 19
abstention_rate: 0.38
mean_token_f1: 0.2474
```

### 输出

```text
artifacts/crag_v0.1.2_slice50/deepseek_flash_judgments_stage_b_50.json
docs/slice50_stage_b_report_2026-11-22.md
docs/manual_review_stage_b_2026-11-22.md
```

旧版文件必须保留：

```text
artifacts/crag_v0.1.2_slice50/results_both_retrieval_final_50.json
artifacts/crag_v0.1.2_slice50/deepseek_flash_judgments.json
```

## 4. 前置检查

输入位置：本地 Windows PowerShell。

打开 PowerShell：

```powershell
cd D:\CODE\Rainys-CRAG-MM
git status --short --branch
```

确认候选文件存在：

```powershell
Get-Item artifacts\crag_v0.1.2_slice50\results_stage_b_candidate_50.json
```

验证 JSON 和样本数：

```powershell
.\.venv-light\Scripts\python.exe -c "import json,pathlib; p=pathlib.Path(r'artifacts/crag_v0.1.2_slice50/results_stage_b_candidate_50.json'); d=json.loads(p.read_text(encoding='utf-8')); print('count=',len(d['results'])); print(d['proxy_metrics'])"
```

预期输出包含：

```text
count= 50
abstention_count: 19
```

运行本地测试：

```powershell
.\.venv-light\Scripts\python.exe -m unittest discover -s tests -v
```

预期：

```text
Ran 57 tests
OK
```

## 5. API Key 检查

输入位置：检查命令在本地 Windows PowerShell；`.env` 内容在 VS Code 或记事本中编辑。

裁判工具从 `.env` 读取 `DEEPSEEK_API_KEY`。`.env` 已被 Git 忽略。

只检查变量是否存在，不显示值：

```powershell
.\.venv-light\Scripts\python.exe -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DEEPSEEK_API_KEY configured=', bool(os.getenv('DEEPSEEK_API_KEY')))"
```

预期：

```text
DEEPSEEK_API_KEY configured= True
```

如果为 `False`，在 `.env` 中增加：

```text
DEEPSEEK_API_KEY=你的Key
```

保存后重新运行检查命令。不要在聊天、截图、终端历史或报告中输出 Key。

`.env` 的本地路径为：

```text
D:\CODE\Rainys-CRAG-MM\.env
```

不要在 PowerShell 中执行 `Get-Content .env`，避免 Key 出现在终端历史或截图中。

## 6. 运行 DeepSeek 裁判

输入位置：本地 Windows PowerShell。不要在 Codex 对话框中粘贴这条命令并要求代为运行，
因为裁判工具会读取本地 `.env`。

执行：

```powershell
.\.venv-light\Scripts\python.exe tools\judge_slice_results.py `
  --input artifacts\crag_v0.1.2_slice50\results_stage_b_candidate_50.json `
  --output artifacts\crag_v0.1.2_slice50\deepseek_flash_judgments_stage_b_50.json `
  --model deepseek-flash `
  --base-url https://api.deepseek.com
```

程序会逐条输出：

```text
{"position": 0, "score": 1, "source": "llm_judge"}
```

分数含义：

- `1`：正确；
- `0`：弃答；
- `-1`：错误。

正常结束时会输出 summary，并保存 JSON。

### 中断恢复

网络中断或 API 临时失败后，使用同一输出文件并增加 `--resume`：

```powershell
.\.venv-light\Scripts\python.exe tools\judge_slice_results.py `
  --input artifacts\crag_v0.1.2_slice50\results_stage_b_candidate_50.json `
  --output artifacts\crag_v0.1.2_slice50\deepseek_flash_judgments_stage_b_50.json `
  --model deepseek-flash `
  --base-url https://api.deepseek.com `
  --resume
```

`--resume` 会复用已完成裁判，只重试 `judge_error`。

## 7. 检查裁判结果

输入位置：本地 Windows PowerShell。

打印 summary：

```powershell
.\.venv-light\Scripts\python.exe -c "import json,pathlib; p=pathlib.Path(r'artifacts/crag_v0.1.2_slice50/deepseek_flash_judgments_stage_b_50.json'); d=json.loads(p.read_text(encoding='utf-8')); print(d['summary'])"
```

检查数量一致：

```powershell
.\.venv-light\Scripts\python.exe -c "import json,pathlib; p=pathlib.Path(r'artifacts/crag_v0.1.2_slice50/deepseek_flash_judgments_stage_b_50.json'); d=json.loads(p.read_text(encoding='utf-8')); print('judgments=',len(d['judgments'])); print('score_sum=',sum(x['score'] for x in d['judgments']))"
```

预期：

```text
judgments= 50
```

列出错误样本：

```powershell
.\.venv-light\Scripts\python.exe -c "import json,pathlib; p=pathlib.Path(r'artifacts/crag_v0.1.2_slice50/deepseek_flash_judgments_stage_b_50.json'); d=json.loads(p.read_text(encoding='utf-8')); print([(x['position'],x['query'],x['agent_response']) for x in d['judgments'] if x['score']==-1])"
```

列出裁判错误：

```powershell
.\.venv-light\Scripts\python.exe -c "import json,pathlib; p=pathlib.Path(r'artifacts/crag_v0.1.2_slice50/deepseek_flash_judgments_stage_b_50.json'); d=json.loads(p.read_text(encoding='utf-8')); print([x['position'] for x in d['judgments'] if x['source']=='judge_error'])"
```

预期输出：

```text
[]
```

若不为空，运行 `--resume`。

## 8. 生成报告与人工复核清单

输入位置：本地 Windows PowerShell。

```powershell
.\.venv-light\Scripts\python.exe tools\build_slice_report.py `
  --results artifacts\crag_v0.1.2_slice50\results_stage_b_candidate_50.json `
  --judgments artifacts\crag_v0.1.2_slice50\deepseek_flash_judgments_stage_b_50.json `
  --report docs\slice50_stage_b_report_2026-11-22.md `
  --review docs\manual_review_stage_b_2026-11-22.md `
  --date 2026-11-22
```

确认文件：

```powershell
Get-Item docs\slice50_stage_b_report_2026-11-22.md
Get-Item docs\manual_review_stage_b_2026-11-22.md
```

## 9. 优先人工复核

操作位置：在 VS Code、Codex 文件预览或 Markdown 编辑器中打开
`docs\manual_review_stage_b_2026-11-22.md`，逐条查看图片、问题、答案和 DeepSeek 标签。

先复核阶段 A 新增回答：

```text
01, 20, 28, 30, 33, 36, 47, 49
```

重点判断：

- 01：是否明确回答 5 加仑足够到达；
- 20：是否正确表达 1998 年时 370Z 尚未生产；
- 28：回答的 MyLink、蓝牙等功能是否可接受为参考答案的语义等价扩展；
- 30：是否覆盖洋葱的消化、抗氧化/抗癌等健康益处；
- 33：是否回答 Space Needle 可承受高于 1906 地震的震级；
- 36：basketball/WNBA 与 boxing 是否足以回答 “what sporting events”；
- 47：Andrea della Robbia 与 1435 是否正确；
- 49：是否精确回答男性 18–24 岁。

再复核现有高风险回答：

```text
00, 07, 12, 13, 16, 21, 26, 29, 34, 37, 42
```

人工标签规则：

- `1`：结论正确，回答问题所需字段；
- `0`：明确 `I don't know.`；
- `-1`：错误、无关、缺少关键比较侧或包含误导事实。

## 10. 与旧版比较

输入位置：本地 Windows PowerShell。

旧版 DeepSeek summary：

```powershell
.\.venv-light\Scripts\python.exe -c "import json,pathlib; old=json.loads(pathlib.Path(r'artifacts/crag_v0.1.2_slice50/deepseek_flash_judgments.json').read_text(encoding='utf-8')); new=json.loads(pathlib.Path(r'artifacts/crag_v0.1.2_slice50/deepseek_flash_judgments_stage_b_50.json').read_text(encoding='utf-8')); print('old=',old['summary']); print('new=',new['summary'])"
```

旧版基线：

```text
correct: 15
miss: 27
wrong: 8
truthfulness_score: 0.14
```

## 11. 验收决策

### 通过

同时满足：

- [ ] `count == 50`
- [ ] `judge_errors == 0`
- [ ] `correct >= 24`
- [ ] `wrong <= 8`
- [ ] `truthfulness_score >= 0.32`
- [ ] 新增 8 条回答已人工复核
- [ ] 报告和人工清单已生成

通过后进入 100 条子集评测。不要直接运行完整 validation。

### 未通过

任一核心指标未达到时：

1. 保留裁判 JSON，不覆盖；
2. 从 `score == -1` 的新增回答开始检查；
3. 将错误样本位置、问题、回答和裁判理由记录到阶段报告；
4. 不运行 100 条或完整 validation；
5. 把 summary 和错误样本列表发回项目对话，进入一次定向修正。

## 12. 云端与计费

阶段 B 在本地运行，不需要连接矩池云。若云端实例仍处于运行状态，会继续按时计费。

暂停实例的位置：矩池云网页控制台。不要在 PowerShell 中删除云端项目、模型或索引。

若准备暂停实例，先确认：

- [ ] 没有 Llama 推理进程；
- [ ] GPU 显存为 0 MiB；
- [ ] 最新代码与阶段 A 结果已同步；
- [ ] 保留实例快照，不删除模型和索引。

当前阶段 A 完成时 GPU 已释放，后台无推理进程。

## 13. 阶段 B 完成清单

- [ ] 候选 JSON 为 `results_stage_b_candidate_50.json`
- [ ] DeepSeek Key 检查为 True，且未输出 Key
- [ ] 50 条裁判全部完成
- [ ] `judge_errors == 0`
- [ ] 自动报告已生成
- [ ] 人工复核清单已生成
- [ ] 新增 8 条回答完成复核
- [ ] 与旧版 summary 完成对比
- [ ] 根据验收门槛作出通过/未通过决策
- [ ] 未运行完整 validation

## 14. 完成后在 Codex 对话框发送的模板

```text
阶段 B 已完成

DeepSeek summary:
- count: 50
- correct: __
- miss: __
- wrong: __
- judge_errors: __
- truthfulness_score: __

错误样本位置: [__]
报告已生成: 是/否
人工复核已完成: 是/否
```

发送这段结果后，我会根据验收门槛判断是否进入 100 条子集，或只修正新增错误样本。
