#!/usr/bin/env bash
#SBATCH --job-name=img_hidream
#SBATCH --account=ug
#SBATCH --partition=partition1
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
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

# HiDream-I1-Dev 47GB + Llama-3.1-8B 16GB.
# enable_model_cpu_offload() 라 호스트 RAM 에 전량이 올라간다 → --mem=96G.
# meta-llama 는 gated(수동 승인) — 이 HF_TOKEN 계정엔 아직 승인이 안 돼 있어
# 403 GatedRepoError 로 죽는 걸 확인함(2026-08-22). 승인 전까지는 미러가 기본값.
# 승인 완료되면 export LLAMA_ID=meta-llama/Llama-3.1-8B-Instruct 로 되돌릴 것.
export LLAMA_ID="${LLAMA_ID:-NousResearch/Meta-Llama-3.1-8B-Instruct}"
echo "LLAMA_ID: $LLAMA_ID"
echo

run_nb img "$PY_IMG" image_hidream.ipynb
