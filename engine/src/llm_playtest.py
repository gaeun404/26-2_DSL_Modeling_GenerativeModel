# -*- coding: utf-8 -*-
"""
llm_playtest.py — **실제 LLM으로 한 판을 끝까지 돌린다.**

판단(누가 언제 실토하는지)은 stance+pressure가 내리므로 키 없이도 관측된다.
키가 필요한 것은 **문장**이다. 그리고 문장만 보면 판이 어떻게 굴러가는지 안 보이므로,
**게임 진행 전체**를 함께 찍는다 — 나레이션·라운드 배너·단서 공개·비밀 공개·이벤트·대질·진상·엔딩.

■ 라운드당 행동 예산 8을 **다 쓴다** (탐색 + 심문이 같은 주머니)
■ 검사 항목
    ① 답변 다양성   인물끼리 겹치는 정도       20% 아래
    ② 되묻기        물음표                    0개
    ③ 말투 고정     종결어미가 말체와 일치
    ④ 자기 반복     같은 인물이 라운드마다 겹침  30% 아래
    ⑤ 설정서 낭독   12자 이상 연속 복붙        0건
    ⑥ 대질          주고받는 대본 재생

사용:
    python3 llm_playtest.py                      # 91편 한 판 (키는 .apikey 자동)
    python3 llm_playtest.py 38_cinderella.json
    python3 llm_playtest.py --rounds 1           # 1라운드만 (비용 절약)
    python3 llm_playtest.py --quiet              # 요약만
"""
import os, sys, json, re, glob, argparse, collections

# ★판본을 **결과 파일에 찍는다** (2026-08-25).
#   같은 이름의 폴더가 여럿 쌓이면서 옛 판으로 돌린 결과를 새것으로 착각하는 일이
#   세 번 있었다. 이제 화면과 json 양쪽에 판본이 남으므로 헷갈릴 일이 없다.
VERSION = "v9 · 2026-08-25 (장소당 1턴 · 비밀 열림 개선)"

BAR = "─" * 76


# ── 검사기 ────────────────────────────────────────────────────────────
def check_question_mark(text):
    n = text.count("?") + text.count("？")
    return n, [s.strip() for s in re.split(r"(?<=[.!?？])\s+", text) if "?" in s or "？" in s]


ENDING_PATTERNS = {
    "해요체": r"(요|죠|예요|어요|네요)[.!…]*$", "합쇼체": r"(니다|니까)[.!…]*$",
    "합니다체": r"(니다|니까)[.!…]*$", "격식체": r"(니다|니까)[.!…]*$",
    "건조체": r"(니다|죠)[.!…]*$", "반존대": r"(요|지|거든|잖아요|는데)[.!…]*$",
    "설명체": r"(더라고요|네요|던데요|요)[.!…]*$", "다정체": r"(요|죠|예요|어요)[.!…]*$",
    "공손체": r"(답니다|지요|니다|소|오)[.!…]*$", "완곡체": r"(군요|네요|더군요|는군요|군|네)[.!…]*$",
    "하오체": r"(하오|소|구려|오)[.!…]*$", "정중체": r"(하오|오|소|소이다)[.!…]*$",
    "하게체": r"(네|하게|인가|겠나|일세)[.!…]*$", "노숙체": r"(네|로군|는가|일세|구먼|지)[.!…]*$",
    "노년체": r"(네|지|구먼|는가)[.!…]*$", "노라체": r"(노라|로다|니라)[.!…]*$",
    "소인체": r"(옵니다|옵니까|습지요|니다|니까)[.!…]*$",
    "올시다체": r"(올시다|소이다|하오|오|소|지요)[.!…]*$", "탄식체": r"(구려|더이다|오이다|하오|오|소)[.!…]*$",
}
_ADDR = re.compile(r"[,·]?\s*(형사님|수사관님|나리|어르신|판관님?|재판관님?)[.!…]*$")


def check_register(text, want):
    pat = ENDING_PATTERNS.get(want)
    if not pat:
        return None, []
    sents = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text) if len(s.strip()) > 3]
    bad = [s for s in sents if not re.search(pat, _ADDR.sub("", s).strip())]
    return (len(sents) - len(bad), len(sents)), bad[:2]


def distinctness(texts):
    def grams(t):
        w = re.findall(r"[가-힣]{2,}", t)
        return set(zip(w, w[1:]))
    gs = [grams(t) for t in texts if t]
    if len(gs) < 2:
        return None
    sims = []
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            u = gs[i] | gs[j]
            if u:
                sims.append(len(gs[i] & gs[j]) / len(u))
    return sum(sims) / len(sims) if sims else 0.0


def check_recital(text, blobs):
    t = re.sub(r"\s+", "", text)
    for blob in blobs:
        b = re.sub(r"\s+", "", blob or "")
        for i in range(0, max(0, len(b) - 12)):
            if b[i:i + 12] in t:
                return b[i:i + 12]
    return None


def _p(txt=""):
    print(txt, flush=True)


def _cut(text, cap=70):
    """단서 한 줄 미리보기 — **낱말 가운데서 끊지 않는다.**
    예전엔 그냥 [:70]이라 "'좋아하는 향: 니코틴'(조" 처럼 잘렸다."""
    x = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(x) <= cap:
        return x
    cut = x[:cap]
    k = max(cut.rfind(". "), cut.rfind(" — "), cut.rfind(", "), cut.rfind(" "))
    return (cut[:k] if k > cap * 0.5 else cut).rstrip(" ,—") + "…"


# ── 플레이어가 아는 것 ────────────────────────────────────────────────
def _known_blob(s, g):
    """**지금까지 공개된 것만** 모은다.

    ★2026-08-25 — 예전 하네스는 질문을 c["pressure_points"][0]["trigger"]에서
      곧장 꺼내 썼다. 그건 **정답지**다. 그래서 1라운드 첫 마디가
      "DSL 2.0에 대해 말해 보시오"였다 — 플레이어가 알 길이 없는 낱말이다.
      질문은 손에 쥔 단서와 이미 드러난 비밀에서만 나와야 한다.
    """
    parts = []
    for cl in (s.get("clue_graph") or []):
        if cl.get("id") in g.held_clues:
            parts += [cl.get("surface", ""), cl.get("meaning", ""), cl.get("name", "")]
    for v in g.disclosed_secrets.values():
        parts += list(v)
    for c in s["cast"]:
        parts.append(c.get("public", ""))
    parts.append((s.get("victim") or {}).get("role", ""))
    return " ".join(x for x in parts if x)


def _je(w):
    ch = (w or " ")[-1]
    return "와는" if ("가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 == 0) else "과는"


def _eun(w):
    ch = (w or " ")[-1]
    return "은" if ("가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28) else "는"


# ── 플레이 방식 ───────────────────────────────────────────────────────
#  ★"진짜 플레이하는 것처럼" 보려면 **한 가지 방식으로만 돌리면 안 된다.**
#    사람마다 예산 8을 쓰는 법이 다르고, 그래서 같은 사건이 다르게 끝난다.
#    search = 예산 중 방을 뒤지는 데 쓰는 비율, mix = 질문을 고르는 성향.
STYLES = {
    "정공법": {"offset": 0, "search": 0.50, "mix": ["되짚기", "관계", "단서", "타인"],
             "note": "골고루 — 뒤지고 묻고 짚는다"},
    "탐색파": {"offset": 1, "search": 0.75, "mix": ["단서", "되짚기", "단서"],
             "note": "발로 뛴다 — 물증을 모아 놓고 마지막에 들이댄다"},
    "심문파": {"offset": 2, "search": 0.15, "mix": ["관계", "타인", "모순", "비밀"],
             "note": "사람만 판다 — 말과 말 사이를 노린다"},
    "증거파": {"offset": 3, "search": 0.40, "mix": ["단서", "비밀", "단서", "모순"],
             "note": "쥔 것을 곧장 들이댄다 — 실토를 노린다"},
    "모순파": {"offset": 4, "search": 0.30, "mix": ["모순", "모순", "타인", "단서"],
             "note": "남의 진술을 물어다 붙인다"},
}


def _ask(s, g, c, rnd, asked_n, style, turns):
    """이 인물에게 지금 던질 질문 하나.

    ★질문은 **플레이어가 아는 것에서만** 나온다. 정답지를 뒤지지 않는다.
      돌려주는 것: (질문, 들이댄 단서 id들)
      단서를 인용해 물으면 그것이 곧 '증거를 들이댄' 것이고,
      그 단서가 비밀의 forced_by에 들어 있으면 stance가 ADMIT을 연다.
    """
    import play_agents as _pa
    F = _pa.forms(s)                    # ★이 편의 시대에 맞는 말투 (2026-08-27)
    v = (s.get("victim") or {}).get("name", "피해자")
    others = [x for x in s["cast"] if x["id"] != c["id"]]
    slots = s.get("time_slots") or ["그날 밤"]
    slot = slots[min(rnd - 1, len(slots) - 1)]
    mix = style["mix"]
    known = _known_blob(s, g)
    # ★사람마다 **다른 것을** 묻는다 (2026-08-25).
    #   asked_n만 쓰면 인물별로 0에서 시작해 다섯 명이 첫 질문을 똑같이 받았다.
    idx = next((i for i, x in enumerate(s["cast"]) if x["id"] == c["id"]), 0)
    k = asked_n * len(s["cast"]) + idx

    # 이 사람에게 아직 안 써 본 단서(소지품·전리품 제외 — 남의 것은 못 들이댄다)
    mine_used = {x for t_ in turns if t_["cast"] == c["id"] for x in (t_.get("evidence") or [])}
    pool = [cl for cl in (s.get("clue_graph") or [])
            if cl.get("id") in g.held_clues and cl.get("surface")
            and cl["id"] not in mine_used and cl.get("channel") != "belongings"]

    # ★단서는 **아무에게나 들이대는 것이 아니다** (2026-08-25).
    #   전에는 손에 쥔 것을 차례로 돌려 가며 물었다. 그래서 학회 사물함 파우치를
    #   엉뚱한 사람에게 내밀고, 정작 그 물건의 임자에게는 묻지 않는 판이 났다.
    #   비밀이 한 판에 0~1개밖에 안 열린 까닭이다.
    #   사람이라면 **그 사람 이야기가 적힌 단서**를 그 사람에게 내민다.
    #   정답지(forced_by)를 보는 것이 아니라, 단서 본문에 이름·신분·낱말이
    #   드러나 있는지만 본다 — 플레이어도 똑같이 할 수 있는 판단이다.
    trig = {x for pp in (c.get("pressure_points") or [])
            for x in (pp.get("trigger") or []) if x}
    marks = {c["name"]} | trig | {w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}",
                                                        c.get("public") or "")}
    aimed = [cl for cl in pool if any(m in cl["surface"] for m in marks)]
    #   ★고른 뒤 **거기서 뽑아야** 한다. 앞에 붙여만 놓고 pool 전체에 k%를 돌리면
    #     k가 커서 결국 엉뚱한 자리를 집는다 — 그래서 고르나 마나였다.
    pool = aimed if aimed else pool

    for kind in (mix[k % len(mix)],) + tuple(mix):     # 원하는 갈래부터, 안 되면 차선
        if kind == "단서" and pool:
            # ★46자로 잘라 붙이던 것을 그만둔다 (2026-08-26).
            #   비밀이 지목한 낱말이 잘려 나가 정곡이 서지 않았다.
            #   화면에서도 플레이어는 단서 카드를 통째로 내민다.
            cl = pool[k % len(pool)]
            return f"「{cl['surface']}」 — {F['evi']}", [cl["id"]]
        if kind == "비밀":
            hot = [t for pp in (c.get("pressure_points") or [])
                   for t in (pp.get("trigger") or []) if t and t in known]
            if hot:
                return (f"{hot[k % len(hot)]}에 대해 "
                        + ("말씀해 주세요." if "주세요" in F["scene"] else "말해 보시오."), [])
        if kind == "모순":
            said = [t_ for t_ in turns if t_["cast"] != c["id"] and t_.get("a")]
            if said:
                t_ = said[-(1 + k) % len(said)]
                frag = _cut(re.split(r"(?<=[.!])\s+", t_["a"])[0], 40)
                return (f"{t_['name']}{_eun(t_['name'])} 「{frag}」라고 하던데, "
                        + ("어떻게 된 일인가요." if "주세요" in F["scene"] else "어떻게 된 것이오."), [])
        if kind == "관계":
            return _pa.rel_q(F, v), []
        if kind == "타인" and others:
            o = others[k % len(others)]
            return F["other"].format(who=o["name"]), []
        if kind == "되짚기":
            # ★동선은 더 이상 묻지 않는다 (2026-08-25). 첫 대면에 이미 들었다.
            #   들은 진술을 **근거로 삼아** 그 안을 파고든다.
            al = (c.get("alibi_narration") or "").strip()
            if al:
                head = _cut(re.split(r"(?<=[.!])\s+", al)[0], 40)
                nowish = "주세요" in F["scene"]
                probe = ([f"그 자리에 얼마나 계셨습니까.", F["scene"], "그 자리를 언제 떠나셨습니까."]
                         if nowish else
                         ["그 자리에 얼마나 있었는지 말해 보시오.", F["scene"],
                          "그 자리를 언제 떴는지 말해 보시오."])[k % 3]
                return f"「{head}」라고 했소. {probe}", []
            return f"{slot}에 " + F["place"].split(" ", 1)[-1], []
    return f"{slot}에 " + F["scene"].split(" ", 1)[-1], []


def _sn(s, *keys):
    """구간 나레이션 한 줄 꺼내기."""
    node = (s.get("ui") or {}).get("story_narration") or {}
    for k in keys:
        node = (node or {}).get(k) if isinstance(node, dict) else None
    return (node or {}).get("text") if isinstance(node, dict) else None


# ── 한 판 ─────────────────────────────────────────────────────────────
def run(path, llm, rounds=None, verbose=True, style="정공법"):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from game_engine_v2 import GameSession
    import stress_agent

    s = json.load(open(path, encoding="utf-8"))
    g = GameSession(s)
    stl = STYLES.get(style) or STYLES["정공법"]
    R = rounds or g.max_rounds
    names = {c["id"]: c["name"] for c in s["cast"]}
    ui = s["ui"]
    toast = {t["id"]: t for t in ui.get("toasts", [])}
    rep = {"version": VERSION, "style": style, "regen": 0, "stripped": 0, "turns": [], "qmark": 0, "register_ok": 0,
           "register_all": 0, "recital": 0, "confront": None, "flow": []}
    history = {cid: [] for cid in g.cast}
    rot = [0]                                   # 심문 순번 — 라운드를 넘어 이어진다
    asked_n = {cid: 0 for cid in g.cast}        # 인물별 질문 횟수
    flinched = {}                               # 흔들린 자리 — 다음 차례에 또 찌른다

    def flow(kind, text):
        rep["flow"].append({"kind": kind, "text": text})
        if verbose:
            _p(text)

    # ── 도입 ──────────────────────────────────────────────────
    if verbose:
        _p("\n" + "═" * 76)
        _p(f"  하네스 {VERSION}")
        _p(f"  「{s['meta']['title']}」  {(s.get('stars') or {}).get('stars','')}"
           f"  ·  {R}라운드 · 행동 예산 {s['config']['turns_per_round']}/R"
           f"  ·  {style} — {stl['note']}")
        _p("═" * 76)
    flow("나레이션", f"\n▶ [사건 공개]\n   {_sn(s,'case_open')}")

    # ★인트로 나레이션을 **쪽 단위로 다 찍는다** (2026-08-25).
    #   지금까지 이 대목이 통째로 빠져 있었다. 게임에서는 삽화와 함께 열여섯 쪽이
    #   넘어가는 가장 긴 구간인데, 기록에는 한 줄도 없어 검토할 수가 없었다.
    nr = (ui.get("narration") or {})
    pages = nr.get("pages") or []
    if pages:
        flow("나레이션", f"\n▶ [오프닝 나레이션] — {len(pages)}쪽 · 삽화 {nr.get('image_count', len(pages))}장")
        for pg in pages:
            mark = "  ⚠글자수초과" if pg.get("over_limit") else ""
            flow("인트로", f"   {pg['page']:2}쪽 ({pg.get('chars', 0)}자) {pg['text']}{mark}")
        blood = next((sc.get("copy", {}).get("line") for sc in ui.get("screens", [])
                      if sc.get("id") == "blood_transition"), None)
        if blood:
            flow("나레이션", f"\n▶ [혈흔 전환]\n   {_cut(blood, 120)}")

    flow("나레이션", f"\n▶ [현장]\n   {_sn(s,'crime_scene')}")
    flow("나레이션", f"\n▶ [피해자]\n   {_sn(s,'victim_card')}")
    if verbose:
        _p("\n▶ [용의자 공개]")
    for c in s["cast"]:
        t_ = _sn(s, "suspect_intro", c["id"])
        flow("나레이션", f"   · {t_}")
    flow("정보", f"\n   시작 보유 단서 {len(g.held_clues)}개 — {sorted(g.held_clues)}")

    # ── 라운드 ────────────────────────────────────────────────
    for rnd in range(1, R + 1):
        if verbose:
            _p("\n" + BAR)
        tb = toast.get("round_start", {})
        flow("토스트", f"· {tb.get('title','').replace('{r}', str(rnd))}")
        flow("나레이션", f"▶ [{rnd}라운드 시작]\n   {_sn(s,'round_start',str(rnd))}")
        ev = _sn(s, "event", str(rnd))
        if ev:
            # 토스트 제목은 **이 이벤트의 종류**로 고른다 — 전부 "판이 뒤집힙니다"가
            # 아니라, 무슨 일이 일어났는지가 제목에 드러나야 한다.
            evd = next((e for e in (s.get("events") or []) if e.get("round") == rnd), {})
            tb_ = toast.get("event", {})
            title = ((tb_.get("titles_by_kind") or {}).get(evd.get("kind"))
                     or tb_.get("fallback_title") or tb_.get("title", ""))
            flow("토스트", f"· {title}")
            flow("나레이션", f"▶ [이벤트]\n   {ev}")

        answers = []
        budget0 = g.turns_left
        # ① 예산 중 **이 방식이 정한 만큼**을 방 뒤지는 데 쓴다
        half = min(g.turns_left, max(0, round(g.turns_left * stl["search"])))
        used = 0; empty = 0
        # ★장소를 **돌려 가며** 뒤진다 (2026-08-25).
        #   예전엔 매 라운드 목록 첫머리부터 훑어서 세 라운드 내내 같은 방만
        #   뒤졌다 — 3라운드엔 네 번 뒤져 하나도 못 찾았다.
        _ps = ui["place_screens"]
        # ★방식마다 **도는 순서를 달리한다** (2026-08-25).
        #   전에는 다섯 방식이 모두 같은 방부터 돌아, 결정타가 있는 방을
        #   똑같이 지나쳤다. 그래서 무엇을 놓치는지가 갈리지 않았다.
        #   사람마다 먼저 가 보는 곳이 다른 것이 자연스럽다.
        off = (rnd - 1 + stl.get("offset", 0)) % len(_ps)
        order = _ps[off:] + _ps[:off]
        for ps in order:
            if used >= half or g.turns_left < 1:
                break
            # ★값은 **장소 하나에 1턴** (2026-08-25 개정).
            #   선택지마다 값을 매기던 시절엔 "책상 밑을 본다"가 심문 한 번과
            #   같은 값이었다. 이제 방을 고르는 것이 판단이고, 들어간 방에서는
            #   그 라운드에 있는 것이 한꺼번에 나온다.
            r = g.search(ps["place_id"])
            if "error" in r:
                break
            if not r.get("first_visit"):
                continue                       # 이미 이 라운드에 본 방 — 값도 안 든다
            used += 1
            if r.get("found_clues"):
                for cl in (r.get("clues") or []):
                    key = "clue_decisive" if cl.get("decisive") else "clue_new"
                    flow("토스트", f"· {toast.get(key,{}).get('title','')}"
                                   f"  [{r['place_name']}]")
                    flow("단서", f"     ▸ {cl.get('id')} — {_cut(cl.get('surface'))}")
            else:
                empty += 1
                flow("탐색", f"   · [{r['place_name']}] 뒤져 보았으나 나오는 것이 없다")

        # ② 남은 예산은 사람을 판다 — 예산을 다 쓴다
        while g.turns_left >= 1:
            # ★한 사람도 빠뜨리지 않는다 (2026-08-25).
            #   예전엔 라운드마다 0번부터 세어 앞의 네 명만 돌았다. 그래서
            #   **범인이 세 라운드 내내 한 번도 심문되지 않고** 만점이 났다.
            ids = list(g.cast)
            cid = ids[rot[0] % len(ids)]
            rot[0] += 1
            c = g.cast[cid]
            # ★처음 만나면 **알리바이부터 듣는다** — 예산 0 (2026-08-25).
            #   동선을 채팅으로 다섯 번 되묻느라 예산이 다 날아가던 것을 없앤다.
            mt = g.meet(cid)                      # 엔진이 첫 대면을 기억한다
            if mt.get("first_meet") and mt.get("alibi"):
                flow("진술", f"   {c['name']} (첫 대면 · 예산 0) — “{mt['alibi']}”")
            # ★흔들린 자리는 **다시 찌른다** (2026-08-26).
            #   전에는 매 턴 새 화제로 옮겨 갔다. 그래서 정곡을 찔러 놓고도
            #   그 자리를 두 번 다시 묻지 않았고, 심문만 하는 방식은 한 판에
            #   비밀을 하나도 못 열었다. 사람이라면 흔들리는 데를 또 판다.
            again = flinched.get(cid)
            if again and stl["mix"] != ["단서", "되짚기", "단서"]:
                q, ev = again
            else:
                q, ev = _ask(s, g, c, rnd, asked_n[cid], stl, rep["turns"])
                asked_n[cid] += 1
            before = set(g.disclosed_secrets.get(cid, set()))
            # ★증거는 **실제로 인용했을 때만** 들이댄 것으로 친다.
            #   True 고정이 1라운드 전원 실토와 만점을 만들었다.
            st = g.interrogate(cid, q, evidence_shown=bool(ev))
            if "error" in st:
                break
            # 흔들렸으면 그 질문을 쥐고 있다가 다음 차례에 그대로 다시 던진다
            if st.get("stance") == "FLINCH":
                flinched[cid] = (q, ev)
            else:
                flinched.pop(cid, None)
            sysmsg = stress_agent.suspect_system(s, c)
            # ★이번 턴의 태도 지시문 — 이게 빠져 있어서 엔진이 ADMIT을 내려도
            #   모델은 계속 "말씀드리기 어려워요"만 했다. 판단과 문장이 따로 놀았다.
            if st.get("directive"):
                sysmsg += "\n\n" + st["directive"]
            # ★장기기억 — 이미 한 말과 '또 물었다'는 지시를 프롬프트에 얹는다
            if st.get("memory_briefing"):
                sysmsg += "\n" + st["memory_briefing"]
            if st.get("again_directive"):
                sysmsg += "\n" + st["again_directive"]
            reply = llm.chat([{"role": "system", "content": sysmsg}]
                             + history[cid][-6:] + [{"role": "user", "content": q}])
            # ★코드로 다시 본다 (2026-08-25) — 프롬프트만으로는 새어 나간다.
            #   ① 이번 턴에 감췄어야 할 것(비밀·은폐·범인의 살해 동기)
            #   ② 범인의 살인 시인
            #   한 번은 다시 받아 보고, 그래도 새면 그 문장만 도려낸다.
            import stance as _stc
            bad = (_stc.leaked(reply, st) or _stc.confessed(reply, c)
                   or _stc.bad_address(reply))
            if bad:
                hard = (sysmsg + "\n\n[★다시 쓴다 — 방금 답이 규칙을 어겼다]\n"
                        "· 방금 답에 **입 밖에 내면 안 되는 것**이 섞였다.\n"
                        "· 같은 질문에 다시 답하되, 감춰야 할 것은 한 조각도 꺼내지 마라.\n"
                        "· 아는 척도 하지 마라. 모르면 모른다고, 말하기 싫으면 말을 돌려라.")
                reply = llm.chat([{"role": "system", "content": hard}]
                                 + history[cid][-4:] + [{"role": "user", "content": q}])
                rep["regen"] = rep.get("regen", 0) + 1
            reply, n1 = _stc.strip_leak(reply, st)
            reply, n2 = _stc.strip_confession(reply, c)
            if _stc.bad_address(reply):
                reply = _stc.fix_address(reply)      # 다시 받아도 남으면 바꿔 놓는다
                rep["stripped"] = rep.get("stripped", 0) + 1
            if n1 or n2:
                rep["stripped"] = rep.get("stripped", 0) + n1 + n2
            history[cid] += [{"role": "user", "content": q},
                             {"role": "assistant", "content": reply}]
            g.remember(cid, q, reply)        # 답을 기억에 적는다

            nq, qs = check_question_mark(reply)
            want = ((c.get("persona") or {}).get("voice") or {}).get("form", "")
            reg, bad = check_register(reply, want)
            blobs = [c.get("bio"), c.get("life_story")] + list((c.get("relationships") or {}).values())
            rec = check_recital(reply, blobs)
            rep["qmark"] += nq
            if reg:
                rep["register_ok"] += reg[0]; rep["register_all"] += reg[1]
            if rec:
                rep["recital"] += 1
            answers.append(reply)
            rep["turns"].append({"round": rnd, "cast": cid, "name": c["name"],
                                 "stance": st.get("stance"), "q": q, "a": reply,
                                 "qmark": nq, "qmark_lines": qs, "register": want,
                                 "register_bad": bad, "recital": rec,
                                 "evidence": ev,
                                 "habit": ((c.get("persona") or {}).get("voice") or {}).get("habit", ""),
                                 "gauge": st.get("gauge_after"),
                                 "asked_before": bool(st.get("asked_before"))})
            if verbose:
                mk = " ⚠물음표" if nq else ""
                if st.get("asked_before"):
                    ab = st["asked_before"]
                    mk += f"  🔁 같은 질문 {ab['times']}번째"
                _p(f"\n  💬 {c['name']} ({want} · {st.get('stance')} · 압박 {st.get('gauge_after')}){mk}")
                _p(f"     Q: {q}")
                _p(f"     A: {reply}")
                if bad:
                    _p(f"     ⚠ 말투 어긋남: {bad[0][:52]}")
                if rec:
                    _p(f"     ⚠ 설정서 낭독: …{rec}…")
            new_sec = set(g.disclosed_secrets.get(cid, set())) - before
            for sec in new_sec:
                flow("토스트", f"· {toast.get('secret_open',{}).get('title','')}"
                               f"  {c['name']} — {sec[:46]}…")
            yb = st.get("yielded_belonging")
            if yb:
                flow("단서", f"     ▸ 소지품 획득 — {yb.get('name')}")

        # ③ 조합 (예산 밖)
        for pair in list(g.composite_clues):
            if all(x in g.held_clues for x in pair):
                r = g.combine(pair[0], pair[1])
                if r.get("success") and not r.get("already_done"):
                    flow("조합", f"  · {pair[0]} + {pair[1]} → {r['name']} (+{r.get('points',0)}점)")

        # ④ 대질 — **풀리는 그 라운드 안에서** 한다 (2026-08-25).
        #   예전엔 세 라운드가 다 끝난 뒤 맨 끝에 붙여서, 대질로 열린 길을
        #   써먹을 라운드가 남아 있지 않았다. 이벤트 뒤에 푸는 뜻이 사라진다.
        if (rep["confront"] is None and g.cx_pairs
                and g.current_round >= g.confront_unlock_round):
            # ★짝을 방식마다 달리 고른다 (2026-08-26).
            #   대질에서 나오는 내용이 짝에 따라 달라지도록 만들어 놓고,
            #   정작 다섯 방식이 모두 같은 짝을 골라 그 차이를 볼 수 없었다.
            pairs = [p for p in g.cx_pairs if all(x in g.met for x in p)] or list(g.cx_pairs)
            (ca, cb) = pairs[stl["offset"] % len(pairs)]
            import play_agents as _pa2
            F2 = _pa2.forms(s)
            q_cx = [F2["cx"], _pa2.rel_q(F2, "상대"),
                    ("서로의 말이 어긋나는 대목을 말씀해 주세요." if "주세요" in F2["scene"]
                     else "서로의 말이 어긋나는 대목을 말해 보시오.")][stl["offset"] % 3]
            r = g.confront(ca, cb, q_cx)
            if "error" not in r:
                ex = (r.get("cross_exam") or {}).get("exchange") or []
                rv = (r.get("cross_exam") or {}).get("reveals") or {}
                rep["confront"] = {"a": names.get(ca), "b": names.get(cb), "round": rnd,
                                   "curated": r.get("is_curated_pair"),
                                   "lines": [(l["name"], l["beat"], l["line"]) for l in ex],
                                   "reveals": rv.get("note")}
                flow("토스트", f"· 대질 — {names.get(ca)} ↔ {names.get(cb)}")
                for l in ex:
                    flow("대질", f"   [{l['beat']}] {l['name']}: {l['line']}")
                flow("대질", f"   ▸ 드러난 것: {rv.get('note','')}")

        flow("정보", f"\n   예산 {budget0} 사용 — 탐색 {used}(헛수고 {empty}) · "
                     f"심문 {len(answers)} · 남은 {g.turns_left}"
                     f"   |  보유 단서 {len(g.held_clues)}개")
        not_asked = [names[x] for x in g.cast
                     if x not in {t_["cast"] for t_ in rep["turns"] if t_["round"] == rnd}]
        if not_asked:
            flow("정보", f"   이번 라운드에 못 만난 사람: {', '.join(not_asked)}")
        flow("나레이션", f"\n▶ [{rnd}라운드 종료]\n   {_sn(s,'round_end',str(rnd))}")
        if rnd < R:
            g.next_round()

    # ── 결말 ──────────────────────────────────────────────────
    if verbose:
        _p("\n" + BAR)
    flow("나레이션", f"\n▶ [지목 직전]\n   {_sn(s,'accuse')}")

    # ★실제로 **이름을 댄다** (2026-08-25).
    #   예전엔 지목을 건너뛰고 culprit_correct 5점을 무조건 얹었다. 그래서
    #   범인을 한 번도 만나지 못한 판이 10/10 '완전한 해명'으로 끝났다.
    #   지목은 손에 쥔 단서가 누구를 가리키는가로 정한다.
    tally = collections.Counter()
    #   ★미끼는 2점 (2026-08-28). 결정타 없이 조각 하나만 쥔 판이 미끼와
    #     동점이 되어 동전 던지기로 맞히는 일이 있었다. 사람은 미끼에 끌린다 —
    #     끌리는 만큼 무게를 준다. 결정타(3점)를 쥔 쪽은 여전히 이긴다.
    #   ★두 가지를 고쳤다 (2026-08-28, 250판 전수 스윕에서 적발) —
    #     · 결정타 판정은 weight 문자열이 아니라 **decisive 플래그**로 본다.
    #       02편 결정타는 decisive:true인데 weight:"physical"이라 1점을 받았고,
    #       결정타를 쥐고도 미끼(2점)에 져서 다섯 방식이 전원 같은 오답을 냈다.
    #     · weight:"alibi"는 셈에서 뺀다 — 「그 밤 제 거처에 있었소」 같은
    #       **결백 증언**이다. 지목 쪽에 더하면 방향이 반대다.
    #     · 같은 사람을 향한 미끼는 **한 번만** 2점 — 03편은 미끼 둘이 다
    #       자동 지급이라 공짜 4점이 됐고, 결정타(3점)를 쥐고도 졌다.
    #       미끼의 힘은 '의심스러운 이야기' 하나지, 장수가 아니다.
    herr_hit = set()
    for cl in g.clue_graph.values():          # 대질·소지품도 셈에 든다
        if cl.get("id") in g.held_clues and cl.get("points_to"):
            if cl.get("weight") == "alibi":
                continue
            if cl.get("weight") == "red_herring":
                if cl["points_to"] in herr_hit:
                    continue
                herr_hit.add(cl["points_to"])
                tally[cl["points_to"]] += 2
                continue
            tally[cl["points_to"]] += 3 if (cl.get("decisive") or cl.get("weight") == "decisive") else 1
    culprit = next((c["id"] for c in s["cast"] if c.get("is_culprit")), None)
    named = tally.most_common(1)[0][0] if tally else list(g.cast)[0]
    correct = (named == culprit)
    flow("정보", f"   지목 — {names.get(named,'?')}  ({'적중' if correct else '빗나감'})")

    n_sec = sum(len(v) for v in g.disclosed_secrets.values())
    sc = s.get("scoring") or {}
    pts = min((sc.get("culprit_correct", 5) if correct else 0)
              + n_sec * sc.get("secret_revealed_each", 1),
              sc.get("max", 10))
    grade = ""
    for gr in sorted(((s.get("ending") or {}).get("grades") or []), key=lambda x: x.get("min", 0)):
        if pts >= gr.get("min", 0):
            grade = gr.get("name", "")
    # 진상·재연·엔딩도 **기록에 남긴다** — 예전엔 화면에만 찍고 flow에 안 넣어서
    # 저장된 판이 '지목 직전'에서 끊겼고, 엔딩을 검토할 수가 없었다.
    flow("나레이션", f"\n▶ [진상] — {len((ui.get('reveal_sequence') or {}).get('beats') or [])}박")
    for bt in (ui.get("reveal_sequence") or {}).get("beats", []):
        flow("진상", f"   [{bt['label']}] {bt['text']}")
    flow("나레이션", f"\n▶ [범행 재연] — {len((ui.get('murder_reenactment') or {}).get('cuts') or [])}컷")
    for ct in (ui.get("murder_reenactment") or {}).get("cuts", []):
        flow("재연", f"   {ct['no']}. {ct['label']} — {_cut(ct['text'], 64)}")
    flow("정보", f"\n▶ [엔딩] 「{grade}」  {pts}/{sc.get('max',10)}점 · 비밀 {n_sec}개")
    flow("나레이션", f"   {_sn(s,'ending',grade)}")
    # ★확신 — 결정타를 손에 쥐고 짚었는가 (2026-08-25).
    #   가리키는 단서를 세어 최다를 고르면 결정타 없이도 맞는 일이 생긴다.
    #   맞았다고 다 같은 것이 아니므로, **근거를 쥐었는지**를 따로 기록한다.
    dec = {cl["id"] for cl in (s.get("clue_graph") or []) if cl.get("decisive")}
    confident = bool(dec & set(g.held_clues))
    rep["held_clues"] = sorted(g.held_clues)
    rep["notebook"] = list(getattr(g, "notebook", []))
    rep["result"] = {"points": pts, "max": sc.get("max", 10), "grade": grade,
                     "secrets": n_sec, "clues": len(g.held_clues),
                     "named": names.get(named), "culprit": names.get(culprit),
                     "correct": correct, "confident": confident,
                     "ending_branch": ("caught" if correct else "escaped")}

    per_cast = collections.defaultdict(list)
    for t_ in rep["turns"]:
        per_cast[t_["cast"]].append(t_["a"])
    rs = [distinctness(v) for v in per_cast.values() if len(v) > 1]
    rs = [x for x in rs if x is not None]
    rep["self_repeat"] = (sum(rs) / len(rs)) if rs else None
    rep["distinct"] = distinctness([t["a"] for t in rep["turns"]])
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", nargs="?", default="91_dsl_demo.json")
    ap.add_argument("--key-file", default=".apikey")
    ap.add_argument("--model", default=os.environ.get("MM_API_MODEL", "gpt-4o-mini"))
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--style", default="정공법",
                    help="플레이 방식: " + " / ".join(STYLES))
    a = ap.parse_args()

    kf = os.path.expanduser(a.key_file)
    if not os.path.exists(kf):
        for alt in ("../.apikey", os.path.expanduser("~/Desktop/murdermystery/.apikey")):
            if os.path.exists(alt):
                kf = alt; break
    if not os.path.exists(kf):
        print(f"키 파일이 없습니다: {a.key_file}"); sys.exit(1)
    os.environ["MM_API_KEY"] = open(kf, encoding="utf-8").read().strip()
    os.environ["MM_API_MODEL"] = a.model

    from llm_api import ApiLLM
    llm = ApiLLM(max_new_tokens=520, temperature=0.8)

    path = a.scenario
    if not os.path.exists(path):
        cand = glob.glob(path) or glob.glob("scenarios/" + path)
        path = cand[0] if cand else path

    rep = run(path, llm, rounds=a.rounds, verbose=not a.quiet, style=a.style)

    n = len(rep["turns"])
    print("\n" + "═" * 76)
    print("  문장 품질 검사")
    print("═" * 76)
    print(f"  ① 답변 다양성   인물끼리 겹침 {rep['distinct']*100:5.1f}%   "
          f"{'✅' if rep['distinct'] < .20 else '❌'} (20% 아래)")
    print(f"  ② 되묻기        물음표 {rep['qmark']}개 / 답변 {n}개        "
          f"{'✅' if rep['qmark']==0 else '❌ 위반'}")
    ro, ra = rep["register_ok"], rep["register_all"]
    print(f"  ③ 말투 고정     {ro}/{ra} 문장 일치 ({ro/ra*100 if ra else 0:4.0f}%)   "
          f"{'✅' if ra and ro/ra >= .9 else '❌'}")
    if rep.get("self_repeat") is not None:
        print(f"  ④ 자기 반복     라운드마다 겹침 {rep['self_repeat']*100:5.1f}%   "
              f"{'✅' if rep['self_repeat'] < .30 else '❌'} (30% 아래)")
    ab = [t_ for t_ in rep["turns"] if t_.get("asked_before")]
    if ab:
        cue = re.compile(r"아까|앞서|말씀드렸|말했|얘기했|아뢰|이르지")
        hit = sum(1 for t_ in ab if cue.search(t_["a"]))
        print(f"  ⑦ 되물음 응대   {hit}/{len(ab)} 이 '아까 말했다'고 짚음   "
              f"{'✅' if hit == len(ab) else '❌ 그냥 반복'}")
    print(f"  ⑤ 설정서 낭독   {rep['recital']}건 / 답변 {n}개        "
          f"{'✅' if rep['recital']==0 else '❌ 복붙'}")
    if rep["confront"]:
        print(f"  ⑥ 대질          {rep['confront']['a']} ↔ {rep['confront']['b']} · "
              f"대본 {len(rep['confront']['lines'])}줄 ✅")
    r_ = rep["result"]
    print(f"\n  결과: 「{r_['grade']}」 {r_['points']}/{r_['max']}점 · "
          f"비밀 {r_['secrets']}개 · 단서 {r_['clues']}개")
    cin, cout = llm.tokens_in, llm.tokens_out
    cost = cin / 1e6 * 0.15 + cout / 1e6 * 0.60
    print(f"  호출 {llm.calls}회 · 토큰 in {cin:,} out {cout:,} · "
          f"약 ${cost:.4f} ({cost*1400:.0f}원)")
    print("═" * 76)

    out = f"llm_playtest_{os.path.basename(path)[:2]}.json"
    json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  전체 기록: {out}")


if __name__ == "__main__":
    main()
