# Architecture

## The one decision everything follows from

**Jurisdiction is data, not code.**

The agent's intelligence is not knowing Turkish inheritance law. It is ordering
institutions by dependency, computing the critical path, tracking deadlines,
chasing non-responders and escalating blockages. That engine is identical
everywhere; only the rulebook changes.

```
┌──────────────────────────────────────────────────────────────┐
│  AGENTS  (Strands — everything that needs a model)           │
│                                                              │
│   planner ─ document ─ tracker ─ verifier ─ (pack_author)    │
└───────────────────────────┬──────────────────────────────────┘
                            │ calls
┌───────────────────────────▼──────────────────────────────────┐
│  ENGINE  (pure Python — no network, no model, no AWS)        │
│                                                              │
│   pack.py           load + validate rule packs               │
│   graph.py          artifact dependency graph, topo order    │
│   critical_path.py  forward + backward passes, slack         │
└───────────────────────────┬──────────────────────────────────┘
                            │ reads
┌───────────────────────────▼──────────────────────────────────┐
│  RULE PACKS  (YAML — data)                                   │
│   packs/tr.yaml    packs/us.yaml                             │
└──────────────────────────────────────────────────────────────┘
```

If you write `if jurisdiction == "TR"` anywhere under `src/`, the pack schema is
missing a field. Extend the schema.

---

## Why the engine has no model in it

A plan that changes between runs is useless when the stake is a 90-day statutory
deadline. Scheduling is deterministic, testable and reproducible; the model is
used only where judgement is genuinely required — reading a free-text description
of an estate, drafting prose, deciding a chase is due, reading a source page.

Practical consequence: `pytest` runs with no credentials. If a test ever needs a
key, something has leaked across the boundary.

---

## The graph: artifacts, not tasks

Steps do not depend on steps. Steps consume and produce **artifacts**:

```
step A  --produces-->  artifact X  --required by-->  step B
```

Two jurisdictions may reach the same artifact by different routes — in Turkey a
certificate of inheritance comes from a notary *or* a civil court — and the
engine does not care which. When a pack offers several producers, the planner
schedules against the fastest worst case and surfaces the alternatives.

---

## The critical path

Two passes:

**Forward** — how soon could each artifact realistically exist, planning against
worst-case durations. Gives `earliest_start` / `earliest_finish` per step.

**Backward** — from each deadline, through `requires_decision_input`, up the
artifact chain. Gives `latest_start` / `latest_finish` per step.

The difference is slack. Negative slack means the deadline is already
unreachable, and Aftermath reports it as `AT RISK` rather than pretending.

A step with no `latest_start` is real work that nothing irreversible depends on —
closing the phone line matters, but nobody loses a right if it slips a week.

---

## Agent topology

| agent | pattern | runs |
|---|---|---|
| `planner` | resolves free text → pack conditions; calls the engine | on case creation and on any change |
| `document` | drafts petitions and declarations from templates + case facts | when a step becomes actionable |
| `tracker` | detects stalls, drafts follow-ups, escalates, re-solves the schedule | daily, unattended |
| `verifier` | re-reads pack sources, flags drift | weekly |
| `pack_author` *(stretch)* | drafts a rule pack for a new jurisdiction from official sources | on demand |

The Strands **Graph** pattern carries the main deterministic line:

```
intake → resolve-jurisdiction → plan → critical-path
       → [human approval] → dispatch → track → escalate → report
```

Human-in-the-loop interrupts sit before every outbound batch and every plan
change. Guardrails block PII leaving the case boundary and block any output that
reads as legal advice.

---

## AWS

| service | use |
|---|---|
| Bedrock | models behind the Strands agents |
| AgentCore Runtime | deployment target |
| AgentCore Memory | per-case memory that has to survive months |
| AgentCore Identity | access to case data |
| AgentCore Observability | OTEL traces |
| EventBridge | the daily tracker sweep — the agent runs with nobody watching |

---

## Known gaps (v0)

- **Action deadlines vs decision deadlines.** `requires_decision_input` models
  "you cannot decide until X exists". A deadline that is itself an action (*file
  the declaration by day 120*) does not currently pull its own step onto the
  backward pass. Needs a `satisfied_by: <step_id>` field on `deadlines`.
- **Multiple producers** are resolved by fastest worst case, with no cost or
  eligibility weighting.
- **Durations are static.** They should eventually learn from observed
  institution response times.
- No per-state US packs; `us.yaml` is illustrative only.
