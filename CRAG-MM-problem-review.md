# CRAG-MM 问题复盘文档

本文件用于长期记录每天遇到的问题、原因、解决方式和更深层理解。  
每日追加，不替代每日交接文档。

## 2026-07-24 复盘

### 1. `requirements.txt` 和依赖安装理解不清

现象：

最初以为项目可以直接通过统一依赖文件顺利安装，但实际运行中陆续遇到缺包问题。

原因：

CRAG-MM 仓库虽然有 `requirements.txt`，但其中包含较重依赖，例如：

```text
vllm
torch
transformers
cragmm-search-pipeline
chromadb
```

Windows 本地轻量学习环境不适合直接完整安装官方大模型推理栈，尤其是 `vllm`。

解决方式：

采用轻量环境 `.venv-light`，根据实际运行报错逐步安装需要的包。

深层理解：

真实 AI 项目中，“依赖能装上”和“本机适合跑”是两件事。官方 baseline 往往面向 Linux + 大 GPU 环境，本地 Windows 更适合先做轻量调试和流程理解。

### 2. `No module named 'anthropic'`

现象：

只想运行 `RandomAgent`，却报缺少 `anthropic`。

直接原因：

`example_agents/user_config.py` 顶部提前导入 closed model agents：

```python
from .closed_model_agents import ClaudeAgent, GeminiAgent, GPTAgent
```

而 `closed_model_agents.py` 需要 `anthropic`、`openai`、`google-generativeai` 等 API 包。

解决方式：

把 `user_config.py` 改成懒加载：只有模型名包含 `claude`、`gpt`、`gemini` 时，才导入对应 Agent。

深层理解：

Python 的 import 会执行模块顶层代码。即使当前不使用某个类，只要模块被顶层导入，它依赖的包也可能被要求存在。懒加载能降低轻量实验阶段的环境负担。

### 3. `No module named 'vllm'`

现象：

只跑随机 Agent，却报缺少 `vllm`。

原因：

`user_config.py` 顶部提前导入 open source model agents，而 `open_source_model_agents.py` 依赖 `vllm`。

解决方式：

继续使用懒加载：只有模型名包含 `llama`、`qwen`、`pixtral`、`internvl` 时才导入 vLLM 相关 Agent。

深层理解：

`vllm` 适合 Linux + NVIDIA GPU 的大模型推理，不是当前 Windows 轻量学习阶段的优先事项。

### 4. `--eval-model None` 的 warning

现象：

运行时出现：

```text
WARNING: SEMANTIC EVALUATION IS DISABLED
No calls to LLM-as-a-Judge will be made!
Results will rely only on exact string matching.
```

原因：

传入：

```bat
--eval-model None
```

表示关闭 GPT-4o 等 LLM-as-a-Judge 语义评测。

解决方式：

无需解决，这是预期行为。当前学习阶段用本地规则评测即可。

深层理解：

`--eval-model None` 不是“不评测”，而是“不调用大模型做语义评测”。评测器仍会判断：

```text
是否精确匹配
是否包含 I don't know
否则算错
```

### 5. Hugging Face symlink warning

现象：

Windows 下出现符号链接 warning。

原因：

Hugging Face 缓存默认使用 symlink 节省空间，但当前 Windows 环境没有启用 Developer Mode 或管理员权限。

解决方式：

暂时忽略。下载仍可继续，只是可能多占磁盘。

深层理解：

这是 Windows 文件系统权限和缓存优化机制之间的问题，不是项目代码错误。

### 6. 误触发大网页索引下载

现象：

原本只是想跑最小闭环，却触发：

```text
crag-mm-2025/web-search-index-public-test
```

大约 17.6GB 的网页索引下载。

直接原因：

命令没有加：

```bat
--suppress-web-search-api
--suppress-image-search-api
```

所以 `local_evaluation.py` 初始化了官方搜索 pipeline。

解决方式：

最小闭环阶段应使用：

```bat
--suppress-web-search-api --suppress-image-search-api
```

并且仓库代码中已有保护：两种检索都 suppress 时，不初始化 `UnifiedSearchPipeline`。

深层理解：

RAG 项目中，检索索引和模型一样可能很大。做小实验时要先关闭不需要的组件，这叫控制变量。

### 7. RandomAgent 跑通但分数为 -1

现象：

结果：

```text
total: 16
hallucination: 16
truthfulness_score: -1.0
```

原因：

`RandomAgent` 随机输出字符串，不会回答问题，也不会说 `I don't know`。

解决方式：

保留该结果作为“最差底线”，后续建立 `IdkAgent` 作为安全底线。

深层理解：

CRAG-MM 不是鼓励大胆猜，而是鼓励可信回答。乱答会扣分，不知道不扣分。

## 2026-07-25 复盘

### 1. cmd 和 PowerShell 语法混用

现象：

用户在终端输入：

```powershell
$env:OPENAI_API_KEY="dummy"
$env:MAX_BATCH_SIZE="1"
```

报错：

```text
文件名、目录名或卷标语法不正确。
```

原因：

当前 VS Code 终端是 Windows `cmd`，不是 PowerShell。`$env:...` 是 PowerShell 语法。

解决方式：

cmd 中应使用：

```bat
set OPENAI_API_KEY=dummy
set MAX_BATCH_SIZE=1
```

深层理解：

不同 shell 的语法不同。后续学习统一只用 cmd，避免混乱。

### 2. Hugging Face 网络超时

现象：

运行数据集加载时出现：

```text
WinError 10060
requesting HEAD https://huggingface.co/...
```

原因：

`datasets` / `huggingface_hub` 想联网检查数据集文件，但网络连接超时。

解决方式：

如果本地已有缓存，可在 cmd 中设置：

```bat
set HF_DATASETS_OFFLINE=1
set HF_HUB_OFFLINE=1
```

深层理解：

Hugging Face 加载数据时不仅可能下载数据，也可能联网检查 metadata。离线变量可以让程序优先使用本地缓存。

### 3. `OPENAI_API_KEY=dummy` 的原因

现象：

即使传了 `--eval-model None`，仍需要设置 `OPENAI_API_KEY`。

原因：

`local_evaluation.py` 在非纯 `generate` 模式下会检查 `OPENAI_API_KEY` 是否存在。虽然 `--eval-model None` 不会真正调用 OpenAI，但检查仍存在。

解决方式：

当前学习阶段设置：

```bat
set OPENAI_API_KEY=dummy
```

深层理解：

这是脚本实现细节，不是 OpenAI 真被调用。`dummy` 只是让检查通过。

### 4. `--num-conversations 5` 实际跑出 6 条或更多

现象：

设置小样本数后，结果条数可能多 1 条，或昨天 RandomAgent 跑出 16 条。

原因：

评测器按 batch 处理，并且停止条件是在处理后检查。`RandomAgent.get_batch_size()` 原本返回 16，所以可能先跑完整 batch。

解决方式：

自定义 Agent 中设置：

```python
def get_batch_size(self) -> int:
    return 1
```

必要时设置：

```bat
set MAX_BATCH_SIZE=1
```

深层理解：

`--num-conversations` 控制总目标数量，`get_batch_size()` 控制每次喂给 Agent 的数量，`--display-conversations` 只控制显示数量。这三个概念不同。

### 5. `IdkAgent` 分数为 0 的意义

现象：

`IdkAgent` 结果：

```text
miss: 6
hallucination: 0
truthfulness_score: 0.0
```

原因：

所有题都回答 `I don't know`。

解决方式：

这不是问题，而是目标结果。它证明拒答不扣分。

深层理解：

建立两个基线：

```text
RandomAgent = 乱答底线，-1
IdkAgent = 安全拒答底线，0
```

后续 Agent 必须至少比 `IdkAgent` 更好，才说明它有价值。

### 6. `DebugAgent` 的作用

现象：

用户需要知道 Agent 到底收到了什么输入。

解决方式：

新增 `DebugAgent`，打印：

```text
Query
Domain
Has image
History
RAG context
```

深层理解：

在复杂系统里，先观察接口输入，比直接写聪明逻辑更重要。`DebugAgent` 是理解工作流的工具，不是为了拿分。

### 7. 图片检索索引加载失败：`Error loading hnsw index`

现象：

打开 image search 后报：

```text
chromadb.errors.InternalError
Error loading hnsw index
```

原因排查：

1. 先怀疑缓存损坏，删除并重下图片索引。
2. 重下后仍失败，排除“下载不完整”。
3. 进一步判断是 `chromadb` 版本或 Windows 缓存路径兼容问题。

解决方式：

把 `chromadb` 从较新的 `1.5.9` 降到：

```text
chromadb==1.0.15
```

并把 Hugging Face 缓存切到 D 盘英文路径：

```bat
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
```

深层理解：

官方预构建的 Chroma/HNSW 索引对 `chromadb` 版本和本地路径环境敏感。Windows + 中文路径 + 新版依赖容易暴露兼容性问题。

### 8. 图片特征提取失败：`BaseModelOutputWithPooling` 没有 `.norm`

现象：

图片索引能初始化后，进一步报：

```text
AttributeError: 'BaseModelOutputWithPooling' object has no attribute 'norm'
```

原因：

`cragmm_search` 第三方包中的原代码假设：

```python
model.get_image_features(**inputs)
```

直接返回 `torch.Tensor`。

但当前 `transformers==5.14.1` 下，它返回的是：

```text
BaseModelOutputWithPooling
```

真正的向量在：

```text
pooler_output
```

或其他字段中。

解决方式：

Claude 帮用户手动修补第三方包：

```text
D:\CODE\Rainys-CRAG-MM\.venv-light\Lib\site-packages\cragmm_search\image_search_mock_api\image_search.py
```

修复逻辑：

```python
output = model.get_image_features(**inputs)

if hasattr(output, 'pooler_output'):
    features = output.pooler_output
elif hasattr(output, 'image_embeds'):
    features = output.image_embeds
elif isinstance(output, torch.Tensor):
    features = output
else:
    features = output[0]
```

深层理解：

第三方库和 Hugging Face `transformers` 的输出格式可能随版本变化。兼容修复的核心是先从模型输出对象中取出真正的 tensor，再做向量归一化。

### 9. 图片检索开启但 `RAG context` 为空壳

现象：

DebugAgent 打印：

```text
RAG context: <search results></search results>
```

原因：

图片搜索已经被调用，但 `utils/retriever.py` 中有阈值：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

检索候选项可能分数都低于 0.75，因此被过滤掉。

解决方式：

下一步建议为了学习目的临时把阈值调成：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.0
```

以观察原始检索候选结构。

深层理解：

`[EMPTY]` 和 `<search results></search results>` 不一样：

```text
[EMPTY] = 检索没开
<search results></search results> = 检索开了，但结果被过滤后没有可用内容
```

阈值过滤是减少 hallucination 的策略，但学习阶段可以调低阈值观察系统内部。

### 10. 缓存混乱

现象：

用户多次下载、删除、切换缓存路径，不确定哪个要用。

当前结论：

1. C 盘 Hugging Face 缓存仍有约 24.67GB。
2. C 盘图片索引已删除。
3. C 盘网页索引仍在，约 16.42GB，后续可能有用。
4. D 盘 `D:\CODE\hf_cache` 是今天新设的推荐 HF 缓存，约 3.80GB。
5. CRAG 图片缓存仍在 `C:\Users\王梓蕊\AppData\Local\cragmm_images_cache`，约 3.72GB。

建议：

先不要删 C 盘网页索引，也不要动 CRAG 图片缓存。后续确认 D 盘缓存稳定后再清理。

## 2026-07-26 复盘

### 1. 图片检索并不是没有工作，而是原阈值过滤太严格

现象：

之前 DebugAgent 看到：

```text
RAG context: <search results></search results>
```

一开始容易误以为图片检索没返回结果。

今天通过打印过滤前 RAW RESULTS 发现，图片检索其实返回了 30 条候选，例如：

```text
[Result 1] score=0.642451286315918
entities: ['Subaru WRX']
```

原因：

`utils/retriever.py` 原始阈值是：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

而当前样例最高分只有约：

```text
0.642
0.650
```

所以候选全被过滤，最终只剩空的 `<search results></search results>` 外壳。

解决方式：

今天先后做了：

```text
1. 临时把阈值改到 0.0 观察所有候选。
2. 打印 IMAGE SEARCH RAW RESULTS。
3. 当前把阈值设为 0.6 作为观察用中间值。
```

深层理解：

```text
0.75 不是错误，而是官方保守策略。
低置信检索结果可能误导 Agent，所以官方宁可过滤。
学习阶段调低阈值，是为了看清系统内部，不等于最终策略。
```

### 2. Agent 原来看不到 score，导致无法判断检索证据可信度

现象：

原始 `RAG context` 中只有：

```text
Entity 1: Subaru WRX
Entity attributes: ...
```

没有告诉 Agent：

```text
这个 Subaru WRX 是 0.64 分，还是 0.95 分。
```

原因：

`score` 只在 `retriever.py` 中用于过滤，没有写进最终交给 Agent 的文本。

解决方式：

今天把 score 注入到 `RAG context`：

```text
Entity 1: Subaru WRX (retrieval score: 0.642)
```

中文专业术语：

```text
检索置信度注入 / RAG 上下文增强
```

深层理解：

```text
RAG 不只是“给资料”，还应该让 Agent 知道资料可信度。
没有置信度时，Agent 容易把弱检索结果当成强证据。
```

### 3. 官方图片检索不准，不是因为代码坏了

现象：

车辆题中检索结果混杂：

```text
Subaru WRX
Scion tC
Subaru Impreza
Toyota GR Corolla
Jeep Grand Cherokee
Kia Telluride
Kia Carnival
```

食物题中检索结果也混杂：

```text
Carne asada fries
Hot dog
Halal snack pack
Chili cheese fries
French fries
```

原因：

官方 pipeline 的图片检索本质是：

```text
视觉相似检索
```

不是：

```text
精确识别
```

它使用 CLIP 类 embedding 找视觉向量相近的候选。它可以找到“大概像什么”，但不保证精确识别：

```text
具体车型
具体年份
具体发动机版本
具体菜名
```

解决方向：

短期：

```text
看 score。
看候选是否集中。
证据弱就拒答。
打开网页检索补充知识。
```

中期：

```text
写更好的规则或提示，让 Agent 不盲信低分候选。
结合网页搜索判断油耗、距离、起源等知识问题。
```

长期：

```text
接入视觉语言模型，如 Llama 11B Vision / Qwen-VL，让 Agent 自己看图并判断检索结果是否可信。
```

深层理解：

```text
检索器给的是候选证据，不是标准答案。
Agent 必须学会“使用检索但不迷信检索”。
```

### 4. 第二题和第三题不是单纯因为没联网才答不出

现象：

第二题：

```text
can the 2023 model with a 1.3l awd engine of this vehicle get from washington, dc to baltimore on 5 gallons of gas?
```

RuleAgent 回答：

```text
I don't know
```

第三题：

```text
what is the origin of this food item?
```

RuleAgent 也回答：

```text
I don't know
```

原因：

第二题需要：

```text
识别车型
找到油耗
知道两地距离
做简单计算
```

当前图片检索没有识别出标准答案中的 `Chevrolet Trailblazer`，网页检索也关闭了，所以没有油耗和距离资料。

第三题需要：

```text
识别具体食物
查询食物起源
```

当前图片检索只大概返回 fries 类食物，没有稳定识别为 `bacon cheese fries`，网页检索也关闭了。

解决方式：

下一步建议先跑：

```text
DebugAgent + 图片检索开 + 网页检索开
```

观察网页 RAG context 是否包含：

```text
油耗
路线距离
食物起源
```

深层理解：

```text
没联网是原因之一，但不是唯一原因。
如果图片识别错了，网页检索可能围绕错误实体查资料，反而扩大错误。
真正要解决的是“图片候选可信度判断 + 网页知识补充 + Agent 保守决策”的组合问题。
```

### 5. RuleAgent 得分为负，不代表规则方向完全错

现象：

RuleAgent 小样本结果：

```text
Total turns: 3
I don't know responses: 2
Hallucinated responses: 1
Truthfulness score: -0.3333
```

其中七人乘车题：

```text
Ground truth:
no, the subaru wrx is a compact car with a total passenger capacity of 5 people.

RuleAgent:
No, the Subaru WRX appears to be a compact or standard passenger car, which is not suitable for transporting seven passengers at once.
```

原因：

运行时使用：

```bat
--eval-model None
```

评测不调用语义裁判，只做精确匹配。虽然 RuleAgent 语义上接近正确，但字符串不完全等于 ground_truth，所以被算作 hallucination。

解决方向：

当前学习阶段：

```text
继续人工查看 response.jsonl，理解 Agent 为什么答。
必要时让规则输出更贴近标准答案格式。
```

后续正式评估：

```text
打开语义评测，或使用人工检查，判断意思是否正确。
```

深层理解：

```text
本地简易评测适合看流程和安全性。
精确匹配分数不完全等于真实语义能力。
```

### 6. 本地简易 Agent 不能提高检索器能力

现象：

今天用户问：本地跑简易 Agent 到底在影响什么。

结论：

`RuleAgent` 影响的是：

```text
Agent 决策层
```

不影响：

```text
CLIP embedding 模型
官方图片索引
网页索引
数据集
ground_truth
评测器规则
```

解决理解：

`RuleAgent` 只能决定：

```text
什么时候信检索结果。
什么时候拒答。
怎么根据 RAG context 组织答案。
```

它不能让图片检索本身更准。

深层理解：

```text
检索器、Agent、评测器是三层不同组件。
今天的本地简易 Agent 是在训练/实验“决策层”，不是在改造“检索层”。
```

### 7. 终端输出太多 RAW RESULTS，后续可能需要开关

现象：

每道题都会打印 30 条图片检索候选，终端输出很长。

原因：

今天为了学习，在 `retriever.py` 中直接加入了 print。

解决方向：

短期保留，因为还要继续观察检索。

后续如果影响阅读，可以改成：

```text
只在 debug 模式打印。
只打印前 5 条。
用环境变量控制是否打印。
```

深层理解：

```text
调试输出适合学习阶段，但最终实验需要更干净的日志。
```

## 2026-07-27 复盘

### 1. Web search 报 `Error loading hnsw index`

现象：

打开网页检索时，终端报：

```text
chromadb.errors.InternalError: Error executing plan:
Error sending backfill request to compactor:
Error constructing hnsw segment reader:
Error creating hnsw segment reader:
Error loading hnsw index
```

排查过程：

```text
1. 单独跑 image-only，能跑通。
2. 单独跑 web-only，报错。
3. web + image 一起跑，也报错。
```

结论：

```text
问题集中在 web search 的 Chroma/HNSW 网页索引读取层。
```

最终根因：

```text
机器上存在两份 web search index 缓存。
C 盘默认缓存被新版 chromadb 迁移过，SQLite schema 多了 embedding_metadata_array 表。
当前 chromadb==1.0.15 读取这份新版 schema 时会触发 Rust 层 panic，表面表现为 Error loading hnsw index。
```

解决方式：

```text
确保 HF_HOME / HF_HUB_CACHE / HF_DATASETS_CACHE 在当前 cmd 终端真正生效，让 snapshot_download() 使用 D:\CODE\hf_cache 的干净副本。
```

cmd 写法：

```bat
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
```

深层理解：

```text
Hugging Face 缓存路径不是“写过一次就永久生效”。
cmd 里的 set 只对当前终端窗口有效。
如果没设，程序可能回到 C 盘默认缓存，读到被污染索引。
```

### 2. Web-only 模式下第三方 search.py 仍加载图片模型

现象：

运行：

```bat
--suppress-image-search-api
```

后，`local_evaluation.py` 会把 image model 设置为 None，但第三方包仍尝试加载：

```text
CLIPModel.from_pretrained(None)
```

原因：

```text
cragmm_search/search.py 原代码无条件初始化图片搜索组件。
```

解决方式：

修改：

```text
D:\CODE\Rainys-CRAG-MM\.venv-light\Lib\site-packages\cragmm_search\search.py
```

修复为：

```text
只有 image_hf_dataset_id 不为 None 时才加载 CLIP 和 CragImageKG。
```

深层理解：

```text
--suppress-image-search-api 不只是“不查询图片”，还应该“不初始化图片检索组件”。
```

### 3. Pipeline 基类不能收到 model=None

现象：

修复无条件加载 CLIP 后，web-only 模式又遇到：

```text
AttributeError: 'NoneType' object has no attribute 'device'
```

原因：

```text
Transformers Pipeline 基类初始化时需要一个有效 model。
web-only 模式下 image_model=None，原代码仍把 image_model 传给 super().__init__。
```

解决方式：

```text
如果 image_model 存在，就传 image_model。
否则传 text_model。
```

深层理解：

```text
UnifiedSearchPipeline 同时服务图片检索和网页检索。
当只开网页检索时，它也需要一个有效底座模型传给 Pipeline 基类。
```

### 4. Windows GBK 编码导致 DebugAgent 打印失败

现象：

网页 RAG context 中含有特殊字符，例如：

```text
®
```

Windows cmd 默认 GBK 编码无法输出，导致：

```text
UnicodeEncodeError
```

解决方式：

修改：

```text
D:\CODE\Rainys-CRAG-MM\example_agents\debug_agent.py
```

增加安全打印逻辑：

```text
打印前按当前控制台编码 encode(errors="replace").decode()
```

深层理解：

```text
网页检索内容来自真实网页片段，字符集比图片实体属性更复杂。
Windows cmd 对 Unicode 的支持不如 UTF-8 环境稳定。
```

### 5. Claude 报告里的 export 不能直接用

现象：

Claude 给出：

```bash
export HF_HOME="D:/CODE/hf_cache"
```

问题：

```text
这是 Linux/macOS shell 语法，不适用于当前 Windows cmd。
```

正确方式：

```bat
set HF_HOME=D:\CODE\hf_cache
set HF_HUB_CACHE=D:\CODE\hf_cache\hub
set HF_DATASETS_CACHE=D:\CODE\hf_cache\datasets
```

深层理解：

```text
同一个环境变量，在不同 shell 里写法不同。
当前学习阶段坚持只用 Windows cmd，避免混用 PowerShell 或 Linux 写法。
```

### 6. 当前修复状态

最终验证：

```text
Web-only 已跑通。
Image-only 已跑通。
Web + Image 已跑通。
```

后续风险：

```text
search.py 和 image_search.py 的关键补丁都在 .venv-light\Lib\site-packages 里。
如果重建虚拟环境或重装 cragmm-search-pipeline，补丁会消失。
```

建议：

```text
后续交接文件必须记录这些第三方包补丁。
租云服务器时也要确认官方包版本是否仍需要这些补丁。
```
