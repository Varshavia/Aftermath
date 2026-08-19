"""Strands agents.

Everything that needs a model lives here. The engine underneath is deterministic
and model-free; these agents wrap it, talk to the outside world, and handle the
parts that genuinely need judgement.

Four agents, plus one stretch goal:

* ``planner``  — turns a rule pack plus a case description into a scheduled plan
* ``document`` — drafts petitions, declarations and applications
* ``tracker``  — watches institution responses, detects stalls, chases, escalates
* ``verifier`` — re-checks the sources behind pack rules and flags stale entries
* ``pack_author`` (stretch) — drafts a rule pack for a new jurisdiction

Rule 1 from CLAUDE.md applies to every one of them: **the agent never files or
sends anything itself.** It prepares; a human reviews and submits.
"""
