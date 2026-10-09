#!/usr/bin/env python3
"""image_qwen.ipynb 를 만든다. diffusers 네이티브 QwenImagePipeline (img/hidream-I1
패턴)에 bitsandbytes 4bit 양자화 트랜스포머 + 진짜 negative_prompt/true_cfg_scale
을 쓴다 — klein/hidream-dev 와 달리 이 모델은 CFG 가 실제로 작동한다."""
import json
import pathlib

ROOT = pathlib.Path(__file__).parent


def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": [l + "\n" for l in lines]}


def code(src):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": src.splitlines(keepends=True)}


cells = []

cells.append(md(
    "# image_qwen",
    "",
    "**Qwen-Image** (Alibaba, 20B) 로 World Reference → 장소 배경 → 인물 초상.",
    "",
    "| | |",
    "|---|---|",
    "| 커널 | `qwen` |",
    "| 출력 | `outputs/image_qwen/<시나리오>/` |",
    "",
    "---",
    "",
    "## 왜 이 모델인가",
    "",
    "Apache 2.0, 게이트 없음. diffusers 에 `QwenImagePipeline` 이 이미 있다(아직",
    "정식 릴리스 전이라 git 최신판 필요 — `setup_kernels.sh --only qwen` 가 처리함).",
    "BF16 그대로면 ~48GB 로 이 GPU 에 거의 꽉 차 위험해서, 트랜스포머만",
    "bitsandbytes 4bit 로 양자화해 ~17-18GB 로 낮췄다.",
    "",
    "**klein/HiDream-Dev 와 달리 이 모델은 `negative_prompt` + `true_cfg_scale` 로",
    "진짜 classifier-free guidance 가 작동한다** — 장소 이미지에 사람이 새는 문제를",
    "프롬프트 강화뿐 아니라 negative_prompt 로도 직접 막을 수 있다.",
))

cells.append(md("## 1. 커널 확인"))

cells.append(code('''import sys, importlib

KERNEL = "qwen"
NEED   = ["torch", "diffusers", "transformers", "bitsandbytes", "PIL"]

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
    f"'{KERNEL}' 커널이 목록에 없으면 setup_kernels.sh --only qwen 을 먼저 실행한다."
)

from diffusers import QwenImagePipeline, QwenImageTransformer2DModel, BitsAndBytesConfig
print("\\nQwenImagePipeline import OK")
'''))

cells.append(md("## 2. 인증", "Apache 2.0, 게이트 없다."))

cells.append(code('''import os, pathlib
tok = os.environ.get("HF_TOKEN", "").strip()
if not tok:
    p = pathlib.Path.home() / ".hf_token"
    if p.exists():
        tok = p.read_text().strip()
        os.environ["HF_TOKEN"] = tok
print("토큰:", (tok[:6] + "…") if tok else "(없음 — 게이트 없는 모델이라 없어도 된다)")
'''))

cells.append(md("## 3. GPU 확인"))

cells.append(code('''import torch

assert torch.cuda.is_available(), "GPU가 없다. 계산 노드에서 실행할 것."
p = torch.cuda.get_device_properties(0)
print(f"GPU  : {p.name}")
print(f"VRAM : {round(p.total_memory / 1e9, 1)} GB")
print(f"CC   : {p.major}.{p.minor}")
print("\\n트랜스포머 4bit 양자화 기준 대략 17-18GB 필요.")
'''))

cells.append(md("## 4. 설정"))

cells.append(code('''import os, sys, json, pathlib, getpass, shutil

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
MODEL = "image_qwen"
OUT_DIR = BASE / "outputs" / MODEL

os.environ.setdefault("HF_HOME",      str(BASE / "hf_cache"))
os.environ.setdefault("TMPDIR",       str(BASE / "tmp"))
os.environ.setdefault("MPLCONFIGDIR", str(BASE / "mpl_cache"))

for p in (OUT_DIR, pathlib.Path(os.environ["HF_HOME"]), pathlib.Path(os.environ["TMPDIR"])):
    p.mkdir(parents=True, exist_ok=True)

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
print("BASE    :", BASE, f"(여유 {shutil.disk_usage(BASE).free/1e9:.0f} GB)")
print("IN_DIR  :", IN_DIR)
print("HF_HOME :", os.environ["HF_HOME"])
print("OUT_DIR :", OUT_DIR)
print(f"시나리오 {len(DATA)}개")
'''))

cells.append(md("## 5. 프롬프트 조립",
                 "다른 이미지 노트북들과 동일한 `build_prompts()`. 추가로 Qwen 전용",
                 "`NEG_PROMPT` 을 정의한다 — 이 모델만 negative_prompt 가 실제로 작동한다."))

cells.append(code('''STYLE = ("cohesive painterly realism, muted desaturated palette, "
         "soft directional daylight, film grain, no text, no watermark")

# 이 모델은 true_cfg_scale/negative_prompt 가 진짜로 작동한다(klein=1.0,
# hidream-dev=0.0 과 다름). world/places 에는 사람이 새는 걸 막는 네거티브를,
# portraits 에는 (인물 사진이니) 네거티브를 비운다.
NEG_PROMPT_SCENE = "people, person, human, humans, figure, figures, crowd, man, woman, group of people"
NEG_PROMPT_PORTRAIT = ""


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

    portraits = {c["id"]: (f"portrait of a {c['age']}-year-old {c['gender']}, "
                           f"{c['occupation']}. {c['appearance']} "
                           f"setting: {era}. mood: {tone}. "
                           f"waist-up framing, neutral background, even lighting. "
                           f"{STYLE}.")
                 for c in d["cast"]}
    return {"world": world, "places": places, "portraits": portraits}


P = {k: build_prompts(d) for k, d in DATA.items()}

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
'''))

cells.append(md("## 6. 모델 로드", "트랜스포머만 bitsandbytes 4bit 양자화, 나머지(텍스트 인코더/VAE)는 bf16."))

cells.append(code('''import torch
from diffusers import QwenImagePipeline, QwenImageTransformer2DModel, BitsAndBytesConfig

MODEL_ID = "Qwen/Qwen-Image"

quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

transformer = QwenImageTransformer2DModel.from_pretrained(
    MODEL_ID, subfolder="transformer",
    quantization_config=quant_config,
    torch_dtype=torch.bfloat16,
)

pipe = QwenImagePipeline.from_pretrained(
    MODEL_ID, transformer=transformer, torch_dtype=torch.bfloat16,
)
pipe.enable_model_cpu_offload()   # 텍스트 인코더/VAE 는 오프로드로 여유를 더 둔다

print("준비됨:", MODEL_ID)
print(f"할당된 VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
'''))

cells.append(md("## 7. 생성 함수"))

cells.append(code('''STEPS = 50
TRUE_CFG_SCALE = 4.0
SIZE = 1024


def gen(prompt, out_file, negative_prompt="", seed=0, size=SIZE):
    g = torch.Generator("cuda").manual_seed(seed)
    image = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or " ",
        width=size, height=size,
        num_inference_steps=STEPS,
        true_cfg_scale=TRUE_CFG_SCALE,
        generator=g,
    ).images[0]
    out_file = pathlib.Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_file)
    return out_file


print("준비됨. 다음 셀(연결 확인)에서 한 장만 먼저 뽑아볼 것.")
'''))

cells.append(md("## 8. 연결 확인", "**전체를 돌리기 전에 한 장만.**"))

cells.append(code('''test = gen("a plain wooden table in an empty room, soft daylight, no text",
           out_path("_smoke_test", "_smoke_test.png"),
           negative_prompt=NEG_PROMPT_SCENE, seed=0, size=512)
print("생성됨:", test)

from IPython.display import display
from PIL import Image
display(Image.open(test))
'''))

cells.append(md("## 9. World Reference", "컨셉 아트로만 남긴다 — 다음 생성에는 넘기지 않는다."))

cells.append(code('''WR = {}
for scen, v in P.items():
    _f = out_path(scen, "world_ref.png")
    if _f.exists():
        WR[scen] = _f
        print("world_ref (이미 있음, 건너뜀):", scen)
        continue
    WR[scen] = gen(v["world"], _f, negative_prompt=NEG_PROMPT_SCENE, seed=0)
    print("world_ref:", scen)
'''))

cells.append(md("## 10. 장소 배경"))

cells.append(code('''for scen, v in P.items():
    for pid, prompt in v["places"].items():
        _f = out_path(scen, "places", f"{pid}.png")
        if _f.exists():
            print("   (이미 있음, 건너뜀)", scen, pid); continue
        gen(prompt, _f, negative_prompt=NEG_PROMPT_SCENE, seed=0)
        print("  ", scen, pid)
'''))

cells.append(md("## 11. 인물 초상", "인물당 1장(p0)만 만든다."))

cells.append(code('''for scen, v in P.items():
    for cid, prompt in v["portraits"].items():
        _f = out_path(scen, "portraits", f"{cid}_p0.png")
        if _f.exists():
            print("   (이미 있음, 건너뜀)", scen, cid); continue
        gen(prompt, _f, negative_prompt=NEG_PROMPT_PORTRAIT, seed=0)
        print("  ", scen, cid)
'''))

cells.append(md("## 12. 합성 확인"))

cells.append(code('''from IPython.display import display
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
'''))

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "qwen · Qwen-Image", "language": "python", "name": "qwen"},
        "language_info": {"name": "python", "version": "3.12"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out = ROOT / "image_qwen.ipynb"
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("생성됨:", out)
