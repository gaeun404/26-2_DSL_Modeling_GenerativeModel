# -*- coding: utf-8 -*-
"""
autoplay.py — **플레이어 에이전트**가 한 판을 끝까지 두고, 생각한 과정을 남긴다.

왜 필요한가
  지금까지는 사람이 몇 턴 쳐 보거나, 검사기가 한 턴씩 판정했다.
  "처음부터 끝까지 어떤 과정으로 풀리는가"는 아무도 본 적이 없다.
  그런데 그게 곧 게임의 재미다 — 무엇을 보고 의심이 올랐고,
  어떤 말에서 앞뒤가 어긋났고, 어디서 확신이 섰는가.

무엇을 하나
  · 라운드마다 장소를 뒤지고, 얻은 단서로 **의심도를 갱신**한다
  · 용의자에게 묻고, 답에서 장소·알리바이를 뽑아 **앞선 진술과 대조**한다
  · 배제 단서가 나오면 후보에서 지운다
  · 결정타를 쥐면 그 인물에게 들이대고, 압박 게이지를 올린다
  · 마지막에 가장 의심스러운 자를 지목하고 채점·엔딩을 받는다
  · **판단 근거를 매번 기록한다** — 이것이 이 도구의 산출물이다

모델
  --api 또는 --model 로 실제 대화를 한다.
  아무것도 안 주면 대사 없이 **판의 진행만** 돌린다(공짜). 기계 부분은 전부 진짜다.

사용:
    python autoplay.py out/13_푸른수염.json                 # 진행만
    python autoplay.py out/13_푸른수염.json --api           # 대사까지
    python autoplay.py out/13_푸른수염.json --out play.md
"""
import json, sys, os, re, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")
FREE_AT_START = ("crime_scene",)   # 공짜로 주는 채널 — 검안뿐
SEARCHABLE = ("location", "record", "physical", "spine")


def _j(w, pair="을/를"):
    a, b = pair.split("/")
    if not w:
        return b
    ch = w[-1]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


_SELF = ("나는", "내가", "저는", "제가", "이 사람은", "소인은", "쇤네는", "저야", "나야", "난 ", "전 ")
_STAY = re.compile(r"(에|에서)[^\.\?!…]{0,14}(있|잤|묵|머물|지냈|보냈|기다렸|일했|썼|했)")
_ASKY = ("궁금", "무슨 일", "어떻게 된", "누가", "물어", "아시", "모르겠")


def _claims(ans, place_names, slots):
    """답변에서 **본인 알리바이 주장**만 뽑는다.
    지나가며 언급한 장소('서재에서 무슨 일이…')를 주장으로 오인하지 않도록,
    ① 1인칭 표지가 있는 문장에서 ② 장소+체류동사 꼴일 때만 인정한다. 슬롯당 하나."""
    got = {}
    for sent in re.split(r"[\.\?!…]\s*", str(ans)):
        if not sent or any(k in sent for k in _ASKY):
            continue
        selfish = any(m in sent for m in _SELF) or sent.strip().startswith(("그 밤", "밤엔", "밤에는"))
        if not selfish:
            continue
        for slot in slots:
            if slot in got or slot not in sent and slot != "밤":
                # '밤' 슬롯은 '그 밤/밤에' 표현이 흔해 문장에 슬롯 낱말이 있을 때만
                if slot not in sent:
                    continue
            if slot in got:
                continue
            for nm in place_names:
                base = nm.split("(")[0]
                i = sent.find(base)
                if i < 0:
                    continue
                tail = sent[i + len(base): i + len(base) + 20]
                if _STAY.match(tail) or _STAY.search(sent[i:]):
                    got[slot] = nm
                    break
    return list(got.items())


class Player:
    """추리하는 쪽. 의심도와 그 근거를 들고 다닌다."""

    def __init__(self, s):
        self.s = s
        self.name = {c["id"]: c["name"] for c in s["cast"]}
        self.susp = {c["id"]: 0.0 for c in s["cast"]}
        self.why = collections.defaultdict(list)     # 왜 그렇게 봤는가
        self.cleared = set()
        self.said = collections.defaultdict(dict)    # 인물이 말한 장소(시간대별)
        self.log = []

    def note(self, line):
        self.log.append(line)

    def see(self, cl):
        """단서 하나를 얻었을 때 판이 어떻게 움직이는가."""
        moved = []
        for e in (cl.get("exculpates") or []):
            if e not in self.cleared:
                self.cleared.add(e)
                self.susp[e] = -99
                moved.append(f"{self.name[e]} 배제")
                self.why[e].append(f"{cl['id']}: 혐의 벗음")
        pt = cl.get("points_to")
        if pt and pt not in self.cleared:
            w = 3.0 if cl.get("decisive") else 1.0
            self.susp[pt] += w
            moved.append(f"{self.name[pt]} 의심 +{w:g}")
            self.why[pt].append(f"{cl['id']}: {cl.get('surface','')[:44]}")
        for a in (cl.get("affects") or []):
            if a not in self.cleared:
                self.susp[a] += 0.3
        return moved

    def hear(self, cid, slot, place):
        """진술을 듣고 앞말과 대조한다."""
        prev = self.said[cid].get(slot)
        self.said[cid][slot] = place
        if prev and place and prev != place:
            self.susp[cid] += 1.5
            self.why[cid].append(f"진술 모순: {slot}에 「{prev}」였다가 「{place}」")
            return f"{self.name[cid]} 진술 모순 (+1.5)"
        return None

    def ranked(self):
        return sorted(((v, k) for k, v in self.susp.items()), reverse=True)


def _notebook_snapshot(P, s, held, r, gauges, opened):
    """사건수첩 3탭이 이 시점에 어떻게 쓰여 있는가."""
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    L = [f"\n### 📓 사건수첩 — {r}라운드 종료 시점\n", "**[인물 탭]**\n"]
    for c in s["cast"]:
        cid = c["id"]
        mark = "✅배제" if cid in P.cleared else ("🔴" if P.susp[cid] == max(
            v for k, v in P.susp.items() if k not in P.cleared) and P.susp[cid] > 0 else "·")
        said = " / ".join(f"{sl}:{pl}" for sl, pl in P.said.get(cid, {}).items()) or "진술 없음"
        sec = " · 비밀 개방" if gauges[cid].hit.get("trigger") else ""
        L.append(f"- {mark} **{c['name']}** — 알리바이 기록: {said}{sec}")
        for w in P.why.get(cid, [])[-2:]:
            L.append(f"    - {w}")
    L.append("\n**[단서 탭]** " + f"{len(held)}건")
    rows = [cl for cl in s["clue_graph"] if cl["id"] in held]
    for cl in rows[-6:]:
        tag = " ★" if cl.get("decisive") else ""
        L.append(f"- `{cl['id']}`{tag} {cl.get('surface','')[:48]}")
    if len(rows) > 6:
        L.append(f"- … 외 {len(rows)-6}건")
    L.append("\n**[메모 탭]** (에이전트가 적은 추리)\n")
    rk = [(v, P.name[k]) for v, k in P.ranked() if v > -50]
    if rk:
        top = rk[0][1]
        L.append(f"> 지금 가장 의심: **{top}**. "
                 + " ".join(f"{n}({v:.1f})" for v, n in rk[:4]))
    gone = [P.name[c] for c in P.cleared]
    if gone:
        L.append(f"> 배제: {', '.join(gone)} — 다시 볼 필요 없음.")
    dec = next((cl for cl in s["clue_graph"] if cl.get("decisive") and cl["id"] in held), None)
    if dec:
        L.append(f"> 결정타 `{dec['id']}` 확보 — 들이댈 상대와 순서를 정할 것.")
    else:
        L.append("> 아직 결정타 없음 — 다음 라운드 탐색 우선순위: 안 뒤진 층.")
    return "\n".join(L)


def run(s, llm=None, out=None, notebook=False):
    from pressure import Gauge
    import question_sets as QS
    P = Player(s)
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    rounds = s.get("config", {}).get("rounds", 3)
    cast = {c["id"]: c for c in s["cast"]}
    gauges = {cid: Gauge(s, cid) for cid in cast}

    by_place = collections.defaultdict(list)
    for cl in s["clue_graph"]:
        loc = cl.get("location") or s["death"]["place"]
        by_place[loc].append(cl)

    held = {cl["id"] for cl in s["clue_graph"]
            if (cl.get("reveal_round") or 9) <= 1 and cl.get("channel") in FREE_AT_START}
    P.note(f"# {s['meta']['title']} — 플레이 기록\n")
    P.note(f"> {s['meta'].get('origin')} · {s['meta'].get('era')} · "
           f"용의자 {len(cast)}명 · {rounds}라운드\n")
    P.note("## 시작 — 손에 쥔 것\n")
    for cid in sorted(held):
        cl = next(c for c in s["clue_graph"] if c["id"] == cid)
        P.note(f"- `{cid}` {cl.get('surface','')}")
        for m in P.see(cl):
            P.note(f"  - → **{m}**")
    d = s["death"]
    P.note(f"\n{s['victim']['name']}{_j(s['victim']['name'],'이/가')} **{d['time_slot']}**, "
           f"**{pn.get(d['place'])}**에서 {d.get('weapon')}에 죽었다.\n")

    for r in range(1, rounds + 1):
        P.note(f"\n---\n\n## {r}라운드\n")
        for e in (s.get("events") or []):
            if e.get("round") == r:
                P.note(f"> ★ **{e.get('name') or e.get('title')}** — {e.get('text')}")
                P.note(f">\n> 판이 바뀐다: {e.get('effect')}\n")

        # ── 장소를 뒤진다 ────────────────────────────────────────
        got_any = []
        for pid, name in pn.items():
            new = [cl for cl in by_place.get(pid, [])
                   if cl["id"] not in held and (cl.get("reveal_round") or 1) <= r]
            if not new:
                continue
            layer = ((s.get("place_layers") or {}).get("layers") or {}).get(pid)
            if isinstance(layer, dict):
                layer = layer.get(str(r))
            elif isinstance(layer, list) and len(layer) >= r:
                layer = layer[r - 1]
            P.note(f"**{name}{_j(name)} 뒤진다** — {layer or ''}")
            for cl in new:
                held.add(cl["id"]); got_any.append(cl)
                tag = " ★결정타" if cl.get("decisive") else ""
                P.note(f"- `{cl['id']}`{tag} {cl.get('surface','')}")
                for m in P.see(cl):
                    P.note(f"  - → **{m}**")
            P.note("")

        # ── 묻는다 ──────────────────────────────────────────────
        alive = [cid for cid in cast if cid not in P.cleared]
        kind = ["alibi", "relation", "secret"][min(r - 1, 2)]
        _k = '동선' if kind == 'alibi' else '관계' if kind == 'relation' else '비밀'
        P.note(f"**심문 — 이번 라운드는 {_k}{_j(_k)} 판다**\n")
        for cid in alive:
            c = cast[cid]
            qs = QS.build(s, kind, cid)[:2]
            for row in qs:
                q = row["q"]
                ans = ""
                if llm:
                    ans = _ask(s, c, q, gauges[cid], llm)
                P.note(f"- **{P.name[cid]}**에게 — “{q}”")
                if ans:
                    P.note(f"  - 「{ans}」")
                    for slot, nm in _claims(ans, pn.values(), s["time_slots"]):
                        m = P.hear(cid, slot, nm)
                        if m:
                            P.note(f"  - → **{m}**")
                gauges[cid].apply(q, ans)
        # 결정타를 쥐었으면 그 사람에게 들이댄다
        dec = next((cl for cl in s["clue_graph"] if cl.get("decisive") and cl["id"] in held), None)
        if dec and dec.get("points_to") in alive:
            tid = dec["points_to"]
            g = gauges[tid]
            P.note(f"\n**{P.name[tid]}에게 `{dec['id']}`를 들이댄다.**")
            g.apply(dec.get("surface", ""), "", evidence_shown=True)
            P.note(f"- 압박 {int(g.state()['value'])}/100 · "
                   + ("**자백 임박**" if g.will_confess() else "아직 모자라다"))
            for k in range(3):
                if g.will_confess():
                    break
                g.apply(f"그 길을 아는 건 자네뿐이야. 더 숨길 것이 남았나? {k}", "")
            P.note(f"- 몰아붙인 뒤 {int(g.state()['value'])}/100 — "
                   + ("**무너진다**" if g.will_confess() else "버틴다"))

        rk = [(v, P.name[k]) for v, k in P.ranked() if v > -50]
        P.note(f"\n*{r}라운드를 마친 판단:* " +
               " · ".join(f"{n} {v:.1f}" for v, n in rk))
        if notebook:
            opened = sum(1 for cid in cast if gauges[cid].hit.get("trigger"))
            P.note(_notebook_snapshot(P, s, held, r, gauges, opened))

    # ── 지목 ────────────────────────────────────────────────────
    P.note("\n---\n\n## 지목\n")
    best = P.ranked()[0][1]
    P.note(f"가장 의심스러운 자는 **{P.name[best]}**이다. 근거는 이렇다.\n")
    for w in P.why[best]:
        P.note(f"- {w}")
    cul = next(c for c in s["cast"] if c.get("is_culprit"))
    sc = s.get("scoring") or {}
    opened = sum(1 for cid in cast if gauges[cid].hit.get("trigger"))
    pts = (sc.get("culprit_correct", 5) if best == cul["id"] else 0) \
        + sc.get("secret_revealed_each", 1) * opened
    P.note(f"\n**결과** — {'맞았다' if best == cul['id'] else '틀렸다. 진범은 ' + cul['name']}"
           f" · 비밀 {opened}개 · 점수 {pts}/{sc.get('max')}")
    gr = sorted((s.get("ending") or {}).get("grades") or [], key=lambda g: g.get("min", 0))
    grade = None
    for g in gr:
        if pts >= g.get("min", 0):
            grade = g
    if grade:
        P.note(f"\n### 엔딩 · {grade.get('name') or grade.get('title')}\n")
        P.note(grade.get("text", ""))
    tr = (s.get("ending") or {}).get("truth_reveal")
    if tr:
        P.note(f"\n### 진상\n\n{tr}")
    text = "\n".join(P.log)
    if out:
        open(out, "w", encoding="utf-8").write(text)
    return text


def _ask(s, c, q, gauge, llm):
    from stress_agent import suspect_system
    from turn_schema import format_block, parse_turn
    from stance import decide, directive
    pdm = {p["id"]: p for p in s["map"]["places"]}
    mine = [pdm[c["timeline"][sl]]["name"] for sl in s["time_slots"]]
    st = decide(s, c, q, gauge.state(), False, set(), held_clues=set())
    lt = st["stance"] in ("ADMIT", "BREAK")
    sysmsg = (suspect_system(s, c) + "\n\n"
              + format_block(c, gauge.state()["value"], allow_guilt_tint=False,
                             forced_disclosure=lt)
              + "\n\n" + directive(st, c, mine))
    try:
        raw = llm.chat([{"role": "system", "content": sysmsg},
                        {"role": "user", "content": q}])
    except Exception as e:
        return f"(호출 실패: {str(e)[:40]})"
    return parse_turn(raw).get("line") or raw[:120]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--notebook", action="store_true")
    a = ap.parse_args()
    llm = None
    if a.api:
        from llm_api import ApiLLM
        llm = ApiLLM(max_new_tokens=260)
    elif a.model:
        from stress_local import LocalLLM
        llm = LocalLLM(a.model)
    s = json.load(open(a.path, encoding="utf-8"))
    out = a.out or f"플레이기록_{os.path.basename(a.path).replace('.json','')}.md"
    print(run(s, llm, out, notebook=a.notebook))
    print(f"\n저장: {out}")
