# -*- coding: utf-8 -*-
"""
placeart.py — **장소 그림 지시를 이미지팀이 그대로 쓸 수 있게 다시 쓴다.**

■ 왜 (2026-08-25, 이미지팀 요청 "장소·장면들 더 구체적으로")
  지금 장소 아트 지시는 이랬다.

      prompt_ko : "빔프로젝터와 긴 테이블이 있는 중앙도서관 6층 세미나실. 사건의 현장"
      prompt_en : "interior of 세미나실(중도 6층), period-accurate, candlelit, painterly…"

  ① 한국어는 desc 한 줄 그대로다 — 구도도 광원도 시각도 없다.
  ② 영어에 **한국어 장소 이름이 그대로** 박혀 있다. 모델이 읽지 못한다.
  ③ 2020년대 대학 도서관에 **candlelit**이라고 적혀 있다(era.py로 해결).
  ④ 무엇이 반드시 보여야 하는지가 없다. 그런데 탐색 선택지는
     「노트북의 영상 파일을 들여다본다」처럼 **그림 속 물건을 가리킨다.**
     그림에 노트북이 없으면 플레이어가 누를 것이 화면에 없다.

■ 새로 넣는 것
    art.prompt_ko    [공간]/[시각]/[반드시 보일 것]/[광원]/[카메라] 다섯 토막
    art.prompt_en    실제 영어. 장소는 번역·의역해서 넣는다
    art.negative_en  이 시대에 나오면 안 되는 것
    art.must_show    탐색 선택지가 가리키는 물건 — 빠지면 화면이 성립하지 않는다
    art.time_of_day  사건 시각 기준
    art.variants     사건 전 / 사건 후 (현장만) — 같은 앵글, 달라진 것 하나
    map_thumb        지도에 박을 작은 그림 — 같은 규격, 인물 없음

사용:
    python3 placeart.py                       # 전 편
    python3 placeart.py out/91_dsl_demo.json
    python3 placeart.py --check               # 고치지 않고 개수만
"""
import json, glob, re, sys
from era import palette

# 장소 이름을 영어로 옮길 때 쓰는 최소 사전. 없으면 desc에서 짐작한다.
_EN = [
    ("세미나실", "university seminar room"), ("도서관", "library"),
    ("복도", "corridor"), ("자판기", "vending machine area"),
    ("사물함", "locker room"), ("카페", "cafe"), ("커피", "coffee shop"),
    ("주막", "roadside tavern"), ("객주", "merchant inn"), ("객방", "guest room"),
    ("사랑채", "men's quarters of a hanok"), ("안방", "inner room of a hanok"),
    ("곳간", "storehouse"), ("부엌", "kitchen"), ("마구간", "stable"),
    ("서재", "study"), ("장서각", "archive hall"), ("동헌", "magistrate's hall"),
    ("관아", "government office"), ("누각", "pavilion"), ("정자", "pavilion"),
    ("처소", "private quarters"), ("별당", "detached quarters"),
    ("무도회", "ballroom"), ("연회", "banquet hall"), ("성", "castle"),
    ("탑", "tower"), ("숲", "forest"), ("오두막", "hut"), ("산막", "mountain hut"),
    ("우물", "well"), ("뜰", "courtyard"), ("마당", "courtyard"),
    ("시장", "market"), ("저잣거리", "market street"), ("배", "boat"),
    ("강", "riverside"), ("막사", "military tent"), ("사당", "shrine"),
    ("절", "temple"), ("방앗간", "mill"), ("헛간", "barn"),
]


def _en_place(name, desc):
    for ko, en in _EN:
        if ko in name:
            return en
    for ko, en in _EN:
        if ko in (desc or ""):
            return en
    return "interior room"


def _objects(s, pid):
    """이 장소의 탐색 선택지가 가리키는 물건들 — 그림에 **반드시** 있어야 한다."""
    out = []
    for ps in ((s.get("ui") or {}).get("place_screens") or []):
        if ps.get("place_id") != pid:
            continue
        for rd in (ps.get("rounds") or {}).values():
            for a in (rd.get("actions") or []):
                # 선택지 이름에서 **물건만** 떼어 낸다.
                #   "명패를 뒤져 본다" → "명패"  ("뒤져 본다"는 동사라 물건이 아니다)
                lab = str(a.get("label") or "").strip()
                m = re.match(r"^(.+?)[을를]\s+.+$", lab)
                if not m:
                    continue                     # 물건을 못 떼면 버린다
                o = m.group(1).strip()
                if o and o not in out and o not in ("방 전체",) and len(o) >= 2:
                    out.append(o)
    return out[:8]


def build(s, p):
    pal = palette(s)
    d = s.get("death") or {}
    dslot = d.get("time_slot", "밤")
    is_scene = p["id"] == d.get("place")
    name, desc = p["name"], (p.get("desc") or "").strip()
    feats = [x for x in (p.get("features") or []) if x]
    objs = _objects(s, p["id"]) or feats
    en_place = _en_place(name, desc)

    must = list(dict.fromkeys(feats + objs))[:8]
    must_line = ", ".join(must) if must else "장소를 알아볼 수 있는 물건 두어 가지"

    ko = (
        f"[공간] {desc or name}. 사람은 그리지 않는다. "
        f"방 전체가 한눈에 들어오는 넓은 구도. "
        f"[시각] {dslot}. {'주검은 그리지 않는다 — 자리만 비워 둔다. ' if is_scene else ''}"
        f"[반드시 보일 것] {must_line}. "
        f"이 물건들은 플레이어가 눌러 조사하는 자리라, 하나라도 빠지면 화면이 성립하지 않는다. "
        f"[광원] {pal['light_ko']}. "
        f"[카메라] 눈높이보다 조금 위, 정면에 가까운 각. 왼쪽 아래를 비워 둔다 — "
        f"인물 서 있는 그림이 그 자리에 겹친다."
    )
    # ★영어 프롬프트에는 **한국어를 섞지 않는다** (2026-08-25).
    #   전에는 "interior of 세미나실(중도 6층)"처럼 한글이 그대로 박혀 있었다.
    #   모델이 읽지 못하는 글자다. 물건 목록은 한국어 지시(prompt_ko)와
    #   must_show가 갖고 있으므로, 영어에는 **구도·광원·재질**만 싣는다.
    en = (
        f"{en_place} at night, {pal['texture_en']}, "
        f"wide establishing interior shot, no people, "
        f"key props clearly readable in frame, "
        f"{pal['light_en']}, {pal['camera_en']}, "
        f"slightly above eye level, near-frontal, "
        f"lower-left third left empty for a character overlay, "
        f"1045x600 landscape"
    )

    art = {
        "w": 1045, "h": 600,
        "time_of_day": dslot,
        "must_show": must,
        "must_show_note": "탐색 선택지가 이 물건들을 가리킨다. 빠지면 누를 것이 없다.",
        "no_people": True,
        "reserve": "왼쪽 아래 3분의 1 — 인물 서 있는 그림이 겹치는 자리",
        "prompt_ko": ko,
        "prompt_en": en,
        "negative_en": pal["negative_en"],
        "era": pal["era_ko"],
        "palette_key": pal["key"],
    }
    if is_scene:
        art["variants"] = {
            "pre_murder": {
                "when": "오프닝 나레이션 — 아직 아무 일도 없던 때",
                "diff": "같은 앵글. 자리에 사람들이 앉아 있던 흔적만 있고 어지럽지 않다.",
                "prompt_en": en.replace("no people", "no people, tidy and undisturbed"),
            },
            "post_murder": {
                "when": "현장 화면 — 사건이 지나간 뒤",
                "diff": "같은 앵글. 의자 하나가 밀려나 있고 잔이 쓰러져 있다. "
                        "주검은 그리지 않는다.",
                "prompt_en": en.replace("no people",
                                        "no people, one chair pushed back, "
                                        "a cup tipped over, subtle disarray"),
            },
            "note": "★두 벌은 **같은 앵글**이어야 한다. 달라진 것 하나가 보여야 한다.",
        }

    thumb = {
        "w": 320, "h": 200,
        "prompt_ko": f"{name} — 지도에 박을 작은 그림. {desc or name} "
                     f"멀리서 본 한 컷. 사람 없음. 무엇인지 한눈에 알아볼 수 있게 단순하게.",
        "prompt_en": (f"small map icon illustration of a {en_place}, seen from a distance, "
                      f"simple readable silhouette, no people, {pal['texture_en']}, "
                      f"{pal['light_en']}, 320x200"),
        "negative_en": pal["negative_en"],
    }
    return art, thumb


def enrich(path, check=False):
    s = json.load(open(path, encoding="utf-8"))
    screens = {x.get("place_id"): x for x in
               ((s.get("ui") or {}).get("place_screens") or [])}
    n = 0
    for p in s["map"]["places"]:
        art, thumb = build(s, p)
        sc = screens.get(p["id"])
        if sc is None:
            continue
        sc["art"] = art
        sc["map_thumb"] = thumb
        n += 1
    if not check:
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  {path.split('/')[-1][:28]:30s} 장소 그림 지시 {n}곳 · {palette(s)['key']}")
    return n


if __name__ == "__main__":
    check = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    tot = sum(enrich(f, check) for f in files)
    print(f"\n{len(files)}편 · 장소 {tot}곳")
