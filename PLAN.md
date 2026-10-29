# PLAN.md — Phase 1 implementation plan

Governs: CRITERIA.md @ `bd254ba` (sha256 `2e50e070…5fae11`) + AMENDMENTS.md A1. Written 2026-10-29 before any simulation code. **Items marked ⚑ are choices CRITERIA does not fix. All were decided by the author on 2026-10-29 (§9): F1 became amendment A2, and F2–F13 were accepted as proposed.** Nothing here changes a threshold, gate or verdict rule.

## 1. Module layout

```
gccap/
  frozen.py       # constants transcribed from CRITERIA + AMENDMENTS; asserts CRITERIA.md sha256 at import
  seeds.py        # SeedSequence tree (see §5)
  photometry.py   # throughputs v1.9.2 loader, AB synthetic photometry, IGM ⚑F2
  grids.py        # FSPS precompute: GC SSP grid, galaxy CSP grid → band fluxes over (params, A_V, z); one cache per SSP library
  population.py   # priors (§4.2/4.3), GCLF, number counts, p(z), TRILEGAL star bank; latent draws
  noise.py        # depth presets SV/C10/paper-like, Δ shift, flux noise + 0.01 mag floor, detection ⚑F1
  features.py     # sets A (5 colors), A15 (15 colors), B (+errors), C (+ i); observed-i bins
  sample.py       # test/train set builders: per-bin GC quotas, contaminant subsampling + importance weights (§4.4)
  bound.py        # Monte Carlo likelihood-ratio bound (§3 below)
  methods/        # m0_rf, m1_mlp, m2_pca_rf, m3_ae_rf, m4_6_gbdt, m7_xd, m8_lda_gbdt
  metrics.py      # weighted precision at completeness, gates, multinomial bootstrap, gaps, margins
  verdicts.py     # V1/V2/V3 rules, reading rules from frozen.py only
  report.py       # generates REPORT.md tables + figure from saved results
scripts/          # build_grids.py, make_sets.py, run_bound.py, run_methods.py, analyse.py
tests/            # pytest: required Step 2 tests + unit tests
configs/grid.yaml # fiducial, 11 OAT points, 3 corners, arm S (generated from frozen.py; read-only)
results/          # see §6
```

Two environments: `.venv` (MIST+MILES, fiducial) and `.venv-padova` (Padova+C3K_LR). Only `grids.py` touches FSPS. Everything downstream reads the cached grids, so the second library changes nothing but the grid file.

## 2. Simulator (CRITERIA §4)

**FSPS settings (⚑F5):** Kroupa IMF (FSPS default `imf_type=2`). Scaled-solar abundances, logzsol = [Fe/H] (no α-enhancement). FSPS defaults otherwise, recorded in the grid file header.

**GC grid:** SSPs (`sfh=0`), [Fe/H] from −3.0 to +0.5 in 0.05 dex, all FSPS ages, interpolated to the drawn age (10–13.5 Gyr). Rest-frame (z = 0) fluxes, no dust. Cost: ~13 s per metallicity, ~15 min per library (measured).

**Galaxy grid:** delayed-tau (`sfh=4`). Nodes:
- log Z/Z☉: −1.5 to +0.2 in 0.1 dex
- tau: 0.1–10 Gyr, 25 log-spaced nodes
- age: 0.1–13.8 Gyr, 60 log-spaced nodes
- nebular on, with `gas_logz` = logzsol and `gas_logu` = −2 (⚑F12)

The rest-frame spectra are then dusted analytically with the Calzetti law (FSPS `dust_type=2` curve reproduced exactly, A_V = 1.086 × dust2). They are redshifted over z = 0–4 in steps of 0.01 (⚑F13 caps z at 4; P(z > 4 | z₀ = 0.30) = 1.7e-4; those draws are redrawn, which truncates p(z) at 4). IGM attenuation is applied (⚑F2), and band fluxes are computed as GPU matrix products. Cost: ~18 metallicities × 24 s plus ~27k CSP calls × 0.024 s, about 20 min per library (measured).

**Interpolation (⚑F6):** galaxy and GC band fluxes for any latent θ come from multilinear interpolation of the cached grid. **The simulator *is* this interpolated model.** Test sets, training sets and the bound's latent bank all use it, so the bound is exact for the data it scores. Fidelity to direct FSPS is checked on 2,000 random draws per class and reported (max and 99th-percentile color error). It is not tuned.

**Magnitudes:**
- GCs: M_i ~ N(−8.5, 1.5) + 31.5. The other bands follow from the SSP colors.
- Galaxies: true i from dN/dm ∝ 10^{slope·m}, 21 < i < 27. The other bands follow from the redshifted SED colors. Magnitude is independent of SED and z (CRITERIA §2).
- Stars (arm S): TRILEGAL catalog rows used as an empirical bank, resampled.

**Age-of-universe cap (⚑F3):** Planck18 cosmology (astropy; one more logged install).

**Metallicity outside an isochrone grid (⚑F4):** drawn values are kept. FSPS clamps to the grid edge, and the clamped fraction is reported per library. Expected Padova clamping (Z_min = 2e-4, [Fe/H] ≈ −1.98) is 2.8% of GCs at fiducial and 7.2% with wider [Fe/H] (computed from the declared mixture).

**Noise (§4.1):** per band, σ_bg = f(m5)/5 in flux. The total flux variance is s² = σ_bg² + (κ·F_true)², with κ = 0.4 ln10 × 0.01 (the 0.01 mag floor in quadrature). Observed flux = F_true + N(0, s²). This is heteroscedastic, because s depends on the true flux and band. The likelihood uses it exactly (§3).

**Catalog inclusion (AMENDMENTS A2):** a source is kept only if its reported magnitude error is ≤ 0.5 mag in all six bands, i.e. S/N_obs ≥ 2.17 per band, with the error computed from the observed flux. Ordinary AB magnitudes and colors are used. Class ratios, the GCLF and the counts are defined before the cut. At SV depth the fainter bins are expected to be sparse or GATED.

## 3. Bayes bound: Monte Carlo marginalization (CRITERIA §7)

**Latent bank** (independent seeds from test/train): L_GC = 1e6, L_gal = 4e6 per configuration (scrambled-Sobol draws mapped through the prior CDFs), L_star = full TRILEGAL bank. Each latent l carries its true fluxes F_l (6 bands).

**Likelihoods:**
- **Set C** (colors + observed i ≡ the observed flux vector f): p(f | class) = (1/L) Σ_l Π_b N(f_b; F_lb, s_b(F_lb)²). This is exact under the model, including heteroscedastic noise.
- **Set A** (colors + bin membership): p(c, bin | class) = ∫_{m_i ∈ bin, A2 cut} p(f(c, m_i) | class) |J(c, m_i)| dm_i over the observed i magnitude. 24-node Gauss–Legendre quadrature per bin, with adaptive subdivision when the integrand ESS is low. The Jacobian is class-independent but kept for the pooled LR.
- **Set B:** the reported color errors are deterministic functions of the observed fluxes. If the map f → x_B is injective (checked numerically on the pilot), LR_B = LR_C exactly. In that case **Bound(B) = Bound(C) by construction (⚑F7)**. If it is not injective, B is marginalized over the non-identified direction like A.
- **Within-bin LR:** p(x | GC)/p(x | cont) × P(bin | cont)/P(bin | GC). The bin factor is constant within a bin, so per-bin thresholds don't need it. It is used for the **pooled** curves, which rank by the full LR over all bins (⚑F11).

**Computation:** torch on MPS, float32 differences with log-sum-exp accumulation, in chunks.
- Pruning: latents are pre-sorted by true i, and for each test object only latents within ±7 s of observed i (Set C) or the bin ± 7 s (Set A) are scanned.
- MC accuracy: the effective sample size of the latent weights is recorded per object. Objects with ESS < 50 trigger a 4× bank top-up for that object.
- Each configuration is run with **two independent latent banks**. Their bound difference is reported per cell as MC error. It is a diagnostic, not a gate.

**Cost:**
- Fiducial: ~1.2M test GCs plus contaminants sized by the §4.4 rule (expected ~2–8M after the cap).
- Set C: ~2.5e12 object–latent pairs, about 5 min on MPS.
- Set A: × 24 quadrature nodes, about 2 h.
- Total: about 15 configurations + arm S at ⅓ size, × 2 banks, roughly 30–40 GPU-hours for the bound.
- These are estimates. Actual throughput will be measured on the pilot and logged. Timing data are never used to change the design.

**Cross-check (gate):** LightGBM per feature set at N_GC = 1e6 and 1e7 (contaminants capped and weighted per §4.4), with fixed hyperparameters declared in §4 and early stopping on a separate validation set. The gate is checked at every non-GATED reported (configuration, set, bin, c) cell: |P_bound − P_GBDT(1e7)| ≤ 0.02 and |P_GBDT(1e7) − P_GBDT(1e6)| < 0.01. Any failure means **STOP**, with a report naming the failing cells. Cost: ~90 models at 10–30 min each.

**Sanity tests (§7):**
- (i) Shuffled labels → precision equals the within-bin weighted prior, within CI.
- (ii) Bound non-decreasing as Δ → +1. CI-aware: a decrease is a failure only if the bootstrap CI excludes zero.
- (iii) C ≥ B ≥ A per cell within CI.
- (iv) Near-zero noise: depth +10 mag and floor 1e-4 mag, compared with a 1-NN noise-free separability estimate from 1e6 noise-free draws per class.

Pass/fail is logged. A failure stops verdicts (CRITERIA §7).

## 4. Methods (CRITERIA §6). Ranges are logged here before any run.

All methods see bin membership as a categorical feature (CRITERIA §3) and are thresholded per bin. Contaminant importance weights are passed as sample weights. Model selection uses 5-fold stratified CV inside the training set only. The test set is never seen.

| ID | Implementation | Search (randomized, 50 draws unless stated) |
|---|---|---|
| M0 | sklearn RandomForest, 15 colors | as CRITERIA §6 |
| M1 | torch MLP 15→10→5→1 | as CRITERIA §6 (fixed, no search) |
| M2 | PCA(4) → RF | RF space as M0 |
| M3 | AE 5→7(sigmoid)→4 latent→linear decoder, MSE, Adam 1e-3, batch 256, ≤500 epochs, patience 20 → RF on latent | RF space as M0 |
| M4–M6 | LightGBM, sets A/B/C | num_leaves {15, 31, 63, 127, 255}, learning_rate {0.02, 0.05, 0.1}, min_child_samples {20, 100, 500}, feature_fraction {0.8, 1.0}, lambda_l2 {0, 1, 10}, n_estimators ≤ 5000 with early stopping 100; 30 draws |
| M7 | Extreme deconvolution (own torch EM, Bovy et al. 2011), per-class GMM in Set A color space with per-source propagated covariances (Set B). LR classifier. | K_GC ∈ {2, 4, 8}, K_cont ∈ {8, 16, 32}, chosen by held-out log-likelihood. Grid, not random. |
| M8 | LDA projection → LightGBM (⚑F8) | LightGBM space as M4, 30 draws |
| GBDT-xcheck | LightGBM, fixed: num_leaves 255, lr 0.05, min_child_samples 100, feature_fraction 1.0, early stopping 100 | none (fixed before any run) |

Regimes: N_GC = 1.4e3 (contaminants unweighted at the true ratio) and 1e6 (capped and weighted). Learning curves also at 1e4 and 1e5. The same train and test sets are used for every method within a configuration.

## 5. Random seeds

Root seed **20261029**. `numpy.random.SeedSequence(20261029).spawn` keys are `(config_id, role, replicate)`, with role ∈ {grid-check, latent-bank-1, latent-bank-2, test, train-N, cv, bootstrap, pilot}. Torch and LightGBM seeds are derived from the same key. All keys are written to RUN_LOG.md at first use. **Pilot seeds are a separate subtree (`role=pilot`), and pilot data are never written to `results/`** (Step 2 requirement).

## 6. Storage

- `results/grids/{library}.npz`: grid fluxes + FSPS parameter header + git hash. About 0.5 GB per library.
- `results/sets/{config}/test.parquet`: float32 observed fluxes, errors, bin, class, weight, latent id. Train sets are **regenerated from seed**, not stored (disk: ~28 GB free).
- `results/scores/{config}/{method|bound-A|B|C}[_{regime}].parquet`: test-set scores aligned by row.
- `results/metrics/{config}.json`: per-cell precision, raw TP/FP counts, gates, plus `bootstrap_{config}.npz` (1000 × cells, shared resample indices so gaps are paired).
- Each results file carries the CRITERIA sha256, the AMENDMENTS.md hash, the git commit and the seed key. `analyse.py` refuses to mix files from different commits of `gccap/`.
- Budget: < 12 GB. Disk is checked before each run.

## 7. Metrics and analysis (CRITERIA §8)

- **Completeness thresholds:** set on the test set per bin from the raw GC count (GCs are unweighted). Precision = weighted TP / (weighted TP + weighted FP).
- **Gate counts:** raw TP ≥ 20,000 (⚑F9: "true GCs at the operating point" read as true positives) and raw FP ≥ 100.
- **Bootstrap:** exact multinomial resampling of each bin's test rows, 1000×, 95% percentile intervals. The same indices are used for all methods and the bound, so gaps are paired.
- `report.py` computes REACHES / HEADROOM / INCONCLUSIVE, the FRAGILE margins, V1 per depth with the single-point labels, and V3. It also lists every GATED cell and NOT RUN item, and draws the headline figure (precision at c = 0.5 vs depth, per bin, bound band = min–max over the grid).

## 8. Order of work

1. Step 2: write `grids.py`, `population.py`, `noise.py`, `features.py` and `sample.py`, plus the tests (required four + unit tests). Grid fidelity check.
2. Step 3: `bound.py` and the cross-check. Pilot timing. Then the fiducial, then the gate. **Stop if the gate fails.**
3. Step 4: methods. Step 5: analysis and report.

Commits after each working module. No push.

## 9. ⚑ Decisions (author, 2026-10-29)

| # | Issue | Decision (F2–F13: accepted as proposed) |
|---|---|---|
| F1 | Detection rule and negative fluxes | **Decided → AMENDMENTS A2:** paper's σ_m ≤ 0.5 in all bands; ordinary mags |
| F2 | IGM absorption (affects u/g at z ≳ 2.5) | Include (Madau 1995, as in FSPS) |
| F3 | Cosmology for the age cap | Planck18 |
| F4 | [Fe/H] outside isochrone grid | Keep draws, FSPS clamps, report fraction |
| F5 | IMF, abundances | Kroupa; scaled-solar, logzsol = [Fe/H] |
| F6 | Simulator = interpolated FSPS grid | Yes, with fidelity report |
| F7 | Bound(B) = Bound(C) if errors are a function of fluxes | Accept and report as a property of the model |
| F8 | M8 for 2 classes: LDA gives 1 dimension | Literal: GBDT on the 1-D LDA projection (+ bin) |
| F9 | "≥ 20,000 true GCs at the operating point" | Raw true positives |
| F11 | Pooled curves | Rank by full LR / score across bins; one global threshold |
| F12 | Nebular parameters | gas_logz = logzsol, gas_logu = −2 |
| F13 | Redshift cap | z ≤ 4 |

Conflicts with CRITERIA found while planning: **none beyond these gaps**. A1 (SSP libraries) is already amended. F1 defines what enters the sample, so it is recorded as AMENDMENTS.md A2. F2–F13 are implementation choices recorded here.
