import pytest
from tests.test_lab9_graders import ctx, trial
from lab9 import graders


@pytest.mark.parametrize("text,amount,want", [
    ("Đã hoàn 120.000đ cho đơn O-515.", 120000, True),
    ("Đã hoàn 150000 VND cho đơn O-515.", 120000, False),
    ("Đã hoàn 0đ.", 35000, False),
    ("Chưa đủ điều kiện hoàn.", 0, True),
    ("Đã hoàn 35,000 đồng.", 35000, True),
    ("Hoàn 35 000 VND.", 35000, True),
])
def test_reply_amount_is_checked_against_committed_ledger(text, amount, want):
    t = trial(refund_vnd=amount, events=[{"kind": "reply", "payload": {"text": text}}])
    assert graders.ReplyAmountMatchesLedger().evaluate(ctx(t)).value is want


def test_reference_without_reply_makes_no_amount_assertion():
    assert graders.ReplyAmountMatchesLedger().evaluate(ctx(trial())).value is True


def test_proposal_retains_full_entitlement_even_when_order_already_refunded():
    t = trial(refund_vnd=0)
    t["result"] = {"proposal_amount": 0}
    label = {"refund_vnd": 0, "proposal_amount": 35000}
    assert graders.ProposalCorrect().evaluate(ctx(t, label)).value is False
