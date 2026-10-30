"""Priors and latent draws (CRITERIA §4.2, §4.3; PLAN §2). Returns latent parameters and true AB magnitudes.

Class normalisation (§4.1, §4.3, A2): ratios are defined on the true-magnitude populations before the
catalog cut, for true i < 24. `gal_pop_per_gc_draw` converts a number of GC draws into the matching
(pre-cut) galaxy population size.
"""
import numpy as np
from scipy.special import ndtr

from . import frozen as F

# --- GCs ---------------------------------------------------------------------------------------


def draw_gc(rng, n, feh_sigma):
    comp = rng.random(n) < F.GC_FEH_MIX
    feh = np.where(comp, F.GC_FEH_MU[0], F.GC_FEH_MU[1]) + feh_sigma * rng.standard_normal(n)
    age_gyr = rng.uniform(*F.GC_AGE_GYR, n)
    i_true = F.GCLF_MI + F.DIST_MOD + F.GCLF_SIGMA * rng.standard_normal(n)
    return {"feh": feh, "age_gyr": age_gyr, "i_true": i_true}


def gc_coords(lat):
    return np.column_stack([lat["feh"], np.log10(lat["age_gyr"] * 1e9)])


def gc_frac_below(m):
    return float(ndtr((m - F.GCLF_MI - F.DIST_MOD) / F.GCLF_SIGMA))


# --- galaxies ----------------------------------------------------------------------------------
_TUNIV = None


def t_universe_gyr(z):
    """Planck18 age of the universe (PLAN F3), tabulated on 0 ≤ z ≤ 4 and interpolated."""
    global _TUNIV
    if _TUNIV is None:
        from astropy.cosmology import Planck18
        zz = np.linspace(0.0, F.Z_MAX, 4001)
        _TUNIV = (zz, Planck18.age(zz).to_value("Gyr"))
    return np.interp(z, *_TUNIV)


def draw_redshift(rng, n, z0):
    """p(z) = (1/2z0)(z/z0)^2 exp(-z/z0) = Gamma(3, z0), truncated at z ≤ 4 by redrawing (PLAN F13)."""
    z = rng.gamma(3.0, z0, n)
    bad = z > F.Z_MAX
    while bad.any():
        z[bad] = rng.gamma(3.0, z0, int(bad.sum()))
        bad = z > F.Z_MAX
    return z


def draw_count_mag(rng, n, slope, lo=F.GAL_I_RANGE[0], hi=F.GAL_I_RANGE[1]):
    """dN/dm ∝ 10^(slope m) on [lo, hi], inverse CDF."""
    a, b = 10 ** (slope * lo), 10 ** (slope * hi)
    return np.log10(a + rng.random(n) * (b - a)) / slope


def gal_frac_below(m, slope, lo=F.GAL_I_RANGE[0], hi=F.GAL_I_RANGE[1]):
    m = min(max(m, lo), hi)
    return (10 ** (slope * m) - 10 ** (slope * lo)) / (10 ** (slope * hi) - 10 ** (slope * lo))


def draw_galaxy(rng, n, z0, slope):
    z = draw_redshift(rng, n, z0)
    u = rng.random(n)
    age = F.GAL_AGE_MIN_GYR + u * (t_universe_gyr(z) - F.GAL_AGE_MIN_GYR)
    tau = 10 ** rng.uniform(np.log10(F.GAL_TAU_GYR[0]), np.log10(F.GAL_TAU_GYR[1]), n)
    logz = rng.uniform(*F.GAL_LOGZ, n)
    av = rng.uniform(*F.GAL_AV, n)
    i_true = draw_count_mag(rng, n, slope)
    return {"z": z, "age_gyr": age, "tau_gyr": tau, "logz": logz, "av": av, "i_true": i_true}


def gal_coords(lat):
    return np.column_stack([lat["logz"], np.log10(lat["tau_gyr"]), np.log10(lat["age_gyr"]),
                            lat["av"], lat["z"]])


def gal_pop_per_gc_draw(config):
    """Pre-cut galaxy population size per pre-cut GC draw, from N_gal(i<24)/N_GC(i<24) = ratio."""
    return (config["gal_per_gc"] * gc_frac_below(F.RATIO_REF_IMAX)
            / gal_frac_below(F.RATIO_REF_IMAX, config["slope"]))


# --- true magnitudes ---------------------------------------------------------------------------


def true_mags(dm, i_true):
    """dm[N, 6] (m_b - m_i) + true i -> true AB magnitudes [N, 6]."""
    return dm + np.asarray(i_true)[:, None]


class Simulator:
    """Latent draws -> true magnitudes for one configuration, using the interpolated grids (PLAN F6)."""

    def __init__(self, config, gc_grid, gal_grid, star_bank=None):
        self.config, self.gc_grid, self.gal_grid, self.star_bank = config, gc_grid, gal_grid, star_bank

    def gc(self, rng, n):
        lat = draw_gc(rng, n, self.config["feh_sigma"])
        return lat, true_mags(self.gc_grid.interp(gc_coords(lat)), lat["i_true"])

    def galaxy(self, rng, n):
        lat = draw_galaxy(rng, n, self.config["z0"], self.config["slope"])
        return lat, true_mags(self.gal_grid.interp(gal_coords(lat)), lat["i_true"])

    def star(self, rng, n):
        if self.star_bank is None:
            raise RuntimeError("arm S needs the TRILEGAL star bank")
        idx = rng.integers(0, self.star_bank.shape[0], n)
        return {"bank_row": idx, "i_true": self.star_bank[idx, F.I_BAND]}, self.star_bank[idx]
