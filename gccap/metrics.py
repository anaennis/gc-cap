"""Precision at fixed completeness, gates and bootstrap (CRITERIA §8, PLAN §7).

Thresholds are set on the test set from raw GC counts (GCs are unweighted): the operating point keeps the
top ceil(c × N_GC) GCs by score, together with every contaminant scoring at least as high as the last kept
GC. Precision uses importance weights; gates use raw counts (TP ≥ 20,000 true positives, PLAN F9; FP ≥ 100).
"""
import numpy as np

from . import frozen as F


def _sorted(score, is_gc, weight):
    o = np.argsort(-np.asarray(score), kind="stable")
    return np.asarray(is_gc, bool)[o], np.asarray(weight, np.float64)[o], np.asarray(score)[o]


def _operating(gc_s, w_s, sc_s, c, counts=None):
    cnt = np.ones(gc_s.size) if counts is None else counts
    ngc = cnt * gc_s
    cum_gc = np.cumsum(ngc)
    if cum_gc.size == 0 or cum_gc[-1] == 0:  # empty cell (or no GCs in a resample)
        return np.nan, 0, 0
    k = int(np.ceil(c * cum_gc[-1]))
    if k == 0:
        return np.nan, 0, 0
    j = int(np.searchsorted(cum_gc, k))  # position of the k-th GC
    j = int(np.searchsorted(-sc_s, -sc_s[j], side="right")) - 1  # include ties with the threshold score
    sl = slice(0, j + 1)
    cont = ~gc_s[sl]
    tp_raw = cum_gc[j]
    fp_raw = (cnt[sl] * cont).sum()
    wtp = (cnt[sl] * w_s[sl] * gc_s[sl]).sum()
    wfp = (cnt[sl] * w_s[sl] * cont).sum()
    return wtp / (wtp + wfp), int(round(tp_raw)), int(round(fp_raw))


def precision_at(score, is_gc, weight, c):
    """(precision, raw TP, raw FP) at completeness c."""
    return _operating(*_sorted(score, is_gc, weight), c)


def gate(tp_raw, fp_raw):
    return tp_raw >= F.GATE_MIN_TP and fp_raw >= F.GATE_MIN_FP


def bootstrap_counts(seed_seq, n, n_boot=F.N_BOOT):
    """Exact multinomial resample counts, one [n] vector per resample. Resample r always uses child seed r
    of `seed_seq`, so every method and the bound see the same resamples (paired gaps)."""
    for r in range(n_boot):  # explicit child keys: SeedSequence.spawn is stateful and would break pairing
        child = np.random.SeedSequence(seed_seq.entropy, spawn_key=tuple(seed_seq.spawn_key) + (r,))
        yield np.random.Generator(np.random.PCG64(child)).multinomial(n, np.full(n, 1.0 / n))


def bootstrap_precision(score, is_gc, weight, c, seed_seq, n_boot=F.N_BOOT):
    o = np.argsort(-np.asarray(score), kind="stable")
    gc_s, w_s, sc_s = np.asarray(is_gc, bool)[o], np.asarray(weight, np.float64)[o], np.asarray(score)[o]
    if o.size == 0:
        return np.full(n_boot, np.nan)
    return np.array([_operating(gc_s, w_s, sc_s, c, cnt[o])[0]
                     for cnt in bootstrap_counts(seed_seq, o.size, n_boot)])


def ci(samples, level=F.CI_LEVEL):
    a = (1 - level) / 2
    return tuple(np.nanquantile(samples, [a, 1 - a]))


def weighted_prior(is_gc, weight):
    is_gc = np.asarray(is_gc, bool)
    return weight[is_gc].sum() / weight.sum()
