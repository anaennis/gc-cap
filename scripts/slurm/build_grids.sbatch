#!/bin/bash
#SBATCH --job-name=gccap-grids
#SBATCH --partition=kipac
#SBATCH --time=06:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=150G
#SBATCH --output=logs/build_grids_%x_%j.out
# Build GC + galaxy grids for one SSP library and run the fidelity check (PLAN §2).
# Usage: sbatch --job-name=gccap-grids-<library> scripts/slurm/build_grids.sbatch <library>
# Restartable: an existing grid file is reused, so a rerun only redoes missing pieces.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
LIB=$1
echo "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11  CRITERIA.md" | sha256sum -c -
echo "job=$SLURM_JOB_ID node=$(hostname) commit=$(git rev-parse HEAD) dirty=$(git status --porcelain gccap scripts | wc -l) library=$LIB date=$(date -Is)"
ml purge; ml system git/2.45.1 python/3.12.1
case $LIB in mist_miles) VENV=.venv;; padova_c3k) VENV=.venv-padova;; *) echo "unknown library $LIB"; exit 1;; esac
export SPS_HOME="$PWD/ext/fsps" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
$VENV/bin/python -I scripts/build_grids.py "$LIB" "$SLURM_CPUS_PER_TASK"
du -sh results/grids/${LIB}_*
echo "$(date -Is) build_grids job $SLURM_JOB_ID ($LIB) on $(hostname): done (see logs/build_grids_${SLURM_JOB_NAME}_$SLURM_JOB_ID.out)" >> RUN_LOG.md
