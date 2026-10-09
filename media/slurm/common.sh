#!/usr/bin/env bash
# =============================================================================
# common.sh — 계산 노드에서 job 이 source 하는 공통 부분
#
# hpccluster (계정 dsl04) 실측 기준으로 맞춰져 있다.
# 다른 스크립트에서 source 로 불러 쓴다. 직접 실행하는 파일이 아니다.
#
# 이 클러스터의 핵심 함정 — 여기서 전부 처리한다
#   · 로그인 노드 HOME = /data1/$USER,  계산 노드 = /mnt/data1/$USER (같은 NFS)
#   · 계산 노드에는 $HOME 자체가 없다 → pip/matplotlib/jupyter 가 전부 깨진다
#   · sbatch 는 스크립트를 spool 로 복사한다 → BASH_SOURCE 로 저장소를 찾으면 틀린다
#   · SLURM_SUBMIT_DIR 은 '로그인 노드' 경로라 계산 노드에 없다 → 쓰면 안 된다
#   · conda/venv 의 콘솔 스크립트는 shebang 이 깨진다 → python 바이너리를 직접 부른다
# =============================================================================

# ---------------------------------------------------------------------------
# 1. 이 노드에서 유효한 저장소 루트를 직접 찾는다 (절대경로를 넘겨받지 않는다)
# ---------------------------------------------------------------------------
: "${USER:=$(id -un)}"

ROOT=""
for c in "/mnt/data1/$USER" "/data1/$USER" "${HOME:-}"; do
  [ -n "$c" ] && [ -d "$c" ] && [ -w "$c" ] && { ROOT="$c"; break; }
done
if [ -z "$ROOT" ]; then
  echo "FATAL: 쓸 수 있는 루트를 못 찾았다 (/mnt/data1/$USER, /data1/$USER, \$HOME)" >&2
  exit 1
fi

# 계산 노드에는 $HOME 이 없다. 그대로 두면 pip cache / jupyter kernelspec /
# matplotlib 이 전부 실패한다. 반드시 살려놓는다.
if [ ! -d "${HOME:-/nonexistent}" ]; then
  export HOME="$ROOT"
  echo "[common] HOME 이 없어서 재설정: $HOME"
fi

# ---------------------------------------------------------------------------
# 2. 경로
#    PROJ_REL: 제출 스크립트가 --export 로 넘겨준 '상대 경로'.
#              절대경로를 넘기면 노드마다 마운트가 달라 깨진다.
# ---------------------------------------------------------------------------
PROJ_INPUT="$ROOT/${PROJ_REL:?PROJ_REL 이 없다. submit_all.sh 로 제출할 것}"
PROJ_BASE="${PROJ_BASE:-$ROOT/mystery}"

export PROJ_INPUT PROJ_BASE

REPOS="$PROJ_BASE/repos"
ENVS="$PROJ_BASE/envs"
LOGS="$PROJ_BASE/logs"
EXECUTED="$PROJ_BASE/executed"

# 캐시류를 전부 대용량 스토리지로. 홈 쿼터에 두면 torch 압축 해제 중
# "No space left on device (os error 28)" 로 죽는다.
export HF_HOME="${HF_HOME:-$PROJ_BASE/hf_cache}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJ_BASE/uv_cache}"
export TMPDIR="${TMPDIR:-$PROJ_BASE/tmp}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PROJ_BASE/pip_cache}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$PROJ_BASE/mpl_cache}"

# 환경별 python 바이너리. conda/venv activate 는 쓰지 않는다 (shebang 문제).
PY_SA3="$REPOS/stable-audio-3/.venv/bin/python"
PY_ACE="$REPOS/ACE-Step-1.5/.venv/bin/python"
PY_FLUX="$REPOS/flux2/.venv/bin/python"
PY_IMG="$ENVS/img/bin/python"
PY_O1="$REPOS/HiDream-O1-Image/.venv/bin/python"
PY_QWEN="$ENVS/qwen/bin/python"
PY_FLUXDEV="$ENVS/fluxdev/bin/python"

# ---------------------------------------------------------------------------
# 3. 헬퍼
# ---------------------------------------------------------------------------

job_prologue() {
  mkdir -p "$PROJ_BASE" "$LOGS" "$EXECUTED" "$HF_HOME" \
           "$UV_CACHE_DIR" "$TMPDIR" "$PIP_CACHE_DIR" "$MPLCONFIGDIR"

  echo "=================================================================="
  echo " job   : ${SLURM_JOB_NAME:-local} (${SLURM_JOB_ID:-no-slurm})"
  echo " node  : $(hostname)"
  echo " time  : $(date '+%F %T')"
  echo " HOME  : $HOME"
  echo " ROOT  : $ROOT"
  echo " repo  : $PROJ_INPUT"
  echo " base  : $PROJ_BASE"
  echo "=================================================================="

  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader \
      | sed 's/^/ GPU   : /'
  else
    echo " GPU   : 없음 (로그인 노드에서 돌고 있는 것은 아닌지 확인)"
  fi

  local avail
  avail="$(df -BG --output=avail "$PROJ_BASE" 2>/dev/null | tail -1 | tr -dc '0-9')"
  echo " 디스크: ${avail:-?} GB 여유  ($PROJ_BASE)"

  # HF 토큰: 환경변수 우선, 없으면 ~/.hf_token
  if [ -z "${HF_TOKEN:-}" ] && [ -f "$HOME/.hf_token" ]; then
    HF_TOKEN="$(tr -d '[:space:]' < "$HOME/.hf_token")"; export HF_TOKEN
  fi
  if [ -n "${HF_TOKEN:-}" ]; then
    echo " HF_TOKEN: 설정됨 (${HF_TOKEN:0:6}…)"
  else
    echo " HF_TOKEN: 없음 — gated repo 에서 401 이 난다"
    echo "           echo hf_... > ~/.hf_token   (로그인 노드에서)"
  fi
  echo
}

# 실패한 셀을 로그 끝에 뽑아준다. 결과 노트북을 열지 않고도 원인을 안다.
show_failed_cell() {
  local nb="$1"
  [ -f "$nb" ] || return 0
  python3 - "$nb" <<'PY' 2>/dev/null
import json, re, sys
try:
    nb = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    raise SystemExit
for i, c in enumerate(nb.get("cells", [])):
    for o in c.get("outputs", []):
        if o.get("output_type") == "error":
            print(f"  실패 셀 #{i}: {o.get('ename')}: {o.get('evalue')}")
            for t in (o.get("traceback") or [])[-10:]:
                print("    ", re.sub(r"\x1b\[[0-9;]*m", "", t).rstrip())
            raise SystemExit
PY
}

# 종료 시 항상 요약을 남긴다. tail 한 번으로 상태를 알 수 있다.
setup_summary_trap() {
  SUMMARY_NB="${1:-}"
  summarize() {
    local rc=$?
    echo
    echo "===== 요약 ====================================================="
    if [ $rc -eq 0 ]; then echo " 성공"; else echo " 실패 (종료코드 $rc)"; fi
    if [ -n "${SUMMARY_NB:-}" ] && [ -f "$SUMMARY_NB" ]; then
      echo " 결과 노트북: $SUMMARY_NB"
      [ $rc -ne 0 ] && show_failed_cell "$SUMMARY_NB"
    fi
    if [ -d "$PROJ_BASE/outputs" ]; then
      echo " 생성물: $(find "$PROJ_BASE/outputs" -type f 2>/dev/null | wc -l | tr -d ' ')개"
    fi
    echo " 종료: $(date '+%F %T')"
    echo "==============================================================="
  }
  trap summarize EXIT
}

# 노트북을 헤드리스로 실행한다.
#   run_nb <커널이름> <python경로> <노트북파일명>
# papermill 은 로그를 stderr 로 보낸다. .err 파일을 볼 것.
run_nb() {
  local kernel="$1" py="$2" nb="$3"
  local base="${nb%.ipynb}"
  local out="$EXECUTED/${base}.executed.ipynb"

  setup_summary_trap "$out"

  if [ ! -x "$py" ]; then
    echo "FAIL: '$kernel' 환경이 없다 -> $py"
    echo "      먼저 00_setup.sbatch 를 돌릴 것."
    return 1
  fi
  if [ ! -f "$PROJ_INPUT/$nb" ]; then
    echo "FAIL: 노트북이 없다 -> $PROJ_INPUT/$nb"
    echo "      PROJ_REL 이 맞는지 확인할 것 (현재: ${PROJ_REL:-미설정})"
    return 1
  fi

  mkdir -p "$EXECUTED"
  echo ">>> 실행 : $nb   (커널 $kernel)"
  echo ">>> 결과 : $out"
  echo

  # 콘솔 스크립트(papermill)가 아니라 python -m 으로 부른다 (shebang 문제 회피)
  "$py" -m papermill "$PROJ_INPUT/$nb" "$out" \
        --kernel "$kernel" --log-output --no-progress-bar
  return $?
}
