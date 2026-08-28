from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class DialogueActType(str, Enum):
    INITIAL_REQUEST = "INITIAL_REQUEST"
    INFORM = "INFORM"
    ANSWER_ATTRIBUTE = "ANSWER_ATTRIBUTE"
    NO_PREFERENCE = "NO_PREFERENCE"
    REJECT = "REJECT"
    ACCEPT = "ACCEPT"
    OVERRIDE = "OVERRIDE"
    RELAX_CONSTRAINT = "RELAX_CONSTRAINT"
    REQUEST_COMPARISON = "REQUEST_COMPARISON"
    REQUEST_MORE_OPTIONS = "REQUEST_MORE_OPTIONS"
    ASK_PRODUCT_QUESTION = "ASK_PRODUCT_QUESTION"


@dataclass(slots=True)
class Product:
    product_id: str
    title: str
    categories: list[str] = field(default_factory=list)
    brand: str | None = None
    price: float | None = None
    features: list[str] = field(default_factory=list)
    description: str | None = None
    attributes: dict[str, list[str]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Constraint:
    attribute: str
    values: list[str]
    strength: Literal["hard", "soft"]
    disclosed: bool = False
    active: bool = True
    source: str | None = None
    relaxable: bool = False

    @property
    def key(self) -> str:
        return f"{self.attribute}:{'|'.join(self.values)}"


@dataclass(slots=True)
class TargetProductGoal:
    goal_id: str
    target_product_id: str
    constraints: list[Constraint] = field(default_factory=list)
    category: str | None = None
    source_dataset: str = "unknown"
    goal_type: Literal["target_product"] = "target_product"


@dataclass(slots=True)
class NeedBasedGoal:
    goal_id: str
    category: str | None
    hard_constraints: list[Constraint] = field(default_factory=list)
    soft_preferences: list[Constraint] = field(default_factory=list)
    alternatives: dict[str, list[str]] = field(default_factory=dict)
    min_soft_matches: int = 1
    source_dataset: str | None = None
    goal_type: Literal["need_based"] = "need_based"


ShoppingGoal = TargetProductGoal | NeedBasedGoal


@dataclass(slots=True)
class Persona:
    name: str
    verbosity: float
    patience: float
    decisiveness: float
    price_sensitivity: float
    brand_loyalty: float
    shopping_expertise: float
    willingness_to_clarify: float
    openness_to_alternatives: float
    comparison_tendency: float
    preference_stability: float


@dataclass(slots=True)
class Fact:
    attribute: str
    values: list[str]


@dataclass(slots=True)
class DialogueAct:
    type: DialogueActType
    attribute: str | None = None
    values: list[str] = field(default_factory=list)
    reason_code: str | None = None
    references: list[str] = field(default_factory=list)
    allowed_facts: list[Fact] = field(default_factory=list)
    surface_text: str | None = None


@dataclass(slots=True)
class Recommendation:
    product_id: str
    score: float | None = None
    raw: Any | None = None


@dataclass(slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(slots=True)
class AgentResponse:
    message: str = ""
    ask_attribute: str | None = None
    recommendations: list[Recommendation] = field(default_factory=list)
    usage: Usage | None = None
    raw: Any | None = None
    error: str | None = None


@dataclass(slots=True)
class AcceptanceResult:
    accepted: bool
    product_id: str | None = None
    rank: int | None = None
    hard_matches: int = 0
    hard_total: int = 0
    soft_matches: int = 0
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OverrideEvent:
    turn: int
    attribute: str
    old_values: list[str]
    new_values: list[str]


@dataclass(slots=True)
class RelaxationEvent:
    turn: int
    attribute: str
    old_values: list[str]
    new_values: list[str]


@dataclass(slots=True)
class ConversationTurn:
    turn: int
    user_message: str
    agent_response: AgentResponse | None = None
    user_dialogue_act: DialogueAct | None = None
    dialogue_act: DialogueAct | None = None
    user_generation_latency_ms: float = 0.0
    agent_latency_ms: float = 0.0
    agent_usage_reported: bool = False
    agent_layer_trace: list[dict[str, Any]] = field(default_factory=list)
    agent_trace_error: str | None = None


@dataclass(slots=True)
class ScenarioSpec:
    scenario_id: str
    goal: ShoppingGoal
    persona_template: str
    max_turns: int = 10
    initial_disclosure_policy: str = "category_plus_one"
    scheduled_overrides: list[OverrideEvent] = field(default_factory=list)
    scheduled_relaxations: list[RelaxationEvent] = field(default_factory=list)
    persona_driven_override_enabled: bool = False
    seed: int = 42
    protocol: Literal["techjam", "realistic"] = "realistic"
    scenario_type: str = "realistic"
    user_profile: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UserState:
    session_id: str
    turn: int
    goal: ShoppingGoal
    persona: Persona
    active_constraints: list[Constraint]
    disclosed_constraints: set[str] = field(default_factory=set)
    removed_constraints: list[Constraint] = field(default_factory=list)
    override_history: list[OverrideEvent] = field(default_factory=list)
    relaxation_history: list[RelaxationEvent] = field(default_factory=list)
    conversation_history: list[ConversationTurn] = field(default_factory=list)
    last_dialogue_act: DialogueAct | None = None
    accepted_product_id: str | None = None
    terminated: bool = False
    termination_reason: Literal["accept", "max_turns"] | None = None
