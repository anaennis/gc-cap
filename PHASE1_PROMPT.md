<!-- Author's original Phase 1 instructions, copied verbatim from the 2026-10-29 session. Do not edit. -->

# Claude Code prompt: Phase 1 (simulation + Bayes bound)

You are implementing Phase 1 of the project defined in `CRITERIA.md`. That file is the frozen design. Read it fully before doing anything else.

## Hard rules

1. **Do not modify `CRITERIA.md`.** If you think something in it is wrong, ambiguous, or infeasible, stop and write the issue to `AMENDMENTS_PROPOSED.md`. Do not act on it. I decide whether to amend.
2. **Do not change any threshold, gate, or verdict rule** (0.02, 0.8, 20,000 GCs, 100 false positives, completeness levels, bootstrap count) for any reason, at any stage.
3. **Do not tune simulator parameters to match the paper's numbers** or any other target after seeing results.
4. **Every network fetch** (throughputs, SSP libraries, any data) must have an entry in `DATA_LOG.md` (URL, date, version/checksum, purpose) *before* you rely on it. If something is unreachable, log the failure and say so. Do not substitute silently.
5. Items marked **[FILL]** in `CRITERIA.md` that are still unfilled: stop and list them. Do not invent values. I will fill them and commit before you proceed.
6. Report what you found, not what would be convenient. Say "NOT RUN" or "GATED" rather than omitting.

## Step 0: preflight (no simulation yet)

- Confirm `CRITERIA.md` is committed and record its git hash in `RUN_LOG.md`.
- List every unfilled **[FILL]** item. If any remain, stop here and report them.
- Check the environment: Python version, whether `python-fsps` is installed and working (check its current install docs; it needs the FSPS source and `SPS_HOME`), GPU availability, available disk and memory. Log the check results.
- Identify which second SSP library, if any, is obtainable. Log it or log that none is.

## Step 1: write `PLAN.md`

Before writing code, write a short plan covering: module layout, how you will implement the Monte Carlo marginalization for the Bayes bound (and its cost for the declared test sizes), how heteroscedastic noise is handled, random seeds (fixed, logged), and how results are stored. Do not start coding until `PLAN.md` exists. Flag anything in the plan that conflicts with `CRITERIA.md`.

## Step 2: simulator + unit tests

Implement the generative model exactly as in section 4. Required tests, all passing before Step 3:

- Shuffled-label null gives precision equal to class prior within bootstrap CI.
- Noise-free GC colors fall in a physically plausible range (report the range; do not auto-adjust anything).
- Bound is non-decreasing as depth improves, on a small pilot (this is a code test, so use a pilot with fixed seeds and keep it separate from the production data).
- Simulation is reproducible from seed.

**Pilot runs must never be used to adjust the simulator design.** If a pilot reveals a bug, fix the bug and log it. If it reveals a design concern, write it to `AMENDMENTS_PROPOSED.md`.

## Step 3: Bayes bound

Implement the primary estimator and the GBDT cross-check as in section 7. Run the validity gate. If the gate fails, **stop** and report. Do not proceed to methods.

## Step 4: methods

Implement M0 to M8 as specified, in both the paper-matched and saturated regimes, with the same train/test splits across methods. Use fixed seeds. Log hyperparameter search ranges before running them.

## Step 5: analysis and report

- Compute metrics, bootstrap intervals, gates, and verdicts with a script that reads only `CRITERIA.md` rules and saved results. The verdict tables in `REPORT.md` must be generated, not hand-written.
- List every GATED cell and every NOT RUN item.
- Mark FRAGILE calls.
- Produce the headline figure: precision at c = 0.5 versus depth shift, one line per method, with the bound band, per observed-i bin.
- Add the replication check against the paper's RF-15-colors result, reported as a comparison only.
- Write a plain-language summary at the top of `REPORT.md` that states each verdict (V1, V2, V3) exactly as the rules produce them, including INCONCLUSIVE and ASSUMPTION-DEPENDENT where they occur. Do not soften or strengthen.

## Deliverables

`CRITERIA.md` (unchanged), `PLAN.md`, `RUN_LOG.md`, `DATA_LOG.md`, `AMENDMENTS_PROPOSED.md` (if any), `REPORT.md`, code, saved results, figure. Commit as you go with clear messages. Do not push to a remote; I will push from my own shell.

## When to stop and ask me

- Any **[FILL]** unresolved.
- Bound validity gate fails.
- A required library or file is unreachable and no declared fallback exists.
- You think a frozen rule is wrong.
