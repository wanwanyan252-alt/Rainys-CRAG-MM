# CRAG-MM 50 条联合检索自动报告

日期：2026-11-22（Asia/Shanghai）

模式：图片检索 + 网页检索 + VLM 实体改写。生成阶段未调用语义裁判。

## 代理指标

- 样本数：50
- 弃答数：19（38%）
- 接受实体改写：20（40%）
- 平均 token F1：0.2474
- 平均检索耗时：0.0837 秒
- 平均生成耗时：1.6817 秒
- 检索初始化：160.333 秒
- 模型初始化：28.190 秒
- CUDA 峰值分配：42.511 GiB

> Token F1 只是词汇重叠代理指标。低分可能仍语义正确，高分也不能排除事实错误。

## 高风险优先复核

非弃答且 token F1 < 0.32：

| 样本 | F1 | 实体改写 | 问题 | 回答 |
|---:|---:|---|---|---|
| 18 | 0.1053 | — | is this cat more likely to be a male or female? | The cat is more likely to be female. |
| 21 | 0.1622 | — | what are the standard sizes of the object with the sign? | The standard sizes of the object with the sign are 24, 30, 36, and 48 inches. |
| 12 | 0.2143 | Tesla Model X | was this car around before the jaguar xk-e? | the Tesla Model X was not around before the Jaguar XKE. |
| 13 | 0.2254 | — | is it dangerous living next to these towers? | According to the provided web search results, it is unlikely to be dangerous living next to these towers. |
| 28 | 0.2430 | — | what multimedia features does this car have? | The 2015 Chevrolet Suburban has multimedia features such as MyLink, which provides easy and intuitive operation of basic functions, and is highly customizable, capable of linking up to 10 devices such as smartphones, SD cards, and MP3 players. Additionally, it includes a Text Messaging Alerts feature for smartphone users with Bluetooth profile (M.A.P.), which reads incoming texts through the vehicle's speakers, and Siri Eyes Free for iPhone iOS 6 and iOS 7 users to enhance connectivity and convenience. |
| 34 | 0.2449 | Minnie Mouse | was this character's first appearance before pluto's? | Minnie Mouse's first appearance was before Pluto's. |
| 16 | 0.2500 | — | which species of the flower on the package are used for herbal beverage infusions? | The species of the flower on the package used for herbal beverage infusions is chamomile. |
| 19 | 0.2632 | — | do these have more protein than chickpeas? | Yes, lentils have more protein than chickpeas. |
| 29 | 0.2727 | — | who is the architect of this building? | The architect of this building is Cass Gilbert. |
| 8 | 0.2857 | — | would wearing this constantly at a 90 decibels volume damage a person's hearing? | Yes, wearing this constantly at a 90 decibels volume can damage a person's hearing. |
| 30 | 0.3030 | — | what are some health benefits of consuming these? | Onions are rich in antioxidants and have anti-inflammatory properties, which can help reduce the risk of heart disease, improve blood circulation, and prevent certain types of cancer. They also contain fiber, which can aid digestion and help manage blood sugar levels. Additionally, onions have prebiotic properties that can support gut health and boost the immune system. |
| 26 | 0.3103 | — | where were the generations of the suv next to the fire hydrant assembled? | The generations of the SUV next to the fire hydrant were assembled in Zama Heritage Car Garage in Japan. |

## Token F1 最高的 10 条

| 样本 | F1 | 问题 | 回答 |
|---:|---:|---|---|
| 45 | 0.8235 | what is considered a normal heart rate for adults? | A normal heart rate for adults is typically considered to be between 60 and 100 beats per minute. |
| 46 | 0.6957 | which borough of new york is this in? | The borough of New York City that this is in is Manhattan. |
| 3 | 0.6667 | what is the range of wavelength required to see the color of nearest fruits? | The range of wavelength required to see the color of nearest fruits is 500 - 570 nm. |
| 1 | 0.5556 | can the 2023 model with a 1.3l awd engine of this vehicle get from washington, dc to baltimore on 5 gallons of gas? | The 2023 Chevy Trailblazer with a 1.3L AWD engine can get from Washington, DC to Baltimore on 5 gallons of gas. |
| 35 | 0.5556 | where is the manufacturer of this car located? | The manufacturer of this car, Honda, is located in Tokyo, Japan. |
| 31 | 0.5490 | does this police force have more officers than the los angeles one? | Yes, the New York City Police Department has more officers than the Los Angeles Police Department. |
| 47 | 0.5455 | when was the artist who made this born? | The artist who made this, Andrea della Robbia, was born in 1435. |
| 20 | 0.5161 | did the japanese police use this during the 1998 winter olympics in nagano? | The Japanese police did not use the Nissan Z during the 1998 Winter Olympics in Nagano. |
| 43 | 0.5000 | when was this logo introduced? | The logo was introduced on June 18, 1971. |
| 33 | 0.4727 | can the tall tower in the picture withstand an earthquake similar to the 1906 san francisco earthquake? | The Space Needle, the tall tower in the picture, is designed to withstand earthquakes of up to 9.0 magnitude. |
## DeepSeek 本地语义裁判

- 模型：`deepseek-flash`
- 正确：24
- 弃答：19
- 错误：7
- 裁判错误：0
- Truthfulness：`0.3400`
- 回答覆盖率：`62.0%`
- 已回答样本正确率：`77.4%`

> 这是 DeepSeek 本地对照分，不等同于官方默认 gpt-4o 裁判分数。
