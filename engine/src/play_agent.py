# -*- coding: utf-8 -*-
"""
play_agent.py — **사람이 직접 심문해 본다.**

왜 필요한가:
  stress_local.py의 판정기는 '규칙 위반'만 센다. 배역을 벗었는가, 한국어를 썼는가,
  형식을 지켰는가. 그런데 우리가 정작 알고 싶은 건 그게 아니다.
  **말이 사람 같은가. 심문하는 맛이 있는가. 계속 파고들고 싶어지는가.**
  이건 자동으로 못 잰다. 사람이 앉아서 해봐야 안다.

두 가지 모드
  ① 그냥 심문      python play_agent.py ../scenarios/23_*.json
  ② ★블라인드 비교  python play_agent.py ../scenarios/23_*.json --blind "모델A,모델B"

  ②를 권한다. 사람은 먼저 본 쪽에 후해지고, 어느 회사 모델인지 알면 그쪽으로 기운다.
  블라인드에서는 두 모델이 같은 질문에 답하고 순서를 섞어 보여준다.
  누가 누군지는 끝나야 밝혀진다. 그래야 '자연스럽다'는 판단이 믿을 만해진다.

명령어 (대화 중 아무 때나)
  /인물          용의자 목록과 현재 상대
  /바꿔 C3       다른 용의자로 교체
  /조사 P2       장소를 뒤져 단서를 얻는다 (얻어야 들이댈 수 있다)
  /가진것        지금까지 확보한 단서
  /증거 K5       확보한 단서를 들이댄다 (없으면 못 쓴다)
  /상태          압박 게이지와 지금까지 확보한 것
  /단서          지금 라운드까지 공개된 단서
  /되감기        마지막 한 턴 취소
  /끝            종료하고 결과 저장

실행 (GPU 노드에서)
  srun --partition=partition1 --gres=gpu:1 --cpus-per-task=4 --mem=48G --time=02:00:00 --pty bash
  export HOME=/mnt/data1/dsl04 && cd $HOME/mm2/tools
  /anaconda/anaconda3/bin/python play_agent.py "../scenarios/23_*.json" --blind "skt/A.X-4.0-Light,kakaocorp/kanana-1.5-8b-instruct-2505"
"""
import os, sys, json, glob, time, random, argparse

# 뒤져야 나오는 채널 — 장소·기록·물증. 현장 검안과 공개 증언만 공짜로 준다.
#   채널을 쪼개면서 'location'만 보던 코드가 기록·물증을 공짜로 줘 버렸다.
FREE_AT_START = ("crime_scene",)   # 공짜로 주는 채널 — 검안뿐
SEARCHABLE = ("location", "record", "physical", "spine")


HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)

# ★ 계산 노드의 로케일이 UTF-8이 아니면 한글 입력에서 UnicodeDecodeError가 난다.
#   PYTHONIOENCODING을 안 걸어도 되게 여기서 직접 표준입출력을 다시 연다.
for _s in ("stdin", "stdout", "stderr"):
    try:
        getattr(sys, _s).reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

C = {"dim":"\033[2m","b":"\033[1m","r":"\033[31m","g":"\033[32m",
     "y":"\033[33m","c":"\033[36m","x":"\033[0m"}
def col(s, k): return f"{C.get(k,'')}{s}{C['x']}"
def log(*a): print(*a, flush=True)


def load_llm(model_id, api=False, max_new=320, temp=0.75):
    """model_id가 "api"면 API를 쓴다 → --blind "skt/A.X-4.0-Light,api" 로
    로컬과 GPT를 한 세션에서 눈 가리고 비교할 수 있다."""
    if api or model_id == "api":
        from llm_api import ApiLLM
        return ApiLLM(max_new_tokens=max_new, temperature=temp)
    from stress_local import LocalLLM
    return LocalLLM(model_id, max_new_tokens=max_new, temperature=temp)


class Session:
    """한 용의자와의 대화 상태."""
    def __init__(self, s, c, acting=True):
        from pressure import Gauge
        self.s, self.c, self.acting = s, c, acting
        self.gauge = Gauge(s, c["id"])
        self.hist = None            # 시스템 프롬프트는 매 턴 재조립
        self.turns = []
        self.secret_open = False
        self.disclosed = set()        # 이미 실토한 비밀 — 두 번 털지 않는다
        self.denied = 0               # 이 인물이 지금까지 몇 번 부인했나
        self.last_stance = None
        self.trig = [w for pp in (c.get("pressure_points") or [])
                     for w in (pp.get("trigger") or [])]

    def system(self, question="", evidence=False, held=None):
        """카드 + [출력 형식] + ★이번 턴의 태도 하나★."""
        from stress_agent import suspect_system
        from turn_schema import format_block
        from stance import decide, directive
        base = suspect_system(self.s, self.c)
        st = self.gauge.state()
        stance = decide(self.s, self.c, question, st, evidence, self.disclosed,
                        denied_before=(self.denied > 0), held_clues=held)
        if stance["stance"] == "DEFLECT":
            self.denied += 1
        self.last_stance = stance
        if stance["stance"] == "ADMIT" and (stance.get("secret") or {}).get("text"):
            self.disclosed.add(stance["secret"]["text"])
        pdm = {p["id"]: p for p in self.s["map"]["places"]}
        mine = [pdm[self.c["timeline"][sl]]["name"] for sl in self.s["time_slots"]]
        d = directive(stance, self.c, mine)
        if not self.acting:
            return base + "\n\n" + d
        axis = st["checklist"]["alibi_break"] or st["checklist"]["decisive"]
        long_turn = stance["stance"] in ("ADMIT", "BREAK")
        return (base + "\n\n" + format_block(self.c, st["value"], allow_guilt_tint=axis,
                                             forced_disclosure=long_turn)
                + "\n\n" + d)

    def messages(self, q, evidence=False, held=None):
        msgs = [{"role": "system", "content": self.system(q, evidence, held)}]
        for t in self.turns:
            msgs.append({"role": "user", "content": t["q"]})
            msgs.append({"role": "assistant", "content": t["a"]})
        msgs.append({"role": "user", "content": ("[결정적 증거 제시] " if evidence else "") + q})
        return msgs


def render(ans, acting):
    """모델 답을 사람이 읽기 좋게."""
    if not acting: return "   " + ans.replace("\n", "\n   ")
    from turn_schema import parse_turn
    p = parse_turn(ans)
    if p["errors"]: return "   " + ans.replace("\n", "\n   ")
    head = f"({p['emotion']} {p['intensity']}) {p['action']}"
    return f"   {col(head,'dim')}\n   {col('「'+(p['line'] or '')+'」','c')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--model", default=os.environ.get("MM_MODEL", "skt/A.X-4.0-Light"))
    ap.add_argument("--blind", default="", help="쉼표로 두 모델 → 블라인드 비교")
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--mock", action="store_true",
                    help="모델 없이 진행 구조만 시험한다(라운드·층·이벤트·채점)")
    ap.add_argument("--no-guard", action="store_true")
    ap.add_argument("--no-acting", action="store_true", help="3줄 연기 규격 끄기")
    ap.add_argument("--temp", type=float, default=0.75)
    ap.add_argument("--max-new", type=int, default=320)  # 답이 길어졌다
    ap.add_argument("--out", default="out_play")
    a = ap.parse_args()

    paths = sorted(glob.glob(a.path))
    if not paths: log(f"[오류] 시나리오 없음: {a.path}"); sys.exit(1)
    s = json.load(open(paths[0], encoding="utf-8"))
    acting = not a.no_acting
    blind = [m.strip() for m in a.blind.split(",") if m.strip()]

    log(col(f"\n═══ {s['meta']['title']} ({s['meta']['origin']}) ═══", "b"))
    det = (s.get("detective") or {})
    log(f"당신은 {col(det.get('title','수사관'),'y')}이다. 용의자 {len(s['cast'])}명.")
    log(col(s["intro"]["twist"][:160], "dim"))

    # 모델 적재
    llms = {}
    if a.mock:
        # 모델을 부르지 않고 놀이판만 돌린다. 라운드·층·이벤트·채점을 손으로 확인할 때 쓴다.
        class _Mock:
            tok = None
            def chat(self, msgs, **kw):
                return "[감정] 평정 1\n[행동] 가만히 선다.\n[대사] (모의 응답) 그 일은 내가 아는 바가 없다."
            def report(self): return "[모의] 모델을 부르지 않았습니다"
        llms = {"mock": _Mock()}
    if a.mock:
        pass                       # 모의 판에서는 모델을 적재하지 않는다
    elif blind:
        log(col(f"\n[블라인드 비교] 두 모델이 같은 질문에 답합니다. 순서는 매번 섞입니다.", "y"))
        for m in blind:
            log(f"  적재 중… ({len(llms)+1}/{len(blind)})")
            llms[m] = load_llm(m, max_new=a.max_new, temp=a.temp)
    else:
        llms[a.model if not a.api else "api"] = load_llm(a.model, a.api, a.max_new, a.temp)
    keys = list(llms)

    guards = {}
    if not a.no_guard:
        from guard import Guard
        for m, llm in llms.items():
            _api = (m == "api")
            guards[m] = None   # 용의자마다 새로 만든다(비밀이 인물별이라)

    cast = {c["id"]: c for c in s["cast"]}
    cur = s["cast"][0]["id"]
    sess = {}
    def S(cid):
        if cid not in sess: sess[cid] = Session(s, cast[cid], acting)
        return sess[cid]

    def make_guard(m, c):
        if a.no_guard: return None
        from guard import Guard
        _api = (m == "api")
        return Guard(llms[m].tok, s, c, model_key=m,
                     use_suppress=not _api, use_bad_words=not _api)

    votes = {m: 0 for m in llms}; ties = 0
    transcript = []

    # ★ 확보한 단서. 1라운드 공개분(현장 검안·공개 증언)은 처음부터 손에 있다.
    # ★ 처음부터 쥐고 시작하는 것은 **현장 검안과 공개 증언**뿐이다.
    #   방에서 나오는 것(location)까지 미리 주면 1라운드에 뒤질 이유가 사라진다.
    held = {cl["id"] for cl in s["clue_graph"]
            if (cl.get("reveal_round") or 9) <= 1
            and cl.get("channel") in FREE_AT_START}
    place_name = {p["id"]: p["name"] for p in s["map"]["places"]}
    by_place = {}
    for cl in s["clue_graph"]:
        loc = cl.get("location")
        if not loc:
            # 현장·물증 단서는 location이 없다. 본문에 적힌 장소 이름으로 붙인다.
            # (없으면 사망 현장에 둔다 — 검안·현장 관찰은 거기서 나오는 것이 맞다)
            for pid, pname in place_name.items():
                key = pname.split("(")[0]
                if key and key in (cl.get("surface","") + cl.get("implies","")):
                    loc = pid; break
            loc = loc or s["death"]["place"]
        by_place.setdefault(loc, []).append(cl)
    log(col(f"  시작 단서 {len(held)}개 확보 (현장 검안·공개 증언)", "dim"))

    log(col("\n명령어: /인물 /바꿔 C3 /조사 P2 /가진것 /증거 K5 /상태 /단서 "
            "/다음 /라운드 /지목 /되감기 /끝", "dim"))
    log(col("  ※ 단서는 **찾아야 쓸 수 있다.** 안 찾고 말로만 찔러도 인물은 인정하지 않는다.\n", "dim"))
    # ── 라운드 ────────────────────────────────────────────────────
    #   시나리오는 라운드·장소 3층·중반 이벤트·엔딩을 전부 적어 두었는데
    #   여태 놀이판이 그중 아무것도 쓰지 않았다. 여기서 잇는다.
    RN = s.get("config", {}).get("rounds", 3)
    TPR = s.get("config", {}).get("turns_per_round", 12)
    rnd = [1, 0]                      # [지금 라운드, 이번 라운드에 쓴 턴]
    fired = set()
    layers = (s.get("place_layers") or {}).get("layers") or {}

    def _layer(pid, r):
        v = layers.get(pid)
        if isinstance(v, dict):
            return v.get(str(r)) or v.get(r)
        if isinstance(v, list) and len(v) >= r:
            return v[r - 1]
        return None

    def _events(r):
        for e in (s.get("events") or []):
            if e.get("round") == r and id(e) not in fired:
                fired.add(id(e))
                nm = e.get("name") or e.get("title") or "이변"
                log(col(f"\n  ┏━━ ★이벤트 — {nm}", "y"))
                for ln in (e.get("text") or "").split(". "):
                    if ln.strip():
                        log(col(f"  ┃ {ln.strip()}", "y"))
                log(col(f"  ┗━ {e.get('effect','')}", "dim"))

    def _round_head():
        ph = next((x for x in (s.get("phases") or [])
                   if str(rnd[0]) in str(x.get("name", ""))), None)
        log(col(f"\n━━━━━ {rnd[0]}라운드 / {RN}"
                + (f" — {ph.get('name')}" if ph else "") + " ━━━━━", "b"))
        log(col(f"  이 라운드에 쓸 수 있는 심문 {TPR}턴. 장소를 뒤지면 그 층의 것이 보인다.", "dim"))
        _events(rnd[0])

    def _advance():
        if rnd[0] >= RN:
            log(col("  마지막 라운드요. 이제 /지목 으로 답을 내시오.", "y")); return
        rnd[0] += 1; rnd[1] = 0
        _round_head()

    def _verdict():
        """지목 → 채점 → 엔딩 낭독. 여태 시나리오에만 적혀 있던 마무리를 실제로 쓴다."""
        sc = s.get("scoring") or {}
        cul = next((c for c in cast.values() if c.get("is_culprit")), {})
        log(col("\n━━━━━ 지목 ━━━━━", "b"))
        for c in s["cast"]:
            log(f"  {c['id']} {c['name']} ({c.get('public','')})")
        try:
            pick = input(col("  범인은 누구요? (C1~C5) > ", "b")).strip().upper()
        except (EOFError, KeyboardInterrupt):
            pick = ""
        pts = 0
        okc = (pick == cul.get("id"))
        if okc:
            pts += sc.get("culprit_correct", 5)
        opened = sum(len(ss.disclosed) for ss in sess.values())   # 실제로 연 비밀 수
        pts += sc.get("secret_revealed_each", 1) * opened
        mx = sc.get("max", 10)
        log(col(f"\n  범인 지목: {'맞았소' if okc else '틀렸소 — ' + cul.get('name','')}", 
                "g" if okc else "r"))
        log(f"  밝혀낸 비밀 {opened}개")
        log(col(f"  점수 {pts} / {mx}", "y"))
        en = s.get("ending") or {}
        gr = sorted((en.get("grades") or []), key=lambda g: g.get("min", 0))
        grade = None
        for g in gr:
            if pts >= g.get("min", 0):
                grade = g
        if grade:
            # 등급 이름은 name으로도 title로도 적혀 있다
            gname = grade.get("name") or grade.get("title") or ""
            log(col(f"\n  ── 엔딩 · {gname} ──", "b"))
            log("  " + (grade.get("text") or ""))
        if en.get("truth_reveal"):
            log(col("\n  ── 진상 ──", "dim"))
            log("  " + en["truth_reveal"][:600])
        for e in (s.get("timeline_events") or []):
            if "★" in (e.get("text") or ""):
                log(col(f"  그 밤 {e.get('time','')} — {e['text'].replace('★','')}", "dim"))

    _round_head()
    log(col(f"── 지금 상대: {cast[cur]['name']} ({cast[cur].get('public','')})", "g"))

    def _pending():
        """붙여넣기로 입력이 밀려 있는가."""
        try:
            import select
            return bool(select.select([sys.stdin], [], [], 0)[0])
        except Exception:
            return False

    while True:
        try:
            paste = _pending()          # 읽기 전에 봐야 이번 줄이 붙여넣기인지 안다
            q = input(col("\n> ", "b")).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q: continue
        # ★ 여러 줄을 한꺼번에 붙여넣으면 화면의 프롬프트 위치와 실제로 읽힌 줄이 어긋난다.
        #   실제 플레이에서 "/조사 P6"을 쳤는데 앞서 밀려 있던 줄이 대신 읽혀,
        #   금단의 방을 못 열고 판이 그대로 끝났다. 무엇이 읽혔는지 그때그때 보여 준다.
        if paste or _pending():
            log(col(f"  ⟨읽은 줄⟩ {q}", "dim"))

        if q in ("/끝", "/quit", "/q"): break
        if q == "/인물":
            for c in s["cast"]:
                mark = "◀" if c["id"] == cur else " "
                log(f"  {c['id']} {c['name']:8} {c.get('public','')} {mark}")
            continue
        if q.startswith("/바꿔"):
            t = q.split()[-1].upper()
            if t in cast:
                cur = t; log(col(f"── 지금 상대: {cast[cur]['name']}", "g"))
            else: log("  그런 인물이 없소.")
            continue
        if q == "/상태":
            st = S(cur).gauge.state(); log("  " + S(cur).gauge.hud())
            continue
        if q == "/단서":
            for cl in s["clue_graph"]:
                mark = "✔" if cl["id"] in held else " "
                log(f"  {mark} [{cl['id']}] {cl.get('surface','')[:76]}")
            continue
        if q == "/가진것":
            if not held: log("  아직 아무것도 없소."); continue
            for cid in sorted(held):
                cl = next((x for x in s["clue_graph"] if x["id"] == cid), {})
                log(f"  [{cid}] {cl.get('surface','')[:76]}")
            continue
        if q.startswith("/조사"):
            parts = q.split()
            if len(parts) < 2:
                log("  어디를 뒤지겠소? " + " / ".join(f"{p['id']}={p['name']}" for p in s["map"]["places"]))
                continue
            pid = parts[1].upper()
            if pid not in place_name:
                log("  그런 곳은 없소."); continue
            got = [cl for cl in by_place.get(pid, [])
                   if cl["id"] not in held and (cl.get("reveal_round") or 1) <= rnd[0]]
            _pn = place_name[pid]
            _j = "을" if (ord(_pn[-1]) - 0xAC00) % 28 and "가" <= _pn[-1] <= "힣" else "를"
            log(col(f"  ── {_pn}{_j} 뒤진다", "g"))
            lay = _layer(pid, rnd[0])
            if lay:
                log(col(f"     [{rnd[0]}층] {lay}", "dim"))
            else:
                for f in next((p.get("features") or [] for p in s["map"]["places"]
                               if p["id"] == pid), []):
                    log(col(f"     · {f}", "dim"))
            if got:
                for cl in got[:3]:
                    held.add(cl["id"])
                    log(col(f"     ★ 단서 획득 [{cl['id']}] {cl.get('surface','')[:70]}", "y"))
            else:
                later = [cl for cl in by_place.get(pid, [])
                         if cl["id"] not in held and (cl.get("reveal_round") or 1) > rnd[0]]
                log(col("     지금은 더 나올 것이 없소."
                        + ("  (뒤에 다시 와 보시오)" if later else ""), "dim"))
            continue
        if q in ("/다음", "/다음라운드"):
            _advance(); continue
        if q == "/라운드":
            log(f"  {rnd[0]}라운드 / {RN} · 이번 라운드 심문 {rnd[1]}/{TPR}턴")
            continue
        if q == "/지목":
            _verdict(); break
        if q == "/되감기":
            if S(cur).turns: S(cur).turns.pop(); log("  한 턴 되감았소.")
            continue

        evidence = q.startswith("/증거")
        if evidence:
            parts = q.split()
            if len(parts) >= 2:
                cid = parts[1].upper()
                if cid not in held:
                    log(col(f"  [{cid}]는 아직 손에 없소. /조사 로 먼저 찾으시오.", "r"))
                    continue
                cl = next((x for x in s["clue_graph"] if x["id"] == cid), {})
            else:
                dec = next((x for x in s["clue_graph"] if x.get("decisive")), {})
                if dec.get("id") not in held:
                    log(col("  결정적 증거를 아직 못 찾았소. /조사 로 뒤져 보시오.", "r"))
                    continue
                cl = dec
            q = cl.get("surface", "") + " 이래도 아니라 하겠는가?"
            log(col(f"  [증거 제시 {cl.get('id')}] {q[:110]}", "r"))

        sess_c = S(cur)
        order = list(llms)
        if blind: random.shuffle(order)

        answers = {}
        for m in order:
            g = make_guard(m, cast[cur])
            msgs = sess_c.messages(q, evidence, held)
            try:
                _stn = sess_c.last_stance or {}
                _admit = ((_stn.get("secret") or {}).get("confession_line")
                          if _stn.get("stance") == "ADMIT" else None)
                _req = None
                if _admit:
                    from guard import Checker as _Ck
                    _req = _Ck._keywords((_stn.get("secret") or {}).get("text",""))
                if g:
                    ans, info = g.generate(llms[m], msgs, acting=acting,
                                           secret_unlocked=True,
                                           require_disclosure=_req,
                                           admit_line=_admit)
                else:
                    ans, info = llms[m].chat(msgs), {}
            except Exception as e:
                ans, info = f"[생성 실패: {e}]", {}
            answers[m] = (ans, info)

        if any(w and w in q for w in sess_c.trig) or evidence:
            sess_c.secret_open = True

        if blind:
            labels = ["A", "B", "C"][:len(order)]
            for lab, m in zip(labels, order):
                _info = answers[m][1]
                _mark = col("  ⚠ 모델이 세 번 실패해 대체된 답", "r") if _info.get("fallback") else ""
                log(f"\n {col(lab,'b')}){_mark}")
                log(render(answers[m][0], acting))
            pick = input(col("\n  더 자연스러운 쪽? (A/B, 비슷하면 엔터) ", "y")).strip().upper()
            chosen = None
            if pick in labels:
                chosen = order[labels.index(pick)]; votes[chosen] += 1
            else:
                ties += 1
            transcript.append({"q": q, "answers": {m: answers[m][0] for m in order},
                               "order": order, "pick": chosen, "suspect": cur})
            # 대화 이력에는 고른 쪽(없으면 첫 번째)을 남긴다
            keep = chosen or order[0]
            sess_c.turns.append({"q": q, "a": answers[keep][0]})
            sess_c.gauge.apply(q, answers[keep][0], evidence_shown=evidence)
        else:
            m = order[0]; ans, info = answers[m]
            log("")
            log(render(ans, acting))
            if info.get("fallback"):
                _how = "실토 뼈대로 대체" if info.get("used_skeleton") else "안전 문구로 대체"
                log(col(f"   ({_how} — {info.get('caught')})", "r"))
            sess_c.turns.append({"q": q, "a": ans})
            sess_c.gauge.apply(q, ans, evidence_shown=evidence)
            transcript.append({"q": q, "a": ans, "suspect": cur, "model": m})
        _st = sess_c.last_stance or {}
        if _st: log(col(f"  [태도: {_st.get('stance')}] {_st.get('why','')}", "dim"))
        log(col("  " + sess_c.gauge.hud(), "dim"))

    # ── 결과 ─────────────────────────────────────────────
    os.makedirs(a.out, exist_ok=True)
    stamp = str(int(time.time()))
    fp = os.path.join(a.out, f"play_{stamp}.json")
    json.dump({"scenario": os.path.basename(paths[0]), "blind": blind,
               "votes": votes, "ties": ties, "transcript": transcript},
              open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    log(col("\n\n═══ 결과 ═══", "b"))
    if blind:
        tot = sum(votes.values()) + ties
        log(f"  판정 {tot}회 (무승부 {ties})")
        for m, v in sorted(votes.items(), key=lambda x: -x[1]):
            bar = "█" * int(v * 20 / max(1, max(votes.values())))
            log(f"  {m:46} {v:3}표 {bar}")
        if tot >= 10:
            best = max(votes, key=votes.get)
            share = votes[best] * 100 / max(1, tot)
            log(f"\n  → {col(best,'g')} 우세 ({share:.0f}%)")
            if share < 55:
                log("    다만 격차가 작다. 둘 중 아무거나 써도 체감 차이는 크지 않다는 뜻이다.")
        else:
            log(col("\n  판정 횟수가 적다. 10턴 이상은 해봐야 신뢰할 만하다.", "y"))
    else:
        log(f"  {len(transcript)}턴 대화")
    log(f"  저장: {fp}")
    log(col("\n  이 파일을 채팅에 붙여넣으면 어디가 부자연스러웠는지 같이 봅니다.", "dim"))


if __name__ == "__main__":
    main()
