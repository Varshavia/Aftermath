# Rule pack schema

A **rule pack** is a declarative YAML file describing what has to happen after a
death in one jurisdiction. It is *data*. The engine in `src/aftermath/engine/` never
contains jurisdiction-specific logic.

If you find yourself writing `if jurisdiction == "TR"` in `src/`, the schema is
missing a field. Extend the schema instead.

---

## Top-level shape

```yaml
meta:         { ... }   # who this pack is for, version, review status
artifacts:    [ ... ]   # the things that get produced and consumed
deadlines:    [ ... ]   # hard legal clocks
institutions: [ ... ]   # who you have to deal with
steps:        [ ... ]   # the work: each consumes artifacts and produces artifacts
```

---

## The central idea: artifacts, not tasks

Steps do **not** depend on other steps. Steps depend on **artifacts**, and steps
produce artifacts.

```
step A  --produces-->  artifact X  --required by-->  step B
```

This matters because it keeps the graph honest. Two different steps may produce
the same artifact in different jurisdictions (in Turkey a certificate of
inheritance comes from a notary *or* a civil court), and the engine should not
care which.

---

## `meta`

| field | type | notes |
|---|---|---|
| `jurisdiction` | string | ISO country code, e.g. `TR` |
| `name` | string | human name of the jurisdiction |
| `version` | semver | bump on every content change |
| `language` | string | language of the `*_local` fields |
| `last_reviewed` | date | when a human last checked the sources |
| `status` | `draft` \| `reviewed` | `draft` packs render with a banner |

---

## `artifacts`

```yaml
- id: inheritance_certificate
  name_en: Certificate of inheritance
  name_local: Mirasçılık belgesi (veraset ilamı)
  kind: document        # document | information | status
```

`kind: information` is for things that are knowledge rather than paper — e.g.
`debt_picture`. The critical-path solver treats them identically; the UI does not.

---

## `deadlines`

The clocks the engine schedules backwards from.

```yaml
- id: renounce_inheritance
  name_en: Renunciation of inheritance
  name_local: Mirasın reddi
  duration_days: 90
  starts_from: knowledge_of_death     # knowledge_of_death | date_of_death
  severity: critical                  # critical | high | normal
  irreversible: true
  requires_decision_input: [debt_picture]
  consequence_en: >
    If the deadline passes without renunciation, the deceased's debts pass to
    the heirs.
  source: { url: "...", cite: "...", retrieved: 2026-08-15 }
```

`requires_decision_input` is the field that makes the critical path possible: it
says *you cannot sensibly make this decision until these artifacts exist*. The
solver walks back from the deadline through the artifact chain and reports the
latest date each upstream step may start.

`irreversible: true` means missing it cannot be fixed later. These are ranked
first in every view.

---

## `institutions`

```yaml
- id: notary
  name_en: Notary
  name_local: Noter
  channels: [in_person]
  responsiveness_days: { typical: 1, max: 3 }   # used for chasing cadence
```

`responsiveness_days` drives the Tracker agent: an institution is considered
*stalled* once `max` is exceeded with no response.

---

## `steps`

```yaml
- id: obtain_inheritance_certificate
  name_en: Obtain the certificate of inheritance
  name_local: Mirasçılık belgesi (veraset ilamı) alınması
  institution: notary
  requires: [death_registered]
  produces: [inheritance_certificate]
  duration_days: { min: 1, typical: 10, max: 21 }
  cost: { currency: TRY, typical: null }
  confidence: verified
  source: { url: "...", cite: "...", retrieved: 2026-08-15 }
  documents: [petition_inheritance_certificate]
  applies_if: always            # always | has_property | has_vehicle | ...
  notes_local: >
    Free text shown to the user in their own language.
```

### `confidence` — required on every step

| value | meaning | how the UI renders it |
|---|---|---|
| `verified` | backed by a primary source (legislation, official page) | normal |
| `common_practice` | widely done this way, no single authoritative source | amber label |
| `ask_a_professional` | genuinely varies by case | red label + advice to consult |

A step with no `source` **may not** be `verified`. The pack loader enforces this.

### `applies_if`

Conditions are declared, not coded. The engine passes a case profile (does the
estate include property? a vehicle? a business?) and filters steps whose
condition is unmet. Add new conditions to the enum in `engine/pack.py`.

---

## Rules for pack authors

1. **No claim without a source.** A step with no `source` is `draft` and must be
   labelled as such in the UI.
2. **Durations are ranges, never single numbers.** `max` is what the critical
   path uses — plan for the bad case.
3. **Write `notes_local` for a grieving person**, not for a lawyer. Short
   sentences. No jargon without explanation.
4. **Never write advice.** State the fact, the clock and the consequence. The
   decision belongs to the human.
5. **`last_reviewed` is a promise.** Bump it only when someone actually re-read
   the sources.
