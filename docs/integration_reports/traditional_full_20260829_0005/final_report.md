# 传统双模式评测分析

## 总体结果

| 模式 | 样本 | 成功率/HitRate@10 | MRR | 平均执行轮次 | API 调用 |
| --- | ---: | ---: | ---: | ---: | ---: |
| TechJam | 200 | 0.820000 | 0.329188 | 3.825000 | 0 |
| Realistic | 100 | 0.970000 | 0.709524 | 1.410000 | 0 |

## 与旧传统基线比较

旧基线只保留 aggregate Markdown，没有 session JSON；因此本节只能比较总体指标，不能声称识别了逐样本 regression。

### Techjam

| 指标 | 旧值 | 当前值 | 差值 |
| --- | ---: | ---: | ---: |
| `sample_count` | 200 | 200 | +0.000000 |
| `hit_rate_at_10` | 0.82 | 0.82 | +0.000000 |
| `mrr` | 0.329188 | 0.329188 | +0.000000 |
| `mttc` | 4.005 | 4.005 | +0.000000 |
| `efficiency` | 0.6995 | 0.6995 | +0.000000 |
| `recommended_technical_score` | 0.648656 | 0.648656 | +0.000000 |

基线来源：`user-simulator/docs/results/baseline-techjam-200.md`

### Realistic

| 指标 | 旧值 | 当前值 | 差值 |
| --- | ---: | ---: | ---: |
| `sample_count` | 100 | 100 | +0.000000 |
| `success_rate` | 0.97 | 0.97 | +0.000000 |
| `mrr` | 0.709524 | 0.709524 | +0.000000 |

基线来源：`user-simulator/docs/results/baseline-realistic-100.md`

## 运行质量

- techjam: 765 turns，trace errors=0，agent errors=0，fallback reasons={'no_structured_signal': 42, 'reference_or_comparison': 42, 'unresolved_negation': 44}
- realistic: 141 turns，trace errors=0，agent errors=0，fallback reasons={'no_structured_signal': 16, 'reference_or_comparison': 5}

## 代表性问题案例

### 案例 1: techjam / public_0046

- 场景：`intent_override`
- 成功：`False`；执行轮次：`10`
- 诊断分类：`constraint_filter_drop_observed_top20`
- 诊断置信度：`low`
- 选择理由：deterministic highest-priority TechJam failure
- 分析：目标进入融合候选后被过滤掉；需检查解析出的硬约束和过滤逻辑。
- 评测目标：`{"goal_type": "target_product", "goal_id": "public_0046", "target_product_id": "B0B42PVX1F", "category": "Socks & Hosiery Leg Warmers", "constraints": [{"attribute": "material", "values": ["wool"], "strength": "hard", "disclosed": false, "active": true, "source": "techjam", "relaxable": false}, {"attribute": "material", "values": ["44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester"], "strength": "hard", "disclosed": false, "active": true, "source": "techjam", "relaxable": false}, {"attribute": "feature", "values": ["Imported"], "strength": "soft", "disclosed": false, "active": true, "source": "techjam", "relaxable": true}, {"attribute": "feature", "values": ["No Closure closure"], "strength": "soft", "disclosed": false, "active": true, "source": "techjam", "relaxable": true}], "source_dataset": "techjam"}`

#### Turn 1

- User: I'm looking for Socks & Hosiery Leg Warmers. No Closure closure
- User act: `{"type": "INITIAL_REQUEST", "attribute": null, "values": [], "reason_code": "techjam:intent_override", "references": [], "allowed_facts": [], "surface_text": "I'm looking for Socks & Hosiery Leg Warmers. No Closure closure"}`
- Agent: The current matches mainly differ by brand: ordenado, durio, guozyun. Which do you prefer?
- Ask: `brand`
- Recommendations: `['B07W47N5ZH', 'B07K2SJFHK', 'B075CJR281', 'B01N0V86B2', 'B0BF5F88VT', 'B07XM5MHB3', 'B00KLNCO5K', 'B0BKBS1DQ3', 'B07PQQQ8ZL', 'B01HJVJXMS']`
- Layer candidate counts: `lexical_candidates=300, dense_candidates=200, attribute_candidates=200, fused_candidates=500, filtered_candidates=488, ranked_candidates=488`
- Agent latency: `108.648 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Socks & Hosiery Leg Warmers", "constraints": [{"field": "feature", "operator": "contains", "value": "No Closure closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "feature", "operator": "not_contains", "value": "Closure closure", "strength": "hard", "confidence": 0.88, "source_turn": 1}, {"field": "feature", "operator": "contains", "value": "warm", "strength": "soft", "confidence": 0.84, "source_turn": 1}], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Socks & Hosiery Leg Warmers No Closure closure warm", "intent_summary": "Socks & Hosiery Leg Warmers No Closure closure warm", "language": "en", "confidence": 0.78, "parser": "fallback", "fallback_reasons": ["unresolved_negation"]}, "semantic_fallback_reasons": ["unresolved_negation"]}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{"active_constraints": [{"field": "feature", "operator": "contains", "value": "No Closure closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "feature", "operator": "not_contains", "value": "Closure closure", "strength": "hard", "confidence": 0.88, "source_turn": 1}, {"field": "feature", "operator": "contains", "value": "warm", "strength": "soft", "confidence": 0.84, "source_turn": 1}], "superseded_constraints": []}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{"lexical_candidates": {"count": 300, "top_product_ids": ["B07W47N5ZH", "B0BF5F88VT", "B07PQQQ8ZL", "B07K2SJFHK", "B0B42PVX1F", "B07FMTQTGD", "B08P8SHDWB", "B09FGHDFB8", "B075CJR281", "B01HJVJXMS", "B07XM5MHB3", "B077YFNJL5", "B00KLNCO5K", "B0BGCL426M", "B00FITO44G", "B0757K589H", "B00BB2O110", "B01N0GC4V7", "B00LLQ246A", "B00AMA1QEC"]}, "dense_candidates": {"count": 200, "top_product_ids": ["B07W47N5ZH", "B0BGCL426M", "B0BF5F88VT", "B07K2SJFHK", "B075CJR281", "B07J55QMR9", "B0BHP4R2S4", "B0B79LH75D", "B01CH9U556", "B0BNTYWGB1", "B08FDDH64V", "B077VMQGL3", "B08MW2K4JR", "B07XM5MHB3", "B00FITO44G", "B07BPXV95Y", "B077YFNJL5", "B08PW3W1JR", "B07ZRB44TH", "B08GRZB5B8"]}, "attribute_candidates": {"count": 200, "top_product_ids": ["B0757K589H", "B00ZUKIA02", "B07PQQQ8ZL", "B0BGCL426M", "B07MYZ4VXM", "B086HXJ2GY", "B01HJVJXMS", "B07FZ13BKH", "B0B42PVX1F", "B07K2SJFHK", "B00AMA1QEC", "B091DQRRQF", "B01N0GC4V7", "B07RM6FNNS", "B07TX3FG1B", "B00KLNCO5K", "B07W47N5ZH", "B01N0V86B2", "B0BF5F88VT", "B00B2YV4BW"]}}`
  - Layer `rrf_fusion`: `{"fused_candidates": {"count": 500, "top_product_ids": ["B07W47N5ZH", "B07K2SJFHK", "B0BF5F88VT", "B0BGCL426M", "B07PQQQ8ZL", "B075CJR281", "B07XM5MHB3", "B0B42PVX1F", "B01HJVJXMS", "B077YFNJL5", "B09FGHDFB8", "B00KLNCO5K", "B08P8SHDWB", "B00FITO44G", "B01N0V86B2", "B07FMTQTGD", "B00AMA1QEC", "B07MYZ4VXM", "B01CH9U556", "B00BB2O110"]}}`
  - Layer `constraint_filter`: `{"filtered_candidates": {"count": 488, "top_product_ids": ["B07W47N5ZH", "B07K2SJFHK", "B0BF5F88VT", "B07PQQQ8ZL", "B075CJR281", "B07XM5MHB3", "B01HJVJXMS", "B077YFNJL5", "B09FGHDFB8", "B00KLNCO5K", "B08P8SHDWB", "B00FITO44G", "B01N0V86B2", "B07FMTQTGD", "B00AMA1QEC", "B07MYZ4VXM", "B01CH9U556", "B00BB2O110", "B01N0GC4V7", "B0757K589H"]}}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 488, "top_product_ids": ["B07W47N5ZH", "B07K2SJFHK", "B075CJR281", "B01N0V86B2", "B0BF5F88VT", "B07XM5MHB3", "B00KLNCO5K", "B0BKBS1DQ3", "B07PQQQ8ZL", "B01HJVJXMS", "B07MYZ4VXM", "B07FMTQTGD", "B078GDJJH3", "B00ZUKIA02", "B01N0GC4V7", "B08SBRYSDS", "B077YFNJL5", "B076S5JZYC", "B01M03UHYC", "B00B2YV4BW"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "brand", "question_scores": {"material": 0.6959173926543089, "color": 0.39539589738056696, "style": 0.4505463662498364, "brand": 0.9980669251587667, "budget": 0.31596026744369715, "use_case": 0.679515931275645}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B07W47N5ZH", "score": 20.650097}, {"parent_asin": "B07K2SJFHK", "score": 20.042093}, {"parent_asin": "B075CJR281", "score": 19.586995}, {"parent_asin": "B01N0V86B2", "score": 19.378491}, {"parent_asin": "B0BF5F88VT", "score": 18.825547}, {"parent_asin": "B07XM5MHB3", "score": 17.904593}, {"parent_asin": "B00KLNCO5K", "score": 17.886604}, {"parent_asin": "B0BKBS1DQ3", "score": 17.424105}, {"parent_asin": "B07PQQQ8ZL", "score": 17.257752}, {"parent_asin": "B01HJVJXMS", "score": 16.645054}]}`
  - Layer `validate_response`: `{"errors": []}`

#### Turn 2

- User: I don't have an additional preference for brand.
- User act: `{"type": "NO_PREFERENCE", "attribute": "brand", "values": [], "reason_code": "techjam:no_additional_preference", "references": [], "allowed_facts": [], "surface_text": "I don't have an additional preference for brand."}`
- Agent: The current matches mainly differ by material: polyester, cotton, spandex. Which do you prefer?
- Ask: `material`
- Recommendations: `['B07W47N5ZH', 'B07K2SJFHK', 'B075CJR281', 'B01N0V86B2', 'B0BF5F88VT', 'B07XM5MHB3', 'B00KLNCO5K', 'B07MYZ4VXM', 'B07FMTQTGD', 'B078GDJJH3']`
- Layer candidate counts: `ranked_candidates=488`
- Agent latency: `109.126 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Socks & Hosiery Leg Warmers", "constraints": [], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Socks & Hosiery Leg Warmers", "intent_summary": "Socks & Hosiery Leg Warmers", "language": "en", "confidence": 0.97, "parser": "fallback", "fallback_reasons": []}, "semantic_fallback_reasons": []}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 488, "top_product_ids": ["B07W47N5ZH", "B07K2SJFHK", "B075CJR281", "B01N0V86B2", "B0BF5F88VT", "B07XM5MHB3", "B00KLNCO5K", "B07MYZ4VXM", "B07FMTQTGD", "B078GDJJH3", "B0BKBS1DQ3", "B00ZUKIA02", "B07PQQQ8ZL", "B01N0GC4V7", "B08SBRYSDS", "B077YFNJL5", "B076S5JZYC", "B01HJVJXMS", "B01M03UHYC", "B00B2YV4BW"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "material", "question_scores": {"material": 0.6959173926543089, "color": 0.39539589738056696, "style": 0.4505463662498364, "budget": 0.31596026744369715, "use_case": 0.679515931275645}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B07W47N5ZH", "score": 19.400097}, {"parent_asin": "B07K2SJFHK", "score": 18.792093}, {"parent_asin": "B075CJR281", "score": 18.336995}, {"parent_asin": "B01N0V86B2", "score": 18.128491}, {"parent_asin": "B0BF5F88VT", "score": 17.575547}, {"parent_asin": "B07XM5MHB3", "score": 16.654593}, {"parent_asin": "B00KLNCO5K", "score": 16.636604}, {"parent_asin": "B07MYZ4VXM", "score": 16.627627}, {"parent_asin": "B07FMTQTGD", "score": 16.511563}, {"parent_asin": "B078GDJJH3", "score": 16.311653}]}`
  - Layer `validate_response`: `{}`

#### Turn 3

- User: For that, what matters is: wool; 44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester.
- User act: `{"type": "ANSWER_ATTRIBUTE", "attribute": "material", "values": ["wool", "44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester"], "reason_code": "techjam:answer_attribute", "references": [], "allowed_facts": [], "surface_text": "For that, what matters is: wool; 44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester."}`
- Agent: The current matches mainly differ by use case: winter, work, running. Which do you prefer?
- Ask: `use_case`
- Recommendations: `['B01N0GC4V7', 'B00KLRU1UG', 'B01M4OJJ3X', 'B074MBFT1M', 'B00VVZHM1I', 'B09C675V6L', 'B07Z949DGK', 'B0BQGG6SY2', 'B0B4JVPFYV', 'B07J481NNG']`
- Layer candidate counts: `lexical_candidates=300, dense_candidates=200, attribute_candidates=200, fused_candidates=500, filtered_candidates=290, ranked_candidates=290`
- Agent latency: `174.258 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Socks & Hosiery Leg Warmers", "constraints": [{"field": "material", "operator": "contains", "value": "44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "not_contains", "value": "Wool", "strength": "hard", "confidence": 0.88, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "cotton", "strength": "soft", "confidence": 0.9, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "polyester", "strength": "soft", "confidence": 0.9, "source_turn": 3}], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Socks & Hosiery Leg Warmers 44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester cotton polyester", "intent_summary": "Socks & Hosiery Leg Warmers 44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester cotton polyester", "language": "en", "confidence": 0.97, "parser": "fallback", "fallback_reasons": []}}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{"active_constraints": [{"field": "feature", "operator": "contains", "value": "No Closure closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "feature", "operator": "not_contains", "value": "Closure closure", "strength": "hard", "confidence": 0.88, "source_turn": 1}, {"field": "feature", "operator": "contains", "value": "warm", "strength": "soft", "confidence": 0.84, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "not_contains", "value": "Wool", "strength": "hard", "confidence": 0.88, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "cotton", "strength": "soft", "confidence": 0.9, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "polyester", "strength": "soft", "confidence": 0.9, "source_turn": 3}]}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{"lexical_candidates": {"count": 300, "top_product_ids": ["B0B42PVX1F", "B01N0GC4V7", "B08S1SYPVJ", "B08P8SHDWB", "B07W47N5ZH", "B075CJR281", "B0BF5F88VT", "B00FITO44G", "B00BB2O110", "B07PQQQ8ZL", "B07K2SJFHK", "B01K55QCTC", "B00KLNCO5K", "B00AMA1QEC", "B0757K589H", "B0B58WVKXC", "B09FGHDFB8", "B00LTY074K", "B00UVTBTXW", "B0BGCL426M"]}, "dense_candidates": {"count": 200, "top_product_ids": ["B0B42PVX1F", "B07BV6G5DZ", "B07W47N5ZH", "B0009GCUIU", "B07XZ9RDG8", "B06ZZPY7TL", "B01CH9U556", "B00VVZHM1I", "B0BGCL426M", "B09PB51MBP", "B01HJVJXMS", "B0BNTYWGB1", "B0749KMYK2", "B09NVZJJ2F", "B0B2XL9LPM", "B0716CNB7X", "B014W132ZM", "B0BF5F88VT", "B07WWW8CXJ", "B09FGHDFB8"]}, "attribute_candidates": {"count": 200, "top_product_ids": ["B0B42PVX1F", "B078GDJJH3", "B0C246QRQS", "B0C277G9FW", "B07XZ9RDG8", "B07WWW8CXJ", "B09NZGBRH8", "B08GRZB5B8", "B07YWJ7KVZ", "B08FD89PBZ", "B07GJD1NNM", "B0CCD37DTM", "B07X9MHYPC", "B07K7TH59T", "B0749KMYK2", "B0BNTYWGB1", "B07VCBPTWG", "B08MXLQCQV", "B07ZNQBNQP", "B08ZMT8S77"]}}`
  - Layer `rrf_fusion`: `{"fused_candidates": {"count": 500, "top_product_ids": ["B0B42PVX1F", "B07WWW8CXJ", "B0749KMYK2", "B07X9MHYPC", "B01N0GC4V7", "B07W47N5ZH", "B0CCD37DTM", "B0BF5F88VT", "B078GDJJH3", "B075CJR281", "B0BNTYWGB1", "B00FITO44G", "B07PQQQ8ZL", "B08S1SYPVJ", "B08P8SHDWB", "B0BGCL426M", "B09FGHDFB8", "B07K7TH59T", "B09NZGBRH8", "B08FD89PBZ"]}}`
  - Layer `constraint_filter`: `{"filtered_candidates": {"count": 290, "top_product_ids": ["B01N0GC4V7", "B07W47N5ZH", "B0BF5F88VT", "B075CJR281", "B00FITO44G", "B07PQQQ8ZL", "B08P8SHDWB", "B09FGHDFB8", "B01HJVJXMS", "B07K2SJFHK", "B00AMA1QEC", "B07FMTQTGD", "B01CH9U556", "B00BB2O110", "B00VVZHM1I", "B07MYZ4VXM", "B077YFNJL5", "B00KLNCO5K", "B01N0V86B2", "B0757K589H"]}}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 290, "top_product_ids": ["B01N0GC4V7", "B00KLRU1UG", "B01M4OJJ3X", "B074MBFT1M", "B00VVZHM1I", "B09C675V6L", "B07Z949DGK", "B0BQGG6SY2", "B0B4JVPFYV", "B07J481NNG", "B07F7T9WC5", "B0853XV3HR", "B07H7DVK7M", "B005ONGJ30", "B0C5RLJDSF", "B01N4X6ZMJ", "B0735V67KT", "B08Z7PYLLY", "B06WD2GXWB", "B082PKZ7DP"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "use_case", "question_scores": {"color": 0.2691082613448433, "style": 0.48118142879803205, "budget": 0.2040364699480271, "use_case": 0.49357229009715586}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B01N0GC4V7", "score": 37.348926}, {"parent_asin": "B00KLRU1UG", "score": 31.667784}, {"parent_asin": "B01M4OJJ3X", "score": 31.509639}, {"parent_asin": "B074MBFT1M", "score": 31.502065}, {"parent_asin": "B00VVZHM1I", "score": 30.594393}, {"parent_asin": "B09C675V6L", "score": 29.924259}, {"parent_asin": "B07Z949DGK", "score": 29.864704}, {"parent_asin": "B0BQGG6SY2", "score": 29.695741}, {"parent_asin": "B0B4JVPFYV", "score": 29.581867}, {"parent_asin": "B07J481NNG", "score": 27.54103}]}`
  - Layer `validate_response`: `{}`

#### Turn 4

- User: Actually, ignore my earlier preference. What I need is: wool.
- User act: `{"type": "OVERRIDE", "attribute": null, "values": ["wool"], "reason_code": "techjam:intent_override", "references": [], "allowed_facts": [], "surface_text": "Actually, ignore my earlier preference. What I need is: wool."}`
- Agent: The current matches mainly differ by style: sport, casual, vintage. Which do you prefer?
- Ask: `style`
- Recommendations: `['B0CCD37DTM', 'B01N22XTDC', 'B01K8WCQLA', 'B07WPFZ1C7', 'B001V5J61M', 'B07H3FP3R5', 'B0B2XL9LPM', 'B07MJGVHZY', 'B09NZGBRH8', 'B004I6E8NW']`
- Layer candidate counts: `lexical_candidates=300, dense_candidates=200, attribute_candidates=200, fused_candidates=500, filtered_candidates=490, ranked_candidates=490`
- Agent latency: `104.975 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "replace", "category": "Socks & Hosiery Leg Warmers", "constraints": [{"field": "material", "operator": "contains", "value": "wool", "strength": "soft", "confidence": 0.9, "source_turn": 4}], "remove_fields": [], "no_preference": [], "retire_soft": true, "semantic_query": "Socks & Hosiery Leg Warmers wool", "intent_summary": "Socks & Hosiery Leg Warmers wool", "language": "en", "confidence": 0.97, "parser": "fallback", "fallback_reasons": []}}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{"active_constraints": [{"field": "feature", "operator": "not_contains", "value": "Closure closure", "strength": "hard", "confidence": 0.88, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "wool", "strength": "soft", "confidence": 0.9, "source_turn": 4}], "superseded_constraints": [{"field": "feature", "operator": "contains", "value": "No Closure closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "feature", "operator": "contains", "value": "warm", "strength": "soft", "confidence": 0.84, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "cotton", "strength": "soft", "confidence": 0.9, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "polyester", "strength": "soft", "confidence": 0.9, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "not_contains", "value": "Wool", "strength": "hard", "confidence": 0.88, "source_turn": 3}]}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{"lexical_candidates": {"count": 300, "top_product_ids": ["B0B42PVX1F", "B07XM5MHB3", "B00FITO44G", "B00KLNCO5K", "B00BB2O110", "B0757K589H", "B07W47N5ZH", "B00LLQ246A", "B00AMA1QEC", "B075CJR281", "B0BF5F88VT", "B077YFNJL5", "B08P8SHDWB", "B07FMTQTGD", "B07K2SJFHK", "B07PQQQ8ZL", "B09FGHDFB8", "B01N0V86B2", "B078GDJJH3", "B00ZUKIA02"]}, "dense_candidates": {"count": 200, "top_product_ids": ["B07W47N5ZH", "B0BGCL426M", "B00FITO44G", "B07BPXV95Y", "B00KLNCO5K", "B0BFV7LR3F", "B01CH9U556", "B075CJR281", "B0BF5F88VT", "B07XM5MHB3", "B01N0V86B2", "B0C277G9FW", "B07YWJ7KVZ", "B0B7F884XV", "B07XZ9RDG8", "B07YJLPJ3R", "B0B2XL9LPM", "B07KVCG6YL", "B08L7CPK1V", "B0776SVXW9"]}, "attribute_candidates": {"count": 200, "top_product_ids": ["B0B42PVX1F", "B078GDJJH3", "B0C246QRQS", "B0C277G9FW", "B0BGJ81PNQ", "B07ZQGLRH4", "B07XZ9RDG8", "B07WWW8CXJ", "B003O696D4", "B07RM4HYFS", "B0BFV7LR3F", "B001V5J61M", "B004I6E8NW", "B074RLSFKX", "B00FAVYNKM", "B009LB8CX6", "B07WPFZ1C7", "B076LKFG1T", "B006230L6C", "B09NZGBRH8"]}}`
  - Layer `rrf_fusion`: `{"fused_candidates": {"count": 500, "top_product_ids": ["B0B42PVX1F", "B078GDJJH3", "B00FITO44G", "B07XM5MHB3", "B00KLNCO5K", "B07W47N5ZH", "B0BFV7LR3F", "B0C277G9FW", "B07YJLPJ3R", "B075CJR281", "B00BB2O110", "B0BF5F88VT", "B07WWW8CXJ", "B07X9MHYPC", "B00AMA1QEC", "B006230L6C", "B002ACD6DO", "B01MRRZ3J1", "B01N0V86B2", "B0BGCL426M"]}}`
  - Layer `constraint_filter`: `{"filtered_candidates": {"count": 490, "top_product_ids": ["B078GDJJH3", "B00FITO44G", "B07XM5MHB3", "B00KLNCO5K", "B07W47N5ZH", "B0BFV7LR3F", "B0C277G9FW", "B07YJLPJ3R", "B075CJR281", "B00BB2O110", "B0BF5F88VT", "B07WWW8CXJ", "B07X9MHYPC", "B00AMA1QEC", "B006230L6C", "B002ACD6DO", "B01MRRZ3J1", "B01N0V86B2", "B00EKRB0C6", "B01M0YUEIZ"]}}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 490, "top_product_ids": ["B0CCD37DTM", "B01N22XTDC", "B01K8WCQLA", "B07WPFZ1C7", "B001V5J61M", "B07H3FP3R5", "B0B2XL9LPM", "B07MJGVHZY", "B09NZGBRH8", "B004I6E8NW", "B074RLSFKX", "B07Q9GB488", "B08S1SYPVJ", "B01GGOKIDM", "B091T7HZBV", "B00LTY074K", "B014EL42S6", "B0C8FCMS9S", "B092L7V5ZR", "B07N1PZFRQ"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "style", "question_scores": {"color": 0.1998589318692112, "style": 0.6351324788605625, "budget": 0.3317724799401196}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B0CCD37DTM", "score": 14.089893}, {"parent_asin": "B01N22XTDC", "score": 13.990905}, {"parent_asin": "B01K8WCQLA", "score": 13.779135}, {"parent_asin": "B07WPFZ1C7", "score": 13.329805}, {"parent_asin": "B001V5J61M", "score": 13.246427}, {"parent_asin": "B07H3FP3R5", "score": 13.243684}, {"parent_asin": "B0B2XL9LPM", "score": 13.237218}, {"parent_asin": "B07MJGVHZY", "score": 13.204546}, {"parent_asin": "B09NZGBRH8", "score": 13.168363}, {"parent_asin": "B004I6E8NW", "score": 13.144577}]}`
  - Layer `validate_response`: `{}`

#### Turn 5

- User: I don't have an additional preference for style.
- User act: `{"type": "NO_PREFERENCE", "attribute": "style", "values": [], "reason_code": "techjam:no_additional_preference", "references": [], "allowed_facts": [], "surface_text": "I don't have an additional preference for style."}`
- Agent: The current matches mainly differ by budget: under 25, 25 to 50, 50 to 100. Which do you prefer?
- Ask: `budget`
- Recommendations: `['B074RLSFKX', 'B07Q9GB488', 'B08S1SYPVJ', 'B01GGOKIDM', 'B091T7HZBV', 'B00LTY074K', 'B014EL42S6', 'B0C8FCMS9S', 'B092L7V5ZR', 'B07N1PZFRQ']`
- Layer candidate counts: `ranked_candidates=490`
- Agent latency: `95.287 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Socks & Hosiery Leg Warmers", "constraints": [], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Socks & Hosiery Leg Warmers", "intent_summary": "Socks & Hosiery Leg Warmers", "language": "en", "confidence": 0.97, "parser": "fallback", "fallback_reasons": []}}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 490, "top_product_ids": ["B074RLSFKX", "B07Q9GB488", "B08S1SYPVJ", "B01GGOKIDM", "B091T7HZBV", "B00LTY074K", "B014EL42S6", "B0C8FCMS9S", "B092L7V5ZR", "B07N1PZFRQ", "B07FBKYGG2", "B0CCD37DTM", "B07D4NZ324", "B01N22XTDC", "B01K8WCQLA", "B0C277G9FW", "B073DYJ2V1", "B07WWW8CXJ", "B0BFV7LR3F", "B0B79LH75D"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "budget", "question_scores": {"color": 0.23150671549274524, "budget": 0.35048054163102355}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B074RLSFKX", "score": 13.139257}, {"parent_asin": "B07Q9GB488", "score": 13.036805}, {"parent_asin": "B08S1SYPVJ", "score": 13.02547}, {"parent_asin": "B01GGOKIDM", "score": 13.010788}, {"parent_asin": "B091T7HZBV", "score": 12.988097}, {"parent_asin": "B00LTY074K", "score": 12.987623}, {"parent_asin": "B014EL42S6", "score": 12.980073}, {"parent_asin": "B0C8FCMS9S", "score": 12.978813}, {"parent_asin": "B092L7V5ZR", "score": 12.971285}, {"parent_asin": "B07N1PZFRQ", "score": 12.962903}]}`
  - Layer `validate_response`: `{}`

#### Turn 6

- User: I don't have an additional preference for budget.
- User act: `{"type": "NO_PREFERENCE", "attribute": "budget", "values": [], "reason_code": "techjam:no_additional_preference", "references": [], "allowed_facts": [], "surface_text": "I don't have an additional preference for budget."}`
- Agent: The current matches mainly differ by color: black, white, red. Which do you prefer?
- Ask: `color`
- Recommendations: `['B07FBKYGG2', 'B0CCD37DTM', 'B07D4NZ324', 'B01N22XTDC', 'B01K8WCQLA', 'B0C277G9FW', 'B073DYJ2V1', 'B07WWW8CXJ', 'B0BFV7LR3F', 'B0B79LH75D']`
- Layer candidate counts: `ranked_candidates=490`
- Agent latency: `88.223 ms`

  - Layer `understand_user`: `{}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 490, "top_product_ids": ["B07FBKYGG2", "B0CCD37DTM", "B07D4NZ324", "B01N22XTDC", "B01K8WCQLA", "B0C277G9FW", "B073DYJ2V1", "B07WWW8CXJ", "B0BFV7LR3F", "B0B79LH75D", "B07CZ84YFJ", "B08CXNN66T", "B006230L6C", "B08MXLQCQV", "B086BLWX9H", "B08GRZB5B8", "B081K9HCJ4", "B01N6ASNMN", "B09DCLDB53", "B07RM4HYFS"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "color", "question_scores": {"color": 0.24070477557222802}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B07FBKYGG2", "score": 12.960943}, {"parent_asin": "B0CCD37DTM", "score": 12.839893}, {"parent_asin": "B07D4NZ324", "score": 12.792336}, {"parent_asin": "B01N22XTDC", "score": 12.740905}, {"parent_asin": "B01K8WCQLA", "score": 12.529135}, {"parent_asin": "B0C277G9FW", "score": 12.513072}, {"parent_asin": "B073DYJ2V1", "score": 12.473415}, {"parent_asin": "B07WWW8CXJ", "score": 12.432822}, {"parent_asin": "B0BFV7LR3F", "score": 12.428885}, {"parent_asin": "B0B79LH75D", "score": 12.350058}]}`
  - Layer `validate_response`: `{}`

#### Turn 7

- User: I don't have an additional preference for color.
- User act: `{"type": "NO_PREFERENCE", "attribute": "color", "values": [], "reason_code": "techjam:no_additional_preference", "references": [], "allowed_facts": [], "surface_text": "I don't have an additional preference for color."}`
- Agent: Here are the closest matches for your current requirements.
- Ask: `None`
- Recommendations: `['B0CCD37DTM', 'B01N22XTDC', 'B01K8WCQLA', 'B07CZ84YFJ', 'B08CXNN66T', 'B006230L6C', 'B08MXLQCQV', 'B086BLWX9H', 'B08GRZB5B8', 'B081K9HCJ4']`
- Layer candidate counts: `ranked_candidates=490`
- Agent latency: `91.298 ms`

  - Layer `understand_user`: `{}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 490, "top_product_ids": ["B0CCD37DTM", "B01N22XTDC", "B01K8WCQLA", "B07CZ84YFJ", "B08CXNN66T", "B006230L6C", "B08MXLQCQV", "B086BLWX9H", "B08GRZB5B8", "B081K9HCJ4", "B01N6ASNMN", "B09DCLDB53", "B07RM4HYFS", "B07ZNQBNQP", "B0BD8CH3S8", "B09BB4X8ZY", "B08L7CPK1V", "B002ACD6DO", "B00WYEOZE2", "B01M0YUEIZ"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": null, "question_scores": {}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B0CCD37DTM", "score": 12.839893}, {"parent_asin": "B01N22XTDC", "score": 12.740905}, {"parent_asin": "B01K8WCQLA", "score": 12.529135}, {"parent_asin": "B07CZ84YFJ", "score": 12.335191}, {"parent_asin": "B08CXNN66T", "score": 12.326619}, {"parent_asin": "B006230L6C", "score": 12.292671}, {"parent_asin": "B08MXLQCQV", "score": 12.287339}, {"parent_asin": "B086BLWX9H", "score": 12.27759}, {"parent_asin": "B08GRZB5B8", "score": 12.26297}, {"parent_asin": "B081K9HCJ4", "score": 12.248462}]}`
  - Layer `validate_response`: `{}`

#### Turn 8

- User: Those options are not quite right yet. Ask me about one specific attribute.
- User act: `{"type": "INFORM", "attribute": null, "values": [], "reason_code": "techjam:ask_specific", "references": [], "allowed_facts": [], "surface_text": "Those options are not quite right yet. Ask me about one specific attribute."}`
- Agent: Here are the closest matches for your current requirements.
- Ask: `None`
- Recommendations: `['B0CCD37DTM', 'B01N22XTDC', 'B01K8WCQLA', 'B00LTY074K', 'B01N6ASNMN', 'B09DCLDB53', 'B07RM4HYFS', 'B07ZNQBNQP', 'B0BD8CH3S8', 'B09BB4X8ZY']`
- Layer candidate counts: `ranked_candidates=490`
- Agent latency: `97.13 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Socks & Hosiery Leg Warmers", "constraints": [{"field": "feature", "operator": "not_contains", "value": "quite right yet", "strength": "hard", "confidence": 0.88, "source_turn": 8}], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Socks & Hosiery Leg Warmers", "intent_summary": "Socks & Hosiery Leg Warmers", "language": "en", "confidence": 0.78, "parser": "fallback", "fallback_reasons": ["unresolved_negation", "reference_or_comparison", "no_structured_signal"]}, "semantic_fallback_reasons": ["unresolved_negation", "reference_or_comparison", "no_structured_signal"]}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{"active_constraints": [{"field": "feature", "operator": "not_contains", "value": "Closure closure", "strength": "hard", "confidence": 0.88, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "wool", "strength": "soft", "confidence": 0.9, "source_turn": 4}, {"field": "feature", "operator": "not_contains", "value": "quite right yet", "strength": "hard", "confidence": 0.88, "source_turn": 8}]}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 490, "top_product_ids": ["B0CCD37DTM", "B01N22XTDC", "B01K8WCQLA", "B00LTY074K", "B01N6ASNMN", "B09DCLDB53", "B07RM4HYFS", "B07ZNQBNQP", "B0BD8CH3S8", "B09BB4X8ZY", "B08L7CPK1V", "B002ACD6DO", "B00WYEOZE2", "B01M0YUEIZ", "B073PTNXC6", "B07YJLPJ3R", "B08LMMB4J2", "B074CHXZ27", "B08QRSXJ52", "B07R8WVBTW"]}}`
  - Layer `information_gain_question`: `{}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B0CCD37DTM", "score": 12.839893}, {"parent_asin": "B01N22XTDC", "score": 12.740905}, {"parent_asin": "B01K8WCQLA", "score": 12.529135}, {"parent_asin": "B00LTY074K", "score": 12.404289}, {"parent_asin": "B01N6ASNMN", "score": 12.240508}, {"parent_asin": "B09DCLDB53", "score": 12.238459}, {"parent_asin": "B07RM4HYFS", "score": 12.215721}, {"parent_asin": "B07ZNQBNQP", "score": 12.210691}, {"parent_asin": "B0BD8CH3S8", "score": 12.206812}, {"parent_asin": "B09BB4X8ZY", "score": 12.200774}]}`
  - Layer `validate_response`: `{}`

#### Turn 9

- User: Those options are not quite right yet. Ask me about one specific attribute.
- User act: `{"type": "INFORM", "attribute": null, "values": [], "reason_code": "techjam:ask_specific", "references": [], "allowed_facts": [], "surface_text": "Those options are not quite right yet. Ask me about one specific attribute."}`
- Agent: Here are the closest matches for your current requirements.
- Ask: `None`
- Recommendations: `['B0CCD37DTM', 'B01N22XTDC', 'B01K8WCQLA', 'B00LTY074K', 'B08L7CPK1V', 'B002ACD6DO', 'B00WYEOZE2', 'B01M0YUEIZ', 'B073PTNXC6', 'B07YJLPJ3R']`
- Layer candidate counts: `ranked_candidates=490`
- Agent latency: `95.63 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Socks & Hosiery Leg Warmers", "constraints": [{"field": "feature", "operator": "not_contains", "value": "quite right yet", "strength": "hard", "confidence": 0.88, "source_turn": 9}], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Socks & Hosiery Leg Warmers", "intent_summary": "Socks & Hosiery Leg Warmers", "language": "en", "confidence": 0.78, "parser": "fallback", "fallback_reasons": ["unresolved_negation", "reference_or_comparison", "no_structured_signal"]}}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 490, "top_product_ids": ["B0CCD37DTM", "B01N22XTDC", "B01K8WCQLA", "B00LTY074K", "B08L7CPK1V", "B002ACD6DO", "B00WYEOZE2", "B01M0YUEIZ", "B073PTNXC6", "B07YJLPJ3R", "B08LMMB4J2", "B074CHXZ27", "B08QRSXJ52", "B07R8WVBTW", "B0BGJ81PNQ", "B08FD89PBZ", "B08ZMT8S77", "B00H2SEM4S", "B07PGR9HSV", "B08H8HFKGC"]}}`
  - Layer `information_gain_question`: `{}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B0CCD37DTM", "score": 12.839893}, {"parent_asin": "B01N22XTDC", "score": 12.740905}, {"parent_asin": "B01K8WCQLA", "score": 12.529135}, {"parent_asin": "B00LTY074K", "score": 12.404289}, {"parent_asin": "B08L7CPK1V", "score": 12.191018}, {"parent_asin": "B002ACD6DO", "score": 12.186763}, {"parent_asin": "B00WYEOZE2", "score": 12.185246}, {"parent_asin": "B01M0YUEIZ", "score": 12.182131}, {"parent_asin": "B073PTNXC6", "score": 12.179506}, {"parent_asin": "B07YJLPJ3R", "score": 12.177327}]}`
  - Layer `validate_response`: `{}`

#### Turn 10

- User: Those options are not quite right yet. Ask me about one specific attribute.
- User act: `{"type": "INFORM", "attribute": null, "values": [], "reason_code": "techjam:ask_specific", "references": [], "allowed_facts": [], "surface_text": "Those options are not quite right yet. Ask me about one specific attribute."}`
- Agent: Here are the closest matches for your current requirements.
- Ask: `None`
- Recommendations: `['B0CCD37DTM', 'B01N22XTDC', 'B01K8WCQLA', 'B00LTY074K', 'B08LMMB4J2', 'B074CHXZ27', 'B08QRSXJ52', 'B07R8WVBTW', 'B0BGJ81PNQ', 'B08FD89PBZ']`
- Layer candidate counts: `ranked_candidates=490`
- Agent latency: `95.555 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Socks & Hosiery Leg Warmers", "constraints": [{"field": "feature", "operator": "not_contains", "value": "quite right yet", "strength": "hard", "confidence": 0.88, "source_turn": 10}], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Socks & Hosiery Leg Warmers", "intent_summary": "Socks & Hosiery Leg Warmers", "language": "en", "confidence": 0.78, "parser": "fallback", "fallback_reasons": ["unresolved_negation", "reference_or_comparison", "no_structured_signal"]}}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 490, "top_product_ids": ["B0CCD37DTM", "B01N22XTDC", "B01K8WCQLA", "B00LTY074K", "B08LMMB4J2", "B074CHXZ27", "B08QRSXJ52", "B07R8WVBTW", "B0BGJ81PNQ", "B08FD89PBZ", "B08ZMT8S77", "B00H2SEM4S", "B07PGR9HSV", "B08H8HFKGC", "B003OQTPJO", "B07X9MHYPC", "B07P2JV6B1", "B0BPMCJ1RD", "B077KRKQVS", "B07N3JH2L8"]}}`
  - Layer `information_gain_question`: `{}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B0CCD37DTM", "score": 12.839893}, {"parent_asin": "B01N22XTDC", "score": 12.740905}, {"parent_asin": "B01K8WCQLA", "score": 12.529135}, {"parent_asin": "B00LTY074K", "score": 12.404289}, {"parent_asin": "B08LMMB4J2", "score": 12.176446}, {"parent_asin": "B074CHXZ27", "score": 12.176361}, {"parent_asin": "B08QRSXJ52", "score": 12.174331}, {"parent_asin": "B07R8WVBTW", "score": 12.174249}, {"parent_asin": "B0BGJ81PNQ", "score": 12.172557}, {"parent_asin": "B08FD89PBZ", "score": 12.171299}]}`
  - Layer `validate_response`: `{}`

### 案例 2: realistic / realistic_0006_B01LG9U9UY

- 场景：`realistic`
- 成功：`False`；执行轮次：`10`
- 诊断分类：`insufficient_soft_matches`
- 诊断置信度：`medium`
- 选择理由：longest realistic failure
- 分析：硬约束可能满足，但软偏好匹配数量不足，需检查排序目标和偏好权重。
- 评测目标：`{"goal_type": "need_based", "goal_id": "realistic:B01LG9U9UY", "category": "Women", "hard_constraints": [{"attribute": "category", "values": ["Women"], "strength": "hard", "disclosed": false, "active": true, "source": "catalog", "relaxable": false}, {"attribute": "budget_max", "values": ["97.90"], "strength": "hard", "disclosed": false, "active": true, "source": "catalog", "relaxable": true}], "soft_preferences": [{"attribute": "brand", "values": ["Adoretex"], "strength": "soft", "disclosed": false, "active": true, "source": "catalog", "relaxable": true}, {"attribute": "feature", "values": ["Oxford Nylon"], "strength": "soft", "disclosed": false, "active": true, "source": "catalog", "relaxable": true}], "alternatives": {}, "min_soft_matches": 1, "source_dataset": "catalog_realistic"}`

#### Turn 1

- User: I'm looking for Women. A key preference is a budget up to $97.90.
- User act: `{"type": "INITIAL_REQUEST", "attribute": null, "values": [], "reason_code": null, "references": [], "allowed_facts": [{"attribute": "category", "values": ["Women"]}, {"attribute": "budget_max", "values": ["97.90"]}], "surface_text": null}`
- Agent: The current matches mainly differ by brand: generic, 55carat, uloveido. Which do you prefer?
- Ask: `brand`
- Recommendations: `['B09WDGKBY7', 'B09MKQ84JV', 'B09W53L858', 'B07VYVLNNJ', 'B00QJO2X9M', 'B0BM95M2QN', 'B07S7HS2LB', 'B081DWNZ1V', 'B07X9NBKLC', 'B00KHYH50W']`
- Layer candidate counts: `lexical_candidates=300, dense_candidates=200, attribute_candidates=200, fused_candidates=500, filtered_candidates=498, ranked_candidates=498`
- Agent latency: `88.887 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Women", "constraints": [{"field": "budget", "operator": "lte", "value": 97.9, "strength": "hard", "confidence": 0.9, "source_turn": 1}], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Women", "intent_summary": "Women", "language": "en", "confidence": 0.97, "parser": "fallback", "fallback_reasons": []}, "semantic_fallback_reasons": []}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{"active_constraints": [{"field": "budget", "operator": "lte", "value": 97.9, "strength": "hard", "confidence": 0.9, "source_turn": 1}], "superseded_constraints": []}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{"lexical_candidates": {"count": 300, "top_product_ids": ["B07XXM8DR7", "B09WDGKBY7", "B09W53L858", "B016MAPNKI", "B07VYVLNNJ", "B07B1PSYZ4", "B00QJO2X9M", "B0BGZWZY6M", "B09W9LD8MH", "B0BVRKLSVP", "B002HJHNGG", "B0C58BBJBN", "B004DSIKIO", "B07H41PH16", "B00HJ1GGOC", "B0074TLN2E", "B07S82CMY3", "B07T1289Y6", "B08RYFVMT6", "B00TSOA03G"]}, "dense_candidates": {"count": 200, "top_product_ids": ["B088NGXXFX", "B09JT1T7GJ", "B08F1SVXHW", "B09KG85H2N", "B0B2151QX6", "B09L1K3BJT", "B08K7JLDX1", "B07HXVSRD8", "B09KX2QR93", "B09LJ252D5", "B09K4CTM9C", "B09G6LDJXM", "B09YLMJ2DF", "B0BBJ1S5NN", "B0BDDWSPYR", "B09HT6W76Q", "B086755PW7", "B09W8QCYG7", "B0B7Q1MN1J", "B07LB2S44R"]}, "attribute_candidates": {"count": 200, "top_product_ids": ["B09MKQ84JV", "B079PHZ3MR", "B07SHJFS4T", "B097M69MDY", "B073X1MB4L", "B076L8JPC1", "B01KV6I4SM", "B09CQGSBTN", "B01B3EH51I", "B08G8DVCPL", "B07CDQTZS4", "B07KMXP7W9", "B07Q6YRB76", "B07CDD3P89", "B06XZ1GNZR", "B01EYHVNO6", "B08C2C2184", "B07J65JHLK", "B072LZJ7T6", "B00XTMHNUQ"]}}`
  - Layer `rrf_fusion`: `{"fused_candidates": {"count": 500, "top_product_ids": ["B07XXM8DR7", "B09WDGKBY7", "B09W53L858", "B016MAPNKI", "B07VYVLNNJ", "B07B1PSYZ4", "B00QJO2X9M", "B0BGZWZY6M", "B09W9LD8MH", "B0BVRKLSVP", "B002HJHNGG", "B0C58BBJBN", "B004DSIKIO", "B07H41PH16", "B00HJ1GGOC", "B0074TLN2E", "B07S82CMY3", "B07T1289Y6", "B08RYFVMT6", "B00TSOA03G"]}}`
  - Layer `constraint_filter`: `{"filtered_candidates": {"count": 498, "top_product_ids": ["B07XXM8DR7", "B09WDGKBY7", "B09W53L858", "B016MAPNKI", "B07VYVLNNJ", "B07B1PSYZ4", "B00QJO2X9M", "B0BGZWZY6M", "B09W9LD8MH", "B0BVRKLSVP", "B002HJHNGG", "B0C58BBJBN", "B004DSIKIO", "B07H41PH16", "B00HJ1GGOC", "B0074TLN2E", "B07S82CMY3", "B07T1289Y6", "B08RYFVMT6", "B00TSOA03G"]}}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B09MKQ84JV", "B09W53L858", "B07VYVLNNJ", "B00QJO2X9M", "B0BM95M2QN", "B07S7HS2LB", "B081DWNZ1V", "B07X9NBKLC", "B00KHYH50W", "B096BWW4KH", "B01ISB1PW4", "B0B4F395GL", "B07HJX2QZW", "B007O3SUBM", "B09C7RRQKK", "B0B49VLFQQ", "B07Q7F76FJ", "B09CQGSBTN", "B07QLX27NG"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "brand", "question_scores": {"material": 0.551000072274508, "color": 0.4082170497584659, "style": 0.573557941920703, "brand": 0.9797280767235863, "use_case": 0.3512784931656156}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 16.230605}, {"parent_asin": "B09MKQ84JV", "score": 14.643937}, {"parent_asin": "B09W53L858", "score": 14.589359}, {"parent_asin": "B07VYVLNNJ", "score": 14.34876}, {"parent_asin": "B00QJO2X9M", "score": 14.346898}, {"parent_asin": "B0BM95M2QN", "score": 14.067703}, {"parent_asin": "B07S7HS2LB", "score": 14.010972}, {"parent_asin": "B081DWNZ1V", "score": 13.950463}, {"parent_asin": "B07X9NBKLC", "score": 13.930753}, {"parent_asin": "B00KHYH50W", "score": 13.922661}]}`
  - Layer `validate_response`: `{"errors": []}`

#### Turn 2

- User: I'd prefer the brand Adoretex.
- User act: `{"type": "ANSWER_ATTRIBUTE", "attribute": "brand", "values": ["Adoretex"], "reason_code": null, "references": [], "allowed_facts": [{"attribute": "brand", "values": ["Adoretex"]}], "surface_text": null}`
- Agent: The current matches mainly differ by style: casual, vintage, formal. Which do you prefer?
- Ask: `style`
- Recommendations: `['B09WDGKBY7', 'B096BWW4KH', 'B01ISB1PW4', 'B0B4F395GL', 'B07HJX2QZW', 'B007O3SUBM', 'B09C7RRQKK', 'B0B49VLFQQ', 'B07Q7F76FJ', 'B09MKQ84JV']`
- Layer candidate counts: `ranked_candidates=498`
- Agent latency: `94.106 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Women", "constraints": [], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Women", "intent_summary": "Women", "language": "en", "confidence": 0.78, "parser": "fallback", "fallback_reasons": ["no_structured_signal"]}, "semantic_fallback_reasons": ["no_structured_signal"]}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B096BWW4KH", "B01ISB1PW4", "B0B4F395GL", "B07HJX2QZW", "B007O3SUBM", "B09C7RRQKK", "B0B49VLFQQ", "B07Q7F76FJ", "B09MKQ84JV", "B09CQGSBTN", "B09W53L858", "B07QLX27NG", "B07SHJFS4T", "B097M69MDY", "B07KMXP7W9", "B084Y7YLZS", "B00XTMHNUQ", "B00O0RRR50", "B07XCKD9DD"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "style", "question_scores": {"material": 0.609151606104314, "color": 0.4283869850635551, "style": 0.622439721067119, "use_case": 0.43063745436575734}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 14.980605}, {"parent_asin": "B096BWW4KH", "score": 13.920087}, {"parent_asin": "B01ISB1PW4", "score": 13.878804}, {"parent_asin": "B0B4F395GL", "score": 13.829052}, {"parent_asin": "B07HJX2QZW", "score": 13.824915}, {"parent_asin": "B007O3SUBM", "score": 13.808861}, {"parent_asin": "B09C7RRQKK", "score": 13.796405}, {"parent_asin": "B0B49VLFQQ", "score": 13.787324}, {"parent_asin": "B07Q7F76FJ", "score": 13.786237}, {"parent_asin": "B09MKQ84JV", "score": 13.393937}]}`
  - Layer `validate_response`: `{}`

#### Turn 3

- User: I don't have a preference for style; please use your judgment.
- User act: `{"type": "NO_PREFERENCE", "attribute": "style", "values": [], "reason_code": null, "references": [], "allowed_facts": [], "surface_text": null}`
- Agent: The current matches mainly differ by material: polyester, cotton, fabric. Which do you prefer?
- Ask: `material`
- Recommendations: `['B09WDGKBY7', 'B09MKQ84JV', 'B09CQGSBTN', 'B09W53L858', 'B07QLX27NG', 'B07SHJFS4T', 'B097M69MDY', 'B07KMXP7W9', 'B084Y7YLZS', 'B00XTMHNUQ']`
- Layer candidate counts: `ranked_candidates=498`
- Agent latency: `95.947 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Women", "constraints": [], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Women", "intent_summary": "Women", "language": "en", "confidence": 0.97, "parser": "fallback", "fallback_reasons": []}, "semantic_fallback_reasons": []}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B09MKQ84JV", "B09CQGSBTN", "B09W53L858", "B07QLX27NG", "B07SHJFS4T", "B097M69MDY", "B07KMXP7W9", "B084Y7YLZS", "B00XTMHNUQ", "B00O0RRR50", "B07XCKD9DD", "B081XCL6K5", "B07C8HQ63K", "B07VYVLNNJ", "B00QJO2X9M", "B01BP3N2SW", "B06X6MTK7H", "B06WP3B6QY", "B09WT8Y5JL"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "material", "question_scores": {"material": 0.6197205933086956, "color": 0.5336836956793104, "use_case": 0.48643635328427387}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 14.980605}, {"parent_asin": "B09MKQ84JV", "score": 13.393937}, {"parent_asin": "B09CQGSBTN", "score": 13.365843}, {"parent_asin": "B09W53L858", "score": 13.339359}, {"parent_asin": "B07QLX27NG", "score": 13.298204}, {"parent_asin": "B07SHJFS4T", "score": 13.27567}, {"parent_asin": "B097M69MDY", "score": 13.271074}, {"parent_asin": "B07KMXP7W9", "score": 13.208184}, {"parent_asin": "B084Y7YLZS", "score": 13.195426}, {"parent_asin": "B00XTMHNUQ", "score": 13.174858}]}`
  - Layer `validate_response`: `{}`

#### Turn 4

- User: I don't have a preference for material; please use your judgment.
- User act: `{"type": "NO_PREFERENCE", "attribute": "material", "values": [], "reason_code": null, "references": [], "allowed_facts": [], "surface_text": null}`
- Agent: The current matches mainly differ by color: black, white, red. Which do you prefer?
- Ask: `color`
- Recommendations: `['B09WDGKBY7', 'B09MKQ84JV', 'B09W53L858', 'B00O0RRR50', 'B07XCKD9DD', 'B081XCL6K5', 'B07C8HQ63K', 'B07VYVLNNJ', 'B00QJO2X9M', 'B01BP3N2SW']`
- Layer candidate counts: `ranked_candidates=498`
- Agent latency: `89.511 ms`

  - Layer `understand_user`: `{}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B09MKQ84JV", "B09W53L858", "B00O0RRR50", "B07XCKD9DD", "B081XCL6K5", "B07C8HQ63K", "B07VYVLNNJ", "B00QJO2X9M", "B01BP3N2SW", "B06X6MTK7H", "B06WP3B6QY", "B09WT8Y5JL", "B092FBXV41", "B074X6Q6GG", "B08RJ7GXNK", "B07YD5CZ5L", "B01NCOMSBK", "B08F23XYYX", "B0755MSMSV"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "color", "question_scores": {"color": 0.5848262034709275, "use_case": 0.5165858047086195}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 14.980605}, {"parent_asin": "B09MKQ84JV", "score": 13.393937}, {"parent_asin": "B09W53L858", "score": 13.339359}, {"parent_asin": "B00O0RRR50", "score": 13.169736}, {"parent_asin": "B07XCKD9DD", "score": 13.154075}, {"parent_asin": "B081XCL6K5", "score": 13.149944}, {"parent_asin": "B07C8HQ63K", "score": 13.149086}, {"parent_asin": "B07VYVLNNJ", "score": 13.09876}, {"parent_asin": "B00QJO2X9M", "score": 13.096898}, {"parent_asin": "B01BP3N2SW", "score": 13.095005}]}`
  - Layer `validate_response`: `{}`

#### Turn 5

- User: I don't have a preference for color; please use your judgment.
- User act: `{"type": "NO_PREFERENCE", "attribute": "color", "values": [], "reason_code": null, "references": [], "allowed_facts": [], "surface_text": null}`
- Agent: The current matches mainly differ by use case: work, winter, fitness. Which do you prefer?
- Ask: `use_case`
- Recommendations: `['B09WDGKBY7', 'B09MKQ84JV', 'B09W53L858', 'B07VYVLNNJ', 'B00QJO2X9M', 'B06X6MTK7H', 'B06WP3B6QY', 'B09WT8Y5JL', 'B092FBXV41', 'B074X6Q6GG']`
- Layer candidate counts: `ranked_candidates=498`
- Agent latency: `85.836 ms`

  - Layer `understand_user`: `{}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B09MKQ84JV", "B09W53L858", "B07VYVLNNJ", "B00QJO2X9M", "B06X6MTK7H", "B06WP3B6QY", "B09WT8Y5JL", "B092FBXV41", "B074X6Q6GG", "B08RJ7GXNK", "B07YD5CZ5L", "B01NCOMSBK", "B08F23XYYX", "B0755MSMSV", "B07B1PSYZ4", "B09W9LD8MH", "B0B7Q1MN1J", "B0C58BBJBN", "B086755PW7"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "use_case", "question_scores": {"use_case": 0.5800798376226517}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 14.980605}, {"parent_asin": "B09MKQ84JV", "score": 13.393937}, {"parent_asin": "B09W53L858", "score": 13.339359}, {"parent_asin": "B07VYVLNNJ", "score": 13.09876}, {"parent_asin": "B00QJO2X9M", "score": 13.096898}, {"parent_asin": "B06X6MTK7H", "score": 13.086368}, {"parent_asin": "B06WP3B6QY", "score": 13.076768}, {"parent_asin": "B09WT8Y5JL", "score": 13.062476}, {"parent_asin": "B092FBXV41", "score": 13.058352}, {"parent_asin": "B074X6Q6GG", "score": 13.057918}]}`
  - Layer `validate_response`: `{}`

#### Turn 6

- User: I don't have a preference for use_case; please use your judgment.
- User act: `{"type": "NO_PREFERENCE", "attribute": "use_case", "values": [], "reason_code": null, "references": [], "allowed_facts": [], "surface_text": null}`
- Agent: Here are the closest matches for your current requirements.
- Ask: `None`
- Recommendations: `['B09WDGKBY7', 'B09MKQ84JV', 'B09W53L858', 'B07VYVLNNJ', 'B00QJO2X9M', 'B08RJ7GXNK', 'B07YD5CZ5L', 'B01NCOMSBK', 'B08F23XYYX', 'B0755MSMSV']`
- Layer candidate counts: `ranked_candidates=498`
- Agent latency: `86.891 ms`

  - Layer `understand_user`: `{}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B09MKQ84JV", "B09W53L858", "B07VYVLNNJ", "B00QJO2X9M", "B08RJ7GXNK", "B07YD5CZ5L", "B01NCOMSBK", "B08F23XYYX", "B0755MSMSV", "B07B1PSYZ4", "B09W9LD8MH", "B0B7Q1MN1J", "B0C58BBJBN", "B086755PW7", "B09W8QCYG7", "B09TZTTP7H", "B09G6LDJXM", "B0BBJ1S5NN", "B0C1BT5862"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": null, "question_scores": {}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 14.980605}, {"parent_asin": "B09MKQ84JV", "score": 13.393937}, {"parent_asin": "B09W53L858", "score": 13.339359}, {"parent_asin": "B07VYVLNNJ", "score": 13.09876}, {"parent_asin": "B00QJO2X9M", "score": 13.096898}, {"parent_asin": "B08RJ7GXNK", "score": 13.053379}, {"parent_asin": "B07YD5CZ5L", "score": 13.051485}, {"parent_asin": "B01NCOMSBK", "score": 13.049578}, {"parent_asin": "B08F23XYYX", "score": 13.031738}, {"parent_asin": "B0755MSMSV", "score": 13.027107}]}`
  - Layer `validate_response`: `{}`

#### Turn 7

- User: Those options aren't quite right yet.
- User act: `{"type": "REJECT", "attribute": null, "values": [], "reason_code": null, "references": [], "allowed_facts": [], "surface_text": null}`
- Agent: Here are the closest matches for your current requirements.
- Ask: `None`
- Recommendations: `['B09WDGKBY7', 'B09MKQ84JV', 'B09W53L858', 'B07VYVLNNJ', 'B00QJO2X9M', 'B07B1PSYZ4', 'B09W9LD8MH', 'B0B7Q1MN1J', 'B0C58BBJBN', 'B086755PW7']`
- Layer candidate counts: `ranked_candidates=498`
- Agent latency: `81.426 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Women", "constraints": [], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Women", "intent_summary": "Women", "language": "en", "confidence": 0.78, "parser": "fallback", "fallback_reasons": ["reference_or_comparison", "no_structured_signal"]}, "semantic_fallback_reasons": ["reference_or_comparison", "no_structured_signal"]}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B09MKQ84JV", "B09W53L858", "B07VYVLNNJ", "B00QJO2X9M", "B07B1PSYZ4", "B09W9LD8MH", "B0B7Q1MN1J", "B0C58BBJBN", "B086755PW7", "B09W8QCYG7", "B09TZTTP7H", "B09G6LDJXM", "B0BBJ1S5NN", "B0C1BT5862", "B0BM95M2QN", "B09L1K3BJT", "B09YLMJ2DF", "B09JG9WZB7", "B0998M3FSN"]}}`
  - Layer `information_gain_question`: `{}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 14.980605}, {"parent_asin": "B09MKQ84JV", "score": 13.393937}, {"parent_asin": "B09W53L858", "score": 13.339359}, {"parent_asin": "B07VYVLNNJ", "score": 13.09876}, {"parent_asin": "B00QJO2X9M", "score": 13.096898}, {"parent_asin": "B07B1PSYZ4", "score": 13.012497}, {"parent_asin": "B09W9LD8MH", "score": 12.935344}, {"parent_asin": "B0B7Q1MN1J", "score": 12.883069}, {"parent_asin": "B0C58BBJBN", "score": 12.861021}, {"parent_asin": "B086755PW7", "score": 12.856584}]}`
  - Layer `validate_response`: `{}`

#### Turn 8

- User: Those aren't quite right. Can you show me some more options?
- User act: `{"type": "REQUEST_MORE_OPTIONS", "attribute": null, "values": [], "reason_code": null, "references": [], "allowed_facts": [], "surface_text": null}`
- Agent: Here are the closest matches for your current requirements.
- Ask: `None`
- Recommendations: `['B09WDGKBY7', 'B09MKQ84JV', 'B09W53L858', 'B07VYVLNNJ', 'B00QJO2X9M', 'B09W8QCYG7', 'B09TZTTP7H', 'B09G6LDJXM', 'B0BBJ1S5NN', 'B0C1BT5862']`
- Layer candidate counts: `ranked_candidates=498`
- Agent latency: `97.077 ms`

  - Layer `understand_user`: `{}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B09MKQ84JV", "B09W53L858", "B07VYVLNNJ", "B00QJO2X9M", "B09W8QCYG7", "B09TZTTP7H", "B09G6LDJXM", "B0BBJ1S5NN", "B0C1BT5862", "B0BM95M2QN", "B09L1K3BJT", "B09YLMJ2DF", "B09JG9WZB7", "B0998M3FSN", "B088NGXXFX", "B07S7HS2LB", "B09DY9Q2HN", "B092B6TJ57", "B096YB5VVY"]}}`
  - Layer `information_gain_question`: `{}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 14.980605}, {"parent_asin": "B09MKQ84JV", "score": 13.393937}, {"parent_asin": "B09W53L858", "score": 13.339359}, {"parent_asin": "B07VYVLNNJ", "score": 13.09876}, {"parent_asin": "B00QJO2X9M", "score": 13.096898}, {"parent_asin": "B09W8QCYG7", "score": 12.844409}, {"parent_asin": "B09TZTTP7H", "score": 12.840196}, {"parent_asin": "B09G6LDJXM", "score": 12.833609}, {"parent_asin": "B0BBJ1S5NN", "score": 12.828529}, {"parent_asin": "B0C1BT5862", "score": 12.824465}]}`
  - Layer `validate_response`: `{}`

#### Turn 9

- User: Those aren't quite right. Can you show me some more options?
- User act: `{"type": "REQUEST_MORE_OPTIONS", "attribute": null, "values": [], "reason_code": null, "references": [], "allowed_facts": [], "surface_text": null}`
- Agent: Here are the closest matches for your current requirements.
- Ask: `None`
- Recommendations: `['B09WDGKBY7', 'B09MKQ84JV', 'B09W53L858', 'B07VYVLNNJ', 'B00QJO2X9M', 'B0BM95M2QN', 'B09L1K3BJT', 'B09YLMJ2DF', 'B09JG9WZB7', 'B0998M3FSN']`
- Layer candidate counts: `ranked_candidates=498`
- Agent latency: `83.787 ms`

  - Layer `understand_user`: `{}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B09MKQ84JV", "B09W53L858", "B07VYVLNNJ", "B00QJO2X9M", "B0BM95M2QN", "B09L1K3BJT", "B09YLMJ2DF", "B09JG9WZB7", "B0998M3FSN", "B088NGXXFX", "B07S7HS2LB", "B09DY9Q2HN", "B092B6TJ57", "B096YB5VVY", "B09NC92ZY7", "B0874CHQYB", "B0BDDWSPYR", "B0BN6DBB4K", "B09HMQRZ69"]}}`
  - Layer `information_gain_question`: `{}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 14.980605}, {"parent_asin": "B09MKQ84JV", "score": 13.393937}, {"parent_asin": "B09W53L858", "score": 13.339359}, {"parent_asin": "B07VYVLNNJ", "score": 13.09876}, {"parent_asin": "B00QJO2X9M", "score": 13.096898}, {"parent_asin": "B0BM95M2QN", "score": 12.817703}, {"parent_asin": "B09L1K3BJT", "score": 12.781747}, {"parent_asin": "B09YLMJ2DF", "score": 12.776575}, {"parent_asin": "B09JG9WZB7", "score": 12.775428}, {"parent_asin": "B0998M3FSN", "score": 12.775282}]}`
  - Layer `validate_response`: `{}`

#### Turn 10

- User: Those aren't quite right. Can you show me some more options?
- User act: `{"type": "REQUEST_MORE_OPTIONS", "attribute": null, "values": [], "reason_code": null, "references": [], "allowed_facts": [], "surface_text": null}`
- Agent: Here are the closest matches for your current requirements.
- Ask: `None`
- Recommendations: `['B09WDGKBY7', 'B09MKQ84JV', 'B09W53L858', 'B07VYVLNNJ', 'B00QJO2X9M', 'B0BM95M2QN', 'B088NGXXFX', 'B07S7HS2LB', 'B09DY9Q2HN', 'B092B6TJ57']`
- Layer candidate counts: `ranked_candidates=498`
- Agent latency: `88.255 ms`

  - Layer `understand_user`: `{}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{}`
  - Layer `rrf_fusion`: `{}`
  - Layer `constraint_filter`: `{}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 498, "top_product_ids": ["B09WDGKBY7", "B09MKQ84JV", "B09W53L858", "B07VYVLNNJ", "B00QJO2X9M", "B0BM95M2QN", "B088NGXXFX", "B07S7HS2LB", "B09DY9Q2HN", "B092B6TJ57", "B096YB5VVY", "B09NC92ZY7", "B0874CHQYB", "B0BDDWSPYR", "B0BN6DBB4K", "B09HMQRZ69", "B081DWNZ1V", "B09WNBHSFN", "B0B61DF2F1", "B07X9NBKLC"]}}`
  - Layer `information_gain_question`: `{}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B09WDGKBY7", "score": 14.980605}, {"parent_asin": "B09MKQ84JV", "score": 13.393937}, {"parent_asin": "B09W53L858", "score": 13.339359}, {"parent_asin": "B07VYVLNNJ", "score": 13.09876}, {"parent_asin": "B00QJO2X9M", "score": 13.096898}, {"parent_asin": "B0BM95M2QN", "score": 12.817703}, {"parent_asin": "B088NGXXFX", "score": 12.770905}, {"parent_asin": "B07S7HS2LB", "score": 12.760972}, {"parent_asin": "B09DY9Q2HN", "score": 12.76094}, {"parent_asin": "B092B6TJ57", "score": 12.748955}]}`
  - Layer `validate_response`: `{}`

### 案例 3: techjam / public_0001

- 场景：`buying`
- 成功：`True`；执行轮次：`1`
- 诊断分类：`accepted_while_agent_asks`
- 诊断置信度：`medium`
- 选择理由：successful outcome with suspicious UX or simulator behavior
- 分析：The simulator accepted a recommendation while the Agent response still asked a clarification question.
- 评测目标：`{"goal_type": "target_product", "goal_id": "public_0001", "target_product_id": "B09PYB7B6Z", "category": "Jewelry Necklaces", "constraints": [{"attribute": "feature", "values": ["Material:alloy"], "strength": "hard", "disclosed": false, "active": true, "source": "techjam", "relaxable": false}, {"attribute": "feature", "values": ["Triple Moon Pentagram Symbol"], "strength": "hard", "disclosed": false, "active": true, "source": "techjam", "relaxable": false}, {"attribute": "feature", "values": ["The Triple Moon represents the Phases of the Moon which are linked to the three aspects of the Goddess and the phases of the Life of Women.The Pentagram representing the holistic r"], "strength": "soft", "disclosed": false, "active": true, "source": "techjam", "relaxable": true}, {"attribute": "feature", "values": ["♥ a special gift to your wife/mom/girlfriend/daughter/grandmother/best friend/kids on St. Valentine’s Day, Easter， Christmas day,Birthday,Anniversary ,Independence Day,Labor Day,Th"], "strength": "soft", "disclosed": false, "active": true, "source": "techjam", "relaxable": true}], "source_dataset": "techjam"}`

#### Turn 1

- User: I'm looking for Jewelry Necklaces. A key requirement is: Material:alloy.
- User act: `{"type": "INITIAL_REQUEST", "attribute": null, "values": [], "reason_code": "techjam:buying", "references": [], "allowed_facts": [], "surface_text": "I'm looking for Jewelry Necklaces. A key requirement is: Material:alloy."}`
- Agent: The current matches mainly differ by brand: konov, halawly, elobeth. Which do you prefer?
- Ask: `brand`
- Recommendations: `['B07RPV75CN', 'B0140NWUGE', 'B013Q214QW', 'B00VX0HZEK', 'B07ZFM77HB', 'B072PTLN1L', 'B09PYB7B6Z', 'B09LV2N6CM', 'B00RKW35S0', 'B0185S1S5Y']`
- Layer candidate counts: `lexical_candidates=300, dense_candidates=200, attribute_candidates=200, fused_candidates=500, filtered_candidates=500, ranked_candidates=500`
- Agent latency: `145.283 ms`

  - Layer `understand_user`: `{"semantic_patch": {"action": "add", "category": "Jewelry Necklaces", "constraints": [{"field": "feature", "operator": "contains", "value": "Material:alloy", "strength": "hard", "confidence": 1.0, "source_turn": 1}], "remove_fields": [], "no_preference": [], "retire_soft": false, "semantic_query": "Jewelry Necklaces Material:alloy", "intent_summary": "Jewelry Necklaces Material:alloy", "language": "en", "confidence": 0.97, "parser": "fallback", "fallback_reasons": []}, "semantic_fallback_reasons": []}`
  - Layer `validate_patch`: `{}`
  - Layer `update_state`: `{"active_constraints": [{"field": "feature", "operator": "contains", "value": "Material:alloy", "strength": "hard", "confidence": 1.0, "source_turn": 1}], "superseded_constraints": []}`
  - Layer `build_query`: `{}`
  - Layer `lexical_retrieve + dense_retrieve_fallback + attribute_retrieve`: `{"lexical_candidates": {"count": 300, "top_product_ids": ["B01EX670LS", "B07TS5Q2G6", "B013Q214QW", "B0140NWUGE", "B072PTLN1L", "B00VX0HZEK", "B07ZKZNMJ5", "B0185S1S5Y", "B07RPV75CN", "B086ZXZ8CX", "B09LV2N6CM", "B09JC4FKXL", "B010AI7T2S", "B00RKW35S0", "B01EYU2NNI", "B078Q424MT", "B07S85N55P", "B06Y69YN9M", "B078G14ZLQ", "B0B6FZH11D"]}, "dense_candidates": {"count": 200, "top_product_ids": ["B075KXNBNF", "B06XFNXFNC", "B08ZN1QY77", "B0836XNNCK", "B08HNCCGNQ", "B07CVVF3G2", "B096RL5D1N", "B07RPV75CN", "B08LNBNPBC", "B07J9YB8NP", "B07MZH7FKD", "B098QHFTF6", "B007RX1OX0", "B07JC23JLT", "B012CSZ7X2", "B00PYFO7XW", "B09QFQ7YWQ", "B087C5WYPK", "B07B4BX6FB", "B07KMCB7HM"]}, "attribute_candidates": {"count": 200, "top_product_ids": ["B0949GR8H9", "B09DXZYFFX", "B079PR44VQ", "B082BWDVJV", "B096LVYWCP", "B0BV7BBRS6", "B07SX1ZSNW", "B00X36350K", "B0BN7LV274", "B0BFVNY3SR", "B09X1V17QL", "B06XGBTLWL", "B00AMX599W", "B07NPWJVPS", "B07KY13JHG", "B01N6H7YTG", "B01N5FRHRD", "B09WYJ5BQG", "B0182OKCD0", "B07D8HX7TY"]}}`
  - Layer `rrf_fusion`: `{"fused_candidates": {"count": 500, "top_product_ids": ["B07TS5Q2G6", "B07RPV75CN", "B07ZKZNMJ5", "B0140NWUGE", "B00VX0HZEK", "B01EX670LS", "B09LV2N6CM", "B07ZFM77HB", "B06Y69YN9M", "B013Q214QW", "B09JC4FKXL", "B09C8H33CM", "B075KXNBNF", "B072PTLN1L", "B0B6FZH11D", "B00RKW35S0", "B010AI7T2S", "B01DS32E9U", "B07CVVF3G2", "B0185S1S5Y"]}}`
  - Layer `constraint_filter`: `{"filtered_candidates": {"count": 500, "top_product_ids": ["B07TS5Q2G6", "B07RPV75CN", "B07ZKZNMJ5", "B0140NWUGE", "B00VX0HZEK", "B01EX670LS", "B09LV2N6CM", "B07ZFM77HB", "B06Y69YN9M", "B013Q214QW", "B09JC4FKXL", "B09C8H33CM", "B075KXNBNF", "B072PTLN1L", "B0B6FZH11D", "B00RKW35S0", "B010AI7T2S", "B01DS32E9U", "B07CVVF3G2", "B0185S1S5Y"]}}`
  - Layer `rerank_fallback`: `{"ranked_candidates": {"count": 500, "top_product_ids": ["B07RPV75CN", "B0140NWUGE", "B013Q214QW", "B00VX0HZEK", "B07ZFM77HB", "B072PTLN1L", "B09PYB7B6Z", "B09LV2N6CM", "B00RKW35S0", "B0185S1S5Y", "B075KXNBNF", "B010AI7T2S", "B01DS32E9U", "B01LWYSGD6", "B07CVVF3G2", "B08FDCV863", "B01CKUTKY4", "B07CZ2TPVB", "B07S85N55P", "B06VTSYTS8"]}}`
  - Layer `information_gain_question`: `{"ask_attribute": "brand", "question_scores": {"material": 0.08649735207179274, "color": 0.24070477557222802, "style": 0.24074757088221224, "brand": 0.9980669251587667, "budget": 0.12114609454120741, "use_case": 0.17695614989903408}}`
  - Layer `build_response`: `{"recommendations": [{"parent_asin": "B07RPV75CN", "score": 16.007061}, {"parent_asin": "B0140NWUGE", "score": 15.976716}, {"parent_asin": "B013Q214QW", "score": 15.914985}, {"parent_asin": "B00VX0HZEK", "score": 15.815433}, {"parent_asin": "B07ZFM77HB", "score": 15.793269}, {"parent_asin": "B072PTLN1L", "score": 15.692476}, {"parent_asin": "B09PYB7B6Z", "score": 15.680367}, {"parent_asin": "B09LV2N6CM", "score": 15.597534}, {"parent_asin": "B00RKW35S0", "score": 15.596919}, {"parent_asin": "B0185S1S5Y", "score": 15.574826}]}`
  - Layer `validate_response`: `{"errors": []}`

## 全体会话问题标记

| 标记 | 次数 |
| --- | ---: |
| `accepted_while_agent_asks` | 253 |
| `answer_value_not_in_question_options` | 67 |
| `brand_first_question` | 300 |
| `constraint_filter_drop_observed_top20` | 1 |
| `fusion_loss_observed_top20` | 7 |
| `insufficient_soft_matches` | 3 |
| `ranking_underperformance_observed_top20` | 5 |
| `recommended_but_not_accepted` | 2 |
| `repeated_recommendation_set` | 8 |
| `response_or_top_k_loss_observed_top20` | 1 |
| `retrieval_not_observed_top20` | 20 |

所有标记均保存在 `comparisons/session_findings.jsonl`，代表性案例按固定优先级选择，不进行人工挑选。

## 解释边界

候选 trace 为每层 Top-20 的紧凑快照，因此“未观察到目标”不等同于目标绝对不在该层完整候选集合中。
Realistic 是 need-based acceptance，不是官方 TechJam 分数。
