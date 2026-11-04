#!/bin/bash
#SBATCH --job-name=gccap-trilegal
#SBATCH --partition=kipac
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --output=logs/fetch_trilegal_%j.out
# Arm-S star catalog from TRILEGAL 1.6 (CRITERIA §4.3; DATA_LOG #25). One 10 deg^2 call.
# TLS verified via ext/certs/bundle.pem (DATA_LOG #23). If the server's 10-min CPU limit
# stops it, the job fails; splitting the field is decided by the author, not here.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
echo "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11  CRITERIA.md" | sha256sum -c -
echo "job=$SLURM_JOB_ID node=$(hostname) commit=$(git rev-parse HEAD) date=$(date -Is)"
ml python/3.12.1
OUT=results/trilegal
python3 -I scripts/fetch_trilegal.py "$OUT" ext/certs/bundle.pem
(cd "$OUT" && sha256sum *)
echo "$(date -Is) fetch_trilegal job $SLURM_JOB_ID on $(hostname): done (see logs/fetch_trilegal_$SLURM_JOB_ID.out)" >> RUN_LOG.md
