from __future__ import annotations

import json
from pathlib import Path

import yaml
from user_simulator.adapters import PythonAgentAdapter
from user_simulator.cli import PRESETS
from user_simulator.datasets import TechJamDatasetAdapter, build_realistic_scenarios
from user_simulator.models import NeedBasedGoal
from user_simulator.simulator import Simulator


def _write_fixture(tmp_path, scenario_type: str = "buying"):
    catalog_path = tmp_path / "catalog.jsonl"
    sessions_path = tmp_path / "public_set.jsonl"
    product = {
        "parent_asin": "A",
        "title": "Black Leather Running Shoe",
        "features": ["waterproof", "cushioned"],
        "details": {"Material": "leather", "Color": "black"},
        "description": ["running shoe"],
        "categories": ["Clothing, Shoes & Jewelry", "Women", "Shoes"],
        "store": "Example Brand",
        "price": 80.0,
    }
    profile = {
        "purchase_frequency": "3-4 prior purchases",
        "average_prior_rating": 4.5,
        "rating_style": "usually positive",
        "preference_tags": ["comfort"],
        "summary": "Prior purchases emphasize comfort.",
    }
    sample = {
        "sample_id": f"sample_{scenario_type}",
        "scenario_type": scenario_type,
        "user_profile": profile,
        "ground_truth": {"parent_asin": "A"},
    }
    catalog_path.write_text(json.dumps(product) + "\n", encoding="utf-8")
    sessions_path.write_text(json.dumps(sample) + "\n", encoding="utf-8")
    return catalog_path, sessions_path, profile


def test_yaml_configs_match_builtin_presets():
    root = Path(__file__).resolve().parents[1]
    config_paths = {
        "techjam": root / "configs" / "techjam_benchmark.yaml",
        "realistic": root / "configs" / "realistic.yaml",
        "realistic_hard": root / "configs" / "realistic_hard.yaml",
        "realistic_broad": root / "configs" / "realistic_broad.yaml",
        "realistic_scale_200k": root / "configs" / "realistic_scale_200k.yaml",
        "realistic_cross_category_500k": (
            root / "configs" / "realistic_cross_category_500k.yaml"
        ),
    }
    for name, path in config_paths.items():
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == PRESETS[name]


class AlwaysTargetAgent:
    def __init__(self):
        self.profile = None

    def reset(self, session_id, user_profile):
        self.profile = dict(user_profile)

    def respond(self, session_id, user_message, turn, top_k):
        return {
            "message": "Here are options.",
            "ask_attribute": "material",
            "recommendations": [{"parent_asin": "A"}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1},
        }


class AskThenTargetAgent(AlwaysTargetAgent):
    def respond(self, session_id, user_message, turn, top_k):
        response = super().respond(session_id, user_message, turn, top_k)
        if turn == 1:
            response["recommendations"] = []
        return response


def test_techjam_mode_preserves_profile_and_official_initial_message(tmp_path):
    catalog_path, sessions_path, profile = _write_fixture(tmp_path, "buying")
    dataset = TechJamDatasetAdapter(catalog_path, sessions_path)
    catalog = {product.product_id: product for product in dataset.load_products()}
    scenario = dataset.build_target_sessions()[0]
    agent = AlwaysTargetAgent()

    result = Simulator(catalog, PythonAgentAdapter(agent)).run_many([scenario])

    assert scenario.protocol == "techjam"
    assert scenario.user_profile == profile
    assert result["mode"] == "techjam"
    assert result["schema_version"] == "1.0"
    assert result["evaluation"]["hit_rate_at_10"] == 1.0
    assert result["evaluation"]["mttc"] == 1.0
    assert result["model_usage"]["agent"]["reported_token_usage"]["total_tokens"] == 3
    assert result["turn_metrics"]["total_executed_turns"] == 1
    assert result["latency"]["agent"]["call_count"] == 1
    assert result["latency"]["available"] is True
    assert agent.profile == profile
    assert result["sessions"][0]["conversation"][0]["user"] == (
        "I'm looking for Women Shoes. A key requirement is: leather."
    )


def test_techjam_intent_override_blocks_early_target_hit(tmp_path):
    catalog_path, sessions_path, _ = _write_fixture(tmp_path, "intent_override")
    dataset = TechJamDatasetAdapter(catalog_path, sessions_path)
    catalog = {product.product_id: product for product in dataset.load_products()}
    scenario = dataset.build_target_sessions()[0]
    override_turn = scenario.metadata["techjam"]["behavior"]["override"]["turn"]

    result = Simulator(catalog, PythonAgentAdapter(AlwaysTargetAgent())).run_many(
        [scenario]
    )

    assert result["sessions"][0]["turns"] == override_turn
    assert result["sessions"][0]["success"] is True
    assert result["evaluation"]["mttc"] == float(override_turn)
    assert (
        "Actually, ignore my earlier preference."
        in (result["sessions"][0]["conversation"][override_turn - 1]["user"])
    )
    assert result["sessions"][0]["override_count"] == 1


def test_techjam_browsing_and_boundary_dialogue_paths(tmp_path):
    for scenario_type in ("browsing", "boundary"):
        case_dir = tmp_path / scenario_type
        case_dir.mkdir()
        catalog_path, sessions_path, _ = _write_fixture(case_dir, scenario_type)
        dataset = TechJamDatasetAdapter(catalog_path, sessions_path)
        catalog = {product.product_id: product for product in dataset.load_products()}
        scenario = dataset.build_target_sessions()[0]

        result = Simulator(catalog, PythonAgentAdapter(AskThenTargetAgent())).run_many(
            [scenario]
        )
        conversation = result["sessions"][0]["conversation"]

        assert (
            conversation[0]["user"]
            == "I'm looking for Women Shoes, but I'm still exploring."
        )
        if scenario_type == "boundary":
            assert conversation[1]["user"] == (
                "I don't have a preference for material; please use your judgment."
            )
        else:
            assert conversation[1]["user"] == "For that, what matters is: leather."


def test_realistic_mode_builds_satisfiable_need_goal_without_extra_data(tmp_path):
    catalog_path, _, _ = _write_fixture(tmp_path, "buying")
    dataset = TechJamDatasetAdapter(catalog_path)
    products = list(dataset.load_products())
    catalog = {product.product_id: product for product in products}
    scenario = build_realistic_scenarios(
        products,
        count=1,
        persona_templates=["decisive_buyer"],
    )[0]

    result = Simulator(catalog, PythonAgentAdapter(AlwaysTargetAgent())).run_many(
        [scenario]
    )

    assert scenario.protocol == "realistic"
    assert isinstance(scenario.goal, NeedBasedGoal)
    assert result["mode"] == "realistic"
    assert result["evaluation"]["success_rate"] == 1.0
    assert (
        result["mode_specific_metrics"]["hard_constraint_satisfaction_at_acceptance"]
        == 1.0
    )


def test_hard_realistic_scenarios_cover_deterministic_pressure_variants(tmp_path):
    catalog_path = tmp_path / "catalog.jsonl"
    rows = []
    for index in range(8):
        rows.append(
            {
                "parent_asin": f"P{index}",
                "title": f"Product {index}",
                "features": [f"feature-{index}"],
                "details": {
                    "Color": f"color-{index}",
                    "Material": f"material-{index}",
                },
                "categories": ["Clothing", "Women"],
                "store": f"Brand {index}",
                "price": 50.0 + index,
            }
        )
    catalog_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    products = list(TechJamDatasetAdapter(catalog_path).load_products())

    scenarios = build_realistic_scenarios(
        products,
        count=4,
        difficulty_profile="hard_v1",
        budget_multiplier=1.02,
        min_soft_preferences=3,
        min_soft_matches=2,
        initial_disclosure_policy="category_only",
        min_turns_before_acceptance=2,
        require_no_pending_question=True,
        scheduled_variants=True,
    )

    assert {scenario.scenario_type for scenario in scenarios} == {
        "realistic_hard:hidden_preferences",
        "realistic_hard:preference_override",
        "realistic_hard:budget_relaxation",
        "realistic_hard:override_and_relaxation",
    }
    assert all(scenario.goal.min_soft_matches == 2 for scenario in scenarios)
    assert all(len(scenario.goal.soft_preferences) == 3 for scenario in scenarios)
    assert all(scenario.initial_disclosure_policy == "category_only" for scenario in scenarios)
    assert all(scenario.require_no_pending_question for scenario in scenarios)
    assert [scenario.min_turns_before_acceptance for scenario in scenarios] == [2, 3, 5, 5]


def test_broad_realistic_sampling_balances_coverage_dimensions(tmp_path):
    catalog_path = tmp_path / "catalog.jsonl"
    prices = [10.0, 20.0, 40.0, 80.0, 150.0]
    rows = []
    for band_index, price in enumerate(prices):
        for item_index in range(10):
            index = band_index * 10 + item_index
            rows.append(
                {
                    "parent_asin": f"P{index}",
                    "title": f"Product {index}",
                    "features": [f"feature-{index}"],
                    "details": {
                        "Color": f"color-{index}",
                        "Material": f"material-{index}",
                    },
                    "categories": ["Clothing", f"Category {index}"],
                    "store": f"Brand {index}",
                    "price": price,
                }
            )
    catalog_path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    products = list(TechJamDatasetAdapter(catalog_path).load_products())

    scenarios = build_realistic_scenarios(
        products,
        count=40,
        seed=20260829,
        difficulty_profile="broad_v1",
        budget_multiplier=1.02,
        min_soft_preferences=3,
        min_soft_matches=2,
        initial_disclosure_policy="category_only",
        min_turns_before_acceptance=2,
        require_no_pending_question=True,
        scheduled_variants=True,
        sampling_strategy="broad_coverage",
    )

    price_distribution = {}
    for scenario in scenarios:
        band = scenario.metadata["coverage"]["price_band"]
        price_distribution[band] = price_distribution.get(band, 0) + 1
    assert price_distribution == {
        "under_15": 8,
        "15_30": 8,
        "30_60": 8,
        "60_120": 8,
        "120_plus": 8,
    }
    assert len({scenario.goal.category for scenario in scenarios}) == 40
    assert len({scenario.metadata["seed_product_id"] for scenario in scenarios}) == 40
    assert all(
        scenario.metadata["coverage"]["sampling_strategy"] == "broad_coverage"
        for scenario in scenarios
    )
    assert {
        scenario.scenario_type: sum(
            item.scenario_type == scenario.scenario_type for item in scenarios
        )
        for scenario in scenarios
    } == {
        "realistic_broad:hidden_preferences": 10,
        "realistic_broad:preference_override": 10,
        "realistic_broad:budget_relaxation": 10,
        "realistic_broad:override_and_relaxation": 10,
    }


def test_realistic_acceptance_waits_until_agent_finishes_clarifying(tmp_path):
    catalog_path, _, _ = _write_fixture(tmp_path, "buying")
    dataset = TechJamDatasetAdapter(catalog_path)
    products = list(dataset.load_products())
    catalog = {product.product_id: product for product in products}
    scenario = build_realistic_scenarios(products, count=1)[0]
    scenario.min_turns_before_acceptance = 2
    scenario.require_no_pending_question = True

    class ClarifyThenFinishAgent(AlwaysTargetAgent):
        def respond(self, session_id, user_message, turn, top_k):
            response = super().respond(session_id, user_message, turn, top_k)
            response["ask_attribute"] = "material" if turn == 1 else None
            return response

    result = Simulator(
        catalog, PythonAgentAdapter(ClarifyThenFinishAgent())
    ).run_many([scenario])
    session = result["sessions"][0]

    assert session["success"] is True
    assert session["turns"] == 2
    assert session["acceptance_gate"]["blocked_candidate_events"] == 1
    assert session["conversation"][0]["acceptance_candidate"] is True
    assert session["conversation"][0]["acceptance_block_reason"] == (
        "minimum_conversation_turns_not_reached"
    )
    assert result["mode_specific_metrics"]["accepted_while_agent_asks"] == 0


def test_agent_adapter_keeps_first_ten_valid_unique_candidates():
    class DuplicateHeavyAgent:
        def reset(self, session_id, user_profile):
            pass

        def respond(self, session_id, user_message, turn, top_k):
            recommendations = [{"parent_asin": "A"}] * 12
            recommendations.extend({"parent_asin": f"P{index}"} for index in range(20))
            return {
                "message": "x",
                "ask_attribute": None,
                "recommendations": recommendations,
            }

    adapter = PythonAgentAdapter(DuplicateHeavyAgent())
    response = adapter.respond("s", "hello", 1, 10)

    assert [item.product_id for item in response.recommendations] == [
        "A",
        "P0",
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
    ]


def test_techjam_normalization_skips_invalid_catalog_ids_before_target(tmp_path):
    catalog_path, sessions_path, _ = _write_fixture(tmp_path, "buying")
    dataset = TechJamDatasetAdapter(catalog_path, sessions_path)
    catalog = {product.product_id: product for product in dataset.load_products()}
    scenario = dataset.build_target_sessions()[0]

    class InvalidFirstAgent(AlwaysTargetAgent):
        def respond(self, session_id, user_message, turn, top_k):
            response = super().respond(session_id, user_message, turn, top_k)
            response["recommendations"] = [
                {"parent_asin": f"INVALID_{index}"} for index in range(15)
            ] + [{"parent_asin": "A"}]
            return response

    result = Simulator(catalog, PythonAgentAdapter(InvalidFirstAgent())).run_many(
        [scenario]
    )

    assert result["evaluation"]["hit_rate_at_10"] == 1.0
    assert result["sessions"][0]["acceptance_rank"] == 1


def test_techjam_invalid_message_discards_recommendations(tmp_path):
    catalog_path, sessions_path, _ = _write_fixture(tmp_path, "buying")
    dataset = TechJamDatasetAdapter(catalog_path, sessions_path)
    catalog = {product.product_id: product for product in dataset.load_products()}
    scenario = dataset.build_target_sessions()[0]

    class InvalidMessageAgent(AlwaysTargetAgent):
        def respond(self, session_id, user_message, turn, top_k):
            response = super().respond(session_id, user_message, turn, top_k)
            response["message"] = None
            return response

    result = Simulator(catalog, PythonAgentAdapter(InvalidMessageAgent())).run_many(
        [scenario]
    )

    assert result["evaluation"]["hit_rate_at_10"] == 0.0
    assert len(result["sessions"][0]["agent_errors"]) == 10
