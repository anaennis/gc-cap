#!/bin/bash
#SBATCH --job-name=gccap-pilot-xcheck
#SBATCH --partition=kipac
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --output=logs/pilot_xcheck_%j.out
# GBDT cross-check pilot (PLAN §3): smoke test at N_GC=1e4, then timing at 1e6. Pilot seeds; logs/ only.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
echo "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11  CRITERIA.md" | sha256sum -c -
echo "job=$SLURM_JOB_ID node=$(hostname) commit=$(git rev-parse HEAD) dirty=$(git status --porcelain gccap scripts | wc -l) date=$(date -Is)"
lscpu | grep -E "Model name|^CPU\(s\)"
ml purge; ml system git/2.45.1 python/3.12.1 math
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH="$PWD"
for n in 1e4 1e6; do
  .venv/bin/python scripts/pilot_xcheck.py logs/pilot_xcheck_${SLURM_JOB_ID}_N$n.json $n $SLURM_CPUS_PER_TASK
done
echo "$(date -Is) pilot_xcheck job $SLURM_JOB_ID on $(hostname): done (see logs/pilot_xcheck_$SLURM_JOB_ID.out)" >> RUN_LOG.md
