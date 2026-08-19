"""Planner agent — turns a case description into a scheduled plan.

The heavy lifting is deterministic and lives in ``aftermath.engine``. The model's job
is narrower and genuinely needs judgement:

* read a free-form description of the estate ("he had a flat in Izmir, an old
  car, no business") and resolve it into pack conditions;
* explain the resulting schedule to a grieving person in their own language,
  without giving advice.

Keeping the scheduling out of the model is deliberate. A plan that changes
between runs is useless when the stake is a three-month statutory deadline.
"""

from __future__ import annotations

from aftermath.engine import load_pack, solve
from aftermath.engine.graph import CaseGraph, CaseProfile
from aftermath.engine.pack import KNOWN_CONDITIONS

SYSTEM_PROMPT = f"""
You are the planning component of Aftermath, a tool that helps a bereaved family work
through the administrative aftermath of a death.

Your only job is to read a description of the estate and decide which of these
conditions hold:

{", ".join(sorted(KNOWN_CONDITIONS))}

Rules you must not break:
- You do not give legal advice. You do not recommend whether to accept or
  renounce an inheritance. You state facts, clocks and consequences.
- You never invent a procedure, an institution or a deadline. Everything comes
  from the rule pack.
- If the description is ambiguous, say what you are unsure about rather than
  guessing.
- You are speaking to someone who has just lost a family member. Be brief, plain
  and calm. No cheerfulness, no condolence boilerplate.
"""


def resolve_conditions(description: str) -> list[str]:
    """Map a free-text estate description onto pack conditions.

    TODO(week 2): implement with a Strands agent using structured output against
    ``KNOWN_CONDITIONS``. Deterministic fallback below keeps the CLI usable and
    the tests model-free.
    """
    text = description.lower()
    hits: list[str] = []
    hints = {
        "has_property": ("daire", "ev", "tapu", "arsa", "flat", "house", "property"),
        "has_vehicle": ("araba", "araç", "otomobil", "car", "vehicle"),
        "has_business": ("şirket", "işletme", "ortaklık", "business", "company"),
        "has_eligible_survivors": ("eş", "çocuk", "spouse", "child", "widow"),
    }
    for condition, needles in hints.items():
        if any(n in text for n in needles):
            hits.append(condition)
    return hits


def plan_case(pack_path: str, description: str = "") -> tuple[CaseGraph, object]:
    """Build the plan for a case. Pure engine — no model call."""
    pack = load_pack(pack_path)
    profile = CaseProfile.from_list(resolve_conditions(description))
    graph = CaseGraph(pack, profile)
    return graph, solve(graph)
