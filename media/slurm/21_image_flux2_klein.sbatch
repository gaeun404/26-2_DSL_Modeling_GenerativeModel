#!/usr/bin/env bash
#SBATCH --job-name=img_flux
#SBATCH --account=ug
#SBATCH --partition=partition1
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=05:00:00
#SBATCH --chdir=/tmp
#SBATCH --output=/mnt/data1/%u/mystery/logs/%x_%j.out
#SBATCH --error=/mnt/data1/%u/mystery/logs/%x_%j.err
#
# 반드시 submit_all.sh 로 제출할 것 (PROJ_REL 전달 + 로그 디렉토리 사전 생성).
# 직접 sbatch 하려면 먼저:  mkdir -p /mnt/data1/$USER/mystery/logs
set -uo pipefail

# sbatch 는 스크립트를 spool 로 복사한다. BASH_SOURCE 도 SLURM_SUBMIT_DIR 도
# 계산 노드에서는 쓸 수 없다. 이 노드에서 유효한 루트를 직접 찾는다.
: "${USER:=$(id -un)}"
ROOT=""
for c in "/mnt/data1/$USER" "/data1/$USER" "${HOME:-}"; do
  [ -n "$c" ] && [ -d "$c" ] && [ -w "$c" ] && { ROOT="$c"; break; }
done
[ -n "$ROOT" ] || { echo "FATAL: 쓸 수 있는 루트를 못 찾았다"; exit 1; }
# shellcheck source=/dev/null
source "$ROOT/${PROJ_REL:?PROJ_REL 미설정 — submit_all.sh 로 제출할 것}/slurm/common.sh"
job_prologue

# klein 의 텍스트 인코더가 Qwen3-4B-FP8 이라 compute capability 8.9 이상 필요.
# 이 클러스터의 RTX 6000 Ada 는 8.9 라 통과한다. 다른 노드에 배정될 때를 대비한 확인.
CC="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -1 | tr -d ' ')"
if [ -n "$CC" ] && awk "BEGIN{exit !($CC < 8.9)}"; then
  echo "SKIP: compute capability $CC < 8.9 → FP8 미지원이라 klein 을 못 돌린다."
  exit 0
fi
echo "compute capability $CC — FP8 가능"
echo

run_nb flux "$PY_FLUX" image_flux2_klein.ipynb
