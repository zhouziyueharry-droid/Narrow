# New100K / 2K LambdaMART 训练与官方200条隔离测试

独立分支实验，默认仍为 PreciseReranker。Agent 和 user verbalizer 均未调用 LLM；API calls/tokens/cost 均为 0。
训练 1570 条合成会话，验证 430 条合成会话，测试 200 条正式会话。
训练 catalog SHA256: `51d12c525b5d90f22709d58d847db65d1f0290a96cc8af3a60329050cb1508e3`；官方测试 catalog SHA256: `da979b05a68af864cb0dcf9ee6a81c010c7e66a57978ad286c7a2e005fc69a67`。
训练商品库中的官方200目标数：0。训练期不加载官方测试商品库；模型冻结后才加载官方50K。
训练/验证目标商品互斥，并排除全部官方样本目标；同一会话不跨集合。同一请求轮次的候选列表是一个训练 group。
复用原 13 个特征，IDF 随模型冻结，重排全部候选。只用模拟目标的二元弱标签，未假定其他候选都语义不相关。
训练样本由原 PreciseReranker 驱动完整离线对话产生；不在候选池的目标不会被偷偷补入；改意图前轮次不标作目标正例。
同时比较当前 Precise、旧 LambdaMART、同数据线性模型和新 LambdaMART。
参数固定一组，轮数只由合成验证集的 NDCG@1/NDCG@10 早停确定，优先 Rank 1；官方200没有用于选模型。

| 精排 | Hit@10 | MRR | MTTC | TechnicalScore | 精排中位延迟(ms) |
|---|---:|---:|---:|---:|---:|
| precise | 0.875 | 0.4119 | 3.69 | 0.7072 | 26.12 |
| old_lambdamart | 0.920 | 0.4781 | 2.88 | 0.7659 | 30.31 |
| linear_same_data | 0.900 | 0.4211 | 3.52 | 0.7260 | 26.48 |
| lambdamart | 0.920 | 0.5330 | 2.85 | 0.7828 | 28.37 |

## 验收结论

```json
{
  "mrr_delta": 0.054871,
  "mrr_delta_at_least_0_02": true,
  "hit_at_10_delta": 0.0,
  "hit_at_10_not_lower_by_more_than_0_005": true,
  "technical_score_delta": 0.01686130000000008,
  "technical_score_improved": true,
  "recommended_merge": true
}
```

## 相同候选、相同对话状态上的比较

取原精排的测试轨迹，固定每轮候选和特征，只替换打分。按会话等权平均每轮指标；不是完整会话命中率。
| 精排 | 冻结轮次 Hit@10 | 冻结轮次 RR | NDCG@10 |
|---|---:|---:|---:|
| precise | 0.6011 | 0.3091 | 0.3674 |
| linear_same_data | 0.5823 | 0.2887 | 0.3466 |
| lambdamart | 0.7248 | 0.4882 | 0.5390 |
| old_lambdamart | 0.7347 | 0.4227 | 0.4911 |

## 限制

- 官方200条全部测试，保留原场景比例；这是本地模拟器评测，不等于线上真实用户效果或私有榜单成绩。
- 全部离线，不能和之前的在线 DeepSeek 分数直接对比。
- 新树模型和同数据线性模型的训练 catalog/IDF 均排除了全部官方200目标；旧模型仅作为历史对照。
- 缺少分级相关性标签和真实点击/购买反馈；算法替换不会解决标签歧义或上游误解析。
- 置信区间按会话配对自助抽样；模型未因此自动切换为默认。

配对比较：{"difference": 0.07563988095238094, "ci95": [0.04822620535714286, 0.10250572916666667], "candidate_only_hits": 10, "baseline_only_hits": 1}

重要特征（gain）：[["term_coverage", 81847.70858484507], ["quality", 33285.736938774586], ["rrf_raw", 25566.367434561253], ["category_match", 9248.30788564682], ["attribute_raw", 8065.825572013855], ["lexical_signal", 6770.687172412872]]

模型在 model/；训练分组与候选ID在 *_groups.json；特征和标签在 *.npz；完整结果在 *_sessions.json。
