#!/usr/bin/env bash
#SBATCH --job-name=verify
#SBATCH --account=ug
#SBATCH --partition=partition1
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:15:00
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

fail=0
check() {
  local name="$1" py="$2" code="$3"
  printf '%-6s ' "$name"
  if [ ! -x "$py" ]; then echo "환경 없음 ($py)"; fail=1; return; fi
  if out=$("$py" -c "$code" 2>&1); then
    echo "${out##*$'\n'}"
  else
    echo "FAIL"; echo "$out" | tail -6 | sed 's/^/       | /'; fail=1
  fi
}

check sa3 "$PY_SA3" '
import torch, transformers
from stable_audio_3 import StableAudioModel
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} transformers={transformers.__version__} StableAudioModel=OK")'

check ace "$PY_ACE" '
import torch, transformers
from acestep.inference import generate_music, GenerationParams, GenerationConfig
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} transformers={transformers.__version__} generate_music=OK")'

check flux "$PY_FLUX" '
import torch, transformers
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} transformers={transformers.__version__}")'

check img "$PY_IMG" '
import torch, diffusers
from diffusers import HiDreamImagePipeline
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} diffusers={diffusers.__version__} HiDreamImagePipeline=OK")'

echo
echo "papermill:"
for n in sa3 ace flux img; do
  eval "p=\$PY_${n^^}"
  [ -x "$p" ] && printf '  %-5s %s\n' "$n" "$("$p" -m papermill --version 2>&1 | head -1)"
done
echo
echo "등록된 커널 ($HOME/.local/share/jupyter/kernels):"
ls -1 "$HOME/.local/share/jupyter/kernels" 2>/dev/null | sed 's/^/  /' || echo "  (없음)"
echo
[ $fail -eq 0 ] && echo "전체 OK" || echo "실패 있음 — setup 로그를 확인할 것"
exit $fail
