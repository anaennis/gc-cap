"""Step 3 pilot: bound throughput on the fiducial config at production bank sizes (PLAN §3).
Pilot seeds only (role=pilot); writes to logs/, never results/. Timing never changes the design."""
import json
import sys
import time

import numpy as np
import torch

from gccap import bound, population, sample, seeds
from gccap import frozen as F
from gccap.grids import load_grid

F.check_criteria()
out = sys.argv[1]
label = "pilot_throughput"
cfg = dict(F.FIDUCIAL)
m5 = np.array(F.m5(cfg))
rec = {"config": cfg, "seed_keys": [[label, "pilot", r] for r in (41, 42)], "device": str(bound.device())}
if torch.cuda.is_available():
    rec["gpu"] = torch.cuda.get_device_name(0)

def tick(name, t0):
    rec[name + "_s"] = round(time.time() - t0, 2)
    print(name, rec[name + "_s"], "s", flush=True)

t0 = time.time()
sim = population.Simulator(cfg, load_grid("mist_miles", "gc"), load_grid("mist_miles", "galaxy"))
tick("load_grids", t0)

t0 = time.time()
t, _ = sample.build_test(seeds.rng(label, "pilot", 41), sim, cfg, gc_per_bin=20_000, cont_per_bin=60_000,
                         gc_draw_cap=3_000_000, cont_draw_cap=30_000_000, chunk=1_000_000)
tick("build_test", t0)
f = t["f_obs"].astype(np.float64)
rec["n_test"] = int(f.shape[0])

t0 = time.time()
gc_b, cont_b = bound.make_banks(sim, cfg, seeds.int_seed(label, "pilot", 42))  # production sizes 1e6 / 4e6
lg, lc = bound.Likelihood(gc_b, m5), bound.Likelihood(cont_b, m5)
tick("make_banks", t0)
rec["bank_sizes"] = [int(gc_b.F.shape[0]), int(cont_b.F.shape[0])]

def pairs(lik, f):
    o = np.sort(f[:, F.I_BAND]); n = 0
    for s in range(0, o.size, 512):
        a, b = lik.window(o[s:s + 512].min(), o[s:s + 512].max()); n += (b - a) * min(512, o.size - s)
    return n

rng = np.random.default_rng(0)
sub = f[rng.choice(f.shape[0], min(100_000, f.shape[0]), replace=False)]
t0 = time.time()
sc, info = bound.score_C(sub, lg, lc)
if torch.cuda.is_available(): torch.cuda.synchronize()
tick("setC", t0)
rec["setC_n"] = int(sub.shape[0])
rec["setC_pairs"] = int(pairs(lg, sub) + pairs(lc, sub))
rec["setC_pairs_per_s"] = rec["setC_pairs"] / rec["setC_s"]
rec["setC_obj_per_s"] = rec["setC_n"] / rec["setC_s"]
rec["setC_frac_ess_lt50"] = [float(np.mean(info["ess_gc"] < 50)), float(np.mean(info["ess_cont"] < 50))]

idx = rng.choice(f.shape[0], min(2_000, f.shape[0]), replace=False)
t0 = time.time()
sa, _ = bound.score_A(f[idx], t["bin"][idx], lg, lc, m5)
tick("setA", t0)
rec["setA_n"] = int(idx.size)
rec["setA_obj_per_s"] = rec["setA_n"] / rec["setA_s"]
rec["setA_finite_frac"] = float(np.isfinite(sa).mean())

for k, n in (("fiducial_2M", 2e6), ("fiducial_8M", 8e6)):
    rec[f"extrap_{k}_h"] = {"setC": n / rec["setC_obj_per_s"] / 3600, "setA": n / rec["setA_obj_per_s"] / 3600}
print(json.dumps(rec, indent=1))
json.dump(rec, open(out, "w"), indent=1)
