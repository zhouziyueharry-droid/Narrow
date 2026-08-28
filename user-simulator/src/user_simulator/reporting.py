from __future__ import annotations

from typing import Any


def _format(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return str(value)


def _key_value_table(values: dict[str, Any]) -> list[str]:
    rows = ["| Metric | Value |", "|---|---:|"]
    rows.extend(
        f"| `{key}` | {_format(value)} |"
        for key, value in values.items()
        if not isinstance(value, dict)
    )
    return rows


def render_markdown(result: dict[str, Any], title: str | None = None) -> str:
    mode = str(result.get("mode", "unknown"))
    display_mode = "TechJam" if mode == "techjam" else mode.title()
    lines = [
        f"# {title or f'{display_mode} simulator evaluation'}",
        "",
        f"Schema version: `{result.get('schema_version', 'unknown')}`",
        "",
        "## Evaluation",
        "",
        *_key_value_table(result.get("evaluation", {})),
        "",
        "## Turn metrics",
        "",
    ]

    turn_metrics = result.get("turn_metrics", {})
    lines.extend(
        _key_value_table(
            {
                key: value
                for key, value in turn_metrics.items()
                if key
                not in {"executed_turn_distribution", "first_hit_turn_distribution"}
            }
        )
    )
    lines.extend(["", "| Turn | Executed sessions | First hits |", "|---:|---:|---:|"])
    executed = turn_metrics.get("executed_turn_distribution", {})
    first_hits = turn_metrics.get("first_hit_turn_distribution", {})
    for turn in range(1, int(turn_metrics.get("max_turns", 0)) + 1):
        lines.append(
            f"| {turn} | {executed.get(str(turn), 0)} | {first_hits.get(str(turn), 0)} |"
        )

    lines.extend(["", "## Latency", ""])
    latency = result.get("latency", {})
    lines.extend(
        [
            f"Clock: `{latency.get('clock', 'unknown')}`; unit: `{latency.get('unit', 'unknown')}`.",
            "",
            "| Component | Count | Total | Mean | P50 | P95 | P99 | Max |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for key, label in (
        ("agent", "Agent"),
        ("user_generation", "User generation"),
        ("session_wall", "Session wall"),
    ):
        values = latency.get(key, {})
        count = values.get("call_count", values.get("session_count", 0))
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                label,
                _format(count),
                _format(values.get("total_ms")),
                _format(values.get("mean_ms")),
                _format(values.get("p50_ms")),
                _format(values.get("p95_ms")),
                _format(values.get("p99_ms")),
                _format(values.get("max_ms")),
            )
        )

    lines.extend(["", "## Model usage", ""])
    model_usage = result.get("model_usage", {})
    agent = model_usage.get("agent", {})
    verbalizer = model_usage.get("user_verbalizer", {})
    combined = model_usage.get("combined", {})
    agent_tokens = agent.get("reported_token_usage", {})
    verbalizer_tokens = {
        "prompt_tokens": verbalizer.get("prompt_tokens", 0),
        "completion_tokens": verbalizer.get("completion_tokens", 0),
        "total_tokens": verbalizer.get("total_tokens", 0),
    }
    combined_tokens = combined.get("reported_token_usage", {})
    lines.extend(
        [
            "| Component | Provider/model | Calls | API calls | Prompt tokens | Completion tokens | Total tokens | Errors/fallbacks | Estimated cost (USD) |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
            "| Agent | {}/{} | {} | {} | {} | {} | {} | {} | {} |".format(
                _format(agent.get("provider")),
                _format(agent.get("model")),
                _format(agent.get("respond_calls")),
                _format(agent.get("api_calls")),
                _format(agent_tokens.get("prompt_tokens", 0)),
                _format(agent_tokens.get("completion_tokens", 0)),
                _format(agent_tokens.get("total_tokens", 0)),
                _format(agent.get("error_count", 0)),
                _format(agent.get("estimated_cost_usd")),
            ),
            "| User verbalizer | {}/{} | {} | {} | {} | {} | {} | {} | {} |".format(
                _format(verbalizer.get("providers", [])),
                _format(verbalizer.get("models", [])),
                _format(verbalizer.get("calls")),
                _format(verbalizer.get("api_calls")),
                _format(verbalizer_tokens.get("prompt_tokens", 0)),
                _format(verbalizer_tokens.get("completion_tokens", 0)),
                _format(verbalizer_tokens.get("total_tokens", 0)),
                _format(verbalizer.get("fallbacks", 0)),
                _format(verbalizer.get("estimated_cost_usd")),
            ),
            "| Combined | — | — | {} | {} | {} | {} | — | {} |".format(
                _format(combined.get("api_calls")),
                _format(combined_tokens.get("prompt_tokens", 0)),
                _format(combined_tokens.get("completion_tokens", 0)),
                _format(combined_tokens.get("total_tokens", 0)),
                _format(combined.get("estimated_cost_usd")),
            ),
            "",
            "Agent cost status: `{}`; verbalizer cost status: `{}`.".format(
                agent.get("cost_status", "unknown"),
                verbalizer.get("cost_status", "unknown"),
            ),
        ]
    )

    lines.extend(["", "## Mode-specific metrics", ""])
    mode_specific = result.get("mode_specific_metrics", {})
    scenario_metrics = mode_specific.get("scenario_metrics")
    if isinstance(scenario_metrics, dict):
        lines.extend(
            _key_value_table(
                {
                    key: value
                    for key, value in mode_specific.items()
                    if key != "scenario_metrics"
                }
            )
        )
        lines.extend(
            [
                "",
                "| Scenario | N | Hit Rate@10 | MRR | MTTC |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for scenario, metrics in scenario_metrics.items():
            lines.append(
                "| {} | {} | {} | {} | {} |".format(
                    scenario,
                    _format(metrics.get("sample_count")),
                    _format(metrics.get("hit_rate_at_10")),
                    _format(metrics.get("mrr")),
                    _format(metrics.get("mttc")),
                )
            )
    else:
        persona_distribution = mode_specific.get("persona_distribution", {})
        lines.extend(
            _key_value_table(
                {
                    key: value
                    for key, value in mode_specific.items()
                    if key != "persona_distribution"
                }
            )
        )
        if persona_distribution:
            lines.extend(["", "| Persona | Sessions |", "|---|---:|"])
            for persona, count in persona_distribution.items():
                lines.append(f"| {persona} | {count} |")

    return "\n".join(lines).rstrip() + "\n"
