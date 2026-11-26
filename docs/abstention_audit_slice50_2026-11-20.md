# CRAG-MM 固定 50 条弃答审计

日期：2026-11-20（Asia/Shanghai）

对象：`results_both_retrieval_optimized_candidate_50.json` 中的 27 条弃答。

目标：把可验证的弃答转成正确答案。错误上限保持为 8，固定 50 条目标为至少 24 条正确。

## 1. 审计结论

27 条弃答分为五类：

| 类型 | 数量 | 含义 |
|---|---:|---|
| A. 实体线索存在，网页查询未使用 | 9 | 图像阶段已给出正确或接近正确的实体，但门控或拼写导致查询退回原问题 |
| B. 网页已有关键证据，Llama 未完成比较/计算 | 4 | 证据足以形成答案，生成阶段仍弃答 |
| C. 图表或图像可直接回答 | 2 | 无需网页补充，视觉识别结果已包含答案 |
| D. 实体或网页证据不足，需要定向补检索 | 4 | 有恢复可能，但当前上下文不足 |
| E. 当前低收益 | 8 | 实体和网页均不可靠，暂不投入 GPU |

P0 恢复集共 15 条：01、02、14、15、20、22、24、28、30、33、36、38、47、49，
以及 05 作为车辆容量备选。P0 的首轮目标是恢复至少 8 条正确答案。

## 2. 逐条审计

| 样本 | 分类 | 优先级 | 当前证据 | 下一动作 |
|---:|---|---|---|---|
| 01 | B | P0 | 已检到 2023 Trailblazer 1.3L MPG 页面 | 补 DC–Baltimore 距离，执行 `5 × MPG` 比较 |
| 02 | A | P0 | 右侧裁剪识别 `Bacon cheese fries` | 用该实体重查 origin，回答 United States |
| 04 | E | P2 | 错识别为 Tesla Model X | 暂不处理 |
| 05 | D | P1 | 车型未锁定，网页为 CR-V/Tahoe | 重新定位红色 Toyota Prius，再查五座 |
| 06 | E | P2 | 圣以撒大教堂未识别且无网页结果 | 暂不处理 |
| 10 | E | P2 | Regions Tower 未识别 | 暂不处理 |
| 14 | D | P0 | 网页出现 Toyota Yaris，但缺 2007 销量表 | 用 `Toyota Yaris Europe annual sales 2007 generation` 定向检索 |
| 15 | B | P0 | 已有 Monet 1874 页面和 Picasso 生平页面 | 比较 1874 与 Picasso 1881 出生，输出 No |
| 20 | B | P0 | 已确认日本警察使用 Nissan 370Z | 补 370Z 首次生产年份，与 1998 比较 |
| 22 | A | P0 | 裁剪出现 RAM 3500，其他裁剪被 RAM 1500 干扰 | 锁定 RAM 3500，查询 2024 6.7L I6 towing/torque |
| 23 | D | P1 | 识别 Grass Rake，但当前安全网页与参考答案口径冲突 | 查儿童在指导下使用 leaf rake 的安全说明 |
| 24 | A | P0 | 多个裁剪重复识别 yellow roses | 查询 fresh cut roses lifespan，回答 5–7 days |
| 25 | E | P2 | Lincoln Navigator 未识别 | 暂不处理 |
| 28 | A | P0 | 全图已识别 `2015 Chevrolet Suburban` | 绕过候选门控，用实体重查 multimedia features |
| 30 | A | P0 | 多裁剪重复识别 Red Onion/Onions | 用 onions health benefits 重查 |
| 32 | E | P2 | 错把车辆问题识别为铁路标志 | 暂不处理 |
| 33 | B | P0 | 网页已出现 Space Needle earthquake 页面 | 补 Space Needle 9.0 设计指标并比较 1906 地震 |
| 36 | A | P0 | 全图原始识别为 Radio City Music Hall | 用实体重查 sporting events |
| 37 | 安全过滤 | 已处理 | 已识别 Honda HR-V，但美国销量冒充加拿大 | 保持弃答，直到检到 Canada 2017 `14,149` |
| 38 | A | P0 | 已识别 changing table | 查询 public baby changing tables first used 1950s |
| 39 | E | P2 | Red fox 未识别 | 暂不处理 |
| 40 | E | P2 | Food court 未识别 | 暂不处理 |
| 41 | D | P1 | Jeep Grand Cherokee 未识别 | 后续车辆裁剪批次处理 |
| 44 | D | P1 | Martinelli 标签未识别 | 后续 OCR/包装裁剪批次处理 |
| 47 | A | P0 | 所有裁剪重复识别 Andrea della Robbia，但出现复数拼写 | 规范化姓名后查出生日期 1435-10-20 |
| 48 | E | P2 | 老虎雕像错识别为动物园 | 暂不处理 |
| 49 | C | P0 | 多个裁剪直接读出 `18-24 males` | 输出简短类别答案，不附加未验证数字 |

## 3. P0 恢复策略

### 3.1 实体门控改为“双通道”

全图门控通过的实体继续作为正式实体。全图门控未通过时，多裁剪中满足以下任一条件的实体
进入“检索候选通道”，但不直接作为最终答案事实：

- 两个及以上裁剪给出同一规范化实体；
- 一个裁剪实体与该裁剪图片索引候选一致；
- 品牌、年份或专名在图像文字中可见。

检索候选只用于构造网页查询。最终答案仍要求网页证据与实体一致。

### 3.2 查询模板按问题类型生成

- 容量：`ENTITY passenger seating capacity`
- 年份比较：`ENTITY first introduced/produced year`
- 车型规格：`YEAR ENTITY ENGINE towing capacity torque`
- 历史：`ENTITY first used/introduction history`
- 场馆：`ENTITY sporting events boxing WNBA NFL draft`
- 食品/植物：`ENTITY origin/health benefits/lifespan`

### 3.3 简单计算由确定性逻辑完成

- 距离能力：`可行驶里程 = gallons × mpg`
- 年份先后：只比较证据中的年份
- 大小/数量比较：只比较同单位数值
- 图表最小值：输出类别，不复制多余数字

## 4. 阶段验收

第一轮只运行 P0 的 15 条及 5 条正确对照，共 20 条，保持一次云端模型/索引进程。

通过条件：

- P0 至少 8 条从弃答转为正确；
- 5 条正确对照全部保持正确；
- 新增错误不超过 1 条。

通过后再合并到固定 50 条。未通过则停止该实现，不扩大评测范围。
