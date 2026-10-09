# -*- coding: utf-8 -*-
"""
pace.py — 단서가 **라운드마다 고르게 나오도록** 공개 시점을 다시 나눈다.

왜 필요한가
  장면 대본을 뽑아 보니 1라운드에 여덟 장소를 다 뒤져도 나오는 단서가 하나였다.
  대부분이 reveal_round=2에 몰려 있었기 때문이다. 플레이어는 첫 10분을
  아무것도 못 건지고 헤맨다 — 여기서 몰입이 끊긴다.

무엇을 지키나
  · 현장 검안(crime_scene)은 시작할 때 준다 — 1라운드 고정
  · 결정타는 **마지막 라운드**에만 나온다
  · 배제 단서(exculpates)는 마지막 라운드에 몰지 않는다 — 좁혀 가는 맛이 사라진다
  · 한 장소에서 같은 라운드에 두 개가 나오지 않는다
  · 라운드마다 나오는 개수를 비슷하게 맞춘다

사용:
    python pace.py out/01_전우치전.json
    python pace.py --all
"""
import json, sys, os, glob, math, argparse, collections

SEARCHABLE = ("location", "record", "physical", "spine")


def rebalance(s):
    rounds = (s.get("config") or {}).get("rounds", 3)
    crime = s["death"]["place"]
    pool = []
    for cl in s["clue_graph"]:
        if cl.get("channel") not in SEARCHABLE:
            cl["reveal_round"] = 1              # 시작할 때 주는 것
            continue
        pool.append(cl)
    if not pool:
        return s, {}

    dec = [c for c in pool if c.get("decisive")]
    # ★지난번 승격을 먼저 되돌린다 (2026-08-25).
    #   승격은 channel을 바꾸는 일이라 파일에 그대로 남는다. 되돌리지 않으면
    #   규칙을 고쳐도 옛 승격이 눌어붙어, 인물의 제 방 단서가 계속 자동 지급으로
    #   남는다(34·35편에서 비밀 탐색 경로가 끊긴 원인).
    for c in s["clue_graph"]:
        if c.pop("_promoted_spine", None) and c.get("channel") == "spine":
            c["channel"] = "record"
    spine = [c for c in pool if c.get("channel") == "spine" and not c.get("decisive")]
    exc = [c for c in pool if c.get("exculpates") and c not in dec and c not in spine]
    rest = [c for c in pool if c not in dec and c not in exc and c not in spine]

    slots = collections.defaultdict(set)        # 라운드 → 이미 쓴 장소
    plan = {}

    def place(cl, want, floor=1):
        loc = cl.get("location") or crime
        for r in list(range(want, rounds + 1)) + list(range(want - 1, floor - 1, -1)):
            if r < floor or r > rounds:
                continue
            if loc in slots[r]:
                continue
            slots[r].add(loc)
            plan[cl["id"]] = r
            return r
        plan[cl["id"]] = min(max(want, floor), rounds)  # 자리가 없으면 겹치더라도 둔다
        return plan[cl["id"]]

    # ① 결정타는 마지막 라운드
    for c in dec:
        place(c, rounds)
    # ①-2 가짜 유력자를 미는 단서(red_herring + points_to)는 **1라운드**에 —
    #      결정타와 같은 라운드에 나오면 헷갈릴 틈이 없어, 처음부터 범인이 뻔해진다
    mislead = [c for c in rest + spine
               if c.get("points_to") and str(c.get("weight", "")).startswith("red")]
    for i, c in enumerate(sorted(mislead, key=lambda x: x["id"])):
        place(c, 1 + (i % max(1, rounds - 2 or 1)))
    rest = [c for c in rest if c not in mislead]
    spine = [c for c in spine if c not in mislead]
    # ②-0 뼈대가 라운드 수보다 적으면 **증언 하나를 뼈대로 올린다** (2026-08-25).
    #     라운드마다 저절로 들어오는 증언이 하나씩은 있어야 판이 굴러간다.
    #     31·47편은 4라운드인데 뼈대가 셋뿐이라 마지막 라운드가 비어 있었다.
    if len(spine) < rounds:
        #     ★인물의 **제 방에 걸린 단서는 건드리지 않는다.** 그것을 뼈대로 올리면
        #       자동 지급으로 바뀌어 그 방을 뒤질 까닭이 사라지고, 비밀로 가는
        #       탐색 경로가 끊긴다(34·35편에서 실제로 끊겼다).
        _owned = {q.get("owner"): q["id"] for q in s["map"]["places"] if q.get("owner")}
        _rooms = set(_owned.values())
        cand = [c for c in rest
                if not c.get("points_to") and not c.get("decisive")
                and c.get("channel") in ("record", "physical")
                and c.get("location") not in _rooms
                and not str(c.get("weight", "")).startswith("red")
                and c.get("weight") != "alibi_break"]
        for c in cand[:rounds - len(spine)]:
            c["channel"] = "spine"
            c["_promoted_spine"] = True      # 되돌릴 수 있게 표시해 둔다
            spine.append(c)
            rest = [x for x in rest if x is not c]

    # ② 뼈대(spine) 단서는 라운드마다 최소 하나씩 — verify의 PACE 규칙
    #    단, 가짜 유력자를 배제하는 스파인 증언은 소문보다 한 라운드 뒤로 (미끼가 숨 쉴 틈)
    m0 = {}
    for c in s["clue_graph"]:
        if c.get("points_to") and str(c.get("weight", "")).startswith("red"):
            m0[c["points_to"]] = min(m0.get(c["points_to"], 99),
                                     plan.get(c["id"], c.get("reveal_round") or 1))
    # ★범인을 가리키는 spine 단서(알리바이 붕괴 등)는 1라운드에 두면 안 된다.
    #   아래 ③-2가 같은 보호를 하지만 rest에만 걸려 있어서, spine으로 분류된
    #   alibi_break가 라운드 로빈에 밀려 1라운드로 갔다(44편 — 성급 지목이 적중).
    _cul0 = next((x["id"] for x in s.get("cast", []) if x.get("is_culprit")), None)
    for i, c in enumerate(sorted(spine, key=lambda x: ((x.get("reveal_round") or 1), x["id"]))):
        want = 1 + (i % rounds)
        floor_ = max((m0[e] + 1 for e in (c.get("exculpates") or []) if e in m0), default=1)
        if _cul0 and (c.get("points_to") == _cul0
                      or c.get("weight") == "alibi_break"):
            floor_ = max(floor_, max(2, rounds - 1))
        place(c, min(rounds, max(want, floor_)))
    # ③ 배제 단서는 앞·가운데 라운드에 흩는다 (좁혀 가는 맛)
    #    단, 가짜 유력자를 미는 단서가 있으면 그 사람의 배제는 **한 라운드 뒤에** —
    #    소문과 배제가 같은 라운드에 나오면 의심이 붙을 틈이 없다
    mislead_round = {}
    for c in s["clue_graph"]:
        if c.get("points_to") and str(c.get("weight", "")).startswith("red"):
            r0 = plan.get(c["id"], c.get("reveal_round") or 1)
            tgt = c["points_to"]
            mislead_round[tgt] = min(mislead_round.get(tgt, 99), r0)
    for i, c in enumerate(sorted(exc, key=lambda x: x["id"])):
        want = 1 + (i % max(1, rounds - 1))
        floor_ = max((mislead_round[e] + 1 for e in (c.get("exculpates") or [])
                      if e in mislead_round), default=1)
        place(c, min(rounds, max(want, floor_)))
    # ③-2 범인을 가리키는 비결정 단서는 뒤 라운드로 — 1라운드부터 범인이 1위면 판이 뻔하다
    cul = next((c["id"] for c in s.get("cast", []) if c.get("is_culprit")), None)
    incrim = [c for c in rest if cul and c.get("points_to") == cul]
    for i, c in enumerate(sorted(incrim, key=lambda x: x["id"])):
        place(c, max(2, rounds - 1 + (i % 2)), floor=2)
    rest = [c for c in rest if c not in incrim]
    # ④ 나머지는 라운드마다 같은 수로
    per = max(1, math.ceil(len(rest) / rounds))
    for i, c in enumerate(sorted(rest, key=lambda x: ((x.get("reveal_round") or 1), x["id"]))):
        place(c, min(rounds, 1 + i // per))

    before = collections.Counter((c.get("reveal_round") or 1) for c in pool)
    for c in pool:
        c["reveal_round"] = plan.get(c["id"], c.get("reveal_round") or 1)
    after = collections.Counter(c["reveal_round"] for c in pool)
    return s, {"before": dict(sorted(before.items())), "after": dict(sorted(after.items()))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    paths = a.paths or (sorted(glob.glob("scenarios/[0-9]*.json")) if a.all else [])
    if not paths:
        print("사용: python pace.py out/01_전우치전.json  또는  python pace.py --all")
        return
    for p in paths:
        s = json.load(open(p, encoding="utf-8"))
        s, d = rebalance(s)
        json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if d:
            print(f"  {os.path.basename(p):22} {d['before']} → {d['after']}")
    print(f"\n{len(paths)}편 다시 나눔")


if __name__ == "__main__":
    main()
