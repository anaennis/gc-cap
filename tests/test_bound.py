"""Bound tests: pruned likelihood vs brute force, bank vs population priors, Set B injectivity (PLAN F7),
and the required "bound non-decreasing as depth improves" pilot (needs the real grids; GPU if available)."""
import math

import numpy as np
import pytest
from scipy.special import logsumexp

from gccap import bound, features, metrics, noise, population, sample, seeds
from gccap import frozen as F
from gccap.grids import grid_path, load_grid


def test_logp_matches_brute_force():
    rng = np.random.default_rng(5)
    m5 = np.array(F.m5(F.FIDUCIAL))
    Ft = noise.mag_to_flux(rng.uniform(19, 25, (3000, 6)))
    bank = bound.Bank(Ft)
    lik = bound.Likelihood(bank, m5, lat_chunk=700)
    f = noise.observe(rng, noise.mag_to_flux(rng.uniform(19, 25, (300, 6))), m5)
    got, ess = lik.logp(f, obj_chunk=64)
    s = noise.true_sigma(bank.F, m5)
    ll = (-0.5 * ((f[:, None, :] - bank.F[None]) / s[None]) ** 2 - np.log(s)[None] - 0.5 * math.log(2 * math.pi)).sum(-1)
    want = logsumexp(ll, axis=1) - math.log(bank.F.shape[0])
    assert np.allclose(got, want, rtol=0, atol=1e-6)  # pruning at 7σ loses < e^-24 of the mass
    assert np.all(ess >= 1 - 1e-9)


def test_bank_matches_population():
    g = bound.gc_bank_latents(200_000, F.GC_FEH_SIGMA, 1)
    p = population.draw_gc(np.random.default_rng(2), 200_000, F.GC_FEH_SIGMA)
    for k in g:
        assert abs(g[k].mean() - p[k].mean()) < 0.01 * max(1, p[k].std()) and abs(g[k].std() / p[k].std() - 1) < 0.01
    g = bound.gal_bank_latents(200_000, F.PZ_Z0, F.COUNT_SLOPE, 3)
    p = population.draw_galaxy(np.random.default_rng(4), 200_000, F.PZ_Z0, F.COUNT_SLOPE)
    for k in g:
        assert abs(g[k].mean() - p[k].mean()) < 0.01 * p[k].std() and abs(g[k].std() / p[k].std() - 1) < 0.01, k


def test_set_B_injective():
    """At fixed colors, every color error rises strictly with m_i, so x_B determines f (PLAN F7)."""
    m5 = np.array(F.m5(F.FIDUCIAL))
    rng = np.random.default_rng(6)
    off = rng.uniform(-1, 2, (500, 6))
    off[:, F.I_BAND] = 0
    mi = np.linspace(15, 28, 400)
    err = np.stack([features.color_errors(noise.mag_to_flux(off + m), m5) for m in mi])  # [400, 500, 5]
    assert np.all(np.diff(err, axis=0) > 0)


def _pilot_bound(sim, cfg, label):
    rng = seeds.rng(label, "pilot", 31)
    t, _ = sample.build_test(rng, sim, cfg, gc_per_bin=20_000, cont_per_bin=60_000, gc_draw_cap=3_000_000,
                             cont_draw_cap=30_000_000, chunk=1_000_000)
    gc_b, cont_b = bound.make_banks(sim, cfg, seeds.int_seed(label, "pilot", 32), n_gc=200_000, n_gal=800_000)
    m5 = np.array(F.m5(cfg))
    sc, _ = bound.score_C(t["f_obs"].astype(np.float64), bound.Likelihood(gc_b, m5), bound.Likelihood(cont_b, m5))
    return t, sc


@pytest.mark.skipif(not grid_path("mist_miles", "galaxy").exists(), reason="grids not built")
def test_bound_nondecreasing_with_depth(record_property):
    """Required test (Step 2 / §7 ii), Set C on a fixed-seed pilot at Δ = −1, 0, +1. CI-aware (PLAN §3):
    a decrease fails only if the 95% CI of the difference excludes zero. Pilot cells need ≥ 1,000 raw TP."""
    gcg, galg = load_grid("mist_miles", "gc"), load_grid("mist_miles", "galaxy")
    res = {}
    for d in (-1.0, 0.0, 1.0):
        cfg = dict(F.FIDUCIAL, delta=d)
        t, sc = _pilot_bound(population.Simulator(cfg, gcg, galg), cfg, f"pilot_depth{d:+.1f}")
        for b in range(F.N_BINS):
            s = t["bin"] == b
            is_gc = t["cls"][s] == 0
            p, tp, fp = metrics.precision_at(sc[s], is_gc, t["weight"][s], 0.5)
            boot = metrics.bootstrap_precision(sc[s], is_gc, t["weight"][s], 0.5,
                                               seeds.seed_sequence(f"pilot_depth{d:+.1f}", "pilot", 33 + b), 200)
            res[(d, b)] = (p, tp, fp, boot)
    checked = 0
    for b in range(F.N_BINS):
        for lo, hi in ((-1.0, 0.0), (0.0, 1.0)):
            p0, tp0, _, b0 = res[(lo, b)]
            p1, tp1, _, b1 = res[(hi, b)]
            print(f"bin {F.BIN_LABELS[b]} Δ {lo:+.1f}->{hi:+.1f}: P {p0:.4f} (TP {tp0}) -> {p1:.4f} (TP {tp1})")
            if min(tp0, tp1) < 1000:
                continue
            diff_hi = np.nanquantile(b1 - b0, 0.975)
            assert diff_hi >= 0, (F.BIN_LABELS[b], lo, hi, p0, p1)
            checked += 1
    record_property("cells_checked", checked)
    assert checked >= 4
