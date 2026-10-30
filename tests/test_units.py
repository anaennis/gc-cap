"""Unit tests for Step 2 modules (no FSPS needed)."""
import numpy as np
import pytest

from gccap import frozen as F
from gccap import metrics, noise, photometry, population, sample, seeds
from gccap.features import feature_set, i_bin
from gccap.grids import Grid


def test_criteria_hash():
    assert F.check_criteria() == F.CRITERIA_SHA256


def test_config_grid():
    oat = [k for k in F.CONFIGS if k not in ("fiducial", "arm_S", "paper_depth") and not k.startswith("corner")]
    assert len(oat) == 11 and sum(k.startswith("corner") for k in F.CONFIGS) == 3
    assert F.m5(F.CONFIGS["depth_p0.5"]) == tuple(m + 0.5 for m in F.DEPTH_PRESETS["SV"])
    assert F.m5(F.CONFIGS["depth_C10"]) == F.DEPTH_PRESETS["C10"]


def test_seeds_deterministic_and_distinct():
    a = seeds.rng("fiducial", "test").random(5)
    assert np.array_equal(a, seeds.rng("fiducial", "test").random(5))
    for other in (("fiducial", "pilot"), ("fiducial", "test", 1), ("feh_wide", "test")):
        assert not np.array_equal(a, seeds.rng(*other).random(5))
    with pytest.raises(ValueError):
        seeds.rng("fiducial", "nonsense")


def test_flat_fnu_has_zero_colors():
    w = np.geomspace(500, 30000, 4000)
    for z in (0.0, 0.7, 1.5):
        M = photometry.redshift_matrices(w, [z], igm=False)[0]
        assert np.allclose(photometry.colors_rel_i(np.ones(w.size) @ M), 0.0, atol=1e-10)


def test_calzetti_normalisation():
    assert abs(photometry.calzetti_fsps(np.array([5500.0]))[0] - 1.0) < 2e-3
    k = photometry.calzetti_fsps(np.geomspace(1000, 1e5, 500))
    assert np.all(np.diff(k) <= 1e-12) and k[-1] == 0.0


def test_igm():
    lam = np.geomspace(91, 1e5, 3000)
    assert np.all(photometry.igm_transmission(lam, 0.0) == 1.0)
    t = photometry.igm_transmission(lam, 3.0)
    assert np.all(t[lam > 1216] == 1.0) and t[(lam > 1100) & (lam < 1200)].max() < 1.0
    # Lyman-continuum absorption: transmission drops across 911.75 Å (Madau 1995 gives ~e^-1.5 at z=3)
    assert t[lam < 900].max() < t[(lam > 912) & (lam < 1000)].min()


def test_grid_interp_exact_for_multilinear():
    ax = [np.array([0.0, 1.0, 3.0]), np.array([-1.0, 2.0])]
    X, Y = np.meshgrid(*ax, indexing="ij")
    dm = np.stack([2 * X + 3 * Y + X * Y] * 6, axis=-1)
    g = Grid(("x", "y"), ax, dm)
    pts = np.array([[0.5, 0.0], [2.0, 1.5], [3.0, -1.0], [0.0, 2.0]])
    want = 2 * pts[:, 0] + 3 * pts[:, 1] + pts[:, 0] * pts[:, 1]
    assert np.allclose(g.interp(pts)[:, 0], want)
    assert np.allclose(g.interp(np.array([[5.0, 9.0]]))[:, 0], 2 * 3 + 3 * 2 + 6)  # clamped


def test_noise_cut_equivalent_to_snr():
    m5 = np.array(F.m5(F.FIDUCIAL))
    rng = np.random.default_rng(1)
    f = noise.observe(rng, noise.mag_to_flux(rng.uniform(20, 26, (20000, 6))), m5)
    s_obs = np.sqrt(noise.sigma_bg(m5) ** 2 + (noise.KAPPA * f) ** 2)
    snr_ok = np.all(f / s_obs >= F.MAG_ERR_CONST / F.SIGMA_M_MAX, axis=1)
    assert np.array_equal(noise.passes_cut(f, m5), snr_ok)


def test_noise_statistics():
    m5 = np.full(6, 24.0)
    rng = np.random.default_rng(2)
    F0 = noise.mag_to_flux(np.full((200000, 6), 24.0))
    d = noise.observe(rng, F0, m5) - F0
    want = np.sqrt((noise.mag_to_flux(24.0) / 5) ** 2 + (noise.KAPPA * F0[0]) ** 2)
    assert np.allclose(d.std(axis=0) / want, 1.0, atol=0.01)


def test_bins_and_features():
    assert list(i_bin(np.array([20.9, 21.0, 22.5, 24.99, 25.0, 26]))) == [0, 1, 2, 4, 5, 5]
    m5 = np.array(F.m5(F.FIDUCIAL))
    f = noise.mag_to_flux(np.array([[22.0, 21.5, 21.2, 21.0, 20.9, 20.8]]))
    assert np.allclose(feature_set("A", f, m5), [[0.5, 0.3, 0.2, 0.1, 0.1]])
    assert feature_set("A15", f, m5).shape == (1, 15) and feature_set("C", f, m5).shape == (1, 11)


def test_draw_distributions():
    rng = np.random.default_rng(3)
    z = population.draw_redshift(rng, 400000, 0.30)
    assert z.max() <= 4.0 and abs(z.mean() - 0.9) < 0.01
    m = population.draw_count_mag(rng, 400000, 0.31)
    assert abs((m < 24).mean() - population.gal_frac_below(24, 0.31)) < 0.003
    g = population.draw_galaxy(rng, 100000, 0.30, 0.31)
    assert np.all(g["age_gyr"] <= population.t_universe_gyr(g["z"]) + 1e-9) and g["age_gyr"].min() >= 0.1


def test_weights_restore_ratio(toy_sim):
    """Deep, floorless noise: everything passes the cut, so weighted counts must reproduce the pre-cut
    ratio N_gal(i<24)/N_GC(i<24) = 34 using observed i as a proxy (σ ~ 1e-3 mag)."""
    cfg = dict(F.FIDUCIAL, depth="SV", delta=12.0)
    sim = population.Simulator(cfg, toy_sim.gc_grid, toy_sim.gal_grid)
    rng = seeds.rng("unit", "pilot")
    t, info = sample.build_test(rng, sim, cfg, gc_per_bin=0, cont_per_bin=60000, gc_draw_cap=400000,
                                cont_draw_cap=4_000_000, chunk=200000)
    i_obs = noise.flux_to_mag(t["f_obs"][:, F.I_BAND].astype(float))
    gc = (t["cls"] == 0) & (i_obs < 24)
    gal = (t["cls"] == 1) & (i_obs < 24)
    r = t["weight"][gal].sum() / gc.sum()
    assert abs(r / 34.0 - 1) < 0.02, r


def test_reproducible_from_seed(toy_sim):
    """Required test: simulation is reproducible from seed."""
    out = []
    for _ in range(2):
        t, info = sample.build_test(seeds.rng("fiducial", "pilot", 7), toy_sim, toy_sim.config, gc_per_bin=500,
                                    cont_per_bin=500, gc_draw_cap=100000, cont_draw_cap=200000, chunk=20000)
        out.append((t, info))
    for k in out[0][0]:
        assert np.array_equal(out[0][0][k], out[1][0][k])
    assert out[0][1] == out[1][1]
    t3, _ = sample.build_test(seeds.rng("fiducial", "pilot", 8), toy_sim, toy_sim.config, gc_per_bin=500,
                              cont_per_bin=500, gc_draw_cap=100000, cont_draw_cap=200000, chunk=20000)
    assert not np.array_equal(t3["f_obs"][:100], out[0][0]["f_obs"][:100])


def test_shuffled_label_null(toy_sim):
    """Required test: a score independent of class gives precision = within-bin weighted prior (in CI)."""
    t, _ = sample.build_test(seeds.rng("fiducial", "pilot", 11), toy_sim, toy_sim.config, gc_per_bin=20000,
                             cont_per_bin=60000, gc_draw_cap=2_000_000, cont_draw_cap=4_000_000)
    rng = seeds.rng("fiducial", "pilot", 12)
    tested = 0
    for b in range(F.N_BINS):
        s = t["bin"] == b
        if (t["cls"][s] == 0).sum() < 2000 or (t["cls"][s] != 0).sum() < 2000:
            continue
        is_gc, w = t["cls"][s] == 0, t["weight"][s]
        score = rng.permutation(feature_set("A", t["f_obs"][s].astype(float), np.array(F.m5(F.FIDUCIAL)))[:, 1])
        prior = metrics.weighted_prior(is_gc, w)
        for c in F.COMPLETENESS:
            boot = metrics.bootstrap_precision(score, is_gc, w, c, seeds.seed_sequence("fiducial", "pilot", 13),
                                               n_boot=200)
            lo, hi = metrics.ci(boot)
            assert lo <= prior <= hi, (b, c, prior, lo, hi)
        tested += 1
    assert tested >= 2


def test_precision_at_known():
    score = np.array([5, 4, 3, 2, 1.0])
    is_gc = np.array([1, 0, 1, 0, 1], bool)
    w = np.array([1, 2, 1, 2, 1.0])
    p, tp, fp = metrics.precision_at(score, is_gc, w, 0.5)  # 2 of 3 GCs -> rows 0..2
    assert (tp, fp) == (2, 1) and abs(p - 2 / 4) < 1e-12
