"""Noise model (CRITERIA §4.1, PLAN §2) and catalog inclusion (AMENDMENTS A2).

Fluxes are in nJy (AB: m = 31.4 - 2.5 log10 f). Per band, σ_bg = f(m5)/5. True-flux variance
s² = σ_bg² + (κ F)² with κ = 0.4 ln10 × 0.01 (0.01 mag floor in quadrature). Observed f = F + N(0, s²).
Reported error uses the observed flux: s_obs² = σ_bg² + (κ f)², σ_m = 1.0857 s_obs / f.
A source is kept only if f > 0 and σ_m ≤ 0.5 in all six bands.
"""
import math

import numpy as np

from . import frozen as F

AB_ZP_NJY = 31.4
KAPPA = 0.4 * math.log(10) * F.CAL_FLOOR_MAG


def mag_to_flux(m):
    return 10 ** (-0.4 * (np.asarray(m) - AB_ZP_NJY))


def flux_to_mag(f):
    return AB_ZP_NJY - 2.5 * np.log10(f)


def sigma_bg(m5):
    return mag_to_flux(np.asarray(m5, dtype=np.float64)) / 5.0


def true_sigma(F_true, m5, kappa=KAPPA):
    return np.sqrt(sigma_bg(m5) ** 2 + (kappa * F_true) ** 2)


def observe(rng, F_true, m5, kappa=KAPPA):
    return F_true + true_sigma(F_true, m5, kappa) * rng.standard_normal(F_true.shape)


def reported_sigma_mag(f_obs, m5, kappa=KAPPA):
    s_obs = np.sqrt(sigma_bg(m5) ** 2 + (kappa * f_obs) ** 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(f_obs > 0, F.MAG_ERR_CONST * s_obs / f_obs, np.inf)


def passes_cut(f_obs, m5, kappa=KAPPA):
    return np.all(reported_sigma_mag(f_obs, m5, kappa) <= F.SIGMA_M_MAX, axis=1)


def observe_mags(rng, mags_true, m5, kappa=KAPPA):
    """True magnitudes -> (observed flux, pass mask)."""
    f = observe(rng, mag_to_flux(mags_true), m5, kappa)
    return f, passes_cut(f, m5, kappa)
