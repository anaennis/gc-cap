"""Monte Carlo likelihood-ratio Bayes bound (CRITERIA §7, PLAN §3).

Latent banks are scrambled-Sobol draws mapped through the same prior CDFs as population.py. Each latent l
carries true fluxes F_l. Under the noise model the observed-flux density of a class is

    p(f | class) = (1/L) Σ_l Π_b N(f_b; F_lb, s_b(F_lb)²),   s² = σ_bg² + (κF)²

which is defined on the pre-cut population, so the A2 cut (a function of f only) needs no correction and
the ratio of these densities is the pooled LR directly (PLAN F11).

Set C (= observed fluxes) score: log p(f|GC) − log p(f|cont).
Set B: color errors rise strictly with m_i at fixed colors, so f ↔ x_B is one-to-one and the Set B score
       equals the Set C score (PLAN F7; checked in tests).
Set A: p(c, bin | class) = ∫_bin p(f(c, m)) |J(c, m)| 1[A2 cut] dm over observed i, by Gauss–Legendre
       (24 nodes per 1-mag sub-interval). Open bins use declared finite ranges (A_RANGE_*).

Latent sums are pruned to latents whose true i flux can lie within 7 s of the observed i flux, and
accumulated with streaming log-sum-exp in float64 on the best available device (cuda → mps → cpu).
"""
import math

import numpy as np
import torch
from scipy.stats import norm, gamma, qmc

from . import frozen as F
from . import population as P
from .noise import KAPPA, mag_to_flux, sigma_bg

N_SIGMA = 7.0
GL_NODES = 24
A_RANGE_LO = 15.0  # lower limit of the "<21" bin integral (GCLF turnover − 5.3σ)
A_RANGE_HI = 28.0  # upper limit of the ">25" bin integral (counts end at 27, plus noise)
LOG2PI = math.log(2 * math.pi)


def device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


# ----------------------------------------------------------------------------- latent banks
def _sobol(d, n, seed):
    s = qmc.Sobol(d, scramble=True, seed=np.random.default_rng(seed))
    return s.random_base2(int(math.ceil(math.log2(n))))[:n]


def gc_bank_latents(n, feh_sigma, seed):
    u = _sobol(4, n, seed)
    mu = np.where(u[:, 0] < F.GC_FEH_MIX, F.GC_FEH_MU[0], F.GC_FEH_MU[1])
    return {"feh": mu + feh_sigma * norm.ppf(u[:, 1]),
            "age_gyr": F.GC_AGE_GYR[0] + u[:, 2] * (F.GC_AGE_GYR[1] - F.GC_AGE_GYR[0]),
            "i_true": F.GCLF_MI + F.DIST_MOD + F.GCLF_SIGMA * norm.ppf(u[:, 3])}


def gal_bank_latents(n, z0, slope, seed):
    u = _sobol(6, n, seed)
    z = gamma.ppf(u[:, 0] * gamma.cdf(F.Z_MAX, 3.0, scale=z0), 3.0, scale=z0)  # truncated at Z_MAX
    lo, hi = 10 ** (slope * F.GAL_I_RANGE[0]), 10 ** (slope * F.GAL_I_RANGE[1])
    lt = np.log10(F.GAL_TAU_GYR)
    return {"z": z, "age_gyr": F.GAL_AGE_MIN_GYR + u[:, 1] * (P.t_universe_gyr(z) - F.GAL_AGE_MIN_GYR),
            "tau_gyr": 10 ** (lt[0] + u[:, 2] * (lt[1] - lt[0])),
            "logz": F.GAL_LOGZ[0] + u[:, 3] * (F.GAL_LOGZ[1] - F.GAL_LOGZ[0]),
            "av": F.GAL_AV[0] + u[:, 4] * (F.GAL_AV[1] - F.GAL_AV[0]),
            "i_true": np.log10(lo + u[:, 5] * (hi - lo)) / slope}


class Bank:
    """True fluxes of one class's latents (or a weighted mixture of classes), sorted by true i flux."""

    def __init__(self, F_true, log_w=None):
        o = np.argsort(F_true[:, F.I_BAND])
        self.F = np.ascontiguousarray(F_true[o])
        n = self.F.shape[0]
        self.log_w = np.full(n, -math.log(n)) if log_w is None else np.asarray(log_w)[o]
        self.Fi = self.F[:, F.I_BAND]

    @classmethod
    def mixture(cls, banks, fractions):
        Fs = np.concatenate([b.F for b in banks])
        lw = np.concatenate([b.log_w + math.log(fr) for b, fr in zip(banks, fractions)])
        return cls(Fs, lw)


def make_banks(sim, config, bank_seed, n_gc=1_000_000, n_gal=4_000_000):
    """Latent banks for one configuration. bank_seed: int from seeds.int_seed(config, 'latent-bank-k')."""
    lat = gc_bank_latents(n_gc, config["feh_sigma"], bank_seed)
    gc = Bank(mag_to_flux(P.true_mags(sim.gc_grid.interp(P.gc_coords(lat)), lat["i_true"])))
    lat = gal_bank_latents(n_gal, config["z0"], config["slope"], bank_seed + 1)
    gal = Bank(mag_to_flux(P.true_mags(sim.gal_grid.interp(P.gal_coords(lat)), lat["i_true"])))
    cont = gal
    if config["stars"]:
        if not hasattr(sim, "star_bank_flux"):
            raise NotImplementedError("arm S star bank (TRILEGAL) not loaded yet")
        star = Bank(sim.star_bank_flux())
        n_g, n_s = P.gal_pop_per_gc_draw(config), sim.star_pop_per_gc_draw()
        cont = Bank.mixture([gal, star], [n_g / (n_g + n_s), n_s / (n_g + n_s)])
    return gc, cont


# ----------------------------------------------------------------------------- likelihood
class Likelihood:
    def __init__(self, bank, m5, dev=None, lat_chunk=200_000):
        self.dev = dev or device()
        self.bank = bank
        self.F = torch.as_tensor(bank.F, dtype=torch.float64, device=self.dev)
        self.log_w = torch.as_tensor(bank.log_w, dtype=torch.float64, device=self.dev)
        sbg = torch.as_tensor(sigma_bg(m5), dtype=torch.float64, device=self.dev)
        s = torch.sqrt(sbg**2 + (KAPPA * self.F) ** 2)
        self.inv_s = 1.0 / s
        self.log_norm = self.log_w - torch.log(s).sum(1) - 3.0 * LOG2PI  # 6 bands × ½ log 2π
        self.sbg_i = float(sigma_bg(m5)[F.I_BAND])
        self.lat_chunk = lat_chunk

    def window(self, fi_lo, fi_hi):
        """Latent index range whose true i flux can be within N_SIGMA s of [fi_lo, fi_hi]."""
        lo = (fi_lo - N_SIGMA * self.sbg_i) / (1 + N_SIGMA * KAPPA)
        hi = (fi_hi + N_SIGMA * self.sbg_i) / (1 - N_SIGMA * KAPPA)
        return int(np.searchsorted(self.bank.Fi, lo, "left")), int(np.searchsorted(self.bank.Fi, hi, "right"))

    def logp(self, f, obj_chunk=512):
        """log p(f | class) and the effective sample size of the latent terms, for f[N, 6] (numpy)."""
        f = np.asarray(f, dtype=np.float64)
        o = np.argsort(f[:, F.I_BAND])
        out, ess = np.full(f.shape[0], -np.inf), np.zeros(f.shape[0])
        for s in range(0, f.shape[0], obj_chunk):
            idx = o[s:s + obj_chunk]
            fc = torch.as_tensor(f[idx], dtype=torch.float64, device=self.dev)
            a, b = self.window(f[idx, F.I_BAND].min(), f[idx, F.I_BAND].max())
            m = torch.full((idx.size,), -math.inf, dtype=torch.float64, device=self.dev)
            s1 = torch.zeros(idx.size, dtype=torch.float64, device=self.dev)
            s2 = torch.zeros_like(s1)
            for c in range(a, b, self.lat_chunk):
                e = min(b, c + self.lat_chunk)
                z = (fc[:, None, :] - self.F[None, c:e]) * self.inv_s[None, c:e]
                ll = self.log_norm[None, c:e] - 0.5 * (z * z).sum(-1)
                mc = torch.maximum(m, ll.max(1).values)
                fin = torch.isfinite(mc)
                scale = torch.where(fin, torch.exp(m - mc), torch.zeros_like(m))
                ex = torch.exp(ll - torch.where(fin, mc, torch.zeros_like(mc))[:, None])
                s1 = s1 * scale + ex.sum(1)
                s2 = s2 * scale**2 + (ex * ex).sum(1)
                m = mc
            out[idx] = (m + torch.log(s1)).cpu().numpy()
            ess[idx] = (s1**2 / s2).cpu().numpy()
        return out, ess


# ----------------------------------------------------------------------------- scores
def score_C(f, lik_gc, lik_cont):
    lg, eg = lik_gc.logp(f)
    lc, ec = lik_cont.logp(f)
    return lg - lc, {"ess_gc": eg, "ess_cont": ec}


def bin_intervals(b):
    edges = (A_RANGE_LO,) + F.BIN_EDGES + (A_RANGE_HI,)
    lo, hi = edges[b], edges[b + 1]
    cuts = np.unique(np.concatenate([np.arange(math.ceil(lo), math.floor(hi) + 1), [lo, hi]]))
    return list(zip(cuts[:-1], cuts[1:]))


def score_A(f, bins, lik_gc, lik_cont, m5):
    """Set A score per object: log ∫_bin p(f(c,m)|GC)|J| − log ∫_bin p(f(c,m)|cont)|J| over observed i."""
    from .noise import passes_cut
    x, wgl = np.polynomial.legendre.leggauss(GL_NODES)
    mags = 31.4 - 2.5 * np.log10(np.asarray(f, np.float64))
    off = mags - mags[:, [F.I_BAND]]  # colors fix m_b - m_i
    out = np.full(f.shape[0], np.nan)
    ess = {"gc": np.full(f.shape[0], np.inf), "cont": np.full(f.shape[0], np.inf)}
    for b in np.unique(bins):
        sel = np.nonzero(bins == b)[0]
        nodes, logw = [], []
        for lo, hi in bin_intervals(int(b)):
            nodes.append(0.5 * (hi - lo) * x + 0.5 * (hi + lo))
            logw.append(np.log(0.5 * (hi - lo) * wgl))
        nodes, logw = np.concatenate(nodes), np.concatenate(logw)
        K = nodes.size
        mi = np.repeat(nodes[None, :], sel.size, 0)  # [n, K]
        fk = mag_to_flux(off[sel, None, :] + mi[:, :, None]).reshape(-1, 6)
        logJ = np.log(0.4 * math.log(10) * fk).sum(1)
        ok = passes_cut(fk, np.asarray(m5))
        terms = {}
        for name, lik in (("gc", lik_gc), ("cont", lik_cont)):
            lp = np.full(fk.shape[0], -np.inf)
            e = np.full(fk.shape[0], np.inf)
            if ok.any():
                lp[ok], e[ok] = lik.logp(fk[ok])
            t = (lp + logJ + np.tile(logw, sel.size)).reshape(sel.size, K)
            t[~ok.reshape(sel.size, K)] = -np.inf
            terms[name] = np.logaddexp.reduce(t, axis=1)
            top = np.argmax(t, axis=1)  # ESS at the node that dominates the integral
            ess[name][sel] = e.reshape(sel.size, K)[np.arange(sel.size), top]
        out[sel] = terms["gc"] - terms["cont"]
    return out, {"ess_gc_top_node": ess["gc"], "ess_cont_top_node": ess["cont"]}
