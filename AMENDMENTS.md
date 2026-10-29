# AMENDMENTS.md

Changes to the frozen CRITERIA.md (commit bd254ba). Each entry gives a timestamp, what changed, why, and whether any results had been seen.

## A1 — SSP libraries (§5)
- **Timestamp:** 2026-10-29 13:37:24 -0700
- **Decided by:** the author (Ana Ennis), from options in AMENDMENTS_PROPOSED.md P12.
- **Change:** §5 "SSP library" axis.
  - Fiducial: **FSPS MILES + MIST**, explicitly named, because it is no longer the FSPS default.
  - Second library: **FSPS Padova (Padova2007) + C3K_LR**, replacing "FSPS Padova + BaSeL".
  - Both use FSPS commit `b6600ff3a983e0c35ec722e961dfdc89c97c37f2` (compiled through the python-fsps 0.5.0 wrapper with this FSPS source; see RUN_LOG).
- **Why:** BaSeL is no longer a compile option in current FSPS, so "Padova + BaSeL" cannot be built. Also, "FSPS default (MILES + MIST)" is inconsistent with current FSPS, whose default is MIST + C3K_LR. The replacement changes both the isochrones and the spectral library relative to the fiducial, which keeps §5's stated intent.
- **Results seen:** **None.** No simulation or compute had run.
- **Effect on other rules:** none. Thresholds, gates and verdict rules are unchanged. Corner (a) uses the new second library.

## A2 — Catalog inclusion rule (fills a gap in §4; affects which sources enter every sample)
- **Timestamp:** 2026-10-29 14:11:34 -0700
- **Decided by:** the author, from PLAN.md ⚑F1 options.
- **Change:** a simulated source (any class) enters the catalog only if its **reported magnitude error is ≤ 0.5 mag in every band (u, g, r, i, z, y)**. This is the cut used by arXiv:2512.17644v2 §II.4. The reported error is computed from observed quantities, σ_m = 1.0857 · s_obs / f_obs with s_obs² = σ_bg² + (κ · f_obs)², so the cut is equivalent to S/N_obs ≥ 2.17 in every band. All kept sources therefore have positive flux in every band, and ordinary AB magnitudes and colors are used (no asinh magnitudes).
- The class ratios (§4.1 1:34, §4.3 1:2.6) are applied to the true-magnitude populations **before** this cut. The GCLF and number counts are also defined before the cut.
- Bins (§4.5), gates (§8) and bound (§7) all operate on the post-cut catalog. The bound's likelihoods are restricted to the selected region, which needs no change to the likelihood ratio because the cut depends only on observed data.
- **Expected consequence, stated in advance:** at SV depth the cut is set mostly by u and y, so the fainter bins will be sparsely populated and are likely GATED.
- **Replication note (§8, comparison only; no rule change):** the paper's labelled galaxies are 19.0 ≤ i ≤ 22.5 (plus a DES morphology cut) and its stars are 18 ≤ i ≤ 20. Its GCs are spectroscopically confirmed, so they are skewed bright relative to the GCLF. Our galaxies are 21 < i < 27, drawn from number counts. REPORT.md will state these differences next to the replication comparison.
- **Why:** CRITERIA has no detection rule, and at SV depth many simulated faint sources would have non-positive fluxes, leaving magnitudes and colors undefined. The paper's cut is citable and keeps the replication setup comparable.
- **Results seen:** **None.** No simulation or compute had run.
- **Effect on other rules:** none. Thresholds, gates and verdict rules are unchanged.
