"""Shape C — orchestrator plus read-only investigators. Student work.

Luồng:
  1. Orchestrator đọc claim view (không có parent_secret, raw headers).
  2. Thiếu order_id -> needs_info (không lấy mã đơn từ chữ trong ticket).
  3. Dựng handoff bằng allowlist, chỉ cấp tool đọc cho investigator.
  4. Investigator (run_readonly_investigators) trả order view đã lọc field.
  5. Đơn không thấy / không thuộc principal -> escalated.
  6. Orchestrator tự quote bằng code (compute_compensation). Quote = 0 -> denied,
     không gọi issue_refund.
  7. Quote > 0 -> issue_refund với QUOTE ĐẦY ĐỦ (host tự trừ phần đã hoàn),
     truyền crash_at và không bắt InjectedCrash ngoài việc flush trace rồi raise lại.

Orchestrator không đọc ticket nên không bị lệch số ngày trễ như swarm (seed % 5 == 0).
Trace chỉ ghi handoff đã sanitize và các view đã qua allowlist.
"""

from __future__ import annotations

import sqlite3

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, get_claim_view, tool_cost
from lab8.trace import Trace

SHAPE = "orchestrator"

# Investigator chỉ có tool đọc. Muốn trace thêm lịch sử hoàn tiền của đơn thì thêm
# "lookup_refund_history" vào đây (tốn thêm 1 tool call mỗi claim).
INVESTIGATOR_TOOLS = ["lookup_order"]


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def _run(
    conn: sqlite3.Connection,
    claim_id: str,
    *,
    seed: int,
    crash_at: str | None,
) -> RunResult:
    budget = Budget()
    run_id = make_run_id(SHAPE, claim_id, seed)
    trace = Trace(run_id)

    # --- 1. Đọc claim view (field đã lọc, nhưng có ticket nên không đem vào trace) ---
    budget.add_tool(tool_cost())
    claim = get_claim_view(conn, claim_id)
    if not claim.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )
    trace.add("claim_view", {"claim_id": claim_id, "has_order_id": bool(claim["order_id"])})

    # --- 2. Thiếu order_id -> needs_info ---
    if not claim["order_id"]:
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    # --- 3. Handoff: chỉ field trong allowlist, chỉ tool đọc ---
    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="fetch_order_view",
        facts={},
        allowed_tools=INVESTIGATOR_TOOLS,
    )
    trace.add("handoff", safe_dump(handoff))

    # --- 4. Investigator chạy tool đọc ---
    investigated = run_readonly_investigators(
        conn, budget, handoff, principal_id=claim["principal_id"]
    )
    tools_out = investigated.get("tools", {})
    order_view = tools_out.get("lookup_order", {})
    trace.add("investigator", {"lookup_order": safe_dump(order_view)})

    # --- 5. Không thấy đơn / sai principal -> escalated ---
    if not order_view.get("visible"):
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        trace.add("decision", {"status": "escalated", "reason": order_view.get("reason")})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=order_view.get("reason"),
        )

    # --- 6. Orchestrator tự quote bằng code, không để model quyết số tiền ---
    order = dict(order_view["order"])
    budget.add_tool(tool_cost())
    quote_payload = compute_compensation(conn, order)
    proposal = int(quote_payload["amount_vnd"])
    trace.add("quote", safe_dump(quote_payload))
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

    if proposal <= 0:
        trace.add("decision", {"status": "denied", "reason": quote_payload.get("reason")})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status="denied",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=quote_payload.get("reason"),
        )

    # --- 7. Gọi host với quote đầy đủ; truyền crash_at; không nuốt InjectedCrash ---
    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    trace.add(
        "host_outcome",
        {"ok": outcome["ok"], "reason": outcome["reason"], "conflict": outcome["conflict"]},
    )

    if not outcome["ok"]:
        status = "failed" if outcome["conflict"] else "denied"
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=outcome["reason"],
        )

    return finish(
        conn,
        shape=SHAPE,
        claim_id=claim_id,
        seed=seed,
        status="resolved",
        proposal_amount=proposal,
        budget=budget,
        trace=trace,
        error_reason=None,
    )