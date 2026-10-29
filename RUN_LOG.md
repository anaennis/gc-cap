# RUN_LOG.md

## 2026-10-29 — Step 0 preflight (no compute run)

### CRITERIA.md commit status: NOT COMMITTED
- `/Users/anaennis/Documents/gc-cap` is not a git repository. `CRITERIA.md` has no commit hash.
- Its own header says "DRAFT until committed", and [FILL] items must be filled before the commit.
- **No compute may run.** I did not initialise git or commit, because committing would freeze a file that still has unfilled [FILL] items.

### Unfilled [FILL] items (all 8 remain)
1. §4.1 Filters: LSST ugrizy throughput source URL, version/commit and date.
2. §4.1 Depths: DR1-like 5σ depths per band, with source and date. The declared fallback is the two presets from Table 3 of arXiv:2512.17644v2. Either way, the paper or the depth source must be fetched and logged.
3. §4.2 GC [Fe/H]: confirm or fill the bimodal parameters against a published Fornax GC color distribution, and log the source.
4. §4.3 Galaxy priors table (tau, age, metallicity, dust) with sources.
5. §4.3 Galaxy p(z), fiducial (and §5 alternative), with sources.
6. §4.3 Number-count slope: value and source.
7. §5 Second SSP library (the choice).
8. §5 Number-count slope alternative value.

Related item that is not marked [FILL]: M0 says "hyperparameter search as in the paper's description". That needs the paper's text, which means a logged fetch.

### Environment check
| Item | Result |
|---|---|
| OS / arch | macOS (Darwin 25.6.0), arm64 |
| CPU | Apple M2, 8 cores |
| RAM | 16 GB |
| GPU | Apple M2 integrated, 10-core, Metal 4. No CUDA. PyTorch is not installed, so MPS is unverified. |
| Disk free | **35 GiB** (volume 92% full) |
| Python | `/usr/bin/python3` 3.9.6 (system). `/opt/homebrew/bin/python3` 3.11.3. python3.10 is also present. `uv` is available. |
| Installed pkgs (system py) | numpy 1.26.4, matplotlib 3.9.4. **Missing:** scipy, scikit-learn, xgboost, lightgbm, torch, jax, pandas, astroML, sedpy, speclite, extreme_deconvolution |
| python-fsps | **NOT INSTALLED** |
| SPS_HOME | **UNSET**. No FSPS source tree found in `~/fsps` or `~/src/fsps`. |
| Compilers | gfortran (Homebrew GCC 13.1.0), gcc, cmake are present. A python-fsps build is feasible. |

Nothing has been installed yet. Installing python-fsps needs network fetches: the FSPS source repo (sets `SPS_HOME`) and the python-fsps package. Each fetch will be logged in `DATA_LOG.md` before I use it.

### Second SSP library
I fetched nothing for this check. It is based on my knowledge of FSPS packaging and has not been verified against current docs.
- **FSPS with Padova isochrones + BaSeL spectra** (the fallback CRITERIA declares): these data files ship in the FSPS source repo. python-fsps has to be **rebuilt** with the compile flags switched (MIST→Padova, MILES→BaSeL), which means two separate builds or environments. Expected to be obtainable once the FSPS repo is fetched.
- **BC03**: needs a separate download from the authors' distribution site. I have not checked whether it is reachable.
- Status: **none obtained yet.** I'll log it when one is fetched.

### Result
STOPPED at Step 0: CRITERIA.md is uncommitted and 8 [FILL] items are unfilled. I also wrote design concerns to `AMENDMENTS_PROPOSED.md` for the author to decide on.

## 2026-10-29 — [FILL] items filled (still no compute)
- At the author's explicit request, Claude edited CRITERIA.md before the freeze. The edits fill all 8 [FILL] items and apply decisions P1–P11 (see AMENDMENTS_PROPOSED.md, "Resolution status"). Sources are in DATA_LOG.md #1–#11.
- No [FILL] markers remain.
- Thresholds are unchanged: 0.02, 0.8, 20,000 GCs, 100 FPs, c ∈ {0.3, 0.5, 0.7}, 1000 bootstraps.
- **Status: waiting for the author to `git init` and commit. The CRITERIA.md commit hash will be recorded here.**
