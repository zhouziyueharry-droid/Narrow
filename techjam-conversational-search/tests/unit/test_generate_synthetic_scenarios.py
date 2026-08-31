from __future__ import annotations

from collections import Counter

from scripts import generate_synthetic_scenarios as generator


def _product() -> dict:
    return {
        "price": 25.0,
        "features": ["a", "b", "c", "d", "e", "f"],
        "rating_number": 5_000,
    }


def test_generate_excludes_official_targets_and_preserves_distribution(monkeypatch):
    products = {asin: _product() for asin in ["OFFICIAL", "A", "B", "C", "D"]}
    official = [
        {
            "sample_id": "official_1",
            "scenario_type": "buying",
            "user_profile": {"summary": "profile"},
            "ground_truth": {"parent_asin": "OFFICIAL"},
        }
    ]
    monkeypatch.setattr(
        generator,
        "catalog_index",
        lambda _path: (set(products), {}, products),
    )
    monkeypatch.setattr(generator, "load_jsonl", lambda _path: official)

    rows = generator.generate(
        catalog_path="catalog.jsonl",
        dataset_path="public_set.jsonl",
        count=100,
        seed=20260831,
        min_features=6,
        min_rating_number=1_000,
        price_min=5.0,
        price_max=90.0,
        sample_prefix="synth5k",
    )

    assert len(rows) == 100
    assert len({row["sample_id"] for row in rows}) == 100
    assert Counter(row["scenario_type"] for row in rows) == {
        "buying": 40,
        "browsing": 40,
        "intent_override": 15,
        "boundary": 5,
    }
    target_counts = Counter(row["ground_truth"]["parent_asin"] for row in rows)
    assert "OFFICIAL" not in target_counts
    assert set(target_counts) == {"A", "B", "C", "D"}
    assert max(target_counts.values()) - min(target_counts.values()) <= 1
