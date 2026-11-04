"""Test and train set builders (CRITERIA §4.4, AMENDMENTS A2, PLAN §2/§7).

GCs are drawn from the true GCLF and are unweighted. Contaminants are drawn from their true populations;
the kept ones are a uniform random subsample (the first n passing draws of an iid stream) and carry
importance weights that restore the declared class ratio exactly:

    population size  N_pop = (GC draws) × (contaminant population per GC draw)       [pre-cut, §4.1/A2]
    weight           w     = N_pop / M_drawn                                          (pooled, train)
                     w_b   = N_pop × k_b / (M_drawn × n_b)                            (per bin, test)

with k_b the number of passing draws that land in bin b and n_b the number kept. Gates count raw rows.
"""
from dataclasses import dataclass

import numpy as np

from . import frozen as F
from . import population as P
from .features import i_bin
from .noise import flux_to_mag, observe_mags

CLASS_GC, CLASS_GAL, CLASS_STAR = 0, 1, 2


@dataclass
class Contaminant:
    cls: int
    draw: callable  # (rng, n) -> (latent, true mags)
    pop_per_gc_draw: float


def contaminants(sim, config, star_frac_below_24=None):
    out = [Contaminant(CLASS_GAL, sim.galaxy, P.gal_pop_per_gc_draw(config))]
    if config["stars"]:
        if star_frac_below_24 is None:
            star_frac_below_24 = sim.star_frac_below_24()
        out.append(Contaminant(CLASS_STAR, sim.star,
                               F.STAR_PER_GC * P.gc_frac_below(F.RATIO_REF_IMAX) / star_frac_below_24))
    return out


def _observe(rng, draw, n, m5):
    lat, mags = draw(rng, n)
    f, ok = observe_mags(rng, mags, m5)
    return lat, mags, f, ok


def _rows(cls, mags, f, ok, w=None):
    i_obs = flux_to_mag(f[ok, F.I_BAND])
    return {"cls": np.full(int(ok.sum()), cls, np.int8), "f_obs": f[ok].astype(np.float32),
            "mag_true": mags[ok].astype(np.float32), "bin": i_bin(i_obs).astype(np.int8),
            "weight": np.ones(int(ok.sum())) if w is None else w}


def _concat(parts):
    keys = parts[0].keys()
    return {k: np.concatenate([p[k] for p in parts]) for k in keys}


def draw_gcs(rng, sim, m5, stop, cap, chunk):
    """Draw GCs in chunks until stop(rows) or `cap` draws. Returns (rows, n_drawn)."""
    parts, n = [], 0
    while n < cap:
        k = min(chunk, cap - n)
        _, mags, f, ok = _observe(rng, sim.gc, k, m5)
        n += k
        parts.append(_rows(CLASS_GC, mags, f, ok))
        if stop(_concat(parts)):
            break
    return _concat(parts), n


def build_test(rng, sim, config, gc_per_bin, cont_per_bin, gc_draw_cap, cont_draw_cap, chunk=1_000_000,
               star_frac_below_24=None):
    """Test set: ≥ gc_per_bin GCs in every bin (or gc_draw_cap draws), contaminants per bin capped at
    cont_per_bin[b] (or cont_draw_cap draws per contaminant class)."""
    m5 = np.array(F.m5(config))
    gc, n_gc = draw_gcs(rng, sim, m5, lambda r: np.all(np.bincount(r["bin"], minlength=F.N_BINS) >= gc_per_bin),
                        gc_draw_cap, chunk)
    parts, info = [gc], {"gc_draws": n_gc, "gc_per_bin": np.bincount(gc["bin"], minlength=F.N_BINS).tolist()}
    target = np.broadcast_to(np.asarray(cont_per_bin, dtype=np.int64), (F.N_BINS,))
    for c in contaminants(sim, config, star_frac_below_24):
        kept = [[] for _ in range(F.N_BINS)]
        n_kept, k_pass, M = np.zeros(F.N_BINS, np.int64), np.zeros(F.N_BINS, np.int64), 0
        while M < cont_draw_cap and np.any(n_kept < target):
            k = min(chunk, cont_draw_cap - M)
            _, mags, f, ok = _observe(rng, c.draw, k, m5)
            M += k
            r = _rows(c.cls, mags, f, ok)
            k_pass += np.bincount(r["bin"], minlength=F.N_BINS)
            for b in range(F.N_BINS):
                if n_kept[b] >= target[b]:
                    continue
                sel = np.nonzero(r["bin"] == b)[0][: target[b] - n_kept[b]]
                kept[b].append({key: v[sel] for key, v in r.items()})
                n_kept[b] += sel.size
        n_pop = n_gc * c.pop_per_gc_draw
        for b in range(F.N_BINS):
            if n_kept[b]:
                rb = _concat(kept[b])
                rb["weight"] = np.full(n_kept[b], n_pop * k_pass[b] / (M * n_kept[b]))
                parts.append(rb)
        info[f"cls{c.cls}"] = {"draws": M, "pop": n_pop, "pass_per_bin": k_pass.tolist(),
                               "kept_per_bin": n_kept.tolist()}
    return _concat(parts), info


def build_train(rng, sim, config, n_gc, cont_cap=F.CONT_CAP_TRAIN, chunk=1_000_000, star_frac_below_24=None):
    """Pooled train set with n_gc kept GCs. Contaminants are the natural population (unweighted) unless
    that would exceed cont_cap kept rows, in which case the first cont_cap are kept and weighted."""
    m5 = np.array(F.m5(config))
    gc, n_draw = draw_gcs(rng, sim, m5, lambda r: r["cls"].size >= n_gc, np.iinfo(np.int64).max, chunk)
    # GC draws that correspond to the n_gc kept rows (ratio estimate; the last chunk overshoots)
    n_gc_draws = n_draw * n_gc / gc["cls"].size
    gc = {k: v[:n_gc] for k, v in gc.items()}
    parts, info = [gc], {"gc_draws": n_gc_draws}
    for c in contaminants(sim, config, star_frac_below_24):
        n_pop = n_gc_draws * c.pop_per_gc_draw
        got, M, n_kept, k_pass = [], 0, 0, 0
        while M < n_pop and n_kept < cont_cap:
            k = int(min(chunk, np.ceil(n_pop - M)))
            _, mags, f, ok = _observe(rng, c.draw, k, m5)
            M += k
            r = _rows(c.cls, mags, f, ok)
            k_pass += r["cls"].size
            r = {key: v[: cont_cap - n_kept] for key, v in r.items()}
            got.append(r)
            n_kept += r["cls"].size
        rc = _concat(got)
        w = n_pop * k_pass / (M * n_kept)  # = 1 up to the ceil when the natural population is drawn
        rc["weight"] = np.full(n_kept, 1.0 if n_kept == k_pass and M >= n_pop else w)
        parts.append(rc)
        info[f"cls{c.cls}"] = {"draws": M, "pop": n_pop, "kept": n_kept, "weight": float(rc["weight"][0])}
    return _concat(parts), info
