"""Arm S star bank (CRITERIA §4.3, DATA_LOG #25)."""
import numpy as np

from gccap import frozen as F
from gccap import population as P


def test_star_bank_loads():
    bank = P.load_star_bank()
    assert bank.shape == (113_429, 6)
    assert np.all(np.isfinite(bank))
    assert bank[:, F.I_BAND].max() <= 27.5


def test_star_ratio_normalisation():
    sim = P.Simulator(F.CONFIGS["arm_S"], None, None, P.load_star_bank())
    n = sim.star_pop_per_gc_draw()
    # N_star(i<24) per GC draw must equal STAR_PER_GC × N_GC(i<24) per GC draw
    assert np.isclose(n * sim.star_frac_below_24(), F.STAR_PER_GC * P.gc_frac_below(F.RATIO_REF_IMAX))
    lat, mags = sim.star(np.random.default_rng(0), 1000)
    assert mags.shape == (1000, 6) and np.array_equal(lat["i_true"], mags[:, F.I_BAND])
