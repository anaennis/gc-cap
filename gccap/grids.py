"""FSPS precompute (PLAN §2) and the interpolated photometric model (PLAN F6: the simulator *is* this model).

Grids store dm_b = m_b - m_i (6 bands) on node axes. Interpolation is multilinear in dm, clamped at the
grid edges. Axes:
  GC:     ([Fe/H], log10 age/yr)                       rest frame, no dust, no nebular
  galaxy: (log Z/Z☉, log10 tau/Gyr, log10 age/Gyr, A_V, z)  delayed-tau, nebular on, Calzetti, IGM

Only grids.py imports fsps. Build functions run inside Slurm jobs (scripts/build_grids.py).
"""
import json
import os
from dataclasses import dataclass, field

import numpy as np

from . import photometry
from .frozen import FSPS_COMMIT, LIBRARIES, ROOT

GRID_DIR = ROOT / "results" / "grids"

# Galaxy grid nodes (PLAN §2). A_V nodes are an implementation choice made before any grid was built:
# log-flux is exactly linear in A_V at fixed wavelength, and 9 nodes (0.25 mag) keep band-integrated
# curvature small; the fidelity check measures the result and is not used to change it.
GAL_LOGZ_NODES = np.round(np.arange(-1.5, 0.2 + 1e-9, 0.1), 2)
GAL_LOGTAU_NODES = np.linspace(np.log10(0.1), np.log10(10.0), 25)
GAL_LOGAGE_NODES = np.linspace(np.log10(0.1), np.log10(13.8), 60)
GAL_AV_NODES = np.linspace(0.0, 2.0, 9)
GAL_Z_NODES = np.round(np.arange(0.0, 4.0 + 1e-9, 0.01), 2)
GC_FEH_NODES = np.round(np.arange(-3.0, 0.5 + 1e-9, 0.05), 2)
GC_LOGAGE_RANGE = (9.9, 10.2)  # FSPS native log-age nodes covering 10–13.5 Gyr

FSPS_COMMON = {"imf_type": 2, "zcontinuous": 1}  # Kroupa, interpolate in logzsol (PLAN F5)


@dataclass
class Grid:
    names: tuple
    axes: list
    dm: np.ndarray  # (*axis_sizes, 6)
    meta: dict = field(default_factory=dict)

    def interp(self, coords, chunk=1_000_000):
        """Multilinear interpolation of dm at coords[N, ndim] (clamped). Returns float64 [N, 6]."""
        coords = np.asarray(coords, dtype=np.float64)
        nd = len(self.axes)
        shape = self.dm.shape[:nd]
        flat = self.dm.reshape(-1, self.dm.shape[-1])
        out = np.empty((coords.shape[0], flat.shape[1]))
        for s in range(0, coords.shape[0], chunk):
            c = coords[s:s + chunk]
            lo, t = [], []
            for d, ax in enumerate(self.axes):
                x = np.clip(c[:, d], ax[0], ax[-1])
                i = np.clip(np.searchsorted(ax, x, side="right") - 1, 0, ax.size - 2)
                lo.append(i)
                t.append((x - ax[i]) / (ax[i + 1] - ax[i]))
            acc = np.zeros((c.shape[0], flat.shape[1]))
            for corner in range(1 << nd):
                idx, w = [], np.ones(c.shape[0])
                for d in range(nd):
                    bit = (corner >> d) & 1
                    idx.append(lo[d] + bit)
                    w = w * (t[d] if bit else 1.0 - t[d])
                acc += w[:, None] * flat[np.ravel_multi_index(idx, shape)]
            out[s:s + chunk] = acc
        return out

    def save(self, path):
        np.savez(path, names=np.array(self.names), dm=self.dm.astype(np.float32),
                 meta=json.dumps(self.meta), **{f"axis_{i}": a for i, a in enumerate(self.axes)})

    @classmethod
    def load(cls, path):
        d = np.load(path, allow_pickle=False)
        names = tuple(str(n) for n in d["names"])
        axes = [d[f"axis_{i}"] for i in range(len(names))]
        return cls(names, axes, d["dm"].astype(np.float64), json.loads(str(d["meta"])))


def grid_path(library, kind):
    return GRID_DIR / f"{library}_{kind}.npz"


def load_grid(library, kind):
    return Grid.load(grid_path(library, kind))


# ----------------------------------------------------------------------------- FSPS (jobs only)
def _check_fsps(library):
    import fsps
    sp = fsps.StellarPopulation(**FSPS_COMMON)
    libs = tuple(x.decode() if isinstance(x, bytes) else x for x in sp.libraries)
    want = LIBRARIES[library]["fsps_libraries"]
    if libs[:2] != want:
        raise RuntimeError(f"fsps build has libraries {libs}, library {library} needs {want}")
    return sp, libs


def fsps_meta(library, sp, extra):
    import fsps
    libs = tuple(x.decode() if isinstance(x, bytes) else x for x in sp.libraries)
    defaults = {}
    for k in sp.params.all_params:
        v = sp.params[k]
        defaults[k] = v.tolist() if hasattr(v, "tolist") else v
    return {"library": library, "fsps_libraries": libs, "fsps_commit": FSPS_COMMIT,
            "python_fsps": getattr(fsps, "__version__", "?"), "SPS_HOME": os.environ.get("SPS_HOME"),
            "fsps_defaults": defaults, **extra}


def _gc_worker(feh):
    import fsps
    sp = fsps.StellarPopulation(**FSPS_COMMON, sfh=0, logzsol=float(feh), add_neb_emission=False)
    wave, spec = sp.get_spectrum(tage=0.0, peraa=False)
    sel = (sp.log_age >= GC_LOGAGE_RANGE[0] - 1e-6) & (sp.log_age <= GC_LOGAGE_RANGE[1] + 1e-6)
    return wave, sp.log_age[sel], spec[sel]


def build_gc_grid(library, processes):
    from multiprocessing import Pool
    sp, libs = _check_fsps(library)
    with Pool(processes) as pool:
        res = pool.map(_gc_worker, GC_FEH_NODES)
    wave, logage = res[0][0], res[0][1]
    if logage[0] > 10.0 or logage[-1] < np.log10(13.5e9):
        raise RuntimeError(f"FSPS log-age nodes {logage} do not cover 10–13.5 Gyr")
    M = photometry.redshift_matrices(wave, [0.0], igm=False)[0]
    dm = np.stack([photometry.colors_rel_i(s @ M) for _, _, s in res])  # (nfeh, nage, 6)
    meta = fsps_meta(library, sp, {"sfh": 0, "add_neb_emission": False, "kind": "gc",
                                   "nwave": int(wave.size)})
    return Grid(("feh", "logage_yr"), [GC_FEH_NODES, logage], dm, meta)


_MZ = None


def _gal_worker(args):
    import fsps
    logz, wave_ref = args
    sp = fsps.StellarPopulation(**FSPS_COMMON, sfh=4, logzsol=float(logz), add_neb_emission=True,
                                gas_logz=float(logz), gas_logu=-2.0, dust_type=2, dust1=0.0, dust2=0.0)
    spec = np.empty((GAL_LOGTAU_NODES.size, GAL_LOGAGE_NODES.size, wave_ref.size))
    for a, lt in enumerate(GAL_LOGTAU_NODES):
        sp.params["tau"] = float(10**lt)
        for b, la in enumerate(GAL_LOGAGE_NODES):
            w, s = sp.get_spectrum(tage=float(10**la), peraa=False)
            spec[a, b] = s
    assert np.array_equal(w, wave_ref)
    cal = photometry.calzetti_fsps(wave_ref)
    S = spec.reshape(-1, wave_ref.size)
    nz, nb = _MZ.shape[0], _MZ.shape[2]
    Mflat = _MZ.transpose(1, 0, 2).reshape(wave_ref.size, nz * nb)
    out = np.empty((GAL_LOGTAU_NODES.size, GAL_LOGAGE_NODES.size, GAL_AV_NODES.size, nz, nb), np.float32)
    for v, av in enumerate(GAL_AV_NODES):
        F = (S * np.exp(-(av / 1.086) * cal)) @ Mflat
        dm = photometry.colors_rel_i(F.reshape(-1, nz, nb))
        out[:, :, v] = dm.reshape(GAL_LOGTAU_NODES.size, GAL_LOGAGE_NODES.size, nz, nb)
    return out


def _gal_init(Mz):
    global _MZ
    _MZ = Mz


def build_gal_grid(library, processes):
    from multiprocessing import Pool
    sp, libs = _check_fsps(library)
    wave = sp.wavelengths
    Mz = photometry.redshift_matrices(wave, GAL_Z_NODES, igm=True)
    with Pool(processes, initializer=_gal_init, initargs=(Mz,)) as pool:
        res = pool.map(_gal_worker, [(z, wave) for z in GAL_LOGZ_NODES])
    dm = np.stack(res)
    meta = fsps_meta(library, sp, {"sfh": 4, "add_neb_emission": True, "gas_logu": -2.0,
                                   "gas_logz": "= logzsol", "dust_type": 2, "dust1": 0.0,
                                   "dust": "Calzetti applied analytically, dust2 = A_V / 1.086",
                                   "igm": "Madau 1995 (FSPS igm_absorb port)", "kind": "galaxy",
                                   "nwave": int(wave.size)})
    return Grid(("logz", "logtau_gyr", "logage_gyr", "av", "z"),
                [GAL_LOGZ_NODES, GAL_LOGTAU_NODES, GAL_LOGAGE_NODES, GAL_AV_NODES, GAL_Z_NODES], dm, meta)


# ----------------------------------------------------------------------------- direct FSPS (fidelity check)
def _direct_gc(args):
    import fsps
    feh, age = args
    sp = fsps.StellarPopulation(**FSPS_COMMON, sfh=0, logzsol=float(feh), add_neb_emission=False)
    w, s = sp.get_spectrum(tage=float(age), peraa=False)
    M = photometry.redshift_matrices(w, [0.0], igm=False)[0]
    return photometry.colors_rel_i(s @ M)


def _direct_gal(args):
    import fsps
    logz, tau, age, av, z = args
    sp = fsps.StellarPopulation(**FSPS_COMMON, sfh=4, logzsol=float(logz), add_neb_emission=True,
                                gas_logz=float(logz), gas_logu=-2.0, dust_type=2, dust1=0.0,
                                dust2=float(av / 1.086), tau=float(tau))
    w, s = sp.get_spectrum(tage=float(age), peraa=False)  # FSPS applies the dust itself here
    wave_obs, trans = photometry.load_throughputs()
    M = photometry.redshift_matrix(w, float(z), wave_obs, photometry.band_weights(wave_obs, trans))
    return photometry.colors_rel_i(s @ M)


def direct_fsps(kind, params, processes):
    """Exact (non-interpolated) dm for each parameter row, using FSPS's own dust (galaxies)."""
    from multiprocessing import Pool
    fn = _direct_gc if kind == "gc" else _direct_gal
    with Pool(processes) as pool:
        return np.array(pool.map(fn, [tuple(p) for p in params], chunksize=1))
