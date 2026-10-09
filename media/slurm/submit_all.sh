#!/usr/bin/env bash
# =============================================================================
# submit_all.sh — 로그인 노드(hpcmaster)에서 실행한다.
#
# hpccluster 실측 기준. 이 클러스터의 함정을 여기서 전부 처리한다:
#   ③ 로그 디렉토리를 '제출 전에' 만든다 (없으면 job 이 로그도 없이 즉사)
#   ④ --output/--error 를 '계산 노드 경로'(/mnt/data1/...)로 준다
#   ⑤ --chdir=/tmp 로 고정한다 (로그인 노드 cwd 는 계산 노드에 없다)
#   ⑥ 저장소 위치를 '상대 경로'로 --export 해서 넘긴다 (BASH_SOURCE 는 spool 을 가리킨다)
#
# 사용법
#   ./submit_all.sh                전부 제출
#   ./submit_all.sh --dry-run      제출하지 않고 명령만 출력
#   ./submit_all.sh --setup-only   환경 구축 + 검증만
#   ./submit_all.sh --no-setup     환경이 이미 있을 때 생성 작업만
#   ./submit_all.sh --only sa3     한 작업만 (sa3|ace|img|flux|o1|qwen)
# =============================================================================
set -euo pipefail

# ---- 클러스터 설정 (실측값) -------------------------------------------------
PARTITION="${PARTITION:-partition1}"   # jobs/gpu 는 down + 권한 없음. 이것만 가능
ACCOUNT="${ACCOUNT:-ug}"
QOS="${QOS:-normal}"
GRES="${GRES:-gpu:1}"

# 시간은 실제 예상의 120% 정도로. 크게 잡으면 backfill 빈틈에 못 들어가 대기가 길어진다.
T_SETUP="${T_SETUP:-04:00:00}"
T_VERIFY="${T_VERIFY:-00:15:00}"
T_BGM="${T_BGM:-03:00:00}"
T_IMG="${T_IMG:-05:00:00}"

# CPU/메모리도 과하게 요청하면 계속 PENDING 이다.
CPUS="${CPUS:-8}"
MEM_DEFAULT="${MEM_DEFAULT:-48G}"
MEM_IMG="${MEM_IMG:-96G}"   # HiDream 은 cpu offload 라 호스트 RAM 에 63GB 를 올린다

# ---- 인자 ------------------------------------------------------------------
DRY=0; SETUP_ONLY=0; NO_SETUP=0; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)    DRY=1; shift ;;
    --setup-only) SETUP_ONLY=1; shift ;;
    --no-setup)   NO_SETUP=1; shift ;;
    --only)       ONLY="${2:-}"; shift 2 ;;
    -h|--help)    sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "알 수 없는 옵션: $1"; exit 2 ;;
  esac
done

# ---- 경로 -------------------------------------------------------------------
# 로그인 노드에서는 BASH_SOURCE 가 유효하다 (sbatch 가 복사하기 전이므로).
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 이 노드에서 유효한 루트
ROOT=""
for c in "/mnt/data1/$USER" "/data1/$USER" "$HOME"; do
  [ -d "$c" ] && [ -w "$c" ] && { ROOT="$c"; break; }
done
[ -n "$ROOT" ] || { echo "쓸 수 있는 루트를 못 찾았다"; exit 1; }

# 계산 노드에서 같은 저장소를 가리키는 경로 (/data1/x -> /mnt/data1/x)
case "$ROOT" in
  /data1/*) COMPUTE_ROOT="/mnt$ROOT" ;;
  *)        COMPUTE_ROOT="$ROOT" ;;
esac

# 저장소를 루트 기준 상대 경로로. 절대경로를 넘기면 노드마다 깨진다.
case "$REPO_DIR" in
  "$ROOT"/*) PROJ_REL="${REPO_DIR#"$ROOT"/}" ;;
  *) echo "FATAL: 저장소가 $ROOT 밖에 있다: $REPO_DIR"
     echo "       계산 노드에서 안 보인다. $ROOT 아래로 옮길 것."; exit 1 ;;
esac

PROJ_BASE_REL="${PROJ_BASE_REL:-mystery}"
COMPUTE_BASE="$COMPUTE_ROOT/$PROJ_BASE_REL"
LOGIN_BASE="$ROOT/$PROJ_BASE_REL"

# ③ 로그 디렉토리를 '제출 전에' 만든다. 스크립트 안의 mkdir 은 이미 늦다.
mkdir -p "$LOGIN_BASE/logs" "$LOGIN_BASE/executed"

cat <<EOF
파티션    : $PARTITION  (account=$ACCOUNT qos=$QOS gres=$GRES)
저장소    : $REPO_DIR
  상대경로: $PROJ_REL
루트      : $ROOT   (계산 노드에서는 $COMPUTE_ROOT)
작업베이스: $COMPUTE_BASE
로그      : $COMPUTE_BASE/logs   (로그인 노드에서는 $LOGIN_BASE/logs)

EOF

# ---- 제출 함수 --------------------------------------------------------------
# sub <스크립트> <시간> <메모리> <gpu:yes|no> [의존성]
sub() {
  local script="$1" tl="$2" mem="$3" gpu="$4" dep="${5:-}"
  local opts=(
    --parsable
    --partition="$PARTITION" --account="$ACCOUNT" --qos="$QOS"
    --cpus-per-task="$CPUS" --mem="$mem" --time="$tl"
    --chdir=/tmp                                        # ⑤ 어느 노드에나 있다
    --output="$COMPUTE_BASE/logs/%x_%j.out"             # ④ 계산 노드 경로
    --error="$COMPUTE_BASE/logs/%x_%j.err"
    --export=ALL,PROJ_REL="$PROJ_REL",PROJ_BASE="$COMPUTE_BASE"   # ⑥ 상대경로 전달
  )
  [ "$gpu" = "yes" ] && opts+=(--gres="$GRES")
  [ -n "$dep" ] && opts+=(--dependency=afterany:"$dep")

  if [ "$DRY" = "1" ]; then
    echo "sbatch ${opts[*]} $REPO_DIR/slurm/$script" >&2
    echo "DRYRUN"
  else
    sbatch "${opts[@]}" "$REPO_DIR/slurm/$script"
  fi
}

want() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ]; }

DEP=""
if [ "$NO_SETUP" = "0" ] && [ -z "$ONLY" ]; then
  J="$(sub 00_setup.sbatch "$T_SETUP" 32G no)";        echo "setup   -> $J"
  DEP="$J"
  V="$(sub 01_verify.sbatch "$T_VERIFY" 16G yes "$J")"; echo "verify  -> $V"
fi

if [ "$SETUP_ONLY" = "1" ]; then
  echo
  echo "환경 구축까지만 제출했다. 끝나면:  ./submit_all.sh --no-setup"
  exit 0
fi

# 생성 작업은 setup 에 afterany 로 건다 (afterok 이면 setup 이 부분 실패했을 때
# 멀쩡한 환경까지 전부 취소된다). 각 job 이 자기 환경을 시작할 때 다시 확인한다.
want sa3  && echo "bgm_sa3     -> $(sub 10_bgm_stable_audio.sbatch  "$T_BGM" "$MEM_DEFAULT" yes "$DEP")"
want ace  && echo "bgm_ace     -> $(sub 11_bgm_ace_step.sbatch      "$T_BGM" "$MEM_DEFAULT" yes "$DEP")"
want img  && echo "img_hidream -> $(sub 20_image_hidream.sbatch     "$T_IMG" "$MEM_IMG"     yes "$DEP")"
want flux && echo "img_flux    -> $(sub 21_image_flux2_klein.sbatch "$T_IMG" "$MEM_DEFAULT" yes "$DEP")"
want o1   && echo "img_o1      -> $(sub 22_image_hidream_o1.sbatch  "$T_IMG" "$MEM_DEFAULT" yes "$DEP")"
want qwen && echo "img_qwen    -> $(sub 23_image_qwen.sbatch         "$T_IMG" "$MEM_DEFAULT" yes "$DEP")"
want fluxdev && echo "img_fluxdev -> $(sub 24_image_fluxdev.sbatch      "$T_IMG" "$MEM_DEFAULT" yes "$DEP")"

cat <<EOF

확인
  squeue -u $USER
  sacct -u $USER --starttime today --format=JobID%12,JobName%16,State%14,ExitCode,Elapsed
로그 (.err 를 꼭 볼 것. papermill 은 stderr 로 로그를 보낸다)
  tail -n 40 $LOGIN_BASE/logs/*.err
결과
  $LOGIN_BASE/outputs/     생성물
  $LOGIN_BASE/executed/    셀 출력이 담긴 노트북
EOF
