import importlib.util
import json
from pathlib import Path


def _load_prepare(script_name):
    script_path = Path(__file__).resolve().parents[2] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prepare


prepare_single = _load_prepare("prepare_amazon_reviews_broad_catalog.py")
prepare_cross_category = _load_prepare(
    "prepare_amazon_reviews_cross_category_catalog.py"
)


def _write_metadata(path, prefix, count):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for index in range(count):
            handle.write(
                json.dumps(
                    {
                        "parent_asin": f"{prefix}{index:04d}",
                        "title": f"{prefix} product {index}",
                        "price": 10 + index,
                        "categories": [prefix, f"{prefix} leaf {index % 3}"],
                    }
                )
                + "\n"
            )


def test_single_category_preparation_can_trim_to_exact_target(tmp_path):
    source = tmp_path / "Clothing" / "meta.jsonl"
    output = tmp_path / "scale_200k.jsonl"
    manifest_path = tmp_path / "manifest.json"
    _write_metadata(source, "clothing", 40)

    manifest = prepare_single(
        source,
        output,
        manifest_path,
        sample_points=30,
        target_products=20,
        seed=7,
    )

    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 20
    assert len({row["parent_asin"] for row in rows}) == 20
    assert manifest["sampling"]["target_products"] == 20
    assert manifest["sampling"]["unique_products_written"] == 20


def test_cross_category_preparation_hits_exact_target_without_clothing(tmp_path):
    first = tmp_path / "Beauty" / "meta.jsonl"
    second = tmp_path / "Appliances" / "meta.jsonl"
    output = tmp_path / "cross_500k.jsonl"
    manifest_path = tmp_path / "manifest.json"
    _write_metadata(first, "beauty", 20)
    _write_metadata(second, "appliance", 10)

    manifest = prepare_cross_category(
        [first, second],
        output,
        manifest_path,
        target_products=24,
        seed=11,
    )

    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 24
    assert len({row["parent_asin"] for row in rows}) == 24
    assert sum(manifest["coverage"]["source_category_distribution"].values()) == 24
    assert manifest["clothing_source_used"] is False
    assert manifest["official_metric_contract"] is False
