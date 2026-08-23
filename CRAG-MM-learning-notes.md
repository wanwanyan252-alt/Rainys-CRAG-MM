# CRAG-MM 学习文档

本文件用于长期记录学习到的概念、命令、项目结构和理解框架。  
每日追加，不替代每日交接文档。

## 2026-07-24 学习内容

### 1. CRAG-MM 项目本质

CRAG-MM 不是单纯训练模型的项目，而是一个多模态 RAG 问答系统评测项目。

可以理解成智能眼镜场景：

```text
用户看到某个东西 -> 拍到图片 -> 问问题 -> 系统检索资料 -> 可信回答
```

项目关键词：

```text
多模态输入
图片
问题
离线检索
Agent
RAG
可信回答
自动评测
```

### 2. RAG 的基本理解

RAG = Retrieval-Augmented Generation，检索增强生成。

它的核心不是让模型只靠记忆回答，而是：

```text
先查资料
再组织答案
```

在 CRAG-MM 里，检索源由官方统一提供，目的是公平、可复现。

### 3. 数据集 split

常见 split：

```text
train       训练集，用于学习模型参数
validation 验证集，用于调方案、调策略、模拟考试
test        测试集，用于最终正式评测，通常不公开标准答案
```

当前 CRAG-MM 公开数据重点使用：

```text
validation
```

### 4. sample / turns / answers

一个 `sample` 可以理解成一条会话。

常见字段：

```python
sample["session_id"]
sample["image"]
sample["image_url"]
sample["turns"]
sample["answers"]
```

在 v0.1.2 中：

```python
sample["turns"]    # dict
sample["answers"]  # dict
```

不是“字典列表”，而是“列的字典”。

例如：

```python
sample["turns"]["query"]       # list[str]
sample["answers"]["ans_full"]  # list[str]
```

### 5. Task 1 / Task 2 / Task 3

| 任务 | 轮次 | 检索源 | 核心能力 |
|---|---|---|---|
| Task 1 | 单轮 | 图片检索 | 看图识别实体并用图片库信息回答 |
| Task 2 | 单轮 | 图片检索 + 网页检索 | 多源 RAG |
| Task 3 | 多轮 | 图片检索 + 网页检索 | 多源 RAG + 历史对话记忆 |

### 6. CLIP / BGE / Llama / Ollama

`CLIP`：

多模态 embedding 模型，用于图片检索。能把图片和文本映射到同一向量空间。

`BGE`：

文本 embedding 模型，用于网页 chunk 检索。

`Llama / DeepSeek / Qwen`：

大语言模型或多模态模型，可作为 Agent 的“大脑”。

`Ollama`：

本地运行模型的工具，不是模型本身。当前仓库默认不是 Ollama 调用方式。

### 7. 评分规则

CRAG-MM 评分非常重要：

```text
答对 Correct: +1
不知道 Missing: 0
答错 Hallucination: -1
```

所以：

```text
不确定时说 I don't know，比乱猜更好。
```

### 8. LLM-as-a-Judge

LLM-as-a-Judge 是评测时的“阅卷老师”。

它不是 Agent 作答用的大脑。

如果设置：

```bat
--eval-model None
```

就关闭语义评测，不调用 GPT-4o 等模型。

### 9. 昨日最小闭环

最小闭环：

```text
数据集 -> RandomAgent -> 评测器 -> 分数文件
```

结果：

```text
RandomAgent 全部乱答
truthfulness_score = -1.0
```

学习意义：

流程跑通，但策略最差。

## 2026-07-25 学习内容

### 1. 工作流的准确理解

本仓库本地评测流程：

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

关键区分：

```text
rag_context 给 Agent 看，是检索资料。
ground_truth 不给 Agent 看，只用于最后评测。
agent_response 是 Agent 的最终回答。
```

### 2. `CRAGEvaluator` 不是两个评测器

`CRAGEvaluator` 是同一个类。

里面有两个阶段：

```python
generate_agent_responses()
```

让 Agent 作答。

```python
evaluate_agent_responses()
```

评测 Agent 的回答。

可以理解为：

```text
同一个监考老师：
先发题收答案，再批改答案。
```

### 3. 什么是 tools

在本项目语境里，`CRAGEvaluator` 和 `CRAGTurnBatchIterator` 更像框架代码，不是 Agent 的工具。

更接近工具的是：

```text
image search API
web search API
UnifiedSearchPipeline
get_rag_context()
```

因为它们提供外部能力：查图片、查网页、拿资料。

### 4. `IdkAgent`

`Idk` 是：

```text
I don't know
```

的缩写。

作用：

```text
所有问题都回答 I don't know
```

学习意义：

建立安全底线，验证拒答不扣分。

### 5. `DebugAgent`

作用：

查看 Agent 收到的输入材料：

```text
Query: 当前问题
Domain: 领域
Has image: 是否收到图片
History: 历史对话
RAG context: 检索上下文
```

学习意义：

先看清楚接口，再写复杂逻辑。

### 6. `[EMPTY]` 与 `<search results></search results>`

两者不同：

```text
[EMPTY]
= 没开检索，rag_context 是空字符串

<search results></search results>
= 开了检索，但检索结果经过过滤后没有留下内容
```

这是今天理解图片检索流程的重要点。

### 7. 图片检索阈值

位置：

```text
utils/retriever.py
```

当前阈值：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

含义：

只有图片检索相似度分数高于 0.75 的结果，才会进入 `rag_context`。

学习实验建议：

临时改成：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.0
```

用于观察所有检索候选。之后可恢复。

### 8. cmd 基础命令

当前只学 Windows `cmd`。

常用命令：

```bat
cd
cd /d D:\CODE\Rainys-CRAG-MM
dir
mkdir folder_name
rmdir folder_name
cls
```

路径概念：

```text
.   当前目录
..  上一级目录
.\  当前目录下
```

### 9. Python 虚拟环境命令

创建虚拟环境：

```bat
python -m venv .venv-light
```

激活虚拟环境：

```bat
.\.venv-light\Scripts\activate
```

退出虚拟环境：

```bat
deactivate
```

`Scripts` 是虚拟环境中的工具脚本目录，里面有 `activate`、`pip.exe`、`python.exe` 等。

### 10. 运行 Python 文件和 `-m`

运行具体 Python 文件：

```bat
python local_evaluation.py
python hello.py
```

运行 Python 模块：

```bat
python -m pip
python -m venv
```

`-m` 的意思是：

```text
module，按模块方式运行
```

推荐用：

```bat
python -m pip install package_name
```

而不是直接：

```bat
pip install package_name
```

因为前者能保证使用当前 Python 对应的 pip。

### 11. 安装和查看包

查看 Python 版本：

```bat
python --version
```

查看 pip 版本：

```bat
python -m pip --version
```

安装包：

```bat
python -m pip install pandas
```

查看已安装包：

```bat
python -m pip list
```

查看某个包：

```bat
python -m pip show chromadb
```

### 12. cmd 环境变量

设置：

```bat
set OPENAI_API_KEY=dummy
set MAX_BATCH_SIZE=1
set HF_HOME=D:\CODE\hf_cache
```

查看：

```bat
echo %OPENAI_API_KEY%
```

特点：

```text
只对当前 cmd 窗口有效。
关掉终端后需要重新设置。
```

### 13. 管道搜索命令

命令：

```bat
dir /s /b "%USERPROFILE%\.cache\huggingface\hub" | findstr /i "image-search-index-public-test"
```

拆解：

```text
dir        列出文件
/s         递归所有子目录
/b         简洁格式，只输出路径
|          管道，把左边输出交给右边
findstr    搜索文本行
/i         忽略大小写
```

用途：

在 Hugging Face 缓存目录中查找包含指定关键词的路径。

### 14. `local_evaluation.py --help` 参数

常用参数：

```text
--dataset-type single-turn / multi-turn
--model-name debug / idk / random / llama / gpt ...
--num-conversations N
--eval-model None / gpt-4o
--suppress-web-search-api
--suppress-image-search-api
--output-dir PATH
--display-conversations N
```

进阶参数：

```text
--split
--revision
--num-workers
--mode generate/evaluate/both
--input-file
--full-query-path
```

### 15. `generate` / `evaluate` / `both`

```text
generate = 只让 Agent 作答，保存 response.jsonl，不打分
evaluate = 只评测已有 response.jsonl
both = 先作答，再打分
```

默认是：

```text
both
```

### 16. `--eval-model None`

含义：

```text
不用 GPT-4o 等模型做语义评测
```

仍然会做本地规则评测：

```text
精确匹配
I don't know
否则算错
```

### 17. `.cpp` 文件如何运行

Python 文件：

```bat
python hello.py
```

C++ 文件不能直接用 Python 运行，需要先编译：

```bat
g++ main.cpp -o main.exe
main.exe
```

流程：

```text
.cpp 源代码 -> g++ 编译 -> .exe 可执行文件 -> 运行
```

### 18. 缓存学习

Hugging Face 缓存：

```text
C:\Users\王梓蕊\.cache\huggingface
D:\CODE\hf_cache
```

CRAG 图片缓存：

```text
C:\Users\王梓蕊\AppData\Local\cragmm_images_cache
```

它们不是同一个东西：

```text
HF cache = 数据集、索引、模型缓存
CRAG image cache = 数据集中图片 URL 下载后的缓存
```

### 19. 虚拟环境 `.venv-light` 文件夹结构

当前项目虚拟环境路径：

```text
D:\CODE\Rainys-CRAG-MM\.venv-light
```

它是一个独立的 Python 小环境。激活后，项目优先使用这里面的 `python.exe`、`pip.exe` 和第三方包。

当前结构：

```text
.venv-light
├── Include
├── Lib
├── Scripts
├── share
└── pyvenv.cfg
```

各部分含义：

```text
Include
= C/C++ 扩展编译时可能用到的头文件目录。普通写 Python 时很少直接打开。

Lib
= Python 库目录，最重要的子目录是 Lib\site-packages。

Lib\site-packages
= pip 安装的第三方包都在这里。
= 今天 Claude 修的 cragmm_search 第三方包就在这里。

Scripts
= Windows 虚拟环境里的工具箱。
= 包含 python.exe、pip.exe、activate、activate.bat、Activate.ps1，以及很多包安装后生成的命令行工具。

share
= 一些包可能放共享资源或元数据的地方。当前阶段一般不用手动处理。

pyvenv.cfg
= 虚拟环境配置文件，记录这个虚拟环境来自哪个基础 Python。
```

当前 `pyvenv.cfg` 内容：

```text
home = D:\Python3.10
include-system-site-packages = false
version = 3.10.10
```

含义：

```text
home = D:\Python3.10
= 这个虚拟环境是基于 D:\Python3.10 创建的。

include-system-site-packages = false
= 不直接使用系统 Python 里的第三方包，保持项目环境相对隔离。

version = 3.10.10
= 这个虚拟环境使用 Python 3.10.10。
```

重要理解：

```text
虚拟环境不是神秘文件夹。
它主要做三件事：
1. 提供当前项目专用 python.exe。
2. 提供当前项目专用 pip.exe。
3. 把 pip 安装的包放到自己的 Lib\site-packages 里。
```

为什么今天第三方包补丁会在 `.venv-light` 里面：

```text
cragmm-search-pipeline 是 pip 安装进虚拟环境的包。
所以它的源码位置在：
D:\CODE\Rainys-CRAG-MM\.venv-light\Lib\site-packages\cragmm_search
```

提醒：

```text
如果删除并重建 .venv-light，所有 pip 安装的包和手动补丁都会消失。
如果重新安装 cragmm-search-pipeline，今天修过的 image_search.py 补丁也可能被覆盖。
```

## 2026-07-26 学习内容

### 1. 这些天任务步骤的中文专业术语

今天把前几天做过的事情统一整理成中文专业叫法：

| 步骤 | 中文术语 | 核心作用 |
|---|---|---|
| RandomAgent | 随机基线实验 | 验证最小评测闭环 |
| IdkAgent | 拒答基线 / 安全基线 | 验证不确定时拒答不扣分 |
| DebugAgent | 输入观测器 / 调试型 Agent | 观察 Agent 实际收到的输入 |
| 打开图片检索 | 图像检索链路验证 | 验证图片能进入检索 pipeline |
| 调低图片阈值 | 检索召回观察 / 阈值调参 | 观察被过滤前的候选 |
| 打印 RAW RESULTS | 原始检索结果暴露 | 看到 score 和实体名 |
| score 写进 RAG context | 检索置信度注入 / RAG 上下文增强 | 让 Agent 看到证据可信度 |
| RuleAgent | 规则型保守 Agent | 在本地做少量保守决策 |

整体路线：

```text
随机基线
  ↓
拒答基线
  ↓
输入观测
  ↓
检索链路验证
  ↓
检索中间结果暴露
  ↓
检索置信度注入
  ↓
规则型保守决策
```

### 2. `retriever.py` 的定位

`retriever.py` 中文叫：

```text
检索器
```

更完整叫：

```text
RAG 检索器
```

它负责在 Agent 回答前准备外部资料。

位置：

```text
图片 + 问题
  ↓
retriever.py
  ↓
RAG context
  ↓
Agent
```

三者区别：

```text
retriever.py = 资料员，负责找资料和整理资料。
Agent = 答题人，负责根据资料生成回答。
evaluator = 阅卷员，负责和 ground_truth 对比打分。
```

### 3. 图片检索的 30 条 Result

今天终端输出的：

```text
========== IMAGE SEARCH RAW RESULTS ==========
[Result 1] score=...
entities: [...]
...
[Result 30] score=...
entities: [...]
==============================================
```

含义：

```text
图片检索器从官方离线图片索引里找出的 30 个最相似候选。
```

对应代码：

```python
NUM_IMG_SEARCH_RESULTS = 30
```

每条结果：

```text
Result N = 第 N 个相似候选
score = 图片相似度分数
entities = 该候选对应的实体名
```

这些不是答案，也不是 ground_truth。它们只是检索阶段的原始候选。

### 4. 检索置信度注入

今天修改 `utils/retriever.py`，让 `RAG context` 中的实体携带检索分数。

原来 Agent 看到：

```text
Entity 1: Subaru WRX
```

现在 Agent 看到：

```text
Entity 1: Subaru WRX (retrieval score: 0.642)
```

学习意义：

```text
Agent 不只知道检索到了什么，还知道这条检索证据有多可信。
```

这是后续做保守 Agent 的基础，因为 Agent 可以根据 score 判断：

```text
高置信结果可以考虑使用。
中低置信结果只能当线索。
候选分散时应该拒答。
```

### 5. 当前图片检索为什么不准

今天理解到：

```text
官方图片检索 pipeline 是视觉相似检索，不是精确识别系统。
```

它依赖 CLIP 类 embedding，把图片转成向量，再去官方离线索引里找相似项。

它擅长：

```text
找视觉上相似的对象。
判断大概类别。
给出候选实体。
```

它不一定擅长：

```text
精确车型识别。
具体年份和发动机版本识别。
精确菜名识别。
从图片直接知道油耗、路线距离、食物起源。
```

今天车辆题最高分约：

```text
0.642
0.650
```

这说明检索器自己也只是中等置信。

官方原阈值：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

会过滤掉这些结果，是为了避免低置信资料误导 Agent。

### 6. 第二、三题为什么当前答不出来

第二题是油耗距离题。

它需要：

```text
识别车型
查询油耗
查询或知道 Washington DC 到 Baltimore 距离
计算 5 gallons 能跑多远
```

当前失败原因：

```text
图片检索没有识别出 ground_truth 中的 Chevrolet Trailblazer。
网页检索被关闭，无法补充油耗和距离知识。
RuleAgent 还没有油耗/距离计算规则。
```

第三题是食物起源题。

它需要：

```text
识别具体食物
查询食物起源
```

当前失败原因：

```text
图片检索只大概返回 fries 类食物，没有稳定识别为 bacon cheese fries。
网页检索被关闭，无法补充起源知识。
RuleAgent 没有食物起源规则。
```

更准确地说：

```text
没有联网是原因之一，但不是唯一原因。
图片识别不准、网页检索关闭、Agent 决策能力弱共同导致无法回答。
```

### 7. 本地简易 Agent 影响的是哪一层

今天建立了 `RuleAgent`，中文叫：

```text
规则型保守 Agent
```

它影响的是：

```text
Agent 决策层
```

也就是：

```text
收到 query、image、history、rag_context 后，怎么生成 agent_response。
```

它不影响：

```text
CLIP embedding 模型
官方图片索引
网页索引
数据集
ground_truth
评测器打分规则
```

所以本地简易 Agent 不能让检索本身变准。

它只能决定：

```text
哪些证据能用。
哪些证据不该信。
什么时候回答。
什么时候 I don't know。
```

### 8. RuleAgent 的当前能力和限制

当前 `RuleAgent` 能做：

```text
解析 RAG context 中的 Entity。
读取 retrieval score。
识别七人乘车类问题。
识别 how many passengers / seat 类问题。
对明显五座车或七座/八座车做简单判断。
证据不足时返回 I don't know。
```

当前不能做：

```text
直接看图。
调用视觉语言模型。
处理油耗和距离计算题。
处理食物起源题。
处理复杂多轮对话。
修正图片检索本身的错误。
```

### 9. `--eval-model None` 下的分数理解

今天 RuleAgent 在七人乘车题中给出了语义接近正确的回答：

```text
No, the Subaru WRX appears to be a compact or standard passenger car...
```

标准答案是：

```text
no, the subaru wrx is a compact car with a total passenger capacity of 5 people.
```

但因为运行时使用：

```bat
--eval-model None
```

评测只做：

```text
精确匹配
I don't know 检测
否则算错
```

所以语义接近正确也会被算作 hallucination。

学习结论：

```text
本地简易评测适合检查流程和安全性。
语义是否正确，需要语义裁判或人工查看。
```

### 10. 明天建议学习方向

下一步建议：

```text
先用 DebugAgent 打开网页检索，观察网页 RAG context。
```

不要急着继续扩大 RuleAgent。

原因：

```text
第二题和第三题需要网页知识。
但我们还不知道网页检索会返回什么、是否会被错误图片实体带偏。
```

推荐观察目标：

```text
网页 RAG context 是否包含油耗。
网页 RAG context 是否包含路线距离。
网页 RAG context 是否包含食物起源。
网页结果和图片候选之间是否一致。
```

### 11. CRAG-MM 当前整体流程图

当前最重要的系统链路：

```text
图片 + 问题
  ↓
retriever.py 检索器
  ↓
RAG context 检索上下文
  ↓
Agent
  ↓
答案 agent_response
  ↓
评测器 evaluator
  ↓
和 ground_truth 对比，得到分数
```

更细一点：

```text
数据集
  ↓
CRAGTurnBatchIterator 把数据整理成 query + image + history + ground_truth
  ↓
CRAGEvaluator.generate_agent_responses()
  ↓
如果检索没被 suppress：
    retriever.py 调图片检索 / 网页检索
    生成 RAG context
  ↓
Agent.batch_generate_response(
    queries,
    images,
    message_histories,
    rag_context_list,
    domains
)
  ↓
Agent 输出 agent_response
  ↓
CRAGEvaluator.evaluate_agent_responses()
  ↓
精确匹配 / I don't know / 语义评测
  ↓
scores_dictionary.json 等结果文件
```

核心分工：

```text
数据集 = 出题材料
retriever.py = 资料员
RAG context = 资料员整理出的参考资料
Agent = 答题人
evaluator = 阅卷员
ground_truth = 标准答案，只给阅卷员看，不给 Agent 看
```

### 12. 项目中常看或常改的代码文件速查表

这张表用于以后快速定位文件。中文名不是官方名称，是学习时方便理解的叫法。

| 文件路径 | 中文名 | 主要作用 | 当前是否常改 |
|---|---|---|---|
| `local_evaluation.py` | 本地评测入口 / 主运行脚本 | 解析命令行参数，加载数据集，初始化检索器和 Agent，启动生成和评测 | 常运行，偶尔读，尽量少改 |
| `utils/retriever.py` | RAG 检索器 / 资料员 | 调图片检索和网页检索，把结果整理成 `RAG context` | 当前常改 |
| `example_agents/user_config.py` | Agent 注册表 / 模型名路由器 | 根据 `--model-name` 选择对应 Agent，并做懒加载 | 常改 |
| `example_agents/base_agent.py` | Agent 基类 / 接口规范 | 定义所有 Agent 必须实现的方法和标准消息组织流程 | 主要阅读，少改 |
| `example_agents/random_agent.py` | 随机基线 Agent | 随机回答，用于验证流程 | 基本不改 |
| `example_agents/idk_agent.py` | 拒答基线 Agent | 永远回答 `I don't know` | 基本不改 |
| `example_agents/debug_agent.py` | 输入观测器 / 调试 Agent | 打印 `Query`、`Domain`、`Has image`、`History`、`RAG context` | 当前常用，偶尔改 |
| `example_agents/rule_agent.py` | 规则型保守 Agent | 根据 `query` 和 `RAG context` 做少量本地规则判断 | 当前常改 |
| `example_agents/prompt_constants.py` | 系统提示词文件 | 存放 LLM / VLM Agent 使用的系统提示词 | 后续接大模型时可能改 |
| `example_agents/closed_model_agents.py` | 闭源模型 Agent | GPT / Claude / Gemini 等 API Agent | 当前不改 |
| `example_agents/open_source_model_agents.py` | 开源模型 Agent | Llama / Qwen / InternVL / Pixtral 等本地或 vLLM Agent | 当前不改，后续接 VLM 时看 |
| `evaluation/evaluator.py` | 评测器核心 | 负责生成回答、保存结果、评测回答 | 主要阅读，谨慎修改 |
| `evaluation/evaluation_utils.py` | 分数计算工具 | 计算 correct、miss、hallucination、truthfulness_score | 主要阅读 |
| `evaluation/llm_judge.py` | 语义裁判调用器 | 调用 LLM-as-a-Judge 判断语义正确性 | 后续打开语义评测时看 |
| `.venv-light\Lib\site-packages\cragmm_search\image_search_mock_api\image_search.py` | 第三方图片检索包补丁文件 | 官方搜索包里的图片特征提取逻辑，曾手动修过 `BaseModelOutputWithPooling` 问题 | 不在项目源码中，重装会丢补丁 |

当前最常修改的四个文件：

```text
utils/retriever.py
example_agents/user_config.py
example_agents/debug_agent.py
example_agents/rule_agent.py
```

当前最常运行的入口：

```text
local_evaluation.py
```

当前最需要谨慎的文件：

```text
evaluation/evaluator.py
.venv-light\Lib\site-packages\cragmm_search\image_search_mock_api\image_search.py
```

原因：

```text
evaluator.py 是评测规则核心，乱改会影响分数可信度。
site-packages 里的 image_search.py 是第三方包补丁，重装环境后可能消失。
```

## 2026-07-27 学习内容

### 1. Web Search 修复状态

今天本地网页检索已修复。

三个模式全部验证通过：

```text
Web-only
Image-only
Web + Image
```

这说明：

```text
本地已经可以同时使用图片检索和网页检索。
```

### 2. 本次 web search 问题的中文专业定位

这次问题不是 Agent 层，也不是评测器层。

问题发生在：

```text
网页检索索引读取层
```

更具体：

```text
ChromaDB / HNSW 在读取官方 web search 向量索引时出错。
```

错误表面上是：

```text
Error loading hnsw index
```

深层原因之一是：

```text
C 盘默认 Hugging Face 缓存里有一份被新版 chromadb 迁移过的 web index。
当前 chromadb==1.0.15 读不了那份新版 schema。
```

### 3. HF 缓存路径必须真正生效

当前推荐 Hugging Face 缓存路径：

```text
D:\CODE\hf_cache
```

cmd 中设置：

```bat
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
```

如果这些没有在当前终端生效，`snapshot_download()` 可能会使用默认 C 盘缓存：

```text
C:\Users\王梓蕊\.cache\huggingface
```

这会重新踩到被新版 ChromaDB 迁移过的 web index。

### 4. Windows cmd 与 export

Claude 报告中出现：

```bash
export HF_HOME="D:/CODE/hf_cache"
```

这是 Linux/macOS shell 语法，不适用于 Windows `cmd`。

当前用户明确只学 Windows `cmd`，所以应使用：

```bat
set HF_HOME=D:\CODE\hf_cache
```

不要混用：

```text
PowerShell 的 $env:
Linux/macOS 的 export
```

### 5. 第三方包 search.py 的 web-only 补丁

文件：

```text
D:\CODE\Rainys-CRAG-MM\.venv-light\Lib\site-packages\cragmm_search\search.py
```

问题：

```text
原代码无条件加载图片 CLIP 模型。
当 --suppress-image-search-api 时，image_model_name=None，仍然执行 CLIPModel.from_pretrained(None)，导致 web-only 模式报错。
```

修复：

```text
仅当 image_hf_dataset_id 不为 None 时加载图片搜索组件。
web-only 模式不加载 CragImageKG。
Pipeline 基类需要 model 参数时，如果没有 image_model，就用 text_model。
图片分支增加 image_search 是否开启的安全检查。
```

### 6. DebugAgent 的 Windows 安全打印

文件：

```text
D:\CODE\Rainys-CRAG-MM\example_agents\debug_agent.py
```

问题：

```text
网页 RAG context 可能包含 ® 等特殊字符。
Windows cmd 默认 GBK 编码可能打印不了，导致 UnicodeEncodeError。
```

修复：

```text
增加 _safe_str()，打印前用当前控制台编码做 errors="replace" 处理。
```

### 7. 当前重要补丁清单

这些补丁很重要，但部分在虚拟环境第三方包里。

```text
1. .venv-light\Lib\site-packages\cragmm_search\image_search_mock_api\image_search.py
   修复 transformers 返回 BaseModelOutputWithPooling 时图片特征提取失败。

2. .venv-light\Lib\site-packages\cragmm_search\search.py
   修复 web-only 模式下仍无条件加载图片模型的问题。

3. example_agents\debug_agent.py
   修复 Windows GBK 打印网页 RAG context 时报 UnicodeEncodeError。
```

提醒：

```text
如果重建 .venv-light 或重装 cragmm-search-pipeline，前两个第三方包补丁会消失。
```

### 8. Web search 验证命令

运行前：

```bat
cd /d D:\CODE\Rainys-CRAG-MM
.\.venv-light\Scripts\activate
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
set OPENAI_API_KEY=dummy
set MAX_BATCH_SIZE=1
```

只开网页检索：

```bat
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --suppress-image-search-api --output-dir .\results_web_test --display-conversations 1
```

图片和网页一起开：

```bat
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --output-dir .\results_web_image_test --display-conversations 1
```

## 2026-08-06 学习内容

今天的主题是计算机云服务，重点不是“照着页面把云服务器租下来”，而是把云服务器背后的计算、存储、网络、安全、Linux、GPU 与 AI 工程体系真正串起来。云服务器页面里的每个选项，本质上都在回答一个问题：我要租一台什么样的远程计算机，它放在哪个网络里，谁能访问它，它能存多少东西，能不能用 GPU，最后出了问题该从哪一层排查。

### 1. 云服务先从“资源租赁”理解

云服务可以理解为把机房里的计算机资源按需租给用户。传统方式是自己买物理服务器、显卡、硬盘、网线、交换机、电源和机房；云服务方式是云厂商已经把这些基础设施搭好，再通过控制台/API 把资源切分、隔离、计费、交付给用户。

常见云资源可以分成几类：

| 资源类型 | 云上的名字 | 解决的问题 | 例子 |
| --- | --- | --- | --- |
| 计算 | ECS、CVM、EC2、云服务器 | 程序在哪里运行 | CPU、内存、GPU 实例 |
| 存储 | 云硬盘、对象存储、快照 | 数据和文件放在哪里 | 系统盘、数据盘、OBS/S3 |
| 网络 | VPC、子网、EIP、带宽 | 机器怎么互联、外部怎么访问 | 公网 IP、安全组、路由 |
| 安全 | 安全组、密钥、IAM | 谁可以访问什么 | SSH 密钥、端口规则 |
| 运维 | 镜像、监控、备份、日志 | 如何复制、恢复、观察系统 | Ubuntu 镜像、磁盘备份 |

云服务器不是“网页上的一个按钮”，而是一台被虚拟化出来、放在云厂商网络里的 Linux/Windows 计算机。你通过 SSH、浏览器、VS Code Remote 等方式远程使用它。

### 2. 物理服务器、虚拟机、云服务器与实例

物理服务器是真实机器，里面有 CPU、内存、硬盘、网卡、GPU 等硬件。云厂商会在物理服务器上运行虚拟化系统，把一台机器切成多个互相隔离的虚拟机，每个虚拟机都像一台独立电脑一样运行操作系统。

云服务器实例就是云平台交付给你的那一台虚拟机/云主机。实例不是“某个软件进程”，而是一组被绑定在一起的资源：

| 实例组成 | 含义 | 常见配置项 |
| --- | --- | --- |
| vCPU | 分配给实例的 CPU 计算能力 | 2 核、8 核、16 核 |
| 内存 | 程序运行时的临时工作空间 | 4 GiB、64 GiB、128 GiB |
| GPU | 深度学习/图形计算加速硬件 | V100、A100、T4 |
| GPU 显存 | GPU 自己的高速内存 | 16 GiB、40 GiB、80 GiB |
| 系统盘 | 操作系统和基础软件所在磁盘 | Ubuntu、驱动、CUDA |
| 数据盘 | 额外挂载的数据存储 | 数据集、模型、项目代码 |
| 网卡/IP | 让实例进入网络 | 私有 IP、公网 IP |

实例规格例如“GPU 加速型、8 vCPU、64 GiB、1 张 V100 16 GiB”，意思是你租到的是一台带 8 个虚拟 CPU、64 GiB 系统内存和 1 张 NVIDIA V100 GPU 的远程计算机。深度学习最容易卡住的不是 64 GiB 系统内存，而是 16 GiB GPU 显存，因为模型参数、梯度、中间激活值都要放进显存。

“弹性”指实例可以按需创建、停止、扩容、释放。它不是永久买断，而是在某段时间内使用云厂商资源。对学习场景，按需计费更灵活；对长期稳定业务，包年包月可能更便宜。

### 3. 区域、可用区与为什么资源有位置

云服务器并不是抽象地“在云上”，它实际在某个机房或机房集群里。区域通常表示地理城市或地区，例如华东、华北、上海、北京；可用区通常表示同一区域内相互隔离的一组机房。

| 概念 | 含义 | 选择时关注 |
| --- | --- | --- |
| 区域 Region | 资源所在的大地理位置 | 离使用者近、符合法规、资源有库存 |
| 可用区 AZ | 同一区域内相对独立的机房 | 高可用架构会跨可用区 |
| 延迟 | 请求来回需要多久 | 区域越近通常越低 |
| 库存 | 某类 GPU/实例是否可买 | GPU 实例经常受库存影响 |

第一次学习租 GPU 云服务器，通常选离自己近、页面有库存、价格能接受的区域即可。复杂业务才需要考虑跨可用区容灾。

### 4. 镜像：云服务器的“装机模板”

镜像就是操作系统和预装软件的模板。你创建实例时，云平台会根据镜像把系统写入系统盘。镜像决定你登录后看到的是 Ubuntu、CentOS、EulerOS 还是 Windows，也可能决定是否已经预装 NVIDIA 驱动、CUDA、conda 或深度学习框架。

| 镜像类型 | 含义 | 适合场景 |
| --- | --- | --- |
| 公共镜像 | 云厂商提供的标准系统 | 初学、通用 Linux 开发 |
| 私有镜像 | 自己保存的系统快照/模板 | 复制已有环境 |
| 共享镜像 | 他人共享给你的镜像 | 团队、课程统一环境 |
| 市场镜像 | 第三方/官方打包的软件环境 | 想省配置时间，但要注意费用和可信度 |

AI 项目推荐 Ubuntu，是因为教程多、Python 生态成熟、CUDA/PyTorch 支持资料多。新项目一般选 Ubuntu 22.04；旧项目或老驱动依赖可考虑 Ubuntu 20.04。创建后第一件事可以用 uname、lsb_release、python3 --version 和 nvidia-smi 检查系统与 GPU 状态。

### 5. GPU、驱动、CUDA、PyTorch 到底是什么关系

GPU 是硬件，CUDA 不是显卡本身。NVIDIA GPU 提供大量并行计算核心，适合矩阵乘法、张量运算、图像处理和深度学习训练/推理。CPU 更像少量能力很强的通用工人，GPU 更像大量适合重复计算的工人。

CUDA 是 NVIDIA 提供的 GPU 并行计算平台和编程模型，包含运行时、编译工具、数学库、API 和开发工具。深度学习框架并不是“直接和显卡聊天”，而是通过驱动和 CUDA 相关库调用 GPU。

完整链路是：

~~~text
NVIDIA GPU 硬件
   |
   v
NVIDIA Driver 驱动
   |
   v
CUDA Runtime / CUDA Toolkit / cuDNN 等库
   |
   v
PyTorch / TensorFlow 的 CUDA 版本
   |
   v
你的训练或推理代码
~~~

各层含义：

| 层 | 作用 | 常见检查 |
| --- | --- | --- |
| GPU 硬件 | 真正执行并行计算 | 实例规格是否含 V100/A100/T4 |
| NVIDIA Driver | 操作系统识别和调度 GPU | nvidia-smi |
| CUDA | 给程序调用 GPU 的运行环境和库 | CUDA 版本、nvcc、动态库 |
| cuDNN | 深度学习常用加速库 | 框架安装时常间接依赖 |
| PyTorch/TensorFlow | 深度学习框架 | torch.cuda.is_available() |
| 代码 | 把模型和张量放到 GPU 上 | model.to("cuda") |

常见问题要分层判断：

| 现象 | 更可能的问题 |
| --- | --- |
| nvidia-smi: command not found | 驱动没装或路径没配 |
| nvidia-smi 报错 | 驱动、内核模块或 GPU 状态异常 |
| nvidia-smi 正常但 torch.cuda.is_available() 是 False | PyTorch 装成 CPU 版或 CUDA 版本不匹配 |
| 能看到 GPU 但训练 CUDA out of memory | GPU 显存不够，不是系统内存不够 |

验证命令：

~~~bash
nvidia-smi
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
python -c "import torch; print(torch.cuda.get_device_name(0))"
~~~

### 6. 系统盘、数据盘、文件系统与挂载

系统盘是启动盘，放操作系统、驱动、基础软件和系统目录。数据盘是额外挂载的云硬盘，适合放项目、数据集、模型权重、缓存、conda 环境、训练输出。

推荐结构：

~~~text
/data
+-- projects
|   +-- Rainys-CRAG-MM
+-- datasets
+-- models
+-- cache
|   +-- huggingface
+-- outputs
+-- logs
+-- miniconda3
~~~

系统盘 40 GiB 能做小实验，但安装 NVIDIA 驱动、CUDA、conda、PyTorch、transformers、Docker 和模型缓存后很容易满。更稳的是系统盘 100 GiB，加 200 GiB 或更大的数据盘。

Linux 里磁盘设备不会自动变成一个可访问目录。新数据盘通常需要：

~~~text
识别磁盘 -> 创建文件系统 -> 挂载到目录 -> 配置开机自动挂载 -> 调整权限
~~~

常用命令：

~~~bash
lsblk
df -h
sudo mkfs.ext4 /dev/vdb
sudo mkdir -p /data
sudo mount /dev/vdb /data
sudo blkid /dev/vdb
sudo nano /etc/fstab
sudo mount -a
sudo chown -R ubuntu:ubuntu /data
~~~

注意：mkfs.ext4 会格式化目标磁盘，旧盘不能随便执行。fstab 里推荐使用 UUID 而不是 /dev/vdb，因为设备名可能随重启或挂载顺序变化，而 UUID 更稳定。

### 7. 计算机网络总图：外部访问云服务器经过什么

从本地电脑访问云服务器时，可以把路径画成：

~~~text
本地电脑
   |
   | SSH / 浏览器 / VS Code Remote
   v
互联网
   |
   v
弹性公网 IP / EIP
   |
   v
云平台边界网络
   |
   v
安全组
   |
   v
VPC：例如 192.168.0.0/16
   |
   v
子网：例如 192.168.0.0/24
   |
   v
云服务器私有 IP：例如 192.168.0.23
   |
   v
Linux 上的 sshd / Jupyter / Python 服务
~~~

这张图的核心是：公网 IP 让互联网找到云平台入口；云平台再把请求映射/转发到 VPC 内部的私有 IP；安全组决定这个来源、协议、端口能不能进入；最后 Linux 上必须真的有对应服务在监听端口。

### 8. IP 到底是地址、协议还是包

IP 这个词有三种常见含义，要看上下文。

| 说法 | 含义 | 例子 |
| --- | --- | --- |
| IP 地址 | 网络里的地址，用来找到设备 | 123.60.xx.xx、192.168.0.23 |
| IP 协议 | Internet Protocol，定义寻址与转发规则 | 网络层协议 |
| IP 包 | 按 IP 协议格式封装的数据包 | 包头里有源 IP、目的 IP、协议类型 |

日常说“服务器 IP 是多少”，一般是 IP 地址。网络原理里说“IP 包头、IP 层、IP 转发”，一般是在说 IP 协议和 IP 数据包。

一个 IP 包大概包含：

~~~text
IP 包
+-- 源 IP 地址：从哪里来
+-- 目的 IP 地址：到哪里去
+-- 协议类型：里面装 TCP、UDP 还是 ICMP
+-- 数据内容：真正要传输的内容
~~~

源地址就是这个包从哪里来，目的地址就是这个包要去哪里。你 SSH 云服务器时，可能是：

| 字段 | 例子 | 含义 |
| --- | --- | --- |
| 源 IP | 你的家庭/校园出口公网 IP | 请求从哪里来 |
| 源端口 | 53621 这类临时端口 | 本地临时开的通信入口 |
| 目的 IP | 云服务器 EIP | 请求发给谁 |
| 目的端口 | 22 | 发给服务器上的 SSH 服务 |
| 协议 | TCP | 使用可靠连接 |

服务器回复时，源和目的会反过来。

### 9. 公网 IP、私有 IP、EIP、VPC、子网

私有 IP 是云服务器在 VPC 内部的地址，例如 192.168.0.23。公网 IP 是互联网上能访问的地址，例如 123.60.xx.xx。EIP 是弹性公网 IP，可以绑定/解绑到云资源上，是云服务器对外暴露的公网门牌号。

| 概念 | 人话解释 | 是否能被互联网直接访问 |
| --- | --- | --- |
| 私有 IP | VPC 内部地址 | 通常不能 |
| 公网 IP/EIP | 互联网地址 | 可以，但受安全组限制 |
| VPC | 云上的私人局域网 | 不是单台机器 |
| 子网 | VPC 中切出来的一段地址范围 | 放具体实例 |

VPC 例如 192.168.0.0/16，表示一整段私有网络空间；子网例如 192.168.0.0/24，表示 VPC 中更小的一段。默认 VPC 和默认子网对第一次学习通常够用。

源/目的检查是云平台检查实例收发的包是否属于它自己。普通云服务器保持开启；只有把实例当 NAT 网关、路由器、代理、防火墙中转时才可能关闭。

### 10. CIDR：/16、/24、/32 与 0.0.0.0/0

CIDR 写法是“IP 地址/网络位数”，例如 192.168.0.0/24。IPv4 一共 32 位，斜杠后的数字表示前多少位是网络号；剩下的位数是主机号。网络位越多，主机位越少，范围越小。

| CIDR | 大致含义 | 常见用途 |
| --- | --- | --- |
| /16 | 大网段，范围较大 | VPC 地址范围 |
| /24 | 较小子网 | 单个子网 |
| /32 | 一个具体 IPv4 地址 | 安全组只允许自己的公网 IP |
| 0.0.0.0/0 | 所有 IPv4 地址 | 对全网开放，风险最高 |

几个判断：

| 判断 | 结论 |
| --- | --- |
| 192.168.0.0/16 是否包含 192.168.0.23 | 包含 |
| 192.168.0.0/24 是否包含 192.168.0.23 | 包含 |
| 192.168.1.0/24 是否包含 192.168.0.23 | 不包含 |
| 1.2.3.4/32 表示什么 | 只表示 1.2.3.4 |
| 0.0.0.0/0 表示什么 | 任意 IPv4 地址都匹配 |

所以安全组里“源地址 = 你的公网 IP/32”表示只允许你当前的出口 IP 访问；“源地址 = 0.0.0.0/0”表示全世界都可以尝试访问，对 SSH、Jupyter、数据库等端口都很危险。

### 11. 以太网、层、协议：网络为什么要分层

以太网 Ethernet 是链路层技术，最初用于局域网有线连接，现在也可以理解为很多本地网络和虚拟网络的二层基础。它关心的是同一局域网/同一链路范围内，设备如何用网卡、MAC 地址、帧、交换机通信。云服务器里的“主网卡、弹性网卡、MAC 地址”可以看成云平台虚拟出来的以太网环境。

协议就是通信双方都遵守的一套规则。它规定数据怎么封装、地址写在哪里、怎么确认收到、失败怎么办、该交给哪个程序处理。

分层的原因是把复杂网络拆成多个职责清楚的层，每层只解决自己的问题：

| 层次 | 核心问题 | 常见协议/对象 | 在云服务器里的例子 |
| --- | --- | --- | --- |
| 应用层 | 用户要做什么 | SSH、HTTP、HTTPS、Jupyter | 远程登录、网页 notebook |
| 传输层 | 交给哪个进程，是否可靠 | TCP、UDP、端口 | TCP 22、TCP 8888 |
| 网络层 | 从哪台机器到哪台机器 | IP、ICMP、路由 | 公网 IP、私有 IP、ping |
| 链路层 | 同一链路内如何传输 | Ethernet、MAC、交换机 | 云服务器主网卡 |
| 物理层 | 电信号/光信号/硬件 | 网线、光纤、机房设备 | 云厂商维护 |

一次 SSH 数据的封装可以理解为：

~~~text
SSH 数据
   放进 TCP 段，写上源端口和目的端口 22
      放进 IP 包，写上源 IP 和目的 IP
         放进以太网帧，写上源 MAC 和目的 MAC
            通过物理网络传输
~~~

不同层的地址不同：MAC 地址偏链路层，IP 地址偏网络层，端口偏传输层。安全组常按源 IP、协议、端口做规则匹配。

### 12. TCP、UDP、ICMP 为什么可以同时存在

TCP、UDP、ICMP 都是网络通信中不同用途的协议。它们可以共用同一个 IP 地址，但每个包里会标明自己携带的是哪种协议。

| 协议 | 所在层次 | 主要用途 | 是否有端口 | 例子 |
| --- | --- | --- | --- | --- |
| TCP | 传输层 | 可靠连接、按序传输、丢包重传 | 有 | SSH 22、HTTP 80、HTTPS 443、Jupyter 8888 |
| UDP | 传输层 | 低延迟、无连接、应用自己处理可靠性 | 有 | DNS、视频、游戏、部分实时服务 |
| ICMP | 网络层辅助协议 | 网络探测、错误报告 | 通常没有 TCP/UDP 端口概念 | ping |

TCP 像打电话，先建立连接再持续对话；ICMP 像敲门问“有人吗”。所以可能出现 SSH 能连但 ping 不通，或 ping 能通但 SSH 连不上，因为它们走的协议不同，安全组也分开判断。

ping 的本质是发送 ICMP Echo Request，如果目标允许并收到，就返回 ICMP Echo Reply。ping 通说明网络层大概率可达，但 ping 不通不一定说明服务器坏了，也可能只是安全组禁用了 ICMP。

### 13. 端口：IP 找机器，端口找服务

一台服务器上可以同时跑很多程序。IP 地址只能定位到“哪台机器”，端口用来定位“这台机器上的哪个服务”。

| 端口 | 常见服务 | 用途 |
| --- | --- | --- |
| 22 | SSH | Linux 远程登录 |
| 80 | HTTP | 普通网页 |
| 443 | HTTPS | 加密网页 |
| 8888 | Jupyter Notebook | 浏览器里的 Python 实验环境 |
| 6006 | TensorBoard | 查看训练日志 |
| 3389 | RDP | Windows 远程桌面 |

访问 123.60.xx.xx:22 的意思是访问公网 IP 为 123.60.xx.xx 的服务器上，监听 22 端口的 SSH 服务。访问 http://公网IP:8888 的意思是访问同一台服务器上监听 8888 的 Jupyter 服务。

### 14. 安全组、防火墙、入方向和出方向

安全组是云平台提供的虚拟防火墙。防火墙是更通用的概念，凡是根据规则允许/拦截网络包的机制都可以叫防火墙。安全组属于云平台层面的防火墙；Linux 里还可能有 ufw、iptables、firewalld；家用路由器、校园网/公司网关也可能有防火墙。

安全组有两个方向：

| 方向 | 以云服务器为中心的含义 | 例子 |
| --- | --- | --- |
| 入方向 | 外部访问云服务器 | SSH 登录、浏览器访问 Jupyter、别人访问网站 |
| 出方向 | 云服务器访问外部 | apt update、pip install、git clone、wget、访问 Hugging Face |

很多云平台默认入方向拒绝、出方向允许。初学者最容易卡在入方向，因为 SSH、Jupyter、TensorBoard 都是“外面访问服务器”。

最小安全规则：

| 需求 | 方向 | 协议 | 端口 | 源地址 |
| --- | --- | --- | --- | --- |
| SSH 登录 | 入方向 | TCP | 22 | 你的公网 IP/32 |
| ping 测试 | 入方向 | ICMP | 全部 | 你的公网 IP/32，可选 |
| Jupyter 直连 | 入方向 | TCP | 8888 | 你的公网 IP/32 |
| TensorBoard | 入方向 | TCP | 6006 | 你的公网 IP/32 |

不推荐把 TCP 22、TCP 8888、所有端口开放给 0.0.0.0/0。正确习惯是最小权限：只开放必要端口，只允许必要来源，只保留必要时间。

### 15. SSH、ping、Jupyter 分别是什么

SSH 是 Secure Shell，用来远程登录 Linux 服务器。你在本地执行 ssh ubuntu@公网IP 后，成功进入的命令行其实是在云服务器上运行。SSH 默认使用 TCP 22 端口，安全组必须放通入方向 TCP 22。

ping 是网络探测命令，用 ICMP 协议测试某个 IP 是否可达、往返延迟大概多少。ping 不是登录，也不是传文件。ping 不通可能是网络不通，也可能只是 ICMP 被安全组或防火墙禁用。

Jupyter 是浏览器里的 Python 实验环境，常用于数据分析、机器学习、深度学习调试和画图。它可以在服务器上启动一个 Web 服务，常用端口 8888：

~~~bash
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
~~~

如果直接用浏览器访问 http://公网IP:8888，就要放通 TCP 8888。更安全的方式是 SSH 隧道：

~~~bash
ssh -i your-key.pem -L 8888:localhost:8888 ubuntu@公网IP
jupyter notebook --ip=127.0.0.1 --port=8888 --no-browser
~~~

然后在本地浏览器打开：

~~~text
http://localhost:8888
~~~

这样安全组只需要开放 TCP 22，不需要把 8888 暴露给公网。

### 16. 弹性公网 IP、BGP、带宽与流量

EIP 让本地电脑能从互联网找到云服务器。创建服务器时一般有“现在购买、使用已有、暂不购买”。第一次学习建议现在购买，否则没有跳板机或其他访问方式时，本地通常无法直接 SSH。

BGP 是互联网路由协议，决定不同网络之间怎么选择路径。云平台里的“全动态 BGP”通常表示线路选择更自动、可用性更好；初学不需要深入配置，选择默认推荐项即可。

带宽和流量不是一回事：

| 概念 | 含义 | 类比 |
| --- | --- | --- |
| 带宽 | 单位时间最多能传多少数据 | 水管粗细 |
| 延迟 | 一个请求来回要多久 | 路途远近 |
| 吞吐 | 实际传输速度 | 实际水流速度 |
| 流量 | 总共传了多少数据 | 水表累计用水量 |

换算要注意 bit 和 Byte：

~~~text
1 Byte = 8 bit
5 Mbit/s = 0.625 MB/s
10 Mbit/s = 1.25 MB/s
~~~

SSH、改代码、看日志，5 Mbit/s 通常够；下载大模型、大数据集、Docker 镜像会慢。按流量计费适合学习和不稳定流量，按带宽计费适合长期稳定对外服务。释放实例时勾选 EIP 随实例释放，可以避免服务器删了但公网 IP 继续计费。

### 17. 密钥对、用户和登录凭证

Linux 云服务器推荐用密钥对登录，不推荐密码登录。密钥对由公钥和私钥组成：

| 部分 | 放在哪里 | 作用 |
| --- | --- | --- |
| 公钥 | 服务器上 | 用来验证私钥 |
| 私钥 | 本地电脑上 | 证明你有登录权限 |

登录命令通常是：

~~~bash
ssh -i your-key.pem ubuntu@公网IP
~~~

常见用户名：

| 系统 | 常见用户名 |
| --- | --- |
| Ubuntu | ubuntu |
| CentOS | root 或 centos |
| EulerOS | root |

私钥要妥善保存，不要上传 GitHub，不要放进项目仓库，不要发给别人。私钥丢了可能无法登录，私钥泄露可能导致别人登录你的服务器。SSH 报 Permission denied (publickey) 时，通常说明网络已经到达 SSH 服务，重点查用户名、私钥、实例绑定的密钥，而不是先怀疑公网 IP。

### 18. AI 工程里的目录、缓存和训练运行

云服务器做 AI 项目时，最容易出现两个问题：系统盘爆满、训练断线停止。解决思路是把大文件放数据盘，把长任务放进稳定会话。

建议把环境和缓存放到 /data：

~~~bash
mkdir -p /data/projects /data/datasets /data/models /data/cache/huggingface /data/outputs /data/logs
export HF_HOME=/data/cache/huggingface
export TRANSFORMERS_CACHE=/data/cache/huggingface
~~~

训练前检查：

~~~bash
pwd
df -h
free -h
nvidia-smi
python --version
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
~~~

训练进程本质上是 Linux 进程。直接在 SSH 会话里运行 python train.py，断线后可能跟着停止。更稳的是用 tmux：

~~~bash
tmux new -s train
python train.py
tmux attach -t train
~~~

也可以用 nohup：

~~~bash
nohup python train.py > train.log 2>&1 &
~~~

查看进程和日志：

~~~bash
ps aux | grep python
nvidia-smi
tail -f train.log
~~~

### 19. 三层门：端口为什么开放了也可能访问不了

Jupyter 或网页服务打不开时，不要只看安全组。一个端口能从公网访问，至少要同时满足：

~~~text
云平台安全组允许
Linux 系统防火墙允许
服务器上真的有程序在监听这个端口
~~~

以 Jupyter 8888 为例：

| 层次 | 要检查什么 | 常用命令/位置 |
| --- | --- | --- |
| 云平台 | 安全组入方向 TCP 8888 是否放通 | 云控制台 |
| 系统防火墙 | ufw / iptables / firewalld 是否拦截 | sudo ufw status |
| 服务进程 | Jupyter 是否监听 8888 | ss -lntp \| grep 8888 |
| 监听地址 | 是否监听 0.0.0.0 或用 SSH 隧道 | ss 输出、启动参数 |
| 访问 URL | 是否带 token，端口是否正确 | 浏览器地址 |

如果 curl http://127.0.0.1:8888 能通，但公网 IP 访问不通，程序本身大概率没问题，重点查监听地址、安全组、系统防火墙或外部网络。

### 20. 常见故障的分层排查

SSH 连不上：

~~~text
1. 实例是否运行中
2. 是否绑定 EIP/公网 IP
3. 本地网络是否能访问公网
4. 安全组入方向是否放通 TCP 22
5. 源地址是否写成正确的公网 IP/32
6. 用户名是否正确
7. 私钥是否正确、权限是否合适
8. 服务器里的 sshd 是否正常
~~~

调试命令：

~~~bash
ssh -vvv -i your-key.pem ubuntu@公网IP
~~~

如果卡在连接阶段，多半是网络、安全组或端口；如果提示 Permission denied，多半是用户名、私钥或认证问题。

nvidia-smi 找不到：

~~~text
1. 确认实例规格确实是 GPU 实例
2. 确认镜像是否包含 GPU 驱动
3. 查看云平台是否有驱动安装工具
4. 按系统和 GPU 型号安装匹配驱动
~~~

PyTorch 看不到 GPU：

~~~text
1. 先看 nvidia-smi 是否正常
2. 再看 PyTorch 是否是 CUDA 版本
3. 再看 CUDA/驱动/框架兼容性
4. 最后看环境变量和虚拟环境是否混乱
~~~

CUDA out of memory：

~~~text
这是 GPU 显存不足，不是系统内存不足。
常见办法：减小 batch size、使用 fp16/bf16、减小输入分辨率、梯度累积、换小模型、清理占显存进程。
~~~

系统盘满：

~~~bash
df -h
du -h --max-depth=1 / | sort -h
~~~

容易占空间的位置包括 /home、/var、/usr/local/cuda、~/.cache、~/.conda、~/.cache/huggingface。预防方式是尽早把项目、数据集、模型和缓存迁到 /data。

### 21. 明天租赁云服务器时的推荐配置逻辑

这不是死记页面选项，而是理解每项背后的目的。

| 配置项 | 推荐 | 背后逻辑 |
| --- | --- | --- |
| 计费模式 | 按需计费 | 学习实验随用随停 |
| 实例规格 | GPU 实例，如 V100 16 GiB | 需要深度学习加速 |
| 镜像 | 公共镜像 Ubuntu 22.04 或 20.04 | AI 生态和教程多 |
| GPU 驱动 | 能自动安装就自动安装 | 减少驱动/CUDA 配置成本 |
| 系统盘 | 推荐 100 GiB | 防止系统、驱动、依赖塞满 |
| 数据盘 | 推荐 200 GiB 或更大 | 放项目、数据、模型、缓存 |
| VPC/子网 | 默认即可 | 初学不需要复杂网络 |
| 私有 IP | 自动分配 | 手动规划只有集群/复杂网络需要 |
| 源/目的检查 | 开启 | 普通服务器不做路由转发 |
| EIP | 现在购买 | 本地需要直接 SSH |
| 公网计费 | 按流量计费 | 学习流量不稳定 |
| 带宽 | 5M 或 10M | SSH 够用，下载多选 10M |
| 安全组 | 只放通必要端口 | 最小权限 |
| SSH 源地址 | 你的公网 IP/32 | 不把 22 暴露给全网 |
| 登录凭证 | 密钥对 | 比密码更安全 |
| EIP 释放 | 随实例释放 | 防止遗留计费 |

创建后第一轮检查：

~~~bash
ssh -i your-key.pem ubuntu@公网IP
uname -a
lsb_release -a
df -h
lsblk
free -h
nvidia-smi
python3 --version
~~~

### 22. 备份、快照、命名和资源管理

云服务器不是只要“能开机”就结束了，还要能被自己管理、恢复和清理。名称、标签、备份、快照这些配置看起来不影响运行，但会影响之后能不能快速找到资源、能不能恢复误删数据、会不会留下隐藏费用。

实例名称建议写清楚用途，而不是保留随机名：

| 命名方式 | 可读性 |
| --- | --- |
| ecs-ed4b | 几天后很难记得用途 |
| gpu-v100-ubuntu | 能看出是 GPU + V100 + Ubuntu |
| crag-mm-train | 能看出服务于 CRAG-MM 训练 |
| ml-lab-v100 | 能看出是机器学习实验机 |

备份和快照用于防止误删、系统损坏、配置失败和数据损坏。它们通常额外计费，所以要按重要程度选择：

| 场景 | 建议 |
| --- | --- |
| 临时学习、随时可重建 | 可以不开自动备份 |
| 课程大作业、毕业设计 | 建议开启备份 |
| 训练结果重要 | 至少备份数据盘或同步到对象存储/本地 |
| 数据集可重新下载 | 可以不备份原始数据集 |
| 配置环境很复杂 | 建议在稳定后做镜像或快照 |

备份不能替代 Git。代码应该用 Git 管理，数据和模型权重再考虑云硬盘备份、对象存储、快照或本地副本。释放实例前要确认：重要文件是否已经保存；EIP 是否随实例释放；数据盘是否保留；快照/备份是否仍在计费。

### 23. 成本意识：云服务器不是本地电脑

云服务器会按资源计费，GPU 实例尤其贵。可能收费的项目包括：

| 资源 | 是否可能持续计费 |
| --- | --- |
| ECS 实例 | 运行中通常计费，部分按需关机策略仍需看平台说明 |
| GPU | 高成本核心资源 |
| 系统盘 | 通常跟实例或云硬盘计费 |
| 数据盘 | 即使实例释放，也可能作为独立云硬盘继续计费 |
| EIP | 未释放时可能计费 |
| 公网流量 | 按流量模式下按实际出网计费 |
| 备份/快照 | 通常额外计费 |

学习时要养成习惯：不用就关机或释放；释放前确认重要数据已保存；确认 EIP 是否随实例释放；确认云硬盘、备份、快照是否仍在计费；项目代码用 Git 保存，重要训练结果至少同步一份。

### 24. 最终心智模型

今天最重要的是把这些术语放回同一张图：

~~~text
计算资源：实例 = vCPU + 内存 + GPU + 显存
系统环境：镜像 = 操作系统 + 初始软件
GPU 链路：硬件 -> Driver -> CUDA -> PyTorch -> 代码
存储结构：系统盘启动系统，数据盘放项目/数据/模型
网络入口：公网 IP/EIP 让外部找到服务器
私有网络：VPC 和子网决定服务器在云内部的位置
访问控制：安全组/防火墙决定协议、端口、来源能否通过
服务定位：IP 找机器，端口找程序，协议规定通信规则
排错方法：按层排查，不要靠猜
~~~

一句话总结：

~~~text
公网 IP 解决“外面怎么找到服务器”。
安全组解决“谁能进来、能进哪个端口”。
VPC/子网解决“服务器在云内部放在哪里”。
系统盘/数据盘解决“系统和数据分别放在哪里”。
GPU/CUDA/框架解决“深度学习计算能不能真正跑起来”。
~~~
