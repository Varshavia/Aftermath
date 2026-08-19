"""Backward scheduling from irreversible deadlines.

This is the heart of Aftermath and the reason it is not a to-do list.

Turkey gives the heirs three months to renounce an inheritance. To decide, they
need to know whether there are debts. To learn that, banks and public bodies must
be queried. To query them, a certificate of inheritance is required — which
itself takes weeks. So the real question is never "what do I have to do", it is
**"when is the last day I can start, and will I even make it?"**

The solver runs two passes over the case graph:

* a **forward pass** giving the earliest each artifact can realistically exist,
  planning against worst-case durations;
* a **backward pass** from each deadline giving the latest each step may start.

Where the two meet is the slack. Negative slack means the deadline is already
unreachable, and Aftermath says so rather than pretending.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aftermath.engine.graph import CaseGraph
from aftermath.engine.pack import Deadline

INFINITY = 10**6


@dataclass
class StepSchedule:
    step_id: str
    name: str
    duration_days: int
    earliest_start: int
    earliest_finish: int
    latest_start: int | None = None
    latest_finish: int | None = None
    #: set by :func:`solve` — this step carries the least slack of any step
    #: upstream of a deadline, so any delay here moves the deadline.
    critical: bool = False

    @property
    def slack(self) -> int | None:
        if self.latest_start is None:
            return None
        return self.latest_start - self.earliest_start

    @property
    def on_critical_path(self) -> bool:
        return self.critical


@dataclass
class DeadlineReport:
    deadline_id: str
    name: str
    day: int
    irreversible: bool
    severity: str
    #: The earliest day this deadline could realistically be honoured. For a
    #: *decision* deadline that is the day its last input exists; for an
    #: *action* deadline it is the day the discharging step could finish.
    #: A deadline that is both takes the later of the two.
    ready_day: int
    #: day - ready_day. Negative means the deadline cannot be met.
    slack_days: int
    feasible: bool
    #: ``decision`` — you must know something by then; ``action`` — you must
    #: have done something by then; ``both`` — the pack declares each.
    kind: str = "decision"
    missing_inputs: list[str] = field(default_factory=list)
    consequence: str | None = None

    @property
    def inputs_ready_day(self) -> int:
        """Deprecated alias for :attr:`ready_day`."""
        return self.ready_day


@dataclass
class Schedule:
    steps: dict[str, StepSchedule]
    deadlines: list[DeadlineReport]

    def critical_path(self) -> list[StepSchedule]:
        return sorted(
            (s for s in self.steps.values() if s.on_critical_path),
            key=lambda s: s.earliest_start,
        )

    def ordered(self) -> list[StepSchedule]:
        return sorted(self.steps.values(), key=lambda s: (s.earliest_start, s.step_id))

    @property
    def at_risk(self) -> list[DeadlineReport]:
        return [d for d in self.deadlines if not d.feasible]


def solve(graph: CaseGraph) -> Schedule:
    """Run the forward and backward passes over a case graph."""
    steps = _forward_pass(graph)
    reports = [_backward_pass(graph, steps, d) for d in graph.pack.deadlines]
    _mark_critical(steps)
    return Schedule(steps=steps, deadlines=reports)


def _mark_critical(steps: dict[str, StepSchedule]) -> None:
    """Flag the chain with the least room to slip.

    Only steps that sit upstream of a deadline have a latest start, so only they
    can be critical. Among those, the ones carrying the minimum slack are the
    ones where a day lost is a day lost off the deadline.
    """
    slacks = [s.slack for s in steps.values() if s.slack is not None]
    if not slacks:
        return
    tightest = min(slacks)
    for s in steps.values():
        s.critical = s.slack == tightest


# ---------------------------------------------------------------------------
# forward: how soon could this realistically be done
# ---------------------------------------------------------------------------
def _forward_pass(graph: CaseGraph) -> dict[str, StepSchedule]:
    artifact_ready: dict[str, int] = {}
    schedules: dict[str, StepSchedule] = {}

    for step_id in graph.order:
        step = graph.step(step_id)
        duration = step.duration_days.worst_case

        if step.requires:
            unmet = [a for a in step.requires if a not in artifact_ready]
            if unmet:
                # An input nothing in this case can produce. Treat as unreachable
                # rather than silently scheduling it on day zero.
                earliest_start = INFINITY
            else:
                earliest_start = max(artifact_ready[a] for a in step.requires)
        else:
            earliest_start = 0

        earliest_finish = (
            INFINITY if earliest_start >= INFINITY else earliest_start + duration
        )

        schedules[step_id] = StepSchedule(
            step_id=step_id,
            name=step.name_en,
            duration_days=duration,
            earliest_start=earliest_start,
            earliest_finish=earliest_finish,
        )

        for artifact in step.produces:
            current = artifact_ready.get(artifact, INFINITY)
            artifact_ready[artifact] = min(current, earliest_finish)

    return schedules


# ---------------------------------------------------------------------------
# backward: what is the last day this may start
# ---------------------------------------------------------------------------
def _backward_pass(
    graph: CaseGraph,
    schedules: dict[str, StepSchedule],
    deadline: Deadline,
) -> DeadlineReport:
    artifact_deadline: dict[str, int] = {}
    missing: list[str] = []

    for artifact in deadline.requires_decision_input:
        if graph.primary_producer(artifact) is None:
            missing.append(artifact)
            continue
        artifact_deadline[artifact] = deadline.duration_days

    # An action deadline is discharged by a step rather than by knowing
    # something. That step must itself finish by the deadline, and everything
    # upstream of it inherits the clock. Without this the filing step looks
    # unconstrained even though the filing *is* the deadline.
    satisfying = deadline.satisfied_by
    if satisfying is not None and satisfying not in schedules:
        satisfying = None  # the step does not apply to this case profile

    # Walk the graph in reverse topological order, pushing deadlines upstream.
    for step_id in reversed(graph.order):
        step = graph.step(step_id)
        relevant = [artifact_deadline[a] for a in step.produces if a in artifact_deadline]
        if step_id == satisfying:
            relevant.append(deadline.duration_days)
        if not relevant:
            continue

        latest_finish = min(relevant)
        latest_start = latest_finish - step.duration_days.worst_case

        sched = schedules[step_id]
        # A step may sit upstream of several deadlines; keep the tightest.
        if sched.latest_finish is None or latest_finish < sched.latest_finish:
            sched.latest_finish = latest_finish
            sched.latest_start = latest_start

        for artifact in step.requires:
            current = artifact_deadline.get(artifact, INFINITY)
            artifact_deadline[artifact] = min(current, latest_start)

    ready = _ready_day(graph, schedules, deadline, satisfying)
    slack = deadline.duration_days - ready

    if deadline.requires_decision_input and satisfying is not None:
        kind = "both"
    elif satisfying is not None:
        kind = "action"
    else:
        kind = "decision"

    return DeadlineReport(
        deadline_id=deadline.id,
        name=deadline.name_en,
        day=deadline.duration_days,
        irreversible=deadline.irreversible,
        severity=deadline.severity,
        ready_day=ready,
        slack_days=slack,
        feasible=slack >= 0 and not missing,
        kind=kind,
        missing_inputs=missing,
        consequence=deadline.consequence_en,
    )


def _ready_day(
    graph: CaseGraph,
    schedules: dict[str, StepSchedule],
    deadline: Deadline,
    satisfying: str | None,
) -> int:
    """The earliest day this deadline could realistically be honoured.

    Decision inputs and the discharging action are both hard requirements, so
    the answer is the later of the two — you cannot file before you can file,
    and you cannot decide before you know.
    """
    ready = 0

    for artifact in deadline.requires_decision_input:
        producer = graph.primary_producer(artifact)
        if producer is None:
            return INFINITY
        ready = max(ready, schedules[producer.id].earliest_finish)

    if satisfying is not None:
        ready = max(ready, schedules[satisfying].earliest_finish)

    return ready
