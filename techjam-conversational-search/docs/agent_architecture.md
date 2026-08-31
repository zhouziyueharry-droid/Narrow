# Agent Architecture

[Backend reference index](../README.md) · [Testing and artifacts](../../docs/TESTING.md)

Team ownership and import rules are defined in
[`architecture/module_boundaries.md`](architecture/module_boundaries.md).
Stable replaceable interfaces are documented in
[`contracts/component_interfaces.md`](contracts/component_interfaces.md).

## Product boundary

The core system is a real-user conversational shopping agent. A user sends a
natural-language message; the agent owns turn counting, intent state, retrieval,
clarification, and recommendations. The competition `reset/respond` shape is a
thin compatibility adapter rather than the product architecture.

```python
session_id = agent.start_session(user_profile={})
result = agent.chat(session_id, "I need light waterproof shoes for city travel")
state = agent.get_intent_state(session_id)
```

## Runtime graph

```text
START
  -> understand_user (explicit online or offline mode)
  -> validate_patch
  -> update_state
  -> build_query
       |-> lexical_retrieve  (lexical_query) --------|
       |-> dense_retrieve_fallback (semantic_query) -|-> rrf_fusion
       |-> attribute_retrieve (structured state) ----|
                                                         -> constraint_filter
                                                              |-> rerank_fallback
                                                              |-> relax_and_backfill
                                                                    -> rerank_fallback
                                                              -> information_gain_question
                                                              -> build_response
                                                              -> validate_response
                                                              -> END
```

## Dual representation of user intent

Every turn produces one bounded `StatePatch` with two representations:

- structured fields: category, positive/negative constraints, hard/soft
  strength, fields to remove, and explicit no-preference fields;
- `semantic_query`: one concise English product-search sentence representing
  the complete current intent for a multilingual embedding/vector database.

The patch also contains a user-facing intent summary and detected response
language. It cannot retrieve products or generate catalog identifiers.

When `SHOPPING_AGENT_ENABLE_LLM=true`, the LLM
is called on every user turn. The prompt includes current category, active
constraints, previous semantic query, intent summary, and optional user profile,
so references and changes can be resolved against maintained state. Missing keys,
provider/network failures, invalid JSON, or invalid model output fail explicitly;
they do not switch to deterministic extraction. Transient-error retries remain.

## Persistent intent state

LangGraph checkpoints one JSON-serializable state per user session. Important
durable values include:

- active and superseded constraints;
- category, no-preference fields, and already-asked attributes;
- complete semantic query and intent summary;
- previously recommended products for novelty control.

An explicit replacement retires prior constraints for the fields being
replaced, including hard constraints. A new explicit preference also clears an
older no-preference marker for that field.

## Retrieval contracts

The graph intentionally separates three retrieval inputs:

- `lexical_query`: category, positive structured values, and semantic query for
  field-weighted SQLite FTS5/BM25;
- `semantic_query`: the clean LLM sentence sent only to the semantic retriever;
- structured state: attributes and hard constraints used for indexed coarse
  retrieval and centralized filtering.

`SemanticRetriever` is a replaceable boundary with `search(query, limit)`. The
current `LocalDenseIndex` is an offline hashed-vector fallback, not a production
embedding model. A vector database implementation can be injected without
changing graph topology.

Weighted reciprocal-rank fusion combines all routes. High-confidence hard
constraints are applied centrally. When too few products survive, a broader
category search backfills candidates without discarding hard constraints.

## Candidate evidence and dialogue decisions

There are no evaluator-specific “first two turns ask other” rules. After each
retrieval and reranking pass, the agent analyzes the current Top-50 candidates.
For every unknown facet it calculates attribute coverage multiplied by
normalized entropy, excludes already-known, already-asked, and no-preference
fields, and saves representative values and counts as evidence.
Online, the model chooses the dialogue action, question attribute, and wording
from this evidence; it is not given a local `fallback_suggestion` and does not
call the offline `choose_question` policy. Offline, deterministic clarification
uses candidate partitions and can recommend without forcing another question.

## Online/offline isolation

- Online interpretation does not call the local parser or pass a rule-generated
  patch to the model. Category, constraints, replacements, removals, no-preference
  fields, semantic query, and retrieval intent come from model output.
- Validation checks types, normalizes whitespace, and deduplicates values.
  Positive/negative conflicts for the same attribute and value are errors,
  not an opportunity to choose a constraint on the model's behalf.
- State updates apply the patch and inherit unchanged history. Retrieval
  serializes these fields and does not infer extra constraints from user text;
  explicit `unknown` intent remains unknown.
- Retrieval, filtering, and ranking remain fixed code and numerical models.
  The graph is not an unrestricted tool-calling agent.
- `semantic_patch.model_output` records parsed model intent, not the raw response;
  `dialogue_parser` and `dialogue_model_output` record dialogue provenance.
- Only `SHOPPING_AGENT_ENABLE_LLM=false` enables offline parsing and dialogue
  policy. Online errors do not silently become offline benchmark results.

This boundary does not retroactively repair old checkpoints or historical traces.
Start a new session when validating changed intent behavior.

## Reliability boundary

The final node enforces catalog membership, unique product identifiers, Top-K
limits, allowed question attributes, and non-negative usage accounting.
The local semantic index and Precise reranker remain default components;
LambdaMART is opt-in. Neither ranking nor response validation grants access
to evaluator hidden targets or permits inventing catalog identifiers.
