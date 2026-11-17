"""Integration checks for the deterministic workflow's host boundary."""

from __future__ import annotations

import json
from pathlib import Path

from lab8.db import connect
from lab8.shapes.workflow import run_claim


def test_unknown_claim_fails_with_fresh_safe_trace(public_db):
    result = run_claim("C-UNKNOWN", seed=11, store_path=str(public_db))
    conn = connect(public_db)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM refund_ledger WHERE claim_id = ?", ("C-UNKNOWN",)
        ).fetchone()[0]
    finally:
        conn.close()

    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert result.status == "failed"
    assert result.error_reason == "unknown_claim"
    assert result.claim_id == "C-UNKNOWN"
    assert result.run_id == trace["run_id"]
    assert isinstance(trace["events"], list)
    assert count == 0


def test_workflow_uses_full_quote_while_host_caps_order_refund(public_db):
    result = run_claim("C-014", seed=55, store_path=str(public_db))
    conn = connect(public_db)
    try:
        row = conn.execute(
            "SELECT amount_vnd FROM refund_ledger WHERE claim_id = ?", ("C-014",)
        ).fetchone()
    finally:
        conn.close()

    assert result.status == "resolved"
    assert result.proposal_amount == 150000
    assert row["amount_vnd"] == 120000
    assert result.committed_audit_count == 1


def test_workflow_trace_never_copies_raw_claim_or_order(public_db):
    result = run_claim("C-010", seed=11, store_path=str(public_db))
    body = Path(result.trace_path).read_text(encoding="utf-8")

    assert result.status == "resolved"
    for private_value in (
        "CANARY_SECRET_PARENT_C-010", "Bearer", "0901000107",
        "CANARY_INTERNAL_O107", "12 Le Loi Q1",
    ):
        assert private_value not in body
