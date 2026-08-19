"""Engine tests.

These run with no network, no model and no AWS credentials. That is the whole
point of the engine/agents split — if these ever need a key, something has
leaked across the boundary.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aftermath.engine import load_pack, solve
from aftermath.engine.graph import CaseGraph, CaseProfile, CycleError
from aftermath.engine.pack import Pack, PackValidationError

PACKS = Path(__file__).resolve().parents[1] / "packs"


# ---------------------------------------------------------------------------
# packs load and are internally consistent
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("pack_file", ["tr.yaml", "us.yaml"])
def test_shipped_packs_are_valid(pack_file: str) -> None:
    pack = load_pack(PACKS / pack_file)
    assert pack.steps
    assert pack.deadlines


def test_verified_claims_require_a_source() -> None:
    raw = {
        "meta": {
            "jurisdiction": "XX",
            "name": "Test",
            "version": "0.0.1",
            "language": "en",
            "last_reviewed": "2026-08-15",
        },
        "artifacts": [{"id": "a", "kind": "document", "name_en": "A"}],
        "steps": [
            {
                "id": "s",
                "name_en": "S",
                "requires": [],
                "produces": ["a"],
                "duration_days": {"max": 1},
                "confidence": "verified",  # no source -> must fail
            }
        ],
    }
    pack = Pack.model_validate(raw)
    with pytest.raises(PackValidationError) as exc:
        pack.validate_consistency()
    assert any("verified but has no source" in p for p in exc.value.problems)


def test_unknown_artifact_reference_is_rejected() -> None:
    raw = {
        "meta": {
            "jurisdiction": "XX",
            "name": "Test",
            "version": "0.0.1",
            "language": "en",
            "last_reviewed": "2026-08-15",
        },
        "artifacts": [{"id": "a", "kind": "document", "name_en": "A"}],
        "steps": [
            {
                "id": "s",
                "name_en": "S",
                "requires": ["ghost"],
                "produces": ["a"],
                "duration_days": {"max": 1},
            }
        ],
    }
    pack = Pack.model_validate(raw)
    with pytest.raises(PackValidationError):
        pack.validate_consistency()


# ---------------------------------------------------------------------------
# the graph
# ---------------------------------------------------------------------------
def test_conditional_steps_are_filtered_by_profile() -> None:
    pack = load_pack(PACKS / "tr.yaml")

    bare = CaseGraph(pack, CaseProfile())
    with_property = CaseGraph(pack, CaseProfile.from_list(["has_property"]))

    assert "transfer_title_deed" not in {s.id for s in bare.steps}
    assert "transfer_title_deed" in {s.id for s in with_property.steps}
    assert len(with_property) > len(bare)


def test_certificate_of_inheritance_precedes_the_bank_queries() -> None:
    pack = load_pack(PACKS / "tr.yaml")
    graph = CaseGraph(pack, CaseProfile())
    order = graph.order
    assert order.index("obtain_inheritance_certificate") < order.index("query_banks")


def test_cycles_are_detected() -> None:
    raw = {
        "meta": {
            "jurisdiction": "XX",
            "name": "Test",
            "version": "0.0.1",
            "language": "en",
            "last_reviewed": "2026-08-15",
        },
        "artifacts": [
            {"id": "a", "kind": "document", "name_en": "A"},
            {"id": "b", "kind": "document", "name_en": "B"},
        ],
        "steps": [
            {
                "id": "s1",
                "name_en": "S1",
                "requires": ["b"],
                "produces": ["a"],
                "duration_days": {"max": 1},
            },
            {
                "id": "s2",
                "name_en": "S2",
                "requires": ["a"],
                "produces": ["b"],
                "duration_days": {"max": 1},
            },
        ],
    }
    pack = Pack.model_validate(raw)
    pack.validate_consistency()
    with pytest.raises(CycleError):
        CaseGraph(pack, CaseProfile())


# ---------------------------------------------------------------------------
# the critical path — the reason this project exists
# ---------------------------------------------------------------------------
def test_renunciation_deadline_is_scheduled_backwards() -> None:
    pack = load_pack(PACKS / "tr.yaml")
    schedule = solve(CaseGraph(pack, CaseProfile()))

    renounce = next(d for d in schedule.deadlines if d.deadline_id == "renounce_inheritance")

    assert renounce.day == 90
    assert renounce.irreversible is True
    # The debt picture depends on a chain of institutional queries, so it cannot
    # possibly be ready on day one. If this ever becomes 0, the graph is broken.
    assert renounce.inputs_ready_day > 30
    assert renounce.slack_days == renounce.day - renounce.inputs_ready_day


def test_upstream_steps_get_a_latest_start_date() -> None:
    pack = load_pack(PACKS / "tr.yaml")
    schedule = solve(CaseGraph(pack, CaseProfile()))

    cert = schedule.steps["obtain_inheritance_certificate"]
    assert cert.latest_start is not None
    assert cert.latest_finish is not None
    # It must start well before the 90-day renunciation deadline.
    assert cert.latest_start < 90


def test_steps_downstream_of_no_deadline_have_no_latest_start() -> None:
    pack = load_pack(PACKS / "tr.yaml")
    schedule = solve(CaseGraph(pack, CaseProfile()))

    # Closing mobile lines is real work but nothing irreversible hangs on it.
    lines = schedule.steps["close_mobile_lines"]
    assert lines.latest_start is None
    assert lines.slack is None


def test_critical_path_is_non_empty_and_ordered() -> None:
    pack = load_pack(PACKS / "tr.yaml")
    schedule = solve(CaseGraph(pack, CaseProfile()))

    path = schedule.critical_path()
    assert path, "expected at least one step with zero or negative slack"
    starts = [s.earliest_start for s in path]
    assert starts == sorted(starts)


def test_engine_generalises_to_another_jurisdiction() -> None:
    """The same solver, a different pack, no code change."""
    pack = load_pack(PACKS / "us.yaml")
    schedule = solve(CaseGraph(pack, CaseProfile()))

    window = next(d for d in schedule.deadlines if d.deadline_id == "creditor_claim_window")
    assert window.inputs_ready_day > 0
    assert schedule.steps["open_probate"].latest_start is not None


# ---------------------------------------------------------------------------
# action deadlines — "file by day 120" is discharged by a step, not by knowing
# ---------------------------------------------------------------------------
def test_action_deadline_pulls_its_own_step_onto_the_backward_pass() -> None:
    """A deadline you satisfy by *doing* something must constrain the doing.

    Before ``satisfied_by`` existed, the filing step had no latest start at all:
    the plan implied the 120-day declaration had no clock of its own, which is
    exactly backwards.
    """
    pack = load_pack(PACKS / "tr.yaml")
    schedule = solve(CaseGraph(pack, CaseProfile()))

    filing = schedule.steps["file_inheritance_tax_declaration"]
    assert filing.latest_start is not None
    assert filing.latest_finish == 120

    report = next(d for d in schedule.deadlines if d.deadline_id == "inheritance_tax_declaration")
    assert report.kind == "action"
    # The reported day is when the filing could actually be completed, not when
    # its inputs merely exist.
    assert report.ready_day == filing.earliest_finish


def test_deadline_with_no_backward_anchor_is_rejected() -> None:
    """A deadline nothing schedules backwards from is a silent no-op."""
    raw = {
        "meta": {
            "jurisdiction": "XX",
            "name": "Test",
            "version": "0.0.1",
            "language": "en",
            "last_reviewed": "2026-08-15",
        },
        "artifacts": [{"id": "a", "kind": "document", "name_en": "A"}],
        "deadlines": [{"id": "d", "name_en": "D", "duration_days": 30}],
        "steps": [
            {
                "id": "s",
                "name_en": "S",
                "requires": [],
                "produces": ["a"],
                "duration_days": {"max": 1},
            }
        ],
    }
    pack = Pack.model_validate(raw)
    with pytest.raises(PackValidationError) as exc:
        pack.validate_consistency()
    assert any("satisfied_by" in p for p in exc.value.problems)


# ---------------------------------------------------------------------------
# mutually exclusive routes to the same artifact
# ---------------------------------------------------------------------------
def test_contested_heirs_swap_the_notary_route_for_the_court() -> None:
    """Two producers of one artifact, and the case decides which one exists."""
    pack = load_pack(PACKS / "tr.yaml")

    ordinary = {s.id for s in CaseGraph(pack, CaseProfile()).steps}
    contested = {s.id for s in CaseGraph(pack, CaseProfile.from_list(["has_contested_heirs"])).steps}

    assert "obtain_inheritance_certificate" in ordinary
    assert "obtain_inheritance_certificate_court" not in ordinary

    assert "obtain_inheritance_certificate" not in contested
    assert "obtain_inheritance_certificate_court" in contested


def test_the_slow_route_puts_the_irreversible_deadline_at_risk() -> None:
    """The scene the whole product exists for.

    An uncontested estate clears the 90-day renunciation window. A contested one
    cannot: the court route alone outruns the deadline, so the family would be
    deciding whether to accept the debts without knowing what they are. Aftermath
    has to say so on day one rather than discover it on day 67.
    """
    pack = load_pack(PACKS / "tr.yaml")

    def renunciation(conditions: list[str]):
        schedule = solve(CaseGraph(pack, CaseProfile.from_list(conditions)))
        return next(d for d in schedule.deadlines if d.deadline_id == "renounce_inheritance")

    ordinary = renunciation([])
    contested = renunciation(["has_contested_heirs"])

    assert ordinary.feasible
    assert not contested.feasible
    assert contested.slack_days < 0
    assert contested.ready_day > contested.day
    # And the schedule surfaces it without anyone asking.
    contested_schedule = solve(CaseGraph(pack, CaseProfile.from_list(["has_contested_heirs"])))
    assert contested_schedule.at_risk


def test_applies_unless_must_name_a_known_condition() -> None:
    raw = {
        "meta": {
            "jurisdiction": "XX",
            "name": "Test",
            "version": "0.0.1",
            "language": "en",
            "last_reviewed": "2026-08-15",
        },
        "artifacts": [{"id": "a", "kind": "document", "name_en": "A"}],
        "steps": [
            {
                "id": "s",
                "name_en": "S",
                "requires": [],
                "produces": ["a"],
                "duration_days": {"max": 1},
                "applies_unless": "has_a_yacht",
            }
        ],
    }
    pack = Pack.model_validate(raw)
    with pytest.raises(PackValidationError) as exc:
        pack.validate_consistency()
    assert any("has_a_yacht" in p for p in exc.value.problems)
