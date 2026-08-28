from __future__ import annotations

import random

from .models import (
    AgentResponse,
    Constraint,
    DialogueAct,
    DialogueActType,
    Fact,
    OverrideEvent,
    RelaxationEvent,
    ScenarioSpec,
    UserState,
)


def _matching_constraint(state: UserState, attribute: str) -> Constraint | None:
    aliases = {"budget": {"budget", "budget_max", "budget_min"}}
    accepted_attributes = aliases.get(attribute, {attribute})
    for constraint in state.active_constraints:
        if (
            constraint.active
            and not constraint.disclosed
            and constraint.attribute in accepted_attributes
        ):
            return constraint
    return None


class UserPolicy:
    def __init__(self, scenario: ScenarioSpec):
        self.scenario = scenario
        self.rng = random.Random(scenario.seed)

    def initial_act(self, state: UserState) -> DialogueAct:
        facts: list[Fact] = []
        if getattr(state.goal, "category", None):
            facts.append(Fact("category", [state.goal.category]))
        undisclosed = [
            c
            for c in state.active_constraints
            if c.active and not c.disclosed and c.attribute != "category"
        ]
        if self.scenario.initial_disclosure_policy == "category_plus_one" and undisclosed:
            selected = self.rng.choice(undisclosed)
            selected.disclosed = True
            state.disclosed_constraints.add(selected.key)
            facts.append(Fact(selected.attribute, list(selected.values)))
        return DialogueAct(DialogueActType.INITIAL_REQUEST, allowed_facts=facts)

    def next_act(self, state: UserState, response: AgentResponse, accepted: bool) -> DialogueAct:
        if accepted:
            return DialogueAct(DialogueActType.ACCEPT)

        override = self._scheduled_override(state.turn)
        if override is None:
            override = self._persona_override(state)
        if override is not None:
            self._apply_override(state, override)
            return DialogueAct(
                DialogueActType.OVERRIDE,
                attribute=override.attribute,
                values=list(override.new_values),
                allowed_facts=[Fact(override.attribute, list(override.new_values))],
            )

        relaxation = self._scheduled_relaxation(state.turn)
        if relaxation is not None:
            self._apply_relaxation(state, relaxation)
            return DialogueAct(
                DialogueActType.RELAX_CONSTRAINT,
                attribute=relaxation.attribute,
                values=list(relaxation.new_values),
                allowed_facts=[Fact(relaxation.attribute, list(relaxation.new_values))],
            )

        if response.ask_attribute:
            constraint = _matching_constraint(state, response.ask_attribute)
            if constraint is None:
                return DialogueAct(
                    DialogueActType.NO_PREFERENCE,
                    attribute=response.ask_attribute,
                )
            constraint.disclosed = True
            state.disclosed_constraints.add(constraint.key)
            return DialogueAct(
                DialogueActType.ANSWER_ATTRIBUTE,
                attribute=constraint.attribute,
                values=list(constraint.values),
                allowed_facts=[Fact(constraint.attribute, list(constraint.values))],
            )

        if response.recommendations:
            x = self.rng.random()
            if x < state.persona.comparison_tendency * 0.35:
                return DialogueAct(DialogueActType.REQUEST_COMPARISON)
            if x < 0.70:
                return DialogueAct(DialogueActType.REQUEST_MORE_OPTIONS)
            return DialogueAct(DialogueActType.REJECT)

        return DialogueAct(DialogueActType.INFORM)

    def _scheduled_override(self, turn: int) -> OverrideEvent | None:
        for event in self.scenario.scheduled_overrides:
            if event.turn == turn:
                return event
        return None

    def _persona_override(self, state: UserState) -> OverrideEvent | None:
        if not self.scenario.persona_driven_override_enabled or state.turn < 3:
            return None
        probability = max(0.0, min(0.25, (1.0 - state.persona.preference_stability) * 0.25))
        if self.rng.random() >= probability:
            return None
        candidates = [c for c in state.active_constraints if c.active and c.strength == "soft" and c.relaxable]
        if not candidates:
            return None
        c = candidates[0]
        # v0.1 never invents a new value. Persona-driven override may only remove
        # a pre-generated soft preference, represented by an empty new value set.
        return OverrideEvent(state.turn, c.attribute, list(c.values), [])

    def _apply_override(self, state: UserState, event: OverrideEvent) -> None:
        for constraint in state.active_constraints:
            if (
                constraint.active
                and constraint.attribute == event.attribute
                and (not event.old_values or constraint.values == event.old_values)
            ):
                constraint.active = False
                state.removed_constraints.append(constraint)
        if event.new_values:
            replacement = Constraint(event.attribute, list(event.new_values), "soft", disclosed=True, active=True)
            state.active_constraints.append(replacement)
        state.override_history.append(event)

    def _scheduled_relaxation(self, turn: int) -> RelaxationEvent | None:
        for event in self.scenario.scheduled_relaxations:
            if event.turn == turn:
                return event
        return None

    def _apply_relaxation(self, state: UserState, event: RelaxationEvent) -> None:
        for constraint in state.active_constraints:
            if constraint.active and constraint.attribute == event.attribute and constraint.relaxable:
                constraint.active = False
                state.removed_constraints.append(constraint)
        if event.new_values:
            state.active_constraints.append(
                Constraint(event.attribute, list(event.new_values), "soft", disclosed=True, active=True, relaxable=True)
            )
        state.relaxation_history.append(event)
