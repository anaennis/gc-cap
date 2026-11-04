"""Step 3 pilot: GBDT cross-check timing and a code check, fiducial config (PLAN §3).
Pilot seeds only (role=pilot, replicates 51-53); writes to logs/, never results/. Timing never changes
the design. Usage: pilot_xcheck.py OUT.json N_GC THREADS"""
import json
import sys
import time

import numpy as np

from gccap import metrics, population, sample, seeds, xcheck
from gccap import frozen as F
from gccap.grids import load_grid

F.check_criteria()
out, n_gc, threads = sys.argv[1], int(float(sys.argv[2])), int(sys.argv[3])
label, cfg = "pilot_xcheck", dict(F.FIDUCIAL)
m5 = np.array(F.m5(cfg))
rec = {"config": cfg, "n_gc": n_gc, "threads": threads, "params": xcheck.PARAMS,
       "seed_keys": [[label, "pilot", r] for r in (51, 52, 53)]}

def tick(name, t0):
    rec[name + "_s"] = round(time.time() - t0, 1)
    print(name, rec[name + "_s"], "s", flush=True)

sim = population.Simulator(cfg, load_grid("mist_miles", "gc"), load_grid("mist_miles", "galaxy"))
t0 = time.time()
tr, va, info = xcheck.build_sets(sim, label, cfg, n_gc,
                                 rngs=(seeds.rng(label, "pilot", 51), seeds.rng(label, "pilot", 52)))
tick("build_train_val", t0)
rec["sizes"] = {"train": int(tr["cls"].size), "val": int(va["cls"].size)}
rec["set_info"] = json.loads(json.dumps(info, default=float))

t0 = time.time()
te, _ = sample.build_test(seeds.rng(label, "pilot", 53), sim, cfg, gc_per_bin=20_000, cont_per_bin=60_000,
                          gc_draw_cap=3_000_000, cont_draw_cap=30_000_000)
tick("build_test", t0)
rec["n_test"] = int(te["cls"].size)

is_gc = te["cls"] == sample.CLASS_GC
for fset in xcheck.SETS:
    t0 = time.time()
    booster, fit_info = xcheck.fit(tr, va, fset, m5, seeds.int_seed(label, "pilot", 51), threads)
    tick(f"fit_{fset}", t0)
    s = xcheck.score(booster, te, fset, m5)
    cells = {}
    for b in range(F.N_BINS):
        sel = te["bin"] == b
        for c in F.COMPLETENESS:
            p, tp, fp = metrics.precision_at(s[sel], is_gc[sel], te["weight"][sel], c)
            cells[f"{F.BIN_LABELS[b]}|{c}"] = [None if np.isnan(p) else round(float(p), 4), tp, fp]
    rec[f"set_{fset}"] = dict(fit_info, cells=cells)
    print(fset, json.dumps(rec[f"set_{fset}"]), flush=True)
json.dump(rec, open(out, "w"), indent=1)
