from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from shopping_agent.intent import COLORS, MATERIALS, classify_attribute, parse_message
from shopping_agent.schemas import Attribute, Constraint

# Negated phrases longer than this many words are too unstructured for the
# regex extractor to trust as a single attribute value; they are dropped so
# the LLM parser (or a low-confidence rule patch) can handle them instead of
# filing a garbage not_contains constraint. See _negative_phrases().
MAX_NEGATION_WORDS = 6


class StatePatch(BaseModel):
    """A bounded user-intent update; it cannot retrieve or recommend products.

    ``semantic_query`` is the model's compact, catalog-facing description of
    the *current complete intent*. Structured constraints remain the source of
    truth for filtering; the sentence is reserved for semantic retrieval.
    """

    action: Literal["add", "replace", "remove", "no_preference"] = "add"
    category: str | None = None
    constraints: list[Constraint] = Field(default_factory=list, max_length=20)
    remove_fields: list[Attribute] = Field(default_factory=list)
    no_preference: list[Attribute] = Field(default_factory=list)
    retire_soft: bool = False
    semantic_query: str = Field(default="", max_length=500)
    intent_summary: str = Field(default="", max_length=1000)
    language: Literal["zh", "en", "other"] = "en"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    parser: Literal["rules", "fallback", "deepseek"] = "rules"
    fallback_reasons: list[str] = Field(default_factory=list)


PROTOCOL_MARKERS = (
    "i'm looking for",
    "a key requirement is:",
    "what matters is:",
    "what i need is:",
    "i don't have a preference for",
    "i don't have an additional preference for",
)

REFERENCE_MARKERS = (
    " it ", " that ", " those ", " them ", " one ", " ones ",
    "lighter", "shorter", "taller", "smaller", "larger",
)

CATEGORY_TERMS = {
    "boot": "boots",
    "boots": "boots",
    "shoe": "shoes",
    "shoes": "shoes",
    "sneaker": "sneakers",
    "sneakers": "sneakers",
    "jacket": "jackets",
    "coat": "coats",
    "dress": "dresses",
    "shirt": "shirts",
    "pants": "pants",
    "jeans": "jeans",
    "bag": "bags",
    "purse": "handbags",
    "belt": "belts",
    "watch": "watches",
}

STYLE_TERMS = {
    "formal": "formal",
    "dressy": "formal",
    "casual": "casual",
    "vintage": "vintage",
    "sporty": "sport",
    "athletic": "sport",
}

USE_CASE_TERMS = {
    "running": "running",
    "hiking": "hiking",
    "work": "work",
    "office": "work",
    "gym": "gym",
    "winter": "winter",
    "outdoor": "outdoor",
}

FEATURE_TERMS = {
    "waterproof": "waterproof",
    "water resistant": "water resistant",
    "breathable": "breathable",
    "lightweight": "lightweight",
    "lighter": "lightweight",
    "warm": "warm",
    "durable": "durable",
}


def _constraint(
    field: Attribute,
    value: str | float,
    turn: int,
    *,
    operator: str = "contains",
    strength: str = "soft",
    confidence: float = 0.8,
) -> Constraint:
    return Constraint(
        field=field,
        operator=operator,  # type: ignore[arg-type]
        value=value,
        strength=strength,  # type: ignore[arg-type]
        confidence=confidence,
        source_turn=turn,
    )


def rule_state_patch(message: str, turn: int) -> StatePatch:
    parsed = parse_message(message, turn)
    lowered = f" {message.casefold()} "
    reasons: list[str] = []
    protocol_language = any(marker in lowered for marker in PROTOCOL_MARKERS)
    structured_protocol = any(
        marker in lowered
        for marker in (
            "a key requirement is:", "what matters is:", "what i need is:",
            "i don't have a preference for", "i don't have an additional preference for",
        )
    )

    has_negative_language = bool(
        re.search(r"\b(?:not|no|avoid|without|don't want|do not want)\b", lowered)
    ) and "don't have a preference" not in lowered
    has_negative_constraint = any(item.operator == "not_contains" for item in parsed.constraints)
    if not structured_protocol and has_negative_language and not has_negative_constraint:
        reasons.append("unresolved_negation")

    if not structured_protocol and any(marker in lowered for marker in REFERENCE_MARKERS):
        reasons.append("reference_or_comparison")

    amounts = re.findall(r"\$\s*(\d+(?:\.\d+)?)", message)
    if not structured_protocol and (
        len(amounts) > 1
        or (amounts and any(marker in lowered for marker in ("if possible", "stretch", "unless")))
    ):
        reasons.append("conditional_budget")

    extracted = bool(parsed.category or parsed.constraints or parsed.no_preference or parsed.override)
    if protocol_language:
        confidence = 0.97
    elif extracted:
        confidence = 0.78
    else:
        confidence = 0.25
        reasons.append("no_structured_signal")
    if reasons:
        confidence = min(confidence, 0.55)

    return StatePatch(
        action="replace" if parsed.override else ("no_preference" if parsed.no_preference else "add"),
        category=parsed.category,
        constraints=parsed.constraints,
        no_preference=sorted(parsed.no_preference),
        retire_soft=parsed.override,
        confidence=confidence,
        parser="rules",
        fallback_reasons=list(dict.fromkeys(reasons)),
    )


def _negative_phrases(message: str) -> list[str]:
    """Extract negated attribute values, splitting compound negations.

    Two bugs in the previous implementation are fixed here:

    1. "I don't want cotton or wool" used to stop capturing at the first
       " or"/" and" boundary and silently dropped "wool". The boundary now
       only stops at "and"/"but"/punctuation, so an "or"-joined list is
       captured whole and then split into separate values below.
    2. An unstructured, multi-clause span ("a huge floral pattern that
       clashes with everything in my closet") used to be filed verbatim as
       one not_contains value. It is now capped at MAX_NEGATION_WORDS and
       dropped, so the caller's ``unresolved_negation`` fallback reason (see
       rule_state_patch) routes it to the LLM parser instead of polluting
       the structured constraints with garbage.
    """

    cleaned = re.sub(r"\bdon't mind\b[^,.;]*", "", message, flags=re.IGNORECASE)
    pattern = re.compile(
        r"(?:don't want|do not want|avoid|without|not(?: that)?|no)\s+"
        r"(?:any(?:thing)?\s+)?([a-z][a-z ,/-]{1,60}?)(?=\s+(?:and|but)\b|[,.;!?]|$)",
        re.IGNORECASE,
    )
    phrases: list[str] = []
    for match in pattern.finditer(cleaned):
        raw = match.group(1).strip()
        if not raw:
            continue
        for part in re.split(r"\s*(?:,|/|\bor\b)\s*", raw):
            part = re.sub(r"^(?:that|this|a|an|the)\s+", "", part.strip()).strip()
            if not part:
                continue
            if len(part.split()) > MAX_NEGATION_WORDS:
                continue
            phrases.append(part)
    return phrases


def semantic_fallback_patch(
    message: str,
    turn: int,
    rule_patch: StatePatch,
    *,
    current_category: str = "",
) -> StatePatch:
    """Deterministically enrich an uncertain rule patch.

    This is the local substitute for a future structured semantic model call.
    """

    lowered = message.casefold()
    constraints = list(rule_patch.constraints)
    negative_values = _negative_phrases(message)
    negative_text = " ".join(negative_values).casefold()

    for value in negative_values:
        constraints.append(_constraint(
            classify_attribute(value),
            value,
            turn,
            operator="not_contains",
            strength="hard",
            confidence=0.88,
        ))

    category = rule_patch.category
    for term, normalized in CATEGORY_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            if not any(term in value.casefold() for value in negative_values):
                category = normalized
                break
    category = category or current_category or None

    for material in MATERIALS:
        if re.search(rf"\b{re.escape(material)}\b", lowered) and material not in negative_text:
            constraints.append(_constraint("material", material, turn, confidence=0.9))
    for color in COLORS:
        if re.search(rf"\b{re.escape(color)}\b", lowered) and color not in negative_text:
            constraints.append(_constraint("color", color, turn, confidence=0.88))
    for term, normalized in STYLE_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", lowered) and term not in negative_text:
            constraints.append(_constraint("style", normalized, turn, confidence=0.86))
    for term, normalized in USE_CASE_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", lowered) and term not in negative_text:
            constraints.append(_constraint("use_case", normalized, turn, confidence=0.86))
    for term, normalized in FEATURE_TERMS.items():
        if term in lowered and term not in negative_text:
            constraints.append(_constraint("feature", normalized, turn, confidence=0.84))

    # Range budgets ("between $50 and $100", "$50-$100") are parsed first and
    # their span is excluded from the single-value pass below so a phrase
    # like "under $80 ... stretch to $100" (two independent single-value
    # mentions) is never double-counted as a range.
    range_matches = list(re.finditer(
        r"between\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:and|to)\s*\$?\s*(\d+(?:\.\d+)?)"
        r"|\$\s*(\d+(?:\.\d+)?)\s*-\s*\$?\s*(\d+(?:\.\d+)?)",
        lowered,
    ))
    range_spans: list[tuple[int, int]] = []
    for match in range_matches:
        if match.group(1) is not None:
            low_raw, high_raw = match.group(1), match.group(2)
        else:
            low_raw, high_raw = match.group(3), match.group(4)
        low, high = float(low_raw), float(high_raw)
        if low > high:
            low, high = high, low
        constraints.append(_constraint("budget", low, turn, operator="gte", strength="soft", confidence=0.85))
        constraints.append(_constraint("budget", high, turn, operator="lte", strength="hard", confidence=0.9))
        range_spans.append(match.span())

    budget_matches = [
        match
        for match in re.finditer(
            r"(?:under|below|up to|no more than|stretch to)\s*\$?\s*(\d+(?:\.\d+)?)",
            lowered,
        )
        if not any(start <= match.start() < end for start, end in range_spans)
    ]
    for match in budget_matches:
        prefix = match.group(0)
        soft = "if possible" in lowered and "stretch to" not in prefix
        constraints.append(_constraint(
            "budget",
            float(match.group(1)),
            turn,
            operator="lte",
            strength="soft" if soft else "hard",
            confidence=0.9,
        ))

    action = rule_patch.action
    retire_soft = rule_patch.retire_soft
    if any(marker in lowered for marker in ("actually", "instead", "forget ", "ignore ")):
        action = "replace"
        retire_soft = True

    return validate_state_patch(StatePatch(
        action=action,
        category=category,
        constraints=constraints,
        remove_fields=rule_patch.remove_fields,
        no_preference=rule_patch.no_preference,
        retire_soft=retire_soft,
        confidence=max(rule_patch.confidence, 0.78 if constraints or category else 0.4),
        parser="fallback",
        fallback_reasons=rule_patch.fallback_reasons,
    ))


DEEPSEEK_SYSTEM_PROMPT = """You are the intent-understanding component of a real-user shopping agent.
Read the latest message together with the maintained intent state and return one
JSON object only. Never recommend products or invent product identifiers.

Your output has two equally important representations:
1. structured constraints for exact filtering and state maintenance;
2. semantic_query: one short, fluent English product-search sentence for a
   multilingual embedding/vector database. It must describe the complete
   current intent after applying this turn, not merely repeat the latest turn.

Do not put conversational filler, question wording, ASINs, or implementation
terms in semantic_query. Prefer product type, use case, desired properties and
style. Keep exclusions and numeric limits in structured constraints; mention
them in the sentence only when they are central to product meaning.

Schema:
{
  "action": "add|replace|remove|no_preference",
  "category": "string or null",
  "constraints": [{
    "field": "category|material|color|size|style|brand|budget|feature|use_case|other",
    "operator": "contains|not_contains|eq|lte|gte",
    "value": "string or number",
    "strength": "hard|soft",
    "confidence": 0.0,
    "source_turn": 1
  }],
  "remove_fields": [],
  "no_preference": [],
  "retire_soft": false,
  "semantic_query": "concise English semantic retrieval sentence",
  "intent_summary": "concise complete intent in the user's language",
  "language": "zh|en|other",
  "confidence": 0.0,
  "fallback_reasons": []
}

Extract every explicit constraint, including use case and occasion. Use
action=replace plus remove_fields when the user retracts or replaces an earlier
requirement. Negation must use not_contains. Long-term profile preferences are
never hard constraints. Do not infer a preference merely because candidate
products have that attribute.
"""


def _detect_language(message: str) -> Literal["zh", "en", "other"]:
    if re.search(r"[\u3400-\u9fff]", message):
        return "zh"
    if re.search(r"[a-z]", message, re.IGNORECASE):
        return "en"
    return "other"


def _fallback_semantic_query(
    message: str,
    category: str | None,
    constraints: list[Constraint],
) -> str:
    """Build a compact retrieval query when the semantic model is unavailable."""

    positive = [
        str(item.value)
        for item in constraints
        if item.operator != "not_contains" and item.field != "budget"
    ]
    parts = [category or "", *positive]
    if not any(parts):
        cleaned = re.sub(r"\s+", " ", message).strip()
        return cleaned[:500]
    return " ".join(dict.fromkeys(part.strip() for part in parts if part.strip()))[:500]


def _deepseek_enabled() -> bool:
    return os.getenv("SHOPPING_AGENT_ENABLE_LLM", "false").strip().casefold() in {
        "1", "true", "yes", "on",
    }


class _InvalidDeepSeekResponse(Exception):
    """Raised when the provider's reply is not a schema-valid StatePatch.

    Kept distinct from network/timeout failures so ``fallback_reasons`` can
    tell you *why* a turn fell back to the deterministic parser: a bad
    prompt/schema mismatch ("deepseek_invalid_response") needs a different
    fix than an outage or missing credentials ("deepseek_unavailable").
    """


# Fields where a new value plausibly *replaces* an existing one rather than
# adding beside it. Budget, category, and free-form "feature"/"other" values
# are deliberately excluded: budget updates are usually additive/soft
# (a preferred vs. a maximum), category is already always overwritten by
# update_state in graph.py, and "feature"/"other" are too heterogeneous to
# assume a swap safely.
OVERRIDE_SENSITIVE_FIELDS = {"color", "material", "size", "style", "brand", "use_case"}


def _has_conflicting_value(
    active_constraints: list[dict[str, Any]],
    incoming: list[Constraint],
) -> bool:
    """True when ``incoming`` swaps an already-set attribute to a new value.

    This is the rule-layer's substitute for an explicit override marker
    ("actually", "instead"): if the user previously locked in ``color=red``
    and the new turn says ``color=blue`` with no marker at all, the intent
    has still changed and should replace the old value rather than sit
    beside it as a second, contradictory ``color`` constraint.
    """

    active_by_field: dict[str, set[str]] = {}
    for value in active_constraints:
        if value.get("operator") == "not_contains":
            continue
        active_by_field.setdefault(value.get("field", ""), set()).add(
            str(value.get("value", "")).casefold()
        )
    for item in incoming:
        if item.operator == "not_contains" or item.field not in OVERRIDE_SENSITIVE_FIELDS:
            continue
        existing = active_by_field.get(item.field)
        if existing and str(item.value).casefold() not in existing:
            return True
    return False


def _fallback_result(
    message: str,
    turn: int,
    rule_patch: StatePatch,
    current_category: str,
    reason: str | None,
    active_constraints: list[dict[str, Any]] | None,
) -> tuple[StatePatch, dict[str, int]]:
    """Build the deterministic fallback patch shared by every non-model path."""

    fallback = semantic_fallback_patch(
        message,
        turn,
        rule_patch,
        current_category=current_category,
    )
    if reason:
        fallback.fallback_reasons = list(dict.fromkeys([*fallback.fallback_reasons, reason]))
    if fallback.action != "replace" and _has_conflicting_value(active_constraints or [], fallback.constraints):
        fallback.action = "replace"
        fallback.fallback_reasons = list(dict.fromkeys([
            *fallback.fallback_reasons,
            "implicit_override_heuristic",
        ]))
    fallback.semantic_query = _fallback_semantic_query(
        message,
        fallback.category,
        fallback.constraints,
    )
    fallback.intent_summary = fallback.semantic_query
    fallback.language = _detect_language(message)
    return fallback, {"prompt_tokens": 0, "completion_tokens": 0}


def resolve_semantic_patch(
    message: str,
    turn: int,
    rule_patch: StatePatch,
    *,
    current_category: str = "",
    active_constraints: list[dict[str, Any]] | None = None,
    current_semantic_query: str = "",
    intent_summary: str = "",
    user_profile: dict[str, Any] | None = None,
) -> tuple[StatePatch, dict[str, int]]:
    """Interpret every turn with the configured LLM, with deterministic fallback."""

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not _deepseek_enabled() or not api_key:
        return _fallback_result(message, turn, rule_patch, current_category, None, active_constraints)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        payload = {
            "turn": turn,
            "current_category": current_category or None,
            "active_constraints": active_constraints or [],
            "current_semantic_query": current_semantic_query or None,
            "current_intent_summary": intent_summary or None,
            "user_profile": user_profile or {},
            "user_message": message,
            "rule_patch": rule_patch.model_dump(mode="json"),
        }

        def _call_once():
            return client.chat.completions.create(
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
                messages=[
                    {"role": "system", "content": DEEPSEEK_SYSTEM_PROMPT},
                    {"role": "user", "content": "Return the JSON state patch for:\n" + json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=800,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
            )

        response = None
        call_error: Exception | None = None
        # One retry absorbs a transient network blip or rate limit without
        # falling all the way back to the deterministic parser on every hiccup.
        for _attempt in range(2):
            try:
                response = _call_once()
                call_error = None
                break
            except Exception as exc:  # noqa: BLE001 - broad: any provider/network failure
                call_error = exc
        if response is None:
            raise call_error or RuntimeError("deepseek call failed")

        content = response.choices[0].message.content or ""
        try:
            model_patch = StatePatch.model_validate_json(content)
        except Exception as exc:
            raise _InvalidDeepSeekResponse(content) from exc

        local_patch = semantic_fallback_patch(
            message,
            turn,
            rule_patch,
            current_category=current_category,
        )
        # The provider adds semantic interpretation; deterministic extraction
        # remains a second source of evidence so a model omission cannot delete
        # obvious material, use-case, budget, or negation signals.
        patch = StatePatch(
            action=model_patch.action,
            category=model_patch.category or local_patch.category,
            constraints=[*local_patch.constraints, *model_patch.constraints],
            remove_fields=[*local_patch.remove_fields, *model_patch.remove_fields],
            no_preference=[*local_patch.no_preference, *model_patch.no_preference],
            retire_soft=local_patch.retire_soft or model_patch.retire_soft,
            semantic_query=model_patch.semantic_query or _fallback_semantic_query(
                message,
                model_patch.category or local_patch.category,
                [*local_patch.constraints, *model_patch.constraints],
            ),
            intent_summary=model_patch.intent_summary or model_patch.semantic_query,
            language=model_patch.language or _detect_language(message),
            confidence=max(local_patch.confidence, model_patch.confidence),
            parser="deepseek",
            fallback_reasons=model_patch.fallback_reasons,
        )
        usage = getattr(response, "usage", None)
        return validate_state_patch(patch), {
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        }
    except _InvalidDeepSeekResponse:
        return _fallback_result(
            message, turn, rule_patch, current_category, "deepseek_invalid_response", active_constraints,
        )
    except Exception:
        return _fallback_result(
            message, turn, rule_patch, current_category, "deepseek_unavailable", active_constraints,
        )


def validate_state_patch(patch: StatePatch) -> StatePatch:
    """Normalize, deduplicate, and resolve positive/negative collisions."""

    deduplicated: dict[tuple[str, str, str], Constraint] = {}
    for item in patch.constraints:
        if isinstance(item.value, str):
            item.value = re.sub(r"\s+", " ", item.value).strip(" .;,\t\n")
            if not item.value:
                continue
        elif item.field == "budget" and float(item.value) <= 0:
            continue
        key = (item.field, item.operator, str(item.value).casefold())
        deduplicated[key] = item

    negatives = {
        (item.field, str(item.value).casefold())
        for item in deduplicated.values()
        if item.operator == "not_contains"
    }
    constraints = [
        item
        for item in deduplicated.values()
        if item.operator == "not_contains"
        or (item.field, str(item.value).casefold()) not in negatives
    ]
    return patch.model_copy(update={
        "constraints": constraints[:20],
        "remove_fields": list(dict.fromkeys(patch.remove_fields)),
        "no_preference": list(dict.fromkeys(patch.no_preference)),
        "semantic_query": re.sub(r"\s+", " ", patch.semantic_query).strip()[:500],
        "intent_summary": re.sub(r"\s+", " ", patch.intent_summary).strip()[:1000],
    })


def apply_state_patch(
    active_values: list[dict[str, Any]],
    patch: StatePatch,
) -> tuple[list[Constraint], list[Constraint]]:
    active = [Constraint.model_validate(value) for value in active_values]
    superseded: list[Constraint] = []

    if patch.retire_soft:
        superseded.extend(item for item in active if item.strength == "soft")
        active = [item for item in active if item.strength == "hard"]

    if patch.action == "replace":
        replacement_fields = {item.field for item in patch.constraints}
        if replacement_fields:
            superseded.extend(item for item in active if item.field in replacement_fields)
            active = [item for item in active if item.field not in replacement_fields]

    removed_fields = set(patch.remove_fields) | set(patch.no_preference)
    if removed_fields:
        superseded.extend(item for item in active if item.field in removed_fields)
        active = [item for item in active if item.field not in removed_fields]

    for incoming in patch.constraints:
        value = str(incoming.value).casefold()
        conflicts = [
            item for item in active
            if item.field == incoming.field
            and str(item.value).casefold() == value
            and item.operator != incoming.operator
        ]
        if conflicts:
            superseded.extend(conflicts)
            active = [item for item in active if item not in conflicts]
        key = (incoming.field, incoming.operator, value)
        if not any((item.field, item.operator, str(item.value).casefold()) == key for item in active):
            active.append(incoming)
    return active, superseded
