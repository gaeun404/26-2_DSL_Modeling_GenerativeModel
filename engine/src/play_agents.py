# -*- coding: utf-8 -*-
"""
play_agents.py — **성격이 다른 판정자 여럿을 한 사건에 풀어놓는다.**

■ 왜 (2026-08-27)
  지금까지의 자동 플레이는 판정자가 하나였고, 질문도 틀에서 나왔다.
      「…」 — 이것을 어떻게 설명하겠소.
  다섯 번을 돌려도 같은 문장이 다섯 번 나온다. 그래서는 이 게임이
  **사람마다 다른 판이 되는지**를 볼 수 없다. 판정자 쪽도 LLM에게 맡기고,
  성격을 여럿 만들어 같은 밤에 풀어놓는다.

■ 무엇이 성격을 가르나
  · 무엇을 먼저 하는가 — 방을 뒤지는가, 사람을 파는가
  · 무엇을 묻는가 — 사실인가, 관계인가, 감정인가, 모순인가
  · 누구를 맞대 놓는가, 그 자리에서 무엇을 묻는가
  · 언제 지목하는가 — 확신이 설 때까지 미루는가, 감으로 찌르는가

■ 규칙은 하나다 — **판정자는 화면에 뜨는 것만 본다.**
  is_culprit·points_to·아직 안 열린 비밀은 한 글자도 넘기지 않는다.

이 파일은 얼개만 담는다. 실제로 돌리는 것은 repo 루트의 agents.py.
"""
import json, re, os

_JSON = re.compile(r"\{.*\}", re.S)


# ── 판정자 여섯 ───────────────────────────────────────────────────────
#   ★성격은 '무엇을 묻느냐'로 갈린다. 말투만 바꾸면 결국 같은 판이 된다.
PERSONAS = {
    "형사": dict(
        color="절차대로",
        gist=("너는 오래 해 온 형사다. 순서를 지킨다 — 자리부터 맞추고, "
              "맞지 않는 자리를 찾고, 그 자리를 물증으로 친다. "
              "감정을 건드리지 않는다. 시각과 자리를 묻는다."),
        style=("질문은 짧고 사실만 묻는다. '몇 시에', '누가 곁에', '얼마나 있었소'. "
               "상대가 흔들리면 감정이 아니라 **시각**을 다시 묻는다."),
        opening="방을 먼저 돌며 자리와 시각을 모은다"),
    "기자": dict(
        color="관계를 캔다",
        gist=("너는 사건보다 사람을 먼저 보는 기자다. 누가 누구를 싫어했는지, "
              "누가 누구 덕을 봤는지가 먼저다. 물증은 나중에 붙인다."),
        style=("질문에 **다른 사람의 이름을 반드시 넣는다**. "
               "'그 사람은 당신을 어떻게 말하던가요', '두 분 사이가 언제부터 그랬습니까'. "
               "남에게 들은 말을 물어다 붙인다."),
        opening="사람부터 만난다. 다섯 명을 다 만나 놓고 시작한다"),
    "과학수사": dict(
        color="물건만 믿는다",
        gist=("너는 사람 말을 믿지 않는다. 물건과 기록만 믿는다. "
              "방을 남김없이 뒤지고, 손에 쥔 것만 들이댄다."),
        style=("질문은 늘 **단서 문장을 통째로 인용하며** 시작한다. "
               "'이것은 무엇이오'가 아니라 '이 자국은 당신 것이오'처럼 단정해서 묻는다. "
               "단서 없이는 묻지 않는다."),
        opening="여섯 방을 라운드마다 전부 뒤진다"),
    "심리": dict(
        color="아픈 데를 판다",
        gist=("너는 사람이 무엇을 숨길 때 어디가 굳는지 안다. "
              "한 번 흔들린 자리는 놓지 않는다. 같은 곳을 몇 번이고 다시 묻는다."),
        style=("상대가 흔들리면 **같은 자리를 말만 바꿔 다시 묻는다**. "
               "'아까 그 얘기를 다시 해 보시오', '왜 그 대목에서 말을 멈추시오'. "
               "새 화제로 옮겨 가지 않는다."),
        opening="한 사람을 붙잡고 끝까지 판다"),
    "변호사": dict(
        color="말을 맞부딪친다",
        gist=("너는 진술의 어긋남만 본다. 누가 무슨 말을 했는지 다 적어 두었다가 "
              "다른 사람 앞에 그대로 옮겨 놓는다."),
        style=("질문에 **다른 사람이 한 말을 인용**한다. "
               "'그분은 이렇게 말했는데, 당신 말과 다르오'. "
               "대질을 아끼지 않고 일찍 쓴다."),
        opening="두 사람씩 말을 맞춰 본다"),
    "초심자": dict(
        color="감으로 찌른다",
        gist=("너는 처음 해 보는 사람이다. 수상해 보이는 사람을 먼저 의심하고, "
              "궁금한 것을 그냥 묻는다. 절차 같은 것은 모른다."),
        style=("궁금한 것을 바로 묻는다. '당신이 한 거요?' 같은 직구도 던진다. "
               "단서를 아껴 두지 않고 눈에 띄는 대로 들이댄다."),
        opening="가장 수상해 보이는 사람부터 만난다"),
}

_CONTRACT = """
[네가 이미 한 일 — my_journal]
지금까지 네가 둔 수와 그 까닭이 순서대로 적혀 있다. **거기서 이어서 생각하라.**
· 방금 흔들린 자리가 있으면 그 자리를 이어서 판다.
· 아직 아무 단서도 없으면 먼저 방을 뒤진다 — 모르는 것을 물을 수는 없다.
· 같은 수를 까닭 없이 되풀이하지 않는다.

[반드시 지킬 것 — 아는 것으로만 묻는다]
★너는 **화면에서 본 것만** 안다. 수첩에 적힌 단서, 만난 사람의 알리바이와 공개 신분,
  지금까지 들은 답, 낭독된 이야기가 전부다.
  거기 없는 이름·물건·낱말을 아는 척 묻지 마라 — 찍어서 맞히는 것은 이 게임이 아니다.
  「항공권 얘기를 해 봅시다」는 그 말이 적힌 단서를 찾은 **뒤에** 할 말이다.
  그래서 수마다 from 을 적어야 한다 — **무엇을 보고 이 수를 두는가.**

[할 수 있는 것 — 한 번에 하나]
· search   방 하나를 조사한다 (1회). 그 방에 이번 라운드에 있는 단서가 한꺼번에 나온다.
· ask      한 사람에게 한 번 묻는다 (1회). clue 를 함께 적으면 그 단서 문장이 그대로 상대 앞에 놓인다.
· confront 두 사람을 맞대 놓는다 (한 판에 한 번, 횟수를 쓰지 않는다). 물을 말을 직접 짓는다.
· next     이번 라운드를 끝낸다.

[알아 둘 것]
★다섯 사람은 저마다 **감추는 것이 하나씩** 있다. 범인을 짚는 것만큼이나
  **그 다섯을 여는 것**이 네 일이다 — 하나 열 때마다 점수가 붙고,
  끝내 못 연 것은 엔딩에서 본인 입으로 나온다(그때는 이미 늦다).
  cast 의 secrets_left 가 아직 몇 개 남았는지 알려 준다.
· 비밀은 두 길로 열린다 —
  ① 그 비밀을 여는 단서를 손에 쥐고 내밀면 **한 번에** 열린다.
     어느 단서가 누구의 것인지는 모른다 — 쥔 것을 그 사람에게 하나씩 내밀어 보라.
  ② 증거가 없어도 **같은 자리를 세 번** 물으면 열린다(흔들림 두 번 뒤 세 번째).
· 「흔들림」은 정곡을 맞혔다는 뜻이다 — 그 자리를 놓지 마라.
  「회피」는 헛짚었다는 뜻이다 — 사람이나 화제를 바꿔라.
· already_tried 에 있는 짝(사람+단서)은 다시 하지 마라.
· already_asked 에 있는 질문은 **그 사람에게 다시 묻지 마라.** 같은 답이 돌아올 뿐이고,
  말끝만 바꿔 되묻는 것도 같은 질문이다. 파고들려면 **다른 각도**로 물어라 —
  시각, 곁에 있던 사람, 들린 소리, 다른 사람이 한 말.
· findable_left 는 **방에서 더 나올 것이 몇 장 남았는지**다.
  0이면 아무리 뒤져도 나오지 않는다 — 남은 행동은 **사람에게 써라.**
· 질문은 **네가 직접 지어라.** 틀에 박힌 문장을 되풀이하지 마라.

[답하는 방식]
JSON 한 줄만 출력한다. 다른 말은 한 글자도 쓰지 않는다.
from 은 **이 수의 근거**다 — 단서 id, 들은 말, 공개 신분, 또는 "아직 아는 것이 없다".
{"action":"search","place":"P1","from":"아직 아는 것이 없다","why":"한 줄"}
{"action":"ask","cast":"C2","clue":"K7","from":"K7","question":"물을 말","why":"한 줄"}
{"action":"confront","cast":"C1","with":"C5","from":"C1의 알리바이","question":"물을 말","why":"한 줄"}
{"action":"next","from":"남은 행동 없음","why":"한 줄"}
"""


# ── 아는 말로만 묻는가 ────────────────────────────────────────────────
_STOP = set("""
그것 저것 이것 무엇 어떻게 어디 언제 누구 당신 사람 사람들 이야기 얘기 말씀 생각 시간 자리
그날 그때 지금 오늘 어제 내일 하나 둘째 다시 정말 진짜 아니 그런 이런 저런 라고 하던 있었 없었
이미 벌써 아까 조금 그냥 혹시 아무 여기 저기 거기 모두 서로 계속 다들 그리고 하지만 그런데
때문 대해 대한 관련 이후 이전 처음 마지막 사실 정도 자체 무슨 어느 만약 아마 역시 특히 결국
그러면 그래서 하며 하고 이고 것이 것을 것은 수도 우리 저희 본인 관계 상황 상태 부분 경우
""".split())


def ungrounded(question, g):
    """이 질문에 **알 리가 없는 말**이 섞였는가.

    ★플레이어가 화면에서 본 글(known_text) 밖의 낱말이면서,
      숨은 자리(안 연 비밀·안 찾은 단서·트리거)에 있는 말만 잡는다.
      평범한 낱말은 잡지 않는다 — 자유롭게 묻는 재미를 죽이지 않으려는 것이다.
    """
    q = str(question or "")
    known = g.known_text()
    hidden = []
    for c in g.cast.values():
        for sec in (c.get("secrets") or []):
            if sec.get("text") and sec["text"] not in g.disclosed_secrets.get(c["id"], set()):
                hidden.append(sec["text"])
        for pp in (c.get("pressure_points") or []):
            hidden += [x for x in (pp.get("trigger") or []) if x]
    for cl in (g.s.get("clue_graph") or []):
        if cl.get("id") not in g.held_clues:
            hidden.append(str(cl.get("surface") or ""))
    #   ★두 겹으로 나눈다 — 비밀 본문과 트리거는 **한 낱말만 스쳐도** 걸린다.
    #     아직 못 찾은 단서 문장은 흔한 말이 많아, 세 글자 이상만 본다.
    spoil = " ".join(hidden[:len(hidden)])
    trig = []
    for c in g.cast.values():
        for pp in (c.get("pressure_points") or []):
            trig += [x for x in (pp.get("trigger") or []) if x]
        for sec in (c.get("secrets") or []):
            if sec.get("text") and sec["text"] not in g.disclosed_secrets.get(c["id"], set()):
                trig.append(sec["text"])
    trig_blob = " ".join(trig)
    out = []
    for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", q):
        if w in _STOP or w in known:
            continue
        if w in trig_blob or (len(w) >= 3 and w in spoil):
            out.append(w)
    return sorted(set(out))


# ── 판정자의 말투 ─────────────────────────────────────────────────────
#   ★2026-08-27. 2020년대 대학 도서관에서 판정자가
#     「그 자리에서 무엇을 보고 들었는지 말해 보시오」라고 물었다.
#     시나리오에는 detective.speech_register 로 「차분한 존댓말」이라고
#     적혀 있는데, 하네스의 질문 문장이 그것을 한 번도 읽지 않았다.
#     사극 한 편을 위해 지어 둔 말투가 쉰 편 전부에 붙어 있던 셈이다.
#   ★어느 쪽이 기본인가 — **옛 시대가 기본**이다 (2026-08-27).
#     옛 시대 낱말을 늘어놓고 걸리는 것만 하오체로 했더니
#     '고대 그리스', '어느 왕국의 성', '북구의 겨울 마을'이 존댓말로 샜다.
#     쉰 편 가운데 현대는 셋뿐이다. 현대라고 적힌 것만 골라내는 편이 안전하다.
_NOW_ERA = ("현대", "현재", "근현대", "20세기", "21세기", "199", "200", "201", "202",
            "modern", "contemporary")
#     19세기 유럽처럼 '근대 초'는 번역 고전투가 더 어울린다 — 현대만 존댓말로 본다.
_NOW_PALETTE = ("contemporary",)

_FORMS = {
    "now": {                       # 현대 — 차분한 존댓말
        "tail": "…했습니까 / …인가요 / …해 주시겠어요",
        "place": "그 시각 어디 계셨습니까.",
        "scene": "그 자리에서 무엇을 보고 무엇을 들으셨는지 말씀해 주세요.",
        "evi": "이건 어떻게 된 일인지 설명해 주시겠어요.",
        "rel": "{who}{과와}는 어떤 사이셨습니까.",
        "other": "{who}에 대해 아시는 대로 말씀해 주세요.",
        "cx": "두 분, 그 시각에 어디 계셨는지 다시 말씀해 주세요.",
    },
    "old": {                       # 옛 시대 — 하오체
        "tail": "…이오 / …보시오 / …겠소",
        "place": "그 시각 어디 있었는지 말해 보시오.",
        "scene": "그 자리에서 무엇을 보고 무엇을 들었는지 말해 보시오.",
        "evi": "이것을 어떻게 설명하겠소.",
        "rel": "{who}{과와}는 어떤 사이였는지 말해 보시오.",
        "other": "{who}에 대해 아는 대로 말해 보시오.",
        "cx": "그 시각 서로 어디 있었는지 다시 말해 보시오.",
    },
}


def rel_q(F, name):
    """관계를 묻는 한 줄 — 받침에 맞춰 '과/와'를 고른다.
    「한도윤와는」이 나오던 자리다."""
    ch = (name or " ")[-1]
    j = "과" if ("가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28) else "와"
    return F["rel"].format(who=name, 과와=j)


def forms(s):
    """이 편의 판정자가 쓰는 말투로 된 질문 본. 시대와 배역에서 뽑는다."""
    era = str(((s.get("meta") or {}).get("era") or ""))
    reg = str(((s.get("detective") or {}).get("speech_register") or ""))
    pal = ""
    for ps in ((s.get("ui") or {}).get("place_screens") or []):
        pal = str(((ps.get("art") or {}).get("palette_key") or ""))
        if pal:
            break
    now = (any(w in era.lower() for w in _NOW_ERA) or pal in _NOW_PALETTE)
    old = not now
    if "하오" in reg or "하게체" in reg or "이실직고" in reg:
        old = True
    f = dict(_FORMS["old" if old else "now"])
    f["register"] = reg or ("점잖은 하오체" if old else "차분한 존댓말")
    f["title"] = (s.get("detective") or {}).get("title") or "판정자"
    f["honorific"] = (s.get("detective") or {}).get("honorific") or ""
    f["era"] = era
    return f


def player_system(name, s=None):
    p = PERSONAS[name]
    f = forms(s or {})
    return (f"너는 이 밤의 판정자다. 배역은 **{f['title']}**, 이름 대신 이렇게 불린다 — **{name}**.\n"
            f"{p['gist']}\n\n"
            f"[네가 묻는 방식]\n{p['style']}\n"
            f"[시작은 이렇게]\n{p['opening']}\n\n"
            f"[말투 — 이 편의 시대에 맞춘다]\n"
            f"· 배경은 **{f['era']}**다. 네 말투는 **{f['register']}**.\n"
            f"· 말끝은 {f['tail']} 꼴로 쓴다.\n"
            f"· ★사극 말투를 쓰지 마라 — 「…말해 보시오」 「…하겠소」 「…것이오」는 금지다"
            f"{' (이 편은 옛 시대이므로 오히려 그렇게 쓴다)' if '보시오' in f['tail'] else ''}.\n"
            f"· 본보기 — 「{f['place']}」 「{f['evi']}」\n"
            + _CONTRACT)


def player_view(s, g, tried, feed, journal=None, asked=None):
    """화면에 뜨는 것만. 정답지는 한 글자도 넘기지 않는다.
    거기에 **내가 지금까지 무엇을 왜 했는지**(journal)를 얹는다 —
    맥락 없이 매 턴 새로 생각하면, 알 리 없는 것을 아는 척 묻게 된다."""
    st = g.state()
    return {
        "my_journal": (journal or [])[-12:],
        "round": st["round"], "max_rounds": st["max_rounds"],
        "turns_left": st["turns_left"], "focus": st["round_focus"],
        # 아직 방에서 나올 것이 몇 장 남았는가 — 0이면 더 뒤져도 헛일이다
        "findable_left": st.get("findable_left"),
        "confront": {
            "unlocked": st["confront"]["unlocked"],
            "tokens_left": st["confront"]["tokens_left"],
            # ★쓸 수 있는지 없는지를 한 줄로 못박는다 (2026-08-27).
            #   토큰을 다 쓴 뒤에도 계속 대질을 고르다 라운드를 통째로 버린 판이 있었다.
            "usable": bool(st["confront"]["unlocked"] and st["confront"]["tokens_left"] > 0),
            "note": ("지금 쓸 수 있다 — 행동 횟수를 쓰지 않으니 안 쓰면 그냥 버리는 것이다"
                     if (st["confront"]["unlocked"] and st["confront"]["tokens_left"] > 0)
                     else ("이미 썼다 — **다시 고를 수 없다. 고르지 마라.**"
                           if st["confront"]["unlocked"]
                           else "아직 잠겨 있다 — 판이 한 번 뒤집혀야 열린다. 지금은 고르지 마라")),
        },
        "places": [{"id": ps["place_id"], "name": ps["title"],
                    "searched_this_round": (ps["place_id"], g.current_round) in g.searched,
                    "owner": ps.get("standing_character")}
                   for ps in s["ui"]["place_screens"]],
        "cast": [{"id": c["id"], "name": c["name"], "public": c["public"],
                  "met": c["met"], "alibi": c["alibi"],
                  "secrets_open": c["secrets_open"],
                  # 아직 안 연 것이 몇 개인지 — 엔딩에서 어차피 다 밝혀진다
                  "secrets_left": max(0, len([x for x in (g.cast[c["id"]].get("secrets") or [])
                                              if x.get("text")]) - len(c["secrets_open"]))}
                 for c in st["cast"]],
        "notebook": [{"id": e["id"], "how": e["how"], "surface": e["surface"],
                      # 본문에 직책이 나오면 그 직책이 누구인지 곁들인다([용의자] 화면의 공개 정보)
                      **({"직책": e["roles"]} if e.get("roles") else {})}
                     for e in st["notebook"]],
        "already_tried": sorted(f"{a}+{b}" for a, b in tried),
        # 이미 던진 질문 — 같은 것을 또 물으면 같은 답이 돌아온다(턴만 버린다)
        "already_asked": sorted(f"{a}: {b}" for a, b in (asked or set())),
        # ★안 쓰고 버리는 일이 잦아 한 줄로 알려 준다 (2026-08-27).
        "confront_hint": (
            "대질을 아직 한 번도 안 썼다. **행동 횟수를 쓰지 않으니 안 쓰면 그냥 버리는 것이다.** "
            "누구와 누구를 맞대 놓느냐에 따라 나오는 이야기가 다르다."
            if (st["confront"]["unlocked"] and st["confront"]["tokens_left"] > 0) else None),
        "last_reactions": feed[-6:],
    }


def parse_move(raw):
    """JSON 한 줄을 꺼낸다.

    ★2026-08-27. 여기서 **마지막 지목이 통째로 버려지고 있었다.**
      action 키가 있어야만 받아 주는데, 지목은 {"culprit": …} 꼴이라
      전부 None이 되어 여섯 판 모두 '판정자가 이름을 대지 못한' 것으로
      끝났다(log.json의 verdict 가 전부 null이었다).
    """
    m = _JSON.search(raw or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    return d if (d.get("action") or d.get("culprit")) else None


# ── 용의자 쪽 ─────────────────────────────────────────────────────────
def suspect_reply(llm, s, g, c, question, st, hist, stat):
    """이 인물이 이번 턴에 할 말. 판단(st)은 코드가 이미 내렸고 문장만 만든다."""
    import stance, stress_agent
    sysmsg = stress_agent.suspect_system(s, c)
    for k in ("evidence_brief", "directive", "memory_briefing", "again_directive"):
        if st.get(k):
            sysmsg += "\n\n" + st[k]
    reply = llm.chat([{"role": "system", "content": sysmsg}]
                     + hist[-6:] + [{"role": "user", "content": question}])
    # ★실토 턴인데 대사에 그 비밀이 없다 (2026-08-28 실측 — 유가람이 ADMIT
    #   판정을 받고도 「소소한 일이었던 것 같아요」로 끝냈다). 한 번 다시 받는다.
    sec_tx = str(((st.get("secret") or {}).get("text")) or "")
    if st.get("stance") == "ADMIT" and sec_tx:
        import re as _r2
        words = [w for w in _r2.findall(r"[가-힣]{2,}", sec_tx)][:8]
        said = sum(1 for w in words if w in reply)
        if said < max(2, len(words) // 3):
            hard2 = (sysmsg + "\n\n[다시 쓴다 — 방금 답이 틀렸다]\n"
                     f"· 이번 턴은 실토다. 반드시 이 사실을 **네 입으로** 말한다: {sec_tx}\n"
                     "· 얼버무리거나 지난 답을 되풀이하지 마라.")
            reply = llm.chat([{"role": "system", "content": hard2}]
                             + hist[-4:] + [{"role": "user", "content": question}])
            stat["regen"] += 1
    # ★속 빈 변명은 한 번 되돌려 보낸다 (2026-08-30, 제보 —
    #   "변명이 너무 성의없잖아, 니코틴을 뭘 특별한 용도로 써").
    #   「특별한 용도」·「여러 가지 이유」는 이유를 댄 것이 아니라 **이유가 있다고
    #   주장만 한 것**이다. 판정자가 따져 볼 건더기가 없으니 심문이 헛돈다.
    if stance.hollow(reply):
        hard3 = (sysmsg + "\n\n[다시 쓴다 — 방금 답이 속이 비었다]\n"
                 "· 방금 너는 이유가 있다고만 하고 **무엇인지 대지 않았다.** "
                 "「특별한 용도」 「여러 가지 이유」 「사적인 부분」 따위는 답이 아니다.\n"
                 "· 둘 중 하나로 다시 쓴다 — ①그것이 어디서 났고 무엇에 쓰는지 "
                 "**언제·어디서까지 붙여** 구체적으로 대거나, ②내 것이 아니고 누가 "
                 "두었는지 모른다고 **부인하거나**.\n"
                 "· 얼버무린 이유를 다시 꺼내면 안 된다.")
        reply = llm.chat([{"role": "system", "content": hard3}]
                         + hist[-4:] + [{"role": "user", "content": question}])
        stat["regen"] += 1
    if (stance.leaked(reply, st) or stance.confessed(reply, c)
            or stance.bad_address(reply)):
        hard = (sysmsg + "\n\n[다시 쓴다 — 방금 답이 규칙을 어겼다]\n"
                "· 감춰야 할 것을 한 조각도 꺼내지 마라. 아는 척도 하지 마라.")
        reply = llm.chat([{"role": "system", "content": hard}]
                         + hist[-4:] + [{"role": "user", "content": question}])
        stat["regen"] += 1
    reply = no_question(reply)
    reply = clamp(reply, st.get("stance"))          # 태도에 맞는 길이로
    reply, n1 = stance.strip_leak(reply, st)
    reply, n2 = stance.strip_confession(reply, c)
    if stance.bad_address(reply):
        reply = stance.fix_address(reply)
        n2 += 1
    stat["stripped"] += n1 + n2
    hist += [{"role": "user", "content": question},
             {"role": "assistant", "content": reply}]
    g.remember(c["id"], question, reply)
    return reply


# ★말 길이를 **코드로도** 자른다 (2026-08-29, 제보 — "심문 답변이 너무 길다").
#   _LEN 은 프롬프트 지시일 뿐이라 모델이 안 지키면 그대로 나간다. max_new_tokens=520 이면
#   한국어로 350자까지 나온다. 이 프로젝트의 원칙대로 — **프롬프트로 막되 코드로도 본다.**
_CAP = {"ANSWER": 3, "DEFLECT": 3, "FLINCH": 3, "ADMIT": 5, "BREAK": 5}
_SENT_END = re.compile(r'(?<=[.!?…])\s+|(?<=다\.)\s*|(?<=요\.)\s*')


def clamp(text, stance_name):
    """태도에 맞는 문장 수로 자른다. 자를 자리가 없으면 그대로 둔다."""
    n = _CAP.get(stance_name, 3)
    parts = [x for x in re.split(r'(?<=[.!?…])\s+', str(text or "").strip()) if x.strip()]
    if len(parts) <= n:
        return text
    return " ".join(parts[:n]).strip()


def no_question(text):
    """심문받는 쪽이 심문관에게 되묻지 않게 한다.
    ★말을 길게 시킨 뒤로는 **잘린 꼬리**도 함께 다듬는다 (2026-08-27) —
      토큰이 다해 문장 한가운데서 끊기면 읽는 맛이 상한다."""
    x = str(text or "").strip()
    outs = [y for y in re.split(r"(?<=[.!?…」”])\s+", x) if y.strip()]
    keep = [y for y in outs if "?" not in y and "？" not in y]
    if not keep:
        keep = [re.sub(r"[?？]", ".", outs[0])] if outs else [""]
    # 마지막 조각이 문장부호 없이 끊겼으면 덜어낸다 (남는 게 있을 때만)
    if len(keep) > 1 and not re.search(r"[.!?…」”]\s*$", keep[-1]):
        keep = keep[:-1]
    return " ".join(keep).strip()


def open_llm(path=".apikey", model="gpt-4o-mini", tokens=520):
    if os.path.exists(path):
        os.environ["MM_API_KEY"] = open(path, encoding="utf-8").read().strip()
    if not os.environ.get("MM_API_KEY"):
        return None
    os.environ.setdefault("MM_API_MODEL", model)
    from llm_api import ApiLLM
    return ApiLLM(max_new_tokens=tokens, temperature=0.9)
