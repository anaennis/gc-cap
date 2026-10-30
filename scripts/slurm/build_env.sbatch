#!/bin/bash
#SBATCH --job-name=gccap-build
#SBATCH --partition=kipac
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --output=logs/build_env_%j.out
# Build the two python-fsps venvs (HANDOFF §3.4–3.6). Venvs live in $HOME; .venv / .venv-padova are symlinks.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
echo "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11  CRITERIA.md" | sha256sum -c -
echo "job=$SLURM_JOB_ID node=$(hostname) commit=$(git rev-parse HEAD) date=$(date -Is)"
ml purge; ml system git/2.45.1 python/3.12.1 gcc/14.2.0 cmake/3.31.4
ml -t list 2>&1
export SPS_HOME="$PWD/ext/fsps" PIP_NO_CACHE_DIR=1 MAKEFLAGS=-j$SLURM_CPUS_PER_TASK
test "$(git -C ext/fsps rev-parse HEAD)" = b6600ff3a983e0c35ec722e961dfdc89c97c37f2
VROOT="$HOME/gc-cap-venvs"; mkdir -p "$VROOT" "$L_SCRATCH_JOB/src"

build() { # name FFLAGS with_torch
  local name=$1 flags=$2 torch=$3 src="$L_SCRATCH_JOB/src/$1"
  mkdir -p "$src"; tar -xzf ext/sdist/fsps-0.5.0.tar.gz -C "$src" --strip-components=1
  rm -rf "$src/src/fsps/libfsps/src"; cp -r ext/fsps/src "$src/src/fsps/libfsps/src"
  diff -r "$src/src/fsps/libfsps/src" ext/fsps/src && echo "$name: libfsps/src == ext/fsps/src"
  python3 -m venv "$VROOT/$name"
  local py="$VROOT/$name/bin/python"
  $py -m pip install -q --upgrade pip
  if [ "$torch" = yes ]; then grep -v '^torch==' requirements.lock > "$L_SCRATCH_JOB/req.txt"
    $py -m pip install -q -r "$L_SCRATCH_JOB/req.txt" torch==2.15.0 astropy
  else grep -vE '^(torch|sympy|mpmath|networkx|jinja2|markupsafe|fsspec|filelock)==' requirements.lock > "$L_SCRATCH_JOB/req.txt"
    $py -m pip install -q -r "$L_SCRATCH_JOB/req.txt" astropy
  fi
  FFLAGS="$flags" $py -m pip install -q --no-build-isolation scikit-build-core 2>/dev/null || true
  FFLAGS="$flags" $py -m pip install -v "$src" > "logs/pyfsps_${name}_$SLURM_JOB_ID.log" 2>&1
  $py -m pip freeze > "requirements.sherlock.$name.lock"
}
build fiducial "-DMIST=1 -DC3K_LR=0 -DMILES=1" yes
build padova   "-DMIST=0 -DPADOVA=1 -DC3K_LR=1 -DMILES=0" no
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
$VROOT/fiducial/bin/python -c "import torch;print('torch',torch.__version__,'cuda',torch.version.cuda)"
du -sh "$VROOT"/*
echo "$(date -Is) build_env job $SLURM_JOB_ID on $(hostname): done (see logs/build_env_$SLURM_JOB_ID.out)" >> RUN_LOG.md
