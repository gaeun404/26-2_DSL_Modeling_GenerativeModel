#!/usr/bin/env python3
"""
image_hidream.ipynb / image_flux2_klein.ipynb 공통 build_prompts() 의
world/places 프롬프트에서 "no people" 지시를 강화한다.

[근거] 실제 생성물 확인 결과 (17_snow_queen P5 "Festival Tavern" 등),
"empty of people" 가 문장 중간에 짧게 한 번 들어가는 정도로는 "tavern"/
"festival" 처럼 사람을 강하게 암시하는 단어를 못 이기고 사람이 그려진다.
이 파이프라인은 두 모델(HiDream-Dev CFG=0, flux klein guidance=1.0) 다
negative_prompt 가 사실상 무효라 프롬프트 텍스트로만 조절 가능하다.
→ 문장 맨 앞에 강하게 배치 + 끝에서 한 번 더 반복.
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent
NOTEBOOKS = ["image_hidream.ipynb", "image_flux2_klein.ipynb"]

OLD = '''    world = (f"establishing reference image defining the visual world. "
             f"period and place: {era}, {loc}. mood: {tone}. "
             f"consistent color palette, lighting logic and material language. "
             f"no characters. {STYLE}.")

    places = {p["place_id"]: (f"{p['name']}. {p['description']} "
                              f"empty of people. period and place: {era}, {loc}. "
                              f"mood: {tone}. {STYLE}.")
              for p in d["places"]}'''

NEW = '''    world = (f"empty, uninhabited establishing reference image — no people, "
             f"no humans, no figures, nobody present anywhere in frame. "
             f"defines the visual world. period and place: {era}, {loc}. "
             f"mood: {tone}. consistent color palette, lighting logic and "
             f"material language. completely vacant, deserted. {STYLE}.")

    places = {p["place_id"]: (f"empty, uninhabited space — no people, no humans, "
                              f"no figures, nobody present anywhere in frame. "
                              f"{p['name']}. {p['description']} "
                              f"period and place: {era}, {loc}. mood: {tone}. "
                              f"completely vacant, deserted, unoccupied. {STYLE}.")
              for p in d["places"]}'''


def main():
    for nb_name in NOTEBOOKS:
        path = ROOT / nb_name
        nb = json.loads(path.read_text(encoding="utf-8"))
        hit = False
        for cell in nb["cells"]:
            if cell.get("cell_type") != "code":
                continue
            src = "".join(cell.get("source", []))
            if OLD in src:
                new_src = src.replace(OLD, NEW)
                cell["source"] = new_src.splitlines(keepends=True)
                cell["outputs"] = []
                cell["execution_count"] = None
                hit = True
        if hit:
            backup = path.with_suffix(path.suffix + ".bak_nopeople")
            if not backup.exists():
                shutil.copy2(path, backup)
            path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{nb_name}: 교체 완료")
        else:
            print(f"{nb_name}: 대상 못 찾음 (확인 필요)")


if __name__ == "__main__":
    main()
