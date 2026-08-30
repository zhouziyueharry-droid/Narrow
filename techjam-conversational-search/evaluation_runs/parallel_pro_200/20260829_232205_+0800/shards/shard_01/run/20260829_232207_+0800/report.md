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
| MRR | 0.370168 |
| MTTC | 3.235294 |
| Efficiency | 0.776471 |
| Technical Score | 0.736933 |
| Prompt tokens | 120469 |
| Completion tokens | 10692 |

## Scenario breakdown

| Scenario | Samples | Hit Rate | MRR | MTTC |
|---|---:|---:|---:|---:|
| boundary | 1 | 1.000000 | 0.125000 | 2.000000 |
| browsing | 11 | 1.000000 | 0.458442 | 2.727273 |
| buying | 3 | 1.000000 | 0.333333 | 2.666667 |
| intent_override | 2 | 0.500000 | 0.062500 | 7.500000 |

## Representative conversations

One long successful session per scenario is shown below. Complete data
for every session is available in `sessions.jsonl`, `turns.jsonl`, and
`node_traces.jsonl`.

### public_0050 — boundary

Target: `B07BYR6T7W` — EverBoots Mens Work Boots for Men, Leather EverFit Lightweight Comfort Boot, Anti Slip & Shock Absorption, Soft Oil Grain, Goodyear Welt, Industrial Construction, Roofing, Electrician Moc Toe Wedge

Result: hit=`True`, first turn=`2`, rank=`8`

#### Turn 1

**User:** I'm looking for Work & Utility Industrial & Construction Boots, but I'm still exploring.

**Agent:** Do you have a preferred brand for your work boots?

- Asked attribute: `brand`
- Semantic query: `work utility industrial construction boots`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "use_case", "operator": "contains", "value": "work", "strength": "soft", "confidence": 0.86, "source_turn": 1}]`
- Top recommendations: `B07GKFWNY7`, `B0BW16W3K8`, `B0B3CK9NW6`, `B009ZNBRBY`, `B07TNFL6TH`

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

**Agent:** Do you have a preference for the material of the boots? For example, leather, fabric, or nylon?

- Asked attribute: `material`
- Semantic query: `work utility industrial construction boots`
- Target rank this turn: `8`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "use_case", "operator": "contains", "value": "work", "strength": "soft", "confidence": 0.86, "source_turn": 1}]`
- Top recommendations: `B07GKFWNY7`, `B0BW16W3K8`, `B07L5WB8ZX`, `B0BMWSD77X`, `B07N9DDRTR`

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

### public_0170 — browsing

Target: `B08LRQX5RH` — UGG Women's Harrison Lace Fashion Boot

Result: hit=`True`, first turn=`7`, rank=`5`

#### Turn 1

**User:** I'm looking for Fashion Combat, but I'm still exploring.

**Agent:** Do you have a preferred brand for your combat boots?

- Asked attribute: `brand`
- Semantic query: `Fashion Combat`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B01M2YTS5G`, `B01M6DWDYU`, `B07CN7853D`, `B01N5K44IX`, `B08FBW62T5`

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

**Agent:** Do you have a preferred style for your combat boots? For example, vintage, casual, or formal?

- Asked attribute: `style`
- Semantic query: `Fashion Combat`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B01M2YTS5G`, `B084JBKQVQ`, `B07D7ZQQKS`, `B07CMLJCT7`, `B00FZ603NI`

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

**Agent:** Do you have a specific use case in mind for your combat boots? For example, winter, work, or outdoor?

- Asked attribute: `use_case`
- Semantic query: `Fashion Combat`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B01M2YTS5G`, `B01M6DWDYU`, `B0844Q75VD`, `B00SK2I9YO`, `B00XLS468A`

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

**Agent:** Here are some combat boots you might like: ALDO Men's Gerrade Combat Boot, Georgia 75 Women Military Lace Up Knee High Combat Boots, and Lucky Top Soda Pack72 Dome Girls Faux Leather Combat Boots.

- Asked attribute: `None`
- Semantic query: `Fashion Combat`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B01M2YTS5G`, `B01M6DWDYU`, `B07CN7853D`, `B01N5K44IX`, `B08FBW62T5`

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

**Agent:** Do you have a preferred color for your combat boots? For example, black, red, or yellow?

- Asked attribute: `color`
- Semantic query: `Fashion Combat`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B01M2YTS5G`, `B01M6DWDYU`, `B07CN7853D`, `B01N5K44IX`, `B08FBW62T5`

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

**User:** I don't have an additional preference for color.

**Agent:** Do you have a preferred material for your combat boots? For example, leather or fabric?

- Asked attribute: `material`
- Semantic query: `Fashion Combat`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[]`
- Top recommendations: `B01M2YTS5G`, `B01M6DWDYU`, `B07CN7853D`, `B01N5K44IX`, `B08FBW62T5`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_confidence, semantic_fallback_reasons, semantic_usage |
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

#### Turn 7

**User:** For that, what matters is: leather; 100% Leather.

**Agent:** Do you have a budget in mind for your combat boots? For example, $50 to $100, $25 to $50, or $100 to $200?

- Asked attribute: `budget`
- Semantic query: `Fashion Combat boots made of 100% leather`
- Target rank this turn: `5`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "leather", "strength": "hard", "confidence": 1.0, "source_turn": 7}, {"field": "material", "operator": "contains", "value": "100% Leather", "strength": "hard", "confidence": 1.0, "source_turn": 7}]`
- Top recommendations: `B00R54VJFY`, `B07CN7853D`, `B00MJ1RJUC`, `B07D7ZQQKS`, `B08LRQX5RH` **(target)**

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

### public_0146 — buying

Target: `B0BCQWYQLQ` — Sarin Mathews Womens One Shoulder Ruched Bodycon Dress Sexy Sleeveless Slit Midi Party Cocktail Wedding Guest Dresses

Result: hit=`True`, first turn=`4`, rank=`3`

#### Turn 1

**User:** I'm looking for Women Dresses. A key requirement is: rayon.

**Agent:** Do you have a preferred style, such as formal, casual, or vintage?

- Asked attribute: `style`
- Semantic query: `Women's dresses made of rayon`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "rayon", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B071G4H1P1`, `B08LPDP499`, `B01M7P6LNC`, `B0B4BRW7JT`, `B011VSTNB6`

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

**Agent:** Do you have a preferred brand, such as Annabelle, Levaca, or Simlu?

- Asked attribute: `brand`
- Semantic query: `Women's dresses made of rayon`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "rayon", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B071G4H1P1`, `B08LPDP499`, `B076L97422`, `B092QB21NK`, `B08Z6KJT1W`

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

**Agent:** Do you have a specific use case in mind, such as work, winter, or running?

- Asked attribute: `use_case`
- Semantic query: `Women's dresses made of rayon`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "rayon", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B071G4H1P1`, `B08LPDP499`, `B0917H9CPN`, `B07PQFZS55`, `B08MF6XVNL`

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

**Agent:** Here are some rayon dresses you might like: 12 Ami Linen Cotton Short Sleeve Pocket Midi Dress, Yosayd Red Lip Long Sleeves Oversize T Shirt Dresses with Pocket, and Sarin Mathews Womens One Shoulder Ruched Bodycon Dress.

- Asked attribute: `None`
- Semantic query: `Women's dresses made of rayon`
- Target rank this turn: `3`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "material", "operator": "contains", "value": "rayon", "strength": "hard", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B071G4H1P1`, `B08LPDP499`, `B0BCQWYQLQ` **(target)**, `B082X5F5VC`, `B073X1MB4L`

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

### public_0038 — intent_override

Target: `B07B5RGY2N` — Blowfish Malibu Women's Fruit Sneaker

Result: hit=`True`, first turn=`4`, rank=`8`

#### Turn 1

**User:** I'm looking for Shoes Fashion Sneakers. Lace Slip On Sneaker

**Agent:** Do you have a preferred brand for these sneakers?

- Asked attribute: `brand`
- Semantic query: `fashion sneakers with lace slip-on style`
- Target rank this turn: `None`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "attribute_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Lace Slip On Sneaker", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07B5RGY2N` **(target)**, `B0C677SDSK`, `B01HSMYV8E`, `B07DPGM4L8`, `B07HCG3SDR`

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
- Semantic query: `fashion sneakers with lace slip-on style`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Lace Slip On Sneaker", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07B5RGY2N` **(target)**, `B07D8Y7KX9`, `B07FH5VRJF`, `B07N9B8LFS`, `B004MXTD5E`

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

**Agent:** Do you have a preferred material, such as leather, fabric, or cotton?

- Asked attribute: `material`
- Semantic query: `fashion sneakers with lace slip-on style`
- Target rank this turn: `None`
- Candidate counts: `{"ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Lace Slip On Sneaker", "strength": "soft", "confidence": 1.0, "source_turn": 1}]`
- Top recommendations: `B07B5RGY2N` **(target)**, `B088PWMMTV`, `B0123OS3G8`, `B01EFGEWK8`, `B0B136Z5FN`

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

**User:** Actually, ignore my earlier preference. What I need is: Textile.

**Agent:** What will you primarily use these sneakers for, such as running, outdoor, or fitness?

- Asked attribute: `use_case`
- Semantic query: `fashion sneakers with textile material`
- Target rank this turn: `8`
- Candidate counts: `{"lexical_candidates": 300, "dense_candidates": 200, "fused_candidates": 500, "filtered_candidates": 500, "ranked_candidates": 500}`
- Active constraints: `[{"field": "feature", "operator": "contains", "value": "Textile", "strength": "hard", "confidence": 1.0, "source_turn": 4}, {"field": "material", "operator": "contains", "value": "Textile", "strength": "hard", "confidence": 1.0, "source_turn": 4}]`
- Top recommendations: `B01MRJUKNX`, `B01MQIF3BA`, `B01HHFU43S`, `B08S45ZBL7`, `B08176BKCY`

| Node stage | Updated fields |
|---|---|
| understand_user | semantic_patch, semantic_usage |
| validate_patch |  |
| update_state | active_constraints, superseded_constraints, pending_question, question_history, intent_changed, semantic_query, intent_summary, recommended_asins |
| build_query | lexical_query, search_query |
| lexical_retrieve + dense_retrieve_fallback + attribute_retrieve | lexical_candidates, dense_candidates |
| rrf_fusion | fused_candidates |
| constraint_filter | filtered_candidates |
| rerank_fallback | ranked_candidates |
| information_gain_question | asked_attributes, pending_question, question_history, ask_attribute, question_scores, question_options, dialogue_reason, dialogue_message, dialogue_usage |
| build_response | response_message, recommendations, usage |
| validate_response | recommended_asins |
