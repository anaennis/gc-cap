"""Constants transcribed from CRITERIA.md (frozen at bd254ba) and AMENDMENTS.md (A1, A2).

Importing this module checks the CRITERIA.md sha256 and refuses to continue if it differs.
Nothing here may be changed to alter a threshold, gate or verdict rule.
"""
import hashlib
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRITERIA_SHA256 = "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_criteria():
    got = sha256_file(ROOT / "CRITERIA.md")
    if got != CRITERIA_SHA256:
        raise RuntimeError(f"CRITERIA.md sha256 {got} != frozen {CRITERIA_SHA256}; refusing to run")
    return got


check_criteria()

# --- §4.1 common -------------------------------------------------------------------------------
BANDS = ("u", "g", "r", "i", "z", "y")
I_BAND = 3
THROUGHPUTS_DIR = ROOT / "ext" / "throughputs" / "baseline"
THROUGHPUTS_COMMIT = "0bcec2a6bec62e442a094df738ec2a9fdff844c5"
THROUGHPUTS_SHA256 = {
    "u": "d8fb220fed913551eb1ae5744a49e145d62aa2fd97786b515f30d20e13223b37",
    "g": "f8935b3a5514e436aea45895369f568bfcc57a682852b0abe3292fd754a7094f",
    "r": "7c2e6d39c57b8d36f664caf1087320af76cd098c382ccb5214e2830096f9a311",
    "i": "ed05e3432509322d8cfb60ee4baf6b8bf1c08fa5a0f011ffee22838c325a9985",
    "z": "66f6a80ace390130e444eabaa59bb9837bbfed6b57af299b6c2cf27a53230c52",
    "y": "f10cc09307ef535c323d9af473b4c4c8dc5905cbf50f91eea1a07cbb38008a20",
}
CAL_FLOOR_MAG = 0.01
DEPTH_PRESETS = {  # 5σ point-source depths (AB)
    "SV": (23.8, 24.5, 24.0, 23.4, 22.7, 22.9),
    "C10": (25.6, 26.9, 26.9, 26.4, 25.6, 24.8),
    "paper": (24.1, 25.45, 25.15, 24.55, 23.85, 22.45),  # replication only
}
DELTAS = (-1.0, -0.5, 0.0, 0.5, 1.0)  # relative to SV

# --- AMENDMENTS A2: catalog inclusion ----------------------------------------------------------
SIGMA_M_MAX = 0.5  # reported magnitude error ≤ 0.5 in every band
MAG_ERR_CONST = 2.5 / math.log(10)  # 1.0857

# --- §4.2 GCs ----------------------------------------------------------------------------------
GC_AGE_GYR = (10.0, 13.5)
GC_FEH_MU = (-1.5, -0.5)
GC_FEH_SIGMA = 0.3
GC_FEH_SIGMA_WIDE = 0.45
GC_FEH_MIX = 0.5
GCLF_MI = -8.5
GCLF_SIGMA = 1.5
DIST_MOD = 31.5

# --- §4.3 galaxies -----------------------------------------------------------------------------
GAL_TAU_GYR = (0.1, 10.0)  # log-uniform
GAL_AGE_MIN_GYR = 0.1  # upper limit: age of the universe at z (Planck18, PLAN F3)
GAL_LOGZ = (-1.5, 0.2)
GAL_AV = (0.0, 2.0)
AV_PER_DUST2 = 1.086  # A_V = 1.086 * dust2 (FSPS Calzetti curve normalised to 1 at 5500 Å)
PZ_Z0 = 0.30
PZ_Z0_ALT = 0.215
Z_MAX = 4.0  # PLAN F13: draws above are redrawn
GAL_I_RANGE = (21.0, 27.0)
COUNT_SLOPE = 0.31
COUNT_SLOPE_ALT = 0.25

# --- class balance (§4.1, §4.3, A2: applied to true-magnitude populations before the cut) ------
RATIO_REF_IMAX = 24.0  # ratio defined for i < 24
GAL_PER_GC = 34.0
GAL_PER_GC_ALT = (10.0, 100.0)
STAR_PER_GC = 2.6

# --- §4.5 bins ---------------------------------------------------------------------------------
BIN_EDGES = (21.0, 22.0, 23.0, 24.0, 25.0)
BIN_LABELS = ("<21", "21-22", "22-23", "23-24", "24-25", ">25")
N_BINS = len(BIN_LABELS)

# --- §4.4 sample sizes -------------------------------------------------------------------------
TEST_GC_PER_BIN_FIDUCIAL = 200_000
TEST_GC_PER_BIN_OTHER = 67_000
FP_TARGET_AT_C07 = 1_000
CONT_CAP_PER_BIN = 5_000_000
TRAIN_N_GC = (1_400, 10_000, 100_000, 1_000_000)
XCHECK_N_GC = (1_000_000, 10_000_000)
CONT_CAP_TRAIN = 5_000_000

# --- §7, §8 rules ------------------------------------------------------------------------------
COMPLETENESS = (0.3, 0.5, 0.7)
GATE_MIN_TP = 20_000
GATE_MIN_FP = 100
N_BOOT = 1000
CI_LEVEL = 0.95
GAP_MARGIN = 0.02
USABLE_PRECISION = 0.8
USABLE_COMPLETENESS = 0.5
XCHECK_AGREE = 0.02
XCHECK_FLAT = 0.01

# --- seeds (PLAN §5) ---------------------------------------------------------------------------
ROOT_SEED = 20261029

# --- §5 SSP libraries (AMENDMENTS A1) ----------------------------------------------------------
LIBRARIES = {
    "mist_miles": {"venv": ".venv", "fsps_libraries": ("mist", "miles")},  # fiducial
    "padova_c3k": {"venv": ".venv-padova", "fsps_libraries": ("pdva", "c3k_lr")},
}
FSPS_COMMIT = "b6600ff3a983e0c35ec722e961dfdc89c97c37f2"


# --- §5 sensitivity grid -----------------------------------------------------------------------
FIDUCIAL = {
    "library": "mist_miles",
    "feh_sigma": GC_FEH_SIGMA,
    "z0": PZ_Z0,
    "gal_per_gc": GAL_PER_GC,
    "depth": "SV",
    "delta": 0.0,
    "slope": COUNT_SLOPE,
    "stars": False,
}


def _cfg(**kw):
    c = dict(FIDUCIAL)
    c.update(kw)
    return c


CONFIGS = {
    "fiducial": _cfg(),
    "lib_padova": _cfg(library="padova_c3k"),
    "feh_wide": _cfg(feh_sigma=GC_FEH_SIGMA_WIDE),
    "pz_alt": _cfg(z0=PZ_Z0_ALT),
    "ratio_10": _cfg(gal_per_gc=10.0),
    "ratio_100": _cfg(gal_per_gc=100.0),
    "depth_m1.0": _cfg(delta=-1.0),
    "depth_m0.5": _cfg(delta=-0.5),
    "depth_p0.5": _cfg(delta=0.5),
    "depth_p1.0": _cfg(delta=1.0),
    "depth_C10": _cfg(depth="C10"),
    "slope_0.25": _cfg(slope=COUNT_SLOPE_ALT),
    "corner_a": _cfg(library="padova_c3k", feh_sigma=GC_FEH_SIGMA_WIDE, z0=PZ_Z0_ALT),
    "corner_b": _cfg(gal_per_gc=100.0, delta=-1.0),
    "corner_c": _cfg(gal_per_gc=10.0, delta=1.0),
    "arm_S": _cfg(stars=True),
    "paper_depth": _cfg(depth="paper"),  # replication only (§8), not a grid point
}


def m5(config):
    """5σ depths for a configuration (preset + Δ, Δ only applies to SV)."""
    base = DEPTH_PRESETS[config["depth"]]
    d = config["delta"] if config["depth"] == "SV" else 0.0
    return tuple(b + d for b in base)


def test_gc_per_bin(config_id):
    return TEST_GC_PER_BIN_FIDUCIAL if config_id == "fiducial" else TEST_GC_PER_BIN_OTHER
