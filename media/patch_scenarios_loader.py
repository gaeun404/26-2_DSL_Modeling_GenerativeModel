#!/usr/bin/env python3
"""
4개 노트북(bgm_ace_step / bgm_stable_audio / image_hidream / image_flux2_klein)의
"입력 JSON" 셀을 asset_input_cinderella/heungbu 2개 하드코딩에서
scenarios_en/*.json 전부를 읽도록 교체한다.

  python3 patch_scenarios_loader.py

원본은 <파일명>.bak 으로 백업된다. 이미 .bak 이 있으면 덮어쓰지 않는다
(여러 번 돌려도 원본을 잃지 않게).
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent

NOTEBOOKS = [
    "bgm_ace_step.ipynb",
    "bgm_stable_audio.ipynb",
    "image_hidream.ipynb",
    "image_flux2_klein.ipynb",
]

OLD_MARKER = 'NEEDED = ["asset_input_cinderella_en.json"'

NEW_LOADER = '''# ---- 입력 JSON (scenarios_en/*.json 전부) ---------------------------------
# papermill 로 돌리면 cwd 가 /tmp 라 "." 만으로는 못 찾는다.
# PROJ_INPUT(환경변수) 을 먼저 보고, 없으면 후보들을 뒤진다.
def pick_input_dir():
    cands = []
    if os.environ.get("PROJ_INPUT"):
        cands.append(pathlib.Path(os.environ["PROJ_INPUT"]))
    cands += [pathlib.Path.cwd(), pathlib.Path.cwd().parent, BASE]
    for c in cands:
        if (c / "scenarios_en").is_dir() and list((c / "scenarios_en").glob("*.json")):
            return c
    # 마지막 수단: ROOT 아래를 얕게 훑는다
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

# scenario_id(파일 내부 필드, 예: "12_heungbu")를 키로 쓴다 — 파일명과 무관하게 안정적.
SCENARIO_FILES = sorted((IN_DIR / "scenarios_en").glob("*.json"))
assert SCENARIO_FILES, f"scenarios_en 에 json 이 없다: {IN_DIR / 'scenarios_en'}"

DATA = {}
for _f in SCENARIO_FILES:
    _d = json.load(open(_f, encoding="utf-8"))
    DATA[_d["scenario_id"]] = _d

for k in DATA:
    (OUT_DIR / k).mkdir(parents=True, exist_ok=True)


def out_path(scen, *parts):
    """OUT_DIR/<시나리오>/<...> 경로를 만들고 돌려준다."""
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
print(f"시나리오 {len(DATA)}개:")
for k, d in DATA.items():
    print(f"  {k:24s} 장소 {len(d['places'])} / 인물 {len(d['cast'])}")
'''


def patch_one(nb_name: str) -> bool:
    path = ROOT / nb_name
    nb = json.loads(path.read_text(encoding="utf-8"))

    hits = []
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if OLD_MARKER in src:
            hits.append((i, cell, src))

    if not hits:
        print(f"{nb_name}: 이미 패치됐거나 대상 셀을 못 찾음 (건너뜀)")
        return False
    if len(hits) > 1:
        print(f"{nb_name}: 대상 셀이 {len(hits)}개다. 첫 번째만 교체한다: 셀 #{hits[0][0]}")

    idx, cell, src = hits[0]
    # 셀 앞부분("입력 JSON" 이전, 경로/BASE 설정)은 그대로 두고 그 뒤만 교체한다.
    marker_pos = src.index("# ---- 입력 JSON")
    prefix = src[:marker_pos]
    new_src = prefix + NEW_LOADER

    backup = path.with_suffix(path.suffix + ".bak")
    if not backup.exists():
        shutil.copy2(path, backup)

    cell["source"] = new_src.splitlines(keepends=True)
    cell["outputs"] = []
    cell["execution_count"] = None

    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{nb_name}: 셀 #{idx} 교체 완료 (백업: {backup.name})")
    return True


def main():
    for nb_name in NOTEBOOKS:
        patch_one(nb_name)


if __name__ == "__main__":
    main()
