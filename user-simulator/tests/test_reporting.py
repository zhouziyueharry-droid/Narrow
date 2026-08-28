from __future__ import annotations

from user_simulator.adapters import PythonAgentAdapter
from user_simulator.models import Product, ScenarioSpec, TargetProductGoal
from user_simulator.reporting import render_markdown
from user_simulator.simulator import Simulator


class OneTurnAgent:
    def reset(self, session_id, user_profile):
        pass

    def respond(self, session_id, user_message, turn, top_k):
        return {
            "message": "Here is the target.",
            "ask_attribute": None,
            "recommendations": [{"parent_asin": "A"}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2},
        }


def test_unified_report_schema_and_markdown_sections():
    catalog = {"A": Product("A", "Shoe")}
    scenario = ScenarioSpec(
        scenario_id="sample",
        goal=TargetProductGoal("goal", "A"),
        persona_template="decisive_buyer",
        protocol="techjam",
        scenario_type="buying",
    )
    result = Simulator(
        catalog,
        PythonAgentAdapter(OneTurnAgent()),
        agent_metadata={
            "class_path": "tests.test_reporting:OneTurnAgent",
            "provider": "local",
            "model": None,
            "llm_enabled": False,
        },
    ).run_many([scenario])

    assert {
        "evaluation",
        "turn_metrics",
        "latency",
        "model_usage",
        "mode_specific_metrics",
    }.issubset(result)
    assert result["evaluation"]["official_metric_contract"] is True
    assert result["turn_metrics"]["executed_turn_distribution"]["1"] == 1
    assert result["latency"]["agent"]["call_count"] == 1
    assert result["model_usage"]["agent"]["respond_calls"] == 1
    assert result["model_usage"]["agent"]["api_calls"] == 0
    assert (
        result["model_usage"]["combined"]["reported_token_usage"]["total_tokens"] == 6
    )
    assert result["sessions"][0]["conversation"][0]["agent_latency_ms"] >= 0

    report = render_markdown(result)
    for heading in (
        "## Evaluation",
        "## Turn metrics",
        "## Latency",
        "## Model usage",
        "## Mode-specific metrics",
    ):
        assert heading in report
