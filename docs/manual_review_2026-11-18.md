# CRAG-MM 小样本人工复核清单

日期：2026-11-18（Asia/Shanghai）

## 复核目标

对固定的 4 条官方 `validation` 样本分别检查：

1. 无检索回答；
2. 仅图片检索回答。

评分沿用 CRAG-MM 规则：正确记 `1`，明确不知道或信息不足记 `0`，错误、
无关或带有误导性事实记 `-1`。本轮没有启用语义裁判，最终标签需要人工确认。

## 操作步骤

1. 依次打开下面 4 张图片，先不要看参考答案。
2. 阅读问题和两种模型回答，判断回答是否真正回答了问题。
3. 再展开参考答案核对事实；不要要求措辞完全一致，只检查核心事实。
4. 在每条样本下勾选一个分数，并在“人工备注”处写下理由。
5. 最后填写文末汇总表。如果认同“建议初判”，直接把对应分数抄入即可。
6. 完成后把本文件中勾选和备注的改动保存，后续即可据此固定人工基线。

原始机器结果：

- `../artifacts/crag_v0.1.2_slice4/results_no_retrieval.json`
- `../artifacts/crag_v0.1.2_slice4/results_image_retrieval.json`

## 样本 0：Subaru WRX 载客量

![样本 0](../artifacts/crag_v0.1.2_slice4/00.jpg)

问题：`is this a good car for transporting seven passengers at once?`

参考答案：不是。图中为 Subaru WRX，乘员容量共 5 人。

无检索回答：

> The car in the image is a Subaru WRX, which is a sports car and not designed
> to transport seven passengers at once. It has two doors and a small interior,
> making it unsuitable for carrying multiple passengers.

建议初判：`1`。核心结论正确，也正确识别了车型；“two doors”不是参考答案所需事实，
但不影响“不能载 7 人”的结论。

- [√] `1` 正确
- [ ] `0` 不知道/信息不足
- [ ] `-1` 错误或无关

人工备注：two doors确实是无关信息

仅图片检索回答：

> I don't have sufficient information to answer this question because I cannot
> identify individuals based on their images.

检索首位实体实际为 `Subaru WRX`，分数约 `0.642`，但生成回答出现与人物识别无关的
拒答。建议初判：`0`；若按“无关回答”严格处理，也可判 `-1`，请人工决定。

- [ ] `1` 正确
- [ ] `0` 不知道/信息不足
- [√] `-1` 错误或无关

人工备注：不知道应该是直接I dont know。而不是一堆废话

## 样本 1：Chevrolet Trailblazer 油耗

![样本 1](../artifacts/crag_v0.1.2_slice4/01.jpg)

问题：`can the 2023 model with a 1.3l awd engine of this vehicle get from washington, dc to baltimore on 5 gallons of gas?`

参考答案：可以。两地约 40–45 英里；该车型约 28 mpg，5 加仑约可行驶 140 英里。

无检索回答：`I don't know.`

建议初判：`0`。

- [ ] `1` 正确
- [√] `0` 不知道/信息不足
- [ ] `-1` 错误或无关

人工备注：这个没问题

仅图片检索回答：`I don't know.`

图片检索没有命中 Chevrolet Trailblazer，首位错误实体为 `Jeep Grand Cherokee`。
建议初判：`0`。

- [ ] `1` 正确
- [√] `0` 不知道/信息不足
- [ ] `-1` 错误或无关

人工备注：这个没问题

## 样本 2：Bacon cheese fries 起源

![样本 2](../artifacts/crag_v0.1.2_slice4/02.jpg)

问题：`what is the origin of this food item?`

参考答案：Bacon cheese fries 来自美国，但确切起源未知；cheese fries 在 1952 年后
随罐装奶酪产品普及，辣肉酱奶酪薯条的一个变体据称来自得州 Tomball。

无检索回答：`I don't know.`

建议初判：`0`。

- [ ] `1` 正确
- [√] `0` 不知道/信息不足
- [ ] `-1` 错误或无关

人工备注：这个没问题

仅图片检索回答：

> The origin of this food item is the American Southwest, specifically San
> Diego, where it originated as a local dish speciality.

该回答给出参考答案不支持的 San Diego 精确起源。建议初判：`-1`。

- [ ] `1` 正确
- [ ] `0` 不知道/信息不足
- [√] `-1` 错误或无关

人工备注：答案完全在胡说

## 样本 3：牛油果颜色波长

![样本 3](../artifacts/crag_v0.1.2_slice4/03.jpg)

问题：`what is the range of wavelength required to see the color of nearest fruits?`

参考答案：最近的水果是牛油果，其绿色对应约 `500–565 nm`。

无检索回答：`The range ... is approximately 380-780 nanometers.`

建议初判：`-1`。回答给的是完整可见光范围，不是图中最近水果颜色的波段。

- [ ] `1` 正确
- [ ] `0` 不知道/信息不足
- [√] `-1` 错误或无关

人工备注：同意初判

仅图片检索回答：`The range ... is approximately 380-780 nanometers.`

图片检索已在第 9 位命中 `avocado`，但生成回答未利用该实体完成绿色波长推断。
建议初判：`-1`。

- [ ] `1` 正确
- [ ] `0` 不知道/信息不足
- [√] `-1` 错误或无关

人工备注：波长错误

## 人工评分汇总

| 样本 | 无检索 | 仅图片检索 | 备注 |
|---|---:|---:|---|
| 0 | 1 | -1 | 图片检索产生无关的身份识别拒答 |
| 1 | 0 | 0 | 两种模式均正确弃答 |
| 2 | 0 | -1 | 图片检索捏造 San Diego 起源 |
| 3 | -1 | -1 | 两种模式均误答为完整可见光范围 |
| 平均分 | **0.00** | **-0.75** | 图片检索相对无检索退化 0.75 分 |

以上分数已由用户于 2026-11-19 人工确认，不是语义裁判的自动评分。

## 复核后建议动作

1. 优先缩短图片检索上下文：减少候选数量、排除超长且低相关实体属性。
2. 检查 Llama 提示模板为何把车辆问答误触发为“无法识别人脸/个人”的拒答。
3. 用本文件的 4 条样本重复回归，确认图片检索不再让样本 0 从正确退化为拒答。
4. 再部署网页索引到云端并运行 `--web-retrieval`；不要在修复图片上下文前扩大样本。

## 2026-11-20 自动回归补充

上述 4 条人工评分已用于指导修复。最终图片 + 网页联合检索结果为：

| 样本 | 最终回答摘要 | 建议标签（未人工确认） |
|---:|---|---:|
| 0 | 正确否定 7 人，但错误声称 WRX 只有 4 座（参考为 5 座） | -1 |
| 1 | `I don't know.` | 0 |
| 2 | `I don't know.`，不再捏造 San Diego/Carne asada 起源 | 0 |
| 3 | avocado 颜色波长 `500–570nm` | 1 |

该回归的建议均分为 `0.00`。正式结果仍以人工或语义裁判为准。

## 云端收尾操作

本轮自动检查确认云端 GPU 已回到 `0 MiB`，没有后台推理任务。完成复核或暂不继续时：

1. 打开矩池云控制台。
2. 找到当前 A40 实例。
3. 点击“暂停”，不要点“释放”或删除快照。
4. 确认实例状态显示为已暂停，停止按时计费。
