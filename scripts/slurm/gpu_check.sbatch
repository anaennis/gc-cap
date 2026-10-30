#!/bin/bash
#SBATCH --job-name=gccap-gpucheck
#SBATCH --partition=owners
#SBATCH --time=00:15:00
#SBATCH -G 1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --requeue
#SBATCH --output=logs/gpu_check_%j.out
# Check that the .venv torch wheel runs on a real GPU and record the hardware (HANDOFF §7). No GPU constraint: this is a smoke test, not the production GPU choice.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
echo "2e50e070598483057f07ee1f2a79bdc780be0324f331cd862f073311285fae11  CRITERIA.md" | sha256sum -c -
echo "job=$SLURM_JOB_ID node=$(hostname) commit=$(git rev-parse HEAD) date=$(date -Is)"
ml purge; ml python/3.12.1
nvidia-smi --query-gpu=name,driver_version,memory.total,compute_cap --format=csv
lscpu | grep -E "^Model name|^CPU\(s\)"; free -g | head -2
.venv/bin/python -I - <<'PY'
import torch
print("torch", torch.__version__, "built for cuda", torch.version.cuda, "arch list", torch.cuda.get_arch_list())
assert torch.cuda.is_available(), "CUDA not available"
d = torch.device("cuda")
print("device", torch.cuda.get_device_name(d), "capability", torch.cuda.get_device_capability(d))
x = torch.randn(4096, 4096, device=d)
y = (x @ x).float().sum().item()
print("matmul ok", y == y)
PY
echo "$(date -Is) gpu_check job $SLURM_JOB_ID on $(hostname): done (see logs/gpu_check_$SLURM_JOB_ID.out)" >> RUN_LOG.md
