#!/bin/bash
#SBATCH --job-name=gccap-build
#SBATCH --partition=kipac,owners
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --output=logs/build_env_%j.out
# Build the two python-fsps venvs (HANDOFF §3.4–3.6). Venvs live in $HOME; .venv / .venv-padova are symlinks.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
echo "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11  CRITERIA.md" | sha256sum -c -
echo "job=$SLURM_JOB_ID node=$(hostname) commit=$(git rev-parse HEAD) date=$(date -Is)"
ml purge; ml system git/2.45.1 gcc/14.2.0 python/3.12.1 cmake/3.31.4
ml -t list 2>&1
export SPS_HOME="$PWD/ext/fsps" PIP_NO_CACHE_DIR=1 MAKEFLAGS=-j$SLURM_CPUS_PER_TASK
test "$(git -C ext/fsps rev-parse HEAD)" = b6600ff3a983e0c35ec722e961dfdc89c97c37f2
VROOT="$HOME/gc-cap-venvs"; mkdir -p "$VROOT" "$L_SCRATCH_JOB/src"

build() { # name FFLAGS
  local name=$1 flags=$2 src="$L_SCRATCH_JOB/src/$1"
  mkdir -p "$src"; tar -xzf ext/sdist/fsps-0.5.0.tar.gz -C "$src" --strip-components=1
  rm -rf "$src/src/fsps/libfsps/src"; cp -r ext/fsps/src "$src/src/fsps/libfsps/src"
  diff -r "$src/src/fsps/libfsps/src" ext/fsps/src && echo "$name: libfsps/src == ext/fsps/src"
  rm -rf "$VROOT/$name"; python3 -m venv "$VROOT/$name"
  local py="$VROOT/$name/bin/python"
  $py -m pip install -q --upgrade pip
  # Unpinned, wheels only: pip picks the newest release with a wheel for this glibc (2.17). Laptop lock ignored (author, 2026-10-30).
  # numpy<2 in both venvs: the module torch (fiducial) is built against numpy 1.x and fails with "Numpy is not available" on 2.x.
  local pkgs="numpy<2 scipy scikit-learn lightgbm pandas pyarrow matplotlib pytest astropy scikit-build-core ninja"
  $py -m pip install -q --only-binary=:all: $pkgs
  FFLAGS="$flags" $py -m pip install -v --no-build-isolation "$src" > "logs/pyfsps_${name}_$SLURM_JOB_ID.log" 2>&1
  $py -m pip freeze > "requirements.sherlock.$name.lock"
}
build fiducial "-DMIST=1 -DC3K_LR=0 -DMILES=1"
build padova   "-DMIST=0 -DPADOVA=1 -DC3K_LR=1 -DMILES=0"
# torch from the Sherlock module, not pip: a pip CUDA torch doesn't fit in $HOME (job 50328971, ENOSPC). Loaded after the
# fsps builds so they keep gcc/14.2.0. The .pth appends the module's site-packages after the venv's own (venv numpy etc. win)
# and works under python -I. Jobs using .venv must still `ml math py-pytorch/2.4.1_py312` for the CUDA/cuDNN libraries.
ml math py-pytorch/2.4.1_py312
tr ':' '\n' <<< "$PYTHONPATH" | grep -v '^$' > "$($VROOT/fiducial/bin/python -c 'import sysconfig;print(sysconfig.get_path("purelib"))')/sherlock-modules.pth"
ln -sfn "$VROOT/fiducial" .venv; ln -sfn "$VROOT/padova" .venv-padova

# Acceptance check (HANDOFF §3.6)
for v in .venv .venv-padova; do echo "== $v"; $v/bin/python -I - <<'PY'
import fsps, numpy as np
sp = fsps.StellarPopulation(zcontinuous=1, add_neb_emission=True, logzsol=-1.0)
w, f = sp.get_spectrum(tage=10.0)
z = sp.zlegend
print("libraries", sp.libraries); print("nwave", len(w), w.min(), w.max())
print("nZ", len(z), z.min(), z.max()); print("neb finite", bool(np.isfinite(f).all()))
PY
done
$VROOT/fiducial/bin/python -c "import torch,numpy;print('torch',torch.__version__,'cuda',torch.version.cuda,'numpy',numpy.__version__)"
du -sh "$VROOT"/*
echo "$(date -Is) build_env job $SLURM_JOB_ID on $(hostname): done (see logs/build_env_$SLURM_JOB_ID.out)" >> RUN_LOG.md
