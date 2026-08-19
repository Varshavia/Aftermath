# Safety

Aftermath operates in a legal-adjacent domain, with users who are grieving and
deadlines that cannot be undone. Getting this wrong is not a bad user
experience — it is someone inheriting a debt they meant to refuse.

These five rules are not aspirations. Where they can be enforced in code, they
are, and there is a test.

---

## 1. Aftermath never files or sends anything itself

Every outbound artefact — a petition, a declaration, an email to an institution —
lands in a review queue. A human reads it, edits it, and submits it under their
own name.

This is a design principle, not a limitation. It is also why the human-in-the-loop
interrupt in Strands is a natural fit rather than a bolted-on approval step.

**Never** add an auto-send path, not even behind a flag.

---

## 2. Every rule carries a source

Each entry in a rule pack links to the legislation, the official page, or the
institution's own guidance.

Enforced: `Pack.validate_consistency()` raises if a step or deadline is marked
`confidence: verified` without a `source`. Covered by
`test_verified_claims_require_a_source`.

An entry with no source is not a smaller claim — it is a different kind of claim,
and it is labelled as one.

---

## 3. Confidence is displayed, never hidden

| level | meaning |
|---|---|
| `verified` | backed by a primary source |
| `common_practice` | widely done this way, no single authoritative source |
| `ask_a_professional` | genuinely varies by case — say so |

Showing uncertainty honestly is not a weakness in the product. A tool that admits
what it does not know is one a person can actually rely on for the parts it does.

---

## 4. A coordination tool, not a legal advisor

Aftermath's value is not legal expertise. It is not forgetting institution #14 and
not missing a 120-day filing.

It therefore:

- states the fact, the clock and the consequence, and stops;
- never recommends whether to accept or renounce an inheritance;
- never argues a legal position in a generated document;
- points to a professional where the answer genuinely depends on the case.

Agent system prompts carry this restriction explicitly. See
`src/aftermath/agents/planner.py`.

---

## 5. Sources go stale, so something re-reads them

Legislation changes and official pages move. The verifier agent re-checks the
source behind each rule on a schedule and raises a flag for a human.

It never edits a pack. It never bumps `meta.last_reviewed` — only a person who
actually re-read the sources does that.

---

## Personal data

- Real case data never enters the repository. `cases/` and `out/` are
  gitignored.
- Demo material is anonymised, and anything shown on screen in the demo video is
  fabricated or masked.
- The engine holds no personal data at all: it operates on a case *profile*
  (does the estate include property? a vehicle?), not on identities.

---

## What Aftermath is not

Not a lawyer. Not a filing service. Not a decision-maker. Not a replacement for
professional advice where the case is contested, cross-border, or involves a
business.
