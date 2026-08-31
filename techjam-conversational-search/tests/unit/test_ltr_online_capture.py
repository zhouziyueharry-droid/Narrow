import json
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("layout", ["bundle", "training_output"])
def test_online_audit_loads_control_weights_without_old_evaluation_runs(tmp_path, layout):
    pytest.importorskip("lightgbm")
    from scripts.ltr_online_support import OnlineAudit, sha256

    bundle = Path(__file__).resolve().parents[2]/"models/lambdamart_synthetic_2000"
    model_dir = tmp_path/"model"
    model_dir.mkdir()
    for name in ("model.txt", "metadata.json", "idf.json"):
        (model_dir/name).write_bytes((bundle/name).read_bytes())
    weights_path = (model_dir if layout == "bundle" else tmp_path)/"same_data_linear_weights.json"
    weights_path.write_bytes((bundle/"same_data_linear_weights.json").read_bytes())
    audit = OnlineAudit(tmp_path, model_dir, "lambdamart")
    try:
        assert audit.config()["linear_weights_sha256"] == sha256(weights_path)
        ranked = audit.rank([{"parent_asin": "A", "title": "black shoes", "rrf_score": .04}],
                            query="black shoes", category="shoes", constraints=[])
        assert [item["parent_asin"] for item in ranked] == ["A"]
        record = json.loads((tmp_path/"rank_calls.jsonl").read_text(encoding="utf-8"))
        assert set(record["counterfactual_scores"]) == {"precise", "linear_same_data", "lambdamart"}
    finally:
        audit.close()


def capture(tmp_path):
    pytest.importorskip("lightgbm")
    from scripts.ltr_online_support import OnlineAudit
    audit = OnlineAudit.__new__(OnlineAudit)
    audit.context = {"sample_id": "fixture", "turn": 2}
    audit.lock = threading.Lock()
    audit.llm_file = (tmp_path/"llm.jsonl").open("w", encoding="utf-8")
    audit.rank_file = (tmp_path/"rank.jsonl").open("w", encoding="utf-8")
    audit._original_create = None
    return audit


def test_sdk_capture_preserves_response_context_and_omits_auth(tmp_path, monkeypatch):
    pytest.importorskip("openai")
    from openai.resources.chat.completions import Completions
    response = SimpleNamespace(model_dump=lambda **kw: {"id": "fake", "usage": {"prompt_tokens": 3}}, _request_id="req")
    observed = []
    def original(resource, *args, **kwargs):
        observed.append(kwargs)
        return response
    monkeypatch.setattr(Completions, "create", original)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-secret")
    audit = capture(tmp_path)
    audit.install_llm_capture()
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(Completions.create, None, model="fixture",
            messages=[{"role": "user", "content": "JSON dialogue decision fixture-secret"}],
            extra_headers={"Authorization": "Bearer fixture-secret"}).result()
    audit.close()
    assert result is response
    assert observed[0]["extra_headers"]["Authorization"] == "Bearer fixture-secret"
    raw = (tmp_path/"llm.jsonl").read_text(encoding="utf-8")
    assert "fixture-secret" not in raw and "Authorization" not in raw
    rows = [json.loads(line) for line in raw.splitlines()]
    assert [r["event"] for r in rows] == ["started", "completed"]
    assert all(r["sample_id"] == "fixture" and r["turn"] == 2 for r in rows)
    assert rows[0]["purpose"] == "dialogue_decision"
    assert rows[0]["call_id"] == rows[1]["call_id"]
    assert Completions.create is original


def test_sdk_capture_records_errors_without_suppressing_them(tmp_path, monkeypatch):
    pytest.importorskip("openai")
    from openai.resources.chat.completions import Completions
    def original(*args, **kwargs):
        raise TimeoutError("fixture timeout")
    monkeypatch.setattr(Completions, "create", original)
    audit = capture(tmp_path)
    audit.install_llm_capture()
    try:
        with pytest.raises(TimeoutError, match="fixture timeout"):
            Completions.create(None, model="fixture", messages=[])
    finally:
        audit.close()
    rows = [json.loads(line) for line in (tmp_path/"llm.jsonl").read_text().splitlines()]
    assert [r["event"] for r in rows] == ["started", "error"]
    assert rows[-1]["error_type"] == "TimeoutError"
