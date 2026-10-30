"""LSST v1.9.2 synthetic AB photometry, FSPS-exact Calzetti dust and Madau (1995) IGM (PLAN F2).

Band fluxes are mean f_nu weighted by T(λ)/λ (AB convention). Only colors are used downstream (magnitudes
are set by the GCLF and number counts), so distance and (1+z) factors that are equal in all bands are dropped.

Redshifting, IGM and band integration are one linear map per redshift: F_b(z) = Σ_k S_k M[z, k, b] for a
rest-frame spectrum S on the FSPS wavelength grid. IGM is applied on the rest grid before redshifting, in
the same order as FSPS compsp.f90.
"""
import numpy as np

from .frozen import BANDS, THROUGHPUTS_DIR, THROUGHPUTS_SHA256, sha256_file


def load_throughputs(check=True):
    """Return (wavelength_AA, T[6, n]) on the common file grid."""
    waves, trans = None, []
    for b in BANDS:
        path = THROUGHPUTS_DIR / f"total_{b}.dat"
        if check and sha256_file(path) != THROUGHPUTS_SHA256[b]:
            raise RuntimeError(f"{path} sha256 mismatch")
        d = np.loadtxt(path)
        w = d[:, 0] * 10.0  # nm -> Å
        if waves is None:
            waves = w
        elif not np.array_equal(w, waves):
            raise RuntimeError("throughput files are on different wavelength grids")
        trans.append(d[:, 1])
    return waves, np.array(trans)


def band_weights(wave_obs, trans):
    """W[j, b] such that F_b = Σ_j f_nu(λ_j) W[j, b] (trapezoid in λ, weight T/λ, normalised)."""
    dl = np.gradient(wave_obs)
    w = (trans / wave_obs * dl).T
    return w / w.sum(axis=0, keepdims=True)


def calzetti_fsps(lam):
    """FSPS attn_curve dust_type=2 (Calzetti et al. 2000), per unit dust2. Ported from attn_curve.f90."""
    lam = np.asarray(lam, dtype=np.float64)
    x = 1e4 / lam
    cal = np.where(
        lam > 6300.0,
        1.17 * (-1.857 + 1.04 * x) + 1.78,
        1.17 * (-2.156 + 1.509 * x - 0.198 * x**2 + 0.011 * x**3) + 1.78,
    )
    cal = cal / 0.44 / 4.05
    # FSPS: w63 = locate(cal00, 0); cal00(w63+1:) = 0 when the curve crosses zero (long wavelengths)
    neg = np.nonzero(cal <= 0.0)[0]
    if neg.size:
        cal[neg[0]:] = 0.0
    return cal


_LYW = np.array([1215.67, 1025.72, 972.537, 949.743, 937.803, 930.748, 926.226, 923.150, 920.963,
                 919.352, 918.129, 917.181, 916.429, 915.824, 915.329, 914.919, 914.576])
_LYC = np.array([0.0036, 0.0017, 0.0011846, 0.0009410, 0.0007960, 0.0006967, 0.0006236, 0.0005665,
                 0.0005200, 0.0004817, 0.0004487, 0.0004200, 0.0003947, 0.000372, 0.000352, 0.0003334,
                 0.00031644])


def igm_transmission(lam_rest, z, factor=1.0):
    """exp(-tau_IGM) on the rest grid. Ported from FSPS igm_absorb.f90 (applied only for z > 0)."""
    lam = np.asarray(lam_rest, dtype=np.float64)
    if z <= 1e-30:  # FSPS: only if zred > tiny_number
        return np.ones_like(lam)
    n = lam.size
    z1 = 1.0 + z
    lobs = lam * z1
    lylim, a_metal = 911.75, 0.0017
    xc = lobs / lylim
    tau = np.zeros(n)
    for i, (lw, lc) in enumerate(zip(_LYW, _LYC)):
        vv = min(max(int(np.searchsorted(lam, lw, side="right")), 1), n)
        tau[:vv] += lc * (lobs[:vv] / lw) ** 3.46
        if i == 0:
            tau[:vv] += a_metal * (lobs[:vv] / lw) ** 1.68
    if lam[0] < lylim:
        vv = min(max(int(np.searchsorted(lam, lylim, side="right")), 1), n)
        x = xc[:vv]
        tau[:vv] += (0.25 * x**3 * (z1**0.46 - x**0.46) + 9.4 * x**1.5 * (z1**0.18 - x**0.18)
                     - 0.7 * x**3 * (x ** (-1.32) - z1 ** (-1.32)) - 0.023 * (z1**1.68 - x**1.68))
    vmax = int(np.argmax(tau))
    tau[:vmax + 1] = tau[vmax]
    return np.exp(-tau * factor)


def redshift_matrix(wave_rest, z, wave_obs, W, igm=True):
    """M[k, b]: band fluxes at redshift z from a rest-frame f_nu spectrum on wave_rest."""
    lr = wave_obs / (1.0 + z)
    k = np.clip(np.searchsorted(wave_rest, lr, side="right") - 1, 0, wave_rest.size - 2)
    t = np.clip((lr - wave_rest[k]) / (wave_rest[k + 1] - wave_rest[k]), 0.0, 1.0)
    M = np.zeros((wave_rest.size, W.shape[1]))
    np.add.at(M, k, (1.0 - t)[:, None] * W)
    np.add.at(M, k + 1, t[:, None] * W)
    if igm:
        M *= igm_transmission(wave_rest, z)[:, None]
    return M


def redshift_matrices(wave_rest, zgrid, igm=True):
    wave_obs, trans = load_throughputs()
    W = band_weights(wave_obs, trans)
    return np.stack([redshift_matrix(wave_rest, z, wave_obs, W, igm=igm) for z in zgrid])


DM_FLOOR = 40.0  # band flux floored at 1e-16 of the i flux (IGM-blanked bands); such sources fail A2


def colors_rel_i(F):
    """F[..., 6] band fluxes -> m_b - m_i (6 values, i entry is 0)."""
    from .frozen import I_BAND
    Fi = F[..., I_BAND:I_BAND + 1]
    ratio = np.maximum(F / Fi, 10 ** (-0.4 * DM_FLOOR))
    return -2.5 * np.log10(ratio)
