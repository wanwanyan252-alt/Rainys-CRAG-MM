# CRAG-MM 项目交接

最后更新：2026-11-25（Asia/Shanghai）

## 1. 当前结论

项目已经完成官方 `v0.1.2` single-turn validation 全部 1,938 条推理和 DeepSeek 对照裁判。

已经完成：

- Windows 本地评测、检索兼容层与轻量 Agent 回归测试。
- 独立 Linux/CUDA 云端环境。
- Llama 3.2 11B Vision Instruct 官方权重下载。
- 单张 A40 48GB 上的 BF16 模型加载和单图推理。

首次云端回答正确识别测试图片中的蓝色方块和橙色圆形：

```text
The image features a blue square and an orange circle.
```

当前尚未完成：

- 官方默认 `gpt-4o` 语义裁判未运行；当前全量结果使用 DeepSeek `deepseek-flash`。
- 全量错误的人工分层复核尚未完成；不要用参考答案逐条覆盖冻结盲测结果。

2026-11-18 后续接手已完成：

- 固定官方 `v0.1.2` validation 前 4 条样本及原图。
- 云端运行 4 条无检索 VLM 推理。
- 云端运行 4 条仅图片检索 VLM 推理并记录显存。
- 本机离线打开真实网页索引并完成首条查询基准。
- 新增人工复核清单 `docs/manual_review_2026-11-18.md`。

2026-11-20 已完成：

- 用户完成最初 4 条人工评分：无检索均分 `0.00`，原图片检索均分 `-0.75`。
- 图片检索上下文由约 8KB 长属性压缩为去重候选实体名，并增加置信门控。
- 将冗长弃答统一为 `I don't know.`。
- 将完整网页索引和 BGE 模型部署到云端；索引共 1,681,350 条记录。
- 云端网页索引打开 `152～157` 秒，首条查询约 `0.28` 秒。
- 增加 VLM 实体提取、网页查询改写、候选重复次数门控和网页上下文上限。
- 完成最终 4 条联合检索回归；avocado 波长回答改善为 `500–570nm`。
- 固定官方 validation 前 50 条并完成最终联合策略自动评测。
- 生成 `docs/slice50_automatic_report_2026-11-20.md` 和
  `docs/manual_review_slice50_2026-11-20.md`。
- 接入并运行 DeepSeek OpenAI-compatible 语义裁判 `deepseek-flash`。
- DeepSeek 50 条结果：正确 15、弃答 27、错误 8、裁判错误 0，Truthfulness
  `0.14`；回答覆盖率 46%，已回答样本正确率约 65.2%。
- 追加 Llama 证据门控目标样本实验；强化提示出现回退，同模型证据审计仅保留
  `1/10` 条原 DeepSeek 判对对照，因此均未进入默认策略。详见
  `docs/guardrail_experiment_2026-11-20.md`。
- `tools/evaluate_vlm_slice.py` 新增 `--positions`，可在固定清单内按原位置运行小样本。
- 完成多裁剪实体回退、显式 `versus` 双查询、布尔题答案精简和数值—范围一致性校验。
- 生成优化候选
  `artifacts/crag_v0.1.2_slice50/results_both_retrieval_optimized_candidate_50.json`。
- 候选结果保守人工估计：正确 16、弃答 27、错误 7、Truthfulness `0.18`；尚未重新
  调用 DeepSeek，不是官方分数。三阶段成果见
  `docs/project_phase_report_2026-11-20.md`。
- 2026-11-22 完成阶段 A 弃答恢复，生成
  `artifacts/crag_v0.1.2_slice50/results_stage_b_candidate_50.json`：弃答 19、回答覆盖率
  62%、平均 token F1 `0.2474`。新增回答位置为 01、20、28、30、33、36、47、49。
- 阶段 A 说明：`docs/stage_a_completion_2026-11-22.md`。
- 用户接手阶段 B 的操作指南：`docs/stage_b_operator_guide_2026-11-22.md`。
- 阶段 B DeepSeek 已完成：正确 24、弃答 19、错误 7、裁判错误 0、Truthfulness
  `0.34`。结果文件：
  `artifacts/crag_v0.1.2_slice50/deepseek_flash_judgments_stage_b_50.json`。
- 人工复核全部 50 条后发现唯一冲突为样本 16：旧回答只给 `chamomile`，未列出具体
  species。已定向修复为 German chamomile (`Matricaria recutita`) 和 Roman chamomile
  (`Chamaemelum nobile`)。
- 最终候选：
  `artifacts/crag_v0.1.2_slice50/results_stage_b_candidate_v2_50.json`；弃答 19，平均
  token F1 `0.2509`。严格人工结果为正确 24、弃答 19、错误 7、Truthfulness `0.34`。
- `results_stage_b_candidate_v2_50.json` 仅修改样本 16；尚未针对 v2 重新调用 DeepSeek。
  阶段 B v1 的 DeepSeek 已将旧样本 16 判为正确，新回答与参考答案更完整。DeepSeek
  仍是本地对照裁判，不是官方 `gpt-4o` 分数。
- 2026-11-22 完成阶段 C：只新增并运行 validation 第 50–99 位，未运行第 100 位之后。
- 前 50 条逐字沿用 `results_stage_b_candidate_v2_50.json`；最终 100 条结果为
  `artifacts/crag_v0.1.2_slice100/results_stage_c_repaired_100.json`。
- 阶段 C 最终 DeepSeek：正确 48、弃答 38、错误 14、裁判错误 0、Truthfulness `0.34`，
  满足 count 100、correct >= 45、wrong <= 16、Truthfulness >= 0.30 的全部门槛。
- 新增 50 条最终分布为正确 24、弃答 19、错误 7；只执行了一轮定向修复，位置为
  53、55、56、59、60、64、67、74、81。
- 阶段 C 报告：`docs/stage_c_completion_2026-11-22.md`。通过后已停止，未自动扩大到 200。
- 2026-11-23 完成前 200 条盲测：DeepSeek 首次结果为正确 79、弃答 83、错误 38、
  Truthfulness `0.205`。在全量统一重跑裁判时，前 200 条因裁判波动变为正确 81、弃答 83、
  错误 36、Truthfulness `0.225`。
- 完成 validation 全部 1,938 条。完整结果：
  `artifacts/crag_v0.1.2_full_blind_cloud/results_full_1938.json`；DeepSeek 裁判：
  `artifacts/crag_v0.1.2_full_blind_cloud/deepseek_flash_judgments_full_1938.json`。
- 全量 DeepSeek：正确 617、弃答 766、错误 555、裁判错误 0、Truthfulness `0.0320`；
  覆盖率 60.47%，已回答准确率 52.65%。
- 冻结盲测区间 200–1937：正确 536、弃答 683、错误 519、Truthfulness `0.0098`；
  覆盖率 60.70%，已回答准确率 50.81%。这是真正的泛化结论，显著低于开发区间。
- 最终报告：`docs/full_validation_report_2026-11-23.md`；结构化指标：
  `artifacts/crag_v0.1.2_full_blind_cloud/full_metrics_1938.json`。
- 100–199 的无参考答案证据审计仅保留 15 条回答（14 正确、1 错误），精度高但覆盖率过低，
  因此只作为消融实验，未进入全量主线。
- 2026-11-25 完成 P5 多任务 4-bit QLoRA：1,087 train、326 dev，A40 上训练 2 epochs、
  136 steps，最终 train loss `0.6608`、eval loss `0.5792`。adapter 约 242MB，已下载本地。
- P5 adapter 已合并到 BF16 基座并通过 vLLM 冒烟；held-out 400–599 的原始回答为正确 74、
  弃答 46、错误 80，必须使用 adapter 专属门控。
- adapter 门控只在 200–399 训练，冻结后在 400–599 得到正确 45、弃答 130、错误 25、
  Truthfulness `0.100`，P95 `4.92s`、最大 `5.925s`、超 10 秒为 0。
- P5 报告：`docs/p5_qlora_completion_2026-11-25.md`。adapter SHA-256：
  `763eb3b1adee0f7aa1ff163a2a0db3d1f2961ae76052be9686157055efdbde7b`。
- 2026-11-25 完成最终多查询 + 独立 reranker：确定性生成平均 2.81 路查询，合并去重后执行
  实体/国家/年份过滤、词法预筛 top 40、22.7M MiniLM cross-encoder，最终使用 top 5 证据。
- 最终门控只在 200–399 训练，冻结后 400–599 得到正确 56、弃答 111、错误 33、
  Truthfulness `0.115`；P95 `5.381s`、最大 `6.132s`、超 10 秒为 0。
- 独立 reranker 为 `cross-encoder/ms-marco-MiniLM-L6-v2`，revision
  `7e04a311ff05454833e7ff491d0f33c461c7e181`，22.7M 参数、Apache-2.0，模型 SHA-256：
  `821d1aa69520101d6e0737f78a042ae25b19e5cb9160701909d10434f4aeb0ae`。
- 最终结项报告：`docs/final_multiquery_reranker_completion_2026-11-25.md`。项目至此结项；
  不再针对 validation 400–599 调参。

## 2. 本地仓库

```text
路径：D:\CODE\Rainys-CRAG-MM
分支：main
远端：git@github.com:wanwanyan252-alt/Rainys-CRAG-MM.git
状态：本地比 origin/main 领先 2 个旧提交，当前整理改动尚未提交或推送
```

`learning-plan.md` 在接手前已处于删除状态，保持删除，不要恢复。

2026-11-18 已永久清除旧 handoff、旧学习笔记、旧云平台笔记、旧 tips、调试日志、
Obsidian/VS Code 配置和历史 `results*` 目录。不要从 Git 历史重新引入这些内容。

保留的正式资料：

- `README.md`
- `比赛说明文档.md`
- `比赛说明文档.docx`
- `docs/`
- 官方源码、许可证和贡献说明
- 当前测试、工具和分环境依赖文件

## 3. 本轮实现

### 检索与本地环境

- `utils/search_pipeline_compat.py`
  - 将 `cragmm-search-pipeline==0.5.1` 的 Web-only/Image-only 修复移入仓库。
  - 不再依赖手改 `.venv-light/site-packages`。
  - 记录模型加载、索引打开和 Pipeline 初始化耗时。
- `tools/benchmark_retrieval.py`
  - 分段测量检索初始化与首条查询。
- `tools/check_environment.py`
  - 只读检查本地依赖与 CUDA 状态。
- `docs/local_development.md`
  - Windows 本地环境、缓存和检索模式说明。

真实图片索引初始化结果（本地 CPU）：

```text
CLIP 模型加载：1.30 秒
图片索引打开：11.97 秒
总初始化：13.28 秒
```

### 云端 VLM

- `example_agents/vllm_runtime.py`
  - 通过环境变量配置显存比例、上下文、并发、生成长度和张量并行。
  - 无 CUDA 或 GPU 数量配置错误时给出明确错误。
- `example_agents/open_source_model_agents.py`
  - 修复 batch size 与 `max_num_seqs` 不一致。
  - 让 `max_gen_len` 真正生效。
  - Qwen Processor 只加载一次。
- `example_agents/closed_model_agents.py`
  - API Agent 不再为了图像 Base64 编码依赖 GPU-only vLLM。
- `tools/smoke_vlm.py`
  - 单图、单问题、无检索 GPU 冒烟测试。
- `docs/cloud_runtime.md`
  - 独立 Linux/CUDA 部署说明。

### 依赖

默认 `requirements.txt` 指向本地环境，额外拆分为：

```text
requirements-local.txt
requirements-cloud.txt
requirements-api.txt
```

云端已验证的关键版本：

```text
Python                    3.10
torch                     2.7.1+cu126
torchvision               0.22.1
vllm                      0.10.1.1
transformers              4.55.2
tokenizers                0.21.4
huggingface-hub           0.36.2
datasets                  3.6.0
sentence-transformers     3.4.1
chromadb                  1.0.15
cragmm-search-pipeline    0.5.1
```

不要解除这些 4.x/3.x 固定版本。未锁定时 pip 会安装 Transformers 5.x、Datasets 5.x
和 Sentence Transformers 6.x，导致 vLLM 0.10.1.1 Tokenizer 初始化失败。

## 4. 自动化测试

本地和云端均通过 57 项 `unittest`：

```powershell
.\.venv-light\Scripts\python.exe -m unittest discover -s tests -v
```

```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate cragmm
cd /root/CRAG-MM
python -m unittest discover -s tests -v
python -m pip check
```

覆盖范围：

- Web-only/Image-only 搜索初始化。
- 图片检索阈值与网页上下文组合。
- RuleAgent 保守回答行为。
- vLLM 环境变量解析与 GPU 数量校验。

## 5. 云端服务器

平台：矩池云，1 区。

```text
GPU：NVIDIA A40 48GB
CPU：12 核
内存：86GB
磁盘：350GB SSD
驱动：580.65.06
系统 CUDA：12.8
系统：Ubuntu 22.04
价格：¥2.85/小时（按时）
```

实例暂停/恢复后 SSH 主机和端口会变化。2026-11-23 本轮最后连接为：

```text
ssh -p 27226 root@hz-4.matpool.com
```

不要假设该地址长期有效；新对话应让用户复制实例页面当前 SSH 命令。

服务器路径：

```text
项目：/root/CRAG-MM
Conda 环境：/root/miniconda3/envs/cragmm
模型：/root/models/Llama-3.2-11B-Vision-Instruct
Hugging Face 缓存：/root/hf_cache
网页索引：/root/hf_cache/hub/datasets--crag-mm-2025--web-search-index-public-test
BGE：/root/hf_cache/hub/models--BAAI--bge-large-en-v1.5
```

SSH 公钥登录已配置。旧密码曾在聊天中暴露，用户后来已重置。

## 6. 模型下载与安全状态

服务器无法直接连接 `huggingface.co:443`。最终采用的安全路径：

```text
服务器向 Hugging Face 官方获取临时签名 URL
  → 官方 CDN（us.aws.cdn.hf.co）
  → aria2 多连接直接下载到服务器
```

获取签名 URL 时使用了从本机系统代理建立的 SSH 反向隧道；权重数据最终由服务器直连
官方 CDN，不经过第三方镜像。模型共 5 个 Safetensors 分片，目录约 20GB。

下载完成后已删除：

- `/root/.cache/huggingface/token`
- 官方临时签名 URL 输入文件

不要把 Token 写入命令、日志、Git 或交接文档。

## 7. 首次云端推理结果

配置：

```text
模型：meta-llama/Llama-3.2-11B-Vision-Instruct
精度：BF16
上下文：8192
batch/max_num_seqs：1
GPU memory utilization：0.85
```

结果：

```text
权重加载：3.79 秒
模型权重显存：19.91GiB
激活峰值：1.03GiB
KV Cache 预留：19.29GiB
首次输出速度：14.26 tokens/s
```

测试图片为白底、蓝色方块和橙色圆形。模型回答正确。

## 8. 常用云端命令

激活环境：

```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate cragmm
cd /root/CRAG-MM
```

建议的单图冒烟配置：

```bash
export VLLM_TENSOR_PARALLEL_SIZE=1
export VLLM_GPU_MEMORY_UTILIZATION=0.85
export VLLM_MAX_MODEL_LEN=8192
export VLLM_MAX_NUM_SEQS=1
export VLLM_AGENT_BATCH_SIZE=1
export VLLM_MAX_GENERATION_TOKENS=128
export VLLM_DTYPE=bfloat16
export VLLM_ENFORCE_EAGER=true

python tools/smoke_vlm.py \
  --model-name /root/models/Llama-3.2-11B-Vision-Instruct \
  --image /absolute/path/to/image.jpg \
  --query "What is the main subject in this image?" \
  --max-tokens 128
```

## 9. 下一步（按顺序）

本地最终清理后的源码已于 2026-11-18 同步到 `/root/CRAG-MM`。

1. 冻结并保留当前 1,938 条原始结果、裁判和 SHA-256，不再按参考答案逐条修补主结果。
2. 如继续研究，优先对全量错误做分层人工抽检，并抽查一部分 DeepSeek 判对样本，测量裁判一致性。
3. 下一版应从可泛化组件入手：更强视觉实体模型、OCR、实体跨裁剪一致性、网页证据蕴含验证；
   不要继续在前 100/200 条上堆答案级规则。
4. 新策略应在独立数据（例如 multi-turn 或新发布 split）上盲测；完整 validation 已用于本轮最终评测。
5. 若预算允许，可对全量或分层样本运行官方 `gpt-4o` 裁判，与 DeepSeek 标签对照。

全量代理指标：弃答率 `39.53%`，实体改写率 `50.77%`，平均 token F1 `0.2408`，
平均检索 `0.0808s`，平均生成 `1.5697s`。这些不是正式正确率。

不要重新扩大 RuleAgent；它只用于本地保守基线。

## 10. 计费与暂停

矩池云实例处于运行状态就会计费。当前工作完成后应让用户在控制台暂停实例，
不要释放或删除快照。恢复时可能因 A40 库存不足暂时无法分配主机；等待资源即可，
不要创建空白实例重装环境。

如果用户准备切换对话，先确认：

- 本地最终源码已同步到云端。
- 云端没有后台下载或推理任务。
- 实例已暂停以停止 GPU 计费。

2026-11-23 全量推理结束时 GPU 为 0 MiB / 0%，无后台推理进程。实例仍会计费，
完成本地收尾后应在控制台暂停，不要释放或删除快照。
