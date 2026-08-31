#!/bin/bash
#SBATCH --partition=MGPU-TC2
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --job-name=lmart5k
#SBATCH --output=slurm_lmart5k_%j.out
#SBATCH --error=slurm_lmart5k_%j.err

set -euo pipefail

module load anaconda/25.5.1
source /apps/miniconda3/etc/profile.d/conda.sh
conda activate lambdamart5k

export PYTHONPATH="$SLURM_SUBMIT_DIR/techjam-conversational-search/src:$SLURM_SUBMIT_DIR/techjam-conversational-search"
export PYTHONDONTWRITEBYTECODE=1
export SHOPPING_AGENT_ENABLE_LLM=false
export SHOPPING_DENSE_BACKEND=local
export LANGSMITH_TRACING=false
export LANGCHAIN_TRACING_V2=false
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4

echo "started_at=$(date --iso-8601=seconds)"
echo "host=$(hostname)"
echo "python=$(python --version 2>&1)"
echo "commit=$(git -C "$SLURM_SUBMIT_DIR" rev-parse HEAD 2>/dev/null || echo staged-source)"
echo "cpus=${SLURM_CPUS_PER_TASK:-unknown}"

cd "$SLURM_SUBMIT_DIR/techjam-conversational-search"
python scripts/experiment_lambdamart.py \
  --synthetic data/synthetic_scenarios_5000.jsonl \
  --seed 20260830 \
  --validation-fraction 0.2 \
  --output evaluation_runs/lambdamart_synthetic_5000_official_200

echo "finished_at=$(date --iso-8601=seconds)"
