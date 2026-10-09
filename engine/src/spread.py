# -*- coding: utf-8 -*-
"""
spread.py — 주저앉은 **구조 축을 벌린다.**

왜 필요한가
  variety.py가 짚었다. 이야기(트릭 21종·흉기 12종)는 다양한데 뼈대가 판박이다.
      rounds   23편 모두 3
      places   6×22, 7×1
      channels 23편 모두 3종
      cross_n  23편 모두 정확히 5개
  이대로 100편을 만들어 학습시키면 모델은 이 숫자들을 **규칙으로** 배운다.
  한 편씩은 다 통과하는데 전부 같은 게임이 나온다.

무엇을 흔드나 (제목으로 씨앗을 고정 — 다시 돌려도 같은 결과)
  rounds    3 또는 4       4라운드는 호흡이 길고 중반이 두 번 온다
  places    +0~2 공용 장소  마당·광·우물처럼 임자 없는 자리. 좁은 집과 넓은 집이 갈린다
  channels  기록/물증 채널 분리  같은 단서라도 어디서 오는지가 달라진다
  cross_n   3~8            관계가 물리는 정도

무엇을 안 건드리나
  인물 수는 그대로 5명이다. 카드·관계·말투·배점이 전부 5인 전제로 짜여 있어
  숫자만 바꾸면 조용히 어긋난다. 그건 따로 손봐야 할 공사다.

사용:
    python spread.py "scenarios/[0-9]*.json"
    python spread.py --check
"""
import json, glob, sys, os, hashlib, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")

# 임자 없는 공용 장소 — 배경 계열에 맞는 것으로 고른다
SHARED = {
    "east": [("마당", "댓돌과 장독대가 있는 마당", ["젖은 발자국", "흐트러진 짚신", "장독 뒤 그늘"]),
             ("우물가", "두레박과 물통이 놓인 우물가", ["물기 마른 자리", "떨어진 천 조각", "이 빠진 바가지"]),
             ("뒤란", "장작과 잡동사니가 쌓인 뒤란", ["쌓다 만 장작", "치우다 만 재", "밟힌 풀"])],
    "west": [("안뜰", "우물과 돌바닥이 있는 안뜰", ["젖은 돌바닥", "떨어진 장갑", "긁힌 자국"]),
             ("복도", "초상화가 걸린 긴 복도", ["기울어진 액자", "촛농 자국", "발자국이 끊긴 자리"]),
             ("헛간", "마구와 연장이 걸린 헛간", ["자리를 옮긴 연장", "흩어진 짚", "새로 난 흠집"])],
    "modern": [("복도", "형광등이 깜빡이는 복도", ["바닥에 끌린 자국", "떨어진 출입증", "꺼진 전등"]),
               ("주차장", "차 몇 대뿐인 지하 주차장", ["기름 얼룩", "밟힌 담배", "가려진 카메라"]),
               ("계단실", "인적 없는 비상계단", ["문틈의 종이", "발소리 울림", "치우다 만 상자"])],
}
# 4라운드용 층 — 세 겹으로는 모자라다
LAYER4 = "마지막으로 한 번 더 훑는다 — 이제야 눈에 드는 것"


def _seed(s, salt=0):
    h = hashlib.sha256((((s.get("meta") or {}).get("title") or "x") + str(salt)).encode())
    return h.digest()[0]


def _register(s):
    import voices
    return voices._register(s)


def widen(s):
    changed = []
    cfg = s.setdefault("config", {})
    seed = _seed(s)

    # ① 라운드 — 셋 중 하나는 4라운드로.
    #   계획표(plan50)가 MM_ROUNDS로 값을 주면 그것을 따른다.
    want = int(os.environ.get("MM_ROUNDS") or 0) or (4 if seed % 3 == 0 else 3)
    if cfg.get("rounds") != want:
        cfg["rounds"] = want
        changed.append(f"라운드 {want}")

    # ② 공용 장소 — 임자 없는 자리를 0~2개
    pool = SHARED.get(_register(s), SHARED["east"])
    add_n = _seed(s, 1) % 3
    tgt_places = int(os.environ.get("MM_PLACES") or 0)
    if tgt_places:
        add_n = max(0, tgt_places - len(s["map"]["places"]))
    def _inside(sc, k):
        """기존 장소들의 한가운데에서 조금 비껴난 자리."""
        ps = [q.get("pos") for q in sc["map"]["places"] if q.get("pos")]
        if not ps:
            return [0.6 * (k + 1), 0.6 * (k + 1)]
        cx = sum(x for x, _y in ps) / len(ps)
        cy = sum(y for _x, y in ps) / len(ps)
        rad = max(0.6, sum(abs(x - cx) + abs(y - cy) for x, y in ps) / (2 * len(ps)))
        ang = [(1, 0.4), (-0.8, 0.7), (0.3, -1), (-1, -0.5)][k % 4]
        return [round(cx + rad * ang[0], 2), round(cy + rad * ang[1], 2)]

    have = {p["name"] for p in s["map"]["places"]}
    used_ids = {p["id"] for p in s["map"]["places"]}
    added = []                     # (pid, name) — 이름만 담으면 아래에서 짝이 어긋난다
    # ★id를 **루프 번호로 짓지 않는다** (2026-08-25).
    #   전에는 pid = f"PX{i+1}"였다. 이름이 이미 있어 continue로 건너뛰면
    #   added와 번호가 어긋났고, 이 스크립트를 두 번 돌리면 **같은 id를 또** 만들었다.
    #   실제로 3편에서 장소 id가 겹쳤고(02·03·23), 장소별 음악 큐가 한 칸 모자랐다.
    def _fresh_id():
        n = 1
        while f"PX{n}" in used_ids:
            n += 1
        used_ids.add(f"PX{n}")
        return f"PX{n}"

    for i in range(add_n):
        nm, desc, feats = pool[(_seed(s, 2 + i)) % len(pool)]
        if nm in have:
            continue
        pid = _fresh_id()
        s["map"]["places"].append({
            "id": pid, "name": nm, "owner": None,
            # ★새 장소는 **기존 무리 안에** 놓는다 (2026-08-25).
            #   전에는 [3+i, 3+i]로 멀찍이 떨어뜨려서 이동 한도 밖으로 나갔고,
            #   45편은 도달 가능한 장소 쌍이 21개 중 3개뿐이었다(동선 추리가 막힘).
            "pos": _inside(s, i), "desc": desc, "features": feats,
        })
        have.add(nm); added.append((pid, nm))
    if added:
        changed.append(f"공용 장소 +{len(added)}({', '.join(n for _p, n in added)})")
        # ★ 빈 방을 만들면 뒤져도 안 나온다. 새 자리마다 볼 것을 하나씩 옮겨 놓는다.
        #   없는 사실을 만들지 않고, 장소가 없어 현장에 몰려 있던 단서를 옮긴다.
        locked = {x for c in s["cast"] for sec in (c.get("secrets") or [])
                  for x in (sec.get("forced_by") or [])}
        movable = [cl for cl in s["clue_graph"]
                   if cl.get("channel") in ("location", "record", "physical")
                   and not cl.get("decisive") and not cl.get("points_to")
                   and cl["id"] not in locked
                   and cl.get("location") in (None, s["death"]["place"])]
        for i, (pid, nm) in enumerate(added):
            if i < len(movable):
                movable[i]["location"] = pid
            else:
                # 옮길 것이 없으면 그 자리의 자취를 단서로 세운다(분위기 단서)
                feats = next((p.get("features") or [] for p in s["map"]["places"]
                              if p["id"] == pid), ["자취"])
                s["clue_graph"].append({
                    "id": f"X{pid}", "channel": "physical", "medium": "탐색",
                    "location": pid, "reveal_round": 2,
                    "surface": f"{nm}에서 {feats[0]}이(가) 눈에 든다.",
                    "implies": f"{nm}을(를) 오간 사람이 있다",
                    "weight": "context", "points_to": None, "exculpates": [],
                    "decisive": False, "layer": 2,
                })

    # ③ 층 — 라운드 수만큼, 서로 다르게
    pl = s.setdefault("place_layers", {"note": "라운드마다 다른 것이 보인다", "layers": {}})
    layers = pl.setdefault("layers", {})
    for p in s["map"]["places"]:
        cur = layers.get(p["id"])
        if isinstance(cur, dict):
            cur = [cur[k] for k in sorted(cur, key=str)]
        f = list(p.get("features") or [])
        base = list(cur or [])
        while len(base) < want:
            i = len(base)
            base.append(f[i] if i < len(f) else
                        (LAYER4 if i >= 3 else f"{p['name']}에서 그제야 눈에 드는 것"))
        # 같은 글이 겹치면 층이 없는 것과 같다
        seen, out = set(), []
        for i, x in enumerate(base[:want]):
            if x in seen:
                x = f"{x} — 앞서 못 본 자리까지"
            seen.add(x); out.append(x)
        layers[p["id"]] = out

    # ④ 단서 채널 — 기록·물증을 갈라 준다
    for cl in s["clue_graph"]:
        if cl.get("channel") != "location":
            continue
        blob = (cl.get("surface", "") + cl.get("implies", ""))
        if any(k in blob for k in ("장부", "문서", "편지", "명부", "계약", "쪽지", "기록")):
            cl["channel"] = "record"
        elif any(k in blob for k in ("조각", "자국", "묻은", "떨어진", "남은", "올")):
            cl["channel"] = "physical"
    if len({c.get("channel") for c in s["clue_graph"]}) > 3:
        changed.append("채널 분화")

    # ⑤ 교차 단서 수를 3~8로 흔든다
    cross = [cl for cl in s["clue_graph"] if len(cl.get("affects") or []) >= 2]
    target = 3 + (_seed(s, 7) % 6)
    ids = [c["id"] for c in s["cast"]]
    if len(cross) < target:
        pool2 = [cl for cl in s["clue_graph"] if len(cl.get("affects") or []) < 2
                 and not cl.get("decisive")]
        for i, cl in enumerate(pool2[: target - len(cross)]):
            a = ids[(_seed(s, 10 + i)) % len(ids)]
            b = ids[(_seed(s, 20 + i)) % len(ids)]
            cl["affects"] = sorted({a, b}) if a != b else [a, ids[(ids.index(a) + 1) % len(ids)]]
    elif len(cross) > target:
        for cl in cross[target:]:
            cl["affects"] = (cl.get("affects") or [])[:1]
    changed.append(f"교차 {target}")

    # ⑥ 라운드가 늘면 단서를 **고르게 다시 편다.**
    #   3라운드짜리에서 몇 개만 4라운드로 옮기면 마지막이 싱거워진다(실제로 그랬다).
    #   1라운드 몫은 그대로 두고, 나머지를 2..N 라운드에 균등하게 나눈다.
    rest = [cl for cl in s["clue_graph"] if (cl.get("reveal_round") or 1) != 1]
    dec = [cl for cl in rest if cl.get("decisive")]
    plain = [cl for cl in rest if not cl.get("decisive")]
    slots = list(range(2, want + 1))
    for i, cl in enumerate(plain):
        cl["reveal_round"] = slots[i % len(slots)]
        cl["layer"] = min(cl["reveal_round"], want)
    for cl in dec:                      # 결정타는 언제나 마지막 라운드
        cl["reveal_round"] = want
        cl["layer"] = want

    # ⑥-1 라운드마다 **스파인 단서**가 하나는 있어야 한다.
    #   증언·현장 단서가 한 라운드에 몰리면 그 라운드만 이야기가 흐른다(verify PACE).
    spine = [cl for cl in s["clue_graph"] if cl.get("channel") in ("spine", "crime_scene")]
    if spine:
        for k in range(1, want + 1):
            if not any((cl.get("reveal_round") or 1) == k for cl in spine):
                donor = max(spine, key=lambda cl: sum(
                    1 for x in spine if (x.get("reveal_round") or 1) == (cl.get("reveal_round") or 1)))
                donor["reveal_round"] = k

    # ⑥-2 빈 장소가 남지 않게 한 번 훑는다.
    #   장소를 늘려 놓고 단서를 안 놓으면 "뒤져도 안 나오는 방"이 늘어난다.
    have_clue = {cl.get("location") for cl in s["clue_graph"] if cl.get("location")}
    for i, p in enumerate(s["map"]["places"]):
        if p["id"] in have_clue:
            continue
        feats = list(p.get("features") or []) or [f"{p['name']}의 자취"]
        s["clue_graph"].append({
            "id": f"Z{p['id']}", "channel": "physical", "medium": "탐색",
            "location": p["id"], "reveal_round": 2 + (i % max(1, want - 1)),
            "surface": f"{p['name']}에서 {feats[-1]}이(가) 눈에 든다.",
            "implies": f"{p['name']}을(를) 오간 사람이 있다",
            "weight": "context", "points_to": None, "exculpates": [],
            "decisive": False, "layer": 2,
        })

    # ⑦ 페이즈를 라운드 수에 맞춘다
    try:
        import upgrade_schema as U
        s["phases"] = U._phases(s)
    except Exception:
        pass
    return changed


def check(s):
    bad = []
    r = s.get("config", {}).get("rounds", 3)
    have = {(cl.get("reveal_round") or 1) for cl in s["clue_graph"]}
    for k in range(1, r + 1):
        if k not in have:
            bad.append(f"{k}라운드에 단서가 없다")
    for pid, v in ((s.get("place_layers") or {}).get("layers") or {}).items():
        if isinstance(v, dict):
            v = list(v.values())
        if len(v) < r:
            bad.append(f"{pid} 층 {len(v)}개 < 라운드 {r}")
        elif len(set(v[:r])) < r:
            bad.append(f"{pid} 층 글이 겹친다")
    names = [p.get("name") for p in s["map"]["places"]]
    if len(set(names)) != len(names):
        bad.append("장소 이름이 겹친다")
    return (not bad), bad


if __name__ == "__main__":
    if "--check" in sys.argv:
        n = 0
        for p in sorted(glob.glob("scenarios/[0-9]*.json")):
            ok, bad = check(json.load(open(p, encoding="utf-8")))
            if not ok:
                print(f"  ❌ {os.path.basename(p):26} {'; '.join(bad[:3])}"); n += 1
        print(f"구조 검사 끝 — 문제 {n}편")
        sys.exit(0 if n == 0 else 1)
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        ch = widen(s)
        json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  {os.path.basename(p):26} {' · '.join(ch)}")
