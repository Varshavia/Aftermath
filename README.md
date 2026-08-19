# Aftermath

**Losing someone starts 40+ institutions and months of paperwork. Aftermath maps the path, drafts every document, and watches every deadline — so the family can grieve instead of file.**

> The funeral takes a day. The aftermath takes a year.

Built for the [Agents for Humans](https://agentsforhumans.devpost.com/) hackathon
with the [Strands Agents SDK](https://strandsagents.com/). Track: **Everyday Agents**.

---

## The problem

When a person dies, the surviving family is handed a months-long bureaucratic
project. In Turkey that means the certificate of inheritance, the banks, the tax
office, the land registry, the social security institution, vehicle transfer,
insurance and private pensions, utility accounts, phone lines, subscriptions —
dozens of institutions, each with its own required documents, its own order, and
its own clock. US industry estimates put settling an estate at roughly
**500–900 hours**. People do this while grieving.

### The part that actually hurts

Turkey runs two clocks that contradict each other:

| | |
|---|---|
| **Renunciation of inheritance** | **90 days** — miss it and the deceased's debts become yours. Irreversible. |
| **Inheritance and gift tax declaration** | **120 days** |

So the right to refuse expires *before* the declaration is even due.

And to decide whether to renounce, you need to know whether there are debts. To
learn that, you must query the banks. To query them, you need the certificate of
inheritance — which itself takes weeks.

```
DAY 0   death
  │
  ├─ certificate of inheritance                    ~1–3 weeks
  │      ├─ bank queries (each bank separately)    ~2–4 weeks
  │      ├─ credit bureau report
  │      └─ tax & social security queries
  │             └─▶ DEBT PICTURE COMPLETE
  │
  └────────────────────────▶ DAY 90: RENOUNCE OR NOT   ⚠ irreversible
```

Aftermath schedules **backwards** from irreversible deadlines and tells you the last
day each upstream step can start. That is the difference between this and a
checklist.

---

## What it does

- **Maps the case.** Builds the institution dependency graph for this particular
  estate — property, vehicle, business, surviving spouse all change the shape.
- **Computes the critical path.** Forward pass for what is realistically
  achievable, backward pass from every irreversible deadline, and the slack
  between them. Says *at risk* when a deadline is already unreachable.
- **Drafts the documents.** Petitions, declarations, applications — as drafts,
  for a human to review.
- **Tracks and chases.** Runs on a schedule for months, notices which
  institutions have gone quiet, drafts the follow-up, escalates blockages.
- **Keeps itself honest.** A verifier agent re-reads the sources behind each rule
  and flags entries that have gone stale.

---

## Architecture: jurisdiction is data, not code

Every country's procedure differs. But the agent's intelligence is not *knowing
Turkish inheritance law* — it is ordering institutions by dependency, computing
the critical path, chasing non-responders and escalating. That engine is the
same everywhere. Only the rulebook changes.

```
CORE ENGINE  (jurisdiction-agnostic, pure Python — no network, no model, no AWS)
   dependency graph · critical path · deadline tracking · escalation
        ▲
        │ reads
        │
RULE PACK  (declarative YAML — data, not code)
   packs/tr.yaml   Turkey — primary, sourced
   packs/us.yaml   United States — partial, proves the engine generalises
```

The engine runs with no credentials and no model. Everything that needs a model
lives in `src/aftermath/agents/`. That boundary is what makes the core testable — and
it is why swapping `tr.yaml` for `us.yaml` produces a US plan with no code change.

See [`docs/PACK_SCHEMA.md`](docs/PACK_SCHEMA.md) for the rule-pack format and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the agent topology.

---

## Safety

This is a legal-adjacent domain and being wrong hurts people. Five rules, spelled
out in [`docs/SAFETY.md`](docs/SAFETY.md):

1. **Aftermath never files or sends anything itself.** It prepares; a human reviews
   and submits.
2. **Every rule carries a source.** The pack loader refuses to mark a claim
   `verified` without one — that check is enforced in code and covered by a test.
3. **Confidence is displayed, not hidden:** `verified` / `common_practice` /
   `ask_a_professional`.
4. **This is a coordination tool, not a legal advisor.** Aftermath states the fact,
   the clock and the consequence. The decision belongs to the human.
5. **A verifier agent re-checks sources** and flags rules whose source moved.

Aftermath does not tell anyone whether to accept or renounce an inheritance.

---

## Try it

```bash
git clone https://github.com/<owner>/aftermath.git
cd aftermath
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# validate a rule pack
aftermath validate --pack packs/tr.yaml

# plan a case: an estate with a flat, a car and a surviving spouse
aftermath plan --pack packs/tr.yaml --has has_property --has has_vehicle --has has_eligible_survivors

# the same engine on a different jurisdiction
aftermath plan --pack packs/us.yaml
```

Output:

```
╭──────────────────── Aftermath ─────────────────────╮
│ Türkiye · pack v0.1.0 · 15 steps               │
│ DRAFT PACK — entries are not yet verified.     │
╰────────────────────────────────────────────────╯
Deadlines
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┓
┃ Deadline                     ┃ Day ┃ Inputs ready ┃ Slack ┃ Status ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━┩
│ Renunciation ⚠ irreversible  │  90 │           69 │  +21d │ OK     │
│ Inheritance & gift tax       │ 120 │           34 │  +86d │ OK     │
└──────────────────────────────┴─────┴──────────────┴───────┴────────┘
```

Run the tests — they need no credentials:

```bash
pytest
```

---

## Repository layout

```
packs/            rule packs (data)
src/aftermath/engine/ jurisdiction-agnostic core — no network, no model
src/aftermath/agents/ Strands agents — planner, document, tracker, verifier
docs/             pack schema, architecture, safety
tests/            engine tests, credential-free
```

---

## Status

Early. The engine, the pack format, the Turkey pack v0 and the critical-path
solver work. The Strands agents are scaffolded and land next. See
[`CLAUDE.md`](CLAUDE.md) for the full plan and current checklist.

**The Turkey pack is a draft.** Every legal duration in it must be verified
against a primary source before it is presented as fact.

---

## Honesty about numbers

The 500–900 hour figure comes from US industry and media estimates, not
peer-reviewed research, and is quoted as an estimate throughout.

## License

MIT — see [LICENSE](LICENSE).
