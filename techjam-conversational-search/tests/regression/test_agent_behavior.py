from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult

from shopping_agent.agent import DeepShoppingAgent, ShoppingAgent
from shopping_agent.catalog import CatalogIndex
from shopping_agent.graph import build_shopping_graph
from shopping_agent.intent import merge_constraints, parse_message
from shopping_agent.question_policy import choose_question, question_options
from shopping_agent.dialogue.decision import decide_dialogue
from shopping_agent.ranking import FallbackReranker
from shopping_agent.retrieval import reciprocal_rank_fusion
from shopping_agent.schemas import AgentTurn, Constraint, Recommendation
from shopping_agent.semantic_state import (
    StatePatch,
    apply_state_patch,
    resolve_semantic_patch,
    rule_state_patch,
    semantic_fallback_patch,
)


def _write_catalog(path: Path) -> None:
    products = [
        {
            "parent_asin": "A",
            "title": "Black leather belt",
            "features": ["100% leather"],
            "details": {"Department": "mens"},
            "description": [],
            "categories": ["Accessories", "Belts"],
            "store": "Example",
            "price": 30.0,
            "average_rating": 4.5,
            "rating_number": 100,
        },
        {
            "parent_asin": "B",
            "title": "Blue running shoe",
            "features": ["breathable mesh"],
            "details": {"Department": "womens"},
            "description": [],
            "categories": ["Shoes", "Running"],
            "store": "Example",
            "price": 80.0,
            "average_rating": 4.4,
            "rating_number": 80,
        },
    ]
    path.write_text("".join(json.dumps(item) + "\n" for item in products), encoding="utf-8")


class FakeGraph:
    def __init__(self) -> None:
        self.configs: list[dict] = []

    def invoke(self, payload: dict, config: dict) -> dict:
        self.configs.append(config)
        return {
            "messages": payload["messages"],
            "structured_response": AgentTurn(
                message="Do you have a material preference?",
                ask_attribute="material",
                recommendations=[
                    Recommendation(parent_asin="A", score=0.9),
                    Recommendation(parent_asin="A", score=0.8),
                    Recommendation(parent_asin="B", score=0.7),
                ],
            ),
        }


class ConstructionOnlyModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "construction-only"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        raise AssertionError("This model is only used to verify graph construction")

    def bind_tools(self, tools, **kwargs):
        return self


def test_catalog_index_retrieves_matching_product(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.jsonl"
    _write_catalog(catalog_path)
    index = CatalogIndex(catalog_path)

    results = index.search("black leather belt", limit=2)

    assert results[0]["parent_asin"] == "A"


def test_deep_agent_graph_constructs_with_catalog_tools(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.jsonl"
    _write_catalog(catalog_path)

    graph = build_shopping_graph(ConstructionOnlyModel(), catalog_path)

    assert graph is not None


def test_official_adapter_uses_session_as_langgraph_thread_and_deduplicates() -> None:
    graph = FakeGraph()
    agent = DeepShoppingAgent(graph=graph)
    agent.reset("session-1", {"preference_tags": ["comfort"]})

    response = agent.respond("session-1", "I need a belt", turn=1, top_k=10)

    assert response["ask_attribute"] == "material"
    assert [item["parent_asin"] for item in response["recommendations"]] == ["A", "B"]
    assert graph.configs[0]["configurable"]["thread_id"].startswith("session-1:")
    assert response["usage"] == {"prompt_tokens": 0, "completion_tokens": 0}


def test_intent_override_retires_soft_preference_but_keeps_hard_constraint() -> None:
    initial = parse_message("I'm looking for belts. I prefer a casual fit.", turn=1)
    hard = parse_message("For that, what matters is: leather.", turn=2)
    active, _ = merge_constraints([], initial)
    active, _ = merge_constraints(active, hard)

    override = parse_message(
        "Actually, ignore my earlier preference. What I need is: color: black.",
        turn=3,
    )
    active, superseded = merge_constraints(active, override)

    assert any(item.strength == "soft" for item in superseded)
    assert any(str(item.value) == "leather" for item in active)
    assert any("black" in str(item.value) for item in active)


def test_explicit_full_restart_clears_hard_and_soft_constraints() -> None:
    active = [
        Constraint(field="material", value="leather", strength="hard"),
        Constraint(field="color", value="brown", strength="soft"),
    ]
    patch = StatePatch(
        action="replace",
        reset_scope="all",
        constraints=[Constraint(field="feature", value="waterproof", strength="hard")],
    )

    updated, superseded = apply_state_patch(
        [item.model_dump() for item in active], patch,
    )

    assert [(item.field, item.value) for item in updated] == [("feature", "waterproof")]
    assert {(item.field, item.value) for item in superseded} == {
        ("material", "leather"), ("color", "brown"),
    }


def test_long_protocol_answer_is_bound_to_the_pending_feature(monkeypatch) -> None:
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "false")
    patch, _ = resolve_semantic_patch(
        "For that, what matters is: Pull On closure for quick dressing; holiday pattern.",
        turn=2,
        previous_ask_attribute="feature",
        previous_question_options=[],
    )

    assert [item.field for item in patch.constraints] == ["feature", "feature"]
    assert [item.value for item in patch.constraints] == [
        "Pull On closure for quick dressing", "holiday pattern",
    ]


def test_care_instructions_do_not_become_product_exclusions(monkeypatch) -> None:
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "false")
    patch, _ = resolve_semantic_patch(
        "For that, what matters is: Care: Machine or hand wash in cold water, "
        "no bleach, no dry clean, hang dry.",
        turn=3,
        previous_ask_attribute="feature",
    )

    assert not any(item.operator == "not_contains" for item in patch.constraints)


def test_mvp_graph_accumulates_turn_constraints_and_returns_catalog_ids(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.jsonl"
    _write_catalog(catalog_path)
    agent = ShoppingAgent(catalog_path)
    agent.reset("session-mvp", {"preference_tags": ["durability"]})

    first = agent.respond("session-mvp", "I'm looking for accessories, but I'm still exploring.", 1, 10)
    second = agent.respond("session-mvp", "For that, what matters is: leather; color: black.", 2, 10)

    assert first["ask_attribute"] is None
    assert second["recommendations"][0]["parent_asin"] == "A"
    intent_state = agent.get_intent_state("session-mvp")
    assert "leather" in intent_state["semantic_query"]
    assert any(item["field"] == "material" for item in intent_state["active_constraints"])


def test_agent_exposes_compact_node_trace(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.jsonl"
    _write_catalog(catalog_path)
    agent = ShoppingAgent(catalog_path)
    agent.reset("trace-session", {})

    agent.respond("trace-session", "I need running shoes", 1, 10)
    trace = agent.get_turn_trace("trace-session", 1, candidate_limit=1)

    assert trace[0]["nodes"] == ["understand_user"]
    assert "semantic_patch" in trace[0]["updates"]
    retrieval = next(item for item in trace if "lexical_retrieve" in item["nodes"])
    assert retrieval["updates"]["lexical_candidates"]["count"] >= 1
    assert len(retrieval["updates"]["lexical_candidates"]["top"]) == 1
    query = next(item for item in trace if item["nodes"] == ["build_query"])
    assert query["updates"]["retrieval_intent"] == "unknown"
    policy = next(item for item in trace if item["nodes"] == ["plan_retrieval"])
    assert policy["updates"]["retrieval_plan"]["dense_limit"] == 300
    fusion = next(item for item in trace if item["nodes"] == ["rrf_fusion"])
    fused_top = fusion["updates"]["fused_candidates"]["top"][0]
    assert fused_top["retrieval_intent"] == "unknown"
    assert fused_top["route_weights"] == {
        "lexical": 0.8,
        "dense": 0.75,
        "attribute": 0.55,
    }
    assert "constraint_evidence" in fused_top
    assert fusion["updates"]["retrieval_diagnostics"]["route_union_count"] >= 1
    agent.release_session("trace-session")


def test_rrf_rewards_candidates_returned_by_multiple_routes() -> None:
    fused = reciprocal_rank_fusion([
        ([{"parent_asin": "A"}, {"parent_asin": "B"}], 1.0),
        ([{"parent_asin": "B"}, {"parent_asin": "C"}], 1.0),
    ])

    assert fused[0]["parent_asin"] == "B"
    assert fused[0]["route_count"] == 2


def test_question_policy_uses_candidate_entropy_after_discovery_turns() -> None:
    attribute, scores = choose_question(
        turn=4,
        candidate_attributes=[
            {"material": {"leather"}, "color": {"black"}},
            {"material": {"cotton"}, "color": {"black"}},
        ],
        asked_attributes=["other"],
        no_preference=set(),
    )

    assert attribute == "material"
    assert scores["material"] > scores["color"]


def test_question_policy_uses_current_candidates_and_exposes_options() -> None:
    candidates = [
        {"material": {"leather"}, "color": {"black"}},
        {"material": {"cotton"}, "color": {"black"}},
        {"material": {"leather"}, "color": {"black"}},
    ]

    attribute, _ = choose_question(
        turn=1,
        candidate_attributes=candidates,
        asked_attributes=[],
        no_preference=set(),
        known_attributes={"color"},
    )

    assert attribute == "material"
    assert question_options(candidates, attribute) == [
        {"value": "leather", "count": 2},
        {"value": "cotton", "count": 1},
    ]


def test_fallback_understands_free_text_answer_from_previous_question(monkeypatch) -> None:
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "false")
    message = "I'd prefer the brand Adoretex."

    patch, _ = resolve_semantic_patch(
        message,
        2,
        rule_state_patch(message, 2),
        previous_ask_attribute="brand",
        previous_question_options=[
            {"value": "generic", "count": 10},
            {"value": "55carat", "count": 8},
        ],
    )

    assert any(
        item.field == "brand" and str(item.value).casefold() == "adoretex"
        for item in patch.constraints
    )
    assert "previous_question_context" in patch.fallback_reasons


def test_dialogue_agent_receives_conversation_state_and_candidate_context(monkeypatch) -> None:
    captured: dict = {}

    def fake_request(payload: dict):
        captured.update(payload)
        return {
            "action": "recommend",
            "ask_attribute": None,
            "message": "These are strong matches for what you described.",
            "reason": "requirements_satisfied",
        }, {"prompt_tokens": 12, "completion_tokens": 5}

    monkeypatch.setattr(
        "shopping_agent.infrastructure.llm.deepseek.is_configured", lambda: True
    )
    monkeypatch.setattr(
        "shopping_agent.infrastructure.llm.deepseek.request_dialogue_decision",
        fake_request,
    )

    decision, scores, _, usage = decide_dialogue(
        turn=2,
        user_message="Adoretex please",
        conversation_history=[
            {"role": "assistant", "content": "Which brand do you prefer?"}
        ],
        active_constraints=[{"field": "budget", "operator": "lte", "value": 100}],
        no_preference=set(),
        asked_attributes=["brand"],
        pending_question={"attribute": "brand", "options": []},
        question_history=[{"attribute": "brand", "status": "pending"}],
        candidate_attributes=[{"brand": {"adoretex"}}, {"brand": {"generic"}}],
        ranked_candidates=[{
            "parent_asin": "A", "title": "Adoretex coat", "reranker_score": 8.5,
        }],
        known_attributes={"budget", "brand"},
        language="en",
    )

    assert decision.action == "recommend"
    assert captured["pending_question"]["attribute"] == "brand"
    assert captured["recent_conversation"][0]["role"] == "assistant"
    assert captured["top_candidates"][0]["title"] == "Adoretex coat"
    assert "brand" not in scores
    assert usage == {"prompt_tokens": 12, "completion_tokens": 5}


def test_replacement_retires_conflicting_hard_state() -> None:
    active = [Constraint(field="color", value="red", strength="hard").model_dump()]
    patch = StatePatch(
        action="replace",
        constraints=[Constraint(field="color", value="blue", strength="hard")],
    )

    updated, superseded = apply_state_patch(active, patch)

    assert [item.value for item in updated] == ["blue"]
    assert [item.value for item in superseded] == ["red"]


def test_reranker_ignores_non_numeric_catalog_price() -> None:
    ranked = FallbackReranker().rank(
        [{"parent_asin": "A", "title": "Watch repair kit", "price": "—"}],
        query="watch repair kit",
        category="repair kits",
        constraints=[Constraint(field="budget", operator="lte", value=30, strength="hard")],
    )

    assert ranked[0]["parent_asin"] == "A"


def test_semantic_fallback_resolves_negation_without_negating_neutral_color() -> None:
    message = "I don't mind black, but I definitely don't want leather."
    rules = rule_state_patch(message, turn=1)
    patch = semantic_fallback_patch(message, 1, rules, current_category="shoes")

    assert "unresolved_negation" in rules.fallback_reasons
    assert any(
        item.field == "material" and item.operator == "not_contains" and item.value == "leather"
        for item in patch.constraints
    )
    assert not any(
        item.field == "color" and item.operator == "not_contains" and item.value == "black"
        for item in patch.constraints
    )


def test_semantic_fallback_splits_preferred_and_maximum_budget() -> None:
    message = "Under $80 if possible, but I could stretch to $100 for waterproof ones."
    patch = semantic_fallback_patch(message, 2, rule_state_patch(message, 2))
    budgets = [item for item in patch.constraints if item.field == "budget"]

    assert any(item.value == 80.0 and item.strength == "soft" for item in budgets)
    assert any(item.value == 100.0 and item.strength == "hard" for item in budgets)
    assert any(item.field == "feature" and item.value == "waterproof" for item in patch.constraints)


def test_semantic_fallback_uses_history_for_comparative_reference() -> None:
    message = "Something lighter, and not that tall."
    patch = semantic_fallback_patch(
        message,
        2,
        rule_state_patch(message, 2),
        current_category="boots",
    )

    assert patch.category == "boots"
    assert any(item.field == "feature" and item.value == "lightweight" for item in patch.constraints)
    assert any(item.operator == "not_contains" and item.value == "tall" for item in patch.constraints)


def test_semantic_provider_stays_off_without_explicit_enable(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "not-used")
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "false")
    message = "Something lighter for hiking."
    patch, usage = resolve_semantic_patch(message, 1, rule_state_patch(message, 1))

    assert patch.parser == "fallback"
    assert patch.semantic_query
    assert usage == {"prompt_tokens": 0, "completion_tokens": 0}


def test_semantic_provider_is_primary_even_for_high_confidence_rule_input(monkeypatch) -> None:
    calls: list[dict] = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            payload = {
                "action": "add",
                "category": "shoes",
                "constraints": [],
                "semantic_query": "lightweight city walking shoes",
                "intent_summary": "轻便的城市步行鞋",
                "language": "zh",
                "confidence": 0.96,
            }
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))],
                usage=SimpleNamespace(prompt_tokens=120, completion_tokens=40),
            )

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "true")
    message = "I'm looking for shoes."

    patch, usage = resolve_semantic_patch(message, 1, rule_state_patch(message, 1))

    assert len(calls) == 1
    assert patch.parser == "deepseek"
    assert patch.semantic_query == "lightweight city walking shoes"
    assert usage == {"prompt_tokens": 120, "completion_tokens": 40}


def test_semantic_fallback_splits_compound_negation_into_separate_constraints() -> None:
    message = "I don't want cotton or wool."
    patch = semantic_fallback_patch(message, 1, rule_state_patch(message, 1))
    negatives = {
        str(item.value)
        for item in patch.constraints
        if item.field == "material" and item.operator == "not_contains"
    }

    assert negatives == {"cotton", "wool"}


def test_semantic_fallback_drops_overlong_negation_span() -> None:
    message = (
        "I don't want a huge floral pattern that clashes with everything in "
        "my closet, but the color is fine."
    )
    rules = rule_state_patch(message, 1)
    patch = semantic_fallback_patch(message, 1, rules)

    assert "unresolved_negation" in rules.fallback_reasons
    assert not any(item.operator == "not_contains" for item in patch.constraints)


def test_semantic_fallback_treats_catalog_no_closure_as_literal() -> None:
    message = "I'm looking for leg warmers. No Closure closure."
    patch = semantic_fallback_patch(message, 1, rule_state_patch(message, 1))

    assert not any(item.operator == "not_contains" for item in patch.constraints)


def test_semantic_fallback_ignores_general_negative_feedback() -> None:
    message = "Those options are not quite right yet. Ask one specific attribute."
    patch = semantic_fallback_patch(message, 2, rule_state_patch(message, 2))

    assert not any(item.operator == "not_contains" for item in patch.constraints)


def test_semantic_fallback_parses_between_budget_range_as_hard_bounds() -> None:
    message = "Between $50 and $100 for boots."
    patch = semantic_fallback_patch(message, 1, rule_state_patch(message, 1))
    budgets = {
        (item.operator, item.value, item.strength)
        for item in patch.constraints
        if item.field == "budget"
    }

    assert ("gte", 50.0, "hard") in budgets
    assert ("lte", 100.0, "hard") in budgets


def test_semantic_fallback_parses_dash_budget_range_as_hard_bounds() -> None:
    message = "$50-$100 range works for me."
    patch = semantic_fallback_patch(message, 1, rule_state_patch(message, 1))
    budgets = {
        (item.operator, item.value, item.strength)
        for item in patch.constraints
        if item.field == "budget"
    }

    assert budgets == {("gte", 50.0, "hard"), ("lte", 100.0, "hard")}


def test_semantic_fallback_does_not_double_count_range_and_single_budget() -> None:
    message = "Under $80 if possible, but I could stretch to $100 for waterproof ones."
    patch = semantic_fallback_patch(message, 2, rule_state_patch(message, 2))
    budgets = [item for item in patch.constraints if item.field == "budget"]

    assert any(item.value == 80.0 and item.strength == "soft" for item in budgets)
    assert any(item.value == 100.0 and item.strength == "hard" for item in budgets)
    assert len(budgets) == 2


def test_resolve_semantic_patch_flags_implicit_override_without_marker(monkeypatch) -> None:
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "false")
    active = [Constraint(field="color", value="red", strength="hard").model_dump()]
    message = "Make it blue please."

    patch, _ = resolve_semantic_patch(
        message, 2, rule_state_patch(message, 2), active_constraints=active,
    )

    assert patch.action == "replace"
    assert "implicit_override_heuristic" in patch.fallback_reasons
    assert any(item.field == "color" and item.value == "blue" for item in patch.constraints)


def test_resolve_semantic_patch_keeps_additive_material_request(monkeypatch) -> None:
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "false")
    active = [Constraint(field="material", value="cotton", strength="hard").model_dump()]
    message = "Also wool please."

    patch, _ = resolve_semantic_patch(
        message, 2, rule_state_patch(message, 2), active_constraints=active,
    )

    assert patch.action == "add"
    assert "implicit_override_heuristic" not in patch.fallback_reasons


def test_resolve_semantic_patch_retries_transient_provider_failure(monkeypatch) -> None:
    calls: list[int] = []

    class FlakyCompletions:
        def create(self, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise TimeoutError("transient")
            payload = {
                "action": "add",
                "category": "shoes",
                "constraints": [],
                "semantic_query": "running shoes",
                "intent_summary": "running shoes",
                "language": "en",
                "confidence": 0.9,
            }
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
            )

    class FlakyOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FlakyCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FlakyOpenAI))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "true")
    message = "I need running shoes."

    patch, usage = resolve_semantic_patch(message, 1, rule_state_patch(message, 1))

    assert len(calls) == 2
    assert patch.parser == "deepseek"
    assert usage == {"prompt_tokens": 10, "completion_tokens": 5}


def test_resolve_semantic_patch_does_not_retry_non_transient_failure(monkeypatch) -> None:
    calls: list[int] = []

    class InvalidRequestCompletions:
        def create(self, **kwargs):
            calls.append(1)
            raise ValueError("invalid request")

    class InvalidRequestOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=InvalidRequestCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=InvalidRequestOpenAI))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "true")
    message = "I need running shoes."

    with pytest.raises(RuntimeError, match="Online intent failed.*ValueError"):
        resolve_semantic_patch(message, 1, rule_state_patch(message, 1))
    assert len(calls) == 1


def test_resolve_semantic_patch_tags_invalid_provider_json(monkeypatch) -> None:
    class BrokenCompletions:
        def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            )

    class BrokenOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=BrokenCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=BrokenOpenAI))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "true")
    message = "I need running shoes."

    with pytest.raises(RuntimeError, match="Online intent failed.*DeepSeekInvalidResponse"):
        resolve_semantic_patch(message, 1, rule_state_patch(message, 1))


def test_resolve_semantic_patch_tags_malformed_provider_response(monkeypatch) -> None:
    class EmptyCompletions:
        def create(self, **kwargs):
            return SimpleNamespace(choices=[], usage=None)

    class EmptyOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=EmptyCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=EmptyOpenAI))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "true")
    message = "I need running shoes."

    with pytest.raises(RuntimeError, match="Online intent failed.*DeepSeekInvalidResponse"):
        resolve_semantic_patch(message, 1, rule_state_patch(message, 1))


def test_resolve_semantic_patch_tags_persistent_outage(monkeypatch) -> None:
    calls: list[int] = []

    class DownCompletions:
        def create(self, **kwargs):
            calls.append(1)
            raise ConnectionError("down")

    class DownOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=DownCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=DownOpenAI))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("SHOPPING_AGENT_ENABLE_LLM", "true")
    message = "I need running shoes."

    with pytest.raises(RuntimeError, match="Online intent failed.*ConnectionError"):
        resolve_semantic_patch(message, 1, rule_state_patch(message, 1))
    assert len(calls) == 2
