"""Document agent — drafts the petitions, declarations and applications.

Produces a *draft*. Always a draft. The output goes into a review queue where a
human reads it, edits it and submits it themselves. Aftermath does not file.

TODO(week 2):
  - template registry keyed by the ``documents`` field on each pack step
  - Strands agent with a ``@tool`` that fills a template from case facts
  - human-in-the-loop interrupt before anything leaves the review queue
  - every generated document carries the source citation of the step it serves
"""

from __future__ import annotations

from dataclasses import dataclass

SYSTEM_PROMPT = """
You draft Turkish administrative documents for Aftermath.

- You produce a draft for a human to review, never a final filing.
- You use only facts supplied to you. If a required fact is missing, you leave a
  clearly marked blank; you never invent a name, a date or an account number.
- You match the register of official correspondence: plain, short, no flourish.
- You do not add legal argument or advice.
"""


@dataclass
class Draft:
    document_id: str
    step_id: str
    title: str
    body: str
    missing_fields: list[str]
    source_cite: str | None = None
    approved: bool = False
