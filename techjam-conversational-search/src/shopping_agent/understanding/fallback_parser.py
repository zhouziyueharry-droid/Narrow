from __future__ import annotations

import re

from shopping_agent.domain.intent import COLORS, MATERIALS, classify_attribute, parse_message
from shopping_agent.domain.schemas import Attribute, Constraint
from shopping_agent.understanding.state_patch import StatePatch, validate_state_patch


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
    "boot": "boots", "boots": "boots", "shoe": "shoes", "shoes": "shoes",
    "sneaker": "sneakers", "sneakers": "sneakers", "jacket": "jackets",
    "coat": "coats", "dress": "dresses", "shirt": "shirts", "pants": "pants",
    "jeans": "jeans", "bag": "bags", "purse": "handbags", "belt": "belts",
    "watch": "watches",
}

STYLE_TERMS = {
    "formal": "formal", "dressy": "formal", "casual": "casual",
    "vintage": "vintage", "sporty": "sport", "athletic": "sport",
}

USE_CASE_TERMS = {
    "running": "running", "hiking": "hiking", "work": "work", "office": "work",
    "gym": "gym", "winter": "winter", "outdoor": "outdoor",
}

FEATURE_TERMS = {
    "waterproof": "waterproof", "water resistant": "water resistant",
    "breathable": "breathable", "lightweight": "lightweight",
    "lighter": "lightweight", "warm": "warm", "durable": "durable",
}

MAX_NEGATION_WORDS = 6


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
    """Extract bounded exclusions and split compound alternatives."""
    cleaned = re.sub(r"\bdon't mind\b[^,.;]*", "", message, flags=re.IGNORECASE)
    pattern = re.compile(
        r"(?:don't want|do not want|avoid|without|not(?: that)?|no)\s+"
        r"(?:any(?:thing)?\s+)?([a-z][a-z ,/-]{1,60}?)(?=\s+(?:and|but)\b|[,.;!?]|$)",
        re.IGNORECASE,
    )
    phrases: list[str] = []
    for match in pattern.finditer(cleaned):
        raw = match.group(1).strip()
        for part in re.split(r"\s*(?:,|/|\bor\b)\s*", raw):
            normalized = re.sub(
                r"^(?:that|this|a|an|the)\s+", "", part.strip()
            ).strip()
            if normalized and len(normalized.split()) <= MAX_NEGATION_WORDS:
                phrases.append(normalized)
    return phrases


def semantic_fallback_patch(
    message: str,
    turn: int,
    rule_patch: StatePatch,
    *,
    current_category: str = "",
) -> StatePatch:
    lowered = message.casefold()
    constraints = list(rule_patch.constraints)
    negative_values = _negative_phrases(message)
    negative_text = " ".join(negative_values).casefold()

    for value in negative_values:
        normalized = "tall" if value in {"that tall", "tall"} else value
        constraints.append(_constraint(
            classify_attribute(normalized), normalized, turn,
            operator="not_contains", strength="hard", confidence=0.88,
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
        constraints.append(_constraint(
            "budget", low, turn, operator="gte", strength="soft", confidence=0.85,
        ))
        constraints.append(_constraint(
            "budget", high, turn, operator="lte", strength="hard", confidence=0.9,
        ))
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
            "budget", float(match.group(1)), turn, operator="lte",
            strength="soft" if soft else "hard", confidence=0.9,
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
