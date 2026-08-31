import json

from shopping_agent.orchestration import graph as graph_module
from shopping_agent.retrieval.lexical import CatalogIndex


def test_graph_reuses_injected_catalog_index(monkeypatch, tmp_path):
    catalog_path = tmp_path / "catalog.jsonl"
    catalog_path.write_text(json.dumps({"parent_asin": "A", "title": "shoe", "features": [], "categories": []}) + "\n", encoding="utf-8")
    index = CatalogIndex(catalog_path)

    def fail_if_constructed(*_args, **_kwargs):
        raise AssertionError("CatalogIndex should be injected, not rebuilt")

    monkeypatch.setattr(graph_module, "CatalogIndex", fail_if_constructed)
    graph = graph_module.build_shopping_graph(catalog_path, catalog_index=index)
    assert graph is not None
