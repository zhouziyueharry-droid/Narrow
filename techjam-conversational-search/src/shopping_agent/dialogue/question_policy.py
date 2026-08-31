from __future__ import annotations

import math
from collections import Counter
from typing import Iterable


QUESTION_ATTRIBUTES = (
    "category", "material", "color", "feature", "style", "size",
    "brand", "budget", "use_case",
)


def _entropy(values: Iterable[str]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    if total <= 1 or len(counts) <= 1:
        return 0.0
    raw = -sum((count / total) * math.log2(count / total) for count in counts.values())
    return raw / math.log2(len(counts))


def choose_question(
    *,
    turn: int,
    candidate_attributes: list[dict[str, set[str]]],
    asked_attributes: list[str],
    no_preference: set[str],
    known_attributes: set[str] | None = None,
) -> tuple[str | None, dict[str, float]]:
    """Ask about the facet that best partitions this turn's candidates.

    ``turn`` remains in the public signature for compatibility, but decisions
    no longer depend on evaluator-specific discovery turns.
    """

    del turn
    scores = facet_scores(
        candidate_attributes=candidate_attributes,
        asked_attributes=asked_attributes,
        no_preference=no_preference,
        known_attributes=known_attributes,
    )
    if not scores:
        return None, {}
    attribute, score = max(scores.items(), key=lambda item: item[1])
    return (attribute if score >= 0.05 else None), scores


def facet_scores(
    *,
    candidate_attributes: list[dict[str, set[str]]],
    asked_attributes: list[str],
    no_preference: set[str],
    known_attributes: set[str] | None = None,
) -> dict[str, float]:
    """Compute candidate evidence without choosing a dialogue action."""
    known_attributes = known_attributes or set()
    if len(candidate_attributes) <= 1:
        return {}

    scores: dict[str, float] = {}
    candidate_count = max(len(candidate_attributes), 1)
    for attribute in QUESTION_ATTRIBUTES:
        if (
            attribute in no_preference
            or attribute in asked_attributes
            or attribute in known_attributes
        ):
            continue
        observed: list[str] = []
        covered = 0
        for attributes in candidate_attributes:
            values = attributes.get(attribute, set())
            if values:
                covered += 1
                observed.append("|".join(sorted(values)))
        coverage = covered / candidate_count
        scores[attribute] = coverage * _entropy(observed)

    return scores


def question_options(
    candidate_attributes: list[dict[str, set[str]]],
    attribute: str | None,
    *,
    limit: int = 3,
) -> list[dict[str, int | str]]:
    """Return representative values that explain why a facet was selected."""

    if not attribute:
        return []
    counts: Counter[str] = Counter()
    for attributes in candidate_attributes:
        for value in attributes.get(attribute, set()):
            cleaned = str(value).strip()
            if cleaned:
                counts[cleaned] += 1
    return [
        {"value": value, "count": count}
        for value, count in counts.most_common(limit)
    ]
