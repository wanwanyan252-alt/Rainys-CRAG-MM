# tips-7.25

这是给我自己看的今日小总结，不是给模型看的交接文档。

## 1. 今天我到底做到了哪一步

昨天是：

```text
证明考试系统能跑。
```

今天是：

```text
开始看清楚考试系统内部给 Agent 传了什么材料。
```

今天没有让真正的大模型回答问题：

```text
Llama 没接入
GPT/Gemini/Claude 没作为答题大脑接入
gpt-4o 阅卷也关掉了
```

现在用的是：

```text
IdkAgent：永远回答 I don't know
DebugAgent：打印输入材料，然后也回答 I don't know
```

所以今天的重点不是变聪明，而是：

```text
看清楚流程，看清楚输入，看清楚检索有没有进来。
```

## 2. 图片和图片索引不是一个东西

今天最容易混的点：

```text
图片 != 图片索引
```

图片是题目里那张图，比如：

```text
用户看到的一辆车
用户看到的一盘食物
用户看到的一栋楼
```

它是“当前要回答的问题对象”。

当前图片缓存主要在：

```text
C:\Users\王梓蕊\AppData\Local\cragmm_images_cache
```

图片索引是官方提前准备好的参考资料库。

它不是某一张题目图片，而是：

```text
很多参考图片 + 它们的向量 + 实体名 + 属性信息
```

当前图片索引在：

```text
D:\CODE\hf_cache\hub\datasets--crag-mm-2025--image-search-index-public-test
```

更准确的流程：

```text
C 盘题目图片
  ↓
CLIP 算成图片向量
  ↓
D 盘官方图片索引
  ↓
查相似图片 / 实体 / 属性
  ↓
生成 rag_context
```

不是“D 盘索引 C 盘所有图片”，而是：

```text
用当前题目图片当查询，去 D 盘官方图片索引库里找相似资料。
```

形象理解：

```text
题目图片 = 我手里拿着的一张照片
图片索引 = 图书馆的检索目录
CLIP = 把照片翻译成检索号码的人
检索结果 = 图书馆里可能相关的资料卡片
```

## 3. IdkAgent 的意义

`IdkAgent` 很笨，但它很重要。

它每题都回答：

```text
I don't know
```

CRAG-MM 的评分规则：

```text
答对 +1
不知道 0
答错 -1
```

所以：

```text
RandomAgent 乱答 -> -1
IdkAgent 全拒答 -> 0
```

这说明：

```text
不乱答本身就是一种进步。
```

这个比赛不是鼓励“勇敢猜”，而是鼓励：

```text
有证据再答，没证据就说不知道。
```

## 4. DebugAgent 的意义

`DebugAgent` 不是为了拿高分。

它是显微镜。

它帮我看到 Agent 收到了什么：

```text
Query: 当前问题
Domain: 题目领域
Has image: 有没有图片
History: 历史对话
RAG context: 检索上下文
```

没有 DebugAgent 时，我只能看到最后分数。

有 DebugAgent 后，我能看到：

```text
材料到底有没有传进来？
检索有没有打开？
rag_context 是空还是有内容？
```

工程上先看清输入，比急着写复杂逻辑更重要。

## 5. `[EMPTY]` 和 `<search results></search results>` 不一样

今天看到两个很像但本质不同的情况。

### `[EMPTY]`

表示：

```text
没有开启检索。
```

比如命令里同时写了：

```bat
--suppress-web-search-api
--suppress-image-search-api
```

这时：

```text
get_rag_context 直接返回空字符串
```

所以 DebugAgent 打印：

```text
RAG context: [EMPTY]
```

### `<search results></search results>`

表示：

```text
检索打开了，但最后没有留下可用结果。
```

今天打开了图片检索，关闭了网页检索：

```bat
--suppress-web-search-api
```

但没有写：

```bat
--suppress-image-search-api
```

所以图片检索是开的。

结果打印：

```text
RAG context: <search results></search results>
```

这说明：

```text
图片检索 pipeline 跑了；
但候选结果可能被阈值过滤掉了。
```

## 6. 图片检索为什么会被过滤

在：

```text
utils/retriever.py
```

里面有：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

意思是：

```text
只有图片检索相似度 score > 0.75 的结果，才会进入 rag_context。
```

如果检索结果分数不够高，就被丢掉。

这是一种保守策略：

```text
不够确定的资料，不要喂给 Agent。
```

因为错误资料可能让 Agent 胡答，造成 hallucination。

明天为了学习，可以临时把阈值调成：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.0
```

这样能看见原始候选结果长什么样。

注意：

```text
调低阈值是观察实验，不一定是最终比赛策略。
```

## 7. Claude 为什么一改就好了

今天图片检索报过这个错：

```text
AttributeError: 'BaseModelOutputWithPooling' object has no attribute 'norm'
```

原代码以为：

```python
model.get_image_features(...)
```

直接返回一个 tensor。

但当前环境里，它返回的是一个包装对象：

```text
BaseModelOutputWithPooling
```

真正的向量在里面，比如：

```text
pooler_output
```

Claude 修的本质是：

```text
先打开包装盒，取出真正的 tensor，再做 norm 归一化。
```

形象理解：

```text
原代码：以为快递员直接给了手机，马上按开机键。
实际情况：快递员给的是盒子，手机在盒子里。
修复后：先打开盒子拿出手机，再按开机键。
```

这不是 Agent 变聪明了，而是：

```text
图片检索工具终于能正常算图片向量了。
```

## 8. 今天命令行学到的核心

我现在先只学 Windows `cmd`，不要混 PowerShell。

常用结构：

```bat
python 文件.py
```

意思是：

```text
运行某个 Python 文件。
```

比如：

```bat
python local_evaluation.py
```

`-m` 的意思是 module：

```bat
python -m pip install pandas
python -m venv .venv-light
```

意思是：

```text
按模块方式运行 pip 或 venv。
```

创建虚拟环境：

```bat
python -m venv .venv-light
```

激活虚拟环境：

```bat
.\.venv-light\Scripts\activate
```

退出：

```bat
deactivate
```

设置当前终端临时变量：

```bat
set OPENAI_API_KEY=dummy
set MAX_BATCH_SIZE=1
set HF_HOME=D:\CODE\hf_cache
```

这些 `set` 只对当前 cmd 窗口有效。

## 9. 今天命令怎么读

今天最重要的命令：

```bat
python local_evaluation.py --dataset-type single-turn --model-name debug --num-conversations 1 --eval-model None --suppress-web-search-api --output-dir .\results_debug_image --display-conversations 1
```

翻译成人话：

```text
用 Python 运行 local_evaluation.py；
使用单轮数据集；
使用 DebugAgent；
大约跑 1 个会话；
不用大模型阅卷；
关闭网页搜索；
打开图片搜索；
结果保存到 results_debug_image；
终端展示 1 条样例。
```

为什么图片搜索是打开的？

因为命令里没有写：

```bat
--suppress-image-search-api
```

所以只关闭了 web search，没有关闭 image search。

## 10. 今天最终状态

现在我已经有：

```text
RandomAgent 结果：乱答，-1
IdkAgent 结果：全不知道，0
DebugAgent 无检索：看到 rag_context 是 [EMPTY]
DebugAgent 开图片检索：看到 rag_context 是 <search results></search results>
```

这说明我已经能区分：

```text
没开检索
开了检索但结果被过滤
```

## 11. 明天从哪里开始

明天建议第一件事：

打开：

```text
D:\CODE\Rainys-CRAG-MM\utils\retriever.py
```

临时把：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.75
```

改成：

```python
IMG_SEARCH_CONFIDENCE_THRESHOLD = 0.0
```

然后重新跑 DebugAgent + 图片检索，观察真正的图片检索结果。

明天要回答的问题：

```text
图片检索到底返回了哪些实体？
score 是多少？
这些实体属性能不能帮助回答问题？
为什么原来 0.75 阈值会过滤掉？
```

一句话总结今天：

```text
今天不是让系统变聪明，而是给系统装了一副“能看见内部输入”的眼镜。
```

## 12. 补充：`.venv-light` 里面都是什么

这个点今天应该记下来。

`.venv-light` 不是一个不能碰的神秘盒子，它就是这个项目自己的 Python 小房间。

路径：

```text
D:\CODE\Rainys-CRAG-MM\.venv-light
```

里面大概是：

```text
.venv-light
├── Include
├── Lib
├── Scripts
├── share
└── pyvenv.cfg
```

可以这样理解：

```text
Scripts = 工具箱
Lib = 书架
Lib\site-packages = 第三方书架
pyvenv.cfg = 这间小房间的身份证
Include = 给 C/C++ 扩展编译用的材料柜
share = 一些包的共享资源角落
```

最常用的是 `Scripts`：

```text
.venv-light\Scripts\python.exe
.venv-light\Scripts\pip.exe
.venv-light\Scripts\activate
```

所以激活虚拟环境：

```bat
.\.venv-light\Scripts\activate
```

本质就是：

```text
告诉当前 cmd：接下来优先使用 .venv-light\Scripts 里的 python 和 pip。
```

最重要的是 `Lib\site-packages`：

```text
D:\CODE\Rainys-CRAG-MM\.venv-light\Lib\site-packages
```

这里放的是 pip 安装的第三方包。

今天 Claude 修的文件就在：

```text
D:\CODE\Rainys-CRAG-MM\.venv-light\Lib\site-packages\cragmm_search\image_search_mock_api\image_search.py
```

也就是说：

```text
Claude 修的不是项目源码里的 Agent，
而是虚拟环境里 pip 安装的第三方搜索包。
```

`pyvenv.cfg` 是虚拟环境身份证。

当前内容大意：

```text
home = D:\Python3.10
version = 3.10.10
include-system-site-packages = false
```

翻译：

```text
这个小环境来自 D:\Python3.10；
Python 版本是 3.10.10；
不直接混用系统 Python 的第三方包。
```

最重要的提醒：

```text
如果删掉 .venv-light 再重建，里面 pip 装过的包会消失。
如果重装 cragmm-search-pipeline，今天 Claude 改过的第三方包补丁可能会被覆盖。
```
