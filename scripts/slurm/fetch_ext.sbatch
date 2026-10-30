#!/bin/bash
#SBATCH --job-name=gccap-fetch
#SBATCH --partition=kipac
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --output=logs/fetch_ext_%j.out
# Fetch ext/ inputs at pinned versions (HANDOFF §3.2–3.4). Writes checksums to logs/; does not build.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
echo "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11  CRITERIA.md" | sha256sum -c -
echo "job=$SLURM_JOB_ID node=$(hostname) commit=$(git rev-parse HEAD) date=$(date -Is)"
ml system git/2.45.1; git --version
mkdir -p ext/sdist

git init -q ext/fsps
git -C ext/fsps fetch --depth 1 https://github.com/cconroy20/fsps b6600ff3a983e0c35ec722e961dfdc89c97c37f2
git -C ext/fsps checkout -q FETCH_HEAD
echo "fsps HEAD=$(git -C ext/fsps rev-parse HEAD)"

git init -q ext/throughputs
git -C ext/throughputs fetch --depth 1 https://github.com/lsst/throughputs 0bcec2a6bec62e442a094df738ec2a9fdff844c5
git -C ext/throughputs checkout -q FETCH_HEAD
echo "throughputs HEAD=$(git -C ext/throughputs rev-parse HEAD)"
(cd ext/throughputs/baseline && sha256sum total_{u,g,r,i,z,y}.dat)

curl -fsSL -o ext/sdist/fsps-0.5.0.tar.gz https://files.pythonhosted.org/packages/source/f/fsps/fsps-0.5.0.tar.gz
echo "3d57a45d0a196a7a4e3de77254e4bdbe8018e09f0911c1d57cd68af25512f861  ext/sdist/fsps-0.5.0.tar.gz" | sha256sum -c -
du -sh ext
echo "$(date -Is) fetch_ext job $SLURM_JOB_ID on $(hostname): done (see logs/fetch_ext_$SLURM_JOB_ID.out)" >> RUN_LOG.md
