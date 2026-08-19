"""Jurisdiction-agnostic core.

Nothing in this package may make a network call, call a model, or contain a rule
that is specific to one country. All of that lives in ``packs/*.yaml`` (data) or
``aftermath.agents`` (LLM work). This boundary is what makes the engine testable and
what makes the "engine + rule pack" claim credible.
"""

from aftermath.engine.critical_path import Schedule, solve
from aftermath.engine.graph import CaseGraph
from aftermath.engine.pack import Pack, PackValidationError, load_pack

__all__ = [
    "Pack",
    "PackValidationError",
    "load_pack",
    "CaseGraph",
    "Schedule",
    "solve",
]
