# -*- coding: utf-8 -*-
"""
measure_difficulty.py — **예산 제약이 있는 플레이**로 편별 난이도를 잰다.

기존 별점은 `simulate.py`의 몬테카를로 정답률에 55% 의존했는데, 그 모델엔
자원 제약이 없다. 그래서 예산을 넣자 순위가 뒤집혔다 — ★★★★가 100%로 전 등급 중
가장 쉽고 ★★★★★가 25%였다.

이 스크립트는 라운드당 예산 8로 **여러 실력 × 여러 시드**를 돌려
편마다 안정적인 '해결률'을 낸다. stars.py는 이 값을 쓴다.
"""
import json, glob, sys, random, statistics as st
from tune_turns import play_budget

BUDGET = 8
SKILLS = [0.4, 0.55, 0.7, 0.85]     # 서툰 사람부터 능숙한 사람까지
SEEDS = [11, 29, 47, 83, 101]


def measure(path, budget=BUDGET):
    ok = conf = 0; pts = []; n = 0
    for sk in SKILLS:
        for sd in SEEDS:
            r = play_budget(path, budget, sk, random.Random(sd))
            n += 1
            ok += r["correct"]; conf += r["confident"]; pts.append(r["points"])
    return {"solve": ok / n, "confident": conf / n,
            "points": st.mean(pts), "max": 10, "n": n}


if __name__ == "__main__":
    files = [a for a in sys.argv[1:] if not a.startswith("-")] or sorted(glob.glob("[0-9]*.json"))
    rows = []
    for f in files:
        m = measure(f)
        s = json.load(open(f, encoding="utf-8"))
        rows.append((m["solve"], f, s["meta"]["title"],
                     (s.get("stars") or {}).get("n", 0), m))
    rows.sort()
    print(f"{'해결률':>6} {'확신':>6} {'평균점':>6}  {'현별점':>6}  편")
    print("-" * 72)
    for solve, f, title, old, m in rows:
        print(f"{solve*100:5.0f}% {m['confident']*100:5.0f}% {m['points']:6.1f}  "
              f"{'★'*old:6}  {f[:22]:24} {title[:18]}")
    print("-" * 72)
    print(f"평균 해결률 {st.mean(r[0] for r in rows)*100:.0f}% "
          f"· 범위 {min(r[0] for r in rows)*100:.0f}~{max(r[0] for r in rows)*100:.0f}%")
