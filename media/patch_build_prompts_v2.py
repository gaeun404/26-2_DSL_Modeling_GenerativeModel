#!/usr/bin/env python3
"""
1회용 패치. 5개 이미지 노트북(hidream/flux2_klein/hidream_o1/qwen/fluxdev)의
build_prompts() 함수를 동일하게 강화한다:
  - places 에 "this scene must clearly show: <clues>" 강한 지시문 추가
    (json/ 원본 map.places[].features 를 번역한 clues 필드 사용)
  - "no bodies, no corpse" 를 no-people 금지문에 추가
    (must_not_show 의도상 시체도 원래는 그려질 법한데, 우리는 장소를 비워두는
    설계이므로 시체도 명시적으로 금지해야 한다)
  - adapted_story.synopsis(각색 사건 배경)를 world/places/portraits 공통 문맥으로 주입
  - adapted_story.palette(색채 무드)를 world/places/portraits 스타일 지시에 주입

STYLE 변수 정의와 그 위/아래의 주석, banned_terms 검사 블록은 그대로 둔다 —
함수 바디만 갈아 끼운다.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).parent

START = "def build_prompts(d):"
END_MARK = 'return {"world": world, "places": places, "portraits": portraits}'

NEW_BODY = '''def build_prompts(d):
    era      = d["setting"]["era"]
    loc      = d["setting"]["location"]
    tone     = d["adapted_story"]["tone"]
    synopsis = d["adapted_story"]["synopsis"]
    palette  = d["adapted_story"]["palette"]

    world = (f"empty, uninhabited establishing reference image — no people, "
             f"no humans, no figures, no bodies, no corpse, nobody present "
             f"anywhere in frame. defines the visual world. "
             f"context: {synopsis} "
             f"period and place: {era}, {loc}. mood: {tone}. "
             f"color palette: {palette}. consistent color palette, lighting "
             f"logic and material language. completely vacant, deserted. "
             f"{STYLE}.")

    places = {}
    for p in d["places"]:
        clue_list = "; ".join(p["clues"])
        places[p["place_id"]] = (
            f"empty, uninhabited space — no people, no humans, no figures, "
            f"no bodies, no corpse, nobody present anywhere in frame. "
            f"{p['name']}. {p['description']} "
            f"this scene must clearly show: {clue_list}. "
            f"context: {synopsis} "
            f"period and place: {era}, {loc}. mood: {tone}. "
            f"color palette: {palette}. "
            f"completely vacant, deserted, unoccupied. {STYLE}.")

    # 이름은 절대 넣지 않는다. 외모 묘사만으로 그린다.
    portraits = {c["id"]: (f"portrait of a {c['age']}-year-old {c['gender']}, "
                           f"{c['occupation']}. {c['appearance']} "
                           f"context: {synopsis} "
                           f"setting: {era}. mood: {tone}. "
                           f"color palette: {palette}. "
                           f"waist-up framing, neutral background, even lighting. "
                           f"{STYLE}.")
                 for c in d["cast"]}
    return {"world": world, "places": places, "portraits": portraits}'''

TARGETS = [
    "image_hidream.ipynb",
    "image_flux2_klein.ipynb",
    "image_hidream_o1.ipynb",
    "image_qwen.ipynb",
    "image_fluxdev.ipynb",
]

for fname in TARGETS:
    path = ROOT / fname
    nb = json.loads(path.read_text(encoding="utf-8"))
    patched = False
    for cell in nb["cells"]:
        src = "".join(cell["source"])
        if START not in src or END_MARK not in src:
            continue
        start_i = src.index(START)
        end_i = src.index(END_MARK) + len(END_MARK)
        new_src = src[:start_i] + NEW_BODY + src[end_i:]
        # ipynb source 는 줄 단위 리스트다(각 원소가 개행 포함, 마지막만 제외
        # 가능) — splitlines(keepends=True) 로 원래 형식을 최대한 맞춘다.
        lines = new_src.splitlines(keepends=True)
        cell["source"] = lines
        patched = True
        break
    if not patched:
        raise SystemExit(f"{fname}: build_prompts 셀을 못 찾음")
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{fname}: 패치 완료")
