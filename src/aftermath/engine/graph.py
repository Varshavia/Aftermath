"""The artifact dependency graph for one case.

Steps do not depend on other steps. Steps consume **artifacts** and produce
**artifacts**::

    step A  --produces-->  artifact X  --required by-->  step B

This keeps the graph honest across jurisdictions: two countries may produce the
same artifact by completely different routes, and the engine does not care which.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aftermath.engine.pack import Pack, Step


class CycleError(Exception):
    """The pack describes a circular dependency."""


@dataclass
class CaseProfile:
    """What is true about this particular estate.

    Conditions are declared in the pack (``applies_if``) and supplied here. The
    engine never hardcodes them.
    """

    conditions: set[str] = field(default_factory=set)

    def allows(self, condition: str) -> bool:
        return condition == "always" or condition in self.conditions

    @classmethod
    def from_list(cls, conditions: list[str] | None) -> "CaseProfile":
        return cls(conditions=set(conditions or []))


class CaseGraph:
    """The subset of a pack that applies to one case, ordered."""

    def __init__(self, pack: Pack, profile: CaseProfile | None = None) -> None:
        self.pack = pack
        self.profile = profile or CaseProfile()
        self.steps: list[Step] = [s for s in pack.steps if self.profile.allows(s.applies_if)]
        self._by_id = {s.id: s for s in self.steps}
        self.order: list[str] = self._topological_order()

    # -- structure ---------------------------------------------------------
    def producers(self, artifact_id: str) -> list[Step]:
        """Steps that can produce this artifact, fastest worst-case first."""
        found = [s for s in self.steps if artifact_id in s.produces]
        return sorted(found, key=lambda s: s.duration_days.worst_case)

    def primary_producer(self, artifact_id: str) -> Step | None:
        """The route the planner assumes.

        When a pack offers more than one way to obtain an artifact (in Turkey a
        certificate of inheritance may come from a notary *or* a civil court) we
        plan against the fastest worst case, and surface the alternatives in the UI.
        """
        producers = self.producers(artifact_id)
        return producers[0] if producers else None

    def unreachable_artifacts(self) -> list[str]:
        """Artifacts nothing in this case can produce."""
        producible = {a for s in self.steps for a in s.produces}
        needed = {a for s in self.steps for a in s.requires}
        for d in self.pack.deadlines:
            needed.update(d.requires_decision_input)
        return sorted(needed - producible)

    def blocking_steps(self) -> list[Step]:
        """Steps the pack flags as gating almost everything downstream."""
        return [s for s in self.steps if s.blocking]

    # -- ordering ----------------------------------------------------------
    def _topological_order(self) -> list[str]:
        producible: dict[str, list[str]] = {}
        for s in self.steps:
            for a in s.produces:
                producible.setdefault(a, []).append(s.id)

        # step -> the steps that must complete before it
        prereqs: dict[str, set[str]] = {}
        for s in self.steps:
            deps: set[str] = set()
            for a in s.requires:
                deps.update(producible.get(a, []))
            prereqs[s.id] = deps

        order: list[str] = []
        permanent: set[str] = set()
        temporary: set[str] = set()

        def visit(step_id: str, trail: list[str]) -> None:
            if step_id in permanent:
                return
            if step_id in temporary:
                cycle = " -> ".join([*trail, step_id])
                raise CycleError(f"circular dependency: {cycle}")
            temporary.add(step_id)
            for dep in sorted(prereqs.get(step_id, ())):
                visit(dep, [*trail, step_id])
            temporary.discard(step_id)
            permanent.add(step_id)
            order.append(step_id)

        for s in self.steps:
            visit(s.id, [])
        return order

    def step(self, step_id: str) -> Step:
        return self._by_id[step_id]

    def __len__(self) -> int:
        return len(self.steps)
