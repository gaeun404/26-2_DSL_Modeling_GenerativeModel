# -*- coding: utf-8 -*-
"""
retitle.py — 제목이 **사건을 스포하는지** 검사하고, 스포하면 갈아 끼운다.

왜 필요한가
  '녹아 사라진 칼'은 트릭(녹는 흉기)을 제목에서 다 말해 버린다.
  '놀부의 탕약'은 사인을 ???로 가려 놓고 제목이 독살이라 답한다.
  제목은 게임 시작 화면·수첩·사건 목록에 **처음부터** 뜨므로,
  시작 시점에 공개되지 않는 것(흉기·트릭·결정타·동기)은 제목에 못 들어간다.

허용: 현장 이름, 원작의 상징, 분위기 — 시작할 때 이미 보이는 것들
금지: 흉기 낱말, 결정타 단서 낱말, 트릭 이름 낱말, 동기 키워드

사용:
    python retitle.py --check      # 검사만
    python retitle.py --fix        # 스포 제목을 안전한 제목으로 교체(파일 전체에서 치환)
"""
import json, glob, os, re, sys

# 손으로 고른 안전 제목 — 무대·원작 상징·분위기까지만
SAFE = {
    "01": "청운당의 마지막 밤",
    "02": "황부자댁의 밤",
    "03": "장서각의 침묵",
    "04": "영남루의 달밤",
    "05": "취미궁의 꿈",
    "10": "저주받은 성의 밤",
    "12": "제비가 오지 않는 집",
    "14": "성문 누각의 밤비",
    "15": "금실의 탑",
    "17": "얼음 창고의 밤",
    "18": "성냥불이 꺼진 새벽",
    "19": "뒷산 연못의 달",
    "21": "불 꺼진 회의실",
    "22": "불 꺼진 회의실",
    "23": "두 옹고집의 밤",
    "25": "카라바 성의 밤",
    "27": "쫓겨나기 전날 밤",
    "29": "전당강의 홍등",
}

_STOP = {"살인", "사건", "위장", "오인", "은닉", "특정", "연결", "쏠림", "씌우기"}


def _terms(s):
    """제목에 들어가면 스포인 낱말들."""
    out = set()
    w = re.sub(r"\([^)]*\)", " ", s["death"].get("weapon", ""))
    for x in re.findall(r"[가-힣]{2,6}", w):
        out.add(x)
    tr = s.get("trick") or {}
    for x in re.findall(r"[가-힣]{2,6}", str(tr.get("name", "")) + " " + str(tr.get("kind", ""))):
        if x not in _STOP:
            out.add(x)
    for c in s["clue_graph"]:
        if c.get("decisive"):
            for x in re.findall(r"[가-힣]{3,8}", c.get("surface", ""))[:14]:
                out.add(x)
    for k in ((s.get("solution") or {}).get("motive_keywords") or []):
        out.add(str(k))
    # 시작부터 공개인 것은 허용 — 현장 이름·검안에 이미 나온 낱말
    seen = set()
    for p in s["map"]["places"]:
        for x in re.findall(r"[가-힣]{2,8}", p["name"]):
            seen.add(x)
    for line in (s["death"].get("scene_inspection") or [])[:2]:
        pass  # 검안 1~2줄은 무기 '갈래'만 말하므로 그대로 둔다(무기 이름은 금지 유지)
    return out - seen


def check(s):
    title = s["meta"].get("title", "")
    bad = [t for t in _terms(s) if t and t in title]
    return sorted(bad)


def main():
    fix = "--fix" in sys.argv
    changed = 0
    # 현장·원작 상징이라 괜찮은 편 — 린트가 걸어도 두는 목록
    ALLOW = {"06", "07", "08", "09", "11", "13", "16", "20", "43",
             "33", "36", "46", "50"}  # 33 봉인·궤 · 36 미궁 곳간 · 43 동남풍 · 46 항아리·표식 · 50 마디 — 전부 원작 상징이자 시작(나레이션·검안)부터 공개
    for f in sorted(glob.glob("scenarios/[0-9]*.json")):
        s = json.load(open(f, encoding="utf-8"))
        old = s["meta"].get("title", "")
        bad = check(s)
        no = os.path.basename(f)[:2]
        already = (old == SAFE.get(no))
        spoiler = (not already) and ((no in SAFE) or (bad and no not in ALLOW))
        if not spoiler:
            print(f"  ○ {no} {old}" + (f"  (린트: {', '.join(bad)} — 현장/원작 상징이라 허용)" if bad else ""))
            continue
        if not fix:
            print(f"  ✗ {no} {old} — " + (f"스포 낱말: {', '.join(bad)}" if bad else "손 목록"))
            continue
        new = SAFE.get(no)
        if not new:
            pc = next(p["name"] for p in s["map"]["places"] if p["id"] == s["death"]["place"])
            pc_clean = re.sub(r"\([^)]*\)", "", pc).strip()
            new = pc_clean + "의 밤"
        raw = open(f, encoding="utf-8").read()
        raw = raw.replace(old, new)          # 제목이 박힌 모든 자리(BGM 이름·UI·엔딩)를 함께 치환
        open(f, "w", encoding="utf-8").write(raw)
        print(f"  ✎ {no} {old} → {new}  (스포: {', '.join(bad)})")
        changed += 1
    print(f"\n{'교체' if fix else '검사'} 끝" + (f" · {changed}편 바꿈" if fix else ""))


if __name__ == "__main__":
    main()
