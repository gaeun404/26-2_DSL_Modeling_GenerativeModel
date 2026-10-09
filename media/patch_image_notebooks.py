#!/usr/bin/env python3
"""
image_hidream.ipynb / image_flux2_klein.ipynb 를 20개 시나리오에 맞게 고친다.

1. BANNED 이름 검사 — cinderella/heungbu 2개짜리 하드코딩 리스트 대신,
   시나리오마다 자기 source_title 단어 + 스튜디오/프랜차이즈 명칭을 자동으로 금지어로
   써서 검사한다. (places/cast 텍스트엔 원래도 실명을 안 넣으므로 이 검사는 대개
   통과하지만, 원작 IP 명칭이 실수로 섞여 들어가는 것을 잡는 안전망이다.)
2. "생성 예정" 장수 계산 — 장소 7장·인물 6명 고정 가정을 걷어내고 실제 개수를 센다
   (13_푸른수염은 장소가 6이 아니라 7이라 고정값이 틀렸다).
3. composite("heungbu") / side_by_side("heungbu", ...) — 하드코딩된 시나리오 키와
   구 스키마 파일명(place_02, char_01)을 DATA 의 첫 시나리오에서 동적으로 뽑도록 바꾼다.
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent
NOTEBOOKS = ["image_hidream.ipynb", "image_flux2_klein.ipynb"]

OLD_BANNED_BLOCK = '''BANNED = ["cinderella", "prince charming", "nolbu", "heungbu", "disney"]
bad = []
for scen, v in P.items():
    blob = " ".join([v["world"]] + list(v["places"].values())
                    + list(v["portraits"].values())).lower()
    hits = [b for b in BANNED if b in blob]
    if hits:
        bad.append((scen, hits))

for scen, v in P.items():
    print("=" * 70); print(scen)
    print("  [world]", v["world"][:120], "...")
    print(f"  장소 {len(v['places'])} / 인물 {len(v['portraits'])}")

print()
print("이름 유입 검사:", "OK" if not bad else f"FAIL {bad}")
assert not bad, "입력 JSON의 occupation / location / place name 을 확인할 것"
print(f"생성 예정: 시나리오 {len(P)} x (world 1 + 장소 7 + 인물 6) = {len(P) * 14}장")'''

NEW_BANNED_BLOCK = '''# 시나리오마다 자기 source_title 단어를 금지어로 쓴다 — 하드코딩된 2개짜리
# 리스트 대신, 20개 전부에서 원작 고유명사가 새어 들어갔는지 자동으로 잡는다.
STUDIO_TERMS = ["disney", "pixar", "dreamworks", "ghibli"]

def banned_terms(d):
    import re
    title = re.sub(r"\\(.*?\\)", "", d.get("source_title", ""))
    words = {w.strip(".,").lower() for w in title.split() if len(w) > 2}
    return words | set(STUDIO_TERMS)

bad = []
for scen, v in P.items():
    blob = " ".join([v["world"]] + list(v["places"].values())
                    + list(v["portraits"].values())).lower()
    hits = [b for b in banned_terms(DATA[scen]) if b in blob]
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
      f"= {len(P) + total_places + total_portraits}장")'''

OLD_COMPOSITE_CALL = 'composite("heungbu")'
NEW_COMPOSITE_CALL = (
    '# 시나리오 하나만 골라 눈으로 확인한다 (전부 다 볼 필요는 없다).\n'
    'demo_scen = next(iter(DATA))\n'
    'composite(demo_scen)'
)

OLD_SIDE_BY_SIDE_CALLS = '''side_by_side("heungbu", "world_ref.png")
side_by_side("heungbu", "places/place_02.png")
side_by_side("heungbu", "portraits/char_01_p0.png")'''
NEW_SIDE_BY_SIDE_CALLS = '''demo_scen = next(iter(DATA))
demo_place = DATA[demo_scen]["places"][0]["place_id"]
demo_cast = DATA[demo_scen]["cast"][0]["id"]
side_by_side(demo_scen, "world_ref.png")
side_by_side(demo_scen, f"places/{demo_place}.png")
side_by_side(demo_scen, f"portraits/{demo_cast}_p0.png")'''


def patch_cell_source(src: str) -> tuple[str, int]:
    n = 0
    if OLD_BANNED_BLOCK in src:
        src = src.replace(OLD_BANNED_BLOCK, NEW_BANNED_BLOCK)
        n += 1
    if OLD_COMPOSITE_CALL in src:
        src = src.replace(OLD_COMPOSITE_CALL, NEW_COMPOSITE_CALL)
        n += 1
    if OLD_SIDE_BY_SIDE_CALLS in src:
        src = src.replace(OLD_SIDE_BY_SIDE_CALLS, NEW_SIDE_BY_SIDE_CALLS)
        n += 1
    return src, n


def main():
    for nb_name in NOTEBOOKS:
        path = ROOT / nb_name
        nb = json.loads(path.read_text(encoding="utf-8"))
        total = 0
        for cell in nb["cells"]:
            if cell.get("cell_type") != "code":
                continue
            src = "".join(cell.get("source", []))
            new_src, n = patch_cell_source(src)
            if n:
                cell["source"] = new_src.splitlines(keepends=True)
                cell["outputs"] = []
                cell["execution_count"] = None
                total += n
        if total:
            backup = path.with_suffix(path.suffix + ".bak3")
            if not backup.exists():
                shutil.copy2(path, backup)
            path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{nb_name}: {total}곳 교체")


if __name__ == "__main__":
    main()
