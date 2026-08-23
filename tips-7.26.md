# tips-7.26

这是给我自己看的今日小总结，不是给模型看的完整交接文档。

## 1. 今天我到底做到哪一步

昨天重点是：

```text
看清 Agent 收到了什么。
```

今天重点是：

```text
看清图片检索器到底返回了什么，并开始让本地简易 Agent 做一点点保守决策。
```

今天没有接入真正的大视觉语言模型：

```text
没有接 Llama 11B Vision
没有接 Qwen-VL
没有租云服务器
没有正式跑比赛分数优化
```

今天做的是本地学习版：

```text
DebugAgent 看输入
RuleAgent 用规则做少量回答
```

## 2. 这些天每一步的中文专业叫法

我问过“这些步骤用专业术语叫什么”，今天要记住这张表。

| 我做的事 | 中文专业叫法 | 作用 |
|---|---|---|
| 跑 RandomAgent | 随机基线实验 | 验证流程能跑通 |
| 写 IdkAgent | 拒答基线 / 安全基线 | 验证 I don't know 不扣分 |
| 写 DebugAgent | 输入观测器 / 调试型 Agent | 看 Agent 收到什么 |
| 开图片检索 | 图像检索链路验证 | 看图片是否能搜出相似实体 |
| 把阈值 0.75 改低 | 检索召回观察 / 阈值调参 | 看被过滤前的候选 |
| 打印 RAW RESULTS | 原始检索结果暴露 | 看 score 和实体名 |
| 把 score 写进 RAG context | 检索置信度注入 / RAG 上下文增强 | 让 Agent 知道证据可信度 |
| 写 RuleAgent | 规则型保守 Agent | 本地简易决策 |

一句话总结：

```text
从跑通流程，到建立安全底线，再到拆开检索黑箱，最后开始做本地规则决策。
```

## 3. retriever.py 是什么

`retriever.py` 中文叫：

```text
检索器
```

更完整叫：

```text
RAG 检索器
```

它不是 Agent，也不是评测器。

它的位置是：

```text
图片 + 问题
  ↓
retriever.py 检索器
  ↓
RAG context 检索上下文
  ↓
Agent
```

可以理解为：

```text
retriever.py = 资料员
Agent = 答题人
evaluator = 阅卷员
```

今天我们改 `retriever.py`，不是让 Agent 变聪明，而是让资料员把更多线索交给 Agent。

## 4. 30 条 Result 是什么

终端里看到：

```text
========== IMAGE SEARCH RAW RESULTS ==========
[Result 1] score=0.642451286315918
entities: ['Subaru WRX']
...
[Result 30] score=...
entities: [...]
==============================================
```

这 30 条不是答案，也不是标准答案。

它们是：

```text
图片检索器从官方离线图片索引里找出的 30 个最相似候选。
```

因为代码里有：

```python
NUM_IMG_SEARCH_RESULTS = 30
```

每一条的意思：

```text
Result 1 = 第 1 个最相似候选
score = 图片相似度分数
entities = 这个候选对应的实体名
```

这些是过滤前的原始候选。之后 `retriever.py` 会根据阈值过滤，再整理成 `RAG context` 给 Agent。

## 5. 今天发现图片检索为什么不准

今天最重要的技术理解：

```text
官方图片检索 pipeline 是视觉相似检索，不是精确识别。
```

它更像在问：

```text
这张图视觉上像哪些索引里的东西？
```

不是在保证：

```text
这张图百分百就是某个具体车型或菜品。
```

车辆题里最高分只有：

```text
0.642
0.650
```

这说明检索器自己也不是很确定。

所以官方原始阈值：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

会把这些结果全部过滤掉。

这不是 bug，而是一种保守策略：

```text
不够确定的检索资料，不要交给 Agent，避免误导 Agent。
```

## 6. 为什么二三题跑不出来

第二题是油耗距离题。

它需要：

```text
1. 识别图里的车是什么
2. 找到这辆车的油耗
3. 知道 Washington DC 到 Baltimore 的距离
4. 做 5 gallons × mpg 的计算
```

现在问题是：

```text
图片检索没有识别出 ground_truth 里的 Chevrolet Trailblazer。
网页检索又被关闭了。
RuleAgent 也没有油耗/距离规则。
```

所以它回答 `I don't know` 是合理的。

第三题是食物起源题。

它需要：

```text
1. 识别图里是什么食物
2. 查询这个食物的起源
```

当前图片检索只大概搜到 fries 类食物，但没有稳定识别到标准答案里的 `bacon cheese fries`。

而且网页检索关闭，所以没有外部知识补充。

所以第三题也应该先拒答。

## 7. 没联网是不是主要原因

有关系，但不是唯一原因。

更准确：

```text
图片检索不准 = 第一层问题
网页检索关闭 = 第二层问题
RuleAgent 太简单 = 第三层问题
```

第二题和第三题确实需要网页知识：

```text
油耗
距离
食物起源
```

但如果第一步识别实体错了，网页检索也可能围绕错误实体查资料。

所以后续要解决的是组合问题：

```text
先判断图片检索候选是否可信
再用网页检索补知识
最后让 Agent 谨慎回答
```

## 8. 本地简易 Agent 到底影响什么

`RuleAgent` 影响的是：

```text
Agent 决策层
```

它决定：

```text
收到 query 和 rag_context 后，要不要回答，怎么回答。
```

它不影响：

```text
CLIP embedding 模型
官方图片索引
网页索引
数据集
ground_truth
评测器
```

所以本地简易 Agent 不能让检索本身变准。

它只能做：

```text
有证据时回答
证据弱时拒答
不要盲信低分检索结果
```

这就是今天的核心：先别追求聪明，先追求可信。

## 9. RuleAgent 今天的结果怎么理解

结果目录：

```text
D:\CODE\Rainys-CRAG-MM\results_rule\2026-07-26_19-50-02
```

分数：

```text
Total turns: 3
I don't know responses: 2
Hallucinated responses: 1
Truthfulness score: -0.3333
```

注意：

```text
这次用了 --eval-model None。
```

这意味着：

```text
没有语义裁判，只做精确匹配。
```

七人乘车题里，RuleAgent 的回答意思接近正确：

```text
No, the Subaru WRX appears to be a compact or standard passenger car...
```

标准答案是：

```text
no, the subaru wrx is a compact car with a total passenger capacity of 5 people.
```

意思接近，但文字不完全一样，所以被本地精确匹配算错。

这说明：

```text
本地简易评测适合学习流程，不一定能准确判断语义正确。
```

## 10. 明天最建议做什么

明天不要急着继续扩大 RuleAgent。

建议先做：

```text
DebugAgent + 图片检索 + 网页检索
```

目的：

```text
观察网页检索会给 Agent 什么资料。
```

命令关键点：

```text
去掉 --suppress-web-search-api
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

明天要看：

```text
网页 RAG context 是否包含油耗。
网页 RAG context 是否包含两地距离。
网页 RAG context 是否包含食物起源。
网页检索会不会被错误图片实体带偏。
```

一句话总结今天：

```text
今天不是换更强模型，而是学会看检索证据、暴露置信度，并写出第一个本地规则型保守 Agent。
```

## 11. 当前整体流程图

以后只要忘了系统怎么走，就看这张：

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
evaluator 评测器
  ↓
分数
```

再翻译成人话：

```text
图片和问题是题目。
retriever.py 是资料员。
RAG context 是资料员找到并整理好的参考资料。
Agent 是答题人。
agent_response 是答题人的最终答案。
evaluator 是阅卷员。
ground_truth 是标准答案，只给阅卷员看，不给 Agent 看。
```

所以我现在改 `RuleAgent`，影响的是：

```text
答题人怎么决策。
```

我现在改 `retriever.py`，影响的是：

```text
资料员给答题人什么资料。
```

## 12. 常看常改代码文件速查

| 文件 | 中文名 | 作用 | 现在怎么对待 |
|---|---|---|---|
| `local_evaluation.py` | 本地评测入口 | 运行整个本地评测流程 | 常运行，少改 |
| `utils/retriever.py` | RAG 检索器 / 资料员 | 做图片检索、网页检索，生成 `RAG context` | 当前常改 |
| `example_agents/user_config.py` | Agent 注册表 | 让 `--model-name xxx` 找到对应 Agent | 常改 |
| `example_agents/base_agent.py` | Agent 基类 | 规定 Agent 必须长什么样 | 主要读 |
| `example_agents/random_agent.py` | 随机基线 Agent | 乱答，用来证明流程通 | 基本不改 |
| `example_agents/idk_agent.py` | 拒答基线 Agent | 永远回答 `I don't know` | 基本不改 |
| `example_agents/debug_agent.py` | 输入观测器 | 打印 Agent 收到的材料 | 常用，偶尔改 |
| `example_agents/rule_agent.py` | 规则型保守 Agent | 本地规则判断，能答才答 | 当前常改 |
| `example_agents/prompt_constants.py` | 系统提示词文件 | 给未来 LLM/VLM Agent 用的提示词 | 后续可能改 |
| `evaluation/evaluator.py` | 评测器核心 | 生成回答、评测回答、保存结果 | 谨慎读，尽量不改 |
| `evaluation/evaluation_utils.py` | 分数计算工具 | 算 correct、miss、hallucination、truthfulness_score | 主要读 |
| `evaluation/llm_judge.py` | 语义裁判 | 打开语义评测时调用 LLM 判答案 | 后续看 |
| `.venv-light\Lib\site-packages\cragmm_search\image_search_mock_api\image_search.py` | 第三方图片检索补丁文件 | 修过图片特征提取返回值问题 | 不常改，但重装会丢补丁 |

当前最核心的四个学习文件：

```text
utils/retriever.py
example_agents/user_config.py
example_agents/debug_agent.py
example_agents/rule_agent.py
```

简单记：

```text
retriever.py 管资料。
user_config.py 管选哪个 Agent。
debug_agent.py 管看输入。
rule_agent.py 管本地规则作答。
```

## 13. 2026-07-27 补充：Web Search 已修好

今天 Claude 帮忙修复了本地网页检索。

现在三个模式都可以跑：

```text
Web-only：只开网页检索
Image-only：只开图片检索
Web + Image：图片和网页一起开
```

这说明：

```text
昨天的问题不是 Agent 写错，也不是图片检索坏。
真正问题在 web search 的 Chroma/HNSW 索引读取和第三方 search.py 的 web-only 兼容性。
```

### 根因用人话理解

第一层问题：

```text
C 盘默认 HF 缓存里有一份被新版 chromadb 迁移过的 web index。
当前 chromadb==1.0.15 读不了那份新版 schema。
所以会报 Error loading hnsw index。
```

第二层问题：

```text
只开 web search 时，第三方包 search.py 仍然想加载图片 CLIP 模型。
但 image_model_name 已经是 None，于是报错。
```

第三层问题：

```text
只开 web search 时，Pipeline 基类不能收到 model=None。
所以要用 text_model 当 fallback。
```

第四层问题：

```text
Windows cmd 默认 GBK，有些网页字符打印不出来。
DebugAgent 需要安全打印。
```

### 已改过的文件

第三方包：

```text
.venv-light\Lib\site-packages\cragmm_search\search.py
```

作用：

```text
修复 web-only 模式。
只有需要图片检索时才加载 CLIP。
只有需要图片检索时才加载 image index。
web-only 时用 text_model 传给 Pipeline 基类。
```

项目文件：

```text
example_agents\debug_agent.py
```

作用：

```text
安全打印 RAG context，避免 Windows GBK 编码报错。
```

### 今天最重要的 cmd 环境变量

不要用 Claude 报告里的 `export`，那是 Linux/macOS 写法。

我用的是 Windows `cmd`，所以要写：

```bat
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
```

每次运行前建议完整设置：

```bat
cd /d D:\CODE\Rainys-CRAG-MM
.\.venv-light\Scripts\activate
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
set OPENAI_API_KEY=dummy
set MAX_BATCH_SIZE=1
```

### 验证命令

只开网页检索：

```bat
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --suppress-image-search-api --output-dir .\results_web_test --display-conversations 1
```

图片和网页一起开：

```bat
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --output-dir .\results_web_image_test --display-conversations 1
```

### 重要提醒

这些补丁有两个在第三方包里：

```text
.venv-light\Lib\site-packages\cragmm_search\search.py
.venv-light\Lib\site-packages\cragmm_search\image_search_mock_api\image_search.py
```

如果以后重建虚拟环境，或者重装 `cragmm-search-pipeline`，补丁会消失。

以后如果又报 web search / image search 的老错误，要先检查这些补丁还在不在。
