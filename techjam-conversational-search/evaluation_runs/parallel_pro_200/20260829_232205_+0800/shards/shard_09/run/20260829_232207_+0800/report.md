# Traced Evaluation Report

Run: `20260829_232207_+0800`  
Model: `deepseek-v4-pro`  
LLM enabled: `True`  
Git commit: `d838e680fa7a44f5c64f34b8e3952685df195b90`

## Score

| Metric | Value |
|---|---:|
| Samples | 16 |
| Hit Rate@10 | 0.812500 |
| MRR | 0.328274 |
| MTTC | 3.937500 |
| Efficiency | 0.706250 |
| Technical Score | 0.645982 |
| Prompt tokens | 146204 |
| Completion tokens | 14550 |

## Scenario breakdown

| Scenario | Samples | Hit Rate | MRR | MTTC |
|---|---:|---:|---:|---:|
| browsing | 1 | 1.000000 | 1.000000 | 1.000000 |
| buying | 10 | 0.900000 | 0.265238 | 2.900000 |
| intent_override | 5 | 0.600000 | 0.320000 | 6.600000 |

## Representative conversations

One long successful session per scenario is shown below. Complete data
for every session is available in `sessions.jsonl`, `turns.jsonl`, and
`node_traces.jsonl`.

### public_0070 — browsing

Target: `B010LVBVKA` — Travel Neck Wallet with RFID Blocking – Passport Holder Neck Pouch to Keep Your Cash And Documents Safe – Get Peace Of Mind When Traveling

Result: hit=`True`, first turn=`1`, rank=`1`

#### Turn 1

**User:** I'm looking for Travel Accessories Travel Wallets, but I'm still exploring.

**Agent:** Do you have a preferred brand for travel wallets?

- Asked attribute: `brand`
- Semantic query: `travel wallet for organizing travel documents and cards`
- Target rank this turn: `1`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B010LVBVKA` **(target)**, `B07GJ9TJ9Z`, `B078H9ZCLN`, `B07W4PP3M9`, `B099FJP9KP`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state | category, active_constraints, superseded_constraints, no_preference, pending_question, question_history, intent_changed, semantic_query, intent_summary, user_language, retrieval_attempt, constraints_relaxed |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates, attribute_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, candidate_count, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins, errors |

### public_0118 — buying

Target: `B09M72C8PG` — Angerella Women Vintage Polka Dot High Waisted Bathing Suits Bikini Set

Result: hit=`True`, first turn=`5`, rank=`7`

#### Turn 1

**User:** I'm looking for Bikinis Sets. A key requirement is: nylon.

**Agent:** Do you have a preferred brand for the bikini set?

- Asked attribute: `brand`
- Semantic query: `nylon bikini sets`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "nylon", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07WDV3SGZ`, `B07RG5ZJRT`, `B09GC1ZHD2`, `B07QR1MM48`, `B087NL2ZHP`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state | category, active_constraints, superseded_constraints, no_preference, pending_question, question_history, intent_changed, semantic_query, intent_summary, user_language, retrieval_attempt, constraints_relaxed |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates, attribute_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, candidate_count, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins, errors |

#### Turn 2

**User:** I don't have an additional preference for brand.

**Agent:** Here are some bikini sets in nylon that might interest you: ZAFUL Women's Solid Spaghetti Strap Bralette Bikini Set, Lemonfish Women Flounce High Waisted Bikini, and Yii ouneey Plus Size Swimsuit.

- Asked attribute: `None`
- Semantic query: `nylon bikini sets`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "nylon", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07WDV3SGZ`, `B07RG5ZJRT`, `B08DF9F8KG`, `B08VWPKZZL`, `B09GC1ZHD2`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | no_preference, pending_question, question_history |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | ask_attribute, question_scores, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 3

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** Do you have a preferred color for the bikini set?

- Asked attribute: `color`
- Semantic query: `nylon bikini sets`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "nylon", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07WDV3SGZ`, `B07RG5ZJRT`, `B09GC1ZHD2`, `B0BN2SZCY4`, `B08NJLMJFM`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state |  |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 4

**User:** I don't have an additional preference for color.

**Agent:** Do you have a preferred style for the bikini set? For example, vintage, sport, or formal?

- Asked attribute: `style`
- Semantic query: `nylon bikini sets`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "nylon", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07WDV3SGZ`, `B07RG5ZJRT`, `B09GC1ZHD2`, `B07QR1MM48`, `B087NL2ZHP`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state | no_preference, pending_question, question_history |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 5

**User:** I don't have an additional preference for style.

**Agent:** Here are some nylon bikini sets you might like: ZAFUL Women's Solid Spaghetti Strap Bralette Bikini Set, Lemonfish Women Flounce High Waisted Bikini, and Kanu Surf Girls' Alania Flounce Bikini.

- Asked attribute: `None`
- Semantic query: `nylon bikini sets`
- Target rank this turn: `7`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "nylon", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07WDV3SGZ`, `B07RG5ZJRT`, `B09GC1ZHD2`, `B07QR1MM48`, `B087NL2ZHP`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | no_preference, pending_question, question_history |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | ask_attribute, question_scores, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

### public_0046 — intent_override

Target: `B0B42PVX1F` — Wool Plus Size Thigh High Socks For Thick Thighs- Extra Long Womens Warm Cable Knit Over Knee Stockings Leg Warmers

Result: hit=`True`, first turn=`4`, rank=`1`

#### Turn 1

**User:** I'm looking for Socks & Hosiery Leg Warmers. No Closure closure

**Agent:** Do you have a material preference, like spandex, cotton, or polyester?

- Asked attribute: `material`
- Semantic query: `leg warmers without closure`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "No Closure closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "feature", "operator": "contains", "value": "warm", "strength": "soft", "confidence": 0.84, "source_turn": 1}]`
- Top recommendations: `B091DQRRQF`, `B0B42PVX1F` **(target)**, `B0BGCL426M`, `B00LLQ246A`, `B08P8SHDWB`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state | category, active_constraints, superseded_constraints, no_preference, pending_question, question_history, intent_changed, semantic_query, intent_summary, user_language, retrieval_attempt, constraints_relaxed |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates, attribute_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, candidate_count, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins, errors |

#### Turn 2

**User:** For that, what matters is: wool; 44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester.

**Agent:** Based on your material preference, here are some leg warmers that might work for you.

- Asked attribute: `None`
- Semantic query: `wool leg warmers without closure`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 279, "ranked_candidates": 279}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "No Closure closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "feature", "operator": "contains", "value": "warm", "strength": "soft", "confidence": 0.84, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester", "strength": "hard", "confidence": 1.0, "source_turn": 2}, {"field": "material", "operator": "not_contains", "value": "Wool", "strength": "hard", "confidence": 0.88, "source_turn": 2}, {"field": "material", "operator": "contains", "value": "cotton", "strength": "soft", "confidence": 0.9, "source_turn": 2}, {"field": "material", "operator": "contains", "value": "polyester", "strength": "soft", "confidence": 0.9, "source_turn": 2}]`
- Top recommendations: `B07NJ7X594`, `B09HQ4Y91F`, `B0848HKCF5`, `B0CBKVT8WQ`, `B09KMT3PT1`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state | active_constraints, pending_question, question_history, semantic_query, intent_summary |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates, attribute_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | ask_attribute, question_scores, question_options, candidate_count, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 3

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** What style do you prefer, like sport, casual, or formal?

- Asked attribute: `style`
- Semantic query: `wool leg warmers without closure`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 279}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "No Closure closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "feature", "operator": "contains", "value": "warm", "strength": "soft", "confidence": 0.84, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "44% Acrylic, 28% Cotton, 20% Merino Wool, 8% Polyester", "strength": "hard", "confidence": 1.0, "source_turn": 2}, {"field": "material", "operator": "not_contains", "value": "Wool", "strength": "hard", "confidence": 0.88, "source_turn": 2}, {"field": "material", "operator": "contains", "value": "cotton", "strength": "soft", "confidence": 0.9, "source_turn": 2}, {"field": "material", "operator": "contains", "value": "polyester", "strength": "soft", "confidence": 0.9, "source_turn": 2}]`
- Top recommendations: `B07NJ7X594`, `B09HQ4Y91F`, `B00LLQ246A`, `B01CYA9FR2`, `B07PRQ58XV`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state |  |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 4

**User:** Actually, ignore my earlier preference. What I need is: wool.

**Agent:** Do you have a brand preference, like Smartwool, Moon Wood, or Faybox?

- Asked attribute: `brand`
- Semantic query: `wool leg warmers without closure`
- Target rank this turn: `1`
- Candidate counts: `{"lexical_candidates": 300, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "wool", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B0B42PVX1F` **(target)**, `B07XM5MHB3`, `B07RM4HYFS`, `B07W47N5ZH`, `B006230L6C`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state | active_constraints, superseded_constraints, question_history, intent_changed, intent_summary, recommended_asins |
| build_query | lexical_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, attribute_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, candidate_count, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |
