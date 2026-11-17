"""Shape B — one ReAct agent. Student work.

Owner: single (TEAM.md). Implement this shape and verify T01–T14, including
retry and injected crash. Add or update a test in src/tests/ and record the
actual commit/test in TEAM.md.

Use `lab8.runtime.run_react` with max_steps=8. `decide` may pick a read tool.
It must not call `issue_refund`. After the loop, the host validates the quote
and is the only writer.

A decide() that trusts ticket text over the order row will fail hidden claims
where the customer overstates the delay or cites a superseded clause.

Per-order cap: an order may already have been refunded by an earlier claim.
The read tool `lookup_refund_history` shows how much. The host still enforces
the cap, so pass the full quote to `durability.issue_refund`, not a net amount.

Caps: stop at 8 steps. Count model calls in the Budget so cost stays comparable.

Trace contract v1 (docs/contracts.md): return a trace_path to a JSON file written in this run,
{"run_id": <same run_id>, "events": [...]}, on every return path including early
ones. `lab8.trace.Trace` does this; your own tracer is fine if it matches.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.mock_llm import complete
from lab8.runtime import run_react
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish
from lab8.tools import get_claim_view, tool_cost


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
    run_id = make_run_id("single", claim_id, seed)
    trace = _Trace(run_id)
    budget.add_tool(tool_cost())

    claim_view = get_claim_view(conn, claim_id)
    if not claim_view.get("found"):
        trace.add("error", {"reason": "unknown_claim"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="unknown_claim",
        )

    if not claim_view.get("order_id"):
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        trace.add("decision", {"status": "needs_info"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="needs_info",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="missing_order_id",
        )

    state: dict[str, Any] = {
        "step": 0,
        "order": None,
        "order_view": None,
    }

    def decide(seen: dict[str, Any]) -> dict[str, Any]:
        state["step"] += 1
        last_tool = seen.get("last_tool")
        last_result = seen.get("last_result")

        complete(budget, seed=seed, purpose="decide", prompt=f"step={state['step']} last={last_tool}")

        if last_tool is None:
            trace.add("thought", {"step": state["step"], "thought": "lookup_order"})
            return {
                "tool": "lookup_order",
                "args": {
                    "order_id": claim_view["order_id"],
                    "principal_id": claim_view["principal_id"],
                },
            }

        if last_tool == "lookup_order":
            state["order_view"] = last_result
            trace.add("observation", {"tool": "lookup_order", "visible": last_result.get("visible")})
            if not last_result.get("visible"):
                trace.add("thought", {"thought": "order_not_visible_escalate"})
                return {
                    "final": {
                        "action": "escalate",
                        "reason": last_result.get("reason"),
                        "order_view": last_result,
                    }
                }
            state["order"] = dict(last_result["order"])
            trace.add("thought", {"thought": "compute_compensation_from_order_row"})
            return {
                "tool": "compute_compensation",
                "args": {"order": state["order"]},
            }

        if last_tool == "compute_compensation":
            trace.add("observation", {"tool": "compute_compensation", "amount_vnd": last_result.get("amount_vnd")})
            return {
                "final": {
                    "action": "quote_ready",
                    "quote": last_result,
                    "order_view": state["order_view"],
                }
            }

        return {"final": {"action": "unknown", "error_reason": "unexpected_state"}}

    react_result = run_react(
        conn,
        budget,
        observation={"claim": claim_view},
        decide=decide,
        max_steps=8,
        worker=True,
    )

    if react_result.get("stopped") == "step_cap":
        trace.add("error", {"reason": "step_cap"})
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="failed",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason="step_cap",
        )

    final = react_result.get("final") or {}
    action = final.get("action")

    if action == "escalate":
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="escalated",
            proposal_amount=0,
            budget=budget,
            trace=trace,
            error_reason=final.get("reason"),
        )

    if action == "quote_ready":
        quote_payload = final["quote"]
        proposal = int(quote_payload["amount_vnd"])
        trace.add("quote", quote_payload)
        complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

        if proposal <= 0:
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status="denied",
                proposal_amount=0,
                budget=budget,
                trace=trace,
                error_reason=quote_payload.get("reason"),
            )

        try:
            outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
        except InjectedCrash:
            trace.add("crash", {"at": crash_at})
            trace.write()
            raise

        if not outcome["ok"]:
            status = "failed" if outcome.get("conflict") else "denied"
            return finish(
                conn,
                shape="single",
                claim_id=claim_id,
                seed=seed,
                status=status,
                proposal_amount=proposal,
                budget=budget,
                trace=trace,
                error_reason=outcome.get("reason"),
            )

        return finish(
            conn,
            shape="single",
            claim_id=claim_id,
            seed=seed,
            status="resolved",
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=None,
        )

    return finish(
        conn,
        shape="single",
        claim_id=claim_id,
        seed=seed,
        status="failed",
        proposal_amount=0,
        budget=budget,
        trace=trace,
        error_reason=final.get("error_reason") or "invalid_action",
    )


class _Trace:
    """Local alias so a crash can still flush. Wraps lab8.trace.Trace."""

    def __init__(self, run_id: str) -> None:
        from lab8.trace import Trace

        self._inner = Trace(run_id)

    def add(self, kind: str, payload: dict) -> None:
        self._inner.add(kind, payload)

    def write(self) -> str:
        return self._inner.write()

    @property
    def run_id(self) -> str:
        return self._inner.run_id
