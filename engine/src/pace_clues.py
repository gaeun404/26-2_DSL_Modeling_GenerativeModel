# -*- coding: utf-8 -*-
"""
pace_clues.py — 라운드별 단서 공개량을 고르게 편다(재미 지표 F11 '정보분산').

■ 왜
    23편이 라운드별 공개량 편차 4 이상이었다. 가장 심한 23편은 [12, 4, 4, 4] —
    1라운드에 12개가 쏟아지고 나머지 라운드가 비었다. 앞이 정신없고 뒤가 심심하다.

■ 어떻게 (보수적으로)
    1라운드에 몰리는 것은 대개 **검안·현장 단서**인데, 그건 자연스럽다 —
    현장을 먼저 보는 것이 순리다. 그래서 그것들은 **건드리지 않는다.**
    옮기는 것은 뒤로 미뤄도 이야기가 깨지지 않는 것만:
        · channel == "location" 인 비밀/소품 단서
        · weight == "red_herring" 인 소문
    옮기지 않는 것:
        · channel == "crime_scene" (검안·현장 — 1라운드의 뼈대)
        · decisive (결정타는 마지막 라운드 고정)
        · exculpates가 달린 단서 (배제 논리가 라운드에 묶여 있다)
        · alibi_break (알리바이 붕괴 시점이 설계돼 있다)
    그리고 1라운드에 최소 4개는 남긴다(첫 라운드가 비면 시작이 막막하다).

사용:
    python pace_clues.py            # 전 편
    python pace_clues.py --check    # 편차만 보고
"""
import json, glob, sys
from collections import Counter

MOVABLE_WEIGHT = {"red_herring", "secret", "context"}


def _dist(s):
    R = int(s["config"]["rounds"])
    c = Counter(x.get("reveal_round", 1) for x in s["clue_graph"])
    return [c.get(r, 0) for r in range(1, R + 1)]


def rebalance(s, min_first=4, max_spread=3):
    R = int(s["config"]["rounds"])
    moved = []
    for _ in range(40):                       # 넉넉한 반복 상한
        dist = _dist(s)
        if max(dist) - min(dist) <= max_spread:
            break
        src = dist.index(max(dist)) + 1       # 가장 많은 라운드
        dst = dist.index(min(dist)) + 1       # 가장 적은 라운드
        if dst <= src:                        # 앞으로 당기지 않는다(뒤로만 민다)
            later = [r for r in range(src + 1, R + 1)]
            if not later:
                break
            dst = min(later, key=lambda r: dist[r - 1])
        if src == 1 and dist[0] <= min_first:
            break
        cand = [
            c for c in s["clue_graph"]
            if c.get("reveal_round", 1) == src
            and c.get("channel") != "crime_scene"
            and not c.get("decisive")
            and not c.get("exculpates")
            and c.get("weight") != "alibi_break"
            and (c.get("channel") == "location" or c.get("weight") in MOVABLE_WEIGHT)
            # ★1라운드의 헛다리는 절대 빼지 않는다(2026-08-24).
            #   처음엔 소문부터 뒤로 밀었더니 1라운드에 '가리키는 단서'만 남아,
            #   성급하게 찍어도 범인이 맞는 편이 4편 생겼다(eval_policies 적발).
            #   헛다리는 초반 오도를 담당하는 장치다 — 앞에 있어야 한다.
            and not (src == 1 and c.get("weight") == "red_herring")
        ]
        if not cand:
            break
        # 뒤로 밀어도 가장 덜 아쉬운 것부터 — 장소 소품 → 정황 → (헛다리는 2라운드 이후만)
        cand.sort(key=lambda c: (c.get("channel") != "location",
                                 c.get("weight") != "context",
                                 c.get("weight") != "secret"))
        c = cand[0]
        c["reveal_round"] = dst
        moved.append((c["id"], src, dst))
    return moved


def run(path, check=False):
    s = json.load(open(path, encoding="utf-8"))
    before = _dist(s)
    if check:
        sp = max(before) - min(before)
        print(f"  {path.split('/')[-1][:26]:28} {before} 편차{sp}")
        return 0
    moved = rebalance(s)
    after = _dist(s)
    if moved:
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    mark = "" if not moved else f"  ← {len(moved)}개 이동"
    print(f"  {path.split('/')[-1][:26]:28} {before} → {after}"
          f" 편차{max(before)-min(before)}→{max(after)-min(after)}{mark}")
    return len(moved)


if __name__ == "__main__":
    check = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    n = sum(run(f, check) for f in files)
    print(f"\n{len(files)}편 · 단서 {n}개 재배치")
