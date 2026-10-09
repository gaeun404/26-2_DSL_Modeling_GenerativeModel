#!/usr/bin/env python3
"""
scenarios_en/*.json 23개를 실제 노트북 로직(build_prompts, bgm_conditions)에
돌려서 GPU 작업 제출 전에 로컬에서 검증한다:
  - 필드 누락으로 KeyError 나는 곳이 있는지
  - 한글이 그대로 새어 들어간 곳이 있는지 (번역 누락)
  - 원작 고유명사가 새어 들어갔는지 (banned_terms, 기존 로직 그대로)
"""
import glob
import json
import re

STYLE = ("cohesive painterly realism, muted desaturated palette, "
         "soft directional daylight, film grain, no text, no watermark")


def build_prompts(d):
    era      = d["setting"]["era"]
    loc      = d["setting"]["location"]
    tone     = d["adapted_story"]["tone"]
    synopsis = d["adapted_story"]["synopsis"]
    palette  = d["adapted_story"]["palette"]

    world = (f"empty, uninhabited establishing reference image — no people, "
             f"no humans, no figures, no bodies, no corpse, nobody present "
             f"anywhere in frame. defines the visual world. "
             f"period and place: {era}, {loc}. mood: {tone}. "
             f"color palette: {palette}. consistent color palette, lighting "
             f"logic and material language. completely vacant, deserted, "
             f"empty of any person or body no matter what else is implied. "
             f"{STYLE}.")

    places = {}
    for p in d["places"]:
        clue_list = "; ".join(p["clues"])
        places[p["place_id"]] = (
            f"empty, uninhabited space — no people, no humans, no figures, "
            f"no bodies, no corpse, nobody present anywhere in frame. "
            f"{p['name']}. {p['description']} "
            f"this scene must clearly show: {clue_list} — as objects and "
            f"traces only, with no person or body present to go with them. "
            f"period and place: {era}, {loc}. mood: {tone}. "
            f"color palette: {palette}. "
            f"completely vacant, deserted, unoccupied, empty of any person "
            f"or body no matter what else is implied. {STYLE}.")

    portraits = {c["id"]: (f"portrait of a {c['age']}-year-old {c['gender']}, "
                           f"{c['occupation']}. {c['appearance']} "
                           f"context: {synopsis} "
                           f"setting: {era}. mood: {tone}. "
                           f"color palette: {palette}. "
                           f"waist-up framing, neutral background, even lighting. "
                           f"{STYLE}.")
                 for c in d["cast"]}
    return {"world": world, "places": places, "portraits": portraits}


STUDIO_TERMS = ["disney", "pixar", "dreamworks", "ghibli"]
STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "for", "with", "to", "and", "or",
    "korean", "folktale", "fairy", "tale", "tales", "myth", "legend", "legends",
    "novel", "classical", "pansori", "based", "original", "setting", "custom",
    "little", "big", "great", "old", "young", "new",
    "girl", "boy", "man", "woman", "king", "queen", "prince", "princess",
    "red", "white", "black", "gold", "silver", "snow",
    "hood", "riding", "match", "sun", "moon", "woodcutter",
    "night", "day", "house", "story",
    # 일반 명사인데 우연히 제목에 들어간 것들 (실제 IP 고유명사가 아님)
    "piper", "office", "startup", "theater", "theatre", "silent-film", "silent", "film",
}


def banned_terms(d):
    title = re.sub(r"\(.*?\)", "", d.get("source_title", ""))
    words = {w.strip(".,").lower() for w in title.split() if len(w) > 2}
    return (words - STOPWORDS) | set(STUDIO_TERMS)


HANGUL = re.compile(r"[가-힣]")

files = sorted(glob.glob("scenarios_en/*.json"))
print(f"검증 대상: {len(files)}개\n")

errors = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    scen = d["scenario_id"]

    try:
        P = build_prompts(d)
    except KeyError as e:
        errors.append((scen, f"KeyError {e}"))
        continue

    blob = " ".join([P["world"]] + list(P["places"].values()) + list(P["portraits"].values()))

    if HANGUL.search(blob):
        hits = set(HANGUL.findall(blob))
        errors.append((scen, f"한글 잔존: {hits}"))

    hits = [b for b in banned_terms(d) if re.search(rf"\b{re.escape(b)}\b", blob.lower())]
    if hits:
        errors.append((scen, f"고유명사 유입: {hits}"))

    # bgm 쪽에서 읽는 필드도 같이 확인
    for src in ("source_story", "adapted_story"):
        if not d[src].get("synopsis") or not d[src].get("tone"):
            errors.append((scen, f"{src} synopsis/tone 누락"))
    if not d["culture"].get("instruments"):
        errors.append((scen, "culture.instruments 누락"))

    n_places = len(d["places"])
    n_cast = len(d["cast"])
    print(f"  {scen:30s} 장소 {n_places} 인물 {n_cast}  OK")

print()
if errors:
    print(f"실패 {len(errors)}건:")
    for scen, msg in errors:
        print(f"  [{scen}] {msg}")
    raise SystemExit(1)
else:
    print("전부 통과.")
