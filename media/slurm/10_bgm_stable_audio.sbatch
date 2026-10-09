#!/usr/bin/env bash
#SBATCH --job-name=bgm_sa3
#SBATCH --account=ug
#SBATCH --partition=partition1
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=03:00:00
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

# gated: huggingface.co/stabilityai/stable-audio-3-medium 약관 동의 필요
run_nb sa3 "$PY_SA3" bgm_stable_audio.ipynb
