"""Required Step 2 tests that need the real FSPS grids or the bound (PHASE1_PROMPT Step 2).

The reproducibility and shuffled-label tests are in test_units.py. The plausibility bounds below were
declared on 2026-10-30 before any grid existed (logged in RUN_LOG.md). The test reports the range and
never adjusts anything.
"""
import json

import numpy as np
import pytest

from gccap import frozen as F
from gccap.grids import grid_path, load_grid
from gccap.population import draw_gc, gc_coords
from gccap.seeds import rng

PLAUSIBLE = {"u-g": (0.7, 2.2), "g-r": (0.2, 1.0), "r-i": (0.0, 0.6), "i-z": (-0.2, 0.5), "z-y": (-0.3, 0.4)}


@pytest.mark.parametrize("library", list(F.LIBRARIES))
def test_gc_noise_free_color_range(library, record_property):
    if not grid_path(library, "gc").exists():
        pytest.skip(f"{library} GC grid not built")
    g = load_grid(library, "gc")
    for sigma in (F.GC_FEH_SIGMA, F.GC_FEH_SIGMA_WIDE):
        lat = draw_gc(rng("fiducial", "pilot", 21), 200000, sigma)
        dm = g.interp(gc_coords(lat))
        rep = {}
        for k, name in enumerate(PLAUSIBLE):
            c = dm[:, k] - dm[:, k + 1]
            rep[name] = [float(c.min()), float(np.percentile(c, 0.5)), float(np.percentile(c, 99.5)), float(c.max())]
        print(library, sigma, json.dumps(rep))
        record_property(f"{library}_sigma{sigma}", rep)
        for name, (lo, hi) in PLAUSIBLE.items():
            assert np.all(np.isfinite(dm))
            assert lo <= rep[name][0] and rep[name][3] <= hi, (library, sigma, name, rep[name])


def test_bound_nondecreasing_with_depth():
    pytest.skip("NOT RUN: needs gccap/bound.py (Step 3 module); required before Step 3 results")
