"""Verifier agent — keeps the rule packs honest.

Legislation changes and official pages move. A pack that was right in August is
not automatically right in November. The verifier re-reads the source behind each
rule and flags entries whose source has moved, changed or gone.

This exists to answer the obvious objection — *"but the law changes"* — before a
judge raises it, and it is real, unglamorous agent work: dozens of URLs, on a
schedule, with a human reading only the diffs.

Rules:
  - it never edits a pack; it opens a flag for a human
  - a rule whose source cannot be reached drops to ``ask_a_professional``
  - ``meta.last_reviewed`` is only bumped by a human, never by this agent

TODO(week 3): fetch + diff each source, structured output, weekly sweep.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FlagKind = Literal["source_unreachable", "source_changed", "no_source", "stale_review"]


@dataclass
class VerificationFlag:
    target_kind: Literal["step", "deadline"]
    target_id: str
    kind: FlagKind
    detail: str
