# AMENDMENTS_PROPOSED.md

These are proposals only, and I have not acted on any of them. They were written on 2026-10-29 during Step 0 preflight. No simulation or compute had run and no results had been seen. The numbers below come from the GCLF in CRITERIA §4.2 and an **illustrative** number-count slope (dlogN/dm = 0.35, because the real value is [FILL]). They are back-of-envelope estimates, not results.

Because CRITERIA.md is not yet committed, the author can resolve these by editing it before the freeze (filling [FILL] items is pre-registration, not an amendment).

## P1. Fiducial test-set size is likely infeasible on this machine
- §4.4 requires ≥200,000 GCs in **every** observed-i bin. The GCLF puts m_TO,i = 23.0, σ = 1.5. The rarest bins (<21 and >25) each hold ~9.1% of GCs, so the fiducial set needs ~2.2M GCs.
- At 1:34 (i<24) and power-law counts out to i = 27, the within-bin galaxy:GC ratios come out to roughly 19, 28, 62, 214 and 2750 for bins 21-22 through >25. That implies **~7e8 test galaxies** for the fiducial configuration alone.
- At ~20 float32 values per source, that is ~55 GB. **Free disk is 35 GiB and RAM is 16 GB.**
- The cost of Monte Carlo marginalization is about N_test × N_latent × 5 bands × 2 classes. With N_latent ~1e5 that is ~1e14 kernel evaluations, which is days to weeks on an M2.
- Options for the author:
  - (a) Change the requirement to "≥200,000 GCs per bin, contaminants per bin sized by the FP gate" and reweight to the declared class ratio. Precision then comes from importance-weighted counts. This would need a declared weighting rule.
  - (b) Run on larger hardware.
  - (c) Lower the per-bin sizes.

## P2. GBDT cross-check at N_GC = 1e7 is infeasible as written
- §4.4 says contaminants scale to the class ratio. At 1e7 GCs, that means ~3e8 or more training contaminants, which won't fit in 16 GB RAM.
- The same options as P1(a)/(b) apply, for example class-weighted training with a declared, fixed contaminant cap.

## P3. The <21 bin is GATED by construction
- Galaxy counts are defined only for 21 < i < 27 (§4.3). The only galaxies in observed i < 21 are ones scattered down by noise, so the bin can't reach ≥100 false positives.
- The bin will be GATED in every configuration. Should that be stated in advance, or should the count range be extended?

## P4. c = 0.3 cells at non-fiducial grid points are GATED by construction
- Non-fiducial grid points have ≥50,000 GCs per bin (§4.4). At c = 0.3 that gives ~15,000 true positives, which is below the 20,000-GC gate.
- Every c = 0.3 cell off-fiducial would be GATED, and c = 0.3 is the paper's regime. Raising the off-fiducial minimum to ≥67,000 would avoid this.
- V1 uses c = 0.5 (25,000 true positives), so V1 itself is unaffected.

## P5. Ambiguity: does the per-bin Set A bound condition on bin membership?
- Bins are defined on observed i. If the Set A likelihood ratio is computed within a bin, it implicitly uses magnitude information: the within-bin class prior and the within-bin p(colors | class, bin).
- The alternative is the pooled Set A likelihood ratio, evaluated per bin. That stays "colors only" but is not optimal within a bin.
- This choice changes the bound and V3 (C − A). Please state which one is meant.

## P6. Design concern: V1 includes the depth-shift axis
- V1 requires the Set A bound to be on one side of 0.8 at every non-gated grid point, and Δ ∈ {−1, …, +1} is one of the axes. Depth is a known survey parameter, not a modeling assumption.
- Any sizeable depth dependence across 0.8 makes V1 ASSUMPTION-DEPENDENT almost automatically. Should V1 be evaluated per Δ instead?
- This is flagged only; it is the author's call.

## P7. Data dependencies on the paper
- The fallback depth presets (§4.1, Table 3) and M0's hyperparameter search ("as in the paper's description") both need arXiv:2512.17644v2 to be fetched and logged.
- If the paper's description of the search is incomplete, M0 needs a declared default search range.

## P8. Two SSP builds
- The fallback second library (Padova + BaSeL) needs python-fsps compiled with different flags, so two separate builds or environments are required.
- This is a logistics note, not a rule change.

---
## Added 2026-10-29 after checking sources (still no compute, no results seen)

## P9. The paper is a 3-class classifier; Phase 1 is 2-class
- arXiv:2512.17644v2 classifies GC, galaxy and star, and its MLP has 3 softmax outputs. M0/M1 here are GC vs galaxy (arm S is secondary).
- The replication comparison (§8) should say this. It is not like-for-like.

## P10. M0/M1 tuning details are missing from the paper
- The RF search ranges and n_iter are not given, and neither are the MLP optimizer, learning rate or epochs.
- "Hyperparameter search as in the paper's description" can't be fully reproduced. I propose declaring the ranges in CRITERIA (or PLAN.md, logged before running) and labelling M0/M1 as "paper-like, ranges author-declared".

## P11. Galaxy counts and p(z) are used outside the range where they're valid
- The count slope 0.31 is stated for 20.5 < i < 25.5, but §4.3 uses 21 < i < 27. That extrapolates 1.5 mag, into the range where counts are known to flatten.
- The Science Book z0(i) relation is for magnitude-*limited* samples, measured for 21.5 < i < 23. It is not a p(z) at fixed magnitude.
- I tried deriving p(z | i) from it, as d/di[N(<i) p(z | <i)]. The result goes **negative at low z for i ≲ 22** (at i = 21.5, d ln/di at z→0 = 0.714 − 0.820 < 0). So the derived version isn't usable as-is.

---
## Resolution status (2026-10-29, before the freeze)
These were all resolved by pre-freeze edits to CRITERIA.md, made at the author's explicit request. They are not amendments, because no compute had run.
- P1, P2: resolved (§4.4 subsampling and importance weighting; gates count raw sources; §7 cross-check uses the same scheme).
- P3: resolved (§4.5 states in advance that the <21 bin is GATED).
- P4: resolved (§4.4 off-fiducial minimum raised to 67,000).
- P5: resolved (§3: per-bin likelihood ratio using bin membership, for all methods).
- P6: resolved (§8 V1 evaluated per depth setting; single-point label).
- P7: resolved (§4.1 depths from Table 3; §6 declared M0/M1 hyperparameters).
- P8: noted (two python-fsps builds).
- P9: resolved (§8 replication caveat; arm S in §4.3).
- P10: resolved (§6 declared settings).
- P11: resolved (§2 non-claims; §4.3 fixed p(z); slope axis kept with 0.25).

---
## P12. SSP libraries as written in §5 don't match current FSPS (raised 2026-10-29, after the freeze, before any compute; no results seen)
- FSPS commit `b6600ff` (2026-09-28, DATA_LOG #12) defaults to **MIST + C3K_LR**. CRITERIA §5 says "FSPS default (MILES + MIST)", which is internally inconsistent for this version.
- **BaSeL is no longer a compile option.** The spectral libraries are C3K_LR, C3K_HR and MILES. So "FSPS Padova + BaSeL" can't be built from current FSPS.
- MILES in this version comes on an extended wavelength grid (91 Å – 10⁸ Å; the MILES range is padded with a theoretical library). It therefore covers ugrizy at all simulated redshifts. Padova2007 isochrones are present.
- python-fsps 0.5.0 (PyPI) ships prebuilt wheels with default flags. Any non-default library needs a source build with flags.
- Options:
  1. Fiducial **MILES + MIST** (the library named in §5), second **Padova + C3K_LR**. The second differs from the fiducial in both isochrones and spectra, which matches §5's stated intent ("changes isochrones and spectral library"). *Recommended.*
  2. Fiducial MILES + MIST, second Padova + MILES (isochrones only).
  3. Pin an older FSPS commit that still has BaSeL for the second library. This mixes code versions.
  4. Use §5's declared fallback: library sensitivity "not assessed", and every verdict labelled "conditional on a single SSP library".
- Because CRITERIA.md is frozen, any of options 1–3 must be recorded in AMENDMENTS.md (timestamp, change, reason, "no results seen").

---
## P13. torch from the Sherlock module (2.4.1), not ~2.15.0 via pip (raised 2026-10-30, environment build, no results seen)
- HANDOFF §3.5 asks for torch "closest to 2.15.0" for the node's CUDA. The pip CUDA wheel does not fit: build job 50328971 failed with ENOSPC in `$HOME` (15 GB quota full; `$GROUP_HOME` 99% full).
- Author chose (2026-10-30) the Sherlock module `py-pytorch/2.4.1_py312` (reports `2.4.0a0`, CUDA 12.6, cuDNN 9.4), exposed to `.venv` through a `.pth` file. Runtime jobs must `ml math py-pytorch/2.4.1_py312`.
- Consequence: the module torch needs numpy 1.x, so both venvs pin `numpy<2` (laptop lock has numpy 2.4.6). Same pin in both, so the two SSP builds differ only in FSPS flags.
- Environment-only; no threshold, gate, verdict or simulator parameter changes.
