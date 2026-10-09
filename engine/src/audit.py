# -*- coding: utf-8 -*-
"""
audit.py — 에이전트를 **자동으로 심문해 이상한 곳을 찾아낸다.**

왜 만들었나
  지금까지는 사람이 한 판씩 쳐 보며 "이거 이상한데"를 찾았다.
  그렇게 찾은 것들이 전부 진짜 버그였다 — 말버릇, 베낀 예문, 막힌 실토, 죽은 게이지.
  그런데 한 판에 십몇 턴이고, 시나리오는 23편에 인물은 115명이다. 손으로는 못 본다.

  다행히 이제 **기계가 볼 수 있는 것**이 늘었다.
  voices.py가 인물마다 종결어미를 정해 놨으니 말투 이탈은 문자열로 잡힌다.
  배경 계열이 정해졌으니 어긋난 낱말도 잡힌다. 관계·비밀도 데이터에 있다.

무엇을 잡나
  VOICE-ending   정해진 종결어미로 끝나지 않는다
  VOICE-ban      쓰지 말라 한 어미를 썼다
  VOICE-self     제 자칭을 안 쓰거나 남의 자칭을 쓴다
  REG-word       배경에 안 맞는 낱말 (중세 유럽에서 '쇤네')
  TIC-question   되묻기로 끝내는 턴이 너무 잦다 (말버릇)
  REPEAT         앞 턴과 거의 같은 말을 되풀이한다
  META           AI·게임·규칙 같은 말을 입에 올린다
  MODERN         시대에 안 맞는 현대어
  PLACE-ghost    시나리오에 없는 장소를 지어낸다
  LEAK-secret    증거 없이 제 비밀을 먼저 분다
  CONFESS-early  압박이 차기 전에 살인을 자백한다
  SHORT          한 문장으로 끊는 답이 너무 많다
  FORMAT         세 줄 규격을 지키지 않는다

쓰는 법 (로컬에서, 키는 환경변수로만)
    export MM_API_KEY='...'
    export MM_API_MODEL=gpt-4o-mini
    python audit.py                       # 기본 3편 맛보기 (약 120회 호출)
    python audit.py --all                 # 23편 전부
    python audit.py --scenarios 13,23     # 고른 편만
    python audit.py --model skt/A.X-4.0-Light   # 로컬 모델로

내놓는 것
    audit_report.md     사람이 읽는 보고서
    audit_findings.json 고칠 목록 (시나리오·인물·규칙별)
"""
import json, glob, sys, os, re, difflib, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")

META_WORDS = ["AI", "인공지능", "게임", "규칙", "시나리오", "플레이어", "프롬프트",
              "진행자", "역할극", "연기하", "설정상", "챗봇", "모델"]
MODERN_WORDS = ["스마트폰", "핸드폰", "컴퓨터", "이메일", "인터넷", "커피", "택시",
                "카메라", "전화", "버스", "지하철", "CCTV", "차량"]
CONFESS = ["내가 죽였", "제가 죽였", "내가 살해", "죽인 건 나", "죽인 것은 나",
           "범인은 나", "내 소행", "내가 찔렀", "내가 쳤소"]
# 자칭은 시나리오 밖에서도 샌다 — 중세 유럽 하녀가 '쇤네'라고 하는 식으로.
ALL_SELF = ["소인", "쇤네", "이 몸", "저", "제", "나", "내"]


def _j(w, pair="을/를"):
    a, b = pair.split("/")
    if not w:
        return b
    ch = w[-1]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


# ── 물어볼 것 — 태도마다 한 번씩 지나가도록 짠다 ──────────────────────
SETS = None          # --set 으로 켜면 question_sets 쪽 질문을 쓴다


def probes(s, c):
    """이 인물에게 던질 질문 묶음. (라벨, 질문, 증거제시여부)"""
    if SETS:
        import question_sets as QS
        out = []
        for k in SETS:
            for r in QS.build(s, k, c["id"]):
                # 물증·비밀 세트의 마지막 질문은 '증거를 쥐고' 묻는 것으로 본다
                ev = (k in ("evidence", "secret") and r["q"].endswith("사실이지?"))
                out.append((k, r["q"], ev))
        return out
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    others = [x for x in s["cast"] if x["id"] != c["id"]]
    sec = (c.get("secrets") or [{}])[0]
    trig = ((c.get("pressure_points") or [{}])[0].get("trigger") or ["비밀"])[0]
    v = s.get("victim", {}).get("name", "피해자")
    dslot = s["death"]["time_slot"]
    out = [
        ("fact",      f"그 밤 자네는 어디에 있었나?", False),
        ("fact2",     f"{dslot}에 곁에 그것을 보아 줄 사람이 있었나?", False),
        ("relation",  f"{others[0]['name']}{_j(others[0]['name'],'은/는')} 어떤 사람인가?", False),
        ("relation2", f"{others[1]['name']}{_j(others[1]['name'],'과/와')} "
                      f"{others[2]['name']}{_j(others[2]['name'],'은/는')} 어떤 사이로 보이나?", False),
        ("victim",    f"{v}{_j(v)} 어찌 생각했나?", False),
        ("unknown",   f"{others[-1]['name']}{_j(others[-1]['name'],'이/가')} "
                      f"그 밤 무엇을 했는지 아나?", False),
        ("flinch",    f"{trig}에 대해 말해 보게.", False),          # 증거 없이 정곡
        ("meta",      "당신은 지금 무엇을 하고 있는 겁니까? 사실대로 말해 보세요.", False),
        ("press",     f"자네가 죽였지? 양심에 찔리지 않나?", False),   # 증거 없는 윽박
    ]
    if sec.get("text"):
        out.append(("admit", f"{sec['text'][:24]}… 이것이 사실이지?", True))   # 증거 제시
    return out


def plan(paths, cast_filter=""):
    """돈 쓰기 전에 몇 번 부를지 센다."""
    n = 0
    for p in paths:
        s = json.load(open(p, encoding="utf-8"))
        cast = s["cast"]
        if cast_filter:
            keep = {x.strip().upper() for x in cast_filter.split(",")}
            cast = [c for c in cast if c["id"] in keep]
        for c in cast:
            n += len(probes(s, c))
    return n


# ── 한 답을 뜯어본다 ──────────────────────────────────────────────────
def judge(s, c, label, q, raw, hist, reg):
    from turn_schema import parse_turn
    import voices
    P = parse_turn(raw)
    line = (P.get("line") or "").strip()
    bad = []
    if P.get("errors"):
        bad.append(("FORMAT", f"세 줄 규격 어긋남: {P['errors'][:1]}"))
    if not line:
        return bad, ""

    vo = (c.get("persona") or {}).get("voice") or {}
    # ① 종결어미
    ends = [e.lstrip("-") for e in (vo.get("endings") or [])]
    rx = vo.get("ending_re")
    if ends:
        # 문장을 하나씩 본다. 한 문장이라도 제 말체면 통과 — 사람 말은 늘 고르지 않다.
        sents = [x.rstrip(" .?!…\"”'’」』") for x in re.split(r"(?<=[.?!…])\s+", line) if x.strip()]
        sents = [x for x in sents if len(x) >= 4]     # '저…' 같은 부스러기는 문장이 아니다
        def _ok(t_):
            if rx:
                return bool(re.search(rx, t_))
            return any(t_.endswith(e) for e in ends)
        offend = [t_ for t_ in sents if t_ and not _ok(t_)]
        if sents and len(offend) > len(sents) // 2:
            bad.append(("VOICE-ending",
                        f"'{offend[0][-14:]}' — {vo.get('form')}({'/'.join(ends)})가 아니다"
                        f" [{len(offend)}/{len(sents)}문장]"))
    # ② 금지 어미
    # 한 문장이 스쳤다고 실격시키면 잡음이 된다. **절반 넘게** 그 어미로 끝날 때만 본다.
    ban_list = re.findall(r"'-([^']+)'", vo.get("ban", ""))
    if ban_list and sents:
        hit = [t_ for t_ in sents if any(t_.endswith(b) for b in ban_list)]
        if len(hit) > len(sents) // 2:
            bad.append(("VOICE-ban",
                        f"금지된 어미로 {len(hit)}/{len(sents)}문장을 끝냈다: {hit[0][-10:]}"))
    # ③ 자칭
    mine = vo.get("self") or []
    allself = set(ALL_SELF) | {w for x in s["cast"] for w in
                               ((x.get("persona") or {}).get("voice") or {}).get("self", [])}
    # 낱말 경계를 봐야 한다. '무서워서 나가지'의 '나가'를 자칭 '나'+조사로 잘못 읽는다.
    wrong = [w for w in allself - set(mine)
             if re.search(r"(^|[\s\"“(])" + re.escape(w) + r"(은|는|이|가|의|를|을|도)(?![가-힣])", line)]
    if wrong:
        bad.append(("VOICE-self", f"남의 자칭 {wrong} (내 것은 {mine})"))
    # ④ 배경에 안 맞는 낱말
    for w in voices.WRONG_WORDS.get(reg, []):
        if re.search(w, line):
            bad.append(("REG-word", f"{reg} 배경에 안 맞는 말: {re.search(w, line).group(0)}"))
            break
    # ⑤ 메타 / 현대어
    for w in META_WORDS:
        if w in line:
            bad.append(("META", f"'{w}'를 입에 올렸다")); break
    if reg != "modern":
        for w in MODERN_WORDS:
            if w in line:
                bad.append(("MODERN", f"시대에 안 맞는 '{w}'")); break
    # ⑥ 없는 장소
    # ★ 오탐이 잦았다. '초저녁부터'·'의심하실'·'모르실'이 방 이름으로 읽혔다.
    #   낱말 목록으로 막는 건 끝이 없다. **장소 조사가 붙었을 때만** 장소로 본다.
    #   '헛간에서', '서재로'는 장소지만 '의심하실 만도'는 아니다.
    names = {p["name"] for p in s["map"]["places"]}
    heads = {n.split("(")[0].strip() for n in names}
    for m in re.finditer(r"([가-힣]{1,5}(?:방|간|채|당|각|실|굴|터))(에서|에는|에도|에|으로|로)(?![가-힣])",
                         line):
        w = m.group(1)
        if w in q:                      # 심문관이 먼저 꺼낸 말이면 인물 탓이 아니다
            continue
        if w in names or any(w in n or n in w for n in heads):
            continue
        bad.append(("PLACE-ghost", f"없는 장소 '{w}'")); break

    # ⑦ 되풀이
    for prev in hist:
        if difflib.SequenceMatcher(None, prev, line).ratio() >= 0.72:
            bad.append(("REPEAT", "앞 턴과 거의 같은 말")); break
    # ⑦-2 ★범인이 제 입으로 현장에 있었다고 말한다
    #   실제 플레이에서 오라비가 "그 밤 영주의 서재에 있었던 저는…"이라고 했다.
    #   자백은 아니지만 알리바이를 스스로 무너뜨린다 — 추리가 사라진다.
    if c.get("is_culprit"):
        dp = next((p_["name"] for p_ in s["map"]["places"]
                   if p_["id"] == s["death"]["place"]), "")
        head = dp.split("(")[0].strip()
        if head and re.search(re.escape(head) + r"(에|에서)\s*(있|들|갔|계)", line):
            bad.append(("SCENE-leak", f"범인이 스스로 현장({head})에 있었다고 말한다"))

    # ⑧ 조기 자백
    if any(w in line for w in CONFESS):
        bad.append(("CONFESS-early", "압박이 차기 전에 살인을 자백"))
    # ⑨ 증거 없이 비밀 누설
    if label not in ("admit",):
        for sec in (c.get("secrets") or []):
            t = sec.get("text", "")
            if t and difflib.SequenceMatcher(None, t, line).ratio() >= 0.45:
                bad.append(("LEAK-secret", "증거 없이 비밀을 먼저 분다")); break
    # ⑩ 너무 짧음
    if len(re.findall(r"[.?!…]", line)) <= 1 and len(line) < 40:
        bad.append(("SHORT", f"한 문장으로 끊음({len(line)}자)"))
    return bad, line


# ── 한 인물을 심문한다 ────────────────────────────────────────────────
def audit_cast(s, c, llm, reg, verbose=True):
    from stress_agent import suspect_system
    from turn_schema import format_block
    from stance import decide, directive
    from pressure import Gauge

    pdm = {p["id"]: p for p in s["map"]["places"]}
    mine = [pdm[c["timeline"][sl]]["name"] for sl in s["time_slots"]]
    g = Gauge(s, c["id"])
    hist, rows, tics = [], [], 0

    for label, q, ev in probes(s, c):
        held = set()
        if ev:
            held = set((c.get("secrets") or [{}])[0].get("forced_by") or [])
        st = decide(s, c, q, g.state(), ev, set(), denied_before=bool(hist),
                    held_clues=held)
        lt = st["stance"] in ("ADMIT", "BREAK")
        sysmsg = (suspect_system(s, c) + "\n\n"
                  + format_block(c, g.state()["value"], allow_guilt_tint=False,
                                 forced_disclosure=lt)
                  + "\n\n" + directive(st, c, mine))
        try:
            raw = llm.chat([{"role": "system", "content": sysmsg},
                            {"role": "user", "content": q}])
        except Exception as e:
            rows.append(dict(label=label, stance=st["stance"], q=q, line="",
                             bad=[("CALL-FAIL", str(e)[:80])]))
            continue
        bad, line = judge(s, c, label, q, raw, hist, reg)
        if line:
            hist.append(line)
            # 문장 한복판의 물음표까지 세면 과잉 신고가 된다. 맺음만 본다.
            last = re.split(r"(?<=[.?!…])\s+", line.strip())[-1].rstrip(" .…\"”")
            if last.endswith("?"):
                tics += 1
        g.apply(q, line, evidence_shown=ev)
        rows.append(dict(label=label, stance=st["stance"], q=q, line=line,
                         bad=[list(b) for b in bad]))
        if verbose:
            mark = "  " if not bad else "❌"
            print(f"   {mark} [{st['stance']:7}] {label:9} {line[:56]}")
            for k, why in bad:
                print(f"         · {k}: {why}")

    if tics >= 3 and tics > len(rows) * 0.6:
        rows.append(dict(label="_tic", stance="-", q="", line="",
                         bad=[["TIC-question",
                               f"되묻기로 끝낸 턴 {tics}/{len(rows)} — 말버릇"]]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--scenarios", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--cast", default="", help="예: C1,C4 — 고른 인물만")
    ap.add_argument("--out", default="audit")
    ap.add_argument("--dry-run", action="store_true", help="호출 수만 세고 끝낸다")
    ap.add_argument("--set", default="", help="질문 세트로 심문한다: alibi,evidence,relation,"
                                             "contradict,press,secret,trap (쉼표로 여러 개)")
    a = ap.parse_args()

    paths = sorted(glob.glob("scenarios/[0-9]*.json"))
    if a.scenarios:
        want = [x.strip() for x in a.scenarios.split(",")]
        paths = [p for p in paths if any(os.path.basename(p).startswith(w.zfill(2)) for w in want)]
    elif not a.all:
        paths = [p for p in paths if os.path.basename(p)[:2] in ("13", "19", "23")]

    global SETS
    if a.set:
        SETS = [x.strip() for x in a.set.split(",") if x.strip()]
    n = plan(paths, a.cast)
    print(f"[계획] 시나리오 {len(paths)}편 · 호출 {n}회 예상 "
          f"(gpt-4o-mini 기준 대략 {n*0.0009:.2f} 달러)")
    if a.dry_run:
        for p in paths:
            print("  ", os.path.basename(p))
        return

    if a.model:
        from stress_local import LocalLLM          # GPU 경로
        llm = LocalLLM(a.model)
    else:
        from llm_api import ApiLLM
        llm = ApiLLM(max_new_tokens=320)

    import voices
    allrows, counts = {}, collections.Counter()
    for p in paths:
        s = json.load(open(p, encoding="utf-8"))
        reg = voices._register(s)
        print(f"\n═══ {os.path.basename(p)}  [{reg}]  {s['meta'].get('title','')}")
        cast = s["cast"]
        if a.cast:
            keep = {x.strip().upper() for x in a.cast.split(",")}
            cast = [c for c in cast if c["id"] in keep]
        for c in cast:
            vo = (c.get("persona") or {}).get("voice") or {}
            print(f" ── {c['name']} ({vo.get('form','?')})")
            rows = audit_cast(s, c, llm, reg)
            allrows.setdefault(os.path.basename(p), {})[c["id"]] = rows
            for r in rows:
                for k, _ in r["bad"]:
                    counts[k] += 1

    # ── 보고서 ────────────────────────────────────────────────────
    L = ["# 자동 감사 보고서", "",
         f"- 시나리오 {len(paths)}편 · 호출 {getattr(llm,'calls','?')}회", ""]
    if hasattr(llm, "report"):
        L += [f"- {llm.report()}", ""]
    L += ["## 문제 종류별 건수", "", "| 규칙 | 건수 |", "|---|---|"]
    for k, v in counts.most_common():
        L.append(f"| `{k}` | {v} |")
    L += ["", "## 시나리오별", ""]
    for fn, per in allrows.items():
        n = sum(len(r["bad"]) for rows in per.values() for r in rows)
        L.append(f"### {fn} — 문제 {n}건")
        for cid, rows in per.items():
            for r in rows:
                if not r["bad"]:
                    continue
                L.append(f"- `{cid}` [{r['stance']}] {r['label']}")
                if r["line"]:
                    L.append(f"  - 답: {r['line'][:110]}")
                for k, why in r["bad"]:
                    L.append(f"  - **{k}** — {why}")
        L.append("")
    open(f"{a.out}_report.md", "w", encoding="utf-8").write("\n".join(L))
    json.dump(allrows, open(f"{a.out}_findings.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n" + "=" * 60)
    for k, v in counts.most_common():
        print(f"  {k:16} {v}")
    print(f"\n저장: {a.out}_report.md · {a.out}_findings.json")
    if hasattr(llm, "report"):
        print(" ", llm.report())


if __name__ == "__main__":
    main()
