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
