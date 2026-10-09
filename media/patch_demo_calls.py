#!/usr/bin/env python3
"""남은 하드코딩된 'heungbu'/'cinderella' 데모 호출 3곳을 고친다."""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent

FIXES = [
    ("bgm_ace_step.ipynb",
     'compare("heungbu", "case")',
     'demo_scen = next(iter(DATA))\ncompare(demo_scen, "case")'),
    ("bgm_stable_audio.ipynb",
     'print("### 흥부놀부 · 원작(story)")\n'
     'listen("heungbu", "story*")\n'
     'print("### 흥부놀부 · 사건 후(case)")\n'
     'listen("heungbu", "case*")',
     'demo_scen = next(iter(DATA))\n'
     'print(f"### {demo_scen} · 원작(story)")\n'
     'listen(demo_scen, "story*")\n'
     'print(f"### {demo_scen} · 사건 후(case)")\n'
     'listen(demo_scen, "case*")'),
    ("image_flux2_klein.ipynb",
     'out_path("cinderella", "_smoke_test.png")',
     'out_path("_smoke_test", "_smoke_test.png")'),
]

for nb_name, old, new in FIXES:
    path = ROOT / nb_name
    nb = json.loads(path.read_text(encoding="utf-8"))
    hit = False
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if old in src:
            new_src = src.replace(old, new)
            cell["source"] = new_src.splitlines(keepends=True)
            cell["outputs"] = []
            cell["execution_count"] = None
            hit = True
    if hit:
        backup = path.with_suffix(path.suffix + ".bak5")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{nb_name}: 교체 완료")
    else:
        print(f"{nb_name}: 대상 못 찾음 (확인 필요)")
