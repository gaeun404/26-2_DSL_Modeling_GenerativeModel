#!/usr/bin/env bash
#SBATCH --job-name=fix_o1_env
#SBATCH --account=ug
#SBATCH --partition=partition1
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --chdir=/tmp
#SBATCH --output=/mnt/data1/%u/mystery/logs/%x_%j.out
#SBATCH --error=/mnt/data1/%u/mystery/logs/%x_%j.err
#
# 계산 노드에서 o1 venv 를 다시 만든다. 로그인 노드에서 만들면 python 심볼릭
# 링크가 /data1/... 를 가리켜 계산 노드(/mnt/data1/...)에서 깨진다.
set -uo pipefail

: "${USER:=$(id -un)}"
ROOT=""
for c in "/mnt/data1/$USER" "/data1/$USER" "${HOME:-}"; do
  [ -n "$c" ] && [ -d "$c" ] && [ -w "$c" ] && { ROOT="$c"; break; }
done
[ -n "$ROOT" ] || { echo "FATAL: 쓸 수 있는 루트를 못 찾았다"; exit 1; }
source "$ROOT/${PROJ_REL:?PROJ_REL 미설정}/slurm/common.sh"
job_prologue

rm -rf "$REPOS/HiDream-O1-Image/.venv"   # 로그인 노드에서 만든 깨진 venv 제거
export PATH="$HOME/.local/bin:$PATH"
bash "$PROJ_INPUT/setup_kernels.sh" --only o1
rc=$?
echo
echo "setup_kernels.sh --only o1 exit=$rc"
exit $rc
