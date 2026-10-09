# -*- coding: utf-8 -*-
"""
routes.py — 게임을 **여러 경로로 끝까지 돌려 보고** 진행이 막히는 곳을 찾는다.

왜 만들었나
  지금까지 본 것은 '한 턴의 대답'이었다. 그런데 실제로 판이 재미없어지는 이유는
  대개 **진행 구조** 쪽에 있다 — 뒤져도 안 나오는 장소, 영영 안 터지는 이벤트,
  2라운드에 할 일이 없는 판, 만점이 원리상 불가능한 배점.

  이건 모델을 부르지 않고도 알 수 있다. 단서·장소·라운드·이벤트·배점은 전부 데이터다.
  그래서 **LLM 없이** 여러 전략으로 판을 돌려 본다. 공짜고 빠르다.

돌려 보는 경로
  place-first   장소부터 싹 뒤지고 나중에 심문
  talk-first    심문 먼저, 막히면 그때 장소
  greedy        라운드마다 가장 많이 나오는 장소부터
  decisive-rush 결정적 단서가 있는 곳으로 곧장
  blind         함정 단서만 붙잡고 가는 최악의 경로

무엇을 잡나
  ROUND-empty     그 라운드에 새로 나올 단서가 없다 (할 일이 없는 라운드)
  PLACE-barren    아무리 뒤져도 단서가 안 나오는 장소
  LAYER-broken    장소 3층을 약속해 놓고 라운드별 단서가 없다
  EVENT-dead      이벤트가 가리키는 인물·단서가 없거나 라운드가 범위 밖
  DECISIVE-unreach 결정적 단서에 도달할 길이 없다
  SECRET-unreach  어떤 비밀은 어떤 경로로도 열 수 없다
  SCORE-impossible 만점이 원리상 불가능하다
  ENDING-gap      점수 구간에 대응하는 엔딩이 없다
  ROUTE-stuck     그 경로로는 범인에 도달하지 못한다

사용:
    python routes.py                      # 전편
    python routes.py out/13_푸른수염.json
"""
import json, glob, sys, os, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")

# 뒤져야 나오는 채널 — 장소·기록·물증. 현장 검안과 공개 증언만 공짜로 준다.
#   채널을 쪼개면서 'location'만 보던 코드가 기록·물증을 공짜로 줘 버렸다.
FREE_AT_START = ("crime_scene",)   # 공짜로 주는 채널 — 검안뿐
SEARCHABLE = ("location", "record", "physical", "spine")



def _clue_places(s):
    """단서가 어느 장소에서 나오는가 — play_agent와 같은 규칙으로 붙인다."""
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    by = collections.defaultdict(list)
    for cl in s["clue_graph"]:
        loc = cl.get("location")
        if not loc:
            for pid, nm in pn.items():
                key = nm.split("(")[0]
                if key and key in (cl.get("surface", "") + cl.get("implies", "")):
                    loc = pid
                    break
            loc = loc or s["death"]["place"]
        by[loc].append(cl)
    return by


def structure(s):
    """경로를 돌리기 전에, 판 자체가 성립하는지 본다."""
    bad = []
    rounds = s.get("config", {}).get("rounds", 3)
    places = [p["id"] for p in s["map"]["places"]]
    by = _clue_places(s)
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}

    # 라운드마다 새로 나올 것이 있는가
    for r in range(1, rounds + 1):
        n = [cl for cl in s["clue_graph"] if (cl.get("reveal_round") or 1) == r]
        if not n:
            bad.append(("ROUND-empty", f"{r}라운드에 새 단서가 하나도 없다"))

    # 뒤져도 안 나오는 장소
    for pid in places:
        if not by.get(pid):
            bad.append(("PLACE-barren", f"{pn[pid]}({pid}) — 아무것도 안 나온다"))

    # 층을 약속했으면 라운드마다 뭔가 나와야 한다
    # ★ 층은 '라운드마다 새 단서'가 아니라 '라운드마다 새로 보이는 것'이다.
    #   방 하나에 단서가 셋씩 있을 리 없다. 층 글이 라운드 수만큼 있고
    #   서로 다르기만 하면 된다 — 같은 말을 세 번 적어 놓은 것이 진짜 빈 약속이다.
    pl = (s.get("place_layers") or {}).get("layers") or {}
    for pid, layers in pl.items():
        # 층은 리스트로도 dict("1","2","3")로도 적혀 있다. 둘 다 받는다.
        if isinstance(layers, dict):
            layers = [layers[k] for k in sorted(layers, key=lambda x: str(x))]
        if not isinstance(layers, list):
            continue
        if len(layers) < rounds:
            bad.append(("LAYER-broken",
                        f"{pn.get(pid,pid)} — 층이 {len(layers)}개뿐 (라운드 {rounds})"))
        elif len(set(layers[:rounds])) < rounds:
            bad.append(("LAYER-broken",
                        f"{pn.get(pid,pid)} — 층 글이 서로 같다: {layers[:rounds]}"))

    # 1라운드에 장소를 뒤져 나올 것이 있는가
    #   현장 검안은 처음부터 주더라도, 방을 뒤져 나오는 것이 하나도 없으면
    #   플레이어는 첫 라운드 내내 '더 나올 것이 없소'만 본다.
    r1 = [cl for cl in s["clue_graph"]
          if (cl.get("reveal_round") or 1) == 1 and cl.get("channel") in SEARCHABLE]
    if not r1:
        bad.append(("ROUND1-empty", "1라운드에 **뒤져서** 나오는 단서가 없다 — 첫 라운드가 빈다"))

    # 이벤트가 살아 있는가
    # 이벤트는 name으로도 title로도 적혀 있다. 효과가 **판의 무엇을 바꾸는지**만 보면 된다.
    ids = {c["id"] for c in s["cast"]} | {c["name"] for c in s["cast"]}
    # 장소는 '곳간(발견 장소)'처럼 괄호가 붙어 있다. 앞머리로도 맞춰 본다.
    handles = ids | {c["id"] for c in s["clue_graph"]}
    for pp in s["map"]["places"]:
        handles.add(pp["name"]); handles.add(pp["name"].split("(")[0].strip())
    for e in (s.get("events") or []):
        nm = e.get("name") or e.get("title") or "(이름 없음)"
        r = e.get("round", 0)
        if not (2 <= r <= rounds):
            bad.append(("EVENT-dead", f"이벤트 '{nm}' 라운드 {r} — 범위 밖"))
        eff = e.get("effect", "")
        if not eff:
            bad.append(("EVENT-dead", f"이벤트 '{nm}' 효과가 비어 있다"))
        elif not (any(h and h in eff for h in handles) or "비밀" in eff or "압박" in eff):
            bad.append(("EVENT-dead", f"이벤트 '{nm}' 효과가 판의 무엇도 가리키지 않는다"))
        if not (e.get("name") or e.get("title")):
            bad.append(("EVENT-dead", "이름 없는 이벤트 — 화면에 띄울 제목이 없다"))

    # 결정적 단서에 닿을 수 있는가
    dec = next((cl for cl in s["clue_graph"] if cl.get("decisive")), None)
    if dec:
        where = [pid for pid, cls in by.items() if dec in cls]
        if not where:
            bad.append(("DECISIVE-unreach", f"{dec['id']} — 어느 장소에서도 안 나온다"))
    else:
        bad.append(("DECISIVE-unreach", "결정적 단서가 아예 없다"))

    # 비밀은 전부 열 수 있는가
    reach = {cl["id"] for cls in by.values() for cl in cls}
    allbel = {b.get("id") for c in s["cast"] for b in (c.get("belongings") or [])}
    for c in s["cast"]:
        for i, sec in enumerate(c.get("secrets") or []):
            fb = set(sec.get("forced_by") or [])
            if fb and not (fb & (reach | allbel)):
                bad.append(("SECRET-unreach",
                            f"{c['name']}의 비밀 — 여는 단서 {sorted(fb)}에 도달 못 한다"))

    # 배점과 엔딩
    sc = s.get("scoring") or {}
    nsec = sum(len(c.get("secrets") or []) for c in s["cast"])
    if sc:
        want = sc.get("culprit_correct", 0) + sc.get("secret_revealed_each", 0) * nsec
        if sc.get("max") != want:
            bad.append(("SCORE-impossible", f"만점 {sc.get('max')} vs 도달 가능 {want}"))
    gr = (s.get("ending") or {}).get("grades") or []
    if gr and sc.get("max") is not None:
        mins = sorted(g.get("min", 0) for g in gr)
        if mins[0] != 0 or mins[-1] != sc["max"]:
            bad.append(("ENDING-gap", f"엔딩 구간 {mins} — 0점과 만점({sc['max']})을 덮지 못한다"))
    return bad


# ── 경로 다섯 가지 ────────────────────────────────────────────────────
def _route_order(s, kind, by):
    places = [p["id"] for p in s["map"]["places"]]
    dec = next((cl for cl in s["clue_graph"] if cl.get("decisive")), None)
    decp = next((pid for pid, cls in by.items() if dec and dec in cls), None)
    if kind == "place-first":
        return places
    if kind == "greedy":
        return sorted(places, key=lambda p: -len(by.get(p, [])))
    if kind == "decisive-rush":
        return ([decp] if decp else []) + [p for p in places if p != decp]
    if kind == "blind":                       # 함정만 좇는 최악의 경로
        trap = [pid for pid, cls in by.items()
                if any(cl.get("weight") == "red_herring" or cl.get("points_to")
                       and not cl.get("decisive") for cl in cls)]
        return trap + [p for p in places if p not in trap]
    return list(reversed(places))             # talk-first — 장소는 나중에


def run_route(s, kind):
    """한 경로로 라운드를 끝까지 돌린다. 각 라운드에 무엇을 얻는지 센다."""
    by = _clue_places(s)
    rounds = s.get("config", {}).get("rounds", 3)
    order = _route_order(s, kind, by)
    # ★ play_agent와 **같은 규칙**이어야 한다.
    #   처음부터 쥐고 시작하는 것은 현장 검안·공개 증언뿐이고,
    #   방에서 나오는 것(location)은 1라운드라도 뒤져야 나온다.
    held = {cl["id"] for cl in s["clue_graph"]
            if (cl.get("reveal_round") or 9) <= 1 and cl.get("channel") in FREE_AT_START}
    log, bad = [], []
    for r in range(1, rounds + 1):
        got = []
        for pid in order:
            for cl in by.get(pid, []):
                if cl["id"] in held:
                    continue
                if (cl.get("reveal_round") or 1) > r:      # 아직 나올 때가 아니다
                    continue
                held.add(cl["id"])
                got.append(cl["id"])
        log.append((r, got))
        # 한 라운드가 유난히 얄팍하면 그 구간이 늘어진다 — 실격은 아니고 알림
        if r == rounds and len(got) <= 2 and sum(len(g) for _, g in log) >= 8:
            bad.append(("ROUND-thin", f"{kind}: 마지막 라운드 수확 {len(got)}개 — 끝이 싱겁다"))
        if not got and r > 1:
            bad.append(("ROUTE-stuck", f"{kind}: {r}라운드에 아무것도 못 얻는다"))
    dec = next((cl for cl in s["clue_graph"] if cl.get("decisive")), None)
    if dec and dec["id"] not in held:
        bad.append(("ROUTE-stuck", f"{kind}: 끝까지 결정적 단서를 못 얻는다"))
    return log, bad


def audit_one(s, verbose=True):
    bad = structure(s)
    routes = ["place-first", "talk-first", "greedy", "decisive-rush", "blind"]
    per = {}
    for k in routes:
        log, rb = run_route(s, k)
        per[k] = log
        bad += rb
    if verbose:
        print(f"  경로별 라운드 수확: " + " | ".join(
            f"{k}={'/'.join(str(len(g)) for _, g in per[k])}" for k in routes))
    return bad, per


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    counts = collections.Counter()
    total = 0
    lines = ["# 진행 경로 점검", ""]
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        print(f"\n═══ {os.path.basename(p)}  {s['meta'].get('title','')}")
        bad, per = audit_one(s)
        for k, why in bad:
            counts[k] += 1
            print(f"  ❌ {k}  {why}")
        total += len(bad)
        if bad:
            lines.append(f"### {os.path.basename(p)}")
            lines += [f"- **{k}** — {why}" for k, why in bad]
            lines.append("")
    print("\n" + "=" * 60)
    for k, v in counts.most_common():
        print(f"  {k:18} {v}")
    print(f"  합계 {total}건")
    open("routes_report.md", "w", encoding="utf-8").write("\n".join(lines))
    print("\n저장: routes_report.md")
