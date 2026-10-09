#!/usr/bin/env python3
"""image_fluxdev.ipynb 를 만든다. diffusers 네이티브 Flux2Pipeline + 공식
사전양자화 체크포인트(diffusers/FLUX.2-dev-bnb-4bit, 트랜스포머+텍스트인코더
둘 다 4bit) — HF 공식 블로그 기준 필요 VRAM ~20GB."""
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
    "# image_fluxdev",
    "",
    "**FLUX.2 dev (Full, 32B)** 로 World Reference → 장소 배경 → 인물 초상.",
    "오픈웨이트 포토리얼 1위권 모델(BFL 자체 벤치마크 기준).",
    "",
    "| | |",
    "|---|---|",
    "| 커널 | `fluxdev` |",
    "| 출력 | `outputs/image_fluxdev/<시나리오>/` |",
    "",
    "---",
    "",
    "## 왜 klein 이 아니라 dev(Full) 인가, 그리고 어떻게 GPU 한 장에 넣었나",
    "",
    "klein 은 4B 경량 증류판이다. dev(Full)은 32B 풀 모델로 BFL 이 포토리얼",
    "1위 벤치마크로 내세우는 바로 그 모델이지만, 원래 BF16 기준 64GB 가",
    "필요해 이 GPU(48GB) 에 안 들어간다.",
    "",
    "**HuggingFace 공식 블로그가 미리 4bit 로 양자화해 통째로 올려 둔",
    "체크포인트(`diffusers/FLUX.2-dev-bnb-4bit`)를 쓴다** — 트랜스포머와",
    "24B Mistral-3 텍스트 인코더 둘 다 이미 양자화돼 있어 필요 VRAM이",
    "~20GB 로 줄어든다. `black-forest-labs/FLUX.2-dev` 게이트 승인이",
    "이미 돼 있어야 한다(ae.safetensors 받을 때 동의 완료).",
))

cells.append(md("## 1. 커널 확인"))

cells.append(code('''import sys, importlib

KERNEL = "fluxdev"
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
    f"'{KERNEL}' 커널이 목록에 없으면 setup_kernels.sh --only fluxdev 을 먼저 실행한다."
)

from diffusers import Flux2Pipeline, Flux2Transformer2DModel
print("\\nFlux2Pipeline import OK")
'''))

cells.append(md("## 2. 인증", "**필수** — `black-forest-labs/FLUX.2-dev` 게이트 승인이 돼 있어야 한다."))

cells.append(code('''import os, pathlib
tok = os.environ.get("HF_TOKEN", "").strip()
if not tok:
    p = pathlib.Path.home() / ".hf_token"
    if p.exists():
        tok = p.read_text().strip()
        os.environ["HF_TOKEN"] = tok

assert tok.startswith("hf_"), (
    "HF_TOKEN 이 없다.\\n"
    "  export HF_TOKEN=hf_...   후 커널 재시작\\n"
    "  또는  echo hf_... > ~/.hf_token"
)
print("토큰 설정됨:", tok[:6] + "…" + f" ({len(tok)}자)")
print("주의: black-forest-labs/FLUX.2-dev 게이트를 이 계정이 승인했어야 한다.")
'''))

cells.append(md("## 3. GPU 확인"))

cells.append(code('''import torch

assert torch.cuda.is_available(), "GPU가 없다. 계산 노드에서 실행할 것."
p = torch.cuda.get_device_properties(0)
print(f"GPU  : {p.name}")
print(f"VRAM : {round(p.total_memory / 1e9, 1)} GB")
print(f"CC   : {p.major}.{p.minor}")
print("\\n공식 4bit 사전양자화 체크포인트 기준 대략 20GB 필요.")
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
MODEL = "image_fluxdev"
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

cells.append(md("## 5. 프롬프트 조립", "다른 이미지 노트북들과 동일한 `build_prompts()`."))

cells.append(code('''STYLE = ("cohesive painterly realism, muted desaturated palette, "
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

cells.append(md("## 6. 모델 로드", "공식 사전양자화 체크포인트 — 트랜스포머와 텍스트 인코더 둘 다 4bit."))

cells.append(code('''import torch
from transformers import Mistral3ForConditionalGeneration
from diffusers import Flux2Pipeline, Flux2Transformer2DModel

REPO_ID = "diffusers/FLUX.2-dev-bnb-4bit"

transformer = Flux2Transformer2DModel.from_pretrained(
    REPO_ID, subfolder="transformer", torch_dtype=torch.bfloat16, device_map="cpu"
)
text_encoder = Mistral3ForConditionalGeneration.from_pretrained(
    REPO_ID, subfolder="text_encoder", dtype=torch.bfloat16, device_map="cpu"
)

pipe = Flux2Pipeline.from_pretrained(
    REPO_ID, transformer=transformer, text_encoder=text_encoder, torch_dtype=torch.bfloat16
)
pipe.enable_model_cpu_offload()

print("준비됨:", REPO_ID)
'''))

cells.append(md("## 7. 생성 함수"))

cells.append(code('''STEPS = 50
GUIDANCE = 4.0
SIZE = 1024


def gen(prompt, out_file, seed=0, size=SIZE):
    image = pipe(
        prompt=prompt,
        generator=torch.Generator(device="cuda").manual_seed(seed),
        num_inference_steps=STEPS,
        guidance_scale=GUIDANCE,
        width=size, height=size,
    ).images[0]
    out_file = pathlib.Path(out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_file)
    return out_file


print("준비됨. 다음 셀(연결 확인)에서 한 장만 먼저 뽑아볼 것.")
'''))

cells.append(md("## 8. 연결 확인", "**전체를 돌리기 전에 한 장만.**"))

cells.append(code('''test = gen("a plain wooden table in an empty room, soft daylight, no text",
           out_path("_smoke_test", "_smoke_test.png"), seed=0, size=512)
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
    WR[scen] = gen(v["world"], _f, seed=0)
    print("world_ref:", scen)
'''))

cells.append(md("## 10. 장소 배경"))

cells.append(code('''for scen, v in P.items():
    for pid, prompt in v["places"].items():
        _f = out_path(scen, "places", f"{pid}.png")
        if _f.exists():
            print("   (이미 있음, 건너뜀)", scen, pid); continue
        gen(prompt, _f, seed=0)
        print("  ", scen, pid)
'''))

cells.append(md("## 11. 인물 초상", "인물당 1장(p0)만 만든다."))

cells.append(code('''for scen, v in P.items():
    for cid, prompt in v["portraits"].items():
        _f = out_path(scen, "portraits", f"{cid}_p0.png")
        if _f.exists():
            print("   (이미 있음, 건너뜀)", scen, cid); continue
        gen(prompt, _f, seed=0)
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
        "kernelspec": {"display_name": "fluxdev · FLUX.2 dev (4bit)", "language": "python", "name": "fluxdev"},
        "language_info": {"name": "python", "version": "3.12"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out = ROOT / "image_fluxdev.ipynb"
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("생성됨:", out)
