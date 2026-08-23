# 大模型安全 + 多 Agent 全栈开发 — 6 个月学习与项目计划

> **起点：** 大二升大三，Python + C++，有 CRAG (RAG) 项目经验，无 Web 基础
> **目标：** 独立设计并实现 Sentinel — 多 Agent 大模型安全评测平台，完全掌握所需全部知识
> **时间：** 2025.8.1 — 2026.2.1（27 周，可用约 1062h）
> **职业方向：** 大模型安全

---

## 目录

1. [可用时间总览](#1-可用时间总览)
2. [学习路线图](#2-学习路线图)
3. [详细周计划](#3-详细周计划)
4. [项目里程碑：Sentinel 版本路线](#4-项目里程碑sentinel-版本路线)
5. [书单](#5-书单)
6. [学校课程协同](#6-学校课程协同)
7. [检验标准](#7-检验标准)

---

## 1. 可用时间总览

| 时间段 | 天数 | 学习强度 | 总时长 |
|--------|------|---------|--------|
| 8.1 — 9.14 | 45 天（暑假） | 8h/天 | 360h |
| 9.15 — 11.8 | 8 周（上课） | 25h/周 | 200h |
| 11.9 — 1.1 | 7.7 周 | 32h/周 | 246h |
| 1.2 — 2.1 | 31 天（寒假） | 8h/天 | 248h |
| 缓冲余量 | — | — | ~8h |
| **总计** | **27 周** | — | **≈ 1062h** |

---

## 2. 学习路线图

学习顺序经过重新排列：**LLM 原理放在暑假（大块时间啃最难的内容），Web 全栈放在开学后（碎片时间适合工程开发）。**

```
8月-9月中         9月中-10月中       10月中-11月上      11月上-12月        12月-1月           1月-2月
暑假 360h          上课 125h          上课 75h           上课+ 128h         上课+寒假 118h      寒假 248h
    │                  │                  │                  │                  │                  │
┌───▼──────────┐ ┌────▼──────────┐ ┌────▼──────────┐ ┌────▼──────────┐ ┌────▼──────────┐ ┌────▼──────────┐
│ AI/LLM 基础   │ │ Web 全栈地基   │ │ 安全攻击面     │ │ 多 Agent 扩展  │ │ 防御体系      │ │ 部署上线      │
│              │ │              │ │              │ │              │ │              │ │              │
│ ML 基础      │ │ HTTP/网络     │ │ Jailbreak    │ │ 5 Agent并行  │ │ Input Guard  │ │ Docker       │
│ 神经网络     │ │ FastAPI      │ │ Prompt Inj   │ │ 攻击面深化   │ │ Output Guard │ │ Railway/Vercel│
│ Attention   │ │ asyncio      │ │ Sentinel CLI │ │ 前端Dashboard│ │ Prompt硬化   │ │ 文档+复盘    │
│ Transformer │ │ SQL/数据库    │ │              │ │              │ │ RAG防御      │ │ 知识沉淀     │
│ GPT/RLHF    │ │ JS/React     │ │              │ │              │ │ OWASP/ATLAS  │ │              │
│ LLM 工程    │ │              │ │              │ │              │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
       7周              5周              3周              4周             3.5周             4.5周
```

### 三阶段螺旋递进

```
第一轮 (8-9月)：   LLM 原理 → 能解释 Token、Attention、RLHF
第二轮 (9-11月)：  Web 全栈 + 攻击面 → 能做出可用的安全评测工具
第三轮 (11-2月)：  多 Agent + 防御 + 部署 → 完整的线上产品 + 知识体系
```

---

## 3. 详细周计划

---

### 阶段一：AI / LLM 基础深度

> **时间：** 8.1 — 9.14（7 周，暑假，360h）
> **目标：** 从零建立 LLM 的完整认知——从反向传播到 RLHF，从 Attention 到 Agent。能够解释"为什么这个 Prompt 能绕过安全限制"的底层原因。

---

#### 第 1 周 | 8.1 — 8.7 | 56h | ML 基础 + 神经网络

| 知识点 | 内容 | 时间 |
|--------|------|------|
| 机器学习基本概念 | 监督学习 / 无监督学习 / 强化学习的区别、过拟合与欠拟合、训练集/验证集/测试集的划分逻辑 | 4h |
| 损失函数 | MSE、Cross-Entropy 的公式含义，为什么分类用 Cross-Entropy 而不是 MSE | 4h |
| 梯度下降 | 从直觉到数学——导数的方向含义、学习率的影响、SGD → Momentum → Adam 的演进逻辑 | 8h |
| 感知机 → 多层网络 | 单个神经元的计算 → 层叠 → 非线性激活的必要性 | 4h |
| 反向传播 | **完整手算一个 3 层网络的反向传播**——前向计算 → 链式法则 → 梯度更新 | 12h |
| 激活函数 | ReLU / Sigmoid / Tanh / GELU 各自的公式、优缺点、使用场景 | 4h |
| 优化器对比 | SGD vs Momentum vs Adam——直觉和关键差异 | 4h |
| NumPy 实战 | 纯 NumPy 实现一个可训练的 3 层 MLP | 16h |

**产出：** 纯 NumPy 手写 MLP，在 MNIST 上达到 90%+ 准确率

**对应书单：** 《动手学深度学习》第 1-4 章

---

#### 第 2 周 | 8.8 — 8.14 | 56h | NLP 基础 + Attention 起源

| 知识点 | 内容 | 时间 |
|--------|------|------|
| Tokenization 深入 | BPE 算法流程——从字符到子词的完整过程，亲手实现简化版 BPE | 10h |
| Word Embedding | Word2Vec 的直觉（Skip-gram / CBOW），自己训练一个小 Embedding 矩阵 | 6h |
| RNN/LSTM 回顾 | 为什么需要 Attention——RNN 的梯度消失和长距离依赖问题 | 4h |
| Seq2Seq | Encoder-Decoder 架构的设计动机和瓶颈（固定长度上下文向量） | 4h |
| Bahdanau Attention | 原始论文精读——Attention 的诞生：对齐分数、注意力权重、上下文向量的计算 | 8h |
| Scaled Dot-Product Attention | **纯 NumPy 实现**：Q·K^T → Scale → Softmax → ×V 的每一步 | 8h |
| 自回归生成 | 逐个 token 预测的完整流程：输入 → 概率分布 → 采样 → 拼接 → 重复 | 8h |
| 自由探索 | 用 HuggingFace 加载一个小模型，观察每层的 Attention 矩阵 | 8h |

**产出：** NumPy 版 Scaled Dot-Product Attention + 一篇笔记："Attention 到底在 Attend 什么"

**对应书单：** 《动手学深度学习》第 8-10 章；《Speech and Language Processing》第 9-10 章（Jurafsky & Martin，免费在线版）

---

#### 第 3 周 | 8.15 — 8.21 | 56h | Transformer 完整架构

| 知识点 | 内容 | 时间 |
|--------|------|------|
| Q/K/V 的物理含义 | 每个矩阵的维度（batch × heads × seq_len × d_k），Query 在"找什么"，Key 在"提供什么"，Value 在"输出什么" | 8h |
| Multi-Head Attention | 为什么多个头比一个好——不同头关注不同位置、不同语义关系 | 8h |
| Positional Encoding | Sinusoidal 编码的数学推导 → 为什么用 sin/cos → RoPE 的演进直觉 | 8h |
| Feed-Forward Network | 两层全连接 + GeLU——为什么 Transformer Block 里需要 FFN | 4h |
| LayerNorm | LayerNorm vs BatchNorm 的数学区别，Pre-norm vs Post-norm 的设计选择 | 4h |
| 残差连接 | 为什么是必须的——从梯度消失的角度理解 | 4h |
| Transformer Block 完整实现 | **NumPy 实现**：Multi-Head Attention + Add&Norm + FFN + Add&Norm | 12h |
| 三种架构对比 | Encoder-only (BERT) vs Decoder-only (GPT) vs Encoder-Decoder (T5) | 4h |
| 论文重读 | "Attention Is All You Need" 全文精读，对照代码理解每一段 | 4h |

**产出：** 一个可工作的 Transformer Block（NumPy 实现）+ 完整的计算图

**对应书单：** 《Build a Large Language Model》第 3 章；《神经网络与深度学习》第 6 章

---

#### 第 4 周 | 8.22 — 8.28 | 56h | GPT 系列 + 推理机制

| 知识点 | 内容 | 时间 |
|--------|------|------|
| GPT 发展史 | GPT-1（无监督预训练）→ GPT-2（Zero-shot，规模）→ GPT-3（In-Context Learning）→ GPT-4（多模态+推理），每次迭代解决了什么问题 | 8h |
| Decoder-only 推理过程 | Prefill 阶段（并行计算所有 token 的 KV Cache）→ Decode 阶段（逐个生成，只算新 token） | 8h |
| KV Cache 原理 | 为什么 Prefill 之后不需要重新算之前的 Key/Value、节省的计算量有多大 | 6h |
| 采样策略实验 | Temperature（平滑/锐化概率分布）、Top-k（截断低概率 token）、Top-p（核采样，累积概率阈值）、Repetition Penalty——**每个参数亲自调、看输出变化** | 8h |
| Context Window | 注意力矩阵的 O(n²) 复杂度、长上下文的挑战、RoPE 等位置编码如何扩展上下文 | 4h |
| Prompt Engineering 底层机制 | In-Context Learning 为什么有效（Induction Heads 假说）、Few-shot 示例如何影响 Attention 分布、**System Prompt 在多层 Attention 中如何被稀释——这是 Prompt Injection 的物理基础** | 6h |
| HuggingFace 实战 | 用 transformers 库加载 GPT-2，逐层 debug Attention 权重，可视化每个头的注意力分布 | 16h |

**产出：** 能画出 GPT 推理的完整计算图 + 解释每一步 + 写笔记："为什么 System Prompt 可以被覆盖"

**对应书单：** 《Build a Large Language Model》第 4-5 章

---

#### 第 5 周 | 8.29 — 9.4 | 56h | 训练流程全景

| 知识点 | 内容 | 时间 |
|--------|------|------|
| Pre-training | 数据来源与清洗、数据配比（代码/网页/书籍/学术论文）、自回归语言模型的目标函数、Scaling Law（参数量×数据量×计算量）的基本直觉 | 10h |
| SFT 指令微调 | 数据格式（instruction-input-output）、为什么需要指令微调而不仅是预训练、和 Pre-training 阶段的目标函数差异 | 8h |
| RLHF 完整推导 | Reward Model 的训练过程 → PPO 如何用 Reward Model 优化策略 → 为什么需要 KL 散度约束（防止模型偏离太远） | 10h |
| DPO 简化 | DPO 如何直接从偏好数据中学习而无需显式 Reward Model——配对数据的 loss 函数推导 | 6h |
| Reward Hacking | 模型"钻空子"获取高 Reward 但输出质量下降——案例分析和解决思路 | 4h |
| Alignment Tax | 安全性提升但有用性下降的 trade-off，"过度对齐"导致模型拒绝回答合理问题 | 4h |
| **为什么 RLHF 后仍可被攻击** | **对齐的本质是统计约束而非逻辑约束。Jailbreak 利用了 RLHF 训练数据的分布盲区——"你不可能在训练时见过所有对抗性输入"。** | 8h |
| RLAIF / Constitutional AI | 用 AI 反馈替代人工反馈，Constitutional AI 的自我改进循环 | 6h |

**产出：** 训练流程全景图 + 一篇笔记："Alignment 为什么不是一劳永逸"

**对应书单：** 《Build a Large Language Model》第 6-7 章；《The Alignment Problem》第 7-8 章

---

#### 第 6 周 | 9.5 — 9.11 | 56h | LLM 工程实践

> 这一周利用你在 CRAG 项目中的 RAG 经验，深化工程能力。

| 知识点 | 内容 | 时间 |
|--------|------|------|
| LLM SDK 深入 | Anthropic SDK + OpenAI SDK 的完整参数体系：max_tokens / temperature / top_p / top_k / stop_sequences / system prompt / streaming | 8h |
| Streaming 机制 | chunk 级别的数据结构、SSE 协议对接、首字延迟优化 | 4h |
| Function Calling | Tool Definition Schema 设计、模型如何"决定调用工具"、ReAct 循环（Think → Act → Observe → Think → ...） | 8h |
| Agent 架构模式对比 | Plan-Execute（先规划再执行）、ReAct（边想边做）、Multi-Agent Supervisor（分配任务给子 Agent）——各自的适用场景和失败模式 | 8h |
| RAG 进阶 | 基于 CRAG 经验深化：Chunking 策略深入（固定大小 vs 语义 vs 递归分割）、Hybrid Search（BM25 + 向量 + Rerank）、HyDE（假设性文档嵌入）、Self-RAG（自我反思检索）、GraphRAG 概念 | 16h |
| 结构化输出 | JSON Mode vs Function Calling 强制结构化；Pydantic 约束生成；结构化输出在评测中的可靠性 | 4h |
| Prompt 缓存 + Token 优化 | Anthropic Prompt Caching 原理、Token 计数、成本估算 | 4h |
| CRAG 复盘 | 把学到的原理套回 CRAG 项目——你的 RAG 为什么有效、哪些地方可以用新知识优化 | 4h |

**产出：** 一个 ReAct Agent 的最小实现 + CRAG 优化笔记

**对应书单：** Anthropic/OpenAI 官方文档；LangChain/LangGraph 官方 tutorial（仅参考架构思想）

---

#### 第 7 周 | 9.12 — 9.14 | 约 24h | 阶段一收尾 + 缓冲

| 活动 | 内容 | 时间 |
|------|------|------|
| 回顾补漏 | 第 1-6 周哪个知识点还没完全吃透——回补薄弱环节 | 16h |
| 阶段总结 | **写一篇长文："我理解的 LLM——从 Token 到 Agent"**（这篇文档是你面试时回答"你对 LLM 的理解"的弹药库） | 8h |

**产出：** 一篇完整的 LLM 知识总结

---

### 阶段二：Web 全栈地基

> **时间：** 9.15 — 10.19（5 周，上课模式 25h/周，125h）
> **目标：** 建立完整的 Web 全栈能力——从前端 UI 到后端 API 到数据库，独立搭建任何一个 AI 产品的骨架。

---

#### 第 8 周 | 9.15 — 9.21 | 25h | 网络基础 + FastAPI 启动

| 知识点 | 内容 | 时间 |
|--------|------|------|
| HTTP 协议 | 请求/响应模型、方法语义（GET vs POST 的幂等性和安全性）、状态码含义、**对着 Chrome DevTools Network 面板逐行解释** | 6h |
| HTTP Header | Content-Type / Accept / Authorization / Cache-Control / CORS 系列——每个 Header 存在的"设计理由" | 4h |
| DNS + URL + HTTPS | DNS 解析链路、URL 结构、TLS 握手过程、证书链验证 | 4h |
| FastAPI 路由 | 路径参数 / 查询参数 / 请求体 / Pydantic 验证 | 4h |
| FastAPI 中间件 + 异常 | 中间件的洋葱模型、全局异常处理器、startup/shutdown 生命周期 | 4h |
| HTML + TailwindCSS | 表单标签、语义化 HTML、TailwindCSS 实用优先写法 | 3h |

**产出：** 网页输入文字 → POST 到 FastAPI → 返回 JSON → 显示在页面

**对应书单：** 《图解 HTTP》第 1-6 章

---

#### 第 9 周 | 9.22 — 9.28 | 25h | asyncio 核心

| 知识点 | 内容 | 时间 |
|--------|------|------|
| 事件循环模型 | 事件循环的运行机制、**coroutine / Future / Task 三者是什么关系**、await 到底挂起了什么 | 8h |
| 并发操作 | `gather` vs `create_task` vs `TaskGroup`——各自的使用场景和错误处理差异 | 6h |
| 生产者-消费者 | `asyncio.Queue` 做任务队列、`Semaphore` 做并发限流、超时控制（`asyncio.wait_for` + `asyncio.timeout`） | 6h |
| 错误与调试 | 竞态条件的识别与修复、取消传播（`CancelledError`）、asyncio 调试模式的输出解读 | 5h |

**产出：** 3 个异步任务并发执行 → 结果流式 SSE 推送到前端 → 前端逐字显示

**对应书单：** 《Using Asyncio in Python》第 1-5 章

---

#### 第 10 周 | 9.29 — 10.5 | 25h | 数据库 + 认证 + 测试

| 知识点 | 内容 | 时间 |
|--------|------|------|
| SQL 基础 | SELECT / JOIN / GROUP BY / 子查询——裸写 SQL，不靠 ORM 生成 | 8h |
| 表设计与范式 | 1NF/2NF/3NF 的直觉、什么时候反范式、索引的类型和何时使用 | 3h |
| SQLAlchemy 2.0 | ORM vs Core、async session 管理、关系映射、Alembic 迁移 | 3h |
| JWT 认证 | Token 结构（header.payload.signature）、无状态 vs 有状态认证的取舍、Refresh Token 策略 | 8h |
| pytest 测试 | fixture、mock、FastAPI TestClient、什么该测什么不该测 | 3h |

**产出：** 带认证的完整 API + SQLite 持久化 + 测试覆盖

**对应书单：** 《SQL 必知必会》前 18 课

---

#### 第 11 周 | 10.6 — 10.12 | 25h | JavaScript 核心

| 知识点 | 内容 | 时间 |
|--------|------|------|
| JS 事件循环 | 和 Python asyncio 对比理解——调用栈 / 宏任务 / 微任务 / requestAnimationFrame | 6h |
| 闭包 | 闭包的底层原因（作用域链 + 垃圾回收）、在 React hooks 中的应用 | 4h |
| Promise 与异步 | Promise 链、async/await、错误传播、Promise.all / allSettled / race | 4h |
| DOM 操作 | 不依赖框架——查找 / 创建 / 修改 / 删除元素、事件委托、表单数据获取 | 4h |
| fetch + SSE | fetch 的请求/响应处理、EventSource API、断线重连策略、流式渲染 | 4h |
| TailwindCSS 实战 | 做一个完整的数据看板页面 | 3h |

**产出：** 纯 JS + Tailwind 的实时数据面板

**对应书单：** 《JavaScript 高级程序设计》第 4 版，第 4-8 章、第 11 章（Promise）、第 14 章（DOM）

---

#### 第 12 周 | 10.13 — 10.19 | 25h | React 组件化

| 知识点 | 内容 | 时间 |
|--------|------|------|
| JSX 与组件 | JSX 的本质是 `React.createElement` 的语法糖、函数组件、Props 单向数据流、key 的作用（diff 算法相关） | 6h |
| 状态管理 | `useState` vs `useReducer` 的选择依据、状态提升（lifting state up）、受控 vs 非受控组件 | 4h |
| 副作用 | `useEffect` 的执行时机、依赖数组、cleanup 函数、与 React StrictMode 的交互、常见反模式 | 4h |
| Context + useRef | Context 的适用场景与性能陷阱、useRef 的正确用途（不是"存放变量"而是"跨渲染保持引用"） | 4h |
| 自定义 Hook | Hook 的命名和封装原则——把 `useSSE`、`useDebate` 抽成可复用 Hook | 4h |
| 实战 | 把之前原生 HTML 页面完整迁移到 React | 3h |

**产出：** React 版 AI 对话界面

**对应书单：** 《React 设计原理》第 1-6 章

---

### 阶段三：安全攻击面 + Sentinel 启动

> **时间：** 10.20 — 11.8（3 周，上课模式 25h/周，75h）
> **目标：** 深入理解 LLM 攻击面，启动 Sentinel 项目，实现 CLI 版安全评测。

---

#### 第 13 周 | 10.20 — 10.26 | 25h | 攻击理论 + 攻击模板

| 知识点 | 内容 | 时间 |
|--------|------|------|
| Competing Objectives 理论 | 模型被训练为"尊重用户指令"和"遵守安全规则"，当这两者冲突时攻击产生——这是所有 Jailbreak 的理论基础 | 4h |
| Jailbreak 分类学 | 角色扮演类（DAN 及变体）、编码绕过类（Base64/ROT13/莫尔斯码）、多轮 Crescendo（渐进式越狱）、多语言绕过（低资源语言安全对齐缺失）、token 拼接绕过 | 10h |
| 动手写攻击 | 自己写 20+ 条攻击变体——对 Claude / GPT / Gemini 分别实测，记录每个模型的差异和弱点 | 8h |
| LLM-as-a-Judge | Judge Agent 的评分标准设计（语义一致性/安全性/忠实性/帮助性）、常见偏差（位置偏差/长度偏差） | 3h |

**产出：** 攻击模板 YAML 库（30+ 条）+ Judge 评分系统 + 实测记录

**参考资料：** Lakera 安全知识库 (lakera.ai/blog)、Simon Willison Prompt Injection 系列、Anthropic 安全研究博客、OWASP LLM Top 10

---

#### 第 14 周 | 10.27 — 11.2 | 25h | Sentinel v0.1 — CLI 原型

| 知识点 | 内容 | 时间 |
|--------|------|------|
| Agent 基类设计 | Pydantic 定义 Agent 协议（输入/输出/状态/错误）、攻击 Agent 的通用接口 | 8h |
| Jailbreak Agent | 攻击模板加载 → 变量替换 → LLM 调用 → 结果解析 → 返回结构化结果 | 6h |
| CLI 编排器 | 单 Agent → 逐个跑攻击模板 → Judge 打分 → 汇总为评测报告 | 6h |
| 多模型实测 | 对 Claude / GPT / Gemini 分别跑一遍完整评测，记录每个模型的攻击成功率（ASR）和保护弱点 | 5h |

**产出：** Sentinel v0.1 — CLI 版越狱评测工具，支持单个模型的完整安全评测

---

#### 第 15 周 | 11.3 — 11.8 | 25h | Prompt Injection + 双 Agent 并行

| 知识点 | 内容 | 时间 |
|--------|------|------|
| Prompt Injection 理论 | Data-Plane vs Control-Plane 混淆——为什么模型无法可靠区分"指令"和"数据"；直接注入 vs 间接注入（检索投毒/邮件注入/网页注入） | 6h |
| Injection Agent 实现 | 参考 Prompt Injection 经典攻击手法，实现第二个攻击 Agent | 5h |
| 双 Agent 并行 | asyncio.Queue 任务池 + Semaphore 限流 → Jailbreak Agent 和 Injection Agent 同时执行 | 6h |
| SSE 多通道推送 | 后端两个 Agent 的执行进度 → SSE 多通道 → 前端分别显示 | 4h |
| 前端基础 | 用已有的 React 基础做一个简单的评估管理页面 | 4h |

**产出：** Sentinel v0.2 — 2 个攻击 Agent 并行 + Web 界面

---

### 阶段四：多 Agent 扩展 + 攻击面深化

> **时间：** 11.9 — 12.7（4 周，32h/周，128h）
> **目标：** 攻击 Agent 扩展到 5 个，实现完整的多 Agent 并行编排和前端 Dashboard。

---

#### 第 16 周 | 11.9 — 11.15 | 32h | 攻击面完整扩展

| 知识点 | 内容 | 时间 |
|--------|------|------|
| Training Data Extraction | 模型记忆 vs 泛化的边界、差分隐私的基本概念、Membership Inference Attack 原理、Canary 测试设计（"我的密码是 hunter2"） | 8h |
| 数据提取 Agent | 实现训练数据泄露检测 Agent | 6h |
| Tool Manipulation | Function Calling 中的参数注入、MCP 工具投毒、工具输出不可信问题 | 8h |
| 工具安全 Agent | 实现工具调用安全检测 Agent | 4h |
| Multi-Agent 间攻击 | Agent-to-Agent 间接攻击、记忆系统投毒、跨会话状态污染、权限漂移 | 6h |

**产出：** 5 个攻击 Agent：Jailbreak / Prompt Injection / Data Extraction / Tool Manipulation / Multi-Agent Attack。攻击模板库扩展至 50+ 条。

---

#### 第 17 周 | 11.16 — 11.22 | 32h | 多 Agent 编排完善

| 知识点 | 内容 | 时间 |
|--------|------|------|
| 5 Agent 并行调度 | asyncio.Queue 任务池管理 5 个 Agent、Semaphore 限流控制并发数 | 8h |
| 结果聚合 | 多个 Agent 的攻击结果去重、交叉验证（同一漏洞被多个 Agent 发现 → 置信度更高） | 4h |
| 错误处理 | Agent 超时 → 取消 → 重试（指数退避）、取消传播的完整链路、资源（API 连接/SQLite 连接）的正确释放 | 8h |
| 评测历史 | 数据库 Schema 设计（评测记录/攻击结果/评分/模型信息）、历史查询接口 | 8h |
| 性能优化 | 连接池管理、批量 API 调用、结果缓存 | 4h |

**产出：** Sentinel v0.5 — 5 个 Agent 并行稳定运行 + 评测历史持久化

---

#### 第 18 周 | 11.23 — 11.29 | 32h | 前端 Dashboard

| 知识点 | 内容 | 时间 |
|--------|------|------|
| 多通道 SSE | React 端消费 5 个 Agent 的 SSE 流 → 实时显示每个 Agent 的当前进度和输出 | 10h |
| 攻击结果卡片 | 每个漏洞的卡片展示（攻击类型/严重级别/攻击文本/模型响应/Judge 评分） | 4h |
| 安全评分雷达图 | Recharts 实现雷达图（5 个安全维度：越狱抵抗力/注入抵抗力/数据保护/工具安全/Agent 安全） | 4h |
| 评测历史 | 评测历史列表 + 详情页 + 筛选（按时间/模型/攻击类型） | 6h |
| 加载态与过渡 | 骨架屏、进度条、Agent 状态动画 | 4h |
| react-markdown | 报告内容渲染（攻击响应中可能包含 Markdown 格式） | 4h |

**产出：** Sentinel v0.6 — 完整前端 Dashboard

---

#### 第 19 周 | 11.30 — 12.6 | 32h | React 进阶 + 报告导出

| 知识点 | 内容 | 时间 |
|--------|------|------|
| 性能优化 | `memo` / `useMemo` / `useCallback` 的正确使用——什么时候需要、什么时候是过度优化 | 8h |
| 自定义 Hook 抽取 | `useAgentStream`（SSE 封装）、`useEvaluation`（评测状态管理）、`useHistory`（历史查询） | 8h |
| 响应式布局 | 桌面端三栏布局 / 平板端两栏 / 手机端单栏——用 TailwindCSS 实现 | 8h |
| PDF 报告 | 用 jsPDF 或浏览器 print 方案生成含图表的 PDF 安全报告 | 8h |

**产出：** Sentinel v0.7 — 生产级前端体验（响应式 + PDF 导出）

---

### 阶段五：防御体系 + 产品化

> **时间：** 12.8 — 1.1（3.5 周，约 118h）
> **目标：** 从"攻击平台"升级为"攻防一体的安全评测平台"。学习并实现大模型安全防御体系。

---

#### 第 20 周 | 12.8 — 12.14 | 32h | Guard 体系实现

| 知识点 | 内容 | 时间 |
|--------|------|------|
| Input Guard 设计 | 输入净化（正则过滤/敏感词替换）、意图分类（安全 vs 不安全请求）、PII 检测（邮箱/电话/身份证号正则）、Regex vs LLM 分类的延迟 vs 准确率权衡 | 10h |
| Output Guard 设计 | 输出内容审核（关键词匹配 + LLM 二次审核）、事实性校验（检索验证）、PII 脱敏（替换/遮盖）、Refusal 检测（模型是否正常拒绝） | 10h |
| Guard 性能评估 | 延迟增加（Guard 引入的额外耗时）、准确率/误拒率（FRR）/漏过率（FNR）、A/B 测试设计 | 6h |
| 攻防一体 | 被评测模型启用 Guard → 重新跑攻击套件 → 对比启用前后的 ASR 变化 | 6h |

**产出：** Input Guard + Output Guard 模块完整实现 + 攻防一体评测闭环

---

#### 第 21 周 | 12.15 — 12.21 | 32h | 防御深入 + 安全标准

| 知识点 | 内容 | 时间 |
|--------|------|------|
| System Prompt 硬化 | Instruction Hierarchy（指令优先级声明）、分隔符选择（XML/Markdown/自定义）、Self-Reminder 技术、Defense-in-Depth 多层提示设计——亲手实验每种技术的效果 | 8h |
| RAG 防御 | 检索结果净化（过滤低质量/对抗性内容）、来源验证（URL/域名白名单）、Chunk 污染抵抗（如何防止攻击者通过网页内容注入）、引用溯源（每个输出关联到具体来源） | 8h |
| 护栏框架对比 | NeMo Guardrails / Guardrails AI / LLM-as-a-Guard——各自的架构、延迟特征、准确率差异 | 8h |
| OWASP LLM Top 10 | LLM01-LM10 每条风险的名称、含义、攻击案例、防护建议——能用自己的话讲出来 | 4h |
| MITRE ATLAS | ATLAS 矩阵的结构、和 MITRE ATT&CK 的关系、ATLAS 在 AI 安全评测中的应用 | 4h |

**产出：** 完整的防御体系 + OWASP/MITRE 标准映射到 Sentinel

---

#### 第 22 周 | 12.22 — 12.28 | 32h | 评测方法论 + Sentinel 完善

| 知识点 | 内容 | 时间 |
|--------|------|------|
| 评测指标 | ASR（Attack Success Rate）的严格定义、FPR/FRR（误报率/误拒率）、多维度评分（安全性/有用性/忠实性/鲁棒性） | 4h |
| 评测偏差 | 位置偏差（Judge 倾向于第一个/最后一个回答）、长度偏差（更长的回答得分更高）、风格偏差（更"学术"的回答得分更高）——校准方法 | 4h |
| 多模型横向对比 | 同时评测 Claude/GPT/Gemini/开源模型 → 雷达图对比 → 趋势分析 | 8h |
| 安全评分趋势 | 同一模型的多次评测 → 安全分数变化趋势 → 检测模型的"安全退化" | 4h |
| 攻击模板版本管理 | 模板的版本号/更新日期/攻击类型/测试记录——方便追踪和社区贡献 | 4h |
| 代码重构 + 测试 | 全系统重构不合理的地方 + 补充集成测试 | 8h |

**产出：** Sentinel v0.85 — 完整的评测 + 防御系统 + 多模型对比

---

#### 第 23 周 | 12.29 — 1.1 | 22h | 年末冲刺

| 活动 | 内容 | 时间 |
|------|------|------|
| 性能优化 | 数据库连接池调优、API 结果缓存（Redis 或内存 LRU）、大评测任务的批量处理 | 10h |
| 日志与错误处理 | 结构化日志（时间/级别/Agent/消息）、全局异常捕获、用户友好的错误提示 | 8h |
| 边缘情况修复 | 空输入/超大输入/特殊字符/并发冲突——各种异常输入的防御性处理 | 4h |

**产出：** Sentinel v0.9 — 接近生产级质量

---

### 阶段六：部署上线 + 知识沉淀

> **时间：** 1.2 — 2.1（4.5 周，寒假，248h）
> **目标：** 将 Sentinel 部署为线上可访问的完整产品，沉淀知识体系，准备面试弹药。

---

#### 第 24 周 | 1.2 — 1.8 | 56h | Docker + 线上部署

| 知识点 | 内容 | 时间 |
|--------|------|------|
| Docker 核心概念 | Image / Layer / Container / Volume / Network——每个概念的含义和关系 | 8h |
| 容器化实践 | 编写 Dockerfile（FastAPI 后端 + React 前端）、docker-compose 编排多服务、多阶段构建（builder stage + runtime stage）优化镜像大小 | 12h |
| 后端部署 | Railway / Render 部署 FastAPI——环境变量管理、健康检查、自动重启 | 8h |
| 前端部署 | Vercel 部署 React 前端——构建配置、环境变量、API 地址注入 | 6h |
| HTTPS + CORS | 证书配置、跨域策略、安全 Headers | 6h |
| 线上测试 | 全功能测试 + Bug 修复 | 16h |

**产出：** Sentinel v1.0 — 线上可访问的完整产品 🎉

**对应书单：** 《设计数据密集型应用》第 3/5/7 章（部署前理解数据层）

---

#### 第 25 周 | 1.9 — 1.15 | 56h | 文档化 + 开源准备

| 活动 | 内容 | 时间 |
|------|------|------|
| README | 项目介绍 / 功能列表 / 架构图（ASCII art 或 Excalidraw） / 快速开始（一键 Docker 启动）/ API 文档 | 12h |
| 技术文档 | 攻击模板库文档（每条攻击的原理和用法）、防御策略库文档（每种防御的配置和效果） | 12h |
| 开源规范 | CONTRIBUTING.md、LICENSE（Apache 2.0 或 MIT）、Issue Templates | 4h |
| Demo 视频 | 录制 3-5 分钟的演示视频：对一个模型做完整评测 → 展示报告 → 启用防御 → 重新评测对比 | 8h |
| 代码规范 | 最终代码审查——变量命名/注释/类型提示/pylint 通过 | 8h |
| 发布博客 | 写一篇技术博客："我如何用 5 个 Agent 构建 LLM 安全评测平台" | 12h |

**产出：** Sentinel v1.1 — 开源就绪 + 一篇发布博客

---

#### 第 26 周 | 1.16 — 1.22 | 56h | 知识体系沉淀

| 活动 | 内容 | 时间 |
|------|------|------|
| 知识模块总结 | 9 个模块各写一篇技术笔记（每篇 2-3h，共 ~24h）：<br>1. 神经网络与深度学习基础<br>2. Transformer 架构详解<br>3. GPT 系列与自回归生成<br>4. LLM 训练流程（Pre-training → SFT → RLHF）<br>5. LLM 工程实践（RAG / Agent / Function Calling）<br>6. 大模型攻击面（Jailbreak / Prompt Injection / Data Extraction / Tool Manipulation）<br>7. 大模型防御体系（Guard / Prompt 硬化 / RAG 防御）<br>8. 安全评测方法论（ASR / ASR / OWASP / MITRE ATLAS / LLM-as-a-Judge）<br>9. Web 全栈开发心得 | 24h |
| 踩坑记录 | 项目中遇到的 20 个最深的坑 + 怎么解决的（每个坑 20-30 分钟写清楚） | 8h |
| 演讲练习 | 给假想的同年级同学讲一遍整个系统（录音→回听→改进） | 8h |
| 面试 STAR 话术 | 针对"介绍一下你的项目"、"遇到最大的技术难点"、"为什么这样设计"准备 STAR 法话术 | 8h |
| 查漏补缺 | 哪个模块还不能独立讲清楚 → 回补 | 8h |

**产出：** 一套完整的技术文档（9 篇）+ 面试弹药库

---

#### 第 27 周 | 1.23 — 2.1 | 56h | 全面复盘 + 后期规划 + 休息

| 活动 | 内容 | 时间 |
|------|------|------|
| 全系统走查 | 从用户输入话题 → 多 Agent 执行 → 报告生成 → 前端展示，逐行代码过一遍，确保每一行都能解释 | 16h |
| v2.0 Roadmap | 列出未完成的功能和优化方向（如：开源模型本地评测、CI/CD 自动评测、社区攻击模板市场） | 4h |
| 研究方向规划 | 基于 Sentinel 的积累，思考研一可以做哪些研究——Jailbreak 防御的论文方向、评测标准的改进、Multi-Agent 攻击的建模 | 8h |
| 休息 | **你值得。600+ 小时的持续学习，给自己几天彻底放松。** | 28h |

**最终产出：** 你 = Sentinel 的唯一作者 + 每一行代码都知道为什么 + 面试时能侃侃而谈 1 小时

---

## 4. 项目里程碑：Sentinel 版本路线

| 版本 | 时间 | Agent 数 | 关键能力 | 界面 |
|------|------|---------|---------|------|
| **v0.1** | 第 14 周 (10月底) | 1 | Jailbreak 攻击 + Judge 评分 | CLI |
| **v0.2** | 第 15 周 (11月初) | 2 | 越狱 + 注入，双 Agent 并行 | Web 基础 |
| **v0.5** | 第 17 周 (11月中) | 5 | 全攻击 Agent 并行 + 评测历史 | Dashboard |
| **v0.7** | 第 19 周 (12月初) | 5 | 前端完善 + PDF 报告 + 响应式 | 完整前端 |
| **v0.85** | 第 22 周 (12月底) | 5 | 攻防一体 + OWASP 映射 + 多模型对比 | 完整平台 |
| **v0.9** | 第 23 周 (1月初) | 5 | 性能优化 + 日志 + 错误处理 | 接近生产级 |
| **v1.0** | 第 24 周 (1月中) | 5 | Docker 化 + 线上部署 | 线上可访问 🎉 |
| **v1.1** | 第 25 周 (1月底) | 5 | 文档 + 开源就绪 | 开源 |

---

## 5. 书单

### 必读（从头到尾精读）

| #   | 书名                                                | 作者                | 出版社             | 覆盖板块                            | 什么时候读   | 为什么是这本                                                                                             |
| --- | ------------------------------------------------- | ----------------- | --------------- | ------------------------------- | ------- | -------------------------------------------------------------------------------------------------- |
| 1   | **《动手学深度学习》** (Dive into Deep Learning)           | 李沐 等              | 人民邮电出版社 / 免费在线版 | ML 基础 + Attention + Transformer | 第 1-3 周 | 代码 + 数学 + 图解三者合一。每章有可运行的 Jupyter Notebook，学完就能写。免费在线版在 d2l.ai                                      |
| 2   | **《Build a Large Language Model (From Scratch)》** | Sebastian Raschka | Manning (2025)  | LLM 完整构建流程                      | 第 3-5 周 | 2025 年最好的 LLM 入门书。从 Tokenization 到 Pre-training 到 SFT 到 RLHF，每一步都带着你写代码。读完你自然就理解"为什么 Prompt 可以被注入" |
| 3   | **《Using Asyncio in Python》**                     | Caleb Hattingh    | O'Reilly (2020) | Python asyncio                  | 第 9 周   | 市面上唯一一本把 Python asyncio 讲透的书。从事件循环的内部机制到 Queue/Semaphore 的正确用法，每个例子都能跑                             |
| 4   | **《React 设计原理》**                                  | 卡颂                | 电子工业出版社 (2024)  | React 核心                        | 第 12 周  | 不讲 API，讲 React 为什么这样设计——JSX 的本质、Fiber 架构、Hooks 的运行机制、Diff 算法。理解原理后 API 自然就会用                       |

### 精读部分章节（不是通读全书）

| # | 书名 | 作者 | 出版社 | 重点读哪些章 | 什么时候读 |
|---|------|------|--------|------------|-----------|
| 5 | **《图解 HTTP》** | 上野宣 | 人民邮电出版社 | 第 1-6 章（HTTP 报文/状态码/Header/HTTPS）、第 9 章（HTTP/2.0） | 第 8 周 |
| 6 | **《SQL 必知必会》** | Ben Forta | 人民邮电出版社 | 前 18 课（SELECT → JOIN → 子查询 → 索引） | 第 10 周 |
| 7 | **《JavaScript 高级程序设计》** | Matt Frisbie | 人民邮电出版社 | 第 4-8 章（变量/引用类型/集合）、第 10-11 章（函数/Promise）、第 14 章（DOM）、第 16 章（事件） | 第 11 周 |
| 8 | **《神经网络与深度学习》** | 邱锡鹏 | 机械工业出版社 | 第 1-6 章（ML 基础 → 前馈网络 → CNN → RNN → Attention → Transformer） | 第 2-3 周 |
| 9 | **《设计数据密集型应用》** (DDIA) | Martin Kleppmann | 中国电力出版社 | 第 3 章（存储引擎）、第 5 章（复制）、第 7 章（事务） | 第 24 周 |

### 参考与扩展

| # | 书名/资源 | 作者 | 什么时候用 |
|---|----------|------|-----------|
| 10 | **《The Alignment Problem》** | Brian Christian | 第 5 周 RLHF 学习时的哲学背景补充，以及贯穿全计划的睡前读物 |
| 11 | **《Speech and Language Processing》** 第 3 版 | Jurafsky & Martin | 需要深入 NLP 某个话题时查。免费在线版：[web.stanford.edu/~jurafsky/slp3/](https://web.stanford.edu/~jurafsky/slp3/) |
| 12 | **OWASP LLM Top 10** | OWASP 社区 | 第 21 周系统学习 AI 安全标准：[owasp.org/www-project-top-10-for-large-language-model-applications/](https://owasp.org/www-project-top-10-for-large-language-model-applications/) |
| 13 | **MITRE ATLAS** | MITRE | 第 21 周：[atlas.mitre.org](https://atlas.mitre.org/) |
| 14 | **Lakera 安全知识库** | Lakera | 第 13-15 周攻击面学习时持续参考：[lakera.ai/blog](https://www.lakera.ai/blog) |
| 15 | **Simon Willison 博客** | Simon Willison | Prompt Injection 系列是领域内最好的实战参考 |
| 16 | **Anthropic 安全研究博客** | Anthropic | 第 13 周起持续关注：Alignment / Jailbreak / Constitutional AI 的官方研究 |
| 17 | **Andrej Karpathy "Let's build GPT from scratch"** | Karpathy | 第 4 周，作为《Build a Large Language Model》的视频版补充 |
| 18 | **3Blue1Brown 神经网络系列** | Grant Sanderson | 第 1 周，反向传播的直觉建立：YouTube 搜索 "3Blue1Brown neural networks" |

### 书单时间线

```
8月第1周      《动手学深度学习》第1-4章
8月第2周      《动手学深度学习》第8-10章 + 《神经网络与深度学习》第6章
8月第3周      《Build a Large Language Model》第3章
8月第4周      《Build a Large Language Model》第4-5章
8月第5周      《Build a Large Language Model》第6-7章 + 《The Alignment Problem》第7-8章
9月           《图解 HTTP》+ 《Using Asyncio in Python》+ 《SQL必知必会》
10月          《JavaScript 高级程序设计》+ 《React 设计原理》
11月-2月      Lakera / Simon Willison / Anthropic 安全博客持续关注
1月           《设计数据密集型应用》部分章节
```

---

## 6. 学校课程协同

你的下学期专业课和本计划高度互补：

| 课程 | 覆盖计划的哪些内容 | 省下的自学时间 |
|------|-------------------|-------------|
| **计算机网络** | OSI 七层模型、TCP/IP 协议栈、HTTP 底层实现、DNS 解析、TLS 握手——这些课上就学，你只需额外聚焦 HTTP 应用层（Header/CORS/SSE） | ~25h |
| **操作系统** | 进程/线程模型、CPU 调度算法、内存管理（虚拟内存/分页）、文件系统——帮助你对比理解 asyncio 事件循环 vs OS 线程调度、数据库为什么需要 Buffer Pool | ~20h |
| **软件工程** | 设计模式、Git 工作流、CI/CD、测试方法论、文档规范——直接套用到 Sentinel 项目的工程实践 | ~15h |

三门课共节省约 60h，自动转化为计划的缓冲余量。

---

## 7. 检验标准

每个阶段结束时，回答以下问题。如果任何一个答不上来，回补。

### 阶段一结束（9.14）

- [ ] 能画出 Transformer 的完整计算图，标注 Q/K/V 的矩阵维度
- [ ] 能解释为什么 Multi-Head Attention 比 Single-Head 好
- [ ] 能手算一个 3 层 MLP 的反向传播
- [ ] 能解释 "GPT 生成一个 token 时，哪些计算是必须的，哪些（KV Cache）是缓存"
- [ ] 能解释 RLHF 三阶段各自在做什么、为什么 DPO 比 RLHF 更简单
- [ ] 能解释"为什么 RLHF 训练后的模型仍然可以被 Jailbreak"

### 阶段二结束（10.19）

- [ ] 打开 Chrome DevTools Network 面板，能解释每个请求的完整链路
- [ ] 能独立设计一个 5 张表的数据库 Schema
- [ ] 能写出一个带 JWT 认证的 FastAPI 后端
- [ ] 能解释 asyncio 事件循环和 JS 事件循环的关键区别
- [ ] 能独立用 React + TailwindCSS 做一个数据看板页面
- [ ] 能消费 SSE 流式输出并实时渲染到页面

### 阶段三结束（11.8）

- [ ] 能解释 Competing Objectives 理论
- [ ] 能手写 5 种不同类型的 Jailbreak 变体
- [ ] 能解释 Direct Prompt Injection 和 Indirect Prompt Injection 的区别
- [ ] 能让 Sentinel CLI 对一个模型完成完整评测并输出结构化报告

### 阶段四结束（12.7）

- [ ] 5 个攻击 Agent 能稳定并行运行
- [ ] 如果一个 Agent 超时，其他 Agent 是否被正确处理
- [ ] 前端 Dashboard 能实时显示每个 Agent 的执行进度
- [ ] 能解释每个攻击 Agent 利用了 LLM 的哪个底层特性

### 阶段五结束（1.1）

- [ ] 能解释 Input Guard 和 Output Guard 的各自职责
- [ ] 能说出 Regex Guard 和 LLM-as-Guard 的延迟/准确率 trade-off
- [ ] 能用自己的话讲出 OWASP LLM Top 10 的每一条
- [ ] 被评测模型启用 Guard 后，ASR 下降了多少、为什么

### 阶段六结束（2.1）

- [ ] Sentinel 线上可访问
- [ ] 完整的 README + API 文档 + 架构图
- [ ] 能给一个同年级同学讲一遍整个系统，让他听懂
- [ ] 能回答："你为什么这样设计 Agent 编排？""为什么不直接用 LangChain？""你项目的最大技术挑战是什么？"

---

## 附录：快速参考

### 技术栈总览

| 层 | 选型 |
|----|------|
| **前端** | React + Vite + TypeScript + TailwindCSS + Recharts |
| **后端** | Python 3.12+ / FastAPI / asyncio / Pydantic v2 |
| **AI** | Anthropic SDK (Claude) / OpenAI SDK (GPT) |
| **数据库** | SQLite (开发) → PostgreSQL (生产) + SQLAlchemy 2.0 |
| **部署** | Docker + Railway (后端) + Vercel (前端) |
| **测试** | pytest + FastAPI TestClient |

### 关键时间节点

| 日期 | 里程碑 |
|------|--------|
| 8.1 | 开始学习——反向传播手算 |
| 8.24 | 阶段一过半——Transformer 能写出来了 |
| 9.7 | 阶段一完成——RLHF/DPO 理解了 |
| 9.15 | 开始学 Web 全栈 |
| 10.20 | 开始学安全攻击面 + Sentinel 启动 |
| 10.31 | Sentinel v0.1（第一个可运行的 CLI 评测） |
| 11.9 | 进入 32h/周节奏 |
| 11.30 | Sentinel v0.6（5 Agent + Dashboard） |
| 12.22 | Sentinel v0.85（攻防一体 + OWASP 映射） |
| 1.8 | Sentinel v1.0 上线 🎉 |
| 1.15 | 开源 + 发布博客 |
| 1.25 | 知识体系沉淀完成 |
| 2.1 | 全面复盘完成——你准备好面试了 |
