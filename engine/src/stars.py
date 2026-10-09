# -*- coding: utf-8 -*-
"""
stars.py — 시나리오마다 **별 다섯 개 난이도**를 매긴다.

■ 왜
    기존 난이도는 몬테카를로 정답률(`difficulty.solve_rate`)과 3단 티어(쉬움/중/어려움)뿐이었다.
    목록 화면에서 고를 때 3단은 너무 성기고, 정답률 숫자(0.63)는 플레이어에게 와닿지 않는다.

■ 어떻게 매기나 — **예산 제약이 있는 실제 플레이로 잰다** (2026-08-25 재보정)
    전에는 simulate.py의 몬테카를로 정답률에 55% 의존했다. 그런데 그 모델엔
    **자원 제약이 없다.** 라운드당 행동 예산을 8로 넣고 재 보니 순위가 뒤집혔다 —
    ★★★★가 적중 100%로 전 등급 중 가장 쉬웠고 ★★★★★가 25%였다.

    이제 measure_difficulty.py가 **예산 8 · 실력 4단 × 시드 5개 = 편당 20판**을 돌려
    세 가지를 재고, 그것으로 난이도를 만든다.

      ① 해결률(solve)      가중 45 — 범인을 짚었는가
      ② 확신율(confident)  가중 35 — 근거가 한 사람만 가리켰는가.
                                    "다 해도 헷갈리는가"가 여기서 잡힌다
      ③ 점수(points)       가중 20 — 비밀까지 캤는가

    난이도 = (1-해결)*0.45 + (1-확신)*0.35 + (1-점수/10)*0.20
    50편 실측 분포의 오분위로 다섯 칸을 가른다(각 9~11편으로 고르게 찬다).

사용:
    python stars.py                 # 전 편
    python stars.py --table         # 별점 분포표
"""
import json, glob, sys, statistics as st

BANDS = [
    (1, "★☆☆☆☆", "가볍게",   "처음 해 보는 사람에게. 단서가 곧게 이어진다"),
    (2, "★★☆☆☆", "무난하게", "한 번쯤 헤매지만 길을 잃지는 않는다"),
    (3, "★★★☆☆", "제법",     "표준. 메모를 해야 풀린다"),
    (4, "★★★★☆", "만만찮게", "트릭이 꼬여 있다. 두 번은 들여다봐야 한다"),
    (5, "★★★★★", "혹독하게", "정답률이 낮다. 각오하고 들어가라"),
]


def _score_from_play(m):
    """예산 제약 플레이 측정값 → 난이도 점수(0~1). 높을수록 어렵다."""
    total = ((1 - m["solve"]) * 0.45
             + (1 - m["confident"]) * 0.35
             + (1 - m["points"] / 10.0) * 0.20)
    return total, dict(solve=round(m["solve"], 2),
                       confident=round(m["confident"], 2),
                       points=round(m["points"], 1),
                       trials=m["n"], budget=8,
                       measured_by="budget_play_4skills_x_5seeds")


def _band(total):
    """경계는 예산 8 실측 난이도 분포의 오분위. 각 칸이 9~11편으로 고르게 찬다.
    (난이도가 높을수록 별이 많다 — total이 클수록 어렵다)"""
    # 2026-08-25 2차 재보정 — spine 단서를 장소 탐색에서 뺀 뒤 판이 전반적으로
    #   어려워져, 옛 경계로는 50편 중 26편이 ★5로 몰렸다. 별점이 변별을 못 하면
    #   없느니만 못하므로 현재 빌드의 실측 분포로 오분위를 다시 잡았다.
    for cut, b in zip((0.180, 0.278, 0.364, 0.592), BANDS):
        if total < cut:
            return b
    return BANDS[4]


def enrich(path, write=True):
    from measure_difficulty import measure          # 예산 제약 플레이로 잰다
    s = json.load(open(path, encoding="utf-8"))
    total, parts = _score_from_play(measure(path))
    n, stars, label, blurb = _band(total)
    s["stars"] = {
        "n": n, "stars": stars, "label": label, "blurb": blurb,
        "score": round(total, 3),
        "basis": parts,
        "note": "라운드당 행동 예산 8로 실력 4단 × 시드 5개 = 20판을 돌려 잰 값. "
                "해결률 45% + 확신율 35% + 점수 20%. "
                "simulate.py의 몬테카를로는 자원 제약이 없어 실제 난이도와 어긋났다(2026-08-25 재보정).",
        "how_shown": "목록·시작 화면에 별 다섯 개로 표시한다. label은 한 줄 설명.",
    }
    if write:
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return s["meta"].get("title", ""), s["stars"], parts


if __name__ == "__main__":
    table = "--table" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    rows = []
    for f in files:
        title, st_, parts = enrich(f, write=not table)
        rows.append((st_["n"], st_["stars"], st_["score"], parts["solve"],
                     parts["confident"], parts["points"], 0,
                     f.split("/")[-1][:2], title))
    rows.sort()
    print(f"{'별':6} {'난이도':>6} {'해결':>6} {'확신':>6} {'점수':>6}  편  제목")
    for n, stars, sc, solve, conf, pts, _x, no, title in rows:
        print(f"{stars} {sc:6.3f} {solve*100:5.0f}% {conf*100:5.0f}% {pts:6.1f}  {no}  {title}")
    from collections import Counter
    c = Counter(r[0] for r in rows)
    print("\n분포:", " · ".join(f"{BANDS[k-1][1]} {c.get(k,0)}편" for k in range(1, 6)))
