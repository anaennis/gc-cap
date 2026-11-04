"""GBDT cross-check of the bound (PLAN §3 "Cross-check (gate)", §4 GBDT-xcheck row).

One LightGBM model per (configuration, feature set, N_GC), N_GC ∈ {1e6, 1e7}. Hyperparameters are fixed
(PLAN §4), not searched. Bin membership is a categorical feature (CRITERIA §3); contaminant importance
weights are sample weights. Early stopping uses a separate validation set (seed key (config, train-N, 1),
N_GC/10 GCs; RUN_LOG 2026-11-04). Scores are thresholded per bin on the shared test set (metrics.py).
"""
import numpy as np
import lightgbm as lgb

from . import frozen as F
from . import sample, seeds
from .features import feature_set

PARAMS = {  # PLAN §4, fixed before any run
    "objective": "binary",
    "num_leaves": 255,
    "learning_rate": 0.05,
    "min_child_samples": 100,
    "feature_fraction": 1.0,
    "verbose": -1,
}
N_ESTIMATORS_MAX = 5000  # as M4–M6
EARLY_STOPPING = 100
VAL_FRACTION = 10  # validation N_GC = N_GC // VAL_FRACTION
SETS = ("A", "B", "C")


def train_key(config_id, n_gc, replicate=0):
    return (config_id, f"train-N{n_gc:.0e}", replicate)


def design(rows, fset, m5):
    """Feature matrix: the set's columns plus the observed-i bin as the last (categorical) column."""
    x = feature_set(fset, rows["f_obs"].astype(np.float64), m5)
    return np.column_stack([x, rows["bin"]]).astype(np.float32)


def dataset(rows, fset, m5, reference=None):
    x = design(rows, fset, m5)
    y = (rows["cls"] == sample.CLASS_GC).astype(np.int8)
    return lgb.Dataset(x, y, weight=rows["weight"], categorical_feature=[x.shape[1] - 1],
                       reference=reference, free_raw_data=True)


def build_sets(sim, config_id, config, n_gc, star_frac_below_24=None, rngs=None):
    """(train, val) rows. `rngs` = (train rng, val rng) overrides the production keys (pilot runs)."""
    if rngs is None:
        rngs = tuple(seeds.rng(*train_key(config_id, n_gc, rep)) for rep in (0, 1))
    tr, tr_info = sample.build_train(rngs[0], sim, config, n_gc, star_frac_below_24=star_frac_below_24)
    va, va_info = sample.build_train(rngs[1], sim, config, n_gc // VAL_FRACTION,
                                     star_frac_below_24=star_frac_below_24)
    return tr, va, {"train": tr_info, "val": va_info}


def fit(train_rows, val_rows, fset, m5, seed, threads):
    dtr = dataset(train_rows, fset, m5)
    dva = dataset(val_rows, fset, m5, reference=dtr)
    params = dict(PARAMS, seed=seed, num_threads=threads)
    booster = lgb.train(params, dtr, num_boost_round=N_ESTIMATORS_MAX, valid_sets=[dva],
                        callbacks=[lgb.early_stopping(EARLY_STOPPING, verbose=False)])
    return booster, {"best_iteration": int(booster.best_iteration),
                     "val_logloss": float(booster.best_score["valid_0"]["binary_logloss"])}


def score(booster, rows, fset, m5):
    return booster.predict(design(rows, fset, m5), num_iteration=booster.best_iteration)
