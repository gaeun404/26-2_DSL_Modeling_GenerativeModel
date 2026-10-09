# -*- coding: utf-8 -*-
"""
era.py — **시대에 맞는 광원·재질·카메라**를 한 곳에서 정한다.

■ 왜 (2026-08-25)
  그림 지시가 전 편에 같은 문장으로 박혀 있었다.

      "촛불·등불 하나뿐인 어둠. 그림자가 길고 윤곽만 남는다"
      "period-accurate, candlelit, painterly"

  91편은 **2020년대 연세대 중앙도서관 6층 세미나실**이다. 빔프로젝터가 돌아가고
  형광등이 켜져 있는 방인데 촛불로 그리라고 적혀 있었다. 조선 관아든 중세 성이든
  현대 스터디룸이든 같은 지시가 나가니, 이미지팀이 무엇을 뽑아도 어긋난다.

  광원은 시대가 정한다. 그래서 **한 표로 모아 두고 모든 프롬프트가 여기서 꺼내 쓴다.**

■ 쓰는 법
    from era import palette
    p = palette(scenario)          # 광원·재질·카메라·금지 목록
    p["light_ko"] · p["light_en"] · p["negative_en"] · p["texture_en"]
"""
import re

# 시대 → 그림의 결. 키는 setting_raw.era / culture에서 찾을 낱말이다.
_TABLE = [
    # ── 현대 ──────────────────────────────────────────────────────────
    (("현대", "2020", "2010", "스타트업", "오피스", "대학"), {
        "key": "contemporary",
        "light_ko": "천장 형광등과 화면 불빛. 그림자가 옅고 색이 차다. "
                    "창밖은 밤이라 유리에 실내가 비친다",
        "light_en": "cool fluorescent ceiling light mixed with screen glow, "
                    "flat soft shadows, night reflected in the window glass",
        "texture_en": "clean modern interior, laminate and steel, "
                      "cables and paper cups, contemporary Korean university",
        "camera_en": "photographic realism, 35mm, natural perspective",
        "negative_en": "candles, lanterns, torches, hanbok, period costume, "
                       "medieval, wooden beams, oil lamp, sepia",
    }),
    # ── 근대(19세기~20세기 초) ────────────────────────────────────────
    (("근대", "19세기", "20세기", "개화기", "경성"), {
        "key": "modern_early",
        "light_ko": "가스등과 초기 전등. 노란빛이 고르지 않고 구석이 어둡다",
        "light_en": "gaslight and early electric bulbs, uneven warm pools of light, "
                    "dark corners",
        "texture_en": "late-19th-century interior, painted plaster and heavy fabric, "
                      "printed paper and glass",
        "camera_en": "painterly realism, soft grain",
        "negative_en": "smartphones, computers, LED, fluorescent, modern clothing, plastic",
    }),
    # ── 조선·동아시아 전근대 ─────────────────────────────────────────
    (("조선", "한국 전통", "관아", "궁중", "사찰", "명나라", "당나라", "고도"), {
        "key": "joseon",
        "light_ko": "문살을 넘어오는 등잔불과 달빛. 창호지가 빛을 부드럽게 퍼뜨린다. "
                    "방 안쪽은 먹처럼 어둡다",
        "light_en": "oil lamp and moonlight diffused through hanji paper screens, "
                    "warm low light, ink-dark depths",
        "texture_en": "Korean traditional interior, wooden beams and paper doors, "
                      "hanbok, celadon and brassware, straw mat floor",
        "camera_en": "painterly realism, ink-wash depth",
        "negative_en": "electricity, glass windows, modern clothing, plastic, "
                       "European furniture, chandeliers",
    }),
    # ── 옛 일본 ──────────────────────────────────────────────────────
    (("일본", "옛 일본"), {
        "key": "japan_old",
        "light_ko": "행등과 달빛. 장지문 너머로 그림자가 비친다",
        "light_en": "andon lantern and moonlight, silhouettes cast on shoji screens",
        "texture_en": "old Japanese interior, tatami and shoji, kimono, "
                      "lacquer and unfinished cedar",
        "camera_en": "painterly realism, ukiyo-e composition sense",
        "negative_en": "electricity, modern clothing, plastic, European furniture",
    }),
    # ── 중세·근세 유럽 ───────────────────────────────────────────────
    (("중세", "유럽", "왕국", "궁정", "영지", "독일", "북유럽", "그리스"), {
        "key": "europe_old",
        "light_ko": "촛대와 벽난로. 불빛이 흔들려 그림자가 함께 움직인다. "
                    "높은 창으로 푸른 밤빛이 든다",
        "light_en": "candelabra and hearth fire, flickering shadows, "
                    "cold blue night through tall windows",
        "texture_en": "stone walls and heavy oak, tapestry and pewter, "
                      "period European costume",
        "camera_en": "painterly chiaroscuro, old-master palette",
        "negative_en": "electricity, modern clothing, plastic, hanbok, "
                       "Asian architecture, neon",
    }),
    # ── 중화권(청·송·한) ─────────────────────────────────────────────
    (("청나라", "북송", "후한", "중화권", "강남", "산동", "적벽", "양산박"), {
        "key": "china_old",
        "light_ko": "종이 등롱과 달빛. 처마 밑이 깊게 어둡고, 물가면 물에 불빛이 흔들린다",
        "light_en": "paper lanterns and moonlight, deep shadow under wide eaves, "
                    "lamplight rippling on water where there is a river",
        "texture_en": "old Chinese interior and riverside, dark timber and lattice windows, "
                      "hanfu robes, porcelain and lacquer, banners",
        "camera_en": "painterly realism, scroll-painting depth",
        "negative_en": "electricity, modern clothing, plastic, European furniture, hanbok",
    }),
    # ── 아랍·페르시아 ────────────────────────────────────────────────
    (("아랍", "페르시아", "바그다드", "사막"), {
        "key": "arabian",
        "light_ko": "구멍 뚫린 놋등에서 새는 불빛. 벽에 무늬가 어른거린다",
        "light_en": "pierced brass lantern casting patterned light on the walls, "
                    "warm amber glow",
        "texture_en": "carved plaster and tile, carpets and cushions, "
                      "brass and silk, arched openings",
        "camera_en": "painterly realism, ornamental composition",
        "negative_en": "electricity, modern clothing, plastic, European furniture",
    }),
]

_FALLBACK = {
    "key": "generic",
    "light_ko": "등불 하나가 비추는 어둠. 윤곽만 남는다",
    "light_en": "single lamp in darkness, rim-lit forms",
    "texture_en": "period-accurate interior",
    "camera_en": "painterly realism",
    "negative_en": "text, watermark, modern logos",
}

_COMMON_NEG = "text, watermark, signature, extra fingers, deformed hands, "\
              "logos, subtitles, caption bars"


def palette(s):
    """이 시나리오의 그림 결. setting_raw의 era·culture로 고른다."""
    raw = ((s.get("background") or {}).get("setting_raw") or {})
    hay = " ".join([str(raw.get("era", "")), str(raw.get("culture", "")),
                    str(raw.get("location", ""))])
    for keys, val in _TABLE:
        if any(k in hay for k in keys):
            out = dict(val)
            out["negative_en"] = out["negative_en"] + ", " + _COMMON_NEG
            out["era_ko"] = raw.get("era", "")
            return out
    out = dict(_FALLBACK)
    out["negative_en"] = out["negative_en"] + ", " + _COMMON_NEG
    out["era_ko"] = raw.get("era", "")
    return out


def is_contemporary(s):
    return palette(s)["key"] == "contemporary"


if __name__ == "__main__":
    import json, glob, collections
    c = collections.Counter()
    for f in sorted(glob.glob("scenarios/[0-9]*.json")):
        sc = json.load(open(f, encoding="utf-8"))
        c[palette(sc)["key"]] += 1
    for k, v in c.most_common():
        print(f"{v:3}편  {k}")
