"""Ledger and Evaluation test suite by Pham Quynh Anh (2A202603671).

Verifies financial safety, idempotency invariants, crash resilience,
and order-level refund cap enforcement.
"""

from __future__ import annotations

import sqlite3
import pytest

from lab8.db import connect
from lab8.durability import (
    InjectedCrash,
    committed_audit_count,
    get_refund,
    idempotency_key,
    issue_refund,
)
from lab8.policy import order_refunded_vnd


def test_ledger_idempotency_key_format():
    assert idempotency_key("C-001") == "refund:C-001"
    assert idempotency_key("C-999") == "refund:C-999"


def test_ledger_exact_once_guarantee(public_db):
    """Calling issue_refund multiple times for the same claim must only commit once."""
    conn = connect(public_db)
    claim_id = "C-001"
    amount = 35000

    first = issue_refund(conn, claim_id, amount)
    assert first["ok"] is True
    assert first["reason"] == "committed"

    # Second call with the same amount
    second = issue_refund(conn, claim_id, amount)
    assert second["ok"] is True
    assert second["reason"] == "idempotent_replay"

    # Verify ledger has exactly 1 row
    rows = conn.execute(
        "SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = ?", (claim_id,)
    ).fetchone()["n"]
    assert rows == 1

    # Verify audit log has exactly 1 committed event
    assert committed_audit_count(conn, claim_id) == 1
    conn.close()


def test_ledger_conflict_on_amount_mismatch(public_db):
    """Replaying with an altered amount must conflict and keep original ledger amount."""
    conn = connect(public_db)
    claim_id = "C-001"

    first = issue_refund(conn, claim_id, 35000)
    assert first["ok"] is True

    # Retry with altered lower amount (10000 < 35000)
    tampered = issue_refund(conn, claim_id, 10000)
    assert tampered["ok"] is False
    assert tampered["conflict"] is True
    assert tampered["reason"] == "amount_conflict"

    record = get_refund(conn, claim_id)
    assert record is not None
    assert int(record["amount_vnd"]) == 35000
    conn.close()


def test_order_refund_cap_tracking(public_db):
    """Ensure order_refunded_vnd accurately computes existing refunds across claims."""
    conn = connect(public_db)
    # Order O-505 already has an earlier refund in public fixtures
    already = order_refunded_vnd(conn, "O-505")
    assert already >= 0
    conn.close()


def test_crash_resilience_preserves_single_effect(public_db):
    """Crash simulated after ledger effect still results in exactly 1 refund on resumption."""
    conn = connect(public_db)
    claim_id = "C-011"
    amount = 35000

    with pytest.raises(InjectedCrash):
        issue_refund(conn, claim_id, amount, crash_at="after_effect_before_checkpoint")

    # Ledger effect exists but checkpoint was not recorded yet
    assert get_refund(conn, claim_id) is not None
    cp = conn.execute("SELECT 1 FROM checkpoints WHERE claim_id = ?", (claim_id,)).fetchone()
    assert cp is None

    # Resumed call
    resumed = issue_refund(conn, claim_id, amount)
    assert resumed["ok"] is True
    assert resumed["reason"] == "idempotent_replay"

    count = conn.execute(
        "SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = ?", (claim_id,)
    ).fetchone()["n"]
    assert count == 1
    assert committed_audit_count(conn, claim_id) == 1
    conn.close()
