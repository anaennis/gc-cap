"""Feature sets (CRITERIA §3) and observed-i bins (§4.5). Inputs are observed fluxes of kept sources."""
from itertools import combinations

import numpy as np

from . import frozen as F
from .noise import KAPPA, flux_to_mag, reported_sigma_mag

ADJ = [(k, k + 1) for k in range(5)]
ALL15 = list(combinations(range(6), 2))


def observed_mags(f_obs):
    return flux_to_mag(f_obs)


def colors(mags, pairs=ADJ):
    return np.column_stack([mags[:, a] - mags[:, b] for a, b in pairs])


def color_errors(f_obs, m5, pairs=ADJ, kappa=KAPPA):
    s = reported_sigma_mag(f_obs, m5, kappa)
    return np.column_stack([np.hypot(s[:, a], s[:, b]) for a, b in pairs])


def i_bin(i_obs):
    """0..5 for <21, 21-22, 22-23, 23-24, 24-25, >25 (edges belong to the upper bin)."""
    return np.digitize(i_obs, F.BIN_EDGES)


def feature_set(name, f_obs, m5):
    m = observed_mags(f_obs)
    if name == "A":
        return colors(m)
    if name == "A15":
        return colors(m, ALL15)
    if name == "B":
        return np.hstack([colors(m), color_errors(f_obs, m5)])
    if name == "C":
        return np.hstack([colors(m), color_errors(f_obs, m5), m[:, [F.I_BAND]]])
    raise ValueError(name)
