# Traced Evaluation Report

Run: `20260829_232207_+0800`  
Model: `deepseek-v4-pro`  
LLM enabled: `True`  
Git commit: `d838e680fa7a44f5c64f34b8e3952685df195b90`

## Score

| Metric | Value |
|---|---:|
| Samples | 16 |
| Hit Rate@10 | 0.875000 |
| MRR | 0.270040 |
| MTTC | 3.187500 |
| Efficiency | 0.781250 |
| Technical Score | 0.674762 |
| Prompt tokens | 114353 |
| Completion tokens | 10043 |

## Scenario breakdown

| Scenario | Samples | Hit Rate | MRR | MTTC |
|---|---:|---:|---:|---:|
| browsing | 8 | 0.750000 | 0.195139 | 4.250000 |
| buying | 7 | 1.000000 | 0.365646 | 1.428571 |
| intent_override | 1 | 1.000000 | 0.200000 | 7.000000 |

## Representative conversations

One long successful session per scenario is shown below. Complete data
for every session is available in `sessions.jsonl`, `turns.jsonl`, and
`node_traces.jsonl`.

### public_0153 — browsing

Target: `B07BMJ77FR` — Susanny High Heel Boots for Women,Womens Platform Boot Heels Sexy Round Toe Lace UP High Heels Mid Calf Boots

Result: hit=`True`, first turn=`6`, rank=`5`

#### Turn 1

**User:** I'm looking for Boots Ankle & Bootie, but I'm still exploring.

**Agent:** Do you have a preferred style, like casual, vintage, or formal?

- Asked attribute: `style`
- Semantic query: `ankle boots and booties`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 451, "filtered_candidates": 451, "ranked_candidates": 451}`
- Active constraints: `[]`
- Top recommendations: `B07GB2KZGK`, `B097XSNQQN`, `B07XP59G1X`, `B073X8Y8LW`, `B073X9SVPT`

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

**User:** I don't have an additional preference for style.

**Agent:** Do you have a preferred brand, like Premier Standard, Dream Pairs, or Kaptene?

- Asked attribute: `brand`
- Semantic query: `ankle boots and booties`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 451}`
- Active constraints: `[]`
- Top recommendations: `B07GB2KZGK`, `B07QS9WXHD`, `B01N9TF9F0`, `B07G2MQ8MW`, `B015DFPMFE`

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

**User:** I don't have an additional preference for brand.

**Agent:** Do you have a specific use case in mind, like winter, work, or outdoor?

- Asked attribute: `use_case`
- Semantic query: `ankle boots and booties`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 451}`
- Active constraints: `[]`
- Top recommendations: `B07GB2KZGK`, `B097XSNQQN`, `B0C7L14F4T`, `B07H24XVP7`, `B072C8T9M5`

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

**User:** I don't have an additional preference for use_case.

**Agent:** Here are some ankle boots you might like: Aukusor Women's Ankle Boots, DREAM PAIRS Platform Boots, and Chellysun Wedge Heel Booties.

- Asked attribute: `None`
- Semantic query: `ankle boots and booties`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 451}`
- Active constraints: `[]`
- Top recommendations: `B07GB2KZGK`, `B097XSNQQN`, `B07XP59G1X`, `B07HSYYG89`, `B0BGQBLKY8`

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

**Agent:** Do you have a preferred material, like leather, polyester, or fabric?

- Asked attribute: `material`
- Semantic query: `ankle boots and booties`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 451}`
- Active constraints: `[]`
- Top recommendations: `B07GB2KZGK`, `B097XSNQQN`, `B07XP59G1X`, `B072FPFPDC`, `B07T6JKQW8`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_usage |
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

#### Turn 6

**User:** For that, what matters is: leather; PU Leather.

**Agent:** Here are some ankle boots that match your material preference: Padgene Women's PU Leather Platform Wedgie Sneakers, Coshare Women's Fashion Leather PU Strappy Upper Ankle High Chunky Heel Booties, and Premier Standard Women's Round Toe Faux Suede Stacked Heel Western Ankle Bootie.

- Asked attribute: `None`
- Semantic query: `ankle boots and booties in leather or PU leather`
- Target rank this turn: `5`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 495, "filtered_candidates": 495, "ranked_candidates": 495}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "leather", "strength": "hard", "confidence": 1.0, "source_turn": 6}, {"field": "material", "operator": "contains", "value": "PU Leather", "strength": "hard", "confidence": 1.0, "source_turn": 6}]`
- Top recommendations: `B08T1K6N3G`, `B015DFPMFE`, `B07DP8QK3W`, `B07DHZY11W`, `B07BMJ77FR` **(target)**

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_usage |
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

### public_0009 — buying

Target: `B07GXHPWTJ` — Angel Barcelo Roomy Fashion Hobo Womens Handbags Ladies Purse Satchel Shoulder Bags Tote Washed Leather Bag

Result: hit=`True`, first turn=`2`, rank=`2`

#### Turn 1

**User:** I'm looking for Handbags & Wallets Totes. A key requirement is: leather.

**Agent:** Do you have a preferred brand for the leather tote?

- Asked attribute: `brand`
- Semantic query: `leather tote bag`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "leather", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B076FTW4HQ`, `B086YMXTQL`, `B08CVGMSFW`, `B07512ZTXZ`, `B08ZN8Y2W1`

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

**Agent:** Do you have a preferred style for the leather tote? For example, casual, vintage, or formal?

- Asked attribute: `style`
- Semantic query: `leather tote bag`
- Target rank this turn: `2`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "leather", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B076FTW4HQ`, `B07GXHPWTJ` **(target)**, `B075LPBBP6`, `B086YMXTQL`, `B07JQPGXZJ`

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

### public_0177 — intent_override

Target: `B07HV9WW6Q` — ANIXAY Women's Short/Long Sleeve Henley Button up T Shirt Casual Basic Tops Blouse

Result: hit=`True`, first turn=`7`, rank=`5`

#### Turn 1

**User:** I'm looking for Tops Tees & Blouses. Button closure

**Agent:** Do you have a preferred material, like cotton or polyester?

- Asked attribute: `material`
- Semantic query: `Tops Tees & Blouses with button closure`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Button closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07XKGWK4G`, `B07QPN8D6X`, `B004OCCBFC`, `B082YTPSJK`, `B07QQVGHGP`

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

**User:** For that, what matters is: cotton; Cotton, Rayon.

**Agent:** Here are some tops with button closure in cotton or cotton-rayon blends.

- Asked attribute: `None`
- Semantic query: `Tops Tees & Blouses with button closure made of cotton or cotton rayon blend`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Button closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 2}, {"field": "material", "operator": "contains", "value": "Cotton, Rayon", "strength": "hard", "confidence": 1.0, "source_turn": 2}, {"field": "material", "operator": "contains", "value": "rayon", "strength": "soft", "confidence": 0.9, "source_turn": 2}]`
- Top recommendations: `B07M7B5FFS`, `B006HSDW0Y`, `B07HV9WW6Q` **(target)**, `B08T8WGSZC`, `B07GJZ1W8P`

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
| information_gain_question | ask_attribute, question_scores, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 3

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** Do you have a preferred brand, like Lee or Ekouaer?

- Asked attribute: `brand`
- Semantic query: `Tops Tees & Blouses with button closure made of cotton or cotton rayon blend`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Button closure", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 2}, {"field": "material", "operator": "contains", "value": "Cotton, Rayon", "strength": "hard", "confidence": 1.0, "source_turn": 2}, {"field": "material", "operator": "contains", "value": "rayon", "strength": "soft", "confidence": 0.9, "source_turn": 2}]`
- Top recommendations: `B07M7B5FFS`, `B006HSDW0Y`, `B07HV9WW6Q` **(target)**, `B08T8WGSZC`, `B07K4PLJ66`

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

**User:** Actually, ignore my earlier preference. What I need is: cotton.

**Agent:** Do you have a preferred style, like casual, vintage, or formal?

- Asked attribute: `style`
- Semantic query: `Tops Tees & Blouses with button closure made of cotton`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B07K13FGJ2`, `B089NH22B5`, `B091DWXPZN`, `B07XRB2C63`, `B09VS3CGMZ`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state | active_constraints, superseded_constraints, question_history, intent_changed, semantic_query, intent_summary, recommended_asins |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates, attribute_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 5

**User:** I don't have an additional preference for style.

**Agent:** Here are some tops with button closure in cotton.

- Asked attribute: `None`
- Semantic query: `Tops Tees & Blouses with button closure made of cotton`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B07K13FGJ2`, `B07ZGPFJZX`, `B01FU1JA2W`, `B07WD1PBC6`, `B07QQVGHGP`

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

#### Turn 6

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** What will you use this top for? For example, work, winter, or outdoor?

- Asked attribute: `use_case`
- Semantic query: `Tops Tees & Blouses with button closure made of cotton`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B07K13FGJ2`, `B089NH22B5`, `B091DWXPZN`, `B07XRB2C63`, `B07P83K23S`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_usage |
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

#### Turn 7

**User:** I don't have an additional preference for use_case.

**Agent:** Do you have a preferred color, like black, blue, or white?

- Asked attribute: `color`
- Semantic query: `Tops Tees & Blouses with button closure made of cotton`
- Target rank this turn: `5`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B07K13FGJ2`, `B089NH22B5`, `B091DWXPZN`, `B07XRB2C63`, `B07HV9WW6Q` **(target)**

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_usage |
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
