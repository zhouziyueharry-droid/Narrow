from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from shopping_agent.domain.intent import COLORS, MATERIALS
from shopping_agent.domain.product_text import _number, _terms, _text
from shopping_agent.domain.schemas import Constraint
from shopping_agent.retrieval.attributes import STYLES, USE_CASES

# Reuses the same controlled vocabularies AttributeIndex already builds from,
# so "does the catalog explicitly assert a conflicting value" can be checked
# here without adding a dependency on AttributeIndex itself.
FLAT_VOCAB = {"material": MATERIALS, "color": COLORS}
GROUPED_VOCAB = {"style": STYLES, "use_case": USE_CASES}


def _normalized_phrase(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _product_corpus(product: dict[str, Any]) -> str:
    return " ".join(
        _text(product.get(f)) for f in ("title", "categories", "features", "details", "store")
    ).casefold()


def _field_corpus(product: dict[str, Any], field_name: str) -> str:
    """Return the narrowest trustworthy catalog text for a constraint field."""
    if field_name == "brand":
        values = (product.get("store"), product.get("brand"), product.get("title"))
    elif field_name == "category":
        values = (product.get("categories"),)
    elif field_name in {"material", "color", "size", "style", "feature", "use_case"}:
        values = (product.get("title"), product.get("features"), product.get("details"))
    else:
        values = (product.get("title"), product.get("features"), product.get("details"))
    return _normalized_phrase(" ".join(_text(value) for value in values))


def _explicit_values(field_name: str, candidate_terms: set[str]) -> set[str]:
    """Explicit attribute value(s) the catalog text asserts for this candidate."""
    if field_name in FLAT_VOCAB:
        return {v for v in FLAT_VOCAB[field_name] if v in candidate_terms}
    if field_name in GROUPED_VOCAB:
        return {name for name, words in GROUPED_VOCAB[field_name].items() if candidate_terms & words}
    return set()


@dataclass
class CandidateFeatures:
    exact_matches: float = 0.0
    partial_matches: float = 0.0
    contradictions: float = 0.0       # explicit catalog value conflicts with a soft constraint
    budget_penalty: float = 0.0       # 0 = within budget, up to 1+ the further over
    category_match: float = 0.0
    term_coverage: float = 0.0        # idf-weighted when a global idf table is supplied
    profile_match: float = 0.0        # idf-weighted when a global idf table is supplied
    quality: float = 0.0              # bayesian-shrunk average_rating, normalized 0..1
    novelty_penalty: float = 0.0
    lexical_signal: float = 0.0       # 1 / lexical_rank -- same scale as the old fallback ranker
    rrf_raw: float = 0.0              # raw fusion score, NOT batch-normalized
    dense_raw: float = 0.0            # raw dense-retrieval score, NOT batch-normalized
    attribute_raw: float = 0.0        # raw attribute-index score, NOT batch-normalized
    title_phrase_match: float = 0.0
    title_term_coverage: float = 0.0
    category_hierarchy_match: float = 0.0
    constraint_satisfaction: float = 0.0  # confidence-weighted satisfied constraints
    hard_constraint_satisfied: float = 0.0
    hard_constraint_violations: float = 0.0
    constraint_unknown: float = 0.0
    budget_satisfied: float = 0.0
    budget_unknown: float = 0.0
    material_match: float = 0.0
    color_match: float = 0.0
    size_match: float = 0.0
    brand_match: float = 0.0
    explanations: list[str] = field(default_factory=list)


def build_global_idf(products: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Document frequency computed over the WHOLE catalog, not a query-biased subset.

    Computing idf only over the candidates a retrieval stage already returned is a
    bug: those candidates were retrieved *because* they contain the query terms, so
    the query's most important terms look artificially common in that subset and get
    under-weighted. This must be built once from the full catalog and reused across
    every ranking call (see PreciseReranker.__init__).
    """
    n_docs = max(len(products), 1)
    df: Counter[str] = Counter()
    for product in products.values():
        df.update(set(_terms(_product_corpus(product))))
    return {term: math.log((n_docs + 1) / (count + 1)) + 1.0 for term, count in df.items()}


def _coverage(query_terms: set[str], candidate_terms: set[str], idf: dict[str, float] | None) -> float:
    if not query_terms:
        return 0.0
    if idf is None:
        # No global idf available (e.g. unit tests without catalog access): fall
        # back to a plain overlap ratio rather than a query-biased local idf.
        return len(query_terms & candidate_terms) / len(query_terms)
    total = sum(idf.get(t, 1.0) for t in query_terms)
    if total <= 0:
        return 0.0
    hit = sum(idf.get(t, 1.0) for t in query_terms & candidate_terms)
    return hit / total


def _bayesian_quality(
    average_rating: Any,
    rating_number: Any,
    *,
    prior: float = 4.0,
    prior_weight: float = 20.0,
) -> float:
    rating = _number(average_rating) if average_rating is not None else None
    count = _number(rating_number) if rating_number is not None else None
    n = max(count or 0.0, 0.0)
    if rating is None:
        rating = prior
    shrunk = (prior_weight * prior + n * rating) / (prior_weight + n)
    return shrunk / 5.0


def extract_batch_features(
    candidates: list[dict[str, Any]],
    *,
    query: str,
    category: str,
    constraints: list[Constraint],
    profile: dict[str, Any] | None,
    previously_recommended: set[str] | None,
    idf: dict[str, float] | None = None,
) -> list[CandidateFeatures]:
    profile = profile or {}
    previously_recommended = previously_recommended or set()
    query_terms = set(_terms(query))
    category_phrase = _normalized_phrase(category)
    profile_terms = set(_terms(" ".join(str(t) for t in profile.get("preference_tags", []))))

    results: list[CandidateFeatures] = []
    for candidate in candidates:
        corpus = _product_corpus(candidate)
        normalized_corpus = _normalized_phrase(corpus)
        candidate_terms = set(_terms(corpus))
        title = _normalized_phrase(_text(candidate.get("title")))
        title_terms = set(_terms(title))
        category_corpus = _normalized_phrase(_text(candidate.get("categories")))
        query_phrase = _normalized_phrase(query)

        feat = CandidateFeatures(
            category_match=1.0 if category_phrase and category_phrase in normalized_corpus else 0.0,
            term_coverage=_coverage(query_terms, candidate_terms, idf),
            profile_match=_coverage(profile_terms, candidate_terms, idf) if profile_terms else 0.0,
            quality=_bayesian_quality(candidate.get("average_rating"), candidate.get("rating_number")),
            novelty_penalty=1.0 if str(candidate["parent_asin"]) in previously_recommended else 0.0,
            lexical_signal=1.0 / max(int(candidate.get("lexical_rank") or 300), 1),
            rrf_raw=float(candidate.get("rrf_score") or 0.0),
            dense_raw=float(candidate.get("dense_score") or 0.0),
            attribute_raw=float(candidate.get("attribute_score") or 0.0),
            title_phrase_match=1.0 if query_phrase and query_phrase in title else 0.0,
            title_term_coverage=_coverage(query_terms, title_terms, idf),
            category_hierarchy_match=(
                1.0 if category_phrase and category_phrase in category_corpus else 0.0
            ),
        )

        for constraint in constraints:
            confidence = float(constraint.confidence)
            status = "unknown"
            if constraint.field == "budget":
                price = _number(candidate.get("price")) if candidate.get("price") is not None else None
                target = _number(constraint.value)
                if price is None or target is None or target <= 0:
                    feat.budget_unknown += confidence
                elif constraint.operator == "lte":
                    status = "satisfied" if price <= target else "violated"
                    if status == "violated":
                        feat.budget_penalty += max(0.0, min(1.0, (price - target) / target))
                        feat.explanations.append("over_budget")
                elif constraint.operator == "gte":
                    status = "satisfied" if price >= target else "violated"
                    if status == "violated":
                        feat.budget_penalty += max(0.0, min(1.0, (target - price) / target))
                        feat.explanations.append("under_budget")
                elif constraint.operator == "eq":
                    status = "satisfied" if math.isclose(price, target, rel_tol=0.0, abs_tol=0.01) else "violated"
                    if status == "violated":
                        feat.budget_penalty += min(1.0, abs(price - target) / target)
                if status == "satisfied":
                    feat.budget_satisfied += confidence
            else:
                phrase = _normalized_phrase(str(constraint.value))
                field_corpus = _field_corpus(candidate, constraint.field)
                mentioned = bool(phrase and phrase in field_corpus)
                explicit_values = _explicit_values(constraint.field, candidate_terms)
                if explicit_values:
                    mentioned = phrase in explicit_values or any(
                        phrase in value or value in phrase for value in explicit_values
                    )
                    status = "satisfied" if mentioned else "violated"
                elif mentioned:
                    status = "satisfied"
                if constraint.operator == "not_contains" and status != "unknown":
                    status = "violated" if status == "satisfied" else "satisfied"

            if status == "satisfied":
                feat.exact_matches += 1.0
                feat.constraint_satisfaction += confidence
                if constraint.strength == "hard":
                    feat.hard_constraint_satisfied += confidence
                field_match = f"{constraint.field}_match"
                if hasattr(feat, field_match):
                    setattr(feat, field_match, getattr(feat, field_match) + confidence)
                feat.explanations.append(f"satisfied:{constraint.field}")
            elif status == "violated":
                feat.contradictions += confidence
                if constraint.strength == "hard":
                    feat.hard_constraint_violations += confidence
                feat.explanations.append(f"conflict:{constraint.field}")
            else:
                feat.constraint_unknown += confidence
                words = set(_terms(str(constraint.value)))
                feat.partial_matches += len(words & candidate_terms) / max(len(words), 1)
                feat.explanations.append(f"unknown:{constraint.field}")

        results.append(feat)
    return results
