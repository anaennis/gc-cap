"""Build the GC and galaxy grids for one SSP library and run the grid fidelity check (PLAN §2, F6).

Usage: python -I scripts/build_grids.py <library> <processes>
Run with that library's venv. Writes results/grids/{library}_{gc,galaxy}.npz and
results/grids/{library}_fidelity.json. The fidelity check is reported, never used to tune the grid.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

from gccap import frozen as F  # noqa: E402
from gccap import grids, population, seeds  # noqa: E402
from gccap.features import ADJ  # noqa: E402

N_CHECK = 2000


def header(library):
    return {"criteria_sha256": F.check_criteria(), "amendments_sha256": F.sha256_file(F.ROOT / "AMENDMENTS.md"),
            "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=F.ROOT, text=True).strip(),
            "slurm_job": os.environ.get("SLURM_JOB_ID"), "node": os.uname().nodename, "library": library}


def color_err(a, b):
    ca = np.column_stack([a[:, i] - a[:, j] for i, j in ADJ])
    cb = np.column_stack([b[:, i] - b[:, j] for i, j in ADJ])
    return ca - cb


def summarise(err, mask):
    e = np.abs(err[mask])
    return {"n": int(mask.sum()), "max": e.max(axis=0).round(5).tolist(),
            "p99": np.percentile(e, 99, axis=0).round(5).tolist(),
            "median": np.median(e, axis=0).round(5).tolist()}


def main(library, processes):
    grids.GRID_DIR.mkdir(parents=True, exist_ok=True)
    hdr = header(library)
    out = {}
    for kind, build in (("gc", grids.build_gc_grid), ("galaxy", grids.build_gal_grid)):
        path = grids.grid_path(library, kind)
        t0 = time.time()
        if path.exists():
            g = grids.Grid.load(path)
            print(f"{kind}: reusing {path}")
        else:
            g = build(library, processes)
            g.meta.update(hdr, build_seconds=round(time.time() - t0, 1))
            g.save(path)
            print(f"{kind}: built {path} shape {g.dm.shape} in {time.time() - t0:.0f} s")
        out[kind] = g

    # Fidelity: 2,000 prior draws per class (fiducial priors), interpolated grid vs direct FSPS
    rep = dict(hdr, seed=seeds.describe(library, "grid-check"), n_per_class=N_CHECK)
    r = seeds.rng(library, "grid-check")
    gc = population.draw_gc(r, N_CHECK, F.GC_FEH_SIGMA)
    gal = population.draw_galaxy(r, N_CHECK, F.PZ_Z0, F.COUNT_SLOPE)
    for kind, lat, coords, params in (
        ("gc", gc, population.gc_coords(gc), np.column_stack([gc["feh"], gc["age_gyr"]])),
        ("galaxy", gal, population.gal_coords(gal),
         np.column_stack([gal["logz"], gal["tau_gyr"], gal["age_gyr"], gal["av"], gal["z"]])),
    ):
        t0 = time.time()
        direct = grids.direct_fsps(kind, params, processes)
        err = color_err(out[kind].interp(coords), direct)
        ok = np.all(np.isfinite(err), axis=1)
        rep[kind] = {"colors": [f"{F.BANDS[i]}-{F.BANDS[j]}" for i, j in ADJ], "all": summarise(err, ok),
                     "nonfinite": int((~ok).sum()), "seconds": round(time.time() - t0, 1)}
        if kind == "galaxy":  # u is IGM-blanked at high z; report the A2-relevant regime separately too
            rep[kind]["z_lt_2.5"] = summarise(err, ok & (gal["z"] < 2.5))
        np.save(grids.GRID_DIR / f"{library}_fidelity_{kind}_err.npy", err)
        print(kind, json.dumps(rep[kind]))
    (grids.GRID_DIR / f"{library}_fidelity.json").write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
