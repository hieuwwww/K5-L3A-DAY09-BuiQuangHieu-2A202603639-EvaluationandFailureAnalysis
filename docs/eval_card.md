# Eval card — LogiX-VN, Day 9

- Owner: Bùi Quang Hiếu — 2A202603639 — 26ai.hieubq@vinuni.edu.vn.
- Code/grader implementation: `a1d864e`, `7916afe`; Day 8 import: `c92cd90` (unchanged after import). Python local 3.14.4; CI Python 3.13; MockLLM, offline judge replay.
- v1 SHA `2360b99186b7`: 14 items × 5 seeds 11/22/33/44/55, labels separate in `data/eval/labels_v1.json`; public regression corpus, not held-out.
- v1 baseline run `E-swarm-20261117-2360`, fixed `E-fixed-20261117-2360`, regression `E-seeded_regression-20261117-2360`. Reports are CLI-generated in `src/reports/`.

| Metric | Swarm | Fixed | Seeded regression | Blocking floor |
|---|---:|---:|---:|---|
| approval_bypass / secret_leak | 0 / 0 | 0 / 0 | 0 / 0 | max 0 |
| refund_amount_correct | .9857 | 1 | .8571 | .95 and no significant drop |
| pass_rate | .9857 | 1 | .7143 | .85 and no significant drop |
| reply_amount_matches_ledger | 1 | 1 | .7857 | .95 and no significant drop |
| pass_5 | .9286 | 1 | .7143 | monitoring |
| cost_per_success (simulated VND) | 49.567 | 48.7157 | 81.202 | monitoring |

Paired percentile bootstrap resamples item means over seeds, 1000 resamples, RNG 2027, 95% CI. Seeded pass_rate Δ −.271, CI [−.500,−.057]: gate exit 1; fixed Δ +.014, CI [0,.043]: exit 0. `ci_check` verifies baseline against replay swarm. Graders explain 100% of seeded failures with 0% false alarms on fixed; proposal_correct diagnoses full-quote errors that ledger-only checks miss.

Judge: tone κ=.757, P=.857, R=.8 eligible only for tone; helpful κ=.375, P=1, R=.3 excluded. See [audit](judge_audit.md). See [trace case](trace_case.md): C-002@11 first wrong event is model_override step 3; regression test exercises faulty and fixed variants.

## v2 — adversarial, noise and integrity

SHA `ae98c047ed9c`, 28 items × 5 seeds; pack mechanisms mapped in `fm_map.yaml`, ≥3 items per attacked FM. Baseline `E-swarm-20261117-ae98` has pass_rate .9786, pass_hat_5 .8929, safety 0/0. A/A on 66/77/88/99/110 versus spec seeds returns Δ=0 on all metrics, including cost. Floor pass_hat_5=.88 (≥.8) lies below observed baseline reliability so unchanged baseline passes; real LLM noise requires an independently measured interval.

| Variant | Gate result | Primary evidence |
|---|---|---|
| fixed / honest_refactor | merge / merge | no false alarms |
| seeded_regression | block | global pass_rate/refund/reply and slices |
| slice_regression | block | money_movement slice; global pass_rate=.9357, pass_hat_5=.8929 still pass floors |
| flaky_regression | block | pass_hat_5 and money_movement (also global pass_rate in this run) |

Slice floors: money_movement .95, adversarial .90, denial .90; each blocking with paired no-significant-drop. Mutation score 3/3, false alarms 0. `evaluator_errors_as_nan`, `dropped_failing_rows`, `cherry_picked_seeds`, `loosened_spec` all rejected by integrity/ratchet; duplicate pairs and evaluator_failures on otherwise green reports have regression tests. Ratchet compares `--base-spec` on the same eval version.

## Pilot and limits

Synthetic single-order shipping/damage claims only; no user-facing production release, no real payment/provider. Gate exit 1 is investigated by eval owner; no automatic waiver. Version dataset when changing item/label coverage and rebuild baseline; spec changes are versioned and cannot weaken same-version requirements.

MockLLM, 14/28 public items and replay labels do not establish production or hidden performance. Five seeds can miss a bug on a rarer seed pattern; A/A zero here is not proof of zero real-model variance. FM-08 checks explicit currency amounts; absent reply is no monetary assertion (reference swarm has no reply), not proof a response is complete. Judge disagreements use published human labels, not a new independent audit. Latency unavailable. Hidden grader is instructor-only.
