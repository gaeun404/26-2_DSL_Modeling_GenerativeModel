# -*- coding: utf-8 -*-
"""
policy_play.py — **여러 플레이 방식**으로 한 편을 반복해 돌려 본다.

play_demo.py는 "한 판이 어떻게 굴러가는가"를 본다.
이건 "**다르게 플레이하면 다르게 끝나는가**"를 본다 — 같은 사건을 여섯 부류가 각자의 방식으로
풀게 하고, 무엇을 손에 넣었고 범인을 짚을 수 있었는지 비교한다.

※ LLM 문장 생성은 쓰지 않는다. 용의자의 **판단**은 stance(태도 상태기계) + pressure(압박 게이지)가
   내리고, LLM은 그 판단을 문장으로 옮길 뿐이다. 그래서 키 없이도 에이전트 행동을 그대로 볼 수 있다.

사용:
    python3 policy_play.py                    # 91_dsl_demo, 여섯 부류
    python3 policy_play.py 38_cinderella.json
    python3 policy_play.py --quiet            # 표만
"""
import sys, json, os
from game_engine_v2 import GameSession


# ── 플레이어가 '지금 아는 것'을 셈한다 ────────────────────────────────
def deduce(g):
    """플레이어가 손에 쥔 것으로 (1) 범인을 짚을 수 있는가 (2) 몇 점인가.

    ★채점은 시나리오의 scoring을 따른다 — 범인 5점 + 비밀 1개당 1점(만점 10).
      처음엔 '범인을 짚었는가'만 봤더니 심문이 기여를 0으로 나왔다.
      실제 설계에서 **심문은 범인 특정이 아니라 비밀 공개(점수)를 담당**한다
      (소지품 points_to가 전부 None이다). 그래서 두 축을 다 재야 공정하다.
    """
    s = g.s
    cast = [c["id"] for c in s["cast"]]
    cleared, pointed = set(), {}
    # 합성 단서(조합/감식)도 가리키는 바가 있으면 센다
    for cid in g.held_clues:
        for pair, comp in g.composite_clues.items():
            if comp.get("id") == cid and comp.get("points_to"):
                w = 3 if comp.get("decisive") else 1
                pointed[comp["points_to"]] = pointed.get(comp["points_to"], 0) + w
    for cid in g.held_clues:
        cl = g.clue_graph.get(cid)
        if not cl:
            continue                       # 조합/감식으로 생긴 합성 단서
        for x in (cl.get("exculpates") or []):
            cleared.add(x)
        pt = cl.get("points_to")
        if pt:
            w = 3 if cl.get("decisive") else (2 if cl.get("weight") == "alibi_break" else 1)
            # 헛다리(red_herring)는 가리키긴 하나 근거로는 약하다
            if cl.get("weight") == "red_herring":
                w = 1
            pointed[pt] = pointed.get(pt, 0) + w
    remain = [c for c in cast if c not in cleared]
    best = max(remain, key=lambda c: pointed.get(c, 0)) if remain else None
    top = pointed.get(best, 0) if best else 0
    tie = [c for c in remain if pointed.get(c, 0) == top and top > 0]
    pick = best if top > 0 else None
    truth = (s.get("solution") or {}).get("culprit")
    sc = s.get("scoring") or {}
    n_sec = sum(len(v) for v in g.disclosed_secrets.values())
    pts = (sc.get("culprit_correct", 5) if pick == truth else 0) \
        + n_sec * sc.get("secret_revealed_each", 1)
    pts = min(pts, sc.get("max", 10))
    grades = sorted(((s.get("ending") or {}).get("grades") or []),
                    key=lambda x: x.get("min", 0))
    grade = ""
    for gr in grades:
        if pts >= gr.get("min", 0):
            grade = gr.get("name", "")
    return {"cleared": sorted(cleared), "remain": remain,
            "pointed": pointed, "pick": pick,
            "confident": bool(top >= 3 and len(tie) == 1),
            "tie": tie, "secrets": n_sec, "points": pts, "max": sc.get("max", 10),
            "grade": grade}


def _talk_all(g, s, evidence=True, limit=None):
    """장소·수첩에서 만날 수 있는 인물을 정곡 트리거로 심문."""
    n = adm = 0
    for cid, acc in (s["ui"].get("cast_access") or {}).items():
        if limit and n >= limit:
            break
        if g.turns_left < 1:
            break
        c = g.cast[cid]
        pp = (c.get("pressure_points") or [{}])[0]
        trig = (pp.get("trigger") or ["그날 밤"])[0]
        r = g.interrogate(cid, f"{trig}에 대해 말해 보시오.", evidence_shown=evidence)
        if "error" in r:
            break
        n += 1
        if r.get("stance") in ("ADMIT", "BREAK"):
            adm += 1
    return n, adm


def _inspect_all(g):
    return sum(1 for pid in list(g.inspections) if g.inspect(pid).get("success"))


def _search_all(g, s):
    """모든 장소의 선택지를 눌러 본다 — 1차 탐색. 턴이 든다."""
    found = tried = 0
    for ps in (s["ui"].get("place_screens") or []):
        rd = (ps.get("rounds") or {}).get(str(g.current_round)) or {}
        for i in range(len(rd.get("actions") or [])):
            if g.turns_left < 1:
                return found, tried
            r = g.search(ps["place_id"], i)
            if "error" in r:
                return found, tried
            tried += 1
            if r.get("found_clue"):
                found += 1
    return found, tried


def _combine_all(g):
    got = 0
    for pair in list(g.composite_clues):
        if all(x in g.held_clues for x in pair):
            r = g.combine(pair[0], pair[1])
            if r.get("success") and not r.get("already_done"):
                got += 1
    return got


def _confront_first(g):
    for (a, b) in list(g.cx_pairs):
        r = g.confront(a, b, "그 시각 어디 있었는지 다시 말해 보시오.")
        if "error" not in r:
            return r
    return None


# ── 여섯 부류 ────────────────────────────────────────────────────────
def run_policy(name, path):
    s = json.load(open(path, encoding="utf-8"))
    g = GameSession(s)
    log = {"name": name, "talk": 0, "admit": 0, "inspect": 0,
           "combine": 0, "confront": 0, "accuse_round": None, "note": ""}

    def advance():
        return g.next_round()

    log.setdefault("search", 0)
    if name == "정공법":
        # 라운드마다 다 하고 마지막에 지목
        while True:
            f, _ = _search_all(g, s)
            log["search"] += f
            t, a = _talk_all(g, s)
            log["talk"] += t; log["admit"] += a
            log["inspect"] += _inspect_all(g)
            log["combine"] += _combine_all(g)
            if g.current_round >= g.confront_unlock_round and log["confront"] == 0:
                if _confront_first(g):
                    log["confront"] += 1
            if "error" in advance():
                break
        log["accuse_round"] = g.current_round

    elif name == "심문만":
        while True:
            t, a = _talk_all(g, s)
            log["talk"] += t; log["admit"] += a
            if "error" in advance():
                break
        log["accuse_round"] = g.current_round
        log["note"] = "조합·감식·대질을 한 번도 안 씀"

    elif name == "탐색만":
        while True:
            f, _ = _search_all(g, s)
            log["search"] += f
            log["inspect"] += _inspect_all(g)
            log["combine"] += _combine_all(g)
            if "error" in advance():
                break
        log["accuse_round"] = g.current_round
        log["note"] = "심문을 한 번도 안 함"

    elif name == "대질올인":
        # 해금 라운드까지 최소로 가서 대질부터
        while g.current_round < g.confront_unlock_round:
            advance()
        if _confront_first(g):
            log["confront"] += 1
        t, a = _talk_all(g, s, limit=2)
        log["talk"] += t; log["admit"] += a
        while "error" not in advance():
            pass
        log["accuse_round"] = g.current_round
        log["note"] = "이벤트 뒤 곧장 대질, 심문은 2명만"

    elif name == "성급이":
        f, _ = _search_all(g, s)
        log["search"] += f
        t, a = _talk_all(g, s, limit=2)
        log["talk"] += t; log["admit"] += a
        log["accuse_round"] = 1
        log["note"] = "1라운드에 바로 지목"

    elif name == "소거파":
        # 배제 단서를 모으는 데만 집중 — 심문 없이 라운드만 넘긴다
        while True:
            log["combine"] += _combine_all(g)
            if "error" in advance():
                break
        log["accuse_round"] = g.current_round
        log["note"] = "배제 단서만 셈해서 남은 사람을 지목"

    d = deduce(g)
    truth = s["solution"]["culprit"]
    log.update({
        "pick": d["pick"], "truth": truth,
        "correct": d["pick"] == truth,
        "confident": d["confident"],
        "cleared": len(d["cleared"]), "remain": len(d["remain"]),
        "clues": len(g.held_clues), "turns_left": g.turns_left, "search": log["search"],
        "tie": d["tie"], "pointed": d["pointed"],
        "secrets": d["secrets"], "points": d["points"], "max": d["max"], "grade": d["grade"],
    })
    return log, g, d, s


POLICIES = ["정공법", "심문만", "탐색만", "대질올인", "성급이", "소거파"]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quiet = "--quiet" in sys.argv
    path = args[0] if args else "91_dsl_demo.json"
    if not os.path.exists(path):
        print(f"파일 없음: {path}"); sys.exit(1)

    s0 = json.load(open(path, encoding="utf-8"))
    names = {c["id"]: c["name"] for c in s0["cast"]}
    truth = s0["solution"]["culprit"]
    print("=" * 96)
    print(f" 「{s0['meta']['title']}」 {(s0.get('stars') or {}).get('stars','')}"
          f"  ·  정답: {names.get(truth)}({truth})"
          f"  ·  {s0['config']['rounds']}라운드 · 턴 {s0['config']['turns_per_round']}/R")
    print("=" * 96)

    rows = []
    for pol in POLICIES:
        log, g, d, s = run_policy(pol, path)
        rows.append(log)
        if quiet:
            continue
        mark = "○ 적중" if log["correct"] else ("✗ 오답" if log["pick"] else "— 못 짚음")
        print(f"\n▶ {pol}   {mark}"
              f"   지목={names.get(log['pick']) or '—'}"
              f"   확신={'예' if log['confident'] else '아니오'}")
        print(f"   행동: 탐색 {log['search']} · 심문 {log['talk']}(실토 {log['admit']}) · 감식 {log['inspect']}"
              f" · 조합 {log['combine']} · 대질 {log['confront']}"
              f" · 지목 R{log['accuse_round']} · 남은턴 {log['turns_left']}")
        print(f"   점수: {log['points']}/{log['max']}점  「{log['grade']}」"
              f"   (범인 {'맞힘 5' if log['correct'] else '틀림 0'}점"
              f" + 비밀 {log['secrets']}개)")
        print(f"   근거: 단서 {log['clues']}개 · 배제 {log['cleared']}명"
              f" · 남은 후보 {log['remain']}명"
              f" · 지목점수 {({names.get(k,k): v for k, v in sorted(log['pointed'].items(), key=lambda x:-x[1])})}")
        if log["tie"] and len(log["tie"]) > 1:
            print(f"   ⚠ 동점 후보 {[names.get(x) for x in log['tie']]} — 근거만으로 못 가른다")
        if log["note"]:
            print(f"   비고: {log['note']}")

    print("\n" + "=" * 96)
    print(f"{'플레이 방식':10} {'범인':6} {'점수':>6} {'엔딩':10} {'비밀':>4} "
          f"{'단서':>4} {'탐색':>4} {'심문':>4} {'감식':>4} {'조합':>4} {'대질':>4}")
    print("-" * 96)
    for r in rows:
        res = "적중" if r["correct"] else ("오답" if r["pick"] else "못짚음")
        print(f"{r['name']:10} {res:6} {r['points']:3}/{r['max']:<2} {r['grade']:10} "
              f"{r['secrets']:4} {r['clues']:4} {r.get('search',0):4} {r['talk']:4} "
              f"{r['inspect']:4} {r['combine']:4} {r['confront']:4}")
    ok = sum(1 for r in rows if r["correct"])
    print("-" * 96)
    best = max(rows, key=lambda r: r["points"])
    print(f" 범인 적중 {ok}/{len(rows)} · 최고점 {best['points']}/{best['max']} ({best['name']})")
    print("=" * 96)


if __name__ == "__main__":
    main()
