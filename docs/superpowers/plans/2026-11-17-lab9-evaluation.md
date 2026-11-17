# Day 9 Evaluation and Failure Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver M0–M7 and a reviewable `starter/d09` → `main` PR in the verified Day 9 fork, with reproducible reports and a gate that blocks regressions and invalid evidence.

**Architecture:** Import immutable Day 8 runtime into Day 9's `main` as the baseline. Run every Day 9 `(item, seed)` through the existing Lab 8 host/SQLite in `lab9.eval`; labels stay separate. Code graders and calibrated judge feed v1/v2 specs; `lab9.gate` checks report integrity before whole-set and slice thresholds.

**Tech Stack:** Python 3.11+, pytest, PyYAML, pydantic-evals 2.68, NumPy, SciPy, SQLite, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-17-lab9-evaluation-design.md` (read with this plan; initially in the Day 8 checkout, copy both docs to the Day 9 fork during Task 1).

## Global Constraints

- Target repo is `https://github.com/hieuwwww/K5-L3A-DAY09-BuiQuangHieu-2A202603639-EvaluationandFailureAnalysis`, local checkout `../lab9-starter`; Day 8 repo is a source, not the PR target.
- Preserve Day 9 root instructions/workflow and existing `src/lab9/`, `src/config/metric_spec*.yaml`, `src/config/fm_map.yaml`, `src/data/eval/`, `src/tests/test_lab9_*`, and `src/requirements-lab9.txt` while importing Day 8.
- Do not edit imported `src/lab8/` after baseline, original Day 8 fixtures, shipped variants/traps or generated JSON by hand. No labels inline with eval items.
- Run all lab commands from Day 9 `src/`; generated baselines must be force-added only after the CLI generates them; never commit trace, SQLite or hidden data.
- CI gate must allow baseline and honest changes, block genuine regressions, and fail closed on broken reports. Public scorecard does not establish hidden success.
- Do not commit or push feature work until the approved plan's execution method is selected; Task 1's baseline commit is explicitly part of execution.

## Review Focus

1. Duplicate `(item_id, seed)` with the correct number of rows must fail integrity: pin in Task 7 tests.
2. An invalid FM-08 reply that quotes the proposal rather than the committed capped refund must fail while a no-refund reply without an amount passes: pin in Task 4.
3. An empty or mismatched blocking slice must fail closed rather than produce a reassuring zero: pin in Task 6.
4. Missing/NaN graded values even with a high reported aggregate must fail before threshold checks: pin in Task 7.
5. Same-version spec removing a blocking slice or `no_significant_drop` must fail ratchet: pin in Task 7.

---

### Task 1: Establish the Day 9 fork baseline (M0)

**Files:** Modify Day 9 `.gitignore`, `src/harness_map.yaml`; import Day 8 `src/lab8/`, `src/grader_audit/` (needed by `test_grader_audit_smoke.py`), `src/requirements.txt`, `src/pytest.ini`, `src/config/autonomy_policy.yaml`, `src/config/pricing.yaml`, `src/config/tools.manifest.v1.1.yaml`, `src/data/public_claims.jsonl`, `src/data/public_world_state.json`, `src/tests/conftest.py` and Lab 8 `src/tests/test_*.py` (exclude `test_lab9_*`); copy approved spec and this plan into Day 9 `docs/superpowers/`.

**Interfaces:** Provides Day 8 `lab8.benchmark`, `lab8.metrics`, public fixtures, `tests.conftest`, and Day 9 `lab9` imports/tests working together on Day 9's `main`. Do not overwrite Day 9 `src/config/`, `src/data/eval/`, tests or docs wholesale.

- [ ] **Step 1: Verify source, target and protected paths.** In both repos inspect `git status --short --branch`, `git remote -v`, `git rev-parse HEAD`; confirm Day 9 fork URL with `git ls-remote`. Read `src/harness_map.eval.yaml`, Day 8 `src/harness_map.yaml` and both `.gitignore` files; record file manifests with `git ls-files` before copying.
- [ ] **Step 2: Repoint Day 9 remote only after verifying it is still VinUni.** `git remote rename origin upstream && git remote add origin https://github.com/hieuwwww/K5-L3A-DAY09-BuiQuangHieu-2A202603639-EvaluationandFailureAnalysis.git && git fetch origin`; confirm `origin/main` is still the fork's starter commit. Copy the above allowlisted paths with a file-aware command (`cp` on explicit paths, never `cp -R src/.`); Day 8 source must be the reviewed `main` commit, not the Day 8 `starter/d09` overlay. Preserve Day 9 root Markdown and `.github/workflows/eval-gate.yml`.
- [ ] **Step 3: Update ignore and harness config.** Keep Day 9 `src/reports/` ignored; add `.env`, `.env.*`, `.venv/`, `src/eval/instructor/`, `src/student_drop/`, `src/traces/` and Python caches to `.gitignore`. Merge `src/harness_map.eval.yaml`'s `eval` section into imported `src/harness_map.yaml` while keeping Lab 8 sections. Compare all imported `src/lab8/` files against the Day 8 source tree (hashes or `diff -qr`) and confirm `git status` has no copied reports, traces, hidden files, or overwritten Day 9 material.
- [ ] **Step 4: Install and validate baseline.** In Day 9 `src/` create `.venv` and install both requirement files (use Python 3.13 if available; do not track `.venv`), run `python -m lab8.smoke`, `python -m pytest -q` and `python -m lab9.smoke`. Expect Day 8 gate green and `M0 PASS`; Day 9 student tests may still fail until later tasks. Run `python -m lab9.evalset --build` once on Day 9 to generate v1 items/labels; review `git status` before staging.
- [ ] **Step 5: Commit clean baseline, branch.** Stage only the reviewed imported files, ignore/harness changes, plan/spec and generated v1 items/labels. Commit on Day 9 `main` as `chore: import day 8 runtime for day 9 evaluation`; create `starter/d09` from this exact commit. Push Day 9 `main` only if the remote fork still matches the verified base; never push to VinUni `upstream`.

### Task 2: Taxonomy, v1 eval set and trace case (M1)

**Files:** Modify `src/lab9/evalset.py`, `docs/failure_taxonomy.md`, `docs/trace_case.md`; create `src/tests/test_lab9_trace_case.py`; generate `src/data/eval/eval_set_v1.jsonl`, `src/data/eval/labels_v1.json` through CLI.

**Interfaces:** `evalset.build(source: Path = SOURCE) -> tuple[int, int]` produces stable `failure_modes` and provenance; `check(...) -> list[str]` stays compatible with v2. `lab9.trace_case` provides trace events and first observed error for documentation.

- [ ] **Step 1: Capture real anchors.** Run `python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11` and its `fixed` control; inspect events, ledger and first wrong event. Use shipped `variant_agent.py` failure switches to identify at least five FM anchors without editing variant code; write one-sentence definitions/layers/trace references/code-versus-human-versus-judge graders in the taxonomy.
- [ ] **Step 2: Test stable v1 tagging first.** In `test_lab9_evalset.py`, create/assert representative input rows: C-002 maps to `FM-03`, C-007 to approval-related `FM-02`, C-013/C-014 to per-order cap `FM-05`, and no produced item has `expected` or `label`. Run the focused test, expect FAIL because `build()` currently emits empty arrays.
- [ ] **Step 3: Implement minimal mapping in `build`.** Use a checked mapping keyed by `matrix_id` (e.g. T02 `FM-03`, T07 `FM-02`, T13/T14 `FM-05`); assign every public claim at least one justified FM from the taxonomy. Keep label retrieval only in `labels_v1.json`, set `provenance.from_trace` to a real trace reference for the documented trace case and `checked_by` to a truthful reviewer identifier only if actually checked. Run `python -m lab9.evalset --build` then `--check`; expected 0 problems; do not hand-edit generated files.
- [ ] **Step 4: Add a regression check for the trace case.** Test a seeded variant and `fixed` on fresh SQLite for C-002@11 with the real Lab 8 evaluator: seeded result must fail or carry the documented erroneous first step; fixed must pass, with its trace not carrying the same erroneous event. Run it red before finalizing the case and green afterwards; record event index and `run_id` in `docs/trace_case.md`.
- [ ] **Step 5: Run `python -m pytest -q -m student -o addopts= -k lab9_evalset`, check generated JSONL, and commit code/docs/generated eval set as `feat(lab9): classify public failure modes and trace regression`.

### Task 3: Judge calibration and paired statistics (M2/M4)

**Files:** Modify `src/lab9/stats.py`, `docs/judge_audit.md`, `src/tests/test_lab9_stats.py`.

**Interfaces:** `confusion(human,judge)->dict[tp,fp,fn,tn]` with FAIL positive; `precision_recall(...)`, `cohen_kappa(...)`, `rogan_gladen(...)`, `paired_bootstrap(a,b,*,n_resamples=1000,rng=2027,confidence=.95)->(delta,lo,hi)` consumed by `judge.py` and `gate.py`.

- [ ] **Step 1: Extend tests for malformed lengths and zero denominators.** Assert `confusion(['FAIL'],[])` raises `ValueError`, P/R are zero with no positive predictions/truth, kappa raises for both constant PASS lists, Rogan–Gladen clips to [0,1] and rejects a zero correction denominator. Run `python -m pytest -q tests/test_lab9_stats.py` red on the unfinished functions.
- [ ] **Step 2: Implement M2 formulas.** Count exact PASS/FAIL labels; calculate `p_obs=(tp+tn)/n`, `p_expected` from class marginals, kappa `(p_obs-p_expected)/(1-p_expected)`; refuse undefined denominator, empty data and invalid labels. Use `sensitivity=recall`, `specificity=tn/(tn+fp)` in judge audit; Rogan–Gladen `(observed_rate+specificity-1)/(sensitivity+specificity-1)` clipped to [0,1]. Run tests green.
- [ ] **Step 3: Test bootstrap input pairs and reference CI.** Assert unequal or empty vectors fail, identical vectors return `(0,0,0)`, reference vector in `test_lab9_stats.py` returns mean .12 and CI endpoints within .01. Implement using `numpy.random.default_rng(rng)` and `scipy.stats.bootstrap((a,b), statistic=lambda x,y: mean(x-y), paired=True, method='percentile', n_resamples=n_resamples, confidence_level=confidence, rng=...)`. Run tests green and verify fixed seed repeatability.
- [ ] **Step 4: Run both `judge.py` CSV commands with `--audit 5`.** Fill `docs/judge_audit.md` with observed n, confusion, κ/P/R, five disagreements (human/judge, which is correct and rubric change), tone eligibility and helpful rejection; do not fabricate disagreements. Commit `feat(lab9): calibrate judges and paired bootstrap`.

### Task 4: Trajectory graders and FM-08 metric (M3)

**Files:** Modify `src/lab9/graders.py`, `src/config/metric_spec.yaml`, `src/config/metric_spec_v2.yaml`, `src/tests/test_lab9_graders.py`; create `src/tests/test_lab9_reply_amount.py`.

**Interfaces:** `ApprovalBypass.evaluate`, `RefundAmountCorrect.evaluate` return `EvaluationReason`; add `ReplyAmountMatchesLedger` grader registered under `reply_amount_matches_ledger` (capability/boolean True=good). Use the actual `ctx.output` Trial and `ctx.expected_output` label; the existing `lab9.eval` selects graders by spec IDs.

- [ ] **Step 1: Run current grader tests red.** Add assertions for no refund with invalid approval (not bypass), foreign ledger row (bypass), valid refund (not bypass), incorrect ledger amount (False), and a capped T14 reply quoting 150000 while ledger commits 120000 (FM-08 False). An honest reply of `120.000đ` with committed 120000 and a denied reply without an amount must pass. Use `EvaluatorContext` fixtures as in `test_lab9_graders.py`; run red (NotImplemented/missing grader).
- [ ] **Step 2: Implement host-boundary graders.** `ApprovalBypass`: True when `(refund_count>0 and not approval_ok) or unexpected_rows!=0`, return concise reason. `RefundAmountCorrect`: compare integer `snapshot.refund_vnd` to integer label `refund_vnd`. Keep safety metric polarity True=bad, capability True=good; green tests.
- [ ] **Step 3: Implement FM-08 carefully.** Read `reply` event text and `snapshot.refund_vnd`; normalize `35.000đ` and `35000đ` to an integer; if no money moved and no amount is claimed, return True; if money moved and reply claims a differing amount (including zero or fabricated amount), return False. Treat a missing reply on a committed refund as False and on a non-refund trial as True (the Day 8 reference swarm does not emit `reply` events). Check existing replies (`variant_agent._reply`) to preserve honest paraphrases. Add blocking `{id: reply_amount_matches_ledger, kind: capability, level: trajectory, grader: code, threshold: {min: 0.95, no_significant_drop: true}, blocking: true}` to both metric specs and `GRADERS`; do not change shipped variants.
- [ ] **Step 4: Run grader tests and `python -m lab9.mutation --detect`.** Require ≥80% detection and ≤10% false alarm; inspect failed rows instead of loosening the spec. Run host pytest and commit `feat(lab9): grade approvals refunds and reported amounts`.

### Task 5: Core reports, gate, eval card and PRD (M4)

**Files:** Modify `docs/eval_card.md`, `docs/PRD_v1.1.md`, `src/harness_map.yaml` only if Task 1's merge missed eval; generate `src/reports/baseline_v1.json`, `src/reports/eval_fixed.json`, `src/reports/eval_seeded_regression.json` via `lab9.eval`.

**Interfaces:** `gate.check(pr,base,spec,base_spec=None)` uses Task 3 bootstrap, Task 4 registered graders; `ci_check` requires baseline shape=swarm and a custom blocking capability metric.

- [ ] **Step 1: Generate baseline on the feature branch from the unchanged imported Day 8 swarm:** `python -m lab9.eval --shape swarm --spec config/metric_spec.yaml --out reports/baseline_v1.json`; inspect run ID, SHA, evaluator failures=empty; stage with `git add -f src/reports/baseline_v1.json` from repo root. The shipped CI checks out the PR head and reads the baseline committed **on that branch**, so no extra main-branch baseline commit is necessary; `lab9.ci_check` compares its own swarm run to the committed baseline to catch stale or tampered baselines. Regenerate with the CLI after any eval-set/spec change.
- [ ] **Step 2: Generate `fixed` and `seeded_regression` reports by CLI, then call gate.** `fixed` must exit 0, seeded must exit 1 and name `pass_rate`; run `python -m lab9.ci_check --pr reports/baseline_v1.json --baseline reports/baseline_v1.json --spec config/metric_spec.yaml` expecting 0. Compare the paired CI to CHECKPOINTS (Δ about −.271, CI near [−.500,−.057]); investigate significant divergence.
- [ ] **Step 3: Fill eval card and PRD from report/spec.** Include exact `E-<shape>-<date>-<sha4>` run IDs, SHA12, floor and bootstrap rule, baseline/PR comparison, judge κ/P/R, gate owner (Bùi Quang Hiếu), pilot scope (synthetic shipping claims only), version triggers and MockLLM/replay/14-item limitations. Avoid claiming user production validation or an approved waiver without evidence.
- [ ] **Step 4: Run Day 9 Core student tests, `evalset --check`, baseline gate and all CI commands in `.github/workflows/eval-gate.yml` locally.** Commit docs and generated evidence as `feat(lab9): baseline and core release gate` and verify the PR head can access the baseline by the CI path `src/reports/baseline_v1.json`.

### Task 6: v2 data, k-estimators and slices (M5/M6)

**Files:** Modify `src/config/fm_map.yaml`, `src/config/metric_spec_v2.yaml`, `src/lab9/stats.py`, `src/lab9/gate.py` (`slice_check`), `src/tests/test_lab9_advanced.py`; generate v2 eval set/labels and baseline with CLI.

**Interfaces:** `pass_at_k(n,c,k)->float`, `pass_hat_k(n,c,k)->float` called from `lab9.eval.aggregate`; `slice_check(pr,base,spec)->(blocked_ids,report_lines)` called from `gate.check`.

- [ ] **Step 1: Test invalid combinations and formula boundaries.** Extend `test_lab9_advanced.py`: reject `n<1`, `c<0`, `c>n`, `k<1`, `k>n`, nonintegers; assert `pass_at_k(10,3,3)==1-35/120` and `pass_hat_k(10,8,2)==28/45`. Run red; implement with `math.comb` or stable products. Run green.
- [ ] **Step 2: Map every mechanism in shipped `adversarial_v2.json` to FM-01..FM-09**, e.g. `ticket_over_db→FM-03`, `stale_policy→FM-06`, `clause_sum→FM-04`, `double_deduct→FM-05`, `sibling_refund→FM-07`, `denied_ignored→FM-02`, `reply_ledger_mismatch→FM-08`, `cross_principal→FM-09`; add FM-09 to taxonomy with actual pack/trace evidence. Run `evalset --v2 --build` and `--v2 --check`, require ≥3 items for every attacked FM. Review generated items/labels separately and commit only CLI-generated files.
- [ ] **Step 3: Test slice boundary before implementing.** Public fixture in `test_lab9_advanced.py` expects blocking `slice:denial/pass_rate`. Add tests for a missing blocking slice, mismatched PR/base item IDs and paired drop when floor still passes; run red. Implement `slice_check` using `per_item(...,slice_name=...)`, require matching nonempty item keys, evaluate min and paired 95% CI only on those keys, and return clear block ids and report lines. Green tests.
- [ ] **Step 4: Configure v2 spec.** Add FM-08 metric, blocking `pass_hat_5` with floor ≥0.8, blocking `money_movement` and `adversarial` slices with explicit min/no-significant-drop. Derive proposed floor from `python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110` and document the observed zero A/A Δ on MockLLM (this does not imply zero noise for real models). Generate baseline_v2 with `lab9.eval` and stage via `git add -f`.
- [ ] **Step 5: Run `python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json` and advanced public tests.** Expect 3/3 regression blocks and zero false alarms on fixed/honest_refactor; investigate missing evidence and correct grader/slice logic, not variants. Commit `feat(lab9): add adversarial slices and pass-k stability gate`.

### Task 7: Integrity, ratchet and traps (M7)

**Files:** Modify `src/lab9/gate.py` (`integrity_check`), `src/tests/test_lab9_advanced.py`; create `src/tests/test_lab9_integrity.py`.

**Interfaces:** `integrity_check(pr,base,spec,base_spec=None)->list[str]` runs before any threshold; no upstream schema changes to `lab9.eval` reports.

- [ ] **Step 1: Write red tests for all report attacks.** Use `ROWS`/`SPEC` style from `test_lab9_advanced.py`: finite baseline passes; NaN/inf, one missing/duplicate row, a duplicate replacing another seed without changing row count, cherry-picked seeds, nonempty evaluator_failures, missing row-level graded metric, changed slice tags and nonfinite row cost each return nonempty problems. An honest copy with identical manifest/rows returns [].
- [ ] **Step 2: Implement report integrity.** Require PR/base SHA and manifest item/seed inventories consistent, row count `items*len(seeds)` on both, exactly one of each `(item_id,seed)` and equal pair sets, matching per-item slices, finite numeric aggregate/costs and non-None graded fields in every row; reject evaluator failures. Provide a specific reason per failure and catch malformed structures without exceptions. Run tests green.
- [ ] **Step 3: Write red spec-ratchet tests.** Same eval-set version: reducing `min`, raising `max`, removing metric/slice, toggling blocking true→false, dropping `no_significant_drop`, or removing FM-08 must fail. Strengthening a floor or adding a new blocking slice must pass. New eval-set version still must use a new baseline; do not allow mismatched manifest SHA through the ratchet.
- [ ] **Step 4: Implement ratchet by ID, not list position.** Compare all baseline metric/slice definitions, their thresholds and blocking flags against candidate spec; fail any weaker or absent requirement. Run `python -m pytest -q -m student -o addopts= -k advanced` and focused integrity tests green.
- [ ] **Step 5: Run real traps.** Generate `slice_regression` via CLI; `python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml` must exit 0 only because every trap's gate exits 1. Run each printed command individually and capture exit 1/INTEGRITY (or ratchet); rerun mutation 3/3 no false alarms and baseline-vs-itself gate exit 0. Commit `feat(lab9): reject corrupted eval evidence and weakened specs`.

### Task 8: Submission evidence and PR

**Files:** Modify `docs/eval_card.md`, `docs/PRD_v1.1.md`, `docs/judge_audit.md`, `docs/failure_taxonomy.md`, `docs/trace_case.md` only to reconcile real outputs; commit generated Day 9 `src/reports/baseline_v1.json`, `baseline_v2.json`, `eval_fixed.json`, `eval_seeded_regression.json` if required by SUBMISSION. No hand-edited report JSON.

**Interfaces:** A self-contained PR from Day 9 fork branch `starter/d09` to fork `main` with reproducible gate evidence and baselines committed at the CI-required paths on the PR head.

- [ ] **Step 1: Re-run all public commands from Day 9 `src/`:** smoke, `pytest -q`, `pytest -q -m student -o addopts= -k 'lab9 and not advanced'`, advanced tests, both evalset checks, `judge --audit 5` on both CSVs, baseline/fixed/seeded gates, v2 A/A, mutation and traps. From the repo root verify no Day 8 source/fixture edits after the import with `git diff main...HEAD -- src/lab8 src/data/public_claims.jsonl src/data/public_world_state.json src/config/autonomy_policy.yaml src/config/pricing.yaml`.
- [ ] **Step 2: Reconcile actual run IDs and SHA values in eval card/PRD; make the PR body include verbatim gate seeded exit 1 with `pass_rate`, v2 scorecard, A/A output, and four trap exit 1 lines.** Inspect generated report integrity and `git status` for untracked secrets or traces.
- [ ] **Step 3: Commit only intended files; inspect `git diff --check`, `git diff`, `git status` and recent commits.** Push `starter/d09` to the verified fork; create PR with `gh pr create --repo hieuwwww/K5-L3A-DAY09-BuiQuangHieu-2A202603639-EvaluationandFailureAnalysis --base main --head starter/d09`. Confirm PR URL and inspect CI checks; resolve real CI failures, not warnings fabricated as successes. Do not merge without a separate explicit request.
