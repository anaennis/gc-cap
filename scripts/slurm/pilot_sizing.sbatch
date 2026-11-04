#!/bin/bash
#SBATCH --job-name=gccap-sizing
#SBATCH --partition=owners
#SBATCH -G 1
#SBATCH -C GPU_SKU:A100_SXM4
#SBATCH --requeue
#SBATCH --time=04:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --output=logs/pilot_sizing_%j.out
# Test-set contaminant sizing (CRITERIA §4.4, author decision 2026-11-04). Pilot seeds; logs/ only.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
echo "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11  CRITERIA.md" | sha256sum -c -
echo "job=$SLURM_JOB_ID node=$(hostname) commit=$(git rev-parse HEAD) dirty=$(git status --porcelain gccap tests | wc -l) date=$(date -Is)"
ml purge; ml system git/2.45.1 python/3.12.1 math py-pytorch/2.4.1_py312
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH="$PWD"
.venv/bin/python scripts/pilot_sizing.py logs/pilot_sizing_$SLURM_JOB_ID.json
echo "$(date -Is) pilot_sizing job $SLURM_JOB_ID on $(hostname): see logs/pilot_sizing_$SLURM_JOB_ID.json" >> RUN_LOG.md
