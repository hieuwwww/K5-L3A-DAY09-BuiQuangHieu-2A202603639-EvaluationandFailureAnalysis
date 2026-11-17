"""The public regression trace must identify the first corrupted DB fact."""

from lab9.trace_case import investigate
from lab8.shapes import SHAPES
import pytest


@pytest.fixture(autouse=True)
def restore_shape_registry():
    original = dict(SHAPES)
    yield
    SHAPES.clear()
    SHAPES.update(original)


def test_ticket_override_is_first_bad_step_and_fixed_restores_db_fact():
    bad = investigate("seeded_regression", "C-002", 11)["trial"]
    good = investigate("fixed", "C-002", 11)["trial"]
    assert not bad["lab8_pass"]
    assert bad["events"][0]["kind"] == "handoff"
    assert bad["events"][1]["kind"] == "investigator"
    assert bad["events"][2] == {"kind": "model_override", "payload": {"delay_days": 5}}
    assert bad["snapshot"]["refund_vnd"] == 20000
    assert good["lab8_pass"]
    assert good["snapshot"]["refund_vnd"] == 0
    assert not any(e["kind"] == "model_override" for e in good["events"])
