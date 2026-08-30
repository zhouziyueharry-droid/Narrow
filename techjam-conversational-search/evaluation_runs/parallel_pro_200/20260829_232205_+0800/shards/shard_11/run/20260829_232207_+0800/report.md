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
| MRR | 0.401116 |
| MTTC | 3.750000 |
| Efficiency | 0.725000 |
| Technical Score | 0.702835 |
| Prompt tokens | 137367 |
| Completion tokens | 12729 |

## Scenario breakdown

| Scenario | Samples | Hit Rate | MRR | MTTC |
|---|---:|---:|---:|---:|
| boundary | 2 | 1.000000 | 0.750000 | 4.000000 |
| browsing | 5 | 1.000000 | 0.428571 | 2.600000 |
| buying | 5 | 0.800000 | 0.460000 | 3.000000 |
| intent_override | 4 | 0.750000 | 0.118750 | 6.000000 |

## Representative conversations

One long successful session per scenario is shown below. Complete data
for every session is available in `sessions.jsonl`, `turns.jsonl`, and
`node_traces.jsonl`.

### public_0192 — boundary

Target: `B0C62MF2HV` — adidas unisex adult Adilette Clog Slide Sandal, Pink Tint/White/Pink Tint, 12 Women Men US

Result: hit=`True`, first turn=`6`, rank=`2`

#### Turn 1

**User:** I'm looking for Athletic Sport Sandals & Slides, but I'm still exploring.

**Agent:** Do you have a preferred brand for your sport sandals?

- Asked attribute: `brand`
- Semantic query: `athletic sport sandals and slides`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 429, "filtered_candidates": 429, "ranked_candidates": 429}`
- Active constraints: `[{"field": "style", "operator": "contains", "value": "sport", "strength": "soft", "confidence": 0.86, "source_turn": 1}]`
- Top recommendations: `B08S6MBMDK`, `B08X118F96`, `B098D763TL`, `B07H8WRX4M`, `B01H0N1T36`

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

**User:** I don't have a preference for brand; please use your judgment.

**Agent:** Do you have a preference for the material of the sandals? For example, leather, fabric, or polyester?

- Asked attribute: `material`
- Semantic query: `athletic sport sandals and slides`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 429}`
- Active constraints: `[{"field": "style", "operator": "contains", "value": "sport", "strength": "soft", "confidence": 0.86, "source_turn": 1}]`
- Top recommendations: `B08S6MBMDK`, `B08X118F96`, `B00LH91BV0`, `B08F51YN5Q`, `B01GSY5RMM`

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

**User:** I don't have an additional preference for material.

**Agent:** Do you have a specific use case in mind, like outdoor activities, running, or winter wear?

- Asked attribute: `use_case`
- Semantic query: `athletic sport sandals and slides`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 429}`
- Active constraints: `[{"field": "style", "operator": "contains", "value": "sport", "strength": "soft", "confidence": 0.86, "source_turn": 1}]`
- Top recommendations: `B08S6MBMDK`, `B08X118F96`, `B075YR29MP`, `B07FK8DK1N`, `B07RC122XL`

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

**Agent:** Based on your interest in sport sandals, here are some great options: riemot Open Toe Sport Sandals, Tuboom Women Cork Footbed Sandals, and Quiksilver Men's Molokai Art 3 Point Sandal Flip-Flop.

- Asked attribute: `None`
- Semantic query: `athletic sport sandals and slides`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 429}`
- Active constraints: `[{"field": "style", "operator": "contains", "value": "sport", "strength": "soft", "confidence": 0.86, "source_turn": 1}]`
- Top recommendations: `B08S6MBMDK`, `B08X118F96`, `B0962V3P3F`, `B098D763TL`, `B008J5G6JC`

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

**Agent:** Do you have a color preference for your sport sandals? For example, black, pink, or white?

- Asked attribute: `color`
- Semantic query: `athletic sport sandals and slides`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 429}`
- Active constraints: `[{"field": "style", "operator": "contains", "value": "sport", "strength": "soft", "confidence": 0.86, "source_turn": 1}]`
- Top recommendations: `B08S6MBMDK`, `B08X118F96`, `B098D763TL`, `B071S8CSD8`, `B0916NM6JB`

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

#### Turn 6

**User:** For that, what matters is: color: pink.

**Agent:** Here are some pink sport sandals that match your preference: SAGUARO Mens Womens Sports Sandal Closed Toe Sandals Non Slip Hiking Sandal Outdoor Walking Summer Water Shoes Pink, and adidas unisex adult Adilette Clog Slide Sandal in Pink Tint.

- Asked attribute: `None`
- Semantic query: `pink athletic sport sandals and slides`
- Target rank this turn: `2`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "style", "operator": "contains", "value": "sport", "strength": "soft", "confidence": 0.86, "source_turn": 1}, {"field": "color", "operator": "contains", "value": "color: pink", "strength": "hard", "confidence": 1.0, "source_turn": 6}, {"field": "color", "operator": "contains", "value": "pink", "strength": "hard", "confidence": 1.0, "source_turn": 6}]`
- Top recommendations: `B08RDV3L3B`, `B0C62MF2HV` **(target)**, `B08CZ8BRZ3`, `B09DBRW4DZ`, `B07R5YRWVC`

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

### public_0012 — browsing

Target: `B08FFGQF72` — GUBERRY Womens Wrap V Neck Long Sleeve Velvet Bodycon Ruched Cocktail Party Dress

Result: hit=`True`, first turn=`4`, rank=`7`

#### Turn 1

**User:** I'm looking for Women Dresses, but I'm still exploring.

**Agent:** Do you have a particular style in mind, like formal, casual, or vintage?

- Asked attribute: `style`
- Semantic query: `women's dresses`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B07NV7NBPH`, `B07HQH7SQB`, `B07RZY7T27`, `B07HP57NDS`, `B01MRV8F5U`

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

**Agent:** Do you have a preference for the material of the dress, like cotton, spandex, or something else?

- Asked attribute: `material`
- Semantic query: `women's dresses`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B07NV7NBPH`, `B08CKBLRZT`, `B07WT9BKMM`, `B07WS5SYTN`, `B07V7C8L6K`

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

**User:** For that, what matters is: polyester; 95% Polyester, 5% Spandex.

**Agent:** Do you have a color preference, like black, blue, or pink?

- Asked attribute: `color`
- Semantic query: `women's dresses made of polyester with spandex blend`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "polyester", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "95% Polyester, 5% Spandex", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "spandex", "strength": "soft", "confidence": 0.9, "source_turn": 3}]`
- Top recommendations: `B09KTVNVKZ`, `B083NDY471`, `B084Z6B4WN`, `B07VVKGN8T`, `B09BJR5R81`

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
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 4

**User:** I don't have an additional preference for color.

**Agent:** Here are some dresses that match your material preference: VWIWV Women's Hooded See Through Bodycon Midi Dress, NeeSee's Dresses Cute Floral Dress, YATHON Women's Spaghetti Straps Off Shoulder Party Sundress, and more.

- Asked attribute: `None`
- Semantic query: `women's dresses made of polyester with spandex blend`
- Target rank this turn: `7`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "polyester", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "95% Polyester, 5% Spandex", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "spandex", "strength": "soft", "confidence": 0.9, "source_turn": 3}]`
- Top recommendations: `B09KTVNVKZ`, `B07CHZBLQS`, `B083NDY471`, `B09BV6T9QM`, `B09K7G8QL9`

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

### public_0108 — buying

Target: `B01I21CI7G` — Hanes Women's Stretch Jersey Bike Shorts, Women’s Cotton Bike Shorts, Women’s Athletic Shorts, 7" Inseam

Result: hit=`True`, first turn=`1`, rank=`5`

#### Turn 1

**User:** I'm looking for Pants & Shorts Shorts. A key requirement is: cotton.

**Agent:** Do you have a preferred style for the shorts, such as sport, casual, or vintage?

- Asked attribute: `style`
- Semantic query: `cotton shorts`
- Target rank this turn: `5`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07P66B5YC`, `B0BV2C1V44`, `B087LY2GDN`, `B08C9Q1WBT`, `B01I21CI7G` **(target)**

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

### public_0084 — intent_override

Target: `B08WKZNFG2` — BeltBro Titan No Buckle Elastic Belt For Men — Fits 1.5 Inch Belt Loops, Comfortable and Easy To Use

Result: hit=`True`, first turn=`5`, rank=`8`

#### Turn 1

**User:** I'm looking for Accessories Belts. Hand Wash Only

**Agent:** What style of belt are you looking for? For example, casual, formal, or vintage?

- Asked attribute: `style`
- Semantic query: `belts that are hand wash only`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Hand Wash Only", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B016KJE6FE`, `B00JW0AYXW`, `B008C1X9QG`, `B0C2TZXDNP`, `B07RZ33BCK`

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

**Agent:** Do you have a preferred brand for the belt? For example, Buckle-Down, Bulliant, or Fossil?

- Asked attribute: `brand`
- Semantic query: `belts that are hand wash only`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Hand Wash Only", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B016KJE6FE`, `B00JW0AYXW`, `B08L13LJ5M`, `B079VSGWS8`, `B0BRVFND5P`

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

**User:** I don't have an additional preference for brand.

**Agent:** Do you have a preferred material for the belt? For example, leather, polyester, or fabric?

- Asked attribute: `material`
- Semantic query: `belts that are hand wash only`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Hand Wash Only", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B016KJE6FE`, `B00JW0AYXW`, `B008C1X9QG`, `B0CHZYH847`, `B07VXNWQ85`

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

**User:** Actually, ignore my earlier preference. What I need is: nylon.

**Agent:** Here are some nylon belts that match your request: Men Tactical Belt, CHAOREN Tactical Belt, AXBXCX Non-Slip Tactical Belt, and more.

- Asked attribute: `None`
- Semantic query: `nylon belts`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "nylon", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B07BP2J7MB`, `B0BRVFND5P`, `B07PJZ193K`, `B09ZYDW9K3`, `B07PDJW7PF`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | active_constraints, superseded_constraints, pending_question, question_history, intent_changed, semantic_query, intent_summary, recommended_asins |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates, attribute_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | ask_attribute, question_scores, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 5

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** What will you primarily use the belt for? For example, outdoor activities, work, or running?

- Asked attribute: `use_case`
- Semantic query: `nylon belts`
- Target rank this turn: `8`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "nylon", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B07BP2J7MB`, `B0BRVFND5P`, `B07PJZ193K`, `B09ZYDW9K3`, `B07PDJW7PF`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_usage |
| validate_patch |  |
| update_state | intent_changed |
| build_query |  |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve |  |
| rrf_fusion |  |
| constraint_filter |  |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_options, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |
