"""SeedSequence tree (PLAN §5): root 20261029, keys (config_id, role, replicate).

Strings are mapped to integers with a fixed hash so the tree does not depend on dict order or Python's
hash randomisation. Pilot data use role="pilot" and are never written to results/.
"""
import hashlib

import numpy as np

from .frozen import ROOT_SEED

ROLES = ("grid-check", "latent-bank-1", "latent-bank-2", "test", "train", "cv", "bootstrap", "pilot")


def _h(s):
    return int.from_bytes(hashlib.sha256(str(s).encode()).digest()[:4], "little")


def seed_sequence(config_id, role, replicate=0):
    base = role.split("-N")[0] if role.startswith("train-N") else role
    if base not in ROLES and base != "train":
        raise ValueError(f"unknown seed role {role!r}")
    return np.random.SeedSequence(ROOT_SEED, spawn_key=(_h(config_id), _h(role), int(replicate)))


def rng(config_id, role, replicate=0):
    return np.random.Generator(np.random.PCG64(seed_sequence(config_id, role, replicate)))


def int_seed(config_id, role, replicate=0):
    """32-bit seed for torch / LightGBM derived from the same key."""
    return int(seed_sequence(config_id, role, replicate).generate_state(1)[0])


def describe(config_id, role, replicate=0):
    ss = seed_sequence(config_id, role, replicate)
    return {"root": ROOT_SEED, "config_id": config_id, "role": role, "replicate": int(replicate),
            "spawn_key": list(ss.spawn_key)}
