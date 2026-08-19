"""Tracker agent — the part that runs for months.

This is what makes Aftermath an agent rather than a form filler. It runs on a
schedule, with no one watching, and it:

* checks which institutions have responded and which have gone quiet;
* marks a step *stalled* once the institution's ``responsiveness_days.max`` has
  passed with no reply;
* drafts the follow-up, escalating in tone and channel as time passes;
* recomputes the critical path when anything slips, and warns when an
  irreversible deadline moves from TIGHT to AT RISK;
* surfaces the blocked items to the human instead of quietly retrying forever.

TODO(week 3):
  - EventBridge schedule -> AgentCore Runtime, one sweep per day
  - AgentCore Memory for per-case memory that survives months
  - approval queue for every outbound message (never auto-send)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StepState(str, Enum):
    NOT_STARTED = "not_started"
    SUBMITTED = "submitted"
    WAITING = "waiting"
    STALLED = "stalled"
    BLOCKED = "blocked"
    DONE = "done"


@dataclass
class StepStatus:
    step_id: str
    state: StepState = StepState.NOT_STARTED
    submitted_on_day: int | None = None
    last_contact_day: int | None = None
    chase_count: int = 0
    note: str | None = None


def is_stalled(status: StepStatus, today: int, max_response_days: int) -> bool:
    """A step is stalled once the institution has had longer than its worst
    typical turnaround and still has not replied."""
    if status.state not in (StepState.SUBMITTED, StepState.WAITING):
        return False
    reference = status.last_contact_day
    if reference is None:
        reference = status.submitted_on_day
    if reference is None:
        return False
    return (today - reference) > max_response_days
