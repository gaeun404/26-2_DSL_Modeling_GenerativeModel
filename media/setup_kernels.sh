#!/usr/bin/env bash
# =============================================================================
# setup_kernels.sh — 노트북 4개용 Jupyter 커널을 서로 격리해서 만든다
#
#   ace  : ACE-Step 1.5         (bgm_ace_step.ipynb)
#   sa3  : Stable Audio 3       (bgm_stable_audio.ipynb)
#   flux : FLUX.2 klein         (image_flux2_klein.ipynb)
#   img  : HiDream-I1 diffusers (image_hidream.ipynb)
#
# 왜 환경을 4개로 나누는가 — 취향이 아니라 강제 사항이다.
# 각 저장소의 pyproject.toml 을 직접 확인한 결과 요구사항이 서로 배타적이다.
#
#   패키지        ace                sa3            flux            img
#   -----------------------------------------------------------------------
#   python        >=3.11,<3.13       >=3.10         >=3.10,<3.13    3.12
#   torch         2.10.0+cu128       2.7.1 (cu126)  2.8.0           2.8.0
#   transformers  >=4.51,<4.58       >=5.8.0        ==4.56.1        최신
#
# transformers 만 봐도 sa3(>=5.8) 와 flux(==4.56.1) 는 한 환경에 공존할 수 없다.
#
# 왜 pip 이 아니라 uv 인가
#   ace 의 torch==2.10.0+cu128 과 nano-vllm 은 [tool.uv.index] / [tool.uv.sources]
#   에만 선언돼 있다. pip 은 그 설정을 읽지 않아 의존성 해결에 실패한다.
#
# 디스크 주의
#   uv 는 기본적으로 ~/.cache/uv 에 받아 압축을 푼다. 홈이 작은 쿼터면
#     "failed to write ... libtorch_cuda.so: No space left on device (os error 28)"
#   로 죽는다. 이 스크립트는 캐시/임시파일을 전부 PROJ_BASE 아래로 돌린다.
#   캐시와 venv 가 같은 파일시스템이어야 하드링크가 되어 공간도 절약된다.
#
# 사용법
#   chmod +x setup_kernels.sh
#   PROJ_BASE=/mnt/data1/$USER/mystery ./setup_kernels.sh --install-uv
#   PROJ_BASE=/mnt/data1/$USER/mystery ./setup_kernels.sh --only sa3
#   ./setup_kernels.sh --check          # 설치 없이 점검만 (디스크/GPU/커널)
#   ./setup_kernels.sh --clean          # 캐시와 실패한 venv 정리
#
# 옵션
#   --only <ace|sa3|flux|img>   해당 환경만 처리
#   --check                     아무것도 설치하지 않고 상태만 점검
#   --clean                     ~/.cache/uv, ~/.cache/pip 과 실패한 .venv 삭제
#   --install-uv                uv 가 없으면 설치한다
# =============================================================================

set -uo pipefail        # -e 는 일부러 안 쓴다. 하나 실패해도 나머지를 진행하고 끝에 요약한다.

# ---- 노드별 경로 차이 흡수 ---------------------------------------------------
# 학과 클러스터는 로그인 노드 HOME=/data1/$USER, 계산 노드=/mnt/data1/$USER 로
# 같은 저장소가 다른 경로에 마운트된다. 그리고 계산 노드에는 $HOME 이 아예 없어서
# 그대로 두면 pip cache / jupyter kernelspec 등록이 전부 실패한다.
: "${USER:=$(id -un)}"
ROOT=""
for c in "/mnt/data1/$USER" "/data1/$USER" "${HOME:-}"; do
  [ -n "$c" ] && [ -d "$c" ] && [ -w "$c" ] && { ROOT="$c"; break; }
done
[ -n "$ROOT" ] || { echo "FATAL: 쓸 수 있는 루트를 못 찾았다"; exit 1; }
if [ ! -d "${HOME:-/nonexistent}" ]; then
  export HOME="$ROOT"
  echo "HOME 이 없어서 재설정: $HOME"
fi

# ---- 경로 -------------------------------------------------------------------
PROJ_BASE="${PROJ_BASE:-$ROOT/mystery}"
PROJ_INPUT="${PROJ_INPUT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
HF_HOME="${HF_HOME:-$PROJ_BASE/hf_cache}"

REPOS="$PROJ_BASE/repos"
ENVS="$PROJ_BASE/envs"
LOGS="$PROJ_BASE/logs"

# ---- 캐시를 전부 PROJ_BASE 아래로 (os error 28 방지) -------------------------
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PROJ_BASE/uv_cache}"
export TMPDIR="${TMPDIR:-$PROJ_BASE/tmp}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PROJ_BASE/pip_cache}"
export HF_HOME

ONLY=""; CHECK_ONLY=0; CLEAN=0; INSTALL_UV=0
while [ $# -gt 0 ]; do
  case "$1" in
    --only)       ONLY="${2:-}"; shift 2 ;;
    --check)      CHECK_ONLY=1; shift ;;
    --clean)      CLEAN=1; shift ;;
    --install-uv) INSTALL_UV=1; shift ;;
    -h|--help)    sed -n '2,50p' "$0"; exit 0 ;;
    *) echo "알 수 없는 옵션: $1"; exit 2 ;;
  esac
done

want() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ]; }

RESULT_FILE="$(mktemp)"
note() { printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$RESULT_FILE"; }
hr()   { printf '%s\n' "------------------------------------------------------------------"; }
step() { hr; echo "## $*"; hr; }

free_gb() { df -BG --output=avail "$1" 2>/dev/null | tail -1 | tr -dc '0-9'; }

# 공간이 모자라면 가중치를 받기 전에 멈춘다
need_space() {
  local want_gb="$1" have
  have="$(free_gb "$PROJ_BASE")"
  [ -n "${have:-}" ] || return 0
  if [ "$have" -lt "$want_gb" ]; then
    echo "  디스크 부족: $PROJ_BASE 여유 ${have}GB < 필요 ${want_gb}GB"
    echo "    1) PROJ_BASE 를 더 큰 볼륨으로 바꾸고 다시 실행"
    echo "    2) 또는 ./setup_kernels.sh --clean 으로 캐시 정리"
    return 1
  fi
  return 0
}

# =============================================================================
# 0. 사전 점검
# =============================================================================
step "0. 사전 점검"

echo "PROJ_BASE    : $PROJ_BASE"
echo "PROJ_INPUT   : $PROJ_INPUT"
echo "HF_HOME      : $HF_HOME"
echo "UV_CACHE_DIR : $UV_CACHE_DIR   <- 작은 디스크면 os error 28 이 난다"
echo "TMPDIR       : $TMPDIR"
echo

echo "=== 마운트별 여유 공간 (큰 곳을 PROJ_BASE 로) ==="
df -h --output=target,size,avail,pcent 2>/dev/null | sort -k3 -hr | head -12 | sed 's/^/  /'
echo

if ! mkdir -p "$PROJ_BASE" "$REPOS" "$ENVS" "$LOGS" "$HF_HOME" "$UV_CACHE_DIR" "$TMPDIR" 2>/dev/null; then
  echo "FAIL: $PROJ_BASE 에 쓸 수 없다."
  echo "      PROJ_BASE=/mnt/data1/\$USER/mystery ./setup_kernels.sh 처럼 지정할 것."
  exit 1
fi
echo "쓰기 권한    : OK"

for f in asset_input_cinderella_en.json asset_input_heungbu_en.json; do
  if [ -f "$PROJ_INPUT/$f" ]; then echo "입력 JSON    : OK   $f"
  else echo "입력 JSON    : 없음 $PROJ_INPUT/$f"; fi
done

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=name,memory.total,compute_cap,driver_version \
             --format=csv,noheader 2>/dev/null | sed 's/^/GPU          : /'
  CC="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -1 | tr -d ' ')"
  if [ -n "${CC:-}" ] && awk "BEGIN{exit !($CC < 8.9)}"; then
    echo "               주의: CC $CC < 8.9 → FP8 미지원. flux 커널을 만들어도"
    echo "               FLUX.2 klein 은 이 GPU 에서 못 돌린다."
  fi
else
  echo "GPU          : nvidia-smi 없음 (로그인 노드면 정상. 설치에는 GPU 가 필요 없다)"
fi

AVAIL_G="$(free_gb "$PROJ_BASE")"
echo
echo "PROJ_BASE 여유: ${AVAIL_G:-?} GB"
echo "  필요량 대략  : 환경 4개 약 50GB + 가중치 약 120GB = 170GB 이상 권장"
echo "                 (HiDream-I1-Dev 47GB, Llama-3.1-8B 16GB 포함)"
if [ -n "${AVAIL_G:-}" ] && [ "$AVAIL_G" -lt 170 ]; then
  echo "  ** 부족하다. PROJ_BASE 를 더 큰 볼륨으로 바꿀 것. **"
fi

# =============================================================================
# 정리 모드
# =============================================================================
if [ "$CLEAN" = "1" ]; then
  step "정리"
  echo "=== 정리 전 ==="
  du -sh "$HOME/.cache/uv" "$HOME/.cache/pip" 2>/dev/null | sed 's/^/  /'
  command -v uv >/dev/null 2>&1 && uv cache clean >/dev/null 2>&1
  rm -rf "$HOME/.cache/uv" "$HOME/.cache/pip"
  for d in "$REPOS/stable-audio-3/.venv" "$REPOS/ACE-Step-1.5/.venv" \
           "$REPOS/flux2/.venv" "$ENVS/img"; do
    [ -d "$d" ] && { echo "  삭제: $d"; rm -rf "$d"; }
  done
  echo "=== 정리 후 ==="
  echo "  PROJ_BASE 여유: $(free_gb "$PROJ_BASE") GB"
  rm -f "$RESULT_FILE"
  exit 0
fi

if [ "$CHECK_ONLY" = "1" ]; then
  step "설치된 커널"
  ls -1 "$HOME/.local/share/jupyter/kernels" 2>/dev/null | sed 's/^/  /' || echo "  (없음)"
  rm -f "$RESULT_FILE"
  exit 0
fi

# ---- uv ---------------------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  if [ "$INSTALL_UV" = "1" ]; then
    echo; echo "uv 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  else
    echo; echo "uv 가 없다. 다음 중 하나:"
    echo "  ./setup_kernels.sh --install-uv"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
  fi
fi
echo "uv           : $(uv --version)"
command -v git >/dev/null 2>&1 || { echo "git 이 없다."; exit 1; }

# =============================================================================
# 공통 헬퍼
# =============================================================================

# 커널 등록 + kernel.json 에 환경변수 주입.
# 이렇게 해두면 노트북의 os.environ.get("PROJ_BASE") 가 항상 잡혀
# /root/mystery 같은 기본값으로 떨어지지 않는다.
register_kernel() {
  local py="$1" name="$2" display="$3"
  "$py" -m ipykernel install --user --name "$name" --display-name "$display" \
    >>"$LOGS/$name.log" 2>&1 || return 1

  local kj="$HOME/.local/share/jupyter/kernels/$name/kernel.json"
  PROJ_BASE="$PROJ_BASE" PROJ_INPUT="$PROJ_INPUT" HF_HOME="$HF_HOME" \
  "$py" - "$kj" <<'PY' || return 1
import json, os, sys
p = sys.argv[1]
with open(p) as f:
    spec = json.load(f)
spec.setdefault("env", {}).update({
    "PROJ_BASE":  os.environ["PROJ_BASE"],
    "PROJ_INPUT": os.environ["PROJ_INPUT"],
    "HF_HOME":    os.environ["HF_HOME"],
    # HF 토큰은 여기 넣지 않는다. 쉘에서 export HF_TOKEN=... 또는 ~/.hf_token
})
with open(p, "w") as f:
    json.dump(spec, f, indent=1)
print("kernel.json patched:", p)
PY
  return 0
}

clone_or_update() {
  local url="$1" dir="$2"
  if [ -d "$dir/.git" ]; then
    echo "  이미 clone 됨: $dir"
  else
    git clone --depth 1 "$url" "$dir" >>"$LOGS/clone.log" 2>&1 \
      || { echo "  clone 실패: $url"; return 1; }
  fi
}

# =============================================================================
# 1. sa3 — Stable Audio 3
#    노트북이 하던 pip install torch==2.7.1 --index-url .../whl/cu124 는 불가능하다.
#    cu124 인덱스의 최신 torch 는 2.6.0 이고 2.7.1 이 아예 없다.
# =============================================================================
if want sa3; then
  step "1. sa3 — Stable Audio 3"
  if need_space 25; then
    D="$REPOS/stable-audio-3"
    if clone_or_update https://github.com/Stability-AI/stable-audio-3.git "$D"; then
      (
        cd "$D" || exit 1
        echo "  uv sync ... (로그: $LOGS/sa3.log)"
        uv sync                                   >>"$LOGS/sa3.log" 2>&1 || exit 1
        uv pip install ipykernel papermill        >>"$LOGS/sa3.log" 2>&1 || exit 1
      )
      if [ $? -eq 0 ] && register_kernel "$D/.venv/bin/python" sa3 "sa3 · Stable Audio 3"; then
        note sa3 OK "$D/.venv"; echo "  OK"
      else
        note sa3 FAIL "로그: $LOGS/sa3.log"; echo "  FAIL — $LOGS/sa3.log 확인"
      fi
    else
      note sa3 FAIL "clone 실패"
    fi
  else
    note sa3 SKIP "디스크 부족"
  fi
fi

# =============================================================================
# 2. ace — ACE-Step 1.5
# =============================================================================
if want ace; then
  step "2. ace — ACE-Step 1.5"
  if need_space 30; then
    D="$REPOS/ACE-Step-1.5"
    if clone_or_update https://github.com/ace-step/ACE-Step-1.5.git "$D"; then
      (
        cd "$D" || exit 1
        echo "  uv sync ... 제일 오래 걸린다 (로그: $LOGS/ace.log)"
        uv sync                                   >>"$LOGS/ace.log" 2>&1 || exit 1
        uv pip install ipykernel papermill        >>"$LOGS/ace.log" 2>&1 || exit 1
      )
      if [ $? -eq 0 ] && register_kernel "$D/.venv/bin/python" ace "ace · ACE-Step 1.5"; then
        note ace OK "$D/.venv"; echo "  OK"
      else
        note ace FAIL "로그: $LOGS/ace.log"; echo "  FAIL — $LOGS/ace.log 확인"
      fi
    else
      note ace FAIL "clone 실패"
    fi
  else
    note ace SKIP "디스크 부족"
  fi
fi

# =============================================================================
# 3. flux — FLUX.2 klein
# =============================================================================
if want flux; then
  step "3. flux — FLUX.2 klein"
  if need_space 25; then
    D="$REPOS/flux2"
    if clone_or_update https://github.com/black-forest-labs/flux2.git "$D"; then
      (
        cd "$D" || exit 1
        echo "  uv venv (python 3.12) ... (로그: $LOGS/flux.log)"
        uv venv --python 3.12 .venv               >>"$LOGS/flux.log" 2>&1 || exit 1
        uv pip install --python .venv/bin/python -e . \
          --extra-index-url https://download.pytorch.org/whl/cu129 \
                                                  >>"$LOGS/flux.log" 2>&1 || exit 1
        uv pip install --python .venv/bin/python ipykernel papermill pillow \
                                                  >>"$LOGS/flux.log" 2>&1 || exit 1
      )
      if [ $? -eq 0 ] && register_kernel "$D/.venv/bin/python" flux "flux · FLUX.2 klein"; then
        note flux OK "$D/.venv"; echo "  OK"
      else
        note flux FAIL "로그: $LOGS/flux.log"; echo "  FAIL — $LOGS/flux.log 확인"
      fi
    else
      note flux FAIL "clone 실패"
    fi
  else
    note flux SKIP "디스크 부족"
  fi
fi

# =============================================================================
# 4. img — HiDream-I1-Dev (diffusers)
#    노트북이 쓰던 HiDreamO1ImagePipeline / HiDream-O1-Image-Dev 는
#    diffusers 에 없는 이름이다. 클래스는 HiDreamImagePipeline 하나뿐이고
#    지원 체크포인트는 HiDream-I1-Full/Dev/Fast 다.
# =============================================================================
if want img; then
  step "4. img — HiDream-I1-Dev (diffusers)"
  if need_space 25; then
    D="$ENVS/img"
    echo "  uv venv (python 3.12) ... (로그: $LOGS/img.log)"
    (
      uv venv --python 3.12 "$D"                  >>"$LOGS/img.log" 2>&1 || exit 1
      # torch 는 CUDA 인덱스에서, 나머지는 PyPI 에서. 인덱스를 섞으면 CPU 빌드가 깔린다.
      uv pip install --python "$D/bin/python" torch==2.8.0 torchvision==0.23.0 \
        --index-url https://download.pytorch.org/whl/cu126 \
                                                  >>"$LOGS/img.log" 2>&1 || exit 1
      uv pip install --python "$D/bin/python" \
        "diffusers>=0.39.0" transformers accelerate safetensors \
        sentencepiece protobuf pillow ipykernel papermill \
                                                  >>"$LOGS/img.log" 2>&1 || exit 1
    )
    if [ $? -eq 0 ] && register_kernel "$D/bin/python" img "img · HiDream-I1 (diffusers)"; then
      note img OK "$D"; echo "  OK"
    else
      note img FAIL "로그: $LOGS/img.log"; echo "  FAIL — $LOGS/img.log 확인"
    fi
  else
    note img SKIP "디스크 부족"
  fi
fi

# =============================================================================
# 5. o1 — HiDream-O1-Image (custom Qwen3-VL 기반 Pixel-DiT, diffusers 아님)
#    inference.py 를 subprocess 로 부른다 (flux2 와 같은 패턴). requirements.txt
#    가 torch>=2.10, transformers==4.57.1 을 못박아 다른 환경과 공존 못 한다.
#    flash-attn 은 안 깐다 — models/pipeline.py 를 이미 use_flash_attn=False 로
#    패치해 뒀다 (원본 README 가 안내하는 공식 우회로).
# =============================================================================
if want o1; then
  step "5. o1 — HiDream-O1-Image"
  if need_space 20; then
    D="$REPOS/HiDream-O1-Image"
    if clone_or_update https://github.com/HiDream-ai/HiDream-O1-Image.git "$D"; then
      (
        cd "$D" || exit 1
        echo "  uv venv (python 3.12) ... (로그: $LOGS/o1.log)"
        uv venv --python 3.12 .venv                 >>"$LOGS/o1.log" 2>&1 || exit 1
        uv pip install --python .venv/bin/python "torch>=2.10" torchvision \
          --index-url https://download.pytorch.org/whl/cu128 \
                                                      >>"$LOGS/o1.log" 2>&1 || exit 1
        uv pip install --python .venv/bin/python \
          "transformers==4.57.1" diffusers accelerate einops numpy pillow tqdm \
          scipy ipykernel papermill                  >>"$LOGS/o1.log" 2>&1 || exit 1
      )
      if [ $? -eq 0 ] && register_kernel "$D/.venv/bin/python" o1 "o1 · HiDream-O1-Image"; then
        note o1 OK "$D/.venv"; echo "  OK"
      else
        note o1 FAIL "로그: $LOGS/o1.log"; echo "  FAIL — $LOGS/o1.log 확인"
      fi
    else
      note o1 FAIL "clone 실패"
    fi
  else
    note o1 SKIP "디스크 부족"
  fi
fi

# =============================================================================
# 6. qwen — Qwen-Image (diffusers, git 최신판 필요 — 아직 정식 릴리스에 없다)
#    BF16 그대로면 ~48GB 로 이 GPU 에 거의 꽉 차 위험하다. bitsandbytes 4bit로
#    트랜스포머만 양자화해서 ~17-18GB 로 낮춘다. negative_prompt/true_cfg_scale
#    진짜 CFG 를 지원한다(klein·hidream-dev 와 다름).
# =============================================================================
if want qwen; then
  step "6. qwen — Qwen-Image"
  if need_space 25; then
    D="$ENVS/qwen"
    echo "  uv venv (python 3.12) ... (로그: $LOGS/qwen.log)"
    (
      uv venv --python 3.12 "$D"                  >>"$LOGS/qwen.log" 2>&1 || exit 1
      uv pip install --python "$D/bin/python" torch==2.8.0 torchvision==0.23.0 \
        --index-url https://download.pytorch.org/whl/cu126 \
                                                    >>"$LOGS/qwen.log" 2>&1 || exit 1
      # QwenImagePipeline 이 아직 정식 릴리스에 없어 git 최신판을 받는다.
      uv pip install --python "$D/bin/python" \
        "git+https://github.com/huggingface/diffusers.git" \
        transformers accelerate safetensors bitsandbytes \
        sentencepiece protobuf pillow ipykernel papermill \
                                                    >>"$LOGS/qwen.log" 2>&1 || exit 1
    )
    if [ $? -eq 0 ] && register_kernel "$D/bin/python" qwen "qwen · Qwen-Image"; then
      note qwen OK "$D"; echo "  OK"
    else
      note qwen FAIL "로그: $LOGS/qwen.log"; echo "  FAIL — $LOGS/qwen.log 확인"
    fi
  else
    note qwen SKIP "디스크 부족"
  fi
fi

# =============================================================================
# 7. fluxdev — FLUX.2 dev (Full, 32B). 공식 사전양자화 체크포인트
#    diffusers/FLUX.2-dev-bnb-4bit (트랜스포머+텍스트인코더 둘 다 4bit) 를 쓴다.
#    HF 공식 블로그 기준 필요 VRAM ~20GB. black-forest-labs/FLUX.2-dev 게이트
#    승인이 이미 돼 있어야 한다(오늘 ae.safetensors 받을 때 이미 승인함).
#    diffusers 최신판(git) 필요 — Flux2Pipeline 이 아직 정식 릴리스 전이다.
# =============================================================================
if want fluxdev; then
  step "7. fluxdev — FLUX.2 dev (Full, 4bit)"
  if need_space 25; then
    D="$ENVS/fluxdev"
    echo "  uv venv (python 3.12) ... (로그: $LOGS/fluxdev.log)"
    (
      uv venv --python 3.12 "$D"                  >>"$LOGS/fluxdev.log" 2>&1 || exit 1
      uv pip install --python "$D/bin/python" torch==2.8.0 torchvision==0.23.0 \
        --index-url https://download.pytorch.org/whl/cu126 \
                                                    >>"$LOGS/fluxdev.log" 2>&1 || exit 1
      uv pip install --python "$D/bin/python" \
        "git+https://github.com/huggingface/diffusers.git" \
        transformers accelerate safetensors bitsandbytes \
        sentencepiece protobuf pillow ipykernel papermill \
                                                    >>"$LOGS/fluxdev.log" 2>&1 || exit 1
    )
    if [ $? -eq 0 ] && register_kernel "$D/bin/python" fluxdev "fluxdev · FLUX.2 dev (4bit)"; then
      note fluxdev OK "$D"; echo "  OK"
    else
      note fluxdev FAIL "로그: $LOGS/fluxdev.log"; echo "  FAIL — $LOGS/fluxdev.log 확인"
    fi
  else
    note fluxdev SKIP "디스크 부족"
  fi
fi

# =============================================================================
# 5. 검증 — 설치했다고 믿지 말고 실제로 import 해본다
# =============================================================================
step "5. 검증"

verify() {
  local name="$1" py="$2" code="$3"
  [ -x "$py" ] || { printf '  %-5s %s\n' "$name" "(환경 없음)"; return; }
  printf '  %-5s ' "$name"
  "$py" -c "$code" 2>&1 | tail -3 | tr '\n' ' '
  echo
}

want sa3  && verify sa3  "$REPOS/stable-audio-3/.venv/bin/python" '
import torch, transformers
from stable_audio_3 import StableAudioModel
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} transformers={transformers.__version__} StableAudioModel=OK")'

want ace  && verify ace  "$REPOS/ACE-Step-1.5/.venv/bin/python" '
import torch, transformers
from acestep.inference import generate_music, GenerationParams, GenerationConfig
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} transformers={transformers.__version__} generate_music=OK")'

want flux && verify flux "$REPOS/flux2/.venv/bin/python" '
import torch, transformers
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} transformers={transformers.__version__}")'

want img  && verify img  "$ENVS/img/bin/python" '
import torch, diffusers, transformers
from diffusers import HiDreamImagePipeline
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} diffusers={diffusers.__version__} HiDreamImagePipeline=OK")'

want o1   && verify o1   "$REPOS/HiDream-O1-Image/.venv/bin/python" '
import torch, transformers
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} transformers={transformers.__version__}")'

want qwen && verify qwen "$ENVS/qwen/bin/python" '
import torch, diffusers, transformers
from diffusers import QwenImagePipeline, QwenImageTransformer2DModel, BitsAndBytesConfig
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} diffusers={diffusers.__version__} QwenImagePipeline=OK")'

want fluxdev && verify fluxdev "$ENVS/fluxdev/bin/python" '
import torch, diffusers, transformers
from diffusers import Flux2Pipeline, Flux2Transformer2DModel
print(f"torch={torch.__version__} cuda={torch.cuda.is_available()} diffusers={diffusers.__version__} Flux2Pipeline=OK")'

# =============================================================================
# 6. 요약
# =============================================================================
step "6. 요약"
if [ -s "$RESULT_FILE" ]; then
  printf '  %-6s %-6s %s\n' "환경" "상태" "위치/메모"
  while IFS=$'\t' read -r e s m; do printf '  %-6s %-6s %s\n' "$e" "$s" "$m"; done < "$RESULT_FILE"
else
  echo "  (처리한 환경 없음)"
fi
rm -f "$RESULT_FILE"

echo
echo "등록된 커널:"
ls -1 "$HOME/.local/share/jupyter/kernels" 2>/dev/null | sed 's/^/  /' || echo "  (없음)"

cat <<EOF

다음 할 일
  1. 노트북의 1번 "설치" 셀은 실행하지 말 것 (이미 커널 확인 셀로 바뀌어 있다).
  2. HF 토큰:  export HF_TOKEN=hf_xxx   또는  echo hf_xxx > ~/.hf_token
     사전 승인이 필요한 gated repo:
       - stabilityai/stable-audio-3-medium   (약관 동의)
       - meta-llama/Llama-3.1-8B-Instruct    (수동 승인, 오래 걸린다)
         승인이 늦으면 노트북에서 LLAMA_ID 를 미러로:
           export LLAMA_ID=NousResearch/Meta-Llama-3.1-8B-Instruct
  3. Slurm 으로 돌리려면 slurm/ 아래 스크립트를 쓸 것.

커널에 박힌 환경변수 (노트북이 자동으로 따라간다)
  PROJ_BASE  = $PROJ_BASE
  PROJ_INPUT = $PROJ_INPUT
  HF_HOME    = $HF_HOME
EOF
