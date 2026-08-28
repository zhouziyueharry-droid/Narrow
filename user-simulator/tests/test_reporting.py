from __future__ import annotations

import json

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
    assert result["sessions"][0]["goal_snapshot"]["target_product_id"] == "A"
    assert result["sessions"][0]["conversation"][0]["user_dialogue_act"]["type"] == (
        "INITIAL_REQUEST"
    )
    assert result["sessions"][0]["conversation"][0]["agent_usage_reported"] is True

    report = render_markdown(result)
    for heading in (
        "## Evaluation",
        "## Turn metrics",
        "## Latency",
        "## Model usage",
        "## Mode-specific metrics",
    ):
        assert heading in report


def test_session_persists_agent_layer_trace():
    class TraceAgent(OneTurnAgent):
        def get_turn_trace(self, session_id, turn, *, candidate_limit=20):
            return [
                {
                    "step": 1,
                    "nodes": ["understand_user"],
                    "updates": {"semantic_patch": {"action": "add"}},
                },
                {
                    "step": 2,
                    "nodes": ["rank_candidates"],
                    "updates": {"ranked_candidates": {"count": 1, "top": []}},
                },
            ]

    catalog = {"A": Product("A", "Shoe")}
    scenario = ScenarioSpec(
        scenario_id="trace-sample",
        goal=TargetProductGoal("goal", "A"),
        persona_template="decisive_buyer",
        protocol="techjam",
        scenario_type="buying",
    )
    result = Simulator(catalog, PythonAgentAdapter(TraceAgent())).run_many([scenario])
    turn = result["sessions"][0]["conversation"][0]

    assert [item["nodes"] for item in turn["agent_layer_trace"]] == [
        ["understand_user"],
        ["rank_candidates"],
    ]
    assert turn["agent_trace_error"] is None


def test_session_records_unavailable_agent_trace():
    catalog = {"A": Product("A", "Shoe")}
    scenario = ScenarioSpec(
        scenario_id="no-trace-sample",
        goal=TargetProductGoal("goal", "A"),
        persona_template="decisive_buyer",
        protocol="techjam",
        scenario_type="buying",
    )
    result = Simulator(catalog, PythonAgentAdapter(OneTurnAgent())).run_many([scenario])
    turn = result["sessions"][0]["conversation"][0]

    assert turn["agent_layer_trace"] == []
    assert turn["agent_trace_error"] == "agent_trace_unavailable"


def test_session_journals_flush_and_agent_state_is_released(tmp_path):
    class ReleasingAgent(OneTurnAgent):
        def __init__(self):
            self.released = []

        def release_session(self, session_id):
            self.released.append(session_id)

    agent = ReleasingAgent()
    catalog = {"A": Product("A", "Shoe")}
    scenario = ScenarioSpec(
        scenario_id="journal-sample",
        goal=TargetProductGoal("goal", "A"),
        persona_template="decisive_buyer",
        protocol="techjam",
        scenario_type="buying",
    )
    session_path = tmp_path / "sessions.jsonl"
    event_path = tmp_path / "events.jsonl"

    result = Simulator(catalog, PythonAgentAdapter(agent)).run_many(
        [scenario], session_output=session_path, event_output=event_path
    )

    persisted = [json.loads(line) for line in session_path.read_text().splitlines()]
    events = [json.loads(line) for line in event_path.read_text().splitlines()]
    assert persisted[0]["scenario_id"] == "journal-sample"
    assert [event["event"] for event in events] == [
        "session_started",
        "session_completed",
    ]
    assert len(agent.released) == 1
    assert result["sessions"][0]["session_release_error"] is None
