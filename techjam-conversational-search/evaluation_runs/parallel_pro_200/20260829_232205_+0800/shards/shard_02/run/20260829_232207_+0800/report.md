# Traced Evaluation Report

Run: `20260829_232207_+0800`  
Model: `deepseek-v4-pro`  
LLM enabled: `True`  
Git commit: `d838e680fa7a44f5c64f34b8e3952685df195b90`

## Score

| Metric | Value |
|---|---:|
| Samples | 17 |
| Hit Rate@10 | 0.882353 |
| MRR | 0.266340 |
| MTTC | 3.176471 |
| Efficiency | 0.782353 |
| Technical Score | 0.677549 |
| Prompt tokens | 117816 |
| Completion tokens | 10182 |

## Scenario breakdown

| Scenario | Samples | Hit Rate | MRR | MTTC |
|---|---:|---:|---:|---:|
| browsing | 9 | 1.000000 | 0.354938 | 1.777778 |
| buying | 5 | 0.800000 | 0.176667 | 3.800000 |
| intent_override | 3 | 0.666667 | 0.150000 | 6.333333 |

## Representative conversations

One long successful session per scenario is shown below. Complete data
for every session is available in `sessions.jsonl`, `turns.jsonl`, and
`node_traces.jsonl`.

### public_0099 — browsing

Target: `B0971YMPCR` — Core 10 Women's Super Soft Fleece Straight Leg Jogger Sweatpant

Result: hit=`True`, first turn=`4`, rank=`6`

#### Turn 1

**User:** I'm looking for Active Pants Sweatpants, but I'm still exploring.

**Agent:** Do you have a preferred brand for the sweatpants?

- Asked attribute: `brand`
- Semantic query: `active pants sweatpants`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 488, "filtered_candidates": 488, "ranked_candidates": 488}`
- Active constraints: `[]`
- Top recommendations: `B07VNC4QY3`, `B00WHLI0Q6`, `B0716XGGKN`, `B08T61LQ9L`, `B084GFK3GR`

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

**Agent:** Do you have a preferred material for the sweatpants, like cotton or polyester?

- Asked attribute: `material`
- Semantic query: `active pants sweatpants`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 488}`
- Active constraints: `[]`
- Top recommendations: `B07VNC4QY3`, `B08R9RC4CF`, `B09SZ8TC1S`, `B08HRF95DQ`, `B07W73CSSH`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | no_preference, pending_question, question_history, intent_summary |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 3

**User:** For that, what matters is: cotton; 60% Cotton, 40% Polyester.

**Agent:** Do you have a preferred style for the sweatpants, like sport, casual, or vintage?

- Asked attribute: `style`
- Semantic query: `active pants sweatpants cotton blend`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "60% Cotton, 40% Polyester", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "polyester", "strength": "soft", "confidence": 0.9, "source_turn": 3}]`
- Top recommendations: `B084GFK3GR`, `B00PTT26HW`, `B08SMP2MMB`, `B07CGLPT17`, `B0C6542QR2`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | active_constraints, pending_question, question_history, semantic_query, intent_summary |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates, attribute_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, candidate_count, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 4

**User:** I don't have an additional preference for style.

**Agent:** What will you primarily use the sweatpants for, like fitness, running, or outdoor activities?

- Asked attribute: `use_case`
- Semantic query: `active pants sweatpants cotton blend`
- Target rank this turn: `6`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "60% Cotton, 40% Polyester", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "polyester", "strength": "soft", "confidence": 0.9, "source_turn": 3}]`
- Top recommendations: `B084GFK3GR`, `B07CGLPT17`, `B0716XGGKN`, `B00WHLI0Q6`, `B00PTT26HW`

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
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

### public_0027 — buying

Target: `B0858VDFDW` — Riders by Lee Indigo Women's Ultra Soft Denim Capri

Result: hit=`True`, first turn=`5`, rank=`3`

#### Turn 1

**User:** I'm looking for Women Jeans. A key requirement is: cotton.

**Agent:** Do you have a preferred brand for the women's jeans?

- Asked attribute: `brand`
- Semantic query: `women's jeans made of cotton`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B088GY1MK1`, `B07CJWHVQD`, `B09TSLQ3B5`, `B0BVFNRYFP`, `B07R5D462C`

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

**Agent:** Do you have a preferred style for the women's jeans?

- Asked attribute: `style`
- Semantic query: `women's jeans made of cotton`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B09VD2299T`, `B095VYFR42`, `B097M69MDY`, `B088GY1MK1`, `B0BY8NSJHQ`

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
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 3

**User:** I don't have an additional preference for style.

**Agent:** Do you have a budget in mind for the women's jeans?

- Asked attribute: `budget`
- Semantic query: `women's jeans made of cotton`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B088GY1MK1`, `B0BT8PMKPV`, `B0BQDTGHMZ`, `B001LRMX92`, `B074JMTF2Z`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | no_preference, pending_question, question_history, intent_summary |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 4

**User:** I don't have an additional preference for budget.

**Agent:** Here are some women's jeans in cotton that might interest you.

- Asked attribute: `None`
- Semantic query: `women's jeans made of cotton`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B088GY1MK1`, `B07CJWHVQD`, `B088THK3RH`, `B01B3EH51I`, `B072HKPZD5`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | no_preference, pending_question, question_history, intent_summary |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | ask_attribute, question_scores, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 5

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** What will you primarily use these jeans for? For example, work, fitness, or winter?

- Asked attribute: `use_case`
- Semantic query: `women's jeans made of cotton`
- Target rank this turn: `3`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B088GY1MK1`, `B07CJWHVQD`, `B0858VDFDW` **(target)**, `B00J2WHI2U`, `B00K5PAYOM`

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
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

### public_0003 — intent_override

Target: `B09YMTWDXJ` — Casio Men's Wrist Watch AQ-800E-7A

Result: hit=`True`, first turn=`5`, rank=`5`

#### Turn 1

**User:** I'm looking for Watches Wrist Watches. Stainless Steel Band

**Agent:** Do you have a preferred brand for the watch?

- Asked attribute: `brand`
- Semantic query: `stainless steel band wrist watch`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Stainless Steel Band", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B0196A59GY`, `B0B7QFCWPX`, `B000GX3IIM`, `B0714R2TL3`, `B09YMTWDXJ` **(target)**

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

**Agent:** Do you have a preferred color for the watch?

- Asked attribute: `color`
- Semantic query: `stainless steel band wrist watch`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Stainless Steel Band", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B0196A59GY`, `B0B7QFCWPX`, `B07PQK7WC4`, `B07W22TLGG`, `B07P15K574`

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
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 3

**User:** Actually, ignore my earlier preference. What I need is: Water Resistant.

**Agent:** Do you have a preferred style for the watch?

- Asked attribute: `style`
- Semantic query: `water resistant wrist watch`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Water Resistant", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B076M5G1DC`, `B08GHDQLPK`, `B07Q2CRDLC`, `B01CEBBO2U`, `B0BJVWCSKQ`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | active_constraints, superseded_constraints, question_history, intent_changed, semantic_query, intent_summary, recommended_asins |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 4

**User:** I don't have an additional preference for style.

**Agent:** Here are some water resistant watches you might like: NORTH EDGE Digital Watches Mens Military Sport Watch, Armitron Sport Retro Men's Digital Bracelet Watch, and Citizen Quartz Womens Watch.

- Asked attribute: `None`
- Semantic query: `water resistant wrist watch`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Water Resistant", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B076M5G1DC`, `B0BJVX7YKG`, `B09Z31F3PD`, `B01LWOGORL`, `B007R9WURS`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | no_preference, pending_question, question_history, intent_changed |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | ask_attribute, question_scores, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 5

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** What is your budget for the watch?

- Asked attribute: `budget`
- Semantic query: `water resistant wrist watch`
- Target rank this turn: `5`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Water Resistant", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B076M5G1DC`, `B08GHDQLPK`, `B09NB67R3X`, `B092RF1J64`, `B09YMTWDXJ` **(target)**

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
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |
