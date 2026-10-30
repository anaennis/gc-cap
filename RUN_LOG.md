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

## 2026-10-29 — CRITERIA.md frozen
- Commit: **bd254bab8548038ad89a93c67b110d5cbcf4269e** ("Freeze CRITERIA.md (Phase 1 pre-registration)", 2026-10-29 13:30:20 -0700). Pushed by the author to git@github.com:anaennis/gc-cap.git.
- CRITERIA.md git blob: `ff5b3abcdcf15675f05836efd577e23372fbb205`. sha256: `2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11`.
- Every later run re-checks this sha256 before computing and refuses to run if it differs.

## 2026-10-29 — Environment setup
- `.venv` (uv, Python 3.11.3): numpy 2.4.6, scipy 1.17.1, scikit-learn 1.9.1, lightgbm 4.7.0, torch 2.15.0 (MPS available: True), pandas 3.1.0, pyarrow 26.0.0, matplotlib 3.11.2, pytest 9.2.0. Full pins are in `requirements.lock`. Packages come from PyPI via uv.
- FSPS source cloned to `ext/fsps` (DATA_LOG #12), which will be `SPS_HOME`. Disk free after the clone: ~30 GiB.
- python-fsps is **not yet installed**. Its build flags depend on the SSP-library decision (AMENDMENTS_PROPOSED P12). **BLOCKED on author.**

## 2026-10-29 — python-fsps builds (AMENDMENTS.md A1)
- Wrapper: python-fsps 0.5.0 sdist (DATA_LOG #13). Its bundled FSPS source (`05b5e55`) was **replaced by the FSPS `b6600ff` src/** (identical except the C3K nzinit 11→13 fix; DATA_LOG #15), so code and `SPS_HOME` data match.
- Build env: `SDKROOT=$(xcrun --show-sdk-path)` was required (Homebrew gfortran 13.1 linker error "library 'System' not found" otherwise). `SPS_HOME=/Users/anaennis/Documents/gc-cap/ext/fsps`.
- `.venv`: `FFLAGS="-DMIST=1 -DC3K_LR=0 -DMILES=1"`. sp.libraries = (mist, miles, DL07). Wavelengths 91 Å–1e8 Å, 5994 points. Isochrone Z grid: 13 values, 5.85e-5–0.0585.
- `.venv-padova`: `FFLAGS="-DMIST=0 -DPADOVA=1 -DC3K_LR=1 -DMILES=0"`; same Python deps as `requirements.lock`. sp.libraries = (pdva, c3k_lr, DL07). Wavelengths 100 Å–1e8 Å, 1936 points. Isochrone Z grid: 22 values, 2e-4–0.03.
- Smoke test (not a simulation): an old SSP and a delayed-tau + Calzetti + nebular spectrum at z = 0.5 return finite spectra in both builds. **Nebular emission is available** (§4.3).
- Throughputs v1.9.2 sha256: total_g.dat=f8935b3a5514e436aea45895369f568bfcc57a682852b0abe3292fd754a7094f total_i.dat=ed05e3432509322d8cfb60ee4baf6b8bf1c08fa5a0f011ffee22838c325a9985 total_r.dat=7c2e6d39c57b8d36f664caf1087320af76cd098c382ccb5214e2830096f9a311 total_u.dat=d8fb220fed913551eb1ae5744a49e145d62aa2fd97786b515f30d20e13223b37 total_y.dat=f10cc09307ef535c323d9af473b4c4c8dc5905cbf50f91eea1a07cbb38008a20 total_z.dat=66f6a80ace390130e444eabaa59bb9837bbfed6b57af299b6c2cf27a53230c52 

## 2026-10-29 — Hand-off to Sherlock
- Author decision: Steps 2–5 (grids, simulator, tests, bound, methods, report) all run on Stanford Sherlock. Every production result comes from that one platform. The laptop python-fsps builds above were smoke-tested only and are not used for any result.
- No simulation code written and no results produced on the laptop.
- Added `HANDOFF.md` (rebuild procedure + acceptance check), `CLAUDE.md`, and `PHASE1_PROMPT.md` (author's original instructions, verbatim). PLAN §3 device wording updated (CUDA on Sherlock); this is an implementation detail and changes no design choice.

## 2026-10-29 — Sherlock: storage layout
- Author decision: `ext/` and `results/` live in the repo on `$SCRATCH` (`$SCRATCH/gc-cap`). The work will finish within 90 days; results are logged elsewhere afterwards and the scratch copy deleted. The author accepts that scratch is unbacked-up and purged.
- Python venvs go in `$HOME` (Sherlock does not allow environments on `$SCRATCH`). `$HOME` had ~5.5 GB free at this time; `$GROUP_HOME` was 99% full; no `$OAK`.
- Fetches and builds run in Slurm jobs (`scripts/slurm/`), not on the login node.

## 2026-10-29 — Sherlock: Python version
- Author decision: use the Sherlock module `python/3.12.1` (not 3.11). No results were produced on the laptop, so nothing has to match it. Toolchain modules: gcc/14.2.0, cmake/3.31.4. Venvs: stdlib `venv` + pip, no uv.
- To fit `$HOME` (~5.5 GB free), torch is installed only in the fiducial venv. `.venv-padova` only builds the second SSP grid and gets the lock minus torch and its dependencies. Each venv's pins are written to `requirements.sherlock.<name>.lock`.
- Build job 50193601 (`scripts/slurm/build_env.sbatch`), which runs after fetch job 50193512 succeeds.

## 2026-10-30 — Sherlock: jobs moved to kipac
- Author decision: run on the `kipac` partition instead of `normal`. Jobs 50193512/50193601 had been pending on priority in `normal` for about 23 h and never ran, so they were cancelled.
- Resubmitted: fetch job 50322152, then build job 50322154 (afterok:50322152). Both are in `kipac`.
