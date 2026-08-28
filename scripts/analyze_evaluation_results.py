from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

TECHJAM_BASELINE = {
    "source": "user-simulator/docs/results/baseline-techjam-200.md",
    "sample_count": 200,
    "hit_rate_at_10": 0.82,
    "mrr": 0.329188,
    "mttc": 4.005,
    "efficiency": 0.6995,
    "recommended_technical_score": 0.648656,
}

REALISTIC_BASELINE = {
    "source": "user-simulator/docs/results/baseline-realistic-100.md",
    "sample_count": 100,
    "success_rate": 0.97,
    "mrr": 0.709524,
}

CANDIDATE_KEYS = (
    "lexical_candidates",
    "dense_candidates",
    "attribute_candidates",
    "fused_candidates",
    "filtered_candidates",
    "ranked_candidates",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_public_targets(path: Path) -> dict[str, str]:
    targets: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            targets[str(record["sample_id"])] = str(record["ground_truth"]["parent_asin"])
    return targets


def metric_comparison(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    comparison: dict[str, Any] = {"baseline_source": baseline["source"]}
    for key, baseline_value in baseline.items():
        if key == "source" or key not in current:
            continue
        current_value = current[key]
        comparison[key] = {
            "baseline": baseline_value,
            "current": current_value,
            "delta": round(float(current_value) - float(baseline_value), 6),
        }
    return comparison


def candidate_view(turn: dict[str, Any], key: str) -> dict[str, Any] | None:
    for step in turn.get("agent_layer_trace", []):
        value = step.get("updates", {}).get(key)
        if isinstance(value, dict):
            return value
    return None


def candidate_ids(turn: dict[str, Any], key: str) -> set[str]:
    view = candidate_view(turn, key) or {}
    return {
        str(item.get("parent_asin"))
        for item in view.get("top", [])
        if isinstance(item, dict) and item.get("parent_asin")
    }


def diagnose_techjam(session: dict[str, Any], target: str) -> dict[str, Any]:
    observed = {key: False for key in CANDIDATE_KEYS}
    recommended = False
    blocked = False
    for turn in session.get("conversation", []):
        for key in CANDIDATE_KEYS:
            observed[key] = observed[key] or target in candidate_ids(turn, key)
        recommended = recommended or target in turn.get("recommendations", [])
    evidence = session.get("acceptance", {}).get("evidence", {})
    blocked = evidence.get("blocked_by") == "intent_override_not_applied"

    if recommended and not session.get("success"):
        code = "recommended_but_not_accepted"
        explanation = "目标商品曾进入最终推荐，但用户策略没有接受；需检查意图覆盖时机或对话状态。"
    elif observed["ranked_candidates"] and not recommended:
        code = "response_or_top_k_loss_observed_top20"
        explanation = "目标出现在记录的排序候选中，但未进入最终推荐；需检查 Top-K 截断或响应构建。"
    elif observed["filtered_candidates"]:
        code = "ranking_underperformance_observed_top20"
        explanation = "目标通过了约束过滤，但没有进入记录的排序候选；主要问题位于重排层。"
    elif observed["fused_candidates"]:
        code = "constraint_filter_drop_observed_top20"
        explanation = "目标进入融合候选后被过滤掉；需检查解析出的硬约束和过滤逻辑。"
    elif any(observed[key] for key in CANDIDATE_KEYS[:3]):
        code = "fusion_loss_observed_top20"
        explanation = "至少一个检索通道找到目标，但融合结果未保留；需检查 RRF 权重和截断。"
    else:
        code = "retrieval_not_observed_top20"
        explanation = "目标未出现在任何轮次所记录的各检索通道 Top-20 中；优先检查查询构建和召回。"
    if blocked:
        explanation += " 最终证据还显示 intent override 尚未满足。"
    return {
        "code": code,
        "explanation": explanation,
        "target_product_id": target,
        "target_observed": observed,
        "target_recommended": recommended,
        "intent_override_blocked": blocked,
        "diagnosis_confidence": "low",
        "trace_scope_limit": "Candidate presence is evaluated only within the recorded top 20 per layer.",
    }


def diagnose_realistic(session: dict[str, Any]) -> dict[str, Any]:
    acceptance = session.get("acceptance", {})
    goal = session.get("goal_snapshot", {})
    if not any(turn.get("recommendations") for turn in session.get("conversation", [])):
        code = "no_recommendations"
        explanation = "整个会话没有产生有效推荐，需先检查检索、过滤和响应契约。"
    elif acceptance.get("hard_matches", 0) < acceptance.get("hard_total", 0):
        code = "hard_constraint_mismatch"
        explanation = "最终候选没有满足全部硬约束，需对照 goal snapshot 检查理解和过滤层。"
    elif acceptance.get("soft_matches", 0) < goal.get("min_soft_matches", 0):
        code = "insufficient_soft_matches"
        explanation = "硬约束可能满足，但软偏好匹配数量不足，需检查排序目标和偏好权重。"
    else:
        code = "dialogue_or_acceptance_stall"
        explanation = "候选存在但会话仍耗尽轮次，需检查追问策略、放宽策略和接受判定。"
    return {"code": code, "explanation": explanation}


def compact_turn(turn: dict[str, Any]) -> dict[str, Any]:
    layers: list[dict[str, Any]] = []
    for step in turn.get("agent_layer_trace", []):
        updates = step.get("updates", {})
        summary: dict[str, Any] = {}
        for key in CANDIDATE_KEYS:
            value = updates.get(key)
            if isinstance(value, dict):
                summary[key] = {
                    "count": value.get("count"),
                    "top_product_ids": [
                        item.get("parent_asin")
                        for item in value.get("top", [])
                        if isinstance(item, dict)
                    ],
                }
        for key in (
            "semantic_patch",
            "semantic_fallback_reasons",
            "active_constraints",
            "superseded_constraints",
            "ask_attribute",
            "question_scores",
            "recommendations",
            "errors",
        ):
            if key in updates:
                summary[key] = updates[key]
        layers.append({"nodes": step.get("nodes", []), "result": summary})
    return {
        "turn": turn.get("turn"),
        "user": turn.get("user"),
        "assistant": turn.get("assistant"),
        "ask_attribute": turn.get("ask_attribute"),
        "recommendations": turn.get("recommendations", []),
        "user_dialogue_act": turn.get("user_dialogue_act"),
        "next_dialogue_act": turn.get("next_dialogue_act_detail"),
        "agent_latency_ms": turn.get("agent_latency_ms"),
        "trace_error": turn.get("agent_trace_error"),
        "layers": layers,
    }


def example_record(
    mode: str,
    session: dict[str, Any],
    diagnosis: dict[str, Any],
) -> dict[str, Any]:
    return {
        "mode": mode,
        "scenario_id": session.get("scenario_id"),
        "scenario_type": session.get("scenario_type"),
        "success": session.get("success"),
        "turns": session.get("turns"),
        "goal_snapshot": session.get("goal_snapshot"),
        "acceptance": session.get("acceptance"),
        "diagnosis": diagnosis,
        "conversation": [compact_turn(turn) for turn in session.get("conversation", [])],
    }


def collect_quality(report: dict[str, Any]) -> dict[str, Any]:
    node_counts: Counter[str] = Counter()
    fallback_counts: Counter[str] = Counter()
    trace_errors: list[dict[str, Any]] = []
    agent_errors: list[dict[str, Any]] = []
    total_turns = 0
    for session in report.get("sessions", []):
        for error in session.get("agent_errors", []):
            agent_errors.append({"scenario_id": session.get("scenario_id"), "error": error})
        for turn in session.get("conversation", []):
            total_turns += 1
            if turn.get("agent_trace_error"):
                trace_errors.append({
                    "scenario_id": session.get("scenario_id"),
                    "turn": turn.get("turn"),
                    "error": turn.get("agent_trace_error"),
                })
            for step in turn.get("agent_layer_trace", []):
                node_counts.update(str(node) for node in step.get("nodes", []))
                reasons = step.get("updates", {}).get("semantic_fallback_reasons", [])
                if isinstance(reasons, list):
                    fallback_counts.update(str(reason) for reason in reasons)
    return {
        "sessions": len(report.get("sessions", [])),
        "turns": total_turns,
        "trace_error_count": len(trace_errors),
        "trace_errors": trace_errors,
        "agent_error_count": len(agent_errors),
        "agent_errors": agent_errors,
        "node_execution_counts": dict(sorted(node_counts.items())),
        "fallback_reason_counts": dict(sorted(fallback_counts.items())),
    }


def question_evidence(turn: dict[str, Any]) -> dict[str, Any]:
    for step in turn.get("agent_layer_trace", []):
        updates = step.get("updates", {})
        if "ask_attribute" in updates or "question_options" in updates:
            return {
                "ask_attribute": updates.get("ask_attribute"),
                "question_options": updates.get("question_options", []),
                "question_scores": updates.get("question_scores", {}),
            }
    return {
        "ask_attribute": turn.get("ask_attribute"),
        "question_options": [],
        "question_scores": {},
    }


def collect_session_findings(
    mode: str,
    report: dict[str, Any],
    targets: dict[str, str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for session in report.get("sessions", []):
        scenario_id = str(session.get("scenario_id"))
        session_context = {
            "mode": mode,
            "scenario_id": scenario_id,
            "scenario_type": session.get("scenario_type"),
            "persona": session.get("persona"),
            "success": session.get("success"),
        }

        def add(
            code: str,
            severity: str,
            explanation: str,
            *,
            turn: int | None = None,
            evidence: dict[str, Any] | None = None,
            context: dict[str, Any] = session_context,
        ) -> None:
            findings.append({
                **context,
                "turn": turn,
                "code": code,
                "severity": severity,
                "explanation": explanation,
                "evidence": evidence or {},
            })

        if not session.get("success"):
            diagnosis = (
                diagnose_techjam(session, targets[session["sample_id"]])
                if mode == "techjam"
                else diagnose_realistic(session)
            )
            add(
                diagnosis["code"],
                "high",
                diagnosis["explanation"],
                evidence=diagnosis,
            )

        if session.get("session_release_error"):
            add(
                "session_release_error",
                "high",
                "Agent session checkpoint cleanup failed after trace persistence.",
                evidence={"error": session["session_release_error"]},
            )

        turns = session.get("conversation", [])
        asked: list[str] = []
        recommendation_signatures: list[tuple[str, ...]] = []
        for index, turn_record in enumerate(turns):
            turn_number = int(turn_record.get("turn", index + 1))
            if turn_record.get("agent_trace_error"):
                add(
                    "agent_trace_error",
                    "high",
                    "A turn completed without an auditable Agent layer trace.",
                    turn=turn_number,
                    evidence={"error": turn_record["agent_trace_error"]},
                )
            question = question_evidence(turn_record)
            attribute = question.get("ask_attribute")
            if attribute:
                asked.append(str(attribute))
                if index == 0 and attribute == "brand":
                    add(
                        "brand_first_question",
                        "medium",
                        "The first clarification asks for brand before testing broader need attributes; this can overfit catalog brands.",
                        turn=turn_number,
                        evidence=question,
                    )

            if index > 0:
                act = turn_record.get("user_dialogue_act") or {}
                previous_question = question_evidence(turns[index - 1])
                if act.get("type") == "ANSWER_ATTRIBUTE":
                    values = {str(value).casefold() for value in act.get("values", [])}
                    options = {
                        str(item.get("value", "")).casefold()
                        for item in previous_question.get("question_options", [])
                        if isinstance(item, dict)
                    }
                    outside = sorted(values - options) if options else []
                    if outside:
                        add(
                            "answer_value_not_in_question_options",
                            "medium",
                            "The simulator answered with a hidden goal value that the Agent did not offer, making the interaction easier than a user constrained by visible options.",
                            turn=turn_number,
                            evidence={
                                "answer_values": sorted(values),
                                "previous_question": previous_question,
                                "outside_options": outside,
                            },
                        )

            signature = tuple(str(value) for value in turn_record.get("recommendations", []))
            recommendation_signatures.append(signature)

        repeated_attributes = sorted(
            attribute for attribute, count in Counter(asked).items() if count > 1
        )
        if repeated_attributes:
            add(
                "repeated_question_attribute",
                "medium",
                "The Agent asked the same attribute more than once in one session.",
                evidence={"attributes": repeated_attributes},
            )
        if (
            len(recommendation_signatures) >= 3
            and len(set(recommendation_signatures[-3:])) == 1
            and recommendation_signatures[-1]
        ):
            add(
                "repeated_recommendation_set",
                "low",
                "The same recommendation list was repeated for the final three turns.",
                evidence={"recommendations": list(recommendation_signatures[-1])},
            )
        if session.get("success") and turns and turns[-1].get("ask_attribute"):
            add(
                "accepted_while_agent_asks",
                "medium",
                "The simulator accepted a recommendation while the Agent response still asked a clarification question.",
                turn=int(turns[-1].get("turn", 0)),
                evidence={"ask_attribute": turns[-1].get("ask_attribute")},
            )
    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        findings,
        key=lambda item: (
            severity_order.get(item["severity"], 9),
            item["mode"],
            item["scenario_id"],
            item["turn"] or 0,
            item["code"],
        ),
    )


def choose_examples(
    techjam: dict[str, Any],
    realistic: dict[str, Any],
    targets: dict[str, str],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    session_lookup = {
        (mode, str(session.get("scenario_id"))): session
        for mode, report in (("techjam", techjam), ("realistic", realistic))
        for session in report["sessions"]
    }
    techjam_failures = [
        session for session in techjam["sessions"] if not session["success"]
    ]
    if techjam_failures:
        diagnosed = [
            (session, diagnose_techjam(session, targets[session["sample_id"]]))
            for session in techjam_failures
        ]
        priority = {
            "constraint_filter_drop_observed_top20": 0,
            "fusion_loss_observed_top20": 1,
            "ranking_underperformance_observed_top20": 2,
            "response_or_top_k_loss_observed_top20": 3,
            "recommended_but_not_accepted": 4,
            "retrieval_not_observed_top20": 5,
        }
        session, diagnosis = min(
            diagnosed,
            key=lambda item: (
                priority.get(item[1]["code"], 99),
                -int(item[0].get("turns", 0)),
                str(item[0].get("scenario_id")),
            ),
        )
        diagnosis["selection_reason"] = "deterministic highest-priority TechJam failure"
        examples.append(example_record("techjam", session, diagnosis))

    realistic_failures = [session for session in realistic["sessions"] if not session["success"]]
    if realistic_failures:
        session = max(realistic_failures, key=lambda item: item.get("turns", 0))
        diagnosis = diagnose_realistic(session)
        diagnosis["selection_reason"] = "longest realistic failure"
        examples.append(example_record("realistic", session, diagnosis))

    selected_ids = {(item["mode"], item["scenario_id"]) for item in examples}
    suspicious = next(
        (
            finding
            for finding in findings
            if finding["success"]
            and finding["severity"] in {"high", "medium"}
            and (finding["mode"], finding["scenario_id"]) not in selected_ids
        ),
        None,
    )
    if suspicious:
        session = session_lookup[(suspicious["mode"], suspicious["scenario_id"])]
        examples.append(example_record(
            suspicious["mode"],
            session,
            {
                "code": suspicious["code"],
                "explanation": suspicious["explanation"],
                "evidence": suspicious["evidence"],
                "diagnosis_confidence": "medium",
                "selection_reason": "successful outcome with suspicious UX or simulator behavior",
            },
        ))

    if not examples:
        all_sessions = [("techjam", item) for item in techjam["sessions"]] + [
            ("realistic", item) for item in realistic["sessions"]
        ]
        mode, session = max(
            all_sessions,
            key=lambda item: item[1].get("latency", {}).get("session_wall_ms", 0),
        )
        examples.append(example_record(
            mode,
            session,
            {
                "code": "slowest_successful_session",
                "explanation": "本次没有失败会话，因此选取最慢会话检查性能瓶颈。",
                "diagnosis_confidence": "medium",
                "selection_reason": "slowest session when no failure was available",
            },
        ))
    return examples


def render_markdown(analysis: dict[str, Any]) -> str:
    tech = analysis["techjam"]
    real = analysis["realistic"]
    lines = [
        "# 传统双模式评测分析",
        "",
        "## 总体结果",
        "",
        "| 模式 | 样本 | 成功率/HitRate@10 | MRR | 平均执行轮次 | API 调用 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| TechJam | {tech['evaluation']['sample_count']} | "
            f"{tech['evaluation']['hit_rate_at_10']:.6f} | "
            f"{tech['evaluation']['mrr']:.6f} | "
            f"{tech['turn_metrics']['mean_executed_turns']:.6f} | "
            f"{tech['model_usage']['combined']['api_calls']} |"
        ),
        (
            f"| Realistic | {real['evaluation']['sample_count']} | "
            f"{real['evaluation']['success_rate']:.6f} | "
            f"{real['evaluation']['mrr']:.6f} | "
            f"{real['turn_metrics']['mean_executed_turns']:.6f} | "
            f"{real['model_usage']['combined']['api_calls']} |"
        ),
        "",
        "## 与旧传统基线比较",
        "",
        "旧基线只保留 aggregate Markdown，没有 session JSON；因此本节只能比较总体指标，不能声称识别了逐样本 regression。",
        "",
    ]
    for mode in ("techjam", "realistic"):
        lines.extend([f"### {mode.title()}", "", "| 指标 | 旧值 | 当前值 | 差值 |", "| --- | ---: | ---: | ---: |"])
        for key, value in analysis["baseline_comparison"][mode].items():
            if key == "baseline_source":
                continue
            lines.append(
                f"| `{key}` | {value['baseline']} | {value['current']} | {value['delta']:+.6f} |"
            )
        lines.extend(["", f"基线来源：`{analysis['baseline_comparison'][mode]['baseline_source']}`", ""])

    lines.extend(["## 运行质量", ""])
    for mode in ("techjam", "realistic"):
        quality = analysis["quality"][mode]
        lines.append(
            f"- {mode}: {quality['turns']} turns，trace errors="
            f"{quality['trace_error_count']}，agent errors={quality['agent_error_count']}，"
            f"fallback reasons={quality['fallback_reason_counts']}"
        )

    lines.extend(["", "## 代表性问题案例", ""])
    for index, example in enumerate(analysis["representative_examples"], 1):
        diagnosis = example["diagnosis"]
        lines.extend([
            f"### 案例 {index}: {example['mode']} / {example['scenario_id']}",
            "",
            f"- 场景：`{example['scenario_type']}`",
            f"- 成功：`{example['success']}`；执行轮次：`{example['turns']}`",
            f"- 诊断分类：`{diagnosis['code']}`",
            f"- 诊断置信度：`{diagnosis.get('diagnosis_confidence', 'medium')}`",
            f"- 选择理由：{diagnosis.get('selection_reason', 'deterministic finding selection')}",
            f"- 分析：{diagnosis['explanation']}",
            f"- 评测目标：`{json.dumps(example.get('goal_snapshot'), ensure_ascii=False)}`",
            "",
        ])
        for turn in example["conversation"]:
            candidate_counts: list[str] = []
            for layer in turn["layers"]:
                for key in CANDIDATE_KEYS:
                    value = layer["result"].get(key)
                    if value:
                        candidate_counts.append(f"{key}={value['count']}")
            lines.extend([
                f"#### Turn {turn['turn']}",
                "",
                f"- User: {turn['user']}",
                f"- User act: `{json.dumps(turn.get('user_dialogue_act'), ensure_ascii=False)}`",
                f"- Agent: {turn['assistant']}",
                f"- Ask: `{turn['ask_attribute']}`",
                f"- Recommendations: `{turn['recommendations']}`",
                f"- Layer candidate counts: `{', '.join(candidate_counts)}`",
                f"- Agent latency: `{turn['agent_latency_ms']} ms`",
                "",
            ])
            for layer in turn["layers"]:
                lines.append(
                    f"  - Layer `{' + '.join(layer['nodes'])}`: "
                    f"`{json.dumps(layer['result'], ensure_ascii=False)}`"
                )
            lines.append("")
    finding_counts = Counter(item["code"] for item in analysis["session_findings"])
    lines.extend(["## 全体会话问题标记", ""])
    if finding_counts:
        lines.extend(["| 标记 | 次数 |", "| --- | ---: |"])
        lines.extend(
            f"| `{code}` | {count} |" for code, count in sorted(finding_counts.items())
        )
    else:
        lines.append("没有发现预定义的问题标记。")
    lines.extend([
        "",
        "所有标记均保存在 `comparisons/session_findings.jsonl`，代表性案例按固定优先级选择，不进行人工挑选。",
        "",
    ])
    lines.extend([
        "## 解释边界",
        "",
        "候选 trace 为每层 Top-20 的紧凑快照，因此“未观察到目标”不等同于目标绝对不在该层完整候选集合中。",
        "Realistic 是 need-based acceptance，不是官方 TechJam 分数。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--techjam", type=Path, required=True)
    parser.add_argument("--realistic", type=Path, required=True)
    parser.add_argument("--public-set", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument("--findings-output", type=Path, required=True)
    args = parser.parse_args()

    techjam = load_json(args.techjam)
    realistic = load_json(args.realistic)
    targets = load_public_targets(args.public_set)
    repo_root = Path(__file__).resolve().parents[1]
    techjam_baseline_path = repo_root / TECHJAM_BASELINE["source"]
    realistic_baseline_path = repo_root / REALISTIC_BASELINE["source"]
    findings = [
        *collect_session_findings("techjam", techjam, targets),
        *collect_session_findings("realistic", realistic, targets),
    ]
    analysis = {
        "schema_version": "1.0",
        "comparison_scope": "aggregate_only_no_legacy_session_json",
        "baseline_sources": {
            "techjam": {
                "path": TECHJAM_BASELINE["source"],
                "sha256": file_sha256(techjam_baseline_path),
            },
            "realistic": {
                "path": REALISTIC_BASELINE["source"],
                "sha256": file_sha256(realistic_baseline_path),
            },
        },
        "techjam": {
            "evaluation": techjam["evaluation"],
            "turn_metrics": techjam["turn_metrics"],
            "latency": techjam["latency"],
            "model_usage": techjam["model_usage"],
            "mode_specific_metrics": techjam["mode_specific_metrics"],
        },
        "realistic": {
            "evaluation": realistic["evaluation"],
            "turn_metrics": realistic["turn_metrics"],
            "latency": realistic["latency"],
            "model_usage": realistic["model_usage"],
            "mode_specific_metrics": realistic["mode_specific_metrics"],
        },
        "baseline_comparison": {
            "techjam": metric_comparison(techjam["evaluation"], TECHJAM_BASELINE),
            "realistic": metric_comparison(realistic["evaluation"], REALISTIC_BASELINE),
        },
        "quality": {
            "techjam": collect_quality(techjam),
            "realistic": collect_quality(realistic),
        },
        "session_findings": findings,
        "representative_examples": choose_examples(
            techjam, realistic, targets, findings
        ),
    }
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(analysis), encoding="utf-8")
    args.findings_output.parent.mkdir(parents=True, exist_ok=True)
    args.findings_output.write_text(
        "".join(
            json.dumps(item, ensure_ascii=False) + "\n" for item in findings
        ),
        encoding="utf-8",
    )
    print(json.dumps({
        "valid": True,
        "techjam_samples": techjam["evaluation"]["sample_count"],
        "realistic_samples": realistic["evaluation"]["sample_count"],
        "representative_examples": len(analysis["representative_examples"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
