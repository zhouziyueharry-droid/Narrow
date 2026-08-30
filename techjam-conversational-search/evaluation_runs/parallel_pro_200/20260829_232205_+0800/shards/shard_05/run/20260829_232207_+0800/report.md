# Traced Evaluation Report

Run: `20260829_232207_+0800`  
Model: `deepseek-v4-pro`  
LLM enabled: `True`  
Git commit: `d838e680fa7a44f5c64f34b8e3952685df195b90`

## Score

| Metric | Value |
|---|---:|
| Samples | 17 |
| Hit Rate@10 | 0.941176 |
| MRR | 0.393861 |
| MTTC | 3.411765 |
| Efficiency | 0.758823 |
| Technical Score | 0.740511 |
| Prompt tokens | 129438 |
| Completion tokens | 11724 |

## Scenario breakdown

| Scenario | Samples | Hit Rate | MRR | MTTC |
|---|---:|---:|---:|---:|
| browsing | 6 | 1.000000 | 0.364352 | 4.000000 |
| buying | 8 | 0.875000 | 0.449107 | 3.000000 |
| intent_override | 3 | 1.000000 | 0.305556 | 3.333333 |

## Representative conversations

One long successful session per scenario is shown below. Complete data
for every session is available in `sessions.jsonl`, `turns.jsonl`, and
`node_traces.jsonl`.

### public_0162 — browsing

Target: `B0B71JNMQY` — Satin Silk Slip Maxi Dress for Wedding Guest Women- Cowl Neck Pleated Bust Split Wedding Guest Cocktail Midi Dresses

Result: hit=`True`, first turn=`10`, rank=`1`

#### Turn 1

**User:** I'm looking for Women Dresses, but I'm still exploring.

**Agent:** Do you have a preferred style, like formal, casual, or vintage?

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

**Agent:** Do you have a preferred material, like fabric, spandex, or cotton?

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

**User:** For that, what matters is: silk.

**Agent:** Here are some silk options for you: a traditional silk saree, a silk scarf, and a silk head scarf.

- Asked attribute: `None`
- Semantic query: `silk women's dresses`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "silk", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B08KH5HGLF`, `B0B5SSB8HD`, `B01C52J5JC`, `B096ZNVBDC`, `B07QGCJVRG`

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

#### Turn 4

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** Do you have a preferred brand?

- Asked attribute: `brand`
- Semantic query: `silk women's dresses`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "silk", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B08KH5HGLF`, `B0B5SSB8HD`, `B01C52J5JC`, `B096ZNVBDC`, `B07RY4JPZJ`

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

#### Turn 5

**User:** I don't have an additional preference for brand.

**Agent:** Do you have a preferred color, like black, red, or pink?

- Asked attribute: `color`
- Semantic query: `silk women's dresses`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "silk", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B08KH5HGLF`, `B0B5SSB8HD`, `B01C52J5JC`, `B096ZNVBDC`, `B07QGCJVRG`

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

#### Turn 6

**User:** I don't have an additional preference for color.

**Agent:** Do you have a specific use case in mind, like winter, work, or outdoor?

- Asked attribute: `use_case`
- Semantic query: `silk women's dresses`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "silk", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B08KH5HGLF`, `B0B5SSB8HD`, `B01C52J5JC`, `B096ZNVBDC`, `B07QGCJVRG`

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

#### Turn 7

**User:** I don't have an additional preference for use_case.

**Agent:** Do you have a budget in mind, like under $25 or $25 to $50?

- Asked attribute: `budget`
- Semantic query: `silk women's dresses`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "silk", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B08KH5HGLF`, `B0B5SSB8HD`, `B01C52J5JC`, `B096ZNVBDC`, `B07QGCJVRG`

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

#### Turn 8

**User:** I don't have an additional preference for budget.

**Agent:** Here are some silk items you might like: a traditional silk saree, a mulberry silk scarf, a silk head scarf, a silk beaded bracelet, a silk satin belt, a silk neckerchief, silk pajamas, and a silk face mask.

- Asked attribute: `None`
- Semantic query: `silk women's dresses`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "silk", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B08KH5HGLF`, `B0B5SSB8HD`, `B01C52J5JC`, `B096ZNVBDC`, `B07QGCJVRG`

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

#### Turn 9

**User:** Those options are not quite right yet. Ask me about one specific attribute.

**Agent:** What specific feature are you looking for, like adjustable, lightweight, or handmade?

- Asked attribute: `feature`
- Semantic query: `silk women's dresses`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "silk", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B08KH5HGLF`, `B0B5SSB8HD`, `B01C52J5JC`, `B096ZNVBDC`, `B07QGCJVRG`

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
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

#### Turn 10

**User:** For that, what matters is: Satin; Imported.

**Agent:** Here are some satin and imported silk items you might like: a satin silk slip maxi dress, a silk beaded wrap bracelet, a mulberry silk scarf, a silk satin belt, a satin nightgown, silk satin pajamas, and a satin kimono robe.

- Asked attribute: `None`
- Semantic query: `silk women's dresses with satin and imported features`
- Target rank this turn: `1`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "silk", "strength": "hard", "confidence": 1.0, "source_turn": 3}, {"field": "feature", "operator": "contains", "value": "Satin", "strength": "hard", "confidence": 1.0, "source_turn": 10}, {"field": "feature", "operator": "contains", "value": "Imported", "strength": "hard", "confidence": 1.0, "source_turn": 10}]`
- Top recommendations: `B0B71JNMQY` **(target)**, `B096ZNVBDC`, `B0B5SSB8HD`, `B07QGCJVRG`, `B07JCQ4C1N`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
| validate_patch |  |
| update_state | active_constraints, pending_question, question_history, semantic_query, intent_summary |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | ask_attribute, dialogue_action, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |

### public_0018 — buying

Target: `B07H3T5YGH` — O2TEE Men's Workout Gym Tank Tops Men - Custom Tank Top - Customized & Personalized Tanktops Text

Result: hit=`True`, first turn=`3`, rank=`7`

#### Turn 1

**User:** I'm looking for Shirts Tanks Tops. A key requirement is: polyester.

**Agent:** Do you have a preferred brand?

- Asked attribute: `brand`
- Semantic query: `polyester shirts tanks tops`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "polyester", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07DPM8H8B`, `B01G92PR4Q`, `B088LWDGBF`, `B07ZYMGXZZ`, `B08TG8JRDZ`

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

**Agent:** Do you have a preferred style, such as casual, sport, or vintage?

- Asked attribute: `style`
- Semantic query: `polyester shirts tanks tops`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "polyester", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07DPM8H8B`, `B08P53R3CN`, `B09P81G2K9`, `B07PCPTMRD`, `B09VS3CGMZ`

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

**Agent:** Do you have a specific use case in mind, such as work, fitness, or running?

- Asked attribute: `use_case`
- Semantic query: `polyester shirts tanks tops`
- Target rank this turn: `7`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "polyester", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07DPM8H8B`, `B01G92PR4Q`, `B088LWDGBF`, `B088R49TH3`, `B07Z7L475T`

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

### public_0198 — intent_override

Target: `B08K1ZJZ4N` — lola mae Quilted Crossbody Bag, Medium Lightweight Shoulder Purse Top Zipper Tassel Accent

Result: hit=`True`, first turn=`4`, rank=`4`

#### Turn 1

**User:** I'm looking for Handbags & Wallets Crossbody Bags. Imported

**Agent:** Do you have a preferred brand for the crossbody bag?

- Asked attribute: `brand`
- Semantic query: `Imported crossbody bags`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 395, "filtered_candidates": 395, "ranked_candidates": 395}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Imported", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B01LZIGLSU`, `B07MYVS3F6`, `B013HUP108`, `B01C6SL1D8`, `B0743XFGRM`

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

**Agent:** Do you have a preferred material for the crossbody bag? For example, leather, polyester, or fabric?

- Asked attribute: `material`
- Semantic query: `Imported crossbody bags`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 395}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Imported", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B01LZIGLSU`, `B07S8NW7PV`, `B07FMCB676`, `B09DKLMG2R`, `B0B5FMVDYH`

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

**User:** For that, what matters is: leather.

**Agent:** Do you have a preferred style for the crossbody bag? For example, casual, vintage, or formal?

- Asked attribute: `style`
- Semantic query: `Imported leather crossbody bags`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 461, "filtered_candidates": 461, "ranked_candidates": 461}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Imported", "strength": "soft", "confidence": 1.0, "source_turn": 1}, {"field": "material", "operator": "contains", "value": "leather", "strength": "hard", "confidence": 1.0, "source_turn": 3}]`
- Top recommendations: `B06Y5SB28W`, `B0B5ZS2J2W`, `B01I1ISOQ4`, `B07RPQP34D`, `B07MYVS3F6`

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

**User:** Actually, ignore my earlier preference. What I need is: leather.

**Agent:** Do you have a budget in mind for the crossbody bag? For example, under $25, $25 to $50, or $50 to $100?

- Asked attribute: `budget`
- Semantic query: `leather crossbody bags`
- Target rank this turn: `4`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "fused_candidates": 458, "filtered_candidates": 458, "ranked_candidates": 458}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "leather", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B07G6WBSX9`, `B07S8NW7PV`, `B07MYVS3F6`, `B08K1ZJZ4N` **(target)**, `B083VHP6BM`

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
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, candidate_count, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |
