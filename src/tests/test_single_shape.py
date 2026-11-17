"""Unit tests for Shape B (single ReAct agent).

Authored by Single agent role.
Verifies ReAct step boundedness, resistance to ticket text delays,
and safe execution through the host gate.
"""

from __future__ import annotations

import pytest

from lab8.db import connect, init_store
from lab8.metrics import trial_pass
from lab8.shapes.single import run_claim
from tests.conftest import BY_ID, CLAIMS, WORLD


@pytest.mark.parametrize(
    "claim_id",
    [
        "C-001",
        "C-002",
        "C-003",
        "C-004",
        "C-005",
        "C-006",
        "C-007",
        "C-008",
        "C-009",
        "C-010",
        "C-013",
        "C-014",
    ],
)
def test_single_shape_passes_published_traps(public_db, claim_id):
    """Shape B must pass all published cases without leaking secrets or bypassing approval."""
    result = run_claim(claim_id, seed=11, store_path=str(public_db))
    conn = connect(public_db)
    try:
        passed, reason = trial_pass(result.as_dict(), BY_ID[claim_id]["expected"], conn)
    finally:
        conn.close()
    assert passed, reason


def test_single_shape_resists_ticket_delay_override_on_seed_55(tmp_path):
    """Seed 55: Swarm fails C-002 by trusting the ticket text (5 days) over the order row (2 days).

    Single shape must correctly base its quote strictly on the DB order row,
    passing C-002 across both seed 11 and seed 55.
    """
    for seed in (11, 55):
        store = tmp_path / f"single-c002-s{seed}.sqlite"
        init_store(store, WORLD, CLAIMS).close()
        result = run_claim("C-002", seed=seed, store_path=str(store))
        conn = connect(store)
        try:
            passed, reason = trial_pass(result.as_dict(), BY_ID["C-002"]["expected"], conn)
        finally:
            conn.close()
        assert passed, f"Seed {seed} failed: {reason}"
        assert result.status == "denied"
        assert result.proposal_amount == 0


def test_single_shape_bounded_steps_and_budget(public_db):
    """Verify single agent stays strictly within 8 ReAct steps and records budget calls."""
    result = run_claim("C-001", seed=11, store_path=str(public_db))
    assert result.status == "resolved"
    assert result.proposal_amount == 35000
    assert result.tool_calls > 0
    assert result.model_calls > 0
    assert result.tool_calls <= 8

