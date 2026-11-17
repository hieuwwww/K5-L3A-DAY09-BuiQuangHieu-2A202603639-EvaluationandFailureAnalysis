"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = {m["id"] for m in spec.get("metrics", []) if m.get("level") != "system"}
    # Only metrics present on individual rows are graded; pass-k is aggregate-only.
    aggregate_only = {"pass_5"} | {m for m in graded if m.startswith(("pass_at_", "pass_hat_"))}
    graded -= aggregate_only
    inventories = []
    for label, report in (("PR", pr), ("baseline", base)):
        try:
            manifest, rows = report["manifest"], report["rows"]
            seeds = manifest["seeds"]
            if len(set(seeds)) != len(seeds) or not seeds:
                problems.append(f"{label}: invalid seed manifest")
            if report.get("evaluator_failures"):
                problems.append(f"{label}: evaluator_failures")
            if len(rows) != manifest["items"] * len(seeds):
                problems.append(f"{label}: row count")
            pairs = [(r["item_id"], r["seed"]) for r in rows]
            items = {i for i, _ in pairs}
            if len(set(pairs)) != len(pairs) or set(pairs) != {(i, s) for i in items for s in seeds} or len(items) != manifest["items"]:
                problems.append(f"{label}: duplicate/missing item-seed pairs")
            for mid, value in report["metrics"].items():
                if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
                    problems.append(f"{label}: nonfinite/missing metric {mid}")
            for metric in spec.get("metrics", []):
                if metric["id"] not in report["metrics"]:
                    problems.append(f"{label}: absent metric {metric['id']}")
            slice_map = {}
            for row in rows:
                for mid in graded:
                    value = row.get(mid)
                    if value is None or not isinstance(value, (bool, int, float)) or not math.isfinite(value):
                        problems.append(f"{label}: missing/nonfinite row metric {mid}")
                if "cost" in row and (not isinstance(row["cost"], (int, float)) or not math.isfinite(row["cost"])):
                    problems.append(f"{label}: nonfinite cost")
                tags = frozenset(row.get("slices", []))
                if row["item_id"] in slice_map and slice_map[row["item_id"]] != tags:
                    problems.append(f"{label}: inconsistent slice tags")
                slice_map[row["item_id"]] = tags
            inventories.append((set(pairs), slice_map, seeds, manifest["items"]))
        except (KeyError, TypeError, ValueError):
            problems.append(f"{label}: malformed report")
    if len(inventories) == 2 and inventories[0] != inventories[1]:
        problems.append("PR inventory or slices differ from baseline")
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        for section in ("metrics", "slices"):
            key = (lambda x: x["id"]) if section == "metrics" else (lambda x: (x["name"], x["metric"]))
            current = {key(x): x for x in spec.get(section, [])}
            for old in base_spec.get(section, []):
                new = current.get(key(old))
                if new is None:
                    problems.append(f"ratchet: removed {section} {key(old)}")
                    continue
                a, b = (old.get("threshold", {}), new.get("threshold", {})) if section == "metrics" else (old, new)
                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"ratchet: disabled blocking {key(old)}")
                for bound in ("min", "max", "max_increase"):
                    if bound in a and (bound not in b or (b[bound] < a[bound] if bound == "min" else b[bound] > a[bound])):
                        problems.append(f"ratchet: loosened {bound} {key(old)}")
                if a.get("no_significant_drop") and not b.get("no_significant_drop"):
                    problems.append(f"ratchet: removed paired drop check {key(old)}")
    return sorted(set(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        key = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        if not a or a.keys() != b.keys():
            if entry.get("blocking"):
                blocked.append(key)
            lines.append(f"  {key}: missing or unpaired items")
            continue
        value = sum(a.values()) / len(a)
        bad = "min" in entry and value < entry["min"]
        note = ""
        if entry.get("no_significant_drop"):
            keys = sorted(a)
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", .95))
            bad = bad or hi < 0
            note = f"delta {d:+.3f} CI [{lo:+.3f},{hi:+.3f}]"
        if bad and entry.get("blocking"):
            blocked.append(key)
        lines.append(f"  {key}: {value:.4f} {note} {'BLOCK' if bad else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
