#!/usr/bin/env python3
"""
bgm_ace_step.ipynb / bgm_stable_audio.ipynb 의 INSTRUMENT_OVERRIDE 사용부를
scenarios_en 의 culture.instruments 필드를 우선 쓰도록 바꾼다.
INSTRUMENT_OVERRIDE 딕셔너리 자체는 예전 asset_input(culture 필드 없음) 을 위한
안전망으로 남겨 둔다.
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent


def patch(nb_name, old, new):
    path = ROOT / nb_name
    nb = json.loads(path.read_text(encoding="utf-8"))
    hits = 0
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if old in src:
            backup = path.with_suffix(path.suffix + ".bak2")
            if not backup.exists():
                shutil.copy2(path, backup)
            new_src = src.replace(old, new)
            cell["source"] = new_src.splitlines(keepends=True)
            cell["outputs"] = []
            cell["execution_count"] = None
            hits += 1
    if hits:
        path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{nb_name}: {hits}곳 교체")
    else:
        print(f"{nb_name}: 대상 문자열을 못 찾음 (이미 패치됐거나 구조가 바뀜)")


patch(
    "bgm_ace_step.ipynb",
    old='        tags += INSTRUMENT_OVERRIDE.get(scen, [])\n',
    new=(
        '        # scenarios_en 은 culture.instruments 를 갖고 있다. 없으면(예전 asset_input)\n'
        '        # INSTRUMENT_OVERRIDE 를 안전망으로 쓴다.\n'
        '        tags += d.get("culture", {}).get("instruments") or INSTRUMENT_OVERRIDE.get(scen, [])\n'
    ),
)

patch(
    "bgm_stable_audio.ipynb",
    old=(
        '        if scen in INSTRUMENT_OVERRIDE:\n'
        '            prompt += f" instrumentation: {INSTRUMENT_OVERRIDE[scen]}."\n'
    ),
    new=(
        '        # scenarios_en 은 culture.instruments 를 갖고 있다. 없으면(예전 asset_input)\n'
        '        # INSTRUMENT_OVERRIDE 를 안전망으로 쓴다.\n'
        '        instruments = d.get("culture", {}).get("instruments")\n'
        '        instr_str = ", ".join(instruments) if instruments else INSTRUMENT_OVERRIDE.get(scen)\n'
        '        if instr_str:\n'
        '            prompt += f" instrumentation: {instr_str}."\n'
    ),
)
