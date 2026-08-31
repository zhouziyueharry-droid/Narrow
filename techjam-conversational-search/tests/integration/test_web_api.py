import json
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from shopping_agent.web import ARCHIVE, Evaluation, create_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    catalog = tmp_path/"catalog.jsonl"
    catalog.write_text(json.dumps({"parent_asin": "A", "title": "Black shoes", "price": 20,
        "categories": ["Shoes"], "features": ["black"], "details": {}, "average_rating": 4.5}) + "\n")
    # HTTP settings update process environment; do not leak them to other suites.
    with patch.dict("os.environ"):
        yield create_app(catalog, tmp_path/"runs")


def test_archived_result_and_trace_are_readonly_and_portable(app):
    with TestClient(app) as client:
        runs = client.get("/api/evaluations").json()["runs"]
        assert len(runs) == 1 and runs[0]["protected"]
        sid = runs[0]["id"]
        result = client.get(f"/api/evaluations/{sid}/result").json()
        assert len(result["sessions"]) == 200
        assert sum(len(s["conversation"]) for s in result["sessions"]) == 453
        assert result["metrics"]["hit_rate_at_10"] == .97
        trace = client.get(f"/api/evaluations/{sid}/diagnostics")
        assert trace.content == (ARCHIVE/"trace.json").read_bytes()
        response = client.request("DELETE", "/api/evaluations", json={"ids": [sid]})
        assert response.status_code == 409
        assert (ARCHIVE/"trace.json").exists()


def test_local_api_blocks_foreign_origins_credentials_redirect_and_missing_key(app):
    with TestClient(app) as client:
        assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
        assert client.post("/api/chat/sessions", headers={"Origin": "https://evil.example"}).status_code == 403
        settings = {k: v for k, v in client.get("/api/settings").json().items()
                    if k not in {"revision", "deepseek_configured", "model_presets"}}
        assert client.put("/api/settings", json=settings | {"base_url": "https://evil.example"}).status_code == 422
        assert client.put("/api/settings", json=settings | {"provider": "deepseek"}).status_code == 422
        assert client.post("/api/evaluations", json={"mode": "simulator-realistic", "count": 101}).status_code == 422
        assert client.get("/api/evaluations/missing/result").status_code == 404


def test_chat_uses_existing_final_agent_contract_and_enriches_products(app, monkeypatch):
    import shopping_agent.web as web
    class Agent:
        def start_session(self, sid):
            self.sid = sid
        def chat(self, sid, message, top_k):
            assert sid == self.sid and message == "shoes" and top_k == 10
            return {"message": "Here are shoes", "recommendations": [{"parent_asin": "A"}]}
        def get_intent_state(self, sid):
            return {"semantic_query": "black shoes"}
        def release_session(self, sid):
            assert sid == self.sid
    monkeypatch.setattr(web, "create_agent", lambda catalog: Agent())
    with TestClient(app) as client:
        session = client.post("/api/chat/sessions").json()
        response = client.post(f'/api/chat/sessions/{session["id"]}/messages', json={"message": "shoes"})
        assert response.status_code == 200
        assert response.json()["recommendations"][0]["title"] == "Black shoes"
        assert response.json()["intent"]["semantic_query"] == "black shoes"
        assert client.delete(f'/api/chat/sessions/{session["id"]}').status_code == 204


def test_worker_commands_reuse_final_scripts_without_demo_backend(app):
    runtime = app.state.runtime
    for mode in ("native", "simulator-techjam", "simulator-realistic"):
        options = Evaluation(mode=mode, count=2, reranker="lambdamart")
        job = {"id": "test", "mode": mode, "config": options.model_dump(exclude={"mode"})}
        command = runtime.command(job)
        assert not any("demo_api" in argument for argument in command)
        if mode == "native":
            assert "--no-llm" in command
            assert command[command.index("--ltr-model-dir")+1].endswith("lambdamart_synthetic_2000")
        else:
            assert "user_simulator.cli" in command
            assert "shopping_agent.web:create_agent" in command


def test_delete_cannot_escape_run_directory(app, tmp_path):
    external = tmp_path/"must_keep.txt"
    external.write_text("keep")
    app.state.runtime.jobs[".."] = {"id": "..", "status": "completed"}
    with TestClient(app) as client:
        response = client.request("DELETE", "/api/evaluations", json={"ids": [".."]})
        assert response.status_code == 409
        assert external.read_text() == "keep"
