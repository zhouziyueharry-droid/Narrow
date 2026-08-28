from __future__ import annotations

import argparse
import copy
import importlib
import json
import os
from pathlib import Path

import yaml

from .adapters import PythonAgentAdapter
from .datasets import TechJamDatasetAdapter, build_realistic_scenarios
from .reporting import render_markdown
from .simulator import Simulator
from .verbalizers import OpenAICompatibleVerbalizer, TemplateVerbalizer

PRESETS: dict[str, dict] = {
    "techjam": {
        "version": "0.3",
        "language": "en",
        "mode": "techjam",
        "seed": 42,
        "max_turns": 10,
        "top_k": 10,
        "dataset": {
            "name": "techjam",
            "catalog_path": "data/raw/techjam/catalog.jsonl",
            "sessions_path": "data/raw/techjam/public_set.jsonl",
        },
        "persona": {"default": "casual_browser"},
        "override": {
            "scheduled_enabled": True,
            "persona_driven_enabled": False,
        },
        "verbalizer": {"type": "template"},
        "agent": {
            "adapter": "python",
            "class_path": "shopping_agent.agent:ShoppingAgent",
        },
    },
    "realistic": {
        "version": "0.3",
        "language": "en",
        "mode": "realistic",
        "seed": 42,
        "max_turns": 10,
        "top_k": 10,
        "dataset": {
            "name": "catalog",
            "catalog_path": "data/raw/techjam/catalog.jsonl",
            "scenario_count": 100,
        },
        "persona": {
            "templates": [
                "decisive_buyer",
                "casual_browser",
                "bargain_hunter",
                "brand_loyalist",
                "picky_shopper",
                "novice_shopper",
                "expert_shopper",
                "indecisive_shopper",
            ]
        },
        "override": {"persona_driven_enabled": True},
        "verbalizer": {"type": "template"},
        "agent": {
            "adapter": "python",
            "class_path": "shopping_agent.agent:ShoppingAgent",
        },
    },
}


def _load_object(path: str):
    module_name, _, attr = path.partition(":")
    if not module_name or not attr:
        raise ValueError("agent.class_path must be in module:attribute form")
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def _environment_flag(name: str) -> bool | None:
    value = os.environ.get(name)
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _agent_runtime_metadata(config: dict) -> dict:
    agent_cfg = config.get("agent", {})
    llm_enabled = _environment_flag("SHOPPING_AGENT_ENABLE_LLM")
    provider = agent_cfg.get("provider")
    model = agent_cfg.get("model")
    if provider is None and llm_enabled is False:
        provider = "local"
    elif (
        provider is None and llm_enabled is True and os.environ.get("DEEPSEEK_API_KEY")
    ):
        provider = "deepseek"
    if model is None and provider == "deepseek":
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    return {
        "class_path": agent_cfg.get("class_path"),
        "provider": provider or "unspecified",
        "model": model,
        "llm_enabled": llm_enabled,
    }


def _load_config(path: str) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _config_from_args(args: argparse.Namespace) -> dict:
    if args.preset:
        config = copy.deepcopy(PRESETS[args.preset])
    else:
        config = _load_config(args.config)
    if config.get("mode") == "benchmark":
        config["mode"] = "techjam"
    dataset = config.setdefault("dataset", {})
    if args.catalog_path:
        dataset["catalog_path"] = args.catalog_path
    if args.sessions_path:
        dataset["sessions_path"] = args.sessions_path
    if args.agent_class:
        config.setdefault("agent", {})["class_path"] = args.agent_class
    if args.verbalizer:
        config["verbalizer"] = {
            "type": "openai_compatible"
            if args.verbalizer == "deepseek"
            else "template",
            "provider": args.verbalizer,
        }
    return config


def _validation_errors(config: dict) -> list[str]:
    errors: list[str] = []
    mode = config.get("mode")
    if mode not in {"techjam", "realistic"}:
        errors.append("mode must be techjam or realistic")
    if config.get("language", "en") != "en":
        errors.append("v0.2 supports English only")
    if int(config.get("max_turns", 10)) < 1:
        errors.append("max_turns must be >= 1")
    if mode == "techjam" and int(config.get("max_turns", 10)) != 10:
        errors.append("TechJam mode requires max_turns=10")
    if mode == "techjam" and int(config.get("top_k", 10)) != 10:
        errors.append("TechJam mode requires top_k=10")
    dataset = config.get("dataset", {})
    if not dataset.get("catalog_path"):
        errors.append("dataset.catalog_path is required")
    if mode == "techjam" and not dataset.get("sessions_path"):
        errors.append("TechJam mode requires dataset.sessions_path")
    if mode == "realistic" and int(dataset.get("scenario_count", 100)) < 1:
        errors.append("realistic dataset.scenario_count must be >= 1")
    if mode == "techjam" and config.get("verbalizer", {}).get("type") != "template":
        errors.append("TechJam mode requires the deterministic template verbalizer")
    agent = config.get("agent", {})
    if not agent.get("class_path"):
        errors.append("agent.class_path is required")
    return errors


def cmd_validate(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    errors = _validation_errors(config)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"valid": True, "mode": config["mode"]}, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    errors = _validation_errors(config)
    if errors:
        raise ValueError("; ".join(errors))

    mode = config["mode"]
    verbalizer_cfg = config.get("verbalizer", {})
    if (
        mode == "realistic"
        and verbalizer_cfg.get("type", "template") == "openai_compatible"
    ):
        verbalizer = OpenAICompatibleVerbalizer(
            provider=verbalizer_cfg.get("provider"),
            temperature=float(verbalizer_cfg.get("temperature", 0.2)),
            max_tokens=int(verbalizer_cfg.get("max_tokens", 120)),
            timeout=int(verbalizer_cfg.get("timeout", 30)),
        )
        if not verbalizer.configured:
            raise ValueError(
                "DeepSeek verbalizer requires DEEPSEEK_API_KEY/LLM_API_KEY and DEEPSEEK_MODEL/LLM_MODEL"
            )
    else:
        verbalizer = TemplateVerbalizer()

    dataset_cfg = config["dataset"]
    adapter = TechJamDatasetAdapter(
        dataset_cfg["catalog_path"], dataset_cfg.get("sessions_path")
    )
    products = list(adapter.load_products())
    catalog = {product.product_id: product for product in products}
    max_turns = int(config.get("max_turns", 10))
    if mode == "techjam":
        scenarios = adapter.build_target_sessions(
            persona_template=config.get("persona", {}).get("default", "casual_browser"),
            max_turns=max_turns,
        )
    else:
        scenario_count = int(dataset_cfg.get("scenario_count", 100))
        if args.limit:
            scenario_count = min(scenario_count, args.limit)
        scenarios = build_realistic_scenarios(
            products,
            count=scenario_count,
            seed=int(config.get("seed", 42)),
            max_turns=max_turns,
            persona_templates=config.get("persona", {}).get("templates"),
            persona_driven_override_enabled=bool(
                config.get("override", {}).get("persona_driven_enabled", True)
            ),
        )

    agent_cfg = config.get("agent", {})
    agent_cls = _load_object(agent_cfg["class_path"])
    agent = agent_cls(dataset_cfg["catalog_path"])
    agent_adapter = PythonAgentAdapter(agent)

    simulator = Simulator(
        catalog,
        agent_adapter,
        verbalizer,
        top_k=int(config.get("top_k", 10)),
        agent_metadata=_agent_runtime_metadata(config),
    )
    selected = scenarios[: args.limit] if args.limit else scenarios
    result = simulator.run_many(
        selected,
        session_output=args.session_output,
        event_output=args.event_output,
    )
    output = Path(args.output or f"runs/{mode}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.report_output:
        report_output = Path(args.report_output)
        report_output.parent.mkdir(parents=True, exist_ok=True)
        report_output.write_text(render_markdown(result), encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "sessions"}, indent=2
        )
    )
    return 0


def _add_config_source(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--preset", choices=sorted(PRESETS))
    source.add_argument("--config")
    parser.add_argument("--catalog-path")
    parser.add_argument("--sessions-path")
    parser.add_argument("--agent-class")
    parser.add_argument("--verbalizer", choices=("template", "deepseek"))


def main() -> int:
    parser = argparse.ArgumentParser(prog="user-simulator")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    _add_config_source(validate)
    validate.set_defaults(func=cmd_validate)

    run = sub.add_parser("run")
    _add_config_source(run)
    run.add_argument("--output")
    run.add_argument("--report-output")
    run.add_argument("--session-output")
    run.add_argument("--event-output")
    run.add_argument("--limit", type=int)
    run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
