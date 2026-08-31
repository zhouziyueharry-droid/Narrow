import json

from scripts.build_metadata_stratified_catalog import build


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def product(identifier, price, rating_number, feature_count):
    return {
        "parent_asin": identifier,
        "price": price,
        "rating_number": rating_number,
        "features": ["f"] * feature_count,
        "description": [],
        "categories": ["Clothing", "Shoes"],
    }


def test_builds_exact_scaled_catalog_and_keeps_all_mandatory_targets(tmp_path):
    reference = tmp_path / "reference.jsonl"
    source = tmp_path / "source.jsonl"
    sessions = tmp_path / "public.jsonl"
    additional_sessions = tmp_path / "additional.jsonl"
    output = tmp_path / "catalog.jsonl"
    manifest = tmp_path / "manifest.json"
    reference_rows = [
        product("r1", 10, 10, 2), product("r2", 20, 30, 6),
        product("r3", 40, 100, 8), product("r4", 80, 300, 12),
    ]
    source_rows = [product(f"s{index}", 10, 10, 2) for index in range(3)]
    source_rows.append(product("TRAINING", 10, 10, 2))
    source_rows += [product(f"m{index}", 20, 30, 6) for index in range(4)]
    source_rows += [product(f"h{index}", 40, 100, 8) for index in range(4)]
    source_rows += [product(f"x{index}", 80, 300, 12) for index in range(3)]
    source_rows.append(product("PUBLIC", 80, 300, 12))
    write_jsonl(reference, reference_rows)
    write_jsonl(source, source_rows)
    write_jsonl(sessions, [{"sample_id": "public", "ground_truth": {"parent_asin": "PUBLIC"}}])
    write_jsonl(additional_sessions, [{"sample_id": "training", "ground_truth": {"parent_asin": "TRAINING"}}])

    result = build(source=source, reference=reference, official_sessions=sessions,
                   output=output, manifest=manifest, target_count=8, seed=7,
                   additional_mandatory_sessions=(additional_sessions,))

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 8
    assert len({row["parent_asin"] for row in rows}) == 8
    assert "PUBLIC" in {row["parent_asin"] for row in rows}
    assert "TRAINING" in {row["parent_asin"] for row in rows}
    assert result["official_public_targets"]["found_in_source"] == 1
    assert result["additional_mandatory_targets"]["found_in_source"] == 1
    assert result["selection"]["scale_multiplier"] == 2
    assert json.loads(manifest.read_text(encoding="utf-8"))["output"]["rows"] == 8


def test_can_exclude_official_targets_while_retaining_training_targets(tmp_path):
    reference = tmp_path / "reference.jsonl"
    source = tmp_path / "source.jsonl"
    public = tmp_path / "public.jsonl"
    training = tmp_path / "training.jsonl"
    output = tmp_path / "catalog.jsonl"
    manifest = tmp_path / "manifest.json"
    reference_rows = [
        product("r1", 10, 10, 2), product("r2", 20, 30, 6),
        product("r3", 40, 100, 8), product("r4", 80, 300, 12),
    ]
    source_rows = [product(f"s{index}", 10, 10, 2) for index in range(4)]
    source_rows += [product(f"m{index}", 20, 30, 6) for index in range(4)]
    source_rows += [product(f"h{index}", 40, 100, 8) for index in range(4)]
    source_rows += [product(f"x{index}", 80, 300, 12) for index in range(2)]
    source_rows += [product("PUBLIC", 80, 300, 12), product("TRAINING", 80, 300, 12)]
    write_jsonl(reference, reference_rows)
    write_jsonl(source, source_rows)
    write_jsonl(public, [{"sample_id": "public", "ground_truth": {"parent_asin": "PUBLIC"}}])
    write_jsonl(training, [{"sample_id": "training", "ground_truth": {"parent_asin": "TRAINING"}}])

    result = build(
        source=source, reference=reference, official_sessions=public,
        output=output, manifest=manifest, target_count=8, seed=7,
        additional_mandatory_sessions=(training,), exclude_official_targets=True,
    )

    identifiers = {json.loads(line)["parent_asin"] for line in output.read_text(encoding="utf-8").splitlines()}
    assert "PUBLIC" not in identifiers
    assert "TRAINING" in identifiers
    assert result["official_public_targets"]["retained_in_catalog"] == 0
    assert result["official_public_targets"]["policy"] == "excluded_from_training_catalog"
