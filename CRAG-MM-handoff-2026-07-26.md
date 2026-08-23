# CRAG-MM 项目交接文档 - 2026-07-26

更新时间：2026-07-26  
项目目录：`D:\CODE\Rainys-CRAG-MM`  
当前学习方式：老师式讲解，用户自己在 VS Code 的 `cmd` 终端操作。  
重要偏好：先解释“为什么”，再给命令；用户不希望只收到操作步骤。  
新增偏好：`--num-conversations` 实际条数可能多一点这件事用户已经知道，后续不用反复解释。

## 1. 当前总目标

CRAG-MM 当前不是在训练模型，也不是在正式冲比赛分数，而是在理解和实现一个面向 CRAG-MM 的多模态 RAG 问答系统。

系统链路可以理解为：

```text
图片 + 问题
  ↓
检索器 retriever.py
  ↓
RAG context 检索上下文
  ↓
Agent
  ↓
agent_response
  ↓
评测器和 ground_truth 对比
```

当前阶段目标：

```text
跑通流程
理解评测
理解 Agent 输入
理解图片检索结果
理解检索为什么不准
开始写本地简易 Agent
```

暂时不做：

```text
训练模型
租云服务器
正式部署 vLLM
接入 Llama 11B Vision / Qwen-VL 大模型
正式优化比赛排行榜分数
```

重要更新：

```text
最终任务不是停留在本地 RuleAgent。
最终任务是租赁云 GPU 服务器，跑真正的视觉语言模型 Agent 和更完整的 CRAG-MM 评测。
```

所以当前本地阶段的定位是：

```text
在租云之前，把项目流程、评测机制、检索机制、Agent 输入输出、依赖环境和缓存路径先搞清楚。
```

请后续模型不要把目标带偏成：

```text
只在本地把 RuleAgent 写到很复杂。
```

`RuleAgent` 当前只是教学和理解用的本地简易 Agent，它的作用是帮助用户理解：

```text
Agent 决策层如何使用 RAG context。
什么时候应该回答。
什么时候应该 I don't know。
为什么检索结果会误导答案。
```

真正的后续主线应该逐步转向：

```text
本地理解流程
  ↓
本地跑通轻量 Agent
  ↓
理解图片检索 + 网页检索
  ↓
准备云服务器部署清单
  ↓
租云 GPU
  ↓
迁移环境 / 缓存 / 数据
  ↓
接入 Llama 11B Vision / Qwen-VL / InternVL 等 VLM Agent
  ↓
跑更完整评测
  ↓
调 prompt、检索策略和拒答策略
```

后续需要准备的云端部署清单包括：

```text
Python 版本
CUDA / PyTorch / transformers / vLLM 版本
是否继续使用 cragmm-search-pipeline
Hugging Face 缓存目录规划
CRAG 图片缓存目录规划
数据集和索引下载或迁移方案
第三方包 cragmm_search 的 image_search.py 补丁是否仍需要
选择哪个 VLM：Llama 11B Vision / Qwen-VL / InternVL
显存需求预估
第一条云端最小测试命令
云端完整评测命令
常见报错和恢复方案
```

时间预估：

```text
本地准备还需要约 3-5 天。
云服务器部署和跑通约 2-4 天。
后续调试和出结果约 3-7 天。
整体比较现实是 1.5-2.5 周；如果遇到 CUDA/vLLM/显存/模型权重问题，可能接近 3 周。
```

## 2. 这些天完成事项的中文专业术语表

这部分是用户今天特别要求总结的重点。

### 2.1 RandomAgent

中文术语：

```text
随机基线实验
```

作用：

```text
验证数据集 -> Agent -> 评测器 -> 结果文件的最小闭环能跑通。
```

结果：

```text
RandomAgent 乱答，truthfulness_score = -1.0。
```

意义：

```text
证明流程通了，但随机回答是最差策略。
```

### 2.2 IdkAgent

中文术语：

```text
拒答基线 / 安全基线 / 保守基线
```

作用：

```text
每题都回答 I don't know。
```

结果：

```text
truthfulness_score = 0.0。
```

意义：

```text
验证“不确定就拒答”不会扣分，建立安全底线。
```

### 2.3 DebugAgent

中文术语：

```text
输入观测器 / 调试型 Agent / Agent 输入探针
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

意义：

```text
开始拆黑箱，确认 Agent 到底收到什么。
```

### 2.4 开启图片检索

中文术语：

```text
图像检索链路验证
```

作用：

确认当前题目图片会被送进官方图片检索 pipeline，检索器会返回相似实体。

重要发现：

```text
[EMPTY] = 没开检索
<search results></search results> = 开了检索，但结果被过滤后为空
```

### 2.5 调低图片检索阈值

中文术语：

```text
检索召回观察实验 / 检索阈值调参
```

过程：

先从：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

临时改到：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.0
```

后来又改成当前的中间观察值：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.6
```

意义：

```text
0.75 很保守，会过滤掉当前样例里所有 0.64 左右的候选。
0.0 用于教学观察，会放出大量低置信候选。
0.6 是当前观察用中间值，不代表最终比赛策略。
```

### 2.6 打印 IMAGE SEARCH RAW RESULTS

中文术语：

```text
原始检索结果暴露 / 检索中间结果可视化
```

作用：

在 `utils/retriever.py` 里打印过滤前的 30 条图片检索候选：

```text
[Result 1] score=...
entities: [...]
```

意义：

```text
第一次看到图片检索器自己的置信度分数。
```

重要观察：

车辆题最高分大约只有：

```text
0.64 ~ 0.65
```

说明官方 CLIP 图片检索器自己也不是很确定。

### 2.7 把 score 写进 RAG context

中文术语：

```text
检索置信度注入 / RAG 上下文增强
```

作用：

原来 Agent 只看到：

```text
Entity 1: Subaru WRX
```

现在 Agent 能看到：

```text
Entity 1: Subaru WRX (retrieval score: 0.642)
```

意义：

```text
让 Agent 不只知道“检索到了什么”，也知道“这条检索证据有多可信”。
```

### 2.8 RuleAgent

中文术语：

```text
规则型保守 Agent / 本地简易决策 Agent
```

作用：

不调用大模型，只用规则解析 `query` 和 `rag_context`，目前只处理很窄的车辆座位问题。

当前策略：

```text
能从检索上下文里看到高于 0.6 的实体和座位/车身类型线索时，尝试回答。
否则回答 I don't know。
```

意义：

```text
从“只观察输入”进入“在本地做最小决策”。
```

## 3. 今日核心代码状态

### 3.1 `utils/retriever.py`

当前关键状态：

```python
NUM_IMG_SEARCH_RESULTS = 30
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.6
```

今日新增/保留：

1. 打印过滤前原始图片检索结果：

```text
========== IMAGE SEARCH RAW RESULTS ==========
[Result 1] score=...
entities: [...]
==============================================
```

2. 把 retrieval score 写进 Agent 能看到的 `RAG context`：

```text
Entity 1: Jeep Grand Cherokee (retrieval score: 0.650)
```

提醒：

```text
RAW RESULTS 打印是调试用，后续如果不想终端太乱，可以删掉或加 debug 开关。
```

### 3.2 `example_agents/rule_agent.py`

今日创建/填写。

当前能力：

```text
解析 RAG context 中的 Entity、retrieval score、属性文本。
识别七人乘坐类问题。
识别 how many passengers / seat 类问题。
在证据不足时返回 I don't know。
```

当前限制：

```text
不看原图本身。
不调用大模型。
不处理食物起源。
不处理油耗、距离、年份、发动机等需要精确知识的题。
```

### 3.3 `example_agents/user_config.py`

今日注册：

```text
rule -> RuleAgent
```

所以现在可以运行：

```bat
--model-name rule
```

当前已注册的轻量 Agent：

```text
random
debug
rule
idk
```

## 4. 今日运行结果

### 4.1 RuleAgent 小样本结果

结果目录：

```text
D:\CODE\Rainys-CRAG-MM\results_rule\2026-07-26_19-50-02
```

关键结果：

```text
Total turns: 3
I don't know responses: 2
Hallucinated responses: 1
Truthfulness score: -0.3333
```

三道题实际情况：

1. 七人乘车题：

```text
Query:
is this a good car for transporting seven passengers at once?

Ground truth:
no, the subaru wrx is a compact car with a total passenger capacity of 5 people.

RuleAgent:
No, the Subaru WRX appears to be a compact or standard passenger car, which is not suitable for transporting seven passengers at once.
```

解释：

```text
语义上接近正确，但因为本次使用 --eval-model None，评测只做精确匹配，所以被算错。
```

2. 油耗距离题：

```text
Query:
can the 2023 model with a 1.3l awd engine of this vehicle get from washington, dc to baltimore on 5 gallons of gas?

Ground truth:
2023 Chevrolet Trailblazer 1.3L AWD 可以，5 加仑约能跑 140 miles，路线约 40-45 miles。

RuleAgent:
I don't know
```

解释：

```text
图片检索没有识别出 Chevrolet Trailblazer，且题目需要油耗和两地距离知识。当前 RuleAgent 拒答是保守合理的。
```

3. 食物起源题：

```text
Query:
what is the origin of this food item?

Ground truth:
bacon cheese fries are from the United States...

RuleAgent:
I don't know
```

解释：

```text
当前 RuleAgent 没有食物起源规则，也没有开网页检索做知识补充，所以拒答。
```

## 5. 当前检索不准的问题

这是今天的核心理解之一。

### 5.1 问题现象

车辆题里图片检索最高分只有：

```text
0.642
0.650
```

并且候选实体混杂：

```text
Subaru WRX
Scion tC
Subaru Impreza
Toyota GR Corolla
Jeep Grand Cherokee
Chevrolet Silverado 2500HD
Kia Telluride
Kia Carnival
```

食物题也类似，返回了很多相似但不一定正确的食物：

```text
Carne asada fries
Hot dog
Halal snack pack
Chili cheese fries
French fries
```

### 5.2 原因

当前官方图片检索 pipeline 更像：

```text
视觉相似检索器
```

不是：

```text
精确识别器
```

它内部用 CLIP 类 embedding，把图片变成向量，然后在离线索引里找相似图片/实体。

所以它擅长：

```text
这张图像什么类型的东西？
这张图视觉上和哪些索引项相似？
```

但不一定擅长：

```text
精确车型
具体年份
具体发动机版本
具体菜名
```

另一个原因：

```text
当前关掉了网页检索，只靠图片检索。
```

图片检索只能给相似实体和部分属性，不能可靠补充：

```text
油耗
城市距离
食物起源
历史事实
官网参数
```

### 5.3 后续解决方法

建议下一步不要直接换 embedding 模型，先做低成本实验：

1. 打开网页检索观察：

```text
DebugAgent + 图片检索开 + 网页检索开
```

命令上就是去掉：

```bat
--suppress-web-search-api
```

先用 `debug`，不要急着用 `rule`，因为目标是观察网页 RAG context。

2. 让 Agent 学会“不盲信检索”：

```text
看 score 高不高。
看前几名候选是否一致。
看实体属性是否真的能回答问题。
证据不足就 I don't know。
```

3. 对第二题这种油耗题，需要组合：

```text
车型识别
油耗检索
距离检索
简单计算
```

4. 对第三题这种食物起源题，需要组合：

```text
食物识别
网页知识检索
来源判断
```

5. 更远期可以接入 VLM：

```text
Llama 11B Vision / Qwen-VL
```

它们不是替代 CLIP 检索，而是替代 DebugAgent / RuleAgent 作为真正会看图、读问题、读 RAG context、再回答的 Agent 大脑。

## 6. 本地跑简易 Agent 到底影响什么

这个问题今天已经讲清楚，后续继续沿用。

本地简易 Agent 影响的是：

```text
Agent 决策层
```

也就是：

```text
Agent 收到 query、image、history、rag_context 后，怎么生成 agent_response。
```

它暂时不影响：

```text
图片 embedding 模型
官方离线图片索引
网页索引内容
CRAG 数据集
ground_truth
评测器规则
```

当前 `RuleAgent` 不会让图片检索本身变准。它只能决定：

```text
哪些检索结果可信
哪些问题可以回答
哪些问题应该拒答
```

所以：

```text
retriever.py = 资料员
RuleAgent = 简单决策员
evaluator = 阅卷员
```

## 7. 评测理解更新

本次运行使用：

```bat
--eval-model None
```

含义：

```text
关闭语义裁判，只做精确匹配 + I don't know 判断。
```

因此七人乘车题虽然 RuleAgent 的回答语义接近正确，但文字不等于 ground_truth，被算作 hallucination。

这说明：

```text
本地简易评测适合看流程和保守策略。
最终要评估“意思对不对”，需要打开语义评测或人工检查。
```

## 8. 明天建议从哪里继续

建议第一步：

```text
先不要继续扩大 RuleAgent。
先用 DebugAgent 打开网页检索，观察网页 RAG context。
```

推荐命令：

```bat
cd /d D:\CODE\Rainys-CRAG-MM
.\.venv-light\Scripts\activate
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
set OPENAI_API_KEY=dummy
set MAX_BATCH_SIZE=1
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 2 --eval-model None --output-dir .\results_debug_image_web --display-conversations 1
```

注意：

```text
这条命令没有 --suppress-web-search-api，所以网页检索会打开。
```

明天重点观察：

```text
网页 RAG context 是否包含油耗信息。
网页 RAG context 是否包含 Washington DC 到 Baltimore 距离。
网页 RAG context 是否包含食物起源信息。
网页结果是否会被错误图片实体带偏。
```

如果网页检索内容可用，再考虑给 RuleAgent 增加：

```text
油耗/距离类规则
食物起源类规则
检索候选一致性判断
```

## 9. 明天新对话建议开场

可以对新模型说：

```text
请阅读：
D:\CODE\Rainys-CRAG-MM\CRAG-MM-handoff-2026-07-26.md
D:\CODE\Rainys-CRAG-MM\tips-7.26.md
D:\CODE\Rainys-CRAG-MM\CRAG-MM-learning-notes.md
D:\CODE\Rainys-CRAG-MM\CRAG-MM-problem-review.md

继续用老师的方式指导我做 CRAG-MM 项目。
我自己在 VS Code 的 cmd 终端操作。
请先解释为什么，再给命令。
不要再重复解释 --num-conversations 实际条数可能多一点这件事。
下一步建议是用 DebugAgent 打开网页检索，观察网页 RAG context。
```

## 10. 2026-07-27 重要更新：本地 Web Search 已修复

今天把本地网页检索问题移交给 Claude 后，已定位并修复。这个更新非常重要，后续模型不要再把状态判断为“web search 还坏着”。

最终结果：

```text
Web-only      只开网页检索，已跑通
Image-only    只开图片检索，已跑通，无回归
Web + Image   图片检索和网页检索一起开，已跑通
```

### 10.1 根因总结

共定位到 4 个独立问题。

Bug A：ChromaDB SQLite schema 版本不兼容。

```text
C 盘默认 Hugging Face 缓存里存在一份 web-search-index-public-test。
这份索引曾被新版 chromadb 迁移过，SQLite schema 多了 embedding_metadata_array 表。
当前 chromadb==1.0.15 读取这份新版 schema 时，Rust SQLite bindings 会 panic，表现为 Error loading hnsw index。
```

关键理解：

```text
HF_HOME / HF_HUB_CACHE / HF_DATASETS_CACHE 如果没有在当前 cmd 终端生效，snapshot_download() 会落回 C 盘默认缓存，从而读到被污染的 web index。
```

Bug B：`cragmm_search/search.py` 无条件加载 CLIP 图片模型。

```text
当运行 --suppress-image-search-api 时，local_evaluation.py 会把 image_model_name 设为 None。
但第三方包 search.py 原来仍然无条件执行 CLIPModel.from_pretrained(None)，导致 web-only 模式报错。
```

Bug C：Transformers `Pipeline` 基类收到 `model=None`。

```text
修掉 Bug B 后，如果只开 web search，image_model 是 None。
原代码 super().__init__(model=image_model, ...) 会把 None 传给 Pipeline，基类访问 self.model.device 时崩溃。
```

Bug D：Windows GBK 控制台编码。

```text
DebugAgent 打印 RAG context 时，网页内容里可能包含 ® 等特殊字符。
Windows cmd 默认 GBK 编码可能无法输出这些字符，导致 UnicodeEncodeError。
```

### 10.2 已修改文件

1. 第三方包：

```text
D:\CODE\Rainys-CRAG-MM\.venv-light\Lib\site-packages\cragmm_search\search.py
```

改动：

```text
只在 image_hf_dataset_id 不为 None 时加载 CLIP 图片搜索组件。
web-only 模式下不加载 CragImageKG。
Pipeline 基类 model 参数使用 image_model；如果没有 image_model，则 fallback 到 text_model。
图片分支增加安全检查，避免未开启 image search 时误走图片分支。
```

2. 项目代码：

```text
D:\CODE\Rainys-CRAG-MM\example_agents\debug_agent.py
```

改动：

```text
增加 _safe_str()，打印前用当前控制台编码做 errors="replace" 过滤，避免 Windows GBK 无法输出特殊字符。
```

### 10.3 当前必须注意的环境变量

用户使用的是 Windows `cmd`，不是 PowerShell，也不是 Linux shell。

所以 Claude 报告中的：

```bash
export HF_HOME="D:/CODE/hf_cache"
```

不能直接用。

cmd 中必须使用：

```bat
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
```

每次运行前建议都设置：

```bat
cd /d D:\CODE\Rainys-CRAG-MM
.\.venv-light\Scripts\activate
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
set OPENAI_API_KEY=dummy
set MAX_BATCH_SIZE=1
```

如遇 Hugging Face 网络检查问题，可在 cmd 中加：

```bat
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
```

### 10.4 当前最小验证命令

Web-only：

```bat
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --suppress-image-search-api --output-dir .\results_web_test --display-conversations 1
```

Image-only：

```bat
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --suppress-web-search-api --output-dir .\results_image_test --display-conversations 1
```

Web + Image：

```bat
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --output-dir .\results_web_image_test --display-conversations 1
```

### 10.5 后续建议

可以考虑清理 C 盘被新版 chromadb 污染的 web index 缓存，但不要自动删除，需用户确认。

只建议删除这个目录：

```text
C:\Users\王梓蕊\.cache\huggingface\hub\datasets--crag-mm-2025--web-search-index-public-test
```

不要删除同级其它目录，例如：

```text
image-search-index-public-test
models--*
```

提醒：

```text
search.py 的补丁在 .venv-light\Lib\site-packages 里，不在项目源码中。
如果重建 .venv-light 或重装 cragmm-search-pipeline，这些补丁会丢失。
```
