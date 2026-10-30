import numpy as np
import pytest

from gccap.grids import Grid
from gccap.population import Simulator
from gccap import frozen as F


def _toy_gc():
    feh = np.array([-3.0, 0.5])
    la = np.array([9.9, 10.2])
    base = np.array([1.2, 0.5, 0.15, 0.0, -0.05, -0.1])
    slope = np.array([0.35, 0.15, 0.05, 0.0, -0.03, -0.05])
    dm = base + slope * (feh[:, None, None] + 1.0) + 0.0 * la[None, :, None]
    return Grid(("feh", "logage_yr"), [feh, la], dm, {"toy": True})


def _toy_gal():
    axes = [np.array([-1.5, 0.2]), np.array([-1.0, 1.0]), np.array([-1.0, 1.15]), np.array([0.0, 2.0]),
            np.array([0.0, 4.0])]
    shape = [a.size for a in axes] + [6]
    z = axes[4].reshape(1, 1, 1, 1, 2, 1)
    av = axes[3].reshape(1, 1, 1, 2, 1, 1)
    base = np.array([0.8, 0.4, 0.2, 0.0, 0.0, 0.05])
    zs = np.array([1.0, 0.6, 0.3, 0.0, -0.1, -0.1])
    avs = np.array([0.5, 0.3, 0.15, 0.0, -0.1, -0.15])
    dm = np.broadcast_to(base + zs * z / 4 + avs * av / 2, shape).copy()
    return Grid(("logz", "logtau_gyr", "logage_gyr", "av", "z"), axes, dm, {"toy": True})


@pytest.fixture(scope="session")
def toy_sim():
    return Simulator(dict(F.FIDUCIAL), _toy_gc(), _toy_gal())
