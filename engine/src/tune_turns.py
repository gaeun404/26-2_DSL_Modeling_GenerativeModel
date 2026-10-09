# -*- coding: utf-8 -*-
"""
tune_turns.py — **적절한 행동 예산**을 실험으로 고른다.

■ 왜 (찬열이형, 2026-08-25)
    "다 해도 범인이 헷갈려야 되는데… 턴도 난이도랑 게임요소들 고려해서 실험해보고
     적절한 횟수 고르자"

    지금은 정공법이 50/50 만점입니다. 재보니 **턴 사용률 42%**,
    탐색은 아예 무제한·공짜였습니다. 자원이 남아도니 선택할 것이 없고,
    선택이 없으니 **다 해 보면 언제나 확신에 이릅니다.**

■ 무엇을 바꿔 실험하나
    ① 공용 예산 — 탐색·심문·감식·대질이 **같은 주머니**를 쓴다.
       그래야 "방을 더 뒤질까, 사람을 더 파고들까"가 결정이 된다.
    ② 행동별 비용 — 탐색 1 / 심문 1 / 감식 1 / 대질 2 (대질은 원래 2턴)
    ③ 예산 크기를 훑어 가며(라운드당 4~16) 결과가 어떻게 갈리는지 본다

■ 무엇을 목표로 하나
    · 범인 적중은 **되긴 하되 늘 되지는 않게** (70~85% 근처)
    · 확신(근거가 한 사람만 가리킴)은 그보다 낮게 — 다 해도 헷갈려야 한다
    · 만점(10점)은 드물게 — 만점이 흔하면 잘한 보람이 없다

사용:
    python3 tune_turns.py                # 50편 전수 스윕
    python3 tune_turns.py 91_dsl_demo.json
"""
import sys, json, glob, os, statistics as st
from game_engine_v2 import GameSession
from policy_play import deduce

COST = {"search": 1, "talk": 1, "inspect": 1, "confront": 2}


def _findable_here(g, s, pid):
    """이 장소 이 라운드에 아직 못 찾은 단서가 몇 개인가 — 우선순위 판단용."""
    ps = next((x for x in s["ui"]["place_screens"] if x["place_id"] == pid), None)
    if not ps:
        return 0
    rd = (ps.get("rounds") or {}).get(str(g.current_round)) or {}
    return sum(1 for a in (rd.get("actions") or [])
               if a.get("finds") and a["finds"] not in g.held_clues)


def play_budget(path, budget, skill=1.0, rng=None):
    """공용 예산 budget(라운드당)으로 한 판.

    skill=1.0 → 완벽한 플레이(단서 있는 선택지만 고른다)
    skill<1.0 → 실제 플레이어처럼 **헛수고도 한다**. 0.6이면 선택의 40%가 빗나간다.
                완벽한 플레이만 재면 예산을 과소평가하게 된다.
    """
    import random as _r
    rng = rng or _r.Random(12345)
    s = json.load(open(path, encoding="utf-8"))
    g = GameSession(s)
    spent = {"search": 0, "talk": 0, "inspect": 0, "confront": 0}
    # ★예산을 갈래별로 나눠 쓴다.
    #   처음엔 "탐색 먼저 → 남으면 심문"으로 짰더니, 실력이 낮을 때 탐색이 예산을 다 먹어
    #   **심문을 한 번도 못 했고**, 그 바람에 예산 5·6·7의 결과가 똑같이 나왔다.
    #   실제 플레이어는 번갈아 한다 — 절반은 방을 뒤지고 절반은 사람을 판다.
    while True:
        pool = budget
        n_search = max(1, round(pool * 0.5))
        n_talk = max(1, pool - n_search)

        # ① 방을 뒤진다
        places = sorted((ps["place_id"] for ps in s["ui"]["place_screens"]),
                        key=lambda p: -_findable_here(g, s, p))
        if skill < 1.0:
            rng.shuffle(places)                   # 어디가 알짜인지 모른다
        used = 0
        for pid in places:
            if used >= n_search:
                break
            ps = next(x for x in s["ui"]["place_screens"] if x["place_id"] == pid)
            rd = (ps.get("rounds") or {}).get(str(g.current_round)) or {}
            acts = list(enumerate(rd.get("actions") or []))
            if skill < 1.0:
                rng.shuffle(acts)
            for i, a in acts:
                if used >= n_search:
                    break
                useful = bool(a.get("finds")) and a["finds"] not in g.held_clues
                if not useful and rng.random() < skill:
                    continue                      # 실력이 좋을수록 헛수고를 피한다
                g.search(pid, i)
                used += COST["search"]; spent["search"] += 1
        pool -= used

        # ② 사람을 판다
        used = 0
        cids = list(g.cast)
        if skill < 1.0:
            rng.shuffle(cids)
        for cid in cids:
            if used >= n_talk or pool - used < COST["talk"]:
                break
            c = g.cast[cid]
            pp = (c.get("pressure_points") or [{}])[0]
            trigs = pp.get("trigger") or ["그날 밤"]
            # 실력이 낮으면 정곡을 못 찌른다 — 엉뚱한 것을 묻는다
            q = (trigs[0] if rng.random() < skill else "그날 밤에 대해") + "에 대해 말해 보시오."
            r = g.interrogate(cid, q, evidence_shown=(rng.random() < skill))
            if "error" in r:
                break
            used += COST["talk"]; spent["talk"] += 1
        pool -= used

        # ③ 감식 — ★예산 밖. 이미 찾은 것을 '더 자세히 보는' 파생 행동이라
        #    탐색·심문과 예산을 다투면 예산 10 이하에서 한 번도 안 쓰인다(실측 0회).
        #    예산은 **무엇을 알아낼까(방이냐 사람이냐)**의 선택에만 쓴다.
        for pid in list(g.inspections):
            if g.inspect(pid).get("success"):
                spent["inspect"] += 1
        # ④ 대질 — ★공용 예산 밖의 **별도 1회 토큰**이다.
        #    예산에서 빼니 예산 10 이하에서는 한 번도 발동하지 않았다.
        #    한 판에 한 번뿐인 특별 행동이 일상 행동과 예산을 다투면 영영 안 쓰인다.
        if spent["confront"] == 0 and g.current_round >= g.confront_unlock_round:
            for (a, b) in list(g.cx_pairs):
                r = g.confront(a, b, "그 시각 어디 있었는지 다시 말해 보시오.")
                if "error" not in r:
                    spent["confront"] += 1
                    break
        # 조합은 공짜 — 수첩에서 생각하는 일이라 행동이 아니다
        for pair in list(g.composite_clues):
            if all(x in g.held_clues for x in pair):
                g.combine(pair[0], pair[1])
        g.turns_left = 10 ** 6      # 예산은 이 함수가 관리한다(엔진 턴 제한은 끈다)
        if "error" in g.next_round():
            break
    d = deduce(g)
    truth = s["solution"]["culprit"]
    return {"correct": d["pick"] == truth, "confident": d["confident"],
            "points": d["points"], "max": d["max"], "tie": len(d["tie"]),
            "spent": spent, "clues": len(g.held_clues),
            "stars": (s.get("stars") or {}).get("n", 3)}


def by_stars(files, budget, skill):
    """난이도(별점)별로 갈라 본다 — 어려운 편일수록 예산이 더 아쉬울 것이다."""
    buckets = {}
    for f in files:
        try:
            r = play_budget(f, budget, skill)
        except Exception:
            continue
        buckets.setdefault(r["stars"], []).append(r)
    print(f"\n  예산 {budget}/R · 실력 {skill:.1f}")
    print(f"  {'별점':6} {'편수':>4} {'적중':>7} {'확신':>7} {'만점':>7} {'평균점':>7}")
    for n in sorted(buckets):
        rs = buckets[n]; k = len(rs)
        print(f"  {'★'*n:6} {k:4} "
              f"{sum(r['correct'] for r in rs)/k*100:6.0f}% "
              f"{sum(r['confident'] for r in rs)/k*100:6.0f}% "
              f"{sum(1 for r in rs if r['points']>=r['max'])/k*100:6.0f}% "
              f"{st.mean(r['points'] for r in rs):7.1f}")


def sweep(files, budgets, skill=1.0):
    print(f"{'예산/R':>6} {'적중':>7} {'확신':>7} {'만점':>7} {'평균점':>7} "
          f"{'탐색':>5} {'심문':>5} {'감식':>5} {'대질':>5}")
    print("-" * 68)
    out = []
    for b in budgets:
        rs = []
        for f in files:
            try:
                rs.append(play_budget(f, b, skill))
            except Exception:
                pass
        n = len(rs)
        ok = sum(r["correct"] for r in rs) / n * 100
        cf = sum(r["confident"] for r in rs) / n * 100
        full = sum(1 for r in rs if r["points"] >= r["max"]) / n * 100
        pts = st.mean(r["points"] for r in rs)
        sp = {k: st.mean(r["spent"][k] for r in rs) for k in COST}
        out.append((b, ok, cf, full, pts))
        print(f"{b:6} {ok:6.0f}% {cf:6.0f}% {full:6.0f}% {pts:7.1f} "
              f"{sp['search']:5.1f} {sp['talk']:5.1f} {sp['inspect']:5.1f} {sp['confront']:5.1f}")
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("[0-9]*.json"))
    print("=" * 68)
    print(f" 공용 행동 예산 스윕 — {len(files)}편 · 비용 탐색1/심문1/감식1/대질2")
    print("=" * 68)
    for sk, label in ((1.0, "완벽한 플레이"), (0.6, "실제 플레이어(헛수고 40%)")):
        print(f"\n■ {label}")
        sweep(files, [4, 5, 6, 7, 8, 10, 12], skill=sk)
    for b in (5, 6, 7):
        by_stars(files, b, 0.6)
    print("\n" + "=" * 68)
    print(" 목표: 적중 70~85% · 확신은 그보다 낮게 · 만점은 드물게")
    print("=" * 68)


if __name__ == "__main__":
    main()
