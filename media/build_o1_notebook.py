#!/usr/bin/env python3
"""image_hidream_o1.ipynb 를 처음부터 만든다. flux2 노트북과 같은 패턴
(inference.py 를 subprocess 로 호출)이지만 O1 은 결과를 --output_image 경로에
직접 저장해서 flux2 처럼 tmp 디렉터리 회수 트릭이 필요 없다."""
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "image_hidream_o1.ipynb"


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}


def code(src):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": src.splitlines(keepends=True),
    }


cells = []

cells.append(md("""# image_hidream_o1

**HiDream-O1-Image (full)** — Qwen3-VL 기반 Pixel-DiT. diffusers 가 아니라 공식
저장소의 `inference.py` 를 subprocess 로 부른다 (flux2 klein 과 같은 패턴).

| | |
|---|---|
| 커널 | `o1` |
| 체크포인트 | `HiDream-ai/HiDream-O1-Image` (full, 50-step, 진짜 CFG guidance=5.0) |
| 출력 | `outputs/image_hidream_o1/<시나리오>/` |

---

## 실행 전 읽을 것

- **MIT 라이선스, 게이트 없음.** HF 토큰 승인 대기가 필요 없다.
- **VRAM ~20GB (bf16, full).** 48GB 카드에서 여유있게 돈다. offload 불필요.
- `full` 체크포인트는 진짜 classifier-free guidance(guidance_scale=5.0)를 쓴다.
  I1-Dev/klein 처럼 distilled 라 CFG=0 인 것들과 달리 프롬프트를 더 세게 따른다 —
  "empty of people" 지시가 더 잘 먹힐 것으로 기대.
- flash-attn 은 안 깐다. `models/pipeline.py` 를 이미
  `use_flash_attn=False` 로 패치해 뒀다 (공식 README 가 안내하는 우회로).
"""))

cells.append(md("## 1. 커널 확인"))

cells.append(code("""import sys, importlib

KERNEL = "o1"
NEED   = ["torch", "transformers", "PIL"]

print("python     :", sys.version.split()[0])
print("interpreter:", sys.executable)
print()

missing = []
for m in NEED:
    try:
        mod = importlib.import_module(m)
        print(f"OK   {m:16s} {getattr(mod, '__version__', '')}")
    except Exception as e:
        missing.append(m)
        print(f"FAIL {m:16s} {type(e).__name__}: {e}")

assert not missing, (
    f"\\n{missing} 를 import 하지 못했다.\\n"
    f"커널을 '{KERNEL}' 로 바꿀 것 (Kernel > Change kernel).\\n"
    f"'{KERNEL}' 커널이 목록에 없으면 setup_kernels.sh --only o1 을 먼저 실행한다."
)
print("\\n커널 OK")

import os, pathlib

O1_DIR = pathlib.Path(os.environ.get("O1_DIR", pathlib.Path(sys.prefix).parent))
assert (O1_DIR / "inference.py").exists(), (
    f"HiDream-O1-Image 저장소를 못 찾았다: {O1_DIR}\\n"
    f"O1_DIR 환경변수로 지정하거나 setup_kernels.sh --only o1 을 먼저 실행할 것."
)
print("O1 저장소:", O1_DIR)
"""))

cells.append(md("## 2. GPU 확인"))

cells.append(code("""import torch

assert torch.cuda.is_available(), "GPU가 없다. 계산 노드에서 실행할 것."

p = torch.cuda.get_device_properties(0)
print(f"GPU  : {p.name}")
print(f"VRAM : {round(p.total_memory / 1e9, 1)} GB")
print(f"CC   : {p.major}.{p.minor}")
"""))

cells.append(md("## 3. 설정"))

cells.append(code("""import os, sys, json, pathlib, getpass, shutil

USER = getpass.getuser()

def pick_root():
    for c in (f"/mnt/data1/{USER}", f"/data1/{USER}",
              str(pathlib.Path.home()), "/workspace", "/scratch"):
        if pathlib.Path(c).is_dir() and os.access(c, os.W_OK):
            return c
    return None

ROOT = os.environ.get("PROJ_ROOT") or pick_root()
if ROOT is None:
    raise SystemExit(f"쓸 수 있는 루트를 못 찾았다 (user={USER})")

if not pathlib.Path(os.environ.get("HOME", "/nonexistent")).is_dir():
    os.environ["HOME"] = ROOT

BASE  = pathlib.Path(os.environ.get("PROJ_BASE") or f"{ROOT}/mystery")
MODEL = "image_hidream_o1"
OUT_DIR = BASE / "outputs" / MODEL

os.environ.setdefault("HF_HOME",      str(BASE / "hf_cache"))
os.environ.setdefault("TMPDIR",       str(BASE / "tmp"))
os.environ.setdefault("MPLCONFIGDIR", str(BASE / "mpl_cache"))

try:
    for p in (OUT_DIR, pathlib.Path(os.environ["HF_HOME"]),
              pathlib.Path(os.environ["TMPDIR"])):
        p.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError) as e:
    raise SystemExit(
        f"{BASE} 에 쓸 수 없다 -> {type(e).__name__}: {e}\\n"
        f"  이 셀 맨 위에서 지정할 것:\\n"
        f"      os.environ['PROJ_BASE'] = '/data1/{USER}/mystery'"
    )

# ---- 입력 JSON (scenarios_en/*.json 전부) ---------------------------------
def pick_input_dir():
    cands = []
    if os.environ.get("PROJ_INPUT"):
        cands.append(pathlib.Path(os.environ["PROJ_INPUT"]))
    cands += [pathlib.Path.cwd(), pathlib.Path.cwd().parent, BASE]
    for c in cands:
        if (c / "scenarios_en").is_dir() and list((c / "scenarios_en").glob("*.json")):
            return c
    for c in pathlib.Path(ROOT).glob("*/*/"):
        if (c / "scenarios_en").is_dir() and list((c / "scenarios_en").glob("*.json")):
            return c
    return None

IN_DIR = pick_input_dir()
if IN_DIR is None:
    raise SystemExit(
        "scenarios_en/*.json 을 못 찾았다.\\n"
        f"  PROJ_INPUT = {os.environ.get('PROJ_INPUT', '(미설정)')}\\n"
        f"  cwd        = {pathlib.Path.cwd()}\\n"
        f"  이 셀 맨 위에서:  os.environ['PROJ_INPUT'] = '/data1/{USER}/<저장소>/Jaemin'"
    )

SCENARIO_FILES = sorted((IN_DIR / "scenarios_en").glob("*.json"))
assert SCENARIO_FILES, f"scenarios_en 에 json 이 없다: {IN_DIR / 'scenarios_en'}"

DATA = {}
for _f in SCENARIO_FILES:
    _d = json.load(open(_f, encoding="utf-8"))
    DATA[_d["scenario_id"]] = _d

for k in DATA:
    (OUT_DIR / k).mkdir(parents=True, exist_ok=True)


def out_path(scen, *parts):
    p = OUT_DIR / scen
    for x in parts[:-1]:
        p = p / x
    p.mkdir(parents=True, exist_ok=True)
    return p / parts[-1]


print("node    :", os.uname().nodename)
print("ROOT    :", ROOT)
print("BASE    :", BASE, f"(여유 {shutil.disk_usage(BASE).free/1e9:.0f} GB)")
print("IN_DIR  :", IN_DIR)
print("HF_HOME :", os.environ["HF_HOME"])
print("OUT_DIR :", OUT_DIR)
print(f"시나리오 {len(DATA)}개")
"""))

cells.append(md("""## 4. 프롬프트 조립

`image_hidream` / `image_flux2_klein` 과 동일한 `build_prompts()` — 같은
프롬프트를 넣어야 세 모델 비교가 성립한다. "empty of people" 강화 버전."""))

cells.append(code("""# 세 이미지 노트북(image_hidream / image_flux2_klein / image_hidream_o1)에
# 동일하게 들어간다. 프롬프트가 달라지면 모델 비교가 성립하지 않는다.
STYLE = ("cohesive painterly realism, muted desaturated palette, "
         "soft directional daylight, film grain, no text, no watermark")


def build_prompts(d):
    era  = d["setting"]["era"]
    loc  = d["setting"]["location"]
    tone = d["adapted_story"]["tone"]

    world = (f"empty, uninhabited establishing reference image — no people, "
             f"no humans, no figures, nobody present anywhere in frame. "
             f"defines the visual world. period and place: {era}, {loc}. "
             f"mood: {tone}. consistent color palette, lighting logic and "
             f"material language. completely vacant, deserted. {STYLE}.")

    places = {p["place_id"]: (f"empty, uninhabited space — no people, no humans, "
                              f"no figures, nobody present anywhere in frame. "
                              f"{p['name']}. {p['description']} "
                              f"period and place: {era}, {loc}. mood: {tone}. "
                              f"completely vacant, deserted, unoccupied. {STYLE}.")
              for p in d["places"]}

    # 이름은 절대 넣지 않는다. 외모 묘사만으로 그린다.
    portraits = {c["id"]: (f"portrait of a {c['age']}-year-old {c['gender']}, "
                           f"{c['occupation']}. {c['appearance']} "
                           f"setting: {era}. mood: {tone}. "
                           f"waist-up framing, neutral background, even lighting. "
                           f"{STYLE}.")
                 for c in d["cast"]}
    return {"world": world, "places": places, "portraits": portraits}


P = {k: build_prompts(d) for k, d in DATA.items()}

# 시나리오마다 자기 source_title 단어를 금지어로 쓴다.
STUDIO_TERMS = ["disney", "pixar", "dreamworks", "ghibli"]

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "with", "to", "and", "or",
    "korean", "folktale", "fairy", "tale", "tales", "myth", "legend", "legends",
    "novel", "classical", "pansori", "based",
    "little", "big", "great", "old", "young", "new",
    "girl", "boy", "man", "woman", "king", "queen", "prince", "princess",
    "red", "white", "black", "gold", "silver", "snow",
    "hood", "riding", "match", "sun", "moon", "woodcutter",
    "night", "day", "house", "story",
}

def banned_terms(d):
    import re
    title = re.sub(r"\\(.*?\\)", "", d.get("source_title", ""))
    words = {w.strip(".,").lower() for w in title.split() if len(w) > 2}
    return (words - STOPWORDS) | set(STUDIO_TERMS)

import re

bad = []
for scen, v in P.items():
    blob = " ".join([v["world"]] + list(v["places"].values())
                    + list(v["portraits"].values())).lower()
    hits = [b for b in banned_terms(DATA[scen])
            if re.search(rf"\\b{re.escape(b)}\\b", blob)]
    if hits:
        bad.append((scen, hits))

for scen, v in P.items():
    print("=" * 70); print(scen)
    print("  [world]", v["world"][:120], "...")
    print(f"  장소 {len(v['places'])} / 인물 {len(v['portraits'])}")

print()
print("이름 유입 검사:", "OK" if not bad else f"FAIL {bad}")
assert not bad, "ENRICH 의 occupation / location / place name 을 확인할 것"
total_places = sum(len(v["places"]) for v in P.values())
total_portraits = sum(len(v["portraits"]) for v in P.values())
print(f"생성 예정: world {len(P)}장 + 장소 {total_places}장 + 인물 {total_portraits}장 "
      f"= {len(P) + total_places + total_portraits}장")
"""))

cells.append(md("""## 5. 생성 함수

`inference.py` 를 subprocess 로 부른다. `--output_image` 에 직접 저장해줘서
flux2 처럼 tmp 디렉터리에서 결과를 회수하는 트릭이 필요 없다."""))

cells.append(code("""import subprocess, sys, pathlib, os

MODEL_PATH = os.environ.get("O1_MODEL_PATH", "HiDream-ai/HiDream-O1-Image")  # full, 진짜 CFG
MODEL_TYPE = "full"
GUIDANCE   = 5.0   # full 기본값. dev 였으면 0.0 (distilled)
SHIFT      = 3.0
NUM_STEPS  = 50    # full 고정값 (inference.py 내부에서 model_type=full 이면 자동 50)
SIZE       = 1024


def build_args(prompt, out_file, seed=0, size=SIZE):
    return [
        sys.executable, str(O1_DIR / "inference.py"),
        "--model_path", MODEL_PATH,
        "--prompt", prompt,
        "--output_image", str(out_file),
        "--height", str(size),
        "--width", str(size),
        "--model_type", MODEL_TYPE,
        "--seed", str(seed),
        "--guidance_scale", str(GUIDANCE),
        "--shift", str(SHIFT),
    ]


def gen(prompt, out_file, seed=0, size=SIZE):
    out_file = pathlib.Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    args = build_args(prompt, out_file, seed=seed, size=size)
    env = dict(os.environ, HF_HOME=os.environ["HF_HOME"])

    r = subprocess.run(args, cwd=O1_DIR, env=env, capture_output=True, text=True)

    if r.returncode != 0 or not out_file.exists():
        print("--- stdout ---"); print(r.stdout[-2000:])
        print("--- stderr ---"); print(r.stderr[-2000:])
        raise RuntimeError(
            f"생성 실패 (returncode={r.returncode}, 파일 존재={out_file.exists()}). "
            "위 stdout/stderr 의 인자 오류를 확인할 것."
        )
    return out_file


print("준비됨. 다음 셀(연결 확인)에서 한 장만 먼저 뽑아볼 것.")
"""))

cells.append(md("## 6. 연결 확인\n\n**전체를 돌리기 전에 한 장만.** 인자가 틀리면 여기서 걸린다."))

cells.append(code("""test = gen("a plain wooden table in an empty room, soft daylight, no text",
           out_path("_smoke_test", "_smoke_test.png"), seed=0, size=512)
print("생성됨:", test)

from IPython.display import display
from PIL import Image
display(Image.open(test))
"""))

cells.append(md("## 7. World Reference"))

cells.append(code("""WR = {}
for scen, v in P.items():
    WR[scen] = gen(v["world"], out_path(scen, "world_ref.png"), seed=0)
    print("world_ref:", scen)
"""))

cells.append(md("## 8. 장소 배경"))

cells.append(code("""for scen, v in P.items():
    for pid, prompt in v["places"].items():
        # refs 없음 — 텍스트만으로 생성한다 (flux 에서 레퍼런스 이미지를 물리면
        # 장소마다 거의 같은 그림이 나오는 문제를 겪은 뒤 세 모델 다 이 방식으로 통일).
        gen(prompt, out_path(scen, "places", f"{pid}.png"), seed=0)
        print("  ", scen, pid)
"""))

cells.append(md("## 9. 인물 초상"))

cells.append(code("""# 표정 세트는 만들지 않는다. 인물당 1장(p0)만 만든다.
for scen, v in P.items():
    for cid, prompt in v["portraits"].items():
        gen(prompt, out_path(scen, "portraits", f"{cid}_p0.png"), seed=0)
        print("  ", scen, cid)
"""))

cells.append(md("""## 10. 합성 확인

`home_place_id` 로 짝을 맞춰 배경 위에 인물을 얹는다."""))

cells.append(code("""from IPython.display import display
from PIL import Image

def composite(scen, w=900):
    d = DATA[scen]
    for c in d["cast"]:
        bg = OUT_DIR / scen / "places" / f"{c['home_place_id']}.png"
        ch = OUT_DIR / scen / "portraits" / f"{c['id']}_p0.png"
        if not (bg.exists() and ch.exists()):
            continue
        b = Image.open(bg).convert("RGB").resize((w, int(w * 0.6)))
        s = int(b.height * 0.85)
        b.paste(Image.open(ch).convert("RGB").resize((s, s)), (int(w * 0.06), b.height - s))
        out = out_path(scen, "composites", f"{c['id']}.png")
        b.save(out)
        print(f"{c['name']} @ {c['home_place_id']}")
        display(b)

demo_scen = next(iter(DATA))
composite(demo_scen)
"""))

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "o1 · HiDream-O1-Image", "language": "python", "name": "o1"},
        "language_info": {"name": "python", "version": "3.12"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"작성 완료: {OUT} ({len(cells)}개 셀)")
