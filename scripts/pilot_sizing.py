"""Test-set contaminant sizing (CRITERIA §4.4; author decision 2026-11-04, RUN_LOG session 4).

Per bin, on a fiducial pilot test set (role=pilot, replicates 61-63; never results/), the bound's Set C
operating point at c = 0.7 gives the raw fraction q_b of kept contaminants that are false positives.
Contaminants per bin = min(ceil(FP_TARGET_AT_C07 / q_lo_b), CONT_CAP_PER_BIN), with q_lo_b the 95%
one-sided Poisson lower limit of q_b (conservative: never undersizes). The same sizes are used for
every configuration. Usage: pilot_sizing.py OUT.json
"""
import json
import sys
import time

import numpy as np
import torch
from scipy.stats import chi2

from gccap import bound, metrics, population, sample, seeds
from gccap import frozen as F
from gccap.grids import load_grid

F.check_criteria()
out = sys.argv[1]
label, cfg, C = "pilot_sizing", dict(F.FIDUCIAL), 0.7
PILOT_GC_PER_BIN, PILOT_CONT_PER_BIN = 20_000, 500_000
m5 = np.array(F.m5(cfg))
rec = {"config": cfg, "c": C, "seed_keys": [[label, "pilot", r] for r in (61, 62)],
       "pilot_gc_per_bin": PILOT_GC_PER_BIN, "pilot_cont_per_bin": PILOT_CONT_PER_BIN,
       "fp_target": F.FP_TARGET_AT_C07, "cap": F.CONT_CAP_PER_BIN, "device": str(bound.device())}
if torch.cuda.is_available():
    rec["gpu"] = torch.cuda.get_device_name(0)

t0 = time.time()
sim = population.Simulator(cfg, load_grid("mist_miles", "gc"), load_grid("mist_miles", "galaxy"))
t, info = sample.build_test(seeds.rng(label, "pilot", 61), sim, cfg, PILOT_GC_PER_BIN, PILOT_CONT_PER_BIN,
                            gc_draw_cap=5_000_000, cont_draw_cap=100_000_000)
rec["test_info"] = json.loads(json.dumps(info, default=float))
gc_b, cont_b = bound.make_banks(sim, cfg, seeds.int_seed(label, "pilot", 62))
lg, lc = bound.Likelihood(gc_b, m5), bound.Likelihood(cont_b, m5)
score, _ = bound.score_C(t["f_obs"].astype(np.float64), lg, lc)
score = np.asarray(score.cpu() if torch.is_tensor(score) else score)
rec["elapsed_s"] = round(time.time() - t0, 1)

is_gc = t["cls"] == sample.CLASS_GC
bins = []
for b in range(F.N_BINS):
    sel = t["bin"] == b
    n_cont = int((sel & ~is_gc).sum())
    _, tp, fp = metrics.precision_at(score[sel], is_gc[sel], t["weight"][sel], C)
    q = fp / n_cont if n_cont else float("nan")
    q_lo = chi2.ppf(0.05, 2 * fp) / 2 / n_cont if (n_cont and fp) else 0.0
    n_req = F.CONT_CAP_PER_BIN if q_lo == 0 else int(min(np.ceil(F.FP_TARGET_AT_C07 / q_lo), F.CONT_CAP_PER_BIN))
    bins.append({"bin": F.BIN_LABELS[b], "n_gc": int((sel & is_gc).sum()), "n_cont": n_cont, "tp": tp,
                 "fp": fp, "q": q, "q_lo95": q_lo, "cont_per_bin": n_req})
    print(bins[-1], flush=True)
rec["bins"] = bins
rec["cont_per_bin"] = [x["cont_per_bin"] for x in bins]
print(json.dumps(rec["cont_per_bin"]))
json.dump(rec, open(out, "w"), indent=1)
