# -*- coding: utf-8 -*-
"""
walk.py — **화면 순서대로 한 판을 걸어 본다.** 터미널에서 도는 모의 프론트엔드.

    인트로 → 사건 발생 → 피해자 → 용의자 → 라운드 시작 → 지도 → 장소
    → (탐색 · 알리바이 · 심문) → 반복 → 이벤트 → 대질 → 라운드 종료
    → 추리 → 범인 공개 → 재연 → 엔딩

■ 왜 만들었나
  fe_lint는 "필드가 스키마에 **있는가**"까지만 본다. 그러나 화면은 필드를
  **꺼내 써야** 성립한다. 이 파일은 프론트가 할 일을 그대로 한다 —
  문구·선택지·나레이션을 전부 스키마와 엔진에서만 꺼낸다.
  하드코딩이 한 줄도 없으므로, **빠진 것이 있으면 그 자리에서 (없음)으로 드러난다.**
  Figma Make에 들어가기 전에 여기서 먼저 걸러 내자는 것이다.

    python3 walk.py                    # 직접 골라 가며
    python3 walk.py --auto             # 알아서 끝까지 (구경만)
    python3 walk.py 38_cinderella.json --auto
    python3 walk.py --auto --quiet     # 화면 이름과 값만 (연결 점검용)

키가 필요 없다. 대사는 자리표시자로 나온다 — 판이 굴러가는지를 보는 것이 목적이다.
"""
import _boot, sys, json, glob, argparse, textwrap   # noqa: F401
import re as _RE
_JSON = _RE.compile(r"\{.*\}", _RE.S)

W = 78
MISSING = []                    # 스키마에서 못 꺼낸 것 — 마지막에 모아 보고한다


# ── 화면 그리기 ───────────────────────────────────────────────────────
def rule(ch="─"):
    print(ch * W)


def screen(sid, name, sub=""):
    print()
    rule("━")
    tail = f"   {sub}" if sub else ""
    print(f" [{sid}] {name}{tail}")
    rule("━")


def para(text, indent="   ", where=None):
    if text is None:
        return
    if where:
        audit_line(where, text)
    for line in textwrap.wrap(str(text), W - len(indent) - 1):
        print(indent + line)


def field(label, value, need=True):
    """스키마에서 꺼낸 값 하나. 없으면 표시하고 기록한다."""
    if value in (None, "", [], {}):
        if need:
            MISSING.append(label)
            print(f"   {label}: ⚠ (스키마에 없음)")
        return None
    return value


def ask(prompt, auto=None):
    if auto is not None:
        print(f"\n   ▸ {prompt} → {auto}")
        return str(auto)
    try:
        return input(f"\n   ▸ {prompt} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def _sn(s, *keys):
    node = (s.get("ui") or {}).get("story_narration") or {}
    for k in keys:
        node = (node or {}).get(k) if isinstance(node, dict) else None
    return (node or {}).get("text") if isinstance(node, dict) else None


def _scr(s, sid):
    return next((x for x in (s.get("ui") or {}).get("screens", [])
                 if x.get("id") == sid), {})



# ── 용의자 에이전트 ───────────────────────────────────────────────────
#   ★대사를 **진짜 LLM이 만든다** (2026-08-25).
#     자리표시자로는 말투도 회피도 실토도 볼 수 없다. --llm 을 주면 다섯 용의자가
#     각자 제 설정서와 이번 턴의 태도 지시문으로 실제 문장을 낸다.
#     판단은 여전히 코드(stance+pressure)가 한다 — 모델은 문장만 쓴다.
AGENT = {"llm": None, "hist": {}, "regen": 0, "stripped": 0}


def agent_open(path=".apikey", model="gpt-4o-mini"):
    import os
    if not os.path.exists(path) and not os.environ.get("MM_API_KEY"):
        return None
    if os.path.exists(path):
        os.environ["MM_API_KEY"] = open(path, encoding="utf-8").read().strip()
    os.environ.setdefault("MM_API_MODEL", model)
    from llm_api import ApiLLM
    AGENT["llm"] = ApiLLM(max_new_tokens=520, temperature=0.8)
    return AGENT["llm"]


def _no_question(text):
    """★되묻지 마라 (2026-08-26).
    지시문에 '물음표 금지'라고 적어 두었는데도 모델이 끝에 되물었다
    ('…기억나는 게 있을까요?'). 심문받는 쪽이 심문관에게 되물으면
    판이 뒤집힌다. 물음으로 끝나는 문장은 통째로 덜어낸다."""
    import re as _r
    outs = [x for x in _r.split(r"(?<=[.!?…」”])\s+", str(text or "")) if x.strip()]
    keep = [x for x in outs if "?" not in x and "？" not in x]
    if not keep:
        keep = [_r.sub(r"[?？]", ".", outs[0])] if outs else [""]
    return " ".join(keep).strip()


def agent_say(s, g, c, question, st):
    """이 인물이 이번 턴에 할 말. 판단(st)은 이미 나와 있고 문장만 만든다."""
    llm = AGENT["llm"]
    if not llm:
        return "(대사는 --llm 을 주면 실제 문장으로 나온다)"
    import stance, stress_agent
    cid = c["id"]
    sysmsg = stress_agent.suspect_system(s, c)
    if st.get("directive"):
        sysmsg += "\n\n" + st["directive"]
    if st.get("memory_briefing"):
        sysmsg += "\n" + st["memory_briefing"]
    if st.get("again_directive"):
        sysmsg += "\n" + st["again_directive"]
    hist = AGENT["hist"].setdefault(cid, [])
    reply = llm.chat([{"role": "system", "content": sysmsg}]
                     + hist[-6:] + [{"role": "user", "content": question}])
    if (stance.leaked(reply, st) or stance.confessed(reply, c)
            or stance.bad_address(reply)):
        hard = (sysmsg + "\n\n[다시 쓴다 — 방금 답이 규칙을 어겼다]\n"
                "· 감춰야 할 것을 한 조각도 꺼내지 마라. 아는 척도 하지 마라.")
        reply = llm.chat([{"role": "system", "content": hard}]
                         + hist[-4:] + [{"role": "user", "content": question}])
        AGENT["regen"] += 1
    reply = _no_question(reply)
    reply, n1 = stance.strip_leak(reply, st)
    reply, n2 = stance.strip_confession(reply, c)
    if stance.bad_address(reply):
        reply = stance.fix_address(reply); n2 += 1
    AGENT["stripped"] += n1 + n2
    hist += [{"role": "user", "content": question},
             {"role": "assistant", "content": reply}]
    g.remember(cid, question, reply)
    return reply


# ── 판정자 에이전트 ───────────────────────────────────────────────────
#   ★판단하는 쪽도 LLM이 맡는다.
#     '자동 진행'이 손으로 짠 규칙이면 그건 사람이 아니라 시계다.
#   ★정답지를 보지 않는다 — 화면에 뜨는 것만 넘긴다.
#     is_culprit·points_to·아직 안 열린 비밀은 한 글자도 넘기지 않는다.
PLAYER = {"llm": None, "log": [], "fallback": 0, "shown": set(), "feed": []}

_PLAYER_SYS = """너는 이 밤의 판정자다. 다섯 사람 가운데 하나가 사람을 죽였고,
너는 라운드마다 정해진 횟수만큼만 움직일 수 있다.

[할 수 있는 것]
· search   장소 하나를 조사한다 (1회). 그 방에 이번 라운드에 있는 단서가 한꺼번에 나온다.
· ask      한 사람에게 한 번 묻는다 (1회). 손에 쥔 단서 문장을 그대로 인용해 물으면 '들이대는' 것이 된다.
· confront 두 사람을 맞대 놓는다 (한 판에 한 번, 횟수를 쓰지 않는다).
· next     이번 라운드를 끝낸다.

[요령]
· 단서를 내밀 때는 ask 에 clue 를 함께 적어라. 그 단서 문장이 그대로 인용되어 상대 앞에 놓인다.
  단서 없이 묻기만 하면 상대는 절대 인정하지 않는다. **비밀을 열려면 단서를 들이대야 한다.**
· 어느 단서가 누구의 것인지는 알 수 없다. 단서 문장에 적힌 이름·신분·낱말·물건으로 짐작해 내밀어 보라.
  · 반응이 「FLINCH(흔들림)」이면 **정곡은 맞았고 증거가 모자란다** — 그 사람에게 다른 단서를 더 내밀어라.
  · 반응이 「ADMIT(실토)」이면 비밀이 열린 것이다. 「DEFLECT(회피)」면 헛짚었으니 사람을 바꿔라.
· already_tried 에 있는 짝(사람+단서)은 다시 하지 마라. 같은 말만 되풀이된다.
· confront 가 열려 있고 아직 안 썼다면 반드시 한 번 써라 — 횟수를 쓰지 않는다.
· 아직 안 만난 사람은 만나기만 해도 알리바이를 공짜로 들려준다.
· 남은 횟수가 적으면 이미 본 방을 또 보지 마라.

[답하는 방식]
JSON 한 줄만 출력한다. 다른 말은 한 글자도 쓰지 않는다.
{"action":"search","place":"P1","why":"한 줄"}
{"action":"ask","cast":"C2","clue":"K7","question":"물을 말","why":"한 줄"}
{"action":"confront","cast":"C1","with":"C5","question":"물을 말","why":"한 줄"}
{"action":"next","why":"한 줄"}
"""


def _player_view(s, g):
    st = g.state()
    return {
        "round": st["round"], "max_rounds": st["max_rounds"],
        "turns_left": st["turns_left"], "focus": st["round_focus"],
        "confront": {"unlocked": st["confront"]["unlocked"],
                     "tokens_left": st["confront"]["tokens_left"]},
        "places": [{"id": ps["place_id"], "name": ps["title"],
                    "searched_this_round": (ps["place_id"], g.current_round) in g.searched,
                    "owner": ps.get("standing_character")}
                   for ps in s["ui"]["place_screens"]],
        "cast": [{"id": c["id"], "name": c["name"], "public": c["public"],
                  "met": c["met"], "alibi": c["alibi"],
                  "secrets_open": c["secrets_open"]} for c in st["cast"]],
        "notebook": [{"id": e["id"], "how": e["how"], "surface": e["surface"]}
                     for e in st["notebook"]],
        # 같은 단서를 같은 사람에게 두 번 들이대지 않도록, 해 본 것을 넘긴다
        "already_tried": sorted(f"{c}+{k}" for c, k in PLAYER["shown"]),
        "last_reactions": PLAYER["feed"][-6:],
    }


def player_decide(s, g, fallback):
    """다음 한 수. LLM이 못 내면 손으로 짠 규칙으로 되돌아간다."""
    if not PLAYER["llm"]:
        return fallback()
    import json as _json
    try:
        raw = PLAYER["llm"].chat(
            [{"role": "system", "content": _PLAYER_SYS},
             {"role": "user", "content": "[지금 상황]\n"
              + _json.dumps(_player_view(s, g), ensure_ascii=False, indent=1)
              + "\n\n다음 한 수를 JSON 한 줄로 답하라."}])
        m = _JSON.search(raw or "")
        d = _json.loads(m.group(0)) if m else None
        if not isinstance(d, dict) or "action" not in d:
            raise ValueError("형식이 아니다")
        PLAYER["log"].append(d)
        return d
    except Exception:
        PLAYER["fallback"] += 1
        return fallback()


# ── 이상한 것 모으기 ──────────────────────────────────────────────────
#   ★손으로 한 판 치면서 눈으로 잡아내던 일을 대신한다.
#     끝까지 자동으로 돌린 뒤, 걸린 것만 마지막에 한 번에 보여 준다.
ISSUES = []
_BAD_WORDS = [
    ("배경 상투구", ["이 집 안에", "성은 그 밤", "이 집이 감추"]),
    ("플레이어 지시", ["적어 두어라", "기억해 두어라", "메모해 두어라"]),
    ("엉뚱한 호칭", ["그 아이", "그 애가", "걔가"]),
    ("빈 자리표시", ["{r}", "{n}", "{name}", "{cast_name}", "○○", "TODO", "TBD"]),
]


def flag(kind, detail):
    ISSUES.append((kind, detail))


def audit_line(where, text):
    x = str(text or "")
    if not x:
        return
    for kind, words in _BAD_WORDS:
        for w in words:
            if w in x:
                i = x.find(w)
                flag(kind, f"{where} — …{x[max(0,i-12):i+len(w)+12]}…")
    if where.startswith("나레이션") and len(x) > 180:
        flag("나레이션이 길다", f"{where} — {len(x)}자 (한 화면 두 문장 권장)")


def audit_report(s, g):
    import stance
    for cid, hist in AGENT["hist"].items():
        nm = g.cast[cid]["name"]
        for m in hist:
            if m["role"] != "assistant":
                continue
            a_ = m["content"]
            if "?" in a_ or "？" in a_:
                i = a_.find("?")
                flag("되묻기(물음표)", f"{nm} — …{a_[max(0,i-24):i+2]}…")
            bad = stance.bad_address(a_)
            if bad:
                flag("엉뚱한 호칭", f"{nm} — {bad}")
            aa = _RE.sub(r"\s+", "", a_)
            for blob in (g.cast[cid].get("bio"), g.cast[cid].get("life_story")):
                b = _RE.sub(r"\s+", "", str(blob or ""))
                hit = next((b[i:i+14] for i in range(0, max(0, len(b)-14), 3)
                            if b[i:i+14] and b[i:i+14] in aa), None)
                if hit:
                    flag("설정서 낭독", f"{nm} — …{hit}…")
                    break

    print()
    rule("═")
    if MISSING:
        print(f"  스키마에서 못 꺼낸 것 {len(dict.fromkeys(MISSING))}가지")
        for m in dict.fromkeys(MISSING):
            print(f"     · {m}")
    else:
        print("  화면이 쓰는 값은 스키마에 하나도 빠짐없이 있다")
    if ISSUES:
        import collections as _c
        by = _c.defaultdict(list)
        for k, d in ISSUES:
            by[k].append(d)
        print(f"\n  걸린 것 {len(ISSUES)}건")
        for k, ds in by.items():
            uniq = list(dict.fromkeys(ds))
            print(f"     [{k}] {len(ds)}건")
            for d in uniq[:3]:
                print(f"        {d[:90]}")
            if len(uniq) > 3:
                print(f"        … 그 밖 {len(uniq)-3}가지")
    else:
        print("\n  걸린 것 없음")
    if AGENT["llm"]:
        llm = AGENT["llm"]
        cost = llm.tokens_in / 1e6 * 0.15 + llm.tokens_out / 1e6 * 0.60
        print(f"\n  용의자 에이전트 — 호출 {llm.calls}회 · 다시 받음 {AGENT['regen']} "
              f"· 도려냄 {AGENT['stripped']} · 약 {cost*1400:.0f}원")
    if PLAYER["llm"]:
        print(f"  판정자 에이전트 — 고른 수 {len(PLAYER['log'])} "
              f"· 형식이 어긋나 규칙으로 돌아간 것 {PLAYER['fallback']}")


# ── 도입 ──────────────────────────────────────────────────────────────
def act_intro(s, quiet):
    ui = s["ui"]

    c = _scr(s, "case_open").get("copy", {})
    screen("S-05", "사건 공개", "건너뛰기 불가")
    print(f"   ┌ {c.get('header','')}")
    print(f"   │ 「{field('제목', c.get('title'))}」")
    para(field("배경", c.get("setting")), where="나레이션/배경")
    para(field("한 줄", c.get("logline")), where="나레이션/한 줄")
    for ln in (c.get("ready_lines") or []):
        print(f"   │ {ln}")
    print(f"   └ [{c.get('button','')}]   [{c.get('reroll_button','')}]")
    para(field("나레이션", _sn(s, "case_open")), where="나레이션/사건 공개")

    nr = ui.get("narration") or {}
    pages = nr.get("pages") or []
    screen("S-06", "오프닝 나레이션", f"{len(pages)}쪽 · 삽화 {nr.get('image_count','?')}장")
    if not pages:
        field("나레이션 쪽", None)
    for pg in (pages if not quiet else pages[:3]):
        over = "  ⚠88자 초과" if pg.get("over_limit") else ""
        print(f"   {pg['page']:2}쪽 ({pg.get('chars',0):2}자) {pg['text']}{over}")
    if quiet and len(pages) > 3:
        print(f"   … 그 밖 {len(pages)-3}쪽")

    screen("S-07", "혈흔 전환", "자동")
    para(field("한 문장", _scr(s, "blood_transition").get("copy", {}).get("line")), where="나레이션/한 문장")

    screen("S-08", "현장", "여기서 시작 단서가 손에 들어온다")
    para(field("나레이션", _sn(s, "crime_scene")), where="나레이션/현장")
    ev = _scr(s, "crime_scene").get("evidence_list") or []
    for e in ev:
        print(f"   · [{e.get('label','')}] {e.get('text','')[:64]}")
    if not ev:
        field("증거 목록", None)

    screen("S-09", "피해자 카드")
    for f in (ui.get("hud", {}).get("summary_fields") or []):
        print(f"   {f.get('label','')} · {f.get('value','')}")
    para(field("나레이션", _sn(s, "victim_card")), where="나레이션/피해자")

    screen("S-10", "용의자 소개", f"{len(s['cast'])}장")
    for c_ in s["cast"]:
        print(f"   ── {c_['name']}")
        para(field(f"{c_['name']} 소개", _sn(s, "suspect_intro", c_["id"])), "      ")


# ── 라운드 ────────────────────────────────────────────────────────────
def act_round_open(s, g, rnd, quiet):
    ui = s["ui"]
    toast = {t["id"]: t for t in ui.get("toasts", [])}
    st = g.state()

    screen("S-12", f"{rnd}라운드 시작", st.get("round_focus", ""))
    tb = toast.get("round_start", {})
    print(f"   · {tb.get('title','').replace('{r}', str(rnd))}  ·  {st.get('round_focus','')}")
    para(field(f"{rnd}라운드 나레이션", _sn(s, "round_start", str(rnd))))

    given = getattr(g, "_last_given", None)
    if given:
        print(f"\n   · 라운드 자동 공개 — {', '.join(given)}")

    ev = _sn(s, "event", str(rnd))
    if ev:
        evd = next((e for e in (s.get("events") or []) if e.get("round") == rnd), {})
        tb_ = toast.get("event", {})
        title = ((tb_.get("titles_by_kind") or {}).get(evd.get("kind"))
                 or tb_.get("fallback_title") or tb_.get("title", ""))
        screen("P-12", "이벤트", "건너뛰기 불가")
        print(f"   · {title}")
        para(ev)
        print(f"   효과 — {evd.get('effect','')}")
        for done in (g.apply_event(rnd) or []):
            for sec in done["secrets"]:
                print(f"   > 비밀 하나가 열렸다 — {sec[:60]}…")
            for k in done["clues"]:
                print(f"   > 단서가 손에 들어왔다 — {k}")
            if done["cast"] and not done["secrets"]:
                print(f"   > 압박이 올랐다 — {', '.join(g.cast[c]['name'] for c in done['cast'])}")
        print(f"   · 대질이 열렸다")


def act_map(s, g, quiet, auto):
    """S-13 지도 → 장소를 고른다."""
    ui = s["ui"]
    st = g.state()
    screen("S-13", "지도", f"남은 행동 {st['turns_left']}")
    places = ui["place_screens"]
    for i, ps in enumerate(places, 1):
        done = (ps["place_id"], g.current_round) in g.searched
        own = ps.get("standing_character")
        mark = " (이미 조사함)" if done else ""
        who = f" · {own}" if own else ""
        print(f"   {i}. {ps['title']}{who}{mark}")
    cf = st["confront"]
    print(f"\n   N. 사건수첩({len(st['notebook'])})   "
          f"P. 용의자   C. 대질{'' if cf['unlocked'] else ' 🔒'}   X. 라운드 넘기기")
    return places


def act_place(s, g, ps, quiet, auto):
    """S-14 장소 — 탐색(1턴) · 알리바이(0) · 심문(1턴)."""
    screen("S-14", ps["title"], f"{g.current_round}라운드")
    art = ps.get("art") or {}
    if not quiet:
        print(f"   [그림] {(art.get('prompt_ko') or '⚠ 없음')[:96]}…")
        print(f"   [반드시 보일 것] {', '.join(art.get('must_show') or []) or '⚠ 없음'}")

    r = g.search(ps["place_id"])
    if "error" in r:
        print(f"   ⚠ {r['error']}")
        return
    print(f"\n   ▸ 조사 — {'1턴 씀' if r.get('first_visit') else '이미 본 방(0턴)'}"
          f" · 남은 {r['turns_left']}")
    for a in (r.get("actions") or []):
        hit = " ← 단서" if a.get("finds") in (r.get("found_clues") or []) else ""
        print(f"     · {a.get('label','')}{hit}")
    for cl in (r.get("clues") or []):
        tag = "결정적인 단서" if cl.get("decisive") else "새로운 단서"
        print(f"   · {tag} — {cl['id']}: {(cl.get('surface') or '')[:60]}…")
    if not r.get("found_clues") and r.get("first_visit"):
        print("     · 나오는 것이 없다")

    own = ps.get("standing_cast_id")
    if not own:
        print(f"\n   ({ps.get('talk',{}).get('note','이 곳엔 사람이 없다')})")
        return
    act_talk(s, g, own, quiet, auto)


def act_talk(s, g, cid, quiet, auto, question=None, clue_id=None):
    """S-15 심문 — 첫 대면 알리바이는 예산 0."""
    import stance
    c = g.cast[cid]
    screen("S-15", f"심문 — {c['name']}", ((c.get("persona") or {}).get("voice") or {}).get("form", ""))

    m = g.meet(cid)
    if m.get("first_meet"):
        print(f"   [첫 대면 · 예산 0] “{m.get('alibi') or '⚠ 알리바이 없음'}”")
    else:
        print(f"   (이미 들은 알리바이 — 수첩에 있다)")

    # *손에 쥔 단서 가운데 **이 사람 이야기가 적힌 것**이 있으면 들이댄다.
    #   정답지를 보는 것이 아니라, 단서 본문에 이름·신분·낱말이 있는지만 본다 —
    #   플레이어도 화면에서 똑같이 할 수 있는 판단이다.
    import re as _re
    trig = {x for pp in (c.get("pressure_points") or [])
            for x in (pp.get("trigger") or []) if x}
    marks = {c["name"]} | trig | set(_re.findall(r"[가-힣A-Za-z0-9]{2,}", c.get("public") or ""))
    def _clue(k):
        return next((cl for cl in (s.get("clue_graph") or []) if cl.get("id") == k), None)

    shown = None
    if clue_id and clue_id in g.held_clues:
        shown = _clue(clue_id)
    if not shown:
        # 이 사람 이야기가 적힌 단서 가운데 **아직 안 내민 것**을 고른다.
        #   전에는 늘 첫 번째 것을 골라, 같은 단서를 세 번 네 번 되풀이했다.
        held = [cl for cl in (s.get("clue_graph") or [])
                if cl.get("id") in g.held_clues and cl.get("surface")
                and (cid, cl["id"]) not in PLAYER["shown"]]
        # ① 이 사람 이야기가 적힌 것부터
        shown = next((cl for cl in held
                      if any(m in cl["surface"] for m in marks)), None)
        # ② 없으면 아무 단서나 돌려 가며 내민다 —
        #    단서 임자가 이름으로 드러나지 않는 편이 더 많다. 사람이라면
        #    짚이는 대로 하나씩 대 볼 것이고, 헛짚으면 회피가 돌아올 뿐이다.
        if not shown and held:
            shown = held[len(PLAYER["shown"]) % len(held)]

    # ★단서를 내밀 때는 **문장을 통째로 인용한다** (2026-08-26).
    #   전에는 44자에서 잘라 붙였다. 그래서 비밀이 지목한 낱말이 잘려 나가
    #   정곡이 서지 않았고, 손에 결정타를 쥐고도 한 판 내내 아무도 실토하지 않았다.
    import play_agents as _pa
    F = _pa.forms(s)                       # 이 편의 시대에 맞는 말투
    if shown:
        PLAYER["shown"].add((cid, shown["id"]))
        head = f"「{shown['surface']}」"
        q = f"{head} — {question}" if question else f"{head} — {F['evi']}"
        print(f"   [증거를 들이댄다] {shown['id']}")
    elif question:
        q = question
    else:
        q = F["scene"]
    st = g.interrogate(cid, q, evidence_shown=bool(shown))
    if "error" in st:
        print(f"   ⚠ {st['error']}")
        return
    print(f"\n   Q. {q}")
    line = agent_say(s, g, c, q, st)
    print("   A.")
    para(line, indent="      ", where=f"대사/{c['name']}")
    print(f"      태도 {st['stance']} · 압박 {st['gauge_after']} · 남은 {st['turns_left']}")
    if not field("태도 지시문", st.get("directive")):
        pass
    PLAYER["feed"].append({"cast": c["name"], "clue": (shown or {}).get("id"),
                           "stance": st["stance"],
                           "means": {"ADMIT": "실토했다 — 비밀이 열렸다",
                                     "FLINCH": "흔들렸다 — 정곡은 맞았고 증거가 모자란다",
                                     "BREAK": "무너졌다",
                                     "DEFLECT": "회피했다 — 헛짚었다",
                                     "ANSWER": "사실만 답했다"}.get(st["stance"], "")})
    if st.get("yielded_belonging"):
        print(f"   · 소지품 획득 — {st['yielded_belonging'].get('name')}")
    # 이번 턴에 **새로** 열린 것만 알린다 — 전에는 열린 비밀을 매 턴 다시 읊었다
    seen = PLAYER.setdefault("told", set())
    for sec in sorted(g.disclosed_secrets.get(cid, set())):
        if (cid, sec) in seen:
            continue
        seen.add((cid, sec))
        print(f"   · 비밀이 열렸다 — {sec[:56]}…")


def act_suspects(s, g, quiet):
    """용의자 화면 — 수첩에서 뺀 인물이 여기 있다. 예산 0."""
    screen("S-11b", "용의자", "예산 0 · 하단 내비")
    st = g.state()
    for c in st["cast"]:
        if not c["met"]:
            print(f"     · {c['name']:6} — 아직 만나지 않았습니다. (실루엣)")
            continue
        print(f"     ○ {c['name']:6} {c['public'][:40]}")
        print(f"        알리바이 — {c['alibi']}")
        for sec in c["secrets_open"]:
            print(f"        · {sec[:56]}…")
    print("\n   [이 사람에게 묻는다] 로 심문에 들어간다 · 제 방이 없는 인물도 여기서 만난다")


def act_notebook(s, g, quiet):
    """사건수첩 — **단서만** 모은다. 인물도 수치도 여기 두지 않는다."""
    screen("S-18~19", "사건수첩", "예산 0")
    st = g.state()
    print(f"   [단서] {len(st['notebook'])}장 — 얻는 즉시 자동으로 적힌다")
    for e in st["notebook"]:
        star = "*" if e.get("decisive") else " "
        print(f"    {star}R{e['round']} {e['id']:5} {e['how']:14} {e['surface'][:40]}…")
        if e.get("roles"):
            # 본문에 직책이 나오면 그게 누구인지 한 줄 — [용의자] 화면을 오갈 일을 던다
            print("           " + " · ".join(
                f"{k} = {v if isinstance(v, str) else ' 또는 '.join(v)}"
                for k, v in e["roles"].items()))
    print("\n   [메모] 플레이어가 직접 쓰는 칸 — 추리는 여기에만 쌓인다")
    print("   (인물은 하단 내비 [용의자]에서 본다)")


def act_confront(s, g, quiet, auto, want=None):
    """S-16 대질 — **누구와 누구를 맞대 놓을지 플레이어가 고른다.**
    전에는 준비된 첫 쌍을 멋대로 골랐다. 한 판에 한 번뿐인 선택인데
    고를 기회를 안 주면 그 무게가 사라진다."""
    screen("S-16", "대질", "한 판 1회 · 예산 밖")
    st = g.state()["confront"]
    if not st["unlocked"]:
        print(f"   [잠김] {st['locked_reason']}  (토큰·예산 모두 그대로)")
        return False

    cs = _scr(s, "confront").get("copy", {})
    names = [(c["id"], c["name"], c.get("public", "")) for c in s["cast"]]
    print(f"   {cs.get('hint','')}")
    print(f"\n   {cs.get('pick_a','누구를 앉힐까요?')}")
    for i, (cid, nm, pub) in enumerate(names, 1):
        met = "" if cid in g.met else "   (아직 만나지 않았다)"
        print(f"     {i}. {nm:6} {pub[:34]}{met}")

    if want and want[0] in g.cast and want[1] in g.cast and want[0] != want[1]:
        a, b = want[0], want[1]
        q = want[2] or ""
        print(f"\n   > {g.cast[a]['name']}  /  {g.cast[b]['name']}")
    elif auto:
        # 준비된 쌍 가운데 둘 다 만나 본 쌍을 고른다
        pick = next((p for p in g.cx_pairs if all(x in g.met for x in p)),
                    (list(g.cx_pairs)[0] if g.cx_pairs else None))
        if not pick:
            print("   (맞대 놓을 사람이 없다)")
            return False
        a, b = pick
        print(f"\n   > {g.cast[a]['name']}  /  {g.cast[b]['name']}")
    else:
        def _pick(prompt, exclude=None):
            while True:
                v = ask(prompt)
                if v.isdigit() and 1 <= int(v) <= len(names):
                    cid = names[int(v) - 1][0]
                    if cid == exclude:
                        print("   (같은 사람끼리는 맞대 놓을 수 없다)")
                        continue
                    return cid
                print("   (번호를 넣으세요)")
        a = _pick(cs.get("pick_a", "누구를 앉힐까요?"))
        print(f"\n   {cs.get('pick_b','누구와 맞대 놓을까요?')}")
        for i, (cid, nm, pub) in enumerate(names, 1):
            if cid == a:
                continue
            print(f"     {i}. {nm:6} {pub[:34]}")
        b = _pick(cs.get("pick_b", "누구와 맞대 놓을까요?"), exclude=a)

        print(f"\n   [경고] {cs.get('warn','')}")
        q = ask(cs.get("ask", "무엇을 묻겠습니까?") + "  (엔터=그 시각의 자리)")
        conf = ask(f"{cs.get('submit','맞대 놓는다')}? (y/N)")
        if conf.lower() not in ("y", "yes", "ㅇ"):
            print(f"   ({cs.get('cancel','조금 더 생각한다')})")
            return False

    q = locals().get("q") or ""
    import play_agents as _pa
    r = g.confront(a, b, q or _pa.forms(s)["cx"])
    if "error" in r:
        print(f"   [{r['error']}]")
        return False

    cx = r.get("cross_exam") or {}
    print(f"\n   {g.cast[a]['name']}  ↔  {g.cast[b]['name']}"
          + (f"   ({cx.get('angle')}을 묻는다)" if cx.get("angle") else ""))
    if cx.get("opening"):
        print(f"   {cx['opening']}")
    for l in (cx.get("exchange") or []):
        print(f"     [{l['beat']}] {l['name']}: {l['line']}")
    note = ((cx.get("reveals") or {}).get("note"))
    print(f"\n   > 드러난 것 — {note or '(없음)'}")
    if cx.get("gained_clue"):
        gc = cx["gained_clue"]
        print(f"   > 새 단서 — {gc['id']}: {gc['surface'][:60]}…")
    if not r.get("is_curated_pair"):
        print("   (대본이 없는 짝 — 두 사람의 알리바이를 맞대 놓았다)")
    return True


def act_end(s, g, quiet):
    ui = s["ui"]
    import collections
    screen("S-21", "범인 지목", "되돌릴 수 없음")
    para(field("지목 직전 나레이션", _sn(s, "accuse")), where="나레이션/지목 직전 나레이션")
    ch = s.get("choices") or {}
    print(f"   범인 보기 {len(ch.get('culprit') or [])} · 흉기 보기 {len(ch.get('weapon') or [])} "
          f"· 동기 {s.get('answer_format',{}).get('motive','?')}")

    tally = collections.Counter()
    for cl in (s.get("clue_graph") or []):
        if cl.get("id") in g.held_clues and cl.get("points_to"):
            tally[cl["points_to"]] += 3 if cl.get("weight") == "decisive" else 1
    culprit = next((c["id"] for c in s["cast"] if c.get("is_culprit")), None)
    named = tally.most_common(1)[0][0] if tally else list(g.cast)[0]
    ok = named == culprit
    print(f"   ▸ 지목 — {g.cast[named]['name']}  ({'적중' if ok else '빗나감'})")

    screen("S-22", "진상", f"{len((ui.get('reveal_sequence') or {}).get('beats') or [])}박")
    for bt in (ui.get("reveal_sequence") or {}).get("beats", []):
        print(f"   [{bt['label']}] {bt['text'][:70]}…")

    screen("S-23", "범행 재연", f"{len((ui.get('murder_reenactment') or {}).get('cuts') or [])}컷 · 건너뛰기 불가")
    for ct in (ui.get("murder_reenactment") or {}).get("cuts", []):
        print(f"   {ct['no']}. {ct['label']} — {ct['text'][:56]}…")

    n_sec = sum(len(v) for v in g.disclosed_secrets.values())
    sc = s.get("scoring") or {}
    pts = min((sc.get("culprit_correct", 5) if ok else 0)
              + n_sec * sc.get("secret_revealed_each", 1), sc.get("max", 10))
    grade = ""
    for gr in sorted(((s.get("ending") or {}).get("grades") or []), key=lambda x: x.get("min", 0)):
        if pts >= gr.get("min", 0):
            grade = gr.get("name", "")
    # *엔딩 서사가 **결과에 따라 갈린다** (2026-08-25, 실물 대본 벤치마킹)
    br = ((s.get("ending") or {}).get("branches") or {})
    leg = br.get("caught" if ok else "escaped") or {}
    screen("S-24", "엔딩", f"「{leg.get('label','')}」 · 「{grade}」 {pts}/{sc.get('max',10)}점")
    for b in (leg.get("beats") or []):
        para(b)
    print(f"\n   {leg.get('result_line','')}")

    # 못 연 비밀은 마지막에 본인이 털어놓는다
    ro = ((s.get("ending") or {}).get("reveal_order") or {})
    if ro.get("order"):
        print(f"\n   ── 비밀 발표")
        for o in ro["order"]:
            opened = bool(g.disclosed_secrets.get(o["cast_id"]))
            print(f"     {o['if_opened'] if opened else o['if_closed']}")
            if not opened:
                for x in o.get("secrets", []):
                    para(f"「{x}」", "        ")

    # 그날 밤을 시각 순으로 되짚는다 — novel에만 있던 대목
    rp = ((s.get("ending") or {}).get("replay") or {})
    if rp.get("lines"):
        print(f"\n   ── 그날 밤 ({len(rp['lines'])}줄)")
        for l in rp["lines"]:
            mark = (" >" if l.get("hidden_until_end") else
                    " *" if l.get("is_murder") else "  ")
            print(f"    {mark}{l['line'][:66]}")
        print("      (> 로 표시된 줄은 아무도 못 본 대목 — 재연에서 처음 열린다)")

    print(f"\n   비밀 {n_sec}개 · 단서 {len(g.held_clues)}개")
    para(field(f"엔딩 나레이션({grade})", _sn(s, "ending", grade)))
    return pts, grade, ok


# ── 한 판 ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", nargs="?", default="91_dsl_demo.json")
    ap.add_argument("--auto", action="store_true", help="알아서 끝까지")
    ap.add_argument("--quiet", action="store_true", help="긴 대목은 줄여서")
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--llm", action="store_true",
                    help="용의자 대사를 실제 LLM이 만든다 (.apikey 필요)")
    ap.add_argument("--agent", action="store_true",
                    help="판정자까지 LLM이 맡아 **끝까지 혼자 논다** (--llm 포함)")
    ap.add_argument("--model", default="gpt-4o-mini")
    a = ap.parse_args()
    if a.agent:
        a.llm = True
        a.auto = True
    if a.llm:
        if not agent_open(model=a.model):
            print("  .apikey 가 없어 대사는 자리표시자로 나옵니다.")
        elif a.agent:
            PLAYER["llm"] = AGENT["llm"]

    path = a.scenario if "/" in a.scenario else f"scenarios/{a.scenario}"
    if not glob.glob(path):
        print(f"그런 시나리오가 없습니다: {path}")
        sys.exit(1)
    s = json.load(open(path, encoding="utf-8"))

    from game_engine_v2 import GameSession
    g = GameSession(s)
    R = a.rounds or g.max_rounds

    print()
    rule("═")
    print(f"  「{s['meta']['title']}」  {(s.get('stars') or {}).get('stars','')}"
          f"  ·  {R}라운드 · 행동 예산 {s['config']['turns_per_round']}/R")
    print(f"  화면 순서대로 걸어 봅니다. 값은 전부 스키마와 엔진에서만 꺼냅니다.")
    rule("═")

    act_intro(s, a.quiet)

    used_confront = False
    asked = {}
    for rnd in range(1, R + 1):
        act_round_open(s, g, rnd, a.quiet)
        while True:
            places = act_map(s, g, a.quiet, a.auto)
            st = g.state()
            if st["turns_left"] < 1:
                print("\n   (이 라운드에 남은 행동이 없습니다)")
                break
            want_q = want_pair = want_cid = want_clue = None
            if a.auto:
                # *방만 뒤지면 비밀이 안 열린다 — 절반은 사람을 판다.
                #   예산의 앞 절반은 탐색, 뒤 절반은 아직 안 만난 사람에게 쓴다.
                def _rule_of_thumb():
                    budget = s["config"]["turns_per_round"]
                    spent = budget - st["turns_left"]
                    if st["confront"]["unlocked"] and not used_confront:
                        return {"action": "confront"}
                    if spent < budget // 2:
                        nxt = next((ps["place_id"] for ps in places
                                    if (ps["place_id"], g.current_round) not in g.searched), None)
                        if nxt:
                            return {"action": "search", "place": nxt}
                    return {"action": "ask"}

                d = player_decide(s, g, _rule_of_thumb)
                act = str(d.get("action", "")).lower()
                if d.get("why") and not a.quiet:
                    print(f"   〔판정자〕 {str(d['why'])[:60]}")
                if act == "search":
                    idx = next((i for i, ps in enumerate(places, 1)
                                if ps["place_id"] == d.get("place")), None)
                    pick = str(idx) if idx else "T"
                elif act == "confront" and st["confront"]["unlocked"] and not used_confront:
                    pick = "C"
                    want_pair = (d.get("cast"), d.get("with"), d.get("question"))
                elif act == "next":
                    pick = "X"
                else:
                    pick = "T"
                    want_q = d.get("question")
                    want_cid = d.get("cast") if d.get("cast") in g.cast else None
                    want_clue = d.get("clue") if d.get("clue") in g.held_clues else None
            else:
                pick = ask("어디로? (번호 장소 / T 심문 / P 용의자 / N 수첩 / C 대질 / X 다음 라운드)")

            if pick.upper() == "N":
                act_notebook(s, g, a.quiet)
            elif pick.upper() == "P":
                act_suspects(s, g, a.quiet)
            elif pick.upper() == "C":
                if act_confront(s, g, a.quiet, a.auto, want=want_pair):
                    used_confront = True
            elif pick.upper() == "X":
                break
            elif pick.upper() == "T":
                # 판정자가 짚은 사람. 못 짚었으면 아직 덜 만난 사람부터 판다.
                cid = (want_cid
                       or min(g.cast, key=lambda x: (x in g.met, asked.get(x, 0))))
                asked[cid] = asked.get(cid, 0) + 1
                act_talk(s, g, cid, a.quiet, a.auto, question=want_q, clue_id=want_clue)
            elif pick.isdigit() and 1 <= int(pick) <= len(places):
                act_place(s, g, places[int(pick) - 1], a.quiet, a.auto)
            else:
                print("   (번호나 N/C/X를 넣으세요)")

        screen("S-20", f"{rnd}라운드 종료")
        para(field(f"{rnd}라운드 종료 나레이션", _sn(s, "round_end", str(rnd))),
             where=f"나레이션/{rnd}R 종료")
        if rnd < R:
            nx = g.next_round()
            g._last_given = nx.get("given")

    act_notebook(s, g, a.quiet)
    pts, grade, ok = act_end(s, g, a.quiet)

    audit_report(s, g)
    print(f"\n  결과 「{grade}」 {pts}점 · 범인 {'적중' if ok else '빗나감'}")
    rule("═")


if __name__ == "__main__":
    main()
