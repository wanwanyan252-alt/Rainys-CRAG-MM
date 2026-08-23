# CRAG-MM 项目学习与环境进度交接文档

更新时间：2026-07-24  
项目目录：`D:\CODE\Rainys-CRAG-MM`  
学习者背景：计算机科学转人工智能方向，正在通过 CRAG-MM 比赛项目理解多模态 RAG、Agent、评测和工程环境。

## 1. 最终目标

本项目的最终目标不是单纯“训练一个模型”，而是理解并实现一个面向 CRAG-MM 任务的多模态问答系统：

1. 输入包括图片和用户问题。
2. 系统可以使用官方提供的离线检索源。
3. Agent 根据图片、问题、检索结果和多轮上下文生成答案。
4. 答案需要尽量正确；不确定时应该回答 `I don't know`，避免幻觉。
5. 最终目标是能跑通官方本地评测流程，并逐步改进自己的 Agent。

可以把它理解成一个智能眼镜场景：

用户看到某个物体、地点、商品、植物、人物或网页相关对象，通过眼镜提问；系统需要根据图像和外部知识给出可靠回答。

## 2. 当前对任务意义的理解

目前已经建立的核心理解：

1. CRAG-MM 主要关注多模态问答中的可信性问题，尤其是减少幻觉。
2. 比赛使用统一的离线检索源，是为了公平、可复现，避免每个人随意联网导致结果不可比较。
3. 检索源相当于 RAG 中的外部知识库，不是训练集。
4. 验证集类似“模拟卷”，用于本地调试和方案调整。
5. LLM-as-a-Judge 是评测时的“阅卷老师”，不是用来帮 Agent 回答问题的模型。
6. Agent 不是单纯的大模型，而是“大模型 + 工具 + 检索 + 工作流 + 记忆策略”的系统。

## 3. 数据集概念

CRAG-MM 公开数据里，重点使用的是 validation split。

常见 split 概念：

- `train`：训练集，用来让模型学习参数。
- `validation`：验证集，用来调方案、调参数、验证思路，类似模拟卷。
- `test`：测试集，最终正式考试，通常不公开标准答案。

本项目公开的 validation 数据可以用来：

1. 看样本长什么样。
2. 跑本地评测。
3. 调 Agent 策略。
4. 对比不同检索和回答方法效果。

但需要注意：CRAG-MM 官方项目重点更像是构建 RAG/Agent 系统，而不是从零训练大模型。

## 4. sample / turns / answers 的理解

在 v0.1.2 数据集中，一个 `sample` 是一条样本，也可以理解成一个会话对象。

它本质上是一个 Python 字典：

```python
sample["session_id"]
sample["image"]
sample["image_url"]
sample["turns"]
sample["answers"]
```

其中：

- `sample["image"]`：图片对象，通常是 PIL Image，也可能为空。
- `sample["image_url"]`：当图片本体为空时，用 URL 指向图片。
- `sample["turns"]`：这一条会话里的所有问题轮次。
- `sample["answers"]`：每一轮问题对应的标准答案。

需要特别注意：v0.1.2 里的 `turns` 和 `answers` 是“列的字典”，不是“字典的列表”。

也就是说：

```python
type(sample["turns"])  # dict

sample["turns"]["query"]       # list[str]
sample["answers"]["ans_full"]  # list[str]
```

含义：

- `query`：用户问的问题。
- `ans_full`：标准答案。
- `interaction_id`：用来把问题和答案对齐。

单轮样本中，`sample["turns"]["query"]` 通常长度为 1。  
多轮样本中，它的长度大于 1，表示同一会话里连续问了多个问题。

## 5. Task 1 / Task 2 / Task 3 区别

当前理解：

| 任务 | 问答形式 | 检索源 | 核心能力 |
|---|---|---|---|
| Task 1 | 单轮 | 图像检索 | 根据图片相关信息回答 |
| Task 2 | 单轮 | 图像检索 + 网页检索 | 多源 RAG |
| Task 3 | 多轮 | 图像检索 + 网页检索 | 多源 RAG + 多轮上下文记忆 |

之前有一个误解是：Task 2 和 Task 3 的区别可能只在记忆系统。  
现在修正为：

- Task 1 到 Task 2：检索源从只有图片扩展为图片 + 网页。
- Task 2 到 Task 3：从单轮问答扩展为多轮问答，需要处理上下文记忆。

## 6. 检索源与 RAG

官方提供两大检索语料：

1. 图像语料 Image-based corpus  
   每条数据是一张图片加结构化属性，例如植物名、物种、实体信息等。

2. 文本网页语料 Text-based corpus  
   网页被切成约 512-token 的 chunk，然后向量化，构成网页检索库。

这些语料的作用类似开卷考试允许查的资料。  
Agent 不能随便上网，只能查官方给的 Mock Search API。

检索流程可以理解为：

```text
用户问题 + 图片
    -> 用 embedding 模型向量化
    -> 在官方索引里找相似内容
    -> 把检索结果拼到 prompt 里
    -> 交给 Llama / GPT / Gemini 等模型生成答案
```

## 7. CLIP / BGE / Llama / Ollama 的区别

### CLIP

CLIP 是多模态 embedding 模型。

它能把图片和文本映射到同一个向量空间里，用于判断“这张图”和“这段文字”是否相关。

本项目中常见配置：

```python
image_model_name="openai/clip-vit-large-patch14-336"
```

主要用于图像检索。

### BGE

BGE 是文本 embedding 模型。

本项目中使用的是：

```python
text_model_name="BAAI/bge-large-en-v1.5"
```

虽然 BGE 系列有中文模型，但这里用的是英文版 `bge-large-en-v1.5`，因为网页语料和比赛数据主要偏英文。

主要用于网页文本 chunk 检索。

### Llama / DeepSeek

Llama 和 DeepSeek 都是大语言模型或多模态大模型家族。  
它们都可以作为 Agent 的“大脑”，负责理解输入并生成答案。

区别主要在：

1. 模型架构和训练数据不同。
2. 是否支持视觉输入不同。
3. 推理部署方式不同。
4. 显存需求、速度、效果不同。
5. 比赛官方 baseline 默认更偏 Hugging Face + vLLM 的部署方式。

### Ollama

Ollama 不是模型本身，而是一个本地运行模型的工具。  
它可以帮助用户在本机运行 llama、qwen、deepseek 等模型。

但当前 CRAG-MM 仓库默认不是 Ollama 调用方式。  
如果后续想用 Ollama，需要自己写一个自定义 Agent，让仓库通过 Ollama API 调模型。

## 8. 模型、训练、权重、损失函数

之前已经讲过一版训练伪代码：

```python
for sample in train_dataset:
    image = sample["image"]
    question = sample["turns"]["query"][0]
    answer = sample["answers"]["ans_full"][0]

    model_input = image + question
    model_output = model(model_input)

    loss = compare(model_output, answer)

    loss.backward()
    optimizer.step()
```

关键概念：

- 模型：一个函数，输入问题/图片，输出答案。
- 权重：模型内部大量可学习参数，类似模型的知识和技能被存放的位置。
- 损失函数：衡量模型输出和标准答案差得多远。
- 反向传播：根据损失计算每个权重应该怎么调整。
- 优化器：真正更新权重的算法，例如 SGD、Adam。
- 训练：不断用样本计算损失并更新权重。
- 推理：权重不再更新，只让模型回答问题。

本项目当前阶段重点不是训练权重，而是：

1. 调检索。
2. 调 prompt。
3. 调 Agent 工作流。
4. 调不知道时回答 `I don't know` 的策略。

## 9. 评测逻辑

官方评测不是简单字符串匹配。

流程大致是：

1. 如果回答里包含 `I don't know`，记为 miss。
2. 如果和标准答案精确匹配，记为 correct。
3. 否则调用 LLM-as-a-Judge 做语义判断。

常见输出文件：

- `turn_evaluation_results_all.csv`
- `turn_evaluation_results_ego.csv`
- `scores_dictionary.json`

得分逻辑重点：

- 答对：加分。
- 不知道：0 分。
- 幻觉答错：扣分。

所以这个比赛鼓励可信回答，而不是乱猜。

## 10. 本机硬件情况

已经检查过：

- 本机 GPU：NVIDIA GeForce RTX 4060 Laptop GPU
- 显存：约 8GB

结论：

1. 本机适合跑轻量流程、读数据、调代码、测试 RandomAgent 或小模型。
2. 本机不适合完整跑官方推荐的 Llama 3.2 11B Vision + vLLM。
3. 官方限制是单张 AWS G6e 实例，NVIDIA L40s GPU，48GB 显存。
4. 后期如果要接近正式提交环境，可能需要 Linux 云服务器。

但当前还有一个月研究，不急着租服务器。  
建议先本地理解流程、写 Agent、跑小规模样本。

## 11. 当前环境安装进度

用户正在使用 Windows + VS Code + PowerShell。

当前虚拟环境：

```powershell
.venv-light
```

已经完成：

```powershell
cd D:\CODE\Rainys-CRAG-MM
python -m venv .venv-light
.\.venv-light\Scripts\activate
python -m pip install --upgrade pip
```

安装过的轻量依赖包括：

| 包 | 用途 |
|---|---|
| `datasets` | 从 Hugging Face 加载 CRAG-MM 数据集 |
| `pandas` | 处理评测结果表格，保存 CSV |
| `pillow` | 处理图片 |
| `rich` | 终端漂亮输出 |
| `tqdm` | 进度条 |
| `python-dotenv` | 读取 `.env` 环境变量 |
| `openai` | 调用 OpenAI API，用于 LLM-as-a-Judge |
| `cragmm-search-pipeline` | 官方 Mock Search API |
| `chromadb` | 文本检索底层依赖之一 |
| `tokenizers` | token 处理和截断 |
| `loguru` | 日志 |
| `pydantic` | 数据结构校验 |
| `requests` | 下载图片、访问 URL |
| `anthropic` | Claude API 相关依赖 |
| `google-generativeai` | Gemini API 相关依赖 |

注意：

- 这些不是所有计算机学生都必须提前掌握的基础知识。
- 它们是这个比赛项目涉及的 Python 第三方库。
- 其中一部分是官方依赖，一部分是为了绕开导入问题补装的。

## 12. 今天遇到的问题与解决方案

### 问题 1：找不到 `requirements.txt`

仓库里没有直接发现一个统一的 `requirements.txt`，所以改成根据报错和项目实际 import 逐步安装轻量依赖。

### 问题 2：`No module named 'anthropic'`

原因：

`example_agents/user_config.py` 顶部提前导入了 closed model agents：

```python
from .closed_model_agents import ClaudeAgent, GeminiAgent, GPTAgent
```

即使只运行 `random_agent`，Python 也会先导入这个文件，于是要求安装 `anthropic`。

解决思路：

把 `user_config.py` 改成懒加载：只有真的用 Claude/Gemini/GPT 时才导入对应依赖。

### 问题 3：`No module named 'vllm'`

原因：

`user_config.py` 顶部提前导入了 open source model agents，而里面需要 `vllm`。

Windows 下不建议安装 vLLM。  
vLLM 更适合 Linux + NVIDIA GPU 环境。

解决思路仍然是懒加载：只跑 `random` 时不导入 vLLM。

### 问题 4：`eval-model None` 后出现 warning

warning 内容：

```text
No calls to LLM-as-a-Judge will be made!
Results will rely only on exact string matching.
```

含义：

因为关闭了 LLM-as-a-Judge，所以不会调用 gpt-4o 做语义判分。  
本地结果只会依赖字符串精确匹配。

这不是错误，是为了省 API key、费用和复杂度。

### 问题 5：Hugging Face symlink warning

warning 大意：

Windows 当前不支持 Hugging Face 默认的符号链接缓存方式。

影响：

- 下载仍然可以继续。
- 只是可能多占一些磁盘空间。

解决办法：

- 可以暂时忽略。
- 或者以后开启 Windows Developer Mode。
- 或者用管理员身份运行。

## 13. 重要事故：误触发大索引下载

用户的目标是先跑通最小闭环。  
之前给出的命令是：

```powershell
python local_evaluation.py --dataset-type single-turn --model-name random --num-conversations 5 --eval-model None
```

问题：

这条命令没有关闭搜索 API，所以触发了官方 web search index 下载。

用户终端出现：

```text
Loading web search data from Hugging Face...
Downloading bytes ...
Reconstructing ... 6.81GB / 17.6GB, 39%
Fetching 7 files: 14%
```

这是指导失误。  
如果只是最小闭环，本来应该优先关闭检索。

用户当前磁盘还有 100GB 以上，而且不急，有一个月研究时间。  
所以当前建议是：如果网络和电脑状态允许，可以让它下完，因为后续 Task 2 / Task 3 会用到网页检索索引。

但要明确：

- 今天最小闭环不需要这个大索引。
- 后续做完整 RAG 会需要它。
- 下完后会进入 Hugging Face 缓存，之后不用重复下载。

## 14. 当前正在下载的东西

正在下载的是：

```text
crag-mm-2025/web-search-index-public-test
```

这是官方网页检索索引。

大约体量：

```text
Reconstructing: 17.6GB
```

用途：

- Task 2：单轮图像 + 网页检索。
- Task 3：多轮图像 + 网页检索 + 记忆。

如果今天先不使用网页检索，可以中断；如果之后一定要研究 Task 2/3，可以让它下载完成。

## 15. Codex 与 VS Code 终端关系

当前 Codex 不能直接看到用户 VS Code 里的终端实时输出。

所以：

1. 用户需要把关键终端输出复制给 Codex。
2. Codex 才能判断当前下载、报错或执行进度。
3. Codex 当前处于桌面 app 的对话环境，不等于已经连接到 VS Code 那个终端。

如果后续需要 Codex 直接操作项目文件，需要确保：

- Codex 有 `D:\CODE\Rainys-CRAG-MM` 的读写权限。
- 或者用户继续自己操作，Codex 只做老师式指导。

用户明确说过：“你指导我做就行，我自己干。”  
所以后续默认应以指导为主，不主动替用户改代码，除非用户明确要求。

## 16. 推荐下一步

等当前下载结束后，建议按这个顺序继续：

### 第一步：确认下载完成

看终端是否不再显示下载进度，并回到 PowerShell 提示符：

```powershell
(.venv-light) D:\CODE\Rainys-CRAG-MM>
```

如果运行继续进入评测，观察是否生成结果文件。

### 第二步：重新跑最小闭环

目标是先让数据集、Agent、评测流程跑通。

建议使用：

```powershell
python local_evaluation.py --dataset-type single-turn --model-name random --num-conversations 5 --eval-model None --suppress-web-search-api --suppress-image-search-api
```

但需要注意：仓库代码里可能即使加了 suppress 参数，也仍然初始化部分检索 pipeline。  
如果它继续下载图像索引，需要进一步修改 `local_evaluation.py`，让它在关闭检索时不要初始化对应 pipeline。

### 第三步：检查输出

重点看是否生成类似：

```text
turn_evaluation_results_all.csv
scores_dictionary.json
```

这代表本地评测闭环跑起来了。

### 第四步：读懂 RandomAgent

需要重点阅读：

```text
D:\CODE\Rainys-CRAG-MM\example_agents\random_agent.py
D:\CODE\Rainys-CRAG-MM\example_agents\base_agent.py
D:\CODE\Rainys-CRAG-MM\local_evaluation.py
```

目标：

1. Agent 输入是什么。
2. Agent 输出是什么。
3. 评测器如何调用 Agent。
4. 检索结果如何传给 Agent。

### 第五步：写一个最简单的自定义 Agent

第一版不追求聪明，只追求结构正确。

例如：

- 如果没有检索结果，回答 `I don't know`。
- 如果有检索结果，从检索结果里抽取最相关文本。
- 暂时不用大模型，先理解 pipeline。

之后再逐步接入：

- Ollama 本地小模型。
- OpenAI API。
- 云服务器上的 vLLM + Llama。

## 17. 后续学习路线建议

建议分阶段学习：

### 阶段 A：跑通流程

目标：

- 能加载 validation 数据。
- 能运行 RandomAgent。
- 能生成评测结果。
- 能读懂结果文件。

### 阶段 B：理解检索

目标：

- 会调用 image search。
- 会调用 web search。
- 会看检索返回的内容。
- 理解 CLIP/BGE embedding 的作用。

### 阶段 C：写规则型 Agent

目标：

- 不接大模型，先用规则组织答案。
- 学会控制什么时候回答 `I don't know`。
- 理解准确率和幻觉惩罚的关系。

### 阶段 D：接入模型

目标：

- 本地可尝试 Ollama 小模型。
- API 可尝试 GPT/Gemini/Claude。
- 云服务器可尝试 vLLM + Llama。

### 阶段 E：优化比赛方案

目标：

- 优化 prompt。
- 优化检索 top-k。
- 优化多轮记忆。
- 优化拒答策略。
- 对 validation 做系统性误差分析。

## 18. 新对话建议开场

如果后续要开新对话，可以直接说：

```text
请阅读 D:\CODE\Rainys-CRAG-MM\CRAG-MM-progress-handoff.md，
接着指导我继续做 CRAG-MM 项目。
我希望你继续用老师的方式讲解，我自己在 VS Code 终端操作。
```

然后把当前终端最新输出复制给新对话。

## 19. 当前最重要的提醒

1. 不急着训练模型。
2. 不急着租云服务器。
3. 不急着装 vLLM。
4. 先跑通最小评测闭环。
5. 再理解检索 pipeline。
6. 最后才考虑模型部署和比赛优化。

这个项目真正要学会的是：

```text
多模态输入 + 离线检索 + Agent 工作流 + 可信回答 + 自动评测
```

这比单纯“会调用一个大模型回答问题”更接近真实 AI 系统工程。
