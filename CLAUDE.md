# CLAUDE.md

Pre-registered simulation study: "Do LSST colors cap GC selection?" Start by reading `HANDOFF.md`. It gives the current state, how to rebuild the environment on Sherlock, and what to do next.

Rules that bind every session (full text in `PHASE1_PROMPT.md`):
- **Never modify `CRITERIA.md`.** Its sha256 must be `2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11`. Write proposed changes to `AMENDMENTS_PROPOSED.md`; the author decides.
- Never change a threshold, gate or verdict rule (0.02, 0.8, 20,000 GCs, 100 FPs, completeness levels, 1000 bootstraps).
- Never tune simulator parameters toward the paper's numbers or any other target. Pilot runs never adjust the design.
- Log every network fetch in `DATA_LOG.md` (URL, date, version/checksum, purpose) before relying on it. Log failures too, and never substitute silently.
- Report results as found. Write "NOT RUN" or "GATED" rather than omitting anything.
- Fixed seeds (root 20261029). Commit locally; **never push**.
