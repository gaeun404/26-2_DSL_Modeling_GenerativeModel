# -*- coding: utf-8 -*-
"""
make_novel.py — 시나리오 JSON에서 **바이블(novel.md)** 을 다시 뽑는다.

왜 필요한가
  out/ 에 있던 *_novel.md는 14편뿐이고, 전부 손으로 쓴 옛 버전이다.
  그 뒤로 스키마가 v2로 올라갔고(비밀·짐·목표·타임라인·페이즈·엔딩),
  관계와 말투가 전부 다시 쓰였다. 문서와 데이터가 따로 논다.
  게다가 별주부전·콩쥐팥쥐처럼 **지금 없는 편**의 문서가 남아 있다.

  바이블은 손으로 관리할 물건이 아니다. JSON이 진실이고, 문서는 그 표현이다.
  그래서 매번 다시 뽑는다.

무엇이 들어가나
  머리말 · 세계 · 그날 밤 · 진실 · 왜 그 사람이 아닌가 ·
  인물(말투·관계·비밀·짐·목표) · 인물별 인생소설 ·
  단서의 결 · 페이즈 · 엔딩 · 채점 · 정답

사용:
    python make_novel.py                      # out/ 전편
    python make_novel.py out/13_푸른수염.json
"""
import json, glob, sys, os, re

def _j(w, pair="을/를"):
    a, b = pair.split("/")
    if not w:
        return b
    ch = w[-1]
    if not ("가" <= ch <= "힣"):
        return b
    jong = (ord(ch) - 0xAC00) % 28
    if pair == "으로/로":
        return b if jong in (0, 8) else a
    return a if jong else b


def _pn(s):
    return {p["id"]: p["name"] for p in s["map"]["places"]}


def build(s):
    L = []
    m = s.get("meta", {})
    v = s.get("victim", {})
    d = s.get("death", {})
    tr = s.get("trick", {})
    sol = s.get("solution", {})
    pn = _pn(s)
    cast = s["cast"]
    cul = next((c for c in cast if c.get("is_culprit")), {})
    bg = s.get("background", {})

    # ── 머리말 ────────────────────────────────────────────────────
    L += [f"# {m.get('title','제목 없음')} — {m.get('origin','원작 미상')} 각색 살인 시나리오 (바이블)", ""]
    L += [f"> 원작: {m.get('origin','—')} · 시대: {m.get('era','—')} · "
          f"무대: {(bg.get('setting_raw') or {}).get('location','—')}"]
    if tr.get("name"):
        L += [f"> 중심 트릭: **{tr.get('name')}** — {tr.get('desc','')}"]
    L += [""]

    # ── 세계 ──────────────────────────────────────────────────────
    L += ["## 세계", "", (bg.get("atmosphere") or "").strip(), ""]
    L += [f"**{v.get('name','피해자')}**({v.get('role') or v.get('public','')}). "
          + (v.get("bio") or "").strip(), ""]
    L += ["이 집에 얽힌 다섯 사람이 있다.", ""]
    for c in cast:
        L += [f"- **{c['name']}** — {c.get('public','')}. {c.get('kill_motive','')}"]
    L += [""]

    # ── 그날 밤 ───────────────────────────────────────────────────
    L += ["## 그날 밤", ""]
    tev = s.get("timeline_events") or []
    if tev:
        for e in tev:
            who = next((x["name"] for x in cast if x["id"] == e.get("who")),
                       "모두" if e.get("who") == "all" else "")
            star = "**" if "★" in (e.get("text") or "") else ""
            L += [f"- `{e.get('time','')}` {star}{who + ' — ' if who else ''}"
                  f"{(e.get('text') or '').replace('★','')}{star}"]
    else:
        for sl in s["time_slots"]:
            row = " / ".join(f"{c['name']}:{pn.get((c.get('timeline') or {}).get(sl),'?')}" for c in cast)
            L += [f"- **{sl}** — {row}"]
    L += ["",
          f"{v.get('name','피해자')}{_j(v.get('name',''),'은/는')} **{d.get('time_slot','')}**, "
          f"**{pn.get(d.get('place'),'현장')}**에서 {d.get('weapon','흉기')}에 목숨을 잃었다.", ""]

    # ── 진실 ──────────────────────────────────────────────────────
    L += ["## 진실 (범인만 안다)", ""]
    L += [(sol.get("reason") or d.get("method") or "").strip(), ""]
    if cul.get("lies"):
        li = cul["lies"][0]
        L += [f"**{cul.get('name')}의 거짓말** — 겉으로는 “{li.get('claim','')}”라고 말한다. "
              f"실제로는 {li.get('truth','')}.", ""]

    # ── 가짜 유력자 ───────────────────────────────────────────────
    fake = [c for c in cast if not c.get("is_culprit")
            and (c.get("mmo") or {}).get("opportunity")]
    if fake:
        L += ["## 왜 그 사람이 아닌가 (가짜 유력자의 함정)", ""]
        for c in fake:
            exc = [cl for cl in s["clue_graph"] if c["id"] in (cl.get("exculpates") or [])]
            why = exc[0].get("surface") if exc else "결정적 수단이 없다"
            L += [f"- **{c['name']}** — 겉보기엔 의심스럽다({c.get('motive_label','')}). "
                  f"그러나 {why}"]
        L += [""]

    # ── 인물 ──────────────────────────────────────────────────────
    L += ["## 인물", ""]
    for c in cast:
        p = c.get("profile") or {}
        vo = (c.get("persona") or {}).get("voice") or {}
        L += [f"### {c['name']} — {c.get('public','')}", ""]
        L += [f"- 신분: {p.get('status','')} · {p.get('age','')} {p.get('sex','')}"]
        if vo:
            L += [f"- 말투: **{vo.get('form')}** ({vo.get('form_desc')}) · "
                  f"어미 {' / '.join(vo.get('endings') or [])} · "
                  f"자칭 {' · '.join(vo.get('self') or [])} · 심문관 호칭 {vo.get('address')}"]
            L += [f"- 말버릇: {vo.get('habit','')}"]
        L += [f"- 성격: {(c.get('persona') or {}).get('personality','')}"]
        L += [f"- 그 밤의 자리: " + ", ".join(
            f"{sl} {pn.get((c.get('timeline') or {}).get(sl),'?')}" for sl in s["time_slots"])]
        L += [f"- 겉으로 하는 말: “{c.get('alibi_narration','')}”"]
        for sec in (c.get("secrets") or []):
            hf = [next((x["name"] for x in cast if x["id"] == i), i)
                  for i in (sec.get("hidden_from") or [])]
            L += [f"- 감춘 것: {sec.get('text','')}"
                  + (f" (특히 {' · '.join(hf)}에게)" if hf else "")]
            L += [f"  - 열리는 조건: {', '.join(sec.get('forced_by') or [])}"]
        for b in (c.get("belongings") or []):
            L += [f"- 짐 `{b.get('id')}`: {b.get('name','')} — {b.get('reveals','')}"]
        for o in (c.get("objectives") or []):
            L += [f"- 목표: {o.get('desc','')}"]
        rel = c.get("relationships") or {}
        if rel:
            nm = {x["id"]: x["name"] for x in cast}
            nm["victim"] = v.get("name", "죽은 이")
            L += ["- 관계:"]
            for k, txt in rel.items():
                L += [f"  - **{nm.get(k,k)}** — {txt}"]
        L += [""]

    # ── 인생소설 ──────────────────────────────────────────────────
    L += ["---", "", "# 인물별 인생소설 (에이전트 정보 창고)", "",
          "> 돌발 질문에도 자기모순 없이 답하도록 삶의 구석까지 채운 글. "
          "범인은 범행 자백을 뺀 커버스토리까지만.", ""]
    if v.get("bio"):
        L += [f"## 피해자 · {v.get('name')}", "", v["bio"].strip(), ""]
    for c in cast:
        L += [f"## {c['name']} — {c.get('public','')}", "",
              (c.get("life_story") or c.get("bio") or "").strip(), ""]

    # ── 단서 ──────────────────────────────────────────────────────
    L += ["---", "", "## 단서의 결 (라운드별)", ""]
    rounds = s.get("config", {}).get("rounds", 3)
    for r in range(1, rounds + 1):
        L += [f"### {r}라운드", ""]
        for cl in s["clue_graph"]:
            if (cl.get("reveal_round") or 1) != r:
                continue
            tag = " **[결정적]**" if cl.get("decisive") else ""
            loc = f" `{pn.get(cl.get('location'),'')}`" if cl.get("location") else ""
            aff = cl.get("affects") or []
            an = ", ".join(next((x["name"] for x in cast if x["id"] == a), a) for a in aff)
            L += [f"- `{cl['id']}`{loc}{tag} {cl.get('surface','')}"
                  + (f"  ↳ 걸리는 사람: {an}" if an else "")]
        L += [""]

    # ── 페이즈 / 이벤트 ───────────────────────────────────────────
    if s.get("phases"):
        L += ["## 진행 (페이즈)", ""]
        for ph in s["phases"]:
            L += [f"{ph.get('no')}. **{ph.get('name')}** — {ph.get('content','')} "
                  f"({ph.get('time','')})"]
        L += [""]
    if s.get("events"):
        L += ["## 중반 이벤트", ""]
        for e in s["events"]:
            L += [f"- {e.get('round')}라운드 · **{e.get('name','')}** — {e.get('text','')}",
                  f"  - 효과: {e.get('effect','')}"]
        L += [""]

    # ── 채점 / 엔딩 ───────────────────────────────────────────────
    sc = s.get("scoring") or {}
    if sc:
        L += ["## 채점", "",
              f"- 범인 지목 **{sc.get('culprit_correct')}점**",
              f"- 비밀 하나당 **{sc.get('secret_revealed_each')}점**",
              f"- 만점 **{sc.get('max')}점**", ""]
    en = s.get("ending") or {}
    if en.get("grades"):
        L += ["## 엔딩 낭독", ""]
        for g in en["grades"]:
            L += [f"- **{g.get('min')}점 이상 · {g.get('name','')}** — {g.get('text','')}"]
        L += ["", f"**진상 낭독**: {en.get('truth_reveal','')}", ""]

    # ── 정답 ──────────────────────────────────────────────────────
    L += ["## 정답", "",
          f"- **범인**: {cul.get('name','')} ({cul.get('public','')})",
          f"- **흉기**: {sol.get('weapon') or d.get('weapon','')}",
          f"- **동기**: {sol.get('motive_label','')} "
          f"(키워드: {' · '.join(sol.get('motive_keywords') or [])})", ""]
    return "\n".join(L)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    n = 0
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        base = os.path.basename(p).replace(".json", "")
        out = os.path.join(os.path.dirname(p), f"{base}_novel.md")
        txt = build(s)
        open(out, "w", encoding="utf-8").write(txt)
        n += 1
        print(f"  {os.path.basename(out):34} {len(txt):>7,}자")
    print(f"\n{n}편 바이블 생성")
