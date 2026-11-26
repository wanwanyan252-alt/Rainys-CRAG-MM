# CRAG-MM 50 条联合检索自动报告

日期：2026-11-20（Asia/Shanghai）

模式：图片检索 + 网页检索 + VLM 实体改写。生成阶段未调用语义裁判。

## 代理指标

- 样本数：50
- 弃答数：27（54%）
- 接受实体改写：10（20%）
- 平均 token F1：0.1812
- 平均检索耗时：0.0805 秒
- 平均生成耗时：1.3346 秒
- 检索初始化：159.413 秒
- 模型初始化：28.058 秒
- CUDA 峰值分配：37.765 GiB

> Token F1 只是词汇重叠代理指标。低分可能仍语义正确，高分也不能排除事实错误。

## 高风险优先复核

非弃答且 token F1 < 0.32：

| 样本 | F1 | 实体改写 | 问题 | 回答 |
|---:|---:|---|---|---|
| 21 | 0.1622 | — | what are the standard sizes of the object with the sign? | The standard sizes of the object with the sign are 24, 30, 36, and 48 inches. |
| 27 | 0.2353 | — | when did these first go on sale versus hello kitty? | Hello Kitty first appeared on a vinyl coin purse in 1975, while the image of the small toy animals is not explicitly mentioned in the provided search results. |
| 34 | 0.2449 | — | was this character's first appearance before pluto's? | Minnie Mouse's first appearance was before Pluto's. |
| 16 | 0.2500 | — | which species of the flower on the package are used for herbal beverage infusions? | The species of the flower on the package used for herbal beverage infusions is chamomile. |
| 19 | 0.2632 | — | do these have more protein than chickpeas? | Yes, lentils have more protein than chickpeas. |
| 12 | 0.2642 | — | was this car around before the jaguar xk-e? | The car in the image was not around before the Jaguar XK-E, as the Jaguar XK-E was produced from 1966 to 1974, and the car in the image appears to be a newer model. |
| 29 | 0.2727 | — | who is the architect of this building? | The architect of this building is Cass Gilbert. |
| 49 | 0.3014 | — | which age and sex had the least amount of injury-related unintentional falls reported? | According to the data, the age group with the lowest number of injury-related unintentional falls reported was 18-24-year-olds, with a total of 125 visits per 10,000 people. This group had the lowest incidence of falls among both males and females, with 77.9 visits per 10,000 people for males and 142.4 visits |
| 8 | 0.3099 | — | would wearing this constantly at a 90 decibels volume damage a person's hearing? | Yes, wearing this constantly at a 90 decibels volume can damage a person's hearing. According to the World Health Organization, prolonged exposure to sounds above 85 decibels can cause permanent damage to the hair cells in the inner ear, leading to hearing loss. |
| 26 | 0.3103 | — | where were the generations of the suv next to the fire hydrant assembled? | The generations of the SUV next to the fire hydrant were assembled in Zama Heritage Car Garage in Japan. |

## Token F1 最高的 10 条

| 样本 | F1 | 问题 | 回答 |
|---:|---:|---|---|
| 45 | 0.8235 | what is considered a normal heart rate for adults? | A normal heart rate for adults is typically considered to be between 60 and 100 beats per minute. |
| 46 | 0.6957 | which borough of new york is this in? | The borough of New York City that this is in is Manhattan. |
| 3 | 0.6667 | what is the range of wavelength required to see the color of nearest fruits? | The range of wavelength required to see the color of nearest fruits is 500 - 570 nm. |
| 35 | 0.5556 | where is the manufacturer of this car located? | The manufacturer of this car, Honda, is located in Tokyo, Japan. |
| 31 | 0.5490 | does this police force have more officers than the los angeles one? | Yes, the New York City Police Department has more officers than the Los Angeles Police Department. |
| 43 | 0.5000 | when was this logo introduced? | The logo was introduced on June 18, 1971. |
| 37 | 0.4500 | which generation of this vehicle saw the highest sales per year in canada? | The 2017 model year saw the highest sales per year in Canada, with 197,251 units sold. |
| 7 | 0.4400 | what are some common attachments for clearing a space one can add to these machines? | Some common attachments for clearing a space that can be added to these machines include brush cutters, stump grinders, and root rakes. |
| 18 | 0.3846 | is this cat more likely to be a male or female? | The cat is more likely to be female, as calico cats are almost always female. |
| 17 | 0.3500 | how can you tell if this has gone bad? | To determine if a banana has gone bad, look for signs of mold, a mushy texture, and a brown color with liquid underneath. If you notice any of these signs, it's best to discard the banana. However, if the banana is simply overripe and has turned brown, it's still safe to eat or use for cooking. |
## DeepSeek 本地语义裁判

- 模型：`deepseek-flash`
- 正确：15
- 弃答：27
- 错误：8
- 裁判错误：0
- Truthfulness：`0.1400`
- 回答覆盖率：`46.0%`
- 已回答样本正确率：`65.2%`

> 这是 DeepSeek 本地对照分，不等同于官方默认 gpt-4o 裁判分数。
