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
