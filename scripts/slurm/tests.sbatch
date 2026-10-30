#!/bin/bash
#SBATCH --job-name=gccap-tests
#SBATCH --partition=kipac
#SBATCH --time=00:45:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --output=logs/tests_%j.out
# Step 2 test suite (unit + required). Pilot seeds only; writes nothing to results/.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
echo "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11  CRITERIA.md" | sha256sum -c -
echo "job=$SLURM_JOB_ID node=$(hostname) commit=$(git rev-parse HEAD) dirty=$(git status --porcelain gccap tests | wc -l) date=$(date -Is)"
ml purge; ml system git/2.45.1 python/3.12.1
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
.venv/bin/python -m pytest -q -rs tests/ -s 2>&1 | tail -60
echo "$(date -Is) tests job $SLURM_JOB_ID on $(hostname): see logs/tests_$SLURM_JOB_ID.out" >> RUN_LOG.md
