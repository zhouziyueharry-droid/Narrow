import json

from scripts.normalize_metadata_catalog_for_agent import normalize


def test_normalization_keeps_agent_fields_and_removes_media(tmp_path):
    source, output, manifest = tmp_path / "source.jsonl", tmp_path / "out.jsonl", tmp_path / "manifest.json"
    source.write_text(json.dumps({"parent_asin": "A", "title": "shoe", "features": ["leather"],
                                  "images": [{"url": "large"}], "videos": ["video"], "unknown": "x"}) + "\n", encoding="utf-8")
    result = normalize(source, output, manifest)
    row = json.loads(output.read_text(encoding="utf-8"))
    assert row["parent_asin"] == "A"
    assert row["title"] == "shoe"
    assert "images" not in row and "videos" not in row and "unknown" not in row
    assert result["output"]["rows"] == 1
