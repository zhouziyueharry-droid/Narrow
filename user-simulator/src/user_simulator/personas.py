from __future__ import annotations

from dataclasses import asdict

from .models import Persona

PERSONA_TEMPLATES: dict[str, Persona] = {
    "decisive_buyer": Persona("decisive_buyer", 0.30, 0.55, 0.95, 0.60, 0.55, 0.70, 0.65, 0.55, 0.25, 0.90),
    "casual_browser": Persona("casual_browser", 0.70, 0.85, 0.30, 0.45, 0.30, 0.45, 0.85, 0.90, 0.70, 0.65),
    "bargain_hunter": Persona("bargain_hunter", 0.35, 0.55, 0.65, 0.95, 0.20, 0.55, 0.75, 0.80, 0.70, 0.75),
    "brand_loyalist": Persona("brand_loyalist", 0.45, 0.60, 0.75, 0.45, 0.95, 0.65, 0.65, 0.25, 0.55, 0.85),
    "picky_shopper": Persona("picky_shopper", 0.65, 0.60, 0.50, 0.75, 0.65, 0.70, 0.70, 0.35, 0.80, 0.80),
    "novice_shopper": Persona("novice_shopper", 0.75, 0.75, 0.35, 0.55, 0.25, 0.15, 0.90, 0.85, 0.45, 0.70),
    "expert_shopper": Persona("expert_shopper", 0.45, 0.65, 0.85, 0.65, 0.55, 0.95, 0.55, 0.60, 0.75, 0.90),
    "indecisive_shopper": Persona("indecisive_shopper", 0.80, 0.80, 0.15, 0.55, 0.35, 0.40, 0.85, 0.95, 0.90, 0.35),
}


def get_persona(name: str) -> Persona:
    try:
        persona = PERSONA_TEMPLATES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown persona template: {name}") from exc
    return Persona(**asdict(persona))
