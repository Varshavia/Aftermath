"""Rule pack loading and validation.

A rule pack is a declarative YAML description of what has to happen after a death
in one jurisdiction. See ``docs/PACK_SCHEMA.md``.

The loader is deliberately strict. A pack that claims ``confidence: verified``
without a source is a bug, not a warning — the whole safety story of this project
rests on every verified claim being traceable.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

Confidence = Literal["verified", "common_practice", "ask_a_professional"]
Severity = Literal["critical", "high", "normal"]
ArtifactKind = Literal["document", "information", "status"]

#: Conditions a step may be gated on. Extend this rather than writing
#: jurisdiction-specific ``if`` statements anywhere in the engine.
KNOWN_CONDITIONS: set[str] = {
    "always",
    "has_property",
    "has_vehicle",
    "has_business",
    "has_eligible_survivors",
    "has_foreign_assets",
}


class PackValidationError(Exception):
    """Raised when a pack is internally inconsistent."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("Invalid rule pack:\n  - " + "\n  - ".join(problems))


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(_Base):
    cite: str
    url: str | None = None
    retrieved: date | str | None = None


class Duration(_Base):
    """A duration in days. ``max`` is what the critical path plans against."""

    min: int | None = None
    typical: int | None = None
    max: int

    @property
    def worst_case(self) -> int:
        return self.max

    @property
    def expected(self) -> int:
        return self.typical if self.typical is not None else self.max


class Cost(_Base):
    currency: str | None = None
    typical: float | None = None


class Meta(_Base):
    jurisdiction: str
    name: str
    version: str
    language: str
    last_reviewed: date | str
    status: Literal["draft", "reviewed"] = "draft"


class Artifact(_Base):
    id: str
    kind: ArtifactKind
    name_en: str
    name_local: str | None = None


class Deadline(_Base):
    id: str
    name_en: str
    name_local: str | None = None
    duration_days: int
    starts_from: Literal["date_of_death", "knowledge_of_death"] = "date_of_death"
    severity: Severity = "normal"
    irreversible: bool = False
    requires_decision_input: list[str] = Field(default_factory=list)
    consequence_en: str | None = None
    consequence_local: str | None = None
    confidence: Confidence = "common_practice"
    source: Source | None = None
    notes_local: str | None = None


class Institution(_Base):
    id: str
    name_en: str
    name_local: str | None = None
    channels: list[str] = Field(default_factory=list)
    responsiveness_days: Duration | None = None


class Step(_Base):
    id: str
    name_en: str
    name_local: str | None = None
    institution: str | None = None
    requires: list[str] = Field(default_factory=list)
    produces: list[str] = Field(default_factory=list)
    duration_days: Duration
    cost: Cost | None = None
    confidence: Confidence = "common_practice"
    source: Source | None = None
    documents: list[str] = Field(default_factory=list)
    applies_if: str = "always"
    notes_local: str | None = None
    blocking: bool = False


class Pack(_Base):
    meta: Meta
    artifacts: list[Artifact] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    institutions: list[Institution] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)

    # -- lookups -----------------------------------------------------------
    @property
    def artifact_ids(self) -> set[str]:
        return {a.id for a in self.artifacts}

    def step(self, step_id: str) -> Step:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(step_id)

    def artifact(self, artifact_id: str) -> Artifact:
        for a in self.artifacts:
            if a.id == artifact_id:
                return a
        raise KeyError(artifact_id)

    def deadline(self, deadline_id: str) -> Deadline:
        for d in self.deadlines:
            if d.id == deadline_id:
                return d
        raise KeyError(deadline_id)

    def institution(self, institution_id: str) -> Institution:
        for i in self.institutions:
            if i.id == institution_id:
                return i
        raise KeyError(institution_id)

    # -- validation --------------------------------------------------------
    def validate_consistency(self) -> None:
        problems: list[str] = []
        artifact_ids = self.artifact_ids
        institution_ids = {i.id for i in self.institutions}

        seen_steps: set[str] = set()
        for s in self.steps:
            if s.id in seen_steps:
                problems.append(f"duplicate step id: {s.id}")
            seen_steps.add(s.id)

            for a in s.requires:
                if a not in artifact_ids:
                    problems.append(f"step '{s.id}' requires unknown artifact '{a}'")
            for a in s.produces:
                if a not in artifact_ids:
                    problems.append(f"step '{s.id}' produces unknown artifact '{a}'")
            if s.institution is not None and s.institution not in institution_ids:
                problems.append(f"step '{s.id}' names unknown institution '{s.institution}'")
            if s.applies_if not in KNOWN_CONDITIONS:
                problems.append(
                    f"step '{s.id}' uses unknown condition '{s.applies_if}'. "
                    f"Add it to KNOWN_CONDITIONS instead of special-casing it."
                )
            # Safety rule 2: no verified claim without a source.
            if s.confidence == "verified" and s.source is None:
                problems.append(f"step '{s.id}' is marked verified but has no source")

        for d in self.deadlines:
            for a in d.requires_decision_input:
                if a not in artifact_ids:
                    problems.append(
                        f"deadline '{d.id}' needs unknown artifact '{a}' to be decidable"
                    )
            if d.confidence == "verified" and d.source is None:
                problems.append(f"deadline '{d.id}' is marked verified but has no source")

        # Every artifact should be producible by something, or it can never exist.
        produced = {a for s in self.steps for a in s.produces}
        for a in self.artifacts:
            if a.id not in produced:
                problems.append(f"artifact '{a.id}' is never produced by any step")

        if problems:
            raise PackValidationError(problems)


def load_pack(path: str | Path) -> Pack:
    """Load and validate a rule pack from disk."""
    path = Path(path)
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    pack = Pack.model_validate(raw)
    pack.validate_consistency()
    return pack
