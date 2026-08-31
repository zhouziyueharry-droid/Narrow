"""Part B: demo session state must persist across turns within one running
service process (the same runtime.agent instance), matching the "Browsing ->
system asks a feature -> multi-turn add material/color/budget" stable demo
scripts under docs/lambdamart_online_pro_report.md's sibling demo scenarios.
"""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from shopping_agent.web import create_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    catalog = tmp_path / "catalog.jsonl"
    catalog.write_text(json.dumps({
        "parent_asin": "A", "title": "Black shoes", "price": 20,
        "categories": ["Shoes"], "features": ["black"], "details": {}, "average_rating": 4.5,
    }) + "\n")
    yield create_app(catalog, tmp_path / "runs")


class StatefulAgent:
    """A minimal stand-in for ShoppingAgent that records every call it gets,
    so the test can prove the *same* instance handles every turn of a
    session rather than a fresh one being built per request."""

    def __init__(self):
        self.started = []
        self.chats = []
        self.released = []
        self._state = {}

    def start_session(self, sid):
        self.started.append(sid)
        self._state[sid] = {"turns": 0, "constraints": []}

    def chat(self, sid, message, top_k):
        state = self._state[sid]
        state["turns"] += 1
        state["constraints"].append(message)
        self.chats.append((sid, message))
        return {"message": f"turn {state['turns']} for '{message}'", "recommendations": [{"parent_asin": "A"}]}

    def get_intent_state(self, sid):
        state = self._state[sid]
        return {"semantic_query": " ".join(state["constraints"]), "turns": state["turns"]}

    def release_session(self, sid):
        self.released.append(sid)


def test_same_agent_instance_serves_every_turn_in_one_process(app, monkeypatch):
    import shopping_agent.web as web

    agent = StatefulAgent()
    build_calls = []

    def fake_create_agent(catalog):
        build_calls.append(catalog)
        return agent

    monkeypatch.setattr(web, "create_agent", fake_create_agent)

    with TestClient(app) as client:
        session = client.post("/api/chat/sessions").json()
        sid = session["id"]

        first = client.post(f"/api/chat/sessions/{sid}/messages", json={"message": "I want boots"})
        assert first.status_code == 200
        assert first.json()["intent"]["turns"] == 1

        second = client.post(f"/api/chat/sessions/{sid}/messages", json={"message": "waterproof please"})
        assert second.status_code == 200
        assert second.json()["intent"]["turns"] == 2
        # State from turn 1 is still there in turn 2's accumulated query.
        assert "boots" in second.json()["intent"]["semantic_query"]
        assert "waterproof" in second.json()["intent"]["semantic_query"]

        third = client.post(f"/api/chat/sessions/{sid}/messages", json={"message": "budget under 100"})
        assert third.json()["intent"]["turns"] == 3

    # The agent (and hence the LangGraph checkpointer inside it) was built
    # exactly once for the whole process, not once per turn or per request.
    assert len(build_calls) == 1
    assert agent.started == [sid]  # start_session only on the first message
    assert [message for _, message in agent.chats] == [
        "I want boots", "waterproof please", "budget under 100",
    ]


def test_two_concurrent_sessions_in_the_same_process_do_not_share_state(app, monkeypatch):
    import shopping_agent.web as web

    agent = StatefulAgent()
    monkeypatch.setattr(web, "create_agent", lambda catalog: agent)

    with TestClient(app) as client:
        sid_a = client.post("/api/chat/sessions").json()["id"]
        sid_b = client.post("/api/chat/sessions").json()["id"]

        client.post(f"/api/chat/sessions/{sid_a}/messages", json={"message": "red dress"})
        client.post(f"/api/chat/sessions/{sid_b}/messages", json={"message": "blue jeans"})
        response_a = client.post(f"/api/chat/sessions/{sid_a}/messages", json={"message": "size M"})

    assert "red dress" in response_a.json()["intent"]["semantic_query"]
    assert "blue jeans" not in response_a.json()["intent"]["semantic_query"]
    assert agent.started == [sid_a, sid_b]


def test_session_state_is_released_and_not_reused_after_deletion(app, monkeypatch):
    import shopping_agent.web as web

    agent = StatefulAgent()
    monkeypatch.setattr(web, "create_agent", lambda catalog: agent)

    with TestClient(app) as client:
        sid = client.post("/api/chat/sessions").json()["id"]
        client.post(f"/api/chat/sessions/{sid}/messages", json={"message": "hello"})
        assert client.delete(f"/api/chat/sessions/{sid}").status_code == 204

    assert agent.released == [sid]
