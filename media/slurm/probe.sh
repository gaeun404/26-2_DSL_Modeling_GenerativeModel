#!/usr/bin/env bash
# =============================================================================
# probe.sh — 제출 전 사전 점검. 로그인 노드(hpcmaster)에서 그냥 실행한다.
#   ./probe.sh
# 아무것도 설치하거나 바꾸지 않는다.
#
# 클러스터 값은 이미 실측으로 확정돼 있다 (계정 dsl04 기준):
#   partition1 / account=ug / qos=normal / gres=gpu:1
#   RTX 6000 Ada, 49GB VRAM, compute capability 8.9 (FP8 가능)
# 그래서 여기서는 '아직 모르는 것'만 확인한다 — 특히 디스크 용량.
# =============================================================================
set -uo pipefail

sec() { echo; printf '%s\n' "=================================================================="; echo "## $*"; printf '%s\n' "=================================================================="; }

echo "호스트: $(hostname)   사용자: $USER   시각: $(date '+%F %T')"
echo "(로그인 노드에는 GPU 가 없다. nvidia-smi 가 없어도 정상이다)"

FAIL=0

sec "1. 디스크 — 이게 제일 중요하다"
cat <<'EOF'
  필요량: 환경 4개 약 50GB + 가중치 약 120GB = 170GB 이상
    HiDream-I1-Dev  47GB
    Llama-3.1-8B    16GB
    ACE-Step / SA3 / FLUX.2 klein 가중치
EOF
echo
for d in "/data1/$USER" "/mnt/data1/$USER" "$HOME"; do
  if [ -d "$d" ]; then
    avail="$(df -BG --output=avail "$d" 2>/dev/null | tail -1 | tr -dc '0-9')"
    printf '  %-24s 여유 %-6s GB   쓰기 %s\n' "$d" "${avail:-?}" \
      "$([ -w "$d" ] && echo 가능 || echo 불가)"
    if [ "$d" = "/data1/$USER" ] && [ -n "${avail:-}" ] && [ "$avail" -lt 170 ]; then
      echo "     ** 170GB 미만. 이대로면 중간에 os error 28 로 죽는다. **"
      FAIL=1
    fi
  fi
done
echo
df -h --output=target,size,avail,pcent 2>/dev/null | sort -k3 -hr | head -10 | sed 's/^/  /'
command -v quota >/dev/null 2>&1 && { echo; echo "  쿼터:"; quota -s 2>/dev/null | sed 's/^/    /'; }

sec "2. 파티션 상태 (partition1 이 살아 있는지)"
if command -v sinfo >/dev/null 2>&1; then
  sinfo -a -o "%-14P %-12N %-10G %-8t %C" 2>/dev/null | head -12 | sed 's/^/  /'
  state="$(sinfo -h -p partition1 -o "%t" 2>/dev/null | head -1)"
  echo
  if [ -z "$state" ]; then
    echo "  partition1 을 못 찾았다"; FAIL=1
  elif [ "$state" = "down" ]; then
    echo "  partition1 이 down 이다. 관리자에게 문의할 것."; FAIL=1
  else
    echo "  partition1 상태: $state — 사용 가능"
  fi
else
  echo "  sinfo 없음 — 로그인 노드가 맞는지 확인할 것"; FAIL=1
fi

sec "3. 내 권한 (account=ug, qos=normal 이어야 한다)"
if command -v sacctmgr >/dev/null 2>&1; then
  sacctmgr -n show assoc user="$USER" format=Account%12,Partition%14,QOS%20 2>/dev/null \
    | sed 's/^/  /' | head -10
else
  echo "  sacctmgr 없음"
fi

sec "4. 저장소 위치 — \$ROOT 안에 있어야 한다"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "  저장소: $REPO_DIR"
ROOT=""
for c in "/mnt/data1/$USER" "/data1/$USER" "$HOME"; do
  [ -d "$c" ] && [ -w "$c" ] && { ROOT="$c"; break; }
done
echo "  루트  : $ROOT"
case "$REPO_DIR" in
  "$ROOT"/*) echo "  상대  : ${REPO_DIR#"$ROOT"/}   OK" ;;
  *) echo "  ** 저장소가 루트 밖에 있다. 계산 노드에서 안 보인다. $ROOT 아래로 옮길 것. **"; FAIL=1 ;;
esac
echo
for f in setup_kernels.sh bgm_ace_step.ipynb bgm_stable_audio.ipynb \
         image_hidream.ipynb image_flux2_klein.ipynb \
         asset_input_heungbu_en.json asset_input_cinderella_en.json; do
  [ -f "$REPO_DIR/$f" ] && printf '  OK   %s\n' "$f" || { printf '  없음 %s\n' "$f"; FAIL=1; }
done

sec "5. 도구와 토큰"
for c in uv git python3; do
  command -v "$c" >/dev/null 2>&1 \
    && printf '  %-9s OK   %s\n' "$c" "$(command -v "$c")" \
    || printf '  %-9s 없음\n' "$c"
done
echo "  (uv 가 없어도 된다. 00_setup 이 --install-uv 로 깐다)"
echo
if [ -f "$HOME/.hf_token" ]; then
  echo "  ~/.hf_token : 있음"
else
  echo "  ~/.hf_token : 없음 — gated repo 에서 401 이 난다"
  echo "                echo hf_xxxxx > ~/.hf_token && chmod 600 ~/.hf_token"
  FAIL=1
fi
cat <<'EOF'

  사전 승인이 필요한 gated repo:
    stabilityai/stable-audio-3-medium    약관 동의
    meta-llama/Llama-3.1-8B-Instruct     수동 승인 (오래 걸린다)
      승인 전이면:  export LLAMA_ID=NousResearch/Meta-Llama-3.1-8B-Instruct
EOF

sec "6. 계산 노드 실제 확인 (선택, 약 1분)"
cat <<'EOF'
  로그 경로 문제를 피해 출력을 터미널로 직접 받는다:

    cd /tmp && srun -p partition1 -A ug -q normal -c 1 --mem=1G -t 0:03:00 bash -c '
      echo "node: $(hostname)"; echo "HOME=$HOME"
      ls -ld /data1 /mnt/data1 2>&1
      df -BG --output=target,avail /mnt/data1 2>/dev/null'
EOF

sec "결론"
if [ "$FAIL" -eq 0 ]; then
  echo "  문제 없음. 제출해도 된다:"
  echo "    ./submit_all.sh --dry-run    # 먼저 명령 확인"
  echo "    ./submit_all.sh"
else
  echo "  위의 ** 표시를 먼저 해결할 것."
fi
exit "$FAIL"
