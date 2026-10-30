# HANDOFF.md — continuing Phase 1 on Sherlock

Written 2026-10-29 at the end of the laptop session (last commit before this file: `0b235a0`). This is for the Claude Code session that continues the work on Stanford's Sherlock cluster. It is self-contained, but the files it points to are authoritative and this file is not.

> **Update 2026-10-30 (Sherlock session 1) — read this first.** Environment built and accepted (§3 done; job 50338921). Step 2 code written and tested; Step 3 `bound.py` written. Details in RUN_LOG.md from "Sherlock env build accepted" onward.
> - **Open jobs to check** (`sacct -j 50347664,50358339,50359220`):
>   - 50347664 `gccap-grids-mist_miles` (kipac): MIST grids are built; the 2,000-draw fidelity check was still running. When done, copy its numbers from `logs/build_grids_gccap-grids-mist_miles_50347664.out` / `results/grids/mist_miles_fidelity.json` into RUN_LOG next to padova's, and commit the JSON.
>   - 50358339 `gccap-gpucheck` (owners, A100_SXM4): confirms torch module on the production GPU; log hardware line in RUN_LOG (§3.7).
>   - 50359220 `gccap-tests` (owners, A100): full suite incl. the **required depth-monotonicity test** (`tests/test_bound.py`). If it fails for a non-bug reason, stop and ask (§8).
> - Author decisions this session: kipac/owners only; production GPU `-C GPU_SKU:A100_SXM4`; AMENDMENTS A3 (draw caps, from P14); P15 option 1 (Padova GC u−g tail accepted, test strict-xfail).
> - Grids (`results/grids/*.npz`, ~2.3 GB each) are git-ignored; rebuild with `scripts/slurm/build_grids.sbatch <library>`.
> - Next: after the tests pass, pilot throughput for the bound (log it), GBDT cross-check (`methods`), TRILEGAL fetch for arm S (log in DATA_LOG first), then the fiducial bound and the validity gate.
> - Session rules unchanged: read /etc/agents/AGENTS.md at session start; never push (the author pushes).

## 1. Read first, in this order
1. `PHASE1_PROMPT.md`: the author's original instructions, verbatim. The hard rules there bind you.
2. `CRITERIA.md`: the frozen design. **Never edit it.** sha256 must be `2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11`. Check it before any compute and refuse to run if it differs.
3. `AMENDMENTS.md`: A1 (SSP libraries) and A2 (catalog inclusion: σ_m ≤ 0.5 mag in all six bands). These override CRITERIA where they apply.
4. `PLAN.md`: the implementation plan. Every ⚑ decision (F1–F13) is already decided by the author.
5. `RUN_LOG.md`, `DATA_LOG.md`, `AMENDMENTS_PROPOSED.md`: history. P1–P12 are all resolved; don't reopen them.

## 2. Where things stand
| Step | Status |
|---|---|
| 0 Preflight | Done on the laptop. All [FILL] items are filled; CRITERIA frozen at `bd254ba`. |
| 1 PLAN.md | Done; all decisions made. |
| 2 Simulator + tests | **Not started. No simulation code exists yet.** |
| 3 Bound + gate | Not started |
| 4 Methods | Not started |
| 5 Report | Not started |

**No simulation has run and no results exist anywhere.** The laptop built both python-fsps variants and ran a smoke test (finite spectra only). Those builds aren't in git and won't be used.

**Platform decision (author, 2026-10-29):** Steps 2–5 all run on Sherlock, and every production result comes from that one platform. Build the grids on Sherlock too, so the simulator and everything downstream share a build. Record this in RUN_LOG.md when you start.

## 3. Rebuild the environment on Sherlock
`ext/` and `.venv*/` are git-ignored, so you need to recreate them. **Log every fetch in DATA_LOG.md before relying on it**, continuing the numbering from #17.

Before you start, ask the author where `ext/` (~3.5 GB) and `results/` (≤ ~20 GB) should live. They should go in persistent storage such as `$GROUP_HOME` or `$OAK`, **not `$SCRATCH`, which is purged**. Do builds and heavy compute in jobs (`sh_dev` or `sbatch`), not on the login node.

1. **Toolchain:** load gcc (gfortran) and cmake through `module`, then record the module versions. Use Python 3.11 to match the laptop (3.11.3), via `uv python install 3.11` (log the fetch) or a Sherlock module.
2. **FSPS source and data (`SPS_HOME`):** get `https://github.com/cconroy20/fsps` at exactly `b6600ff3a983e0c35ec722e961dfdc89c97c37f2`. For example: `git init ext/fsps && cd ext/fsps && git fetch --depth 1 https://github.com/cconroy20/fsps b6600ff3a983e0c35ec722e961dfdc89c97c37f2 && git checkout FETCH_HEAD`. Verify the hash with `git rev-parse HEAD`. It's 3.4 GB.
3. **Throughputs:** fetch `https://github.com/lsst/throughputs` tag v1.9.2 (commit `0bcec2a6bec62e442a094df738ec2a9fdff844c5`) into `ext/throughputs`. The `baseline/total_{u,g,r,i,z,y}.dat` sha256 values must match RUN_LOG.md ("python-fsps builds" section). Stop if any differs.
4. **python-fsps 0.5.0 sdist:** get it from `https://files.pythonhosted.org/packages/source/f/fsps/fsps-0.5.0.tar.gz`. sha256 must be `3d57a45d0a196a7a4e3de77254e4bdbe8018e09f0911c1d57cd68af25512f861`.
   - Extract two copies, one per build.
   - In each copy, **replace `src/fsps/libfsps/src/` with `ext/fsps/src/`**. The bundled FSPS is `05b5e55`, which reads only 11 of the 13 C3K metallicities (DATA_LOG #15). Confirm with `diff -r` that the replaced directory matches `ext/fsps/src` exactly.
5. **Two venvs** with uv. Install the pins from `requirements.lock`, except torch, which needs a Linux CUDA build: use the closest version to 2.15.0 that matches the node's CUDA, and record the exact build. Add `astropy` (needed for Planck18; PLAN ⚑F3) and log it. Then build python-fsps from each prepared sdist with `SPS_HOME` set:
   - `.venv`: `FFLAGS="-DMIST=1 -DC3K_LR=0 -DMILES=1"` (fiducial)
   - `.venv-padova`: `FFLAGS="-DMIST=0 -DPADOVA=1 -DC3K_LR=1 -DMILES=0"`
   - Linux doesn't need the macOS `SDKROOT` workaround.
   - Write `requirements.lock` (Sherlock) as a separate file, e.g. `requirements.sherlock.lock`. Keep the laptop lock.
6. **Build acceptance check:** these must match the laptop values in RUN_LOG.md. If any differs, stop and report.
   | | `.venv` | `.venv-padova` |
   |---|---|---|
   | `sp.libraries` | `(mist, miles, DL07)` | `(pdva, c3k_lr, DL07)` |
   | Wavelength points | 5994 (91 Å–1e8 Å) | 1936 (100 Å–1e8 Å) |
   | Isochrone Z values | 13 (5.85e-5–0.0585) | 22 (2e-4–0.03) |
   | Nebular emission | works | works |
7. **Hardware:** record the node, GPU model, driver, CUDA, CPU and RAM in RUN_LOG.md. Pick one GPU type for all production runs (Sherlock supports GPU feature constraints; check with `sh_node_feat` / `sinfo`) and use it every time.

## 4. Things already decided (don't reopen)
- **Seeds:** root `20261029`, `SeedSequence` keys `(config_id, role, replicate)` (PLAN §5). Pilot data use their own `role=pilot` subtree and **never** go into `results/`.
- **Device:** PLAN §3 says "torch on MPS". On Sherlock that means CUDA. It's an implementation detail, not a design change, but note it in RUN_LOG. Write device-agnostic code (cuda → mps → cpu).
- **Hyperparameter ranges:** fixed in PLAN §4, logged before any run. Don't widen or narrow them after seeing results.
- **The <21 bin is GATED by construction** (CRITERIA §4.5). With A2 at SV depth, faint bins are also expected to be sparse or GATED. That's an expected result, not a bug to fix.

## 5. Work still to do (PLAN §8), with stop points
1. **Step 2:**
   - Write `gccap/` modules (`frozen`, `seeds`, `photometry`, `grids`, `population`, `noise`, `features`, `sample`) and `tests/`.
   - Build the two grids into `results/grids/`.
   - Run the grid fidelity check (2,000 draws per class against direct FSPS) and report it. Don't tune.
   - Required tests: shuffled-label null; noise-free GC color range (report the range, no auto-adjusting); bound non-decreasing with depth on a fixed-seed pilot; reproducibility from seed.
   - All must pass before Step 3.
   - If a pilot shows a bug, fix it and log it. If it shows a design concern, write it to `AMENDMENTS_PROPOSED.md` and stop.
2. **Stars (arm S):** fetch the TRILEGAL v1.6 catalog per CRITERIA §4.3. The site's TLS certificate failed verification on the laptop (DATA_LOG #11, needed `curl -k`). If it still does, log it. If TRILEGAL is unreachable, log that and mark arm S NOT RUN. Don't substitute another star model.
3. **Step 3:**
   - Bound per PLAN §3, then the GBDT cross-check at N_GC = 1e6 and 1e7.
   - Measure pilot throughput first and log it. Timing never changes the design.
   - **If the validity gate fails anywhere, stop and report the failing cells to the author.**
4. **Step 4:** methods M0–M8 in both regimes, using the same splits throughout.
5. **Step 5:** `REPORT.md` generated by `report.py` from saved results. List every GATED and NOT RUN item explicitly.

## 6. Slurm and logging conventions
- **Partition: always `kipac` (or `owners`), never `normal`.** Jobs in `normal` never start because of low fairshare (author, 2026-10-30). `owners` jobs can be preempted, so keep them restartable.
- Put job scripts in `scripts/slurm/` and commit them. Each job should:
  - check the CRITERIA sha256 first;
  - write its Slurm job ID, node, GPU, git commit and seed keys into its results file header;
  - append a line to RUN_LOG.md.
- Check partition time limits with `sinfo`/`scontrol`; don't assume them. Make jobs restartable per configuration, so a timeout only loses one cell.
- Never mix results from different `gccap/` commits (PLAN §6).

## 7. Git
Commit locally with clear messages after each working module, ending with the attribution line used in earlier commits. **Do not push.** The author pushes.

## 8. When to stop and ask the author
- Storage locations or GPU allocation are unclear.
- The build acceptance check (§3.6) fails.
- A required fetch fails and there's no declared fallback.
- A required Step 2 test fails for a reason that isn't a plain bug.
- The bound validity gate fails.
- You think a frozen rule is wrong. In that case write to `AMENDMENTS_PROPOSED.md` and don't act on it.
