# CRITERIA.md: Do LSST colors cap GC selection? (Phase 1: simulation)

**Status: DRAFT until committed.** Once committed to git, this file is frozen. Changes go in `AMENDMENTS.md` (see section 9). No compute may run before the commit hash of this file is recorded in `RUN_LOG.md`.

Items marked **[FILL]** must be completed and committed *before* the first compute run. Filling them is part of the pre-registration, not an amendment.

---

## 1. Question

For unresolved extragalactic globular clusters (GCs) versus unresolved contaminants in LSST-like ugrizy photometry:

- **Q1 (bound).** What is the best precision achievable at fixed completeness using colors only, given the data-generating process? (Bayes bound, per noise bin.)
- **Q2 (methods).** Do common methods (RF, MLP, PCA, autoencoder, GBDT, noise-aware mixture) reach that bound, or is there headroom?
- **Q3 (features).** How much does each added feature set (color errors, magnitude/LF prior) move the bound?

Motivation: Schweder-Souza et al. (arXiv:2512.17644v2) report a contamination floor of ~30% at <30% completeness from ugrizY colors on Fornax data (288 test GCs, one best-F1 operating point per model, no uncertainties). This project asks whether that floor is physical, noise-driven, label-driven, or method-driven. Phase 1 does not use any Fornax data.

## 2. Scope and explicit non-claims

- Phase 1 is simulation only. It cannot establish what happens in real DR1 data (real photometric systematics, deblending, non-Gaussian errors, real label noise).
- **Assumption A1 (worst case for morphology): all contaminants are unresolved.** Morphology carries zero information in this simulation by construction. The result is a bound for the unresolved regime, not for all contaminants.
- Primary contaminant class is **background galaxies**. Foreground stars are a secondary arm (section 4.3).
- The bound is conditional on the simulator's assumptions. It is reported as a **band** over the sensitivity grid (section 5), never as a single number.
- **Galaxy redshift is drawn independently of magnitude** (single p(z) for all galaxies; section 4.3). The p(z) sensitivity axis tests this.
- **Galaxy number counts are extrapolated beyond i = 25.5** (the source is valid for 20.5 < i < 25.5). The count-slope sensitivity axis tests this.
- **GC [Fe/H] parameters are typical literature values, not fitted to Fornax.** The GC metallicity distribution varies with host mass (Fahrion et al. 2020, A&A 637, A27).
- **Galaxy SED priors are conventional broad SED-fitting priors, not a measured population.**

## 3. Features and feature sets

| Set | Inputs |
|---|---|
| **A** | 5 independent colors (u-g, g-r, r-i, i-z, z-y). The 15-color variant is used only for replication of the paper's setup (M0, M1). |
| **B** | A + per-color propagated errors |
| **C** | B + observed i-band magnitude |

The bound is computed separately for each set. "Colors only" means Set A.

Because operating points and results are per observed-i bin (sections 4.5, 8), every method and the bound use observed-i bin membership in the same way. "Colors only" therefore means Set A colors plus observed-i bin membership. The Set A bound in a bin is the likelihood ratio within that bin, using the within-bin class prior. V3 (C − A) therefore measures the magnitude information *within* a bin.

## 4. Simulator specification (frozen)

### 4.1 Common
- Filters: LSST ugrizy baseline throughputs from github.com/lsst/throughputs, `baseline/total_{u,g,r,i,z,y}.dat`, latest release tag at fetch time; as of 2026-10-29 that is v1.9.2, commit `0bcec2a6bec62e442a094df738ec2a9fdff844c5`. The exact tag and SHA used are recorded in `DATA_LOG.md`.
- Noise: Gaussian flux noise per band, constant in flux within a band (background-limited), set by 5σ depth. Plus a calibration floor of **0.01 mag** added in quadrature in each band.
- Depths: no DR1 depths are used. Two named presets from arXiv:2512.17644v2 Table 3 (operations simulations; Bianco et al. 2022, ApJS 258, 1):

  | Preset | u | g | r | i | z | y |
  |---|---|---|---|---|---|---|
  | **SV** (single visit): **fiducial, Δ = 0** | 23.8 | 24.5 | 24.0 | 23.4 | 22.7 | 22.9 |
  | **C10** (10-year coadd) | 25.6 | 26.9 | 26.9 | 26.4 | 25.6 | 24.8 |

  DR1 is assumed to lie between SV and C10. Because the bound is non-decreasing with depth (section 7 sanity test ii), NOT CAPPED at SV implies NOT CAPPED at DR1, and CAPPED at C10 implies CAPPED at DR1.
- Paper-like depth (replication only, section 8): u from FDS 5σ (24.1); g, r, i, z, y from the DES DR2 S/N = 10 limits (arXiv:2512.17644v2 Table 2) converted to 5σ by +0.753 mag (2.5 log₁₀ 2, background-limited): g 25.45, r 25.15, i 24.55, z 23.85, y 22.45. Caveat: the DES limits are for a 1.95″ aperture, while the paper's photometry used 2.92″.
- Noise axis: depth shift Δ ∈ {-1.0, -0.5, 0, +0.5, +1.0} mag applied to all bands, relative to SV (fiducial Δ = 0).
- Class balance is a parameter (section 5); fiducial GC:galaxy ratio in the paper-like range (observed i < 24) is **1:34** (paper test set: 288 GCs, 9916 galaxies).

### 4.2 GC class
- Single-age-dominated old SSPs from FSPS. Age uniform 10 to 13.5 Gyr.
- [Fe/H]: bimodal Gaussian mixture, fiducial components at -1.5 and -0.5, σ = 0.3 each, mixing fraction 0.5. These are adopted as typical literature values, not fitted to Fornax. Fahrion et al. 2020 (A&A 637, A27) find the GC metallicity distribution shape varies with host mass; the section 5 "wider [Fe/H]" axis partly covers this.
- No dust. Redshift 0.
- Apparent magnitude: Gaussian GCLF in i, turnover absolute i = -8.5, σ = 1.5, distance modulus 31.5 (Fornax; same values the paper uses). Distance modulus is a swept parameter in section 5 only through the class-balance axis; it is otherwise fixed.

### 4.3 Contaminants
- **Galaxies (primary):** FSPS delayed-tau SFH, tau, age, metallicity and dust (Calzetti-like) drawn from the declared priors below, redshifted with a declared p(z). Observed i magnitude drawn from a power-law number-count model for 21 < i < 27 with the declared slope. Nebular emission included if available in the FSPS build; if not, state so in `RUN_LOG.md`.

  | Parameter | Prior |
  |---|---|
  | tau | log-uniform, 0.1–10 Gyr |
  | age | uniform, 0.1 Gyr to the age of the universe at z |
  | log Z/Z☉ | uniform, −1.5 to +0.2 |
  | dust | Calzetti (FSPS `dust_type=2`), A_V uniform 0–2 |

  Source: conventional broad SED-fitting priors (not a measured population).
  - **p(z):** p(z) = (1/2z₀)(z/z₀)² exp(−z/z₀), the same for all galaxy magnitudes. Fiducial z₀ = 0.30 (LSST Science Book v2.0, arXiv:0912.0201, section "Galaxy Counts", i < 25 sample; mean z 0.9). Alternative z₀ = 0.215 (the i < 23 sample, within the measured range 21.5 < i < 23).
  - **Number-count slope:** dlogN/dm = 0.31 (LSST Science Book v2.0, section "Galaxy Counts": N(<i) = 46 × 10^{0.31(i−25)} arcmin⁻², from CFHTLS Deep, valid for 20.5 < i < 25.5). Used to i = 27 as an extrapolation.
- **Stars (secondary arm S):** star colors and magnitudes from **TRILEGAL v1.6** (stev.oapd.inaf.it), photometric system "LSST ugrizy, Sept 2023, total filter throughputs R1.9 (ABmags)", all other parameters at the form's defaults, recorded as submitted. Field: 10 deg² centred on NGC 1399 (α = 3.6414 h, δ = −35.4508°), split across calls if the CPU limit requires, with a limiting magnitude of i = 27.5. Simulated stars are resampled with replacement and pass through the same noise model as the other classes. Fiducial GC:star ratio **1:2.6** (paper test set: 288 GCs, 745 stars). In arm S the contaminant class is galaxies + stars at the declared ratios. Arm S reports the bound and V1–V3 as **secondary** results; primary verdicts are galaxies-only. If TRILEGAL output cannot be obtained and logged, arm S is reported as **not assessed**. It must not be silently dropped or replaced.

### 4.4 Sample sizes
- Test: ≥ 200,000 GCs per observed-i bin (bins below) in the fiducial configuration, ≥ 67,000 in other grid points (so that c = 0.3 cells can pass the 20,000-GC gate).
- Test contaminants are **subsampled per bin and importance-weighted** to restore the declared class ratio exactly. Each bin contains enough contaminants that the expected raw false-positive count at c = 0.7 under the fiducial configuration is ≥ 1,000, capped at 5 × 10⁶ contaminants per bin. Precision, bootstrap and gaps use the weights. **Gates (section 8) count raw, unweighted sources.**
- Train sizes for learning curves: N_GC ∈ {1.4e3 (paper-matched), 1e4, 1e5, 1e6}. At 1.4e3, contaminants are unweighted at the true class ratio (paper-like). At larger N_GC, contaminants are capped at min(ratio × N_GC, 5 × 10⁶) and weighted to restore the ratio.

### 4.5 Noise bins
Observed i-band magnitude bins: <21, 21-22, 22-23, 23-24, 24-25, >25. Bins use the noisy observed magnitude (available in real data), not the true one. Results are reported per bin and pooled. The < 21 bin contains galaxies only through noise scatter (counts start at i = 21) and is expected to be GATED in every configuration; this is stated in advance.

## 5. Sensitivity grid (frozen, one-at-a-time around the fiducial, plus 3 declared corners)

| Axis | Values (fiducial first) |
|---|---|
| SSP library | FSPS default (MILES + MIST) ; FSPS Padova + BaSeL (separate python-fsps build; changes isochrones and spectral library, not the synthesis code) |
| GC [Fe/H] | bimodal (-1.5, -0.5) ; wider (σ = 0.45) |
| Galaxy p(z) | z₀ = 0.30 ; z₀ = 0.215 |
| GC:galaxy ratio (i<24) | 1:34 ; 1:10 ; 1:100 |
| Depth | SV with Δ = 0 ; -1.0 ; -0.5 ; +0.5 ; +1.0 (relative to SV) ; C10 (one extra point) |
| Number-count slope | 0.31 ; 0.25 (counts flattening beyond i ≈ 25.5) |

**Corners (declared):** (a) second SSP library + wider [Fe/H] + alt p(z); (b) fiducial everything + ratio 1:100 + Δ = -1.0; (c) fiducial everything + ratio 1:10 + Δ = +1.0.

If no second SSP library is obtainable, the library-sensitivity result is **"not assessed"** and every verdict in section 8 is explicitly labeled "conditional on a single SSP library."

## 6. Methods (frozen)

| ID | Method | Feature set |
|---|---|---|
| M0 | Random forest, 15 colors (paper replication; hyperparameter search as in the paper's description) | A (15) |
| M1 | MLP, architecture as paper (10-5 hidden for 15 inputs) | A (15) |
| M2 | PCA (4 PCs) + RF | A |
| M3 | Autoencoder (latent 4, 1 hidden layer of 7, sigmoid encoder, linear decoder) + RF | A |
| M4 | Gradient-boosted trees | A |
| M5 | Gradient-boosted trees | B |
| M6 | Gradient-boosted trees | C |
| M7 | Class-conditional extreme-deconvolution Gaussian mixtures with per-source errors, likelihood-ratio classifier | B |
| M8 | LDA projection + GBDT | A |
| BOUND | Bayes-optimal likelihood ratio (section 7) | A, B, C separately |

Each method is run in two regimes: **paper-matched N_GC (1.4e3)** and **saturated N_GC (1e6)**. The difference separates data-limited from feature-limited behavior. No new methods may be added after the first compute run except via `AMENDMENTS.md`.

**Declared hyperparameters for M0/M1.** The paper does not give its ranges, so these are author-declared, and M0/M1 are "paper-like" rather than exact:
- **M0:** randomized search, 50 draws, 5-fold stratified CV, selected by GC-class F1. n_estimators {100, 200, 500, 1000}; max_depth {None, 10, 20, 30}; min_samples_split {2, 5, 10}; min_samples_leaf {1, 2, 4}; max_features {sqrt, log2, all}.
- **M1:** hidden layers 10 and 5, ReLU; single GC-vs-contaminant output. Adam, learning rate 1e-3, batch 256, up to 500 epochs, early stopping with patience 20 on validation loss, no weight decay; 5-fold stratified CV.
- **M2–M8:** search ranges are declared in `PLAN.md` and logged before any run.
- All seeds are fixed and logged in `RUN_LOG.md`.

## 7. Bayes bound (frozen procedure)

The bound for feature set X is the precision at fixed completeness of the likelihood-ratio classifier p(x | GC) / p(x | contaminant) marginalized over latent parameters, evaluated on held-out simulated data.

- **Primary estimator:** Monte Carlo marginalization using the generative model (large latent sample, Gaussian noise likelihood).
- **Cross-check:** a GBDT trained at N_GC = 1e6 and 1e7 on the same feature set, using the capped, importance-weighted contaminant scheme of section 4.4. **Bound validity gate:** the cross-check and the primary estimator must agree within **0.02 absolute precision** at every reported (bin, completeness) cell where gates in section 8 pass, and the GBDT learning curve must be flat (change < 0.01 from 1e6 to 1e7). If this gate fails, STOP: report "bound estimation unresolved," do not issue V2 or V3, and document which estimator disagrees.
- Required sanity tests (must pass before any verdict): (i) shuffled-label null gives precision = class prior; (ii) bound is non-decreasing as depth improves; (iii) bound for set C ≥ B ≥ A in every cell (within bootstrap CI); (iv) at near-zero noise the bound approaches the noise-free separability of the templates.

## 8. Metrics, gates, and verdict rules (frozen)

**Metric:** precision at completeness c ∈ {0.3, 0.5, 0.7}, per noise bin and pooled. Operating points are set by thresholding the classifier score on the test set to achieve completeness c.

**Uncertainty:** 1000 bootstrap resamples of the test set; 95% intervals.

**Effective-sample-size gates (per cell):** a (bin, c, configuration) cell is reported only if it has **≥ 20,000 true GCs** and **≥ 100 false positives** at the operating point. Cells failing a gate are marked **GATED** and excluded from all verdicts. They are never silently dropped; the REPORT lists every gated cell.

**Gap definition:** G = P_bound − P_method (absolute precision), with bootstrap CI.
- **REACHES the bound:** upper 95% CI of G ≤ **0.02**.
- **HEADROOM:** lower 95% CI of G > **0.02**.
- **INCONCLUSIVE:** otherwise.

Margin check: every REACHES/HEADROOM call is reported with its margin over the 0.02 line in units of the CI half-width. Calls with margin < 1 CI half-width are labeled **FRAGILE**.

**Reference level for "usable":** precision ≥ **0.8** at completeness ≥ 0.5. This level is an arbitrary, pre-declared reference, not a scientific threshold. All results are also reported as continuous curves.

**Verdicts:**

- **V1 (colors cap).** Using Set A bound at c = 0.5, per noise bin, **evaluated separately at each depth setting** (SV Δ = 0, each other Δ, C10):
  - **CAPPED** at that depth in a bin if the bound is below 0.8 at every non-gated grid point at that depth.
  - **NOT CAPPED** at that depth in a bin if the bound is ≥ 0.8 at every non-gated grid point at that depth.
  - **ASSUMPTION-DEPENDENT** otherwise. In that case the grid axes responsible are named.
  - At depths where only one grid point exists (every depth other than SV Δ = 0, apart from corners b and c at their depths), the call is labeled **single-point** (not tested against model assumptions).
- **V2 (methods reach the bound).** For each method and bin, REACHES / HEADROOM / INCONCLUSIVE at c = 0.5, in the saturated regime. Paper-matched regime reported alongside.
- **V3 (feature value).** Bound(B) − Bound(A) and Bound(C) − Bound(A) at c = 0.5 per bin, with CIs. "Material" means the lower CI exceeds 0.02.

**Replication check (not a gate):** M0 at fiducial settings and paper-like depth is compared with the paper's RF-15-colors result (precision ≈ 0.69, recall ≈ 0.29). Disagreement is reported, not tuned away. The simulator parameters may not be adjusted to match the paper after any compute run. The paper's classifier is 3-class (GC/galaxy/star) on real labeled data; M0 here is 2-class (or arm S combined) on simulated data, so the comparison is indicative only. It uses the paper-like depth preset (section 4.1).

## 9. Process rules

1. `CRITERIA.md` is frozen at commit. Hash recorded in `RUN_LOG.md`.
2. Every external download (throughputs, SSP libraries, stellar libraries, number-count sources) gets an entry in `DATA_LOG.md`: URL, date, version or checksum, purpose. No undeclared network fetches.
3. Any change after the first compute run goes in `AMENDMENTS.md` with: timestamp, what changed, why, and an explicit statement of whether the author had seen any results when making it. Thresholds (0.02, 0.8, gates) and verdict rules cannot be amended after results exist.
4. `REPORT.md` verdict tables are generated by a script from saved results and this file's rules. They are not hand-edited. Prose commentary is allowed but must not contradict the tables.
5. Wrong or overstated statements found later are corrected by appended, flagged notes, not silent edits.
6. Unrun declared analyses are listed in `REPORT.md` as **NOT RUN** with the reason.

## 10. Phase 2 (not declared here)

A Fornax consistency check (DES + FDS catalog; label-noise sensitivity; comparison with simulator predictions at the paper's noise level) will get its own criteria file, committed before any Fornax data is accessed. Nothing in Phase 2 may alter Phase 1 verdicts.
