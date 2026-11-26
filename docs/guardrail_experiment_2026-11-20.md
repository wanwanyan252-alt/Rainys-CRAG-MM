# CRAG-MM Llama 证据门控实验

日期：2026-11-20（Asia/Shanghai）

## 范围

- 保持 `Llama-3.2-11B-Vision-Instruct`、CLIP、BGE 和 DeepSeek 角色不变。
- 只使用固定 validation 前 50 条中的目标位置，没有运行完整 validation。
- 没有下载或替换模型、图片索引、网页索引或 BGE。
- 本轮没有重新调用 DeepSeek；以下结论不是官方 `gpt-4o` 分数。

## 实验一：强化实体与回答提示

目标样本：原 8 条错误及高风险非弃答，共 17 条。

产物：

`../artifacts/crag_v0.1.2_slice50/results_both_retrieval_guardrails_target17.json`

结果：

- 17 条中弃答 5 条。
- 原错误 00、07、37 被安全地转成弃答。
- 21、26、27、29 仍然产生错误答案。
- 43 从原来的正确年份退化为错误的“60s”。
- 16 仍只回答 German chamomile，没有覆盖 Roman chamomile。
- 34 的比较结论正确，但把 Pluto 首次出现的作品写成了 `The Picnic`。

结论：单纯强化提示能减少部分错误，但存在明显回退，不能作为默认策略。

## 实验二：同一 Llama 进行证据审计

第一组 12 条包括旧错误、第一轮残余错误及正确对照：

`../artifacts/crag_v0.1.2_slice50/results_both_retrieval_guardrails_verify_target12.json`

结果：12 条全部被转成弃答。审计正确拒绝了 21、26、27、29、34、43、49
等错误或带错误细节的答案，但也拒绝了 19 等正确答案。

第二组为剩余 10 条原 DeepSeek 判对样本：

`../artifacts/crag_v0.1.2_slice50/results_both_retrieval_guardrails_verify_correct10.json`

结果：10 条中只保留样本 45，其余 9 条均被转成弃答，正确答案保留率仅 10%。

结论：让同一 11B VLM 同时生成并审计自己的答案过度保守，不应默认启用。

## 最终状态

- 已回退所有会改变默认答案行为的实验逻辑。
- 保留 `tools/evaluate_vlm_slice.py --positions`，用于直接从固定清单按原位置运行小样本，避免复制清单或错误扩大范围。
- 本地和云端均通过 32 项 unittest。
- 云端评测结束后 GPU 为 0 MiB / 0%，没有残留推理进程。

## 下一步建议

不要继续堆叠自然语言警告或使用同一 Llama 做二元证据裁判。下一轮更值得做的是改进
目标实体的定位输入，例如对问题指向的局部区域进行裁剪或 grounding，再用原有网页检索和回答
流程验证。开始前仍应先在错误样本和正确对照组成的小集合上测试。

## 后续定位与数值校验结果

后续实验采用“原全图识别优先、多裁剪仅作回退”的策略，避免破坏已可靠识别的样本。
多裁剪修复了样本 27，并将样本 37 从品牌级 `honda` 提升到车型级 `Honda HR-V`。

新增数值—范围一致性校验后，37 使用美国销量冒充加拿大数据的回答被转为弃答。显式
`versus` 问题采用实体查询与原问题双查询，样本 27 同时获得 Sylvanian Families 和
Hello Kitty 证据，最终保留 `1985 vs 1974`。

固定 50 条候选结果见：

`../artifacts/crag_v0.1.2_slice50/results_both_retrieval_optimized_candidate_50.json`

保守人工估计为正确 16、弃答 27、错误 7，Truthfulness `0.18`。该结果尚未重新调用
DeepSeek。
