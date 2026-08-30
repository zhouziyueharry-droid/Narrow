# Traced Evaluation Report

Run: `20260829_232207_+0800`  
Model: `deepseek-v4-pro`  
LLM enabled: `True`  
Git commit: `d838e680fa7a44f5c64f34b8e3952685df195b90`

## Score

| Metric | Value |
|---|---:|
| Samples | 17 |
| Hit Rate@10 | 1.000000 |
| MRR | 0.417063 |
| MTTC | 2.000000 |
| Efficiency | 0.900000 |
| Technical Score | 0.805119 |
| Prompt tokens | 74365 |
| Completion tokens | 7460 |

## Scenario breakdown

| Scenario | Samples | Hit Rate | MRR | MTTC |
|---|---:|---:|---:|---:|
| boundary | 1 | 1.000000 | 0.111111 | 5.000000 |
| browsing | 11 | 1.000000 | 0.393543 | 1.727273 |
| buying | 4 | 1.000000 | 0.612500 | 1.500000 |
| intent_override | 1 | 1.000000 | 0.200000 | 4.000000 |

## Representative conversations

One long successful session per scenario is shown below. Complete data
for every session is available in `sessions.jsonl`, `turns.jsonl`, and
`node_traces.jsonl`.

### public_0187 — boundary

Target: `B000GQ1F3O` — Eastland Men's Newport Slip-On Shoe

Result: hit=`True`, first turn=`5`, rank=`9`

#### Turn 1

**User:** I'm looking for Shoes Loafers & Slip-Ons, but I'm still exploring.

**Agent:** Do you have a preferred brand? For example, Skechers, Sperry, or Hey Dude?

- Asked attribute: `brand`
- Semantic query: `loafers and slip-on shoes`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B07BDKQQ19`, `B09VRSZ81X`, `B09GF1RWH5`, `B006T6CT4E`, `B07NP8LHRK`

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

**Agent:** Do you have a preferred style? For example, casual, vintage, or formal?

- Asked attribute: `style`
- Semantic query: `loafers and slip-on shoes`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B07BDKQQ19`, `B01MY8AI9R`, `B00MMYD5FE`, `B07D3VMBNB`, `B07DHM2PJ5`

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

**User:** I don't have an additional preference for style.

**Agent:** Do you have a preferred material? For example, leather, fabric, or cotton?

- Asked attribute: `material`
- Semantic query: `loafers and slip-on shoes`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B07BDKQQ19`, `B07FKRBF13`, `B07TSF9GW3`, `B00E1ITZIA`, `B07L2LPWTG`

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

**User:** For that, what matters is: leather; 100% Leather.

**Agent:** Here are some leather loafers and slip-ons you might like: Steve Madden Men's Jaaggg Slip-On Loafer, Sperry Men's Hampden Penny, and Bruno Marc Men's Leather Lined Dress Loafers Slip-On Shoes.

- Asked attribute: `None`
- Semantic query: `leather loafers and slip-on shoes`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 445, "filtered_candidates": 445, "ranked_candidates": 445}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "leather", "strength": "hard", "confidence": 1.0, "source_turn": 4}, {"field": "material", "operator": "contains", "value": "100% Leather", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B00RES87GU`, `B00L9DO7GU`, `B06XS2T88L`, `B00HHYFUAM`, `B019YJWYBA`

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
| information_gain_question | ask_attribute, question_scores, question_options, candidate_count, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 5

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** What will you primarily use these loafers for? For example, work, outdoor, or winter?

- Asked attribute: `use_case`
- Semantic query: `leather loafers and slip-on shoes`
- Target rank this turn: `9`
- Candidate counts: `{"ranked_candidates": 445}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "leather", "strength": "hard", "confidence": 1.0, "source_turn": 4}, {"field": "material", "operator": "contains", "value": "100% Leather", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B00RES87GU`, `B004FXOH3E`, `B0090X4PWC`, `B00S0IB440`, `B07PKLDCJY`

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

### public_0007 — browsing

Target: `B08PF98BV4` — RITERA Plus Size Tops for Women Off the Shoulder Cold Shoulder Tops Short Sleeve Shirts Summer Blouses Sexy Tunics Tee XL-5XL

Result: hit=`True`, first turn=`3`, rank=`1`

#### Turn 1

**User:** I'm looking for Tees & Blouses Tunics, but I'm still exploring.

**Agent:** Do you have a preferred brand? For example, Esenchel, Zerdocean, or Ritera?

- Asked attribute: `brand`
- Semantic query: `tees and blouses tunics`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B08K4JWMR6`, `B077JXNCPW`, `B0711X8C7X`, `B07D5T6LGQ`, `B08DNVQJ47`

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

**Agent:** Do you have a preferred material? For example, polyester, spandex, or fabric?

- Asked attribute: `material`
- Semantic query: `tees and blouses tunics`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B08K4JWMR6`, `B08FYN6CBS`, `B09SKWZYD1`, `B089D566YR`, `B09MSY8926`

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

**User:** For that, what matters is: polyester; 75% Polyester, 20% Rayon, 5% Spandex.

**Agent:** Do you have a preferred style? For example, casual, formal, or vintage?

- Asked attribute: `style`
- Semantic query: `tees and blouses tunics made of polyester blend with rayon and spandex`
- Target rank this turn: `1`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "polyester", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "75% Polyester, 20% Rayon, 5% Spandex", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "spandex", "strength": "soft", "confidence": 0.9, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "rayon", "strength": "soft", "confidence": 0.9, "source_turn": 3}]`
- Top recommendations: `B08PF98BV4` **(target)**, `B07J3C2Y2X`, `B0BP2CSW2D`, `B09BQWHZFN`, `B0B7VYPTYQ`

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

### public_0031 — buying

Target: `B0BQDTGHMZ` — Signature by Levi Strauss & Co. Gold Label Women's Modern Skinny Jeans (Standard and Plus)

Result: hit=`True`, first turn=`2`, rank=`5`

#### Turn 1

**User:** I'm looking for Women Jeans. A key requirement is: cotton.

**Agent:** Do you have a preferred brand for the jeans?

- Asked attribute: `brand`
- Semantic query: `cotton women jeans`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B085FT43TV`, `B076J7VB8G`, `B088GY1MK1`, `B076ZV7BQJ`, `B077R8B358`

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

**Agent:** Do you have a preferred style for the jeans? For example, vintage, casual, or sport?

- Asked attribute: `style`
- Semantic query: `cotton women jeans`
- Target rank this turn: `5`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B085FT43TV`, `B07D5M61T2`, `B010C5IKYK`, `B000TJG29U`, `B0BQDTGHMZ` **(target)**

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

### public_0103 — intent_override

Target: `B0BT8T2FQ3` — Fruit of the Loom Men's Eversoft Cotton Stay Tucked Crew T-Shirt

Result: hit=`True`, first turn=`4`, rank=`5`

#### Turn 1

**User:** I'm looking for Underwear Undershirts. Imported

**Agent:** Do you have a preferred brand for the undershirts?

- Asked attribute: `brand`
- Semantic query: `imported underwear undershirts`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 72, "fused_candidates": 459, "filtered_candidates": 459, "ranked_candidates": 459}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Imported", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07C3J1VSQ`, `B0BT8T2FQ3` **(target)**, `B0CKQ3CKZH`, `B019P5WRLK`, `B0BSS36XCS`

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

**Agent:** Do you have a preferred material for the undershirts?

- Asked attribute: `material`
- Semantic query: `imported underwear undershirts`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 459}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Imported", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07C3J1VSQ`, `B0BT8T2FQ3` **(target)**, `B0CKQ3CKZH`, `B07CLKVV5K`, `B0BXP6MG3X`

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

**User:** For that, what matters is: cotton; 100% Cotton.

**Agent:** Here are some cotton undershirts that match your preferences: Berrak Collection Men's Cotton Crew-Neck Undershirts, Fruit of the Loom Men's Eversoft Cotton Stay Tucked Crew T-Shirt, and Feathers Boys White Tank Top 100% Cotton Tagless Undershirts.

- Asked attribute: `None`
- Semantic query: `imported 100% cotton underwear undershirts`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Imported", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "material", "operator": "contains", "value": "100% Cotton", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B07C3J1VSQ`, `B0BT8T2FQ3` **(target)**, `B019P5WRLK`, `B0BSS36XCS`, `B00F0TO1S8`

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
| information_gain_question | ask_attribute, question_scores, question_options, candidate_count, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 4

**User:** Actually, ignore my earlier preference. What I need is: cotton.

**Agent:** Here are some cotton undershirts that match your preferences: Berrak Collection Men's Cotton Crew-Neck Undershirts, Fruit of the Loom Men's Eversoft Cotton Stay Tucked Crew T-Shirt, and Feathers Boys White Tank Top 100% Cotton Tagless Undershirts.

- Asked attribute: `None`
- Semantic query: `cotton underwear undershirts`
- Target rank this turn: `5`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "cotton", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B019P5WRLK`, `B0036UZNBC`, `B0BSS36XCS`, `B00W57TS6S`, `B0BT8T2FQ3` **(target)**

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | active_constraints, superseded_constraints, intent_changed, semantic_query, intent_summary, recommended_asins |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates, attribute_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | question_scores, dialogue_reason, dialogue_usage |
| build_response | recommendations, usage |
| validate_response | recommended_asins |
