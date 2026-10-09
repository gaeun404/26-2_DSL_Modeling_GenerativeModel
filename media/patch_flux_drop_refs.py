#!/usr/bin/env python3
"""
image_flux2_klein.ipynb 의 places/portraits 생성 루프에서 refs=[WR[scen]] 를 뺀다.

[근거] world_ref 를 image conditioning 으로 매 장소/인물 생성에 물려주면, klein
(guidance=1.0 필수)에서 텍스트 프롬프트가 거의 무시되고 레퍼런스 이미지를 그대로
복사하다시피 한다 (실제 생성물 확인: PC.png/P3.png 가 world_ref.png 와 거의
동일 — 별당·무녀방이 서재와 똑같이 나옴). flux2 CLI 에는 img_cond_seq 반영
강도를 조절하는 파라미터가 없다(concat 기반 어텐션 컨디셔닝이라 blend/strength
개념 자체가 없음). HiDream 은애초에 레퍼런스 이미지를 못 받는데 장소별로 제대로
구별되는 걸 확인했으므로, flux 도 텍스트 프롬프트만으로 생성하도록 맞춘다.
world_ref 자체는 그대로 만든다(컨셉 아트로는 유효하다) — 다음 생성에 넘기지만
않는다.
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent
NB = ROOT / "image_flux2_klein.ipynb"

FIXES = [
    (
        'for scen, v in P.items():\n'
        '    for pid, prompt in v["places"].items():\n'
        '        gen(prompt, out_path(scen, "places", f"{pid}.png"),\n'
        '            refs=[WR[scen]], seed=0)\n'
        '        print("  ", scen, pid)',
        'for scen, v in P.items():\n'
        '    for pid, prompt in v["places"].items():\n'
        '        # refs=[WR[scen]] 뺐다 — world_ref 를 레퍼런스로 물리면 klein\n'
        '        # (guidance=1.0) 이 텍스트를 거의 무시하고 레퍼런스를 그대로\n'
        '        # 복사한다(장소마다 다 같은 그림이 나옴). 텍스트만으로 생성.\n'
        '        gen(prompt, out_path(scen, "places", f"{pid}.png"), seed=0)\n'
        '        print("  ", scen, pid)',
    ),
    (
        '# 표정 세트는 만들지 않는다. 인물당 1장(p0)만 만든다.\n'
        'for scen, v in P.items():\n'
        '    for cid, prompt in v["portraits"].items():\n'
        '        gen(prompt, out_path(scen, "portraits", f"{cid}_p0.png"),\n'
        '            refs=[WR[scen]], seed=0)\n'
        '        print("  ", scen, cid)',
        '# 표정 세트는 만들지 않는다. 인물당 1장(p0)만 만든다.\n'
        '# refs=[WR[scen]] 뺐다 — 이유는 장소 루프와 동일(레퍼런스 그대로 복사 문제).\n'
        'for scen, v in P.items():\n'
        '    for cid, prompt in v["portraits"].items():\n'
        '        gen(prompt, out_path(scen, "portraits", f"{cid}_p0.png"), seed=0)\n'
        '        print("  ", scen, cid)',
    ),
]


def main():
    nb2 = json.loads(NB.read_text(encoding="utf-8"))
    changed = 0
    for cell in nb2["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        new_src = src
        for old, new in FIXES:
            if old in new_src:
                new_src = new_src.replace(old, new)
        if new_src != src:
            cell["source"] = new_src.splitlines(keepends=True)
            cell["outputs"] = []
            cell["execution_count"] = None
            changed += 1
    if changed:
        backup = NB.with_suffix(NB.suffix + ".bak_refs")
        if not backup.exists():
            shutil.copy2(NB, backup)
        NB.write_text(json.dumps(nb2, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{NB.name}: {changed}개 셀 교체")


if __name__ == "__main__":
    main()
