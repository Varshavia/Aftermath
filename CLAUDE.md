# CLAUDE.md — Aftermath project context

> This file is the single source of truth for any AI agent (Claude Code, Cowork,
> or a subagent) working on this repository. Read it fully before doing anything.
> Keep it updated: if a decision in here changes, change it here first.

---

## 0. How to work with this team

- The two builders are Turkish. **Reply to them in Turkish**, even though this
  file, the code, the README and all commit messages are in English.
- English is the project's public language because the hackathon judges are
  international and the repository is part of the submission.
- Be direct about risk. This team is on a hard deadline; a warning in week 2 is
  worth more than a polished excuse in week 4.

---

## 1. What this project is

**Aftermath** is an AI agent that manages the administrative aftermath of a death.

> Elevator pitch (as submitted to Devpost):
> *Losing someone starts 40+ institutions and months of paperwork. Aftermath maps the
> path, drafts every document, and watches every deadline — so the family can
> grieve instead of file.*

When a person dies, the surviving family is handed a months-long bureaucratic
project: the certificate of inheritance, bank accounts, title deeds, the social
security office, vehicle transfer, insurance and private pensions, utility
accounts, phone lines, subscriptions, tax filings. Dozens of institutions, each
with its own required documents, its own order, and its own clock. US industry
estimates put settling an estate at roughly **500–900 hours**. People do this
while grieving.

Aftermath builds the institution map for a specific case, computes the order in which
things must happen, drafts the documents, tracks which institutions have
responded, chases the ones that have not, and warns about deadlines before they
pass.

**The name.** The funeral takes a day. The aftermath takes a year. The product is
named after the part nobody prepares you for — and the part nobody has built for.

---

## 2. Hard constraints — do not violate

| Constraint | Value |
|---|---|
| Hackathon | Agents for Humans (Devpost, sponsored by AWS) |
| Track | **Everyday Agents** |
| Submission deadline | **14 September 2026, 17:00 PDT** |
| Code freeze (self-imposed) | **7 September 2026** |
| Required SDK | **Strands Agents** (mandatory — the project must be built with it) |
| AgentCore | Amazon Bedrock AgentCore — optional but scored favourably |
| License | **MIT** (required: MIT or Apache 2.0) |
| Repository | Must be **public** |
| Demo video | ≤ 5 minutes, public on YouTube/Vimeo |
| Also required | README, architecture diagram, AWS Builder ID |
| Originality rule | The project must be **newly built** between 10 Aug and 14 Sep 2026 |
| Bonus | A build post on builder.aws.com tagged `#AgentsforHumans` (+0.6) |

Judging criteria, **equally weighted**: Technical Implementation, Design,
Potential Impact, Creativity & Originality, Presentation.

---

## 3. Why this idea (the reasoning — do not relitigate it)

This was chosen after comparing ~20 alternatives across all three tracks. The
reasoning that produced it:

1. **Everyday is the most crowded track**, so a task-level agent loses. The rule
   we adopted: *losing Everyday projects automate a task; winning Everyday
   projects manage a period of life.* Bill paying, meal planning and calendar
   agents will arrive by the hundred. Nobody is building this.
2. **The agent must talk to other parties, not just the user.** An agent that
   only answers its owner is an assistant. One that chases institutions over
   months is an agent.
3. **Precedent.** The previous AWS AI Agent Global Hackathon was won by
   EcoLafaek — a waste-management project for Timor-Leste. Not the flashiest
   tech; the one grounded in a real place with real people. Locality is depth,
   not narrowness.
4. **Attrition is the real competitor.** That hackathon had 9,467 registrants and
   613 submissions — 94% never submitted. This one has ~1,750 registrants, so
   expect ~115 real projects. What eliminates teams is not weak engineering, it
   is not finishing.

---

## 4. The core architectural decision: jurisdiction is data, not code

Every country's procedure differs. The resolution:

**The agent's intelligence is not "knowing Turkish inheritance law."** It is
ordering institutions by dependency, computing the critical path, tracking
deadlines, chasing non-responders, escalating blockages. That engine is identical
everywhere. Only the rulebook changes.

```
CORE ENGINE  (jurisdiction-agnostic, pure Python, no AWS calls)
   dependency graph · critical path · artifact store
   deadline tracking · institution chasing · escalation · status table
        ▲
        │ reads
        │
RULE PACK  (declarative YAML — data, not code)
   packs/tr.yaml   → Turkey: deep, sourced, verified      [PRIMARY]
   packs/us.yaml   → USA: partial, proves the engine generalises
```

The sentence we tell the judges: *"We did not write an app for one country. We
wrote an engine and a rulebook format."*

**Demo strategy:** Turkey deep and verified; USA shallow and illustrative. ~90%
of the video runs on Turkey, then the last 30 seconds runs the same engine on a
US case to prove portability. Depth *and* generality.

Do not hardcode any jurisdiction-specific rule in `src/`. If you find yourself
writing `if jurisdiction == "TR"`, the pack schema is missing a field — extend
the schema instead.

---

## 5. The heart of the product: the critical-path race

This is what separates Aftermath from a checklist app, and it is the single strongest
scene in the demo video.

Turkey has two clocks that contradict each other:

- **Renunciation of inheritance — 3 months** (Turkish Civil Code art. 606). Miss
  it and the deceased's debts pass to the heirs. Irreversible.
- **Inheritance and gift tax declaration — 4 months.**

So the right to refuse expires *before* the declaration is even due. This
conflict is a known trap.

The deeper problem: to decide whether to renounce, you must know whether there
are debts. To learn that, you must query banks and public bodies. To do that, you
need the certificate of inheritance — which itself takes weeks to obtain.

```
DAY 0   death
  │
  ├─ certificate of inheritance (notary / civil court)     ~1-3 weeks
  │      │
  │      ├─ bank queries (each bank separately)            ~2-4 weeks
  │      ├─ credit bureau risk report
  │      ├─ tax & social security debt query
  │      │
  │      └─▶ DEBT PICTURE COMPLETE
  │
  └──────────────────────────────────────▶ DAY 90: RENOUNCE OR NOT  ⚠ irreversible

Aftermath computes: "to decide on day 90, the certificate must be in hand by day 20."
```

Aftermath schedules **backwards** from irreversible deadlines. That is the algorithm
in `engine/critical_path.py` and it is the reason this cannot be a to-do list.

---

## 6. Safety rules — non-negotiable, and stated in the README

This is a legal-adjacent domain. Being wrong hurts people. Five rules:

1. **The agent never files or sends anything itself.** It prepares; a human
   reviews and submits. This is a design principle, not a limitation — present it
   as such. It also makes Strands' human-in-the-loop interrupt a natural fit.
2. **Every rule carries a source.** Each pack entry links to `mevzuat.gov.tr`,
   e-Devlet, or the institution's own page. No citation, no claim.
3. **Confidence is displayed**, never hidden: `verified` (official source) /
   `common_practice` / `ask_a_professional`. Showing uncertainty honestly
   increases judge trust.
4. **Positioning: a coordination tool, not a legal advisor.** The value is not
   legal expertise — it is not forgetting institution #14 and not missing the
   4-month filing.
5. **A Verifier Agent re-checks sources periodically** and flags rules whose
   source has changed or gone stale. This answers "but the law changes" before it
   is asked, and it is genuine agent work.

Never let the system produce output that reads as legal advice. Never emit a
recommendation on renunciation — present the facts, the clock and the
consequence, and let the human decide.

---

## 7. Repository layout

```
aftermath/
├── CLAUDE.md              ← this file
├── README.md              ← public-facing, part of the submission
├── LICENSE                ← MIT (required)
├── pyproject.toml
├── .env.example
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PACK_SCHEMA.md     ← the rule-pack format spec
│   └── SAFETY.md
├── packs/
│   ├── tr.yaml            ← Turkey rule pack (primary)
│   └── us.yaml            ← USA rule pack (partial)
├── src/aftermath/
│   ├── engine/            ← jurisdiction-agnostic core. NO AWS, NO LLM calls.
│   │   ├── pack.py            load + validate rule packs
│   │   ├── graph.py           artifact dependency graph
│   │   └── critical_path.py   backward scheduling from hard deadlines
│   ├── agents/            ← Strands agents. All LLM work lives here.
│   │   ├── planner.py         builds the case plan from a pack
│   │   ├── document.py        drafts petitions / declarations
│   │   ├── tracker.py         monitors institution responses, chases, escalates
│   │   └── verifier.py        re-checks sources, flags stale rules
│   └── cli.py             ← demo entry point
└── tests/
```

**The engine/agents boundary is important.** The engine must run with no network,
no API key and no model — that is what makes it testable and what makes the
"engine + pack" claim credible. Anything that needs a model goes in `agents/`.

---

## 8. Roles

| | Owner A — Engine & Agents | Owner B — Rule Pack & Product |
|---|---|---|
| | Core engine: dependency graph, critical path | Researching and **sourcing** the TR pack (the longest single task) |
| | Strands agents and orchestration | Document / petition templates |
| | AgentCore deploy + observability | Status dashboard UI |
| | Pack schema design | Partial US pack |
| | Institution-chasing / messaging layer | README + architecture diagram |

Both: the demo video in the final week. Do not leave it to one person.

Work in separate files. There is no time for merge conflicts.

---

## 9. Four-week plan

| Dates | Goal |
|---|---|
| **15–17 Aug** (week 0) | Devpost draft created. AWS Builder IDs. **$50 credit request** (deadline 11 Sep, stock is limited). Public repo + MIT. A trivial Strands agent deployed end-to-end so the pipeline is proven on day 3. Institution list expanded to 41 rows with source links. |
| **18–24 Aug** (week 1) | Pack schema locked. `tr.yaml` v1 with ≥20 sourced institutions. Engine: dependency graph + critical path. **Milestone: enter a case, get the correct order and the day-90 warning.** |
| **25–31 Aug** (week 2) | Strands agents live: Planner, Document, Tracker. Document generation. Human-in-the-loop approval. AgentCore Memory for months-long case memory. **Milestone: the agent plans a case end to end and produces the first documents.** |
| **1–7 Sep** (week 3) | Status dashboard (41 institutions / done / stalled / expiring). Chasing and escalation. Verifier agent. Partial `us.yaml`. Observability on, traces presentable. Architecture diagram. **Code freezes 7 Sep.** |
| **8–12 Sep** (week 4) | No new features. README. **Two full days on the video.** builder.aws.com post with `#AgentsforHumans`. |
| **13 Sep** | Submit. Leave 14 Sep empty as buffer — Devpost slows down on the last day. |

---

## 10. Demo video structure (5 min)

| | |
|---|---|
| 0:00 | Cold open, no music: *"The funeral takes a day. The aftermath takes a year."* |
| 0:25 | The problem: 40+ institutions, months of paperwork, 500–900 hours, done while grieving. |
| 1:00 | **The critical-path scene.** The 3-month / 4-month conflict. *"You had 3 months to refuse your father's debts. You are on day 67. Aftermath told you on day 12."* |
| 2:00 | The agent working: case in → plan built → documents drafted → human approves → institutions tracked. |
| 3:15 | Status dashboard. Source links and confidence labels visible. |
| 4:00 | Same engine, `us.yaml`, a US case. *"The pack changed. The code did not."* |
| 4:30 | Architecture diagram, AgentCore traces, closing line. |

---

## 11. Scope discipline — the biggest risk

The temptation is to cover all 41 institutions. **Do not.** Target ~15
institutions modelled deeply and verified, the rest declared but shallow. Judges
do not count coverage; they judge whether the agent genuinely does work on its
own.

Explicitly out of scope: mobile app, user accounts / multi-tenancy, real
integrations with banks or government APIs, payment, i18n beyond TR/EN,
any actual automated filing.

When in doubt, cut features and deepen the demo.

---

## 12. Honesty rules for claims

- The 500–900 hour figure comes from **US industry and media estimates**, not
  peer-reviewed research. Always phrase it as *"industry estimates put estate
  settlement at 500–900 hours"* — never as a hard fact.
- Better: **measure our own case.** Run one real (or faithfully reconstructed)
  case end to end and report the true numbers: institutions touched, documents
  required, hard deadlines. A number we measured beats a borrowed statistic.
- Every legal duration in `packs/tr.yaml` is **draft until sourced**. The current
  file is v0 and its entries must each be checked against a primary source before
  they appear in the demo.

---

## 13. Current status

- [x] Idea chosen, named, positioned
- [x] Architecture decided (engine + rule packs)
- [x] Critical-path concept specified
- [x] Repo scaffold, working engine, tests, TR pack v0
- [x] Devpost registration; track declared (Everyday Agents)
- [x] $50 AWS credits requested (19 Aug)
- [x] Action vs decision deadlines (`satisfied_by`) — the 120-day filing now
      schedules backwards from its own step
- [x] Mutually exclusive routes (`applies_unless`) — notary vs civil court, and
      the contested case now renders AT RISK. **This is the demo scene.**
- [ ] Devpost draft submission created
- [ ] AWS Builder IDs
- [ ] Bedrock model access enabled + IAM key for the build session
- [ ] Pack schema reviewed by both owners
- [ ] `tr.yaml` expanded to 20+ sourced entries
- [ ] Strands agents implemented — **highest risk, still at zero**
- [ ] AgentCore deployment
- [ ] Dashboard
- [ ] Architecture diagram
- [ ] Video
- [ ] Submitted

Update this checklist as things land. It is how a fresh session knows where the
project stands.
