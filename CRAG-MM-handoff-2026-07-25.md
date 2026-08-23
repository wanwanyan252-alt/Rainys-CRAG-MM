# CRAG-MM 项目交接文档 - 2026-07-25

更新时间：2026-07-25  
项目目录：`D:\CODE\Rainys-CRAG-MM`  
当前学习方式：老师式讲解，用户自己在 VS Code 的 cmd 终端操作。  
重要偏好：先解释“为什么”，再给命令；用户不希望只收到操作步骤。

## 1. 项目总目标

本项目的最终目标不是单纯“训练一个模型”，而是理解并实现一个面向 CRAG-MM 任务的多模态问答系统：

1. 输入包括图片和用户问题。
2. 系统可以使用官方提供的离线检索源。
3. Agent 根据图片、问题、检索结果和多轮上下文生成答案。
4. 答案需要尽量正确；不确定时应该回答 `I don't know`，避免幻觉。
5. 最终目标是能跑通官方本地评测流程，并逐步改进自己的 Agent。

可以把它理解成一个智能眼镜场景：

用户看到某个物体、地点、商品、植物、人物或网页相关对象，通过眼镜提问；系统需要根据图像和外部知识给出可靠回答。


当前阶段目标是：

```text
跑通流程 -> 理解评测 -> 理解 Agent 输入 -> 理解图片检索 RAG context
```

暂时不做：

```text
训练模型
部署 vLLM
租云服务器
接入 Llama 11B Vision
正式优化比赛分数
```

## 2. 昨日基础状态回顾

2026-07-24 已经跑通最小闭环：

```text
数据集 -> RandomAgent -> 评测器 -> 结果文件
```

结果目录：

```text
D:\CODE\Rainys-CRAG-MM\results\2026-07-24_20-27-43
```

关键分数：

```json
{
  "total": 16.0,
  "correct": 0.0,
  "miss": 0.0,
  "hallucination": 16.0,
  "truthfulness_score": -1.0
}
```

解释：

`RandomAgent` 随机输出字符串，所以 16 道题全被判为 hallucination。该结果证明流程通了，但策略是最差底线。

## 3. 今日完成的核心进展

### 3.1 建立保守 baseline：IdkAgent

新增文件：

```text
D:\CODE\Rainys-CRAG-MM\example_agents\idk_agent.py
```

作用：

```text
每道题都回答 I don't know
```

意义：

CRAG-MM 评分规则是：

```text
答对 +1
不知道 0
答错 -1
```

所以 `IdkAgent` 虽然不聪明，但能证明“拒答不扣分”，并建立安全底线。

结果目录：

```text
D:\CODE\Rainys-CRAG-MM\results_idk\2026-07-25_14-29-23
```

关键分数：

```json
{
  "total": 6.0,
  "correct": 0.0,
  "miss": 6.0,
  "hallucination": 0.0,
  "truthfulness_score": 0.0
}
```

结论：

```text
RandomAgent: -1.0
IdkAgent: 0.0
```

项目学习上从“乱答最差底线”进入“保守拒答底线”。

### 3.2 建立输入观察工具：DebugAgent

新增文件：

```text
D:\CODE\Rainys-CRAG-MM\example_agents\debug_agent.py
```

作用：

打印评测器传给 Agent 的材料：

```text
Query
Domain
Has image
History
RAG context
```

最后仍然返回：

```text
I don't know
```

结果目录：

```text
D:\CODE\Rainys-CRAG-MM\results_debug\2026-07-25_15-32-31
```

关键分数：

```json
{
  "total": 3.0,
  "miss": 3.0,
  "hallucination": 0.0,
  "truthfulness_score": 0.0
}
```

无检索时 DebugAgent 观察到：

```text
Query: 有
Domain: 有
Has image: True
History: []
RAG context: [EMPTY]
```

解释：

关闭所有检索时，`get_rag_context()` 直接返回空字符串；单轮任务下 `History` 是空列表。

### 3.3 打开图片检索，进入 Task 1 的第一步

运行目标：

```text
DebugAgent + 图片检索开 + 网页检索关
```

命令形式：

```bat
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --suppress-web-search-api --output-dir .\results_debug_image --display-conversations 1
```

注意：

命令里有 `--suppress-web-search-api`，所以网页搜索关闭。  
命令里没有 `--suppress-image-search-api`，所以图片搜索打开。

结果目录：

```text
D:\CODE\Rainys-CRAG-MM\results_debug_image\2026-07-25_17-41-48
D:\CODE\Rainys-CRAG-MM\results_debug_image\2026-07-25_17-51-15
```

关键分数：

```json
{
  "total": 2.0,
  "miss": 2.0,
  "hallucination": 0.0,
  "truthfulness_score": 0.0
}
```

DebugAgent 终端观察到：

```text
RAG context: <search results></search results>
```

这和 `[EMPTY]` 不同：

```text
[EMPTY]
= 没有开启检索，get_rag_context 直接返回空字符串

<search results></search results>
= 开启了图片检索，但经过阈值过滤后没有留下可用内容
```

当前推测：

`utils/retriever.py` 里有阈值：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

图片检索可能返回了候选项，但分数都没有超过 0.75，所以被过滤掉，最终只剩空的 `<search results></search results>` 外壳。

下一步建议：

为了学习检索结果结构，可以临时把：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

改成：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.0
```

然后重新跑 DebugAgent，观察完整图片检索结果。注意这只是教学实验，不一定是最终比赛策略。

## 4. 今日修改过的代码和环境

### 4.1 `example_agents/user_config.py`

当前已改成懒加载，并登记了：

```text
random -> RandomAgent
debug -> DebugAgent
idk -> IdkAgent
```

意义：

只跑 `random`、`idk`、`debug` 时，不会提前导入 `vllm`、`anthropic`、`google-generativeai` 等重依赖。

注意：

`supported_keywords` 提示字符串里目前没有完全整理好，可能缺 `debug` 或格式不整齐，但功能已可用。

### 4.2 `example_agents/idk_agent.py`

新增保守 Agent。

核心逻辑：

```python
return ["I don't know" for _ in queries]
```

### 4.3 `example_agents/debug_agent.py`

新增调试 Agent。

核心逻辑：

```python
print("Query:", query)
print("Domain:", ...)
print("Has image:", ...)
print("History:", ...)
print("RAG context:", ...)
return ["I don't know" for _ in queries]
```

### 4.4 第三方包 `cragmm_search` 被手动修补

重要：这个修改不在项目源码目录，而在虚拟环境第三方包里：

```text
D:\CODE\Rainys-CRAG-MM\.venv-light\Lib\site-packages\cragmm_search\image_search_mock_api\image_search.py
```

修复位置：`extract_features()` 中 `model.get_image_features(**inputs)` 的返回值处理。

原问题：

当前 `transformers==5.14.1` 下，`model.get_image_features(**inputs)` 返回的是：

```text
BaseModelOutputWithPooling
```

不是直接的 `torch.Tensor`。原代码直接调用：

```python
features.norm(...)
```

导致：

```text
AttributeError: 'BaseModelOutputWithPooling' object has no attribute 'norm'
```

修复逻辑：

```python
with torch.no_grad():
    output = model.get_image_features(**inputs)

if hasattr(output, 'pooler_output'):
    features = output.pooler_output
elif hasattr(output, 'image_embeds'):
    features = output.image_embeds
elif isinstance(output, torch.Tensor):
    features = output
else:
    features = output[0]

features = features / features.norm(dim=-1, keepdim=True)
```

提醒：

如果以后重装 `cragmm-search-pipeline` 或重建 `.venv-light`，这个补丁会消失，需要重新修。

### 4.5 当前关键依赖版本

通过 `python -m pip show ...` 确认：

```text
chromadb==1.0.15
transformers==5.14.1
cragmm-search-pipeline==0.5.1
chroma-hnswlib==0.7.6
torch==2.13.0
```

今日曾经遇到 `chromadb==1.5.9` 读官方图片索引失败，后来降级到 `1.0.15`。

## 5. 当前缓存盘点

### 5.1 C 盘 Hugging Face 旧缓存

路径：

```text
C:\Users\王梓蕊\.cache\huggingface
```

大小约：

```text
24.67 GB
```

其中：

```text
C:\Users\王梓蕊\.cache\huggingface\hub\datasets--crag-mm-2025--crag-mm-single-turn-public
C:\Users\王梓蕊\.cache\huggingface\hub\datasets--crag-mm-2025--web-search-index-public-test
```

网页索引大小约：

```text
16.42 GB
```

C 盘图片索引：

```text
C:\Users\王梓蕊\.cache\huggingface\hub\datasets--crag-mm-2025--image-search-index-public-test
```

当前状态：

```text
MISSING
```

说明今天反复排错时已经删掉了 C 盘图片索引缓存。

建议：

暂时不要删 C 盘的 `web-search-index-public-test`，后续 Task 2 / Task 3 可能会用。等 D 盘缓存方案完全稳定后，再决定是否迁移或清理。

### 5.2 D 盘 Hugging Face 新缓存

路径：

```text
D:\CODE\hf_cache
```

大小约：

```text
3.80 GB
```

包含：

```text
D:\CODE\hf_cache\hub\datasets--crag-mm-2025--crag-mm-single-turn-public
D:\CODE\hf_cache\hub\datasets--crag-mm-2025--image-search-index-public-test
D:\CODE\hf_cache\hub\models--openai--clip-vit-large-patch14-336
```

用途：

今天为避开 Windows 中文用户路径和 Hugging Face symlink/cache 问题，设置了：

```bat
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
```

建议：

后续继续使用 D 盘缓存作为主要 HF 缓存路径。

### 5.3 CRAG 图片缓存

路径：

```text
C:\Users\王梓蕊\AppData\Local\cragmm_images_cache
```

大小约：

```text
3.72 GB
```

用途：

这是 `utils.utils.ensure_crag_cache_dir_is_configured()` 使用的图片下载缓存，不是 Hugging Face 索引缓存。

当前运行日志仍会出现：

```text
Caching downloaded images in C:\Users\王梓蕊\AppData\Local\cragmm_images_cache
```

建议：

先保留。后续如果想也挪到 D 盘，可在 cmd 中设置：

```bat
set CRAG_CACHE_DIR=D:\CODE\cragmm_images_cache
```

但今天还没有做这一步。

## 6. 今日学到的工作流

更准确的本仓库本地评测流程是：

```text
数据集
  ↓
CRAGTurnBatchIterator
  ↓
整理出 query + image + history + ground_truth
  ↓
CRAGEvaluator.generate_agent_responses()
  ↓
如果没有 suppress 搜索：
    调 get_rag_context()
    得到 rag_context
  ↓
调用 Agent.batch_generate_response(
    queries,
    images,
    message_histories,
    rag_context_list,
    domains
)
  ↓
Agent 内部决定怎么处理这些材料
  ↓
如果是 LLM Agent：
    拼 prompt -> 调 LLM -> 得到回答
如果是 IdkAgent / DebugAgent：
    不调 LLM，直接返回 I don't know
  ↓
保存 agent_response
  ↓
CRAGEvaluator.evaluate_agent_responses()
  ↓
和 ground_truth 比较，算分
```

重点：

```text
ground_truth 不给 Agent 看，只用于评测。
rag_context 给 Agent 看，是检索资料，不是标准答案。
```

## 7. 今日命令行学习状态

用户当前明确选择只学 Windows `cmd`，不混 PowerShell。

已学习：

```bat
cd /d D:\CODE\Rainys-CRAG-MM
dir
mkdir
rmdir
python 文件名.py
python -m 模块名
python -m venv .venv-light
.\.venv-light\Scripts\activate
deactivate
python -m pip install ...
python -m pip show ...
set NAME=value
echo %NAME%
cls
Ctrl + C
```

已解释：

```text
python xxx.py = 运行一个具体 Python 文件
python -m xxx = 按模块方式运行 Python 模块
```

已解释 `local_evaluation.py --help` 中的参数：

```text
--dataset-type
--split
--num-conversations
--suppress-web-search-api
--suppress-image-search-api
--display-conversations
--eval-model
--output-dir
--no_progress
--revision
--num-workers
--model-name
--mode
--input-file
--full-query-path
```

## 8. 明天建议从哪里继续

建议明天第一步不要开网页搜索，继续图片检索学习。

推荐任务：

1. 打开 `utils/retriever.py`。
2. 临时把：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

改成：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.0
```

3. 运行：

```bat
cd /d D:\CODE\Rainys-CRAG-MM
.\.venv-light\Scripts\activate
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
set OPENAI_API_KEY=dummy
set MAX_BATCH_SIZE=1
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --suppress-web-search-api --output-dir .\results_debug_image --display-conversations 1
```

4. 复制终端里的 `RAG context`，读懂图片检索返回结构：

```text
entity_names
Entity attributes
score
为什么可能被过滤
```

5. 读完后，再决定阈值要恢复到 `0.75`，还是临时设中间值观察。

## 9. 明天新对话建议开场

可以直接对新模型说：

```text
请阅读 D:\CODE\Rainys-CRAG-MM\CRAG-MM-handoff-2026-07-25.md，
同时阅读：
D:\CODE\Rainys-CRAG-MM\CRAG-MM-problem-review.md
D:\CODE\Rainys-CRAG-MM\CRAG-MM-learning-notes.md

继续用老师的方式指导我做 CRAG-MM 项目。
我自己在 VS Code 的 cmd 终端操作。
请先解释为什么，再给命令。
```

如果继续今天的技术点，还要提醒新模型：

```text
当前第三方包 cragmm_search 的 image_search.py 已经在虚拟环境里被手动补丁修过。
当前推荐 HF 缓存路径是 D:\CODE\hf_cache。
下一步是调低 IMG_SEARCH_CONFIDENCE_THRESHOLD 观察图片检索 RAG context。
```

