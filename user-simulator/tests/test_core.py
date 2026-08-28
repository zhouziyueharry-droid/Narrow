from user_simulator.acceptance import AcceptanceChecker
from user_simulator.adapters import PythonAgentAdapter
from user_simulator.models import (
    Constraint,
    NeedBasedGoal,
    Product,
    Recommendation,
    ScenarioSpec,
    TargetProductGoal,
)
from user_simulator.personas import get_persona
from user_simulator.simulator import Simulator
from user_simulator.verbalizers import TemplateVerbalizer


def test_target_product_acceptance():
    product = Product("A", "Shoe")
    checker = AcceptanceChecker({"A": product})
    goal = TargetProductGoal("g", "A")
    result = checker.check(goal, [Recommendation("X"), Recommendation("A")])
    assert result.accepted is True
    assert result.rank == 2


def test_need_based_acceptance_with_alternative():
    product = Product(
        "A",
        "Running Shoe",
        categories=["running shoes"],
        brand="Adidas",
        price=90.0,
        attributes={"color": ["black"]},
    )
    goal = NeedBasedGoal(
        goal_id="g",
        category="running shoes",
        hard_constraints=[Constraint("budget_max", ["100"], "hard")],
        soft_preferences=[Constraint("brand", ["Nike"], "soft")],
        alternatives={"brand": ["Adidas"]},
        min_soft_matches=1,
    )
    result = AcceptanceChecker({"A": product}).check(goal, [Recommendation("A")])
    assert result.accepted is True


def test_template_verbalizer_is_deterministic():
    persona = get_persona("casual_browser")
    assert persona.name == "casual_browser"
    verbalizer = TemplateVerbalizer()
    from user_simulator.models import DialogueAct, DialogueActType, Fact
    from user_simulator.verbalizers import VerbalizationRequest

    request = VerbalizationRequest(
        persona=persona,
        dialogue_act=DialogueAct(
            DialogueActType.ANSWER_ATTRIBUTE,
            attribute="color",
            values=["black"],
            allowed_facts=[Fact("color", ["black"])],
        ),
        allowed_facts=[Fact("color", ["black"])],
        conversation_history=[],
    )
    assert verbalizer.verbalize(request) == verbalizer.verbalize(request)


class MockAgent:
    def __init__(self):
        self.turn = 0

    def reset(self, session_id, user_profile):
        self.turn = 0

    def respond(self, session_id, user_message, turn, top_k):
        self.turn = turn
        if turn == 1:
            return {"message": "Any color preference?", "ask_attribute": "color", "recommendations": []}
        return {"message": "Here you go", "ask_attribute": None, "recommendations": [{"parent_asin": "A"}]}


def test_full_session_accepts_target():
    catalog = {"A": Product("A", "Black Shoe", attributes={"color": ["black"]})}
    goal = TargetProductGoal(
        goal_id="g",
        target_product_id="A",
        constraints=[Constraint("color", ["black"], "soft")],
        category="shoes",
    )
    scenario = ScenarioSpec("s", goal, "decisive_buyer", max_turns=3, seed=7)
    simulator = Simulator(catalog, PythonAgentAdapter(MockAgent()))
    result = simulator.run_scenario(scenario)
    assert result["success"] is True
    assert result["turns"] == 2
    assert result["acceptance_rank"] == 1
