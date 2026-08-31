import json

from scripts.generate_metadata_matched_scenarios import generate


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def product(identifier, rating, price=20, features=6):
    return {"parent_asin": identifier, "rating_number": rating, "price": price,
            "features": ["f"] * features, "description": [], "categories": ["Clothing", "Shoes"]}


def test_generates_sessions_without_public_target_overlap(tmp_path):
    reference = tmp_path / "reference.jsonl"
    catalog = tmp_path / "catalog.jsonl"
    public = tmp_path / "public.jsonl"
    output = tmp_path / "sessions.jsonl"
    manifest = tmp_path / "manifest.json"
    write_jsonl(reference, [product("PUBLIC_A", 1000), product("PUBLIC_B", 10000, 30, 8)])
    write_jsonl(catalog, [product("PUBLIC_A", 1000), product("PUBLIC_B", 10000, 30, 8),
                           product("A", 1100), product("B", 1200), product("C", 9000, 30, 8),
                           product("D", 11000, 30, 8)])
    write_jsonl(public, [
        {"sample_id": "p1", "scenario_type": "buying", "user_profile": {"summary": "a"},
         "ground_truth": {"parent_asin": "PUBLIC_A"}, "category_bucket": "clothing", "difficulty_bucket": "easy"},
        {"sample_id": "p2", "scenario_type": "browsing", "user_profile": {"summary": "b"},
         "ground_truth": {"parent_asin": "PUBLIC_B"}, "category_bucket": "clothing", "difficulty_bucket": "medium"},
    ])
    result = generate(catalog=catalog, reference_catalog=reference, public_sessions=public,
                      output=output, manifest=manifest, count=4, seed=7, sample_prefix="test")
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 4
    assert {row["scenario_type"] for row in rows} == {"buying", "browsing"}
    assert not {row["ground_truth"]["parent_asin"] for row in rows} & {"PUBLIC_A", "PUBLIC_B"}
    assert result["output"]["official_target_overlap_rows"] == 0
