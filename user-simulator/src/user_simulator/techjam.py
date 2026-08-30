from __future__ import annotations

import random
import re
from typing import Any

from .models import (
    AgentResponse,
    DialogueAct,
    DialogueActType,
    OverrideEvent,
    ScenarioSpec,
    UserState,
)

ALLOWED_ATTRIBUTES = {
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
}
MATERIALS = (
    "cotton",
    "polyester",
    "nylon",
    "leather",
    "wool",
    "spandex",
    "silk",
    "rayon",
    "fabric",
)
SEARCH_FIELDS = ("title", "features", "details", "description", "categories", "store")
MATERIAL_RE = re.compile(r"\b(cotton|polyester|nylon|leather|wool|spandex|silk|rayon|fabric)\b", re.IGNORECASE)
COLOR_RE = re.compile(r"\b(black|white|blue|red|pink|green|brown|gray|grey|purple|yellow|orange)\b", re.IGNORECASE)


def searchable_text(product: dict[str, Any]) -> str:
    parts: list[str] = []
    for field in SEARCH_FIELDS:
        value = product.get(field)
        if isinstance(value, dict):
            parts.extend(f"{key} {item}" for key, item in value.items())
        elif isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).strip()


def _flatten_values(value: object) -> list[str]:
    if isinstance(value, dict):
        return [f"{key}: {item}" for key, item in value.items() if item not in (None, "", [])]
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)] if value not in (None, "") else []


def _clean_constraint(value: str, limit: int) -> str:
    return re.sub(r"\s+", " ", value).strip(" -;,.\t\n")[:limit].rstrip()


def build_intent_card(product: dict[str, Any], limit: int = 180) -> dict[str, Any]:
    """Reproduce the participant evaluator's deterministic public intent card."""

    title = _clean_constraint(str(product.get("title") or "product"), limit)
    candidates = [*_flatten_values(product.get("features")), *_flatten_values(product.get("details"))]
    corpus = searchable_text(product)
    material = MATERIAL_RE.search(corpus)
    color = COLOR_RE.search(corpus)
    if material:
        candidates.insert(0, material.group(1).lower())
    if color:
        candidates.insert(1, f"color: {color.group(1).lower()}")
    if product.get("price") not in (None, ""):
        candidates.append(f"budget around ${product['price']}")
    cleaned = list(
        dict.fromkeys(
            _clean_constraint(item, limit)
            for item in candidates
            if _clean_constraint(item, limit)
        )
    )
    if not cleaned:
        cleaned = [title]
    return {
        "target_category": title,
        "hard_constraints": cleaned[:2],
        "soft_preferences": cleaned[2:4] or cleaned[:1],
    }


def build_behavior(scenario_type: str, card: dict[str, Any], sample_id: str) -> dict[str, Any]:
    behavior: dict[str, Any] = {"scenario_type": scenario_type}
    if scenario_type == "intent_override":
        hard = card.get("hard_constraints", [])
        soft = card.get("soft_preferences", [])
        old_value = soft[-1] if soft else "I prefer a different style."
        new_value = hard[0] if hard else "Please prioritize the target requirements."
        rng = random.Random(f"{sample_id}\0{scenario_type}")
        behavior["override"] = {
            "turn": rng.choice([3, 4]),
            "old_value": old_value,
            "new_value": new_value,
            "message": f"Actually, ignore my earlier preference. What I need is: {new_value}.",
        }
    return behavior


def coarse_category(values: list[str]) -> str:
    excluded = {"clothing", "clothing shoes & jewelry", "clothing, shoes & jewelry"}
    cleaned: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part and part.lower() not in excluded:
                cleaned.append(part)
    return " ".join(cleaned[-2:]) if cleaned else "clothing item"


def classify_constraint(value: str) -> str:
    lowered = value.lower()
    if "budget" in lowered or re.search(r"(?:\$|<=|under)\s*\d", lowered):
        return "budget"
    if any(material in lowered for material in MATERIALS):
        return "material"
    if any(word in lowered for word in ("color", "black", "white", "blue", "red", "pink", "green")):
        return "color"
    if any(word in lowered for word in ("size", "sizing", "width", "wide", "narrow")):
        return "size"
    if any(word in lowered for word in ("department", "style", "fit", "sleeve", "neck")):
        return "style"
    if any(word in lowered for word in ("hiking", "running", "gym", "winter", "outdoor", "work")):
        return "use_case"
    return "feature"


class TechJamUserPolicy:
    """Deterministic Track 4 participant-side user policy."""

    def __init__(self, scenario: ScenarioSpec):
        self.scenario = scenario
        self.spec = scenario.metadata.get("techjam", {})
        self.disclosed: set[str] = set()
        self.boundary_used = False
        self.override_applied = scenario.scenario_type != "intent_override"

    def initial_act(self, state: UserState) -> DialogueAct:
        category = str(self.spec.get("category") or "clothing item")
        card = self.spec.get("intent_card", {})
        behavior = self.spec.get("behavior", {})
        scenario_type = self.scenario.scenario_type
        custom_message = behavior.get("initial_message")
        if isinstance(custom_message, str) and custom_message.strip():
            disclosed = behavior.get("initial_disclosed", [])
            if isinstance(disclosed, list):
                self.disclosed.update(str(value) for value in disclosed)
            message = custom_message.strip()
        elif scenario_type == "buying" and card.get("hard_constraints"):
            constraint = str(card["hard_constraints"][0])
            self.disclosed.add(constraint)
            message = f"I'm looking for {category}. A key requirement is: {constraint}."
        elif scenario_type == "intent_override":
            override = self.spec.get("behavior", {}).get("override") or {}
            old_value = str(override.get("old_value", "I prefer a different style."))
            message = f"I'm looking for {category}. {old_value}"
        else:
            message = f"I'm looking for {category}, but I'm still exploring."
        return DialogueAct(DialogueActType.INITIAL_REQUEST, reason_code=f"techjam:{scenario_type}", surface_text=message)

    def acceptance_allowed(self, turn: int) -> bool:
        if self.scenario.scenario_type != "intent_override":
            return True
        override = self.spec.get("behavior", {}).get("override") or {}
        return turn >= int(override.get("turn", 3))

    def next_act(self, state: UserState, response: AgentResponse, accepted: bool) -> DialogueAct:
        if accepted:
            return DialogueAct(DialogueActType.ACCEPT, reason_code="techjam:accept", surface_text="That works for me.")

        override = self.spec.get("behavior", {}).get("override") or {}
        override_turn = int(override.get("turn", 3))
        if not self.override_applied and state.turn + 1 == override_turn:
            self.override_applied = True
            new_value = str(override.get("new_value", ""))
            old_value = str(override.get("old_value", ""))
            if new_value:
                self.disclosed.add(new_value)
            state.override_history.append(
                OverrideEvent(
                    turn=override_turn,
                    attribute="intent",
                    old_values=[old_value] if old_value else [],
                    new_values=[new_value] if new_value else [],
                )
            )
            message = str(override.get("message", "Actually, please ignore my earlier preference."))
            return DialogueAct(
                DialogueActType.OVERRIDE,
                values=[new_value] if new_value else [],
                reason_code="techjam:intent_override",
                surface_text=message,
            )

        attribute = response.ask_attribute if isinstance(response.ask_attribute, str) else None
        if self.scenario.scenario_type == "boundary" and not self.boundary_used and attribute:
            self.boundary_used = True
            boundary = self.spec.get("behavior", {}).get("boundary") or {}
            message = boundary.get("message")
            boundary_attribute = boundary.get("attribute")
            return DialogueAct(
                DialogueActType.NO_PREFERENCE,
                attribute=str(boundary_attribute or attribute),
                reason_code="techjam:boundary",
                surface_text=(
                    str(message)
                    if isinstance(message, str) and message.strip()
                    else f"I don't have a preference for {attribute}; please use your judgment."
                ),
            )
        if not attribute:
            return DialogueAct(
                DialogueActType.INFORM,
                reason_code="techjam:ask_specific",
                surface_text="Those options are not quite right yet. Ask me about one specific attribute.",
            )
        if attribute not in ALLOWED_ATTRIBUTES:
            attribute = "other"
        card = self.spec.get("intent_card", {})
        constraints = [
            *[str(value) for value in card.get("hard_constraints", [])],
            *[str(value) for value in card.get("soft_preferences", [])],
        ]
        matches = [
            value
            for value in constraints
            if value not in self.disclosed and (attribute == "other" or classify_constraint(value) == attribute)
        ][:2]
        if not matches:
            return DialogueAct(
                DialogueActType.NO_PREFERENCE,
                attribute=attribute,
                reason_code="techjam:no_additional_preference",
                surface_text=f"I don't have an additional preference for {attribute}.",
            )
        self.disclosed.update(matches)
        return DialogueAct(
            DialogueActType.ANSWER_ATTRIBUTE,
            attribute=attribute,
            values=matches,
            reason_code="techjam:answer_attribute",
            surface_text="For that, what matters is: " + "; ".join(matches) + ".",
        )
