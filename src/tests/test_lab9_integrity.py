import copy
import pytest
from lab9.gate import integrity_check

SPEC = {"eval_set_version": "v2", "metrics": [{"id": "pass_rate", "kind": "capability",
        "blocking": True, "threshold": {"min": .8, "no_significant_drop": True}}],
        "slices": [{"name": "money", "metric": "pass_rate", "min": .8, "blocking": True}]}


def report():
    return {"manifest": {"eval_set_sha": "x", "items": 2, "seeds": [11, 22]},
            "rows": [{"item_id": item, "seed": seed, "slices": ["money"], "pass_rate": True, "cost": 1.}
                     for item in ("a", "b") for seed in (11, 22)],
            "metrics": {"pass_rate": 1.}, "evaluator_failures": []}


@pytest.mark.parametrize("attack", ["nan", "duplicate", "drop", "seeds", "grader", "missing", "slice", "cost"])
def test_corrupted_evidence_is_rejected(attack):
    base = report()
    pr = copy.deepcopy(base)
    if attack == "nan": pr["metrics"]["pass_rate"] = float("nan")
    if attack == "duplicate": pr["rows"][0] = copy.deepcopy(pr["rows"][1])
    if attack == "drop": pr["rows"].pop()
    if attack == "seeds": pr["manifest"]["seeds"] = [11]
    if attack == "grader": pr["evaluator_failures"] = ["crashed"]
    if attack == "missing": pr["rows"][0]["pass_rate"] = None
    if attack == "slice": pr["rows"][0]["slices"] = []
    if attack == "cost": pr["rows"][0]["cost"] = float("inf")
    assert integrity_check(pr, base, SPEC)


@pytest.mark.parametrize("attack", ["min", "remove_metric", "blocking", "ci", "slice"])
def test_same_version_cannot_weaken_gate(attack):
    loose = copy.deepcopy(SPEC)
    if attack == "min": loose["metrics"][0]["threshold"]["min"] = .5
    if attack == "remove_metric": loose["metrics"] = []
    if attack == "blocking": loose["metrics"][0]["blocking"] = False
    if attack == "ci": loose["metrics"][0]["threshold"].pop("no_significant_drop")
    if attack == "slice": loose["slices"] = []
    assert integrity_check(report(), report(), loose, SPEC)


def test_honest_report_and_unchanged_spec_pass():
    assert integrity_check(report(), report(), SPEC, SPEC) == []


def test_safety_aggregate_cannot_hide_a_bad_row():
    spec = copy.deepcopy(SPEC)
    spec["metrics"].append({"id": "approval_bypass", "kind": "safety", "level": "trajectory", "threshold": {"max": 0}})
    base = report()
    base["metrics"]["approval_bypass"] = 0
    for row in base["rows"]: row["approval_bypass"] = False
    pr = copy.deepcopy(base)
    pr["rows"][0]["approval_bypass"] = True
    assert integrity_check(pr, base, spec)


@pytest.mark.parametrize("field,value", [("llm", "OtherModel"), ("metric_spec_version", "99")])
def test_incompatible_manifest_is_not_comparable(field, value):
    base = report()
    base["manifest"].update(llm="MockLLM", metric_spec_version="2.0")
    pr = copy.deepcopy(base)
    pr["manifest"][field] = value
    assert integrity_check(pr, base, SPEC)


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_thresholds_must_be_finite(value):
    spec = copy.deepcopy(SPEC)
    spec["metrics"][0]["threshold"]["min"] = value
    assert integrity_check(report(), report(), spec, SPEC)
