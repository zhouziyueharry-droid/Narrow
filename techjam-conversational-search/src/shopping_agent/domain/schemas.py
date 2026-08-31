from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Attribute = Literal[
    "category",
    "material",
    "color",
    "size",
    "style",
    "brand",
    "budget",
    "feature",
    "use_case",
    "other",
]

# The closed set of valid Attribute values, used by deterministic schema
# repair (see understanding/state_patch.py and dialogue/decision.py) to
# validate or normalize a field name coming back from the model without
# hand-rolling the Literal args in more than one place.
ATTRIBUTE_VALUES: frozenset[str] = frozenset(
    {"category", "material", "color", "size", "style", "brand", "budget", "feature", "use_case", "other"}
)


class Constraint(BaseModel):
    """A structured constraint extracted from the active conversation."""

    field: Attribute
    operator: Literal["contains", "not_contains", "eq", "lte", "gte"] = "contains"
    value: str | float
    strength: Literal["hard", "soft"] = "soft"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_turn: int | None = Field(default=None, ge=1, le=10)


class Recommendation(BaseModel):
    parent_asin: str = Field(min_length=1)
    score: float | None = None


class AgentTurn(BaseModel):
    """Structured result returned by the model-backed orchestration graph."""

    message: str
    ask_attribute: Attribute | None
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=10)
