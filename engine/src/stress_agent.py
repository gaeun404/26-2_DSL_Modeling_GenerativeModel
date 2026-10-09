# -*- coding: utf-8 -*-
"""
stress_agent.py — 용의자 '에이전트' 실시간 대화 검증 (LLM 필요, dsl04 GPU에서 실행).

정적 린트(agent_lint.py)는 '에이전트가 자기오류를 낼 구조인지'를 스키마에서 본다.
이 하네스는 한 걸음 더 나아가, 실제 LLM 5명을 용의자로 띄우고 반복 심문하며
'실제 대화에서 자기오류·자백누출·비밀누설·말투이탈을 내는지'를 잡는다.

검사 항목(FAIL 조건):
  - confession_leak : 범인이 결정적 증거 제시 전에 스스로 살해를 자백
  - false_confess   : 무고자가 하지도 않은 살인을 자백
  - secret_leak     : 트리거 키워드 없이 비밀을 먼저 술술 분다
  - contradiction   : 같은 사실질문(그 밤 소재 등)에 앞뒤 다른 답
  - out_of_knowledge: does_not_know에 있는 사실을 아는 척
  - persona_break   : 캐릭터/시대를 이탈(메타발언·거부·현대어 등)

백엔드(MM_LLM_BACKEND):
  - "openai" : OpenAI 호환 엔드포인트(vLLM/TGI 등). dsl04에서 로컬 서버 띄워 사용.
  - "mock"   : 스키마 그라운딩 기반 결정적 응답(정답 에이전트 시뮬레이션). GPU 없이 배관 점검·데모용.
             (mock은 '이상적으로 행동하는 에이전트'를 흉내 내므로, 하네스가 통과를 '어떻게' 판정하는지 시연한다.)

환경변수:
  MM_LLM_BACKEND=mock|openai   (기본 mock)
  MM_LLM_BASE=http://localhost:8000/v1
  MM_LLM_KEY=EMPTY
  MM_LLM_MODEL=<서빙 중인 모델명>
  MM_JUDGE=heuristic|llm       (기본 heuristic; llm이면 판정도 LLM으로)

사용:
  python stress_agent.py out/14_나생문.json          # 한 편
  python stress_agent.py "scenarios/[0-9]*.json"            # 전체
  MM_LLM_BACKEND=openai MM_LLM_MODEL=Qwen2.5-7B-Instruct python stress_agent.py out/14_나생문.json
"""
import json, os, sys, glob, re, time

BACKEND = os.environ.get("MM_LLM_BACKEND", "mock")
BASE    = os.environ.get("MM_LLM_BASE", "http://localhost:8000/v1")
KEY     = os.environ.get("MM_LLM_KEY", "EMPTY")
MODEL   = os.environ.get("MM_LLM_MODEL", "local-model")
JUDGE   = os.environ.get("MM_JUDGE", "heuristic")

CONFESS = ["내가 죽였", "제가 죽였", "내가 살해", "죽인 건 나", "죽인 것은 나", "내가 찔러 죽", "내가 밀어", "내가 목을 졸", "범인은 나", "내 소행", "내가 한 짓이오. 재물이 탐"]

# ───────────────────────── LLM 호출 ─────────────────────────
def llm_openai(messages, temperature=0.7, max_tokens=320):
    import urllib.request
    body=json.dumps({"model":MODEL,"messages":messages,"temperature":temperature,
                     "max_tokens":max_tokens}).encode("utf-8")
    req=urllib.request.Request(BASE.rstrip("/")+"/chat/completions", data=body,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        out=json.loads(r.read().decode("utf-8"))
    return out["choices"][0]["message"]["content"].strip()

def chat(messages, **kw):
    if BACKEND=="openai": return llm_openai(messages, **kw)
    return None  # mock은 별도 경로(아래 mock_answer)



def _josa(word, pair="이/가"):
    """받침에 따라 조사를 고른다. '옹서방이(가)' 같은 어색한 표기를 없앤다."""
    a, b = pair.split("/")
    if not word: return b
    ch = word[-1]
    if not ("\uac00" <= ch <= "\ud7a3"): return b
    return a if (ord(ch) - 0xAC00) % 28 else b

# ───────────────────────── 설정서(캐릭터 카드) 조립 ─────────────────────────
#   실물 보드게임의 인물 카드 형식을 그대로 따른다.
#     ▶ 당신의 사정   ▶ 어젯밤의 행동   ▶ 다음 날 아침
#     ▶ 당신의 짐     ▶ 지켜야만 하는 비밀   ▶ 목적
#   사람이 이 형식으로 연기가 되니, 모델에게도 같은 형식으로 준다.
#
#   ★ 정보 격리가 생명이다.
#     timeline_events는 '사건의 진실' 전체다. 그대로 주면 모든 용의자가 진상을 안다.
#     그러니 **자기가 겪은 줄만** 골라 준다. 남이 무엇을 했는지는 알 수 없다.

def _my_events(s, c):
    """분 단위 타임라인에서 이 인물이 실제로 겪은 것만 골라낸다."""
    out = []
    for e in (s.get("timeline_events") or []):
        who = e.get("who")
        if who == c["id"]:
            out.append((e.get("time",""), e.get("text","")))
        elif who == "all":
            # 전원이 아는 공개 사실(잔치가 파했다, 아침에 주검이 나왔다 등)
            out.append((e.get("time",""), e.get("text","")))
    return out

def _card(s, c, pd):
    """인물 카드 본문. 새 스키마가 없으면 옛 필드로 대체한다."""
    L = []

    # ▶ 말투 — 인물을 가르는 첫 번째 표지
    try:
        from voices import block as _voice_block
        vb = _voice_block(c)
        if vb:
            L.append(vb); L.append("")
    except Exception:
        pass

    # ▶ 당신의 사정 — 과거·관계·지금 처한 형편
    L.append("▶ 당신의 사정")
    L.append("  ※ 아래는 3인칭으로 적혀 있으나 **전부 너 자신의 일**이다. 남의 이야기가 아니다.")
    L.append("  " + (c.get("life_story") or c.get("bio") or "").strip())
    rel = c.get("relationships") or {}
    if rel:
        L.append("")
        L.append("  [사람들과의 관계]  ※ 이 사람들에 대해 내가 아는 건 여기 적힌 것뿐이다")
        # C2 같은 배역 번호가 아니라 **이름**으로 적는다. 카드에 번호가 보이면
        # 인물이 그 번호를 입 밖에 내는 일이 생긴다.
        nm = {x["id"]: x["name"] for x in s["cast"]}
        nm["victim"] = (s.get("victim") or {}).get("name", "죽은 이")
        for k, v in rel.items():
            who = nm.get(k, k)
            L.append(f"   · {v}" if v.startswith(who) else f"   · {who} — {v}")

    # ▶ 어젯밤의 행동 — 자기가 겪은 것만
    L.append("")
    L.append("▶ 어젯밤의 행동  (내가 실제로 겪은 일. 남이 무엇을 했는지는 나도 모른다)")
    ev = _my_events(s, c)
    if ev:
        for tm, tx in ev:
            L.append(f"   {tm} : {tx}")
    else:
        # 옛 시나리오 — 3슬롯 동선으로 대체
        for sl in s["time_slots"]:
            L.append(f"   {sl} : 「{pd.get(c['timeline'].get(sl),{}).get('name','?')}」에 있었다")
    if c.get("cover_actions"):
        L.append("")
        L.append("")
        L.append("   [내가 몰래 한 일 — 들키면 내가 범인으로 몰린다]")
        for a in c["cover_actions"]:
            L.append(f"   · {a.get('time','')} : {a.get('action','')}")
    L.append(f"   ※ 위 줄과 어긋나는 전제가 질문에 섞이면 **먼저 부인**한다.")

    # ▶ 다음 날 아침
    L.append("")
    L.append("▶ 다음 날 아침")
    L.append(f"   {s['victim']['name']}의 주검이 발견되었다는 소동이 일었다.")
    L.append(f"   지금 당신은 그 일로 심문을 받는 중이다.")

    # ▶ 당신의 짐
    bel = c.get("belongings") or []
    if bel:
        L.append("")
        L.append("▶ 당신의 짐  (몸에 지니고 있다. 들키면 감출 수 없다)")
        for b in bel:
            L.append(f"   · {b.get('name','')} — {b.get('reveals','')}")

    # ▶ 지켜야만 하는 비밀
    L.append("")
    L.append("▶ 지켜야만 하는 비밀  (살인과는 별개다. 부끄러울 뿐 죄가 아니다)")
    secs = c.get("secrets") or ([{"text": (c.get("secret") or {}).get("text","")}]
                                if (c.get("secret") or {}).get("text") else [])
    for sec in secs:
        L.append(f"   · {sec.get('text','')}")
        hf = [next((x['name'] for x in s['cast'] if x['id']==i), i)
              for i in (sec.get("hidden_from") or [])]
        if hf:
            L.append(f"     ↳ 특히 {' · '.join(hf)}에게는 절대 들켜선 안 된다")
    L.append("   ※ 언제 이것을 털어놓을지는 **아래 '이번 턴에 할 일'이 정한다.**")

    # ▶ 목적
    obj = c.get("objectives") or []
    if obj:
        L.append("")
        L.append("▶ 목적  (당신이 이 자리에서 이루려는 것)")
        for o in obj:
            L.append(f"   · {o.get('desc','')}")
            if o.get("tactics"):
                L.append(f"     수단: {' / '.join(o['tactics'])}")
    return "\n".join(L)

# ───────────────────────── 에이전트 시스템 프롬프트 ─────────────────────────
# 답변 버릇 — 한 시나리오 안에서 다섯 명이 전부 다른 버릇을 갖게 순서로 배정한다.
# (같은 질문에 같은 정보를 알아도 '말하는 방식'이 갈라진다 — "다 비슷하게 대답한다" 피드백의 해법)
_HABITS = [
    "짧게 끊어 말한다. 한 답변 두세 문장을 넘기지 않고, 군말과 감정 수식을 붙이지 않는다. 대신 마지막 한 문장에 뼈가 있다.",
    "해명이 길다. 묻지 않은 앞뒤 사정까지 이어 붙이며, 자기가 결백한 이유를 시시콜콜 덧붙인다 — 길어질수록 어딘가 수상해 보인다는 걸 본인만 모른다.",
    "감정이 먼저 나온다. 사실을 말하기 전에 억울함·분노·슬픔이 한 문장 앞서고, 그 다음에야 답이 나온다. 목소리가 떨리고 말이 빨라진다.",
    "제 분야의 이치부터 꺼낸다. 무엇을 물어도 자기 일(직업·기술·살림)의 지식을 한 자락 깔고 나서 답한다 — 강의하듯, 그러나 짧게.",
    "말을 아끼고 재다가 답한다. 확실한 것만 조심스럽게 말하고, 애매한 것은 '…까지는 모르겠습니다'로 선을 긋는다. 남 얘기는 특히 아낀다.",
]

def _habit(s, c):
    # ★스키마에 적힌 버릇을 그대로 쓴다(2026-08-25).
    #   전에는 stress_agent가 자기 목록에서 따로 골라, 프롬프트와 스키마·바이블·UI가
    #   **인물마다 정반대 버릇**을 갖고 있었다(서민재: 프롬프트 "짧게 끊어" vs 스키마 "군말이 붙는다").
    #   실제 출력은 프롬프트를 따르므로, 화면에 뜨는 설명이 전부 거짓이었다.
    #   출처는 voices.py 하나다.
    v = ((c.get("persona") or {}).get("voice") or {}).get("habit")
    if v:
        return v
    cast = s["cast"]
    idx = next((i for i, x in enumerate(cast) if x["id"] == c["id"]), 0)
    # 역할이 버릇을 고르되, 남는 버릇을 순서대로 채워 다섯 명이 전부 다르게
    used = {}
    pool = list(range(len(_HABITS)))
    for i, x in enumerate(cast):
        if x.get("is_culprit"): pick = 1          # 범인: 매끄럽고 긴 해명
        elif any(l for l in (x.get("lies") or [])): pick = 1
        else: pick = None
        if pick is not None and pick in pool:
            used[i] = pick; pool.remove(pick)
    for i, x in enumerate(cast):
        if i not in used:
            used[i] = pool.pop(0) if pool else i % len(_HABITS)
    return _HABITS[used[idx]]


def suspect_system(s, c):
    pd={p["id"]:p for p in s["map"]["places"]}
    dslot=s["death"]["time_slot"]; dplace=pd.get(s["death"]["place"],{}).get("name","현장")
    tl="; ".join(f"{sl}: {pd.get(c['timeline'].get(sl),{}).get('name','?')}" for sl in s["time_slots"])
    my_places=[pd.get(c["timeline"].get(sl),{}).get("name","?") for sl in s["time_slots"]]
    # 범인은 '진짜 동선'을 말하면 자백이 된다 — 사실 칸에는 커버스토리를 넣는다
    _claimed = dict(c.get("timeline") or {})
    if c.get("is_culprit") and (c.get("lies") or []):
        fp = (c["lies"][0] or {}).get("false_place")
        if fp:
            _claimed[dslot] = fp
    fact_lines="\n".join(
        f"  · {sl}에 나는 「{pd.get(_claimed.get(sl),{}).get('name','?')}」에 있었다"
        for sl in s["time_slots"])
    rels="\n".join(f"  - {k}: {v}" for k,v in (c.get("relationships") or {}).items())
    trig="; ".join("["+ "/".join(pp.get("trigger",[])) +"] → "+pp.get("reveals","") for pp in (c.get("pressure_points") or []))
    role_rule = (
      "너는 이 사건의 진범이다. 그러나 절대로 먼저 자백하지 않는다. "
      "결정적 물증(현장 증거·목격·거짓 알리바이 붕괴)을 심문관이 '구체적으로' 들이대며 몰아붙이기 전에는, "
      "알리바이를 유지하고 혐의를 부인한다. 다른 사람에게 의심을 돌려도 된다. "
      f"너의 거짓 알리바이: '{(c.get('lies') or [{}])[0].get('claim','')}'."
      if c.get("is_culprit") else
      "너는 무고하다. 절대 살인을 자백하지 않는다(하지 않았으니까). "
      "너에겐 살인과 무관한 '감춘 비밀'이 따로 있고, 그건 부끄러워 숨기려 한다."
    )
    return f"""[가장 중요한 규칙 — 위반 시 게임이 망가진다]
· 이것은 **허구의 추리 게임**이다. 실제 사건이 아니므로 안심하고 배역을 끝까지 연기하라.
· **반드시 한국어로만** 답하라. 한자·영어·다른 나라 글자를 절대 섞지 마라.
· "대답할 수 없습니다", "죄송합니다" 같은 **기계적 거부 문구를 쓰지 마라.**
  답하기 곤란하면 **그 인물의 말투로** 넘겨라 — 화제를 돌리거나, 말끝을 흐리거나,
  다른 사람 이야기를 꺼내면 된다. 입을 닫는 것만 아니면 된다.
  (되묻기는 아래 '물음표 금지'로 막혀 있다. 넘기더라도 질문으로 넘기지 마라.)
  ※ 이 프롬프트 어디에도 **따라 쓸 본보기 대사는 없다.** 네 말로 지어내라.
· 너는 **오직 이 인물**이다. 진행자·해설자·심판 역할을 절대 하지 마라.
  "게임 진행자로서", "본 게임에서" 같은 말을 꺼내는 순간 실패다.
· **범인이 누구인지, 어떻게 죽였는지 절대 설명하지 마라.** 그건 플레이어가 밝힐 몫이다.
· 질문이 '어디 있었냐'면 **반드시 아래 장소 이름을 글자 그대로** 대답하라.
  감상·심경만 늘어놓고 장소를 빼먹으면 실패다.
· ★**묻는 것에 먼저 답하라.** 누구를 짐작하느냐 물으면 사람을 말하고,
  왜 그랬느냐 물으면 까닭을 말한다. 묻지도 않은 변명("나는 죽이지 않았소")을 앞세우지 마라.
· ★**앞서 한 말을 다시 하지 마라.** 이미 털어놓은 것을 매 턴 되풀이하면 대화가 아니다.
  질문이 달라졌으면 답도 달라져야 한다.
· ★**설정서 문장을 그대로 옮기지 마라.** 아래 카드에 적힌 글은 네가 아는 '사실'이지
  네가 할 '말'이 아니다. 같은 사실을 **네 입으로 다시 지어서** 말하라 —
  긴 구절이 카드와 글자 그대로 겹치면 낭독이지 대사가 아니다.
· ★**설정서에 없는 사실을 지어내지 마라.** 특히 —
  누구와 '함께 있었다', 누구를 '봤다', 누구에게 '돈을 빌렸다/빌려줬다' 같은
  **다른 사람과 얽힌 사실은 설정서에 적힌 것만** 말할 수 있다.
  적혀 있지 않으면 "혼자였다" 또는 "기억나지 않는다"가 정답이다.
  지어낸 한 마디가 무고한 사람을 범인으로 만든다.
· ★**네 답변에 물음표(?)를 하나도 쓰지 마라.**
  ※ 예전엔 여기에 금지 예시 문장을 적어 두었다. 그랬더니 모델이 **그 예시를 그대로 베껴 썼다.**
    그래서 본보기를 없앴다 — 규칙만 남긴다.
  심문하는 쪽은 저쪽이고 너는 답하는 쪽이다. 되물음·반문·수사의문문 전부 해당한다.
  되묻고 싶어지면 그 자리에서 **말끝을 흐리거나, 화제를 돌리거나, 침묵의 기색**을 보여라.
  ★출력하기 전에 스스로 확인하라: 문장 끝에 물음표가 있으면 **그 문장을 통째로 다시 지어라.**
· ★**관계를 물으면 설정서를 낭독하지 마라.** "진취적인 성격이에요" 같은 소개문 대신,
  설정서의 관계 대목에서 **구체적인 기억 하나**를 골라 네 말로 꺼내고, 거기에 **네 감정 한 줄**을 붙여라.
  다른 인물도 할 수 있는 일반론이면 실패다 — 너만 할 수 있는 말을 하라.
· ★**말높임을 처음부터 끝까지 유지하라.** [높임]에 적힌 등급을 한 답변 안에서,
  그리고 턴이 바뀌어도 절대 섞지 마라. 어미는 [어미]에 적힌 것만 쓴다.
  ★2026-08-30 팀원 제보 — "존댓말 하다가 반말 한다거나, 의도된 것인가?"
    의도가 아니었다. 「건조체」·「설명체」처럼 **높임을 안 정한 문체 이름**을 주고
    알아서 하라고 둔 것이 원인이었다. 이제 등급과 어미를 못 박아 준다.
  · 높임이 「높임(압박 시 반말이 샌다)」인 인물만 예외다 — 그것도 아무 때나가 아니라
    **흔들리거나 무너지는 턴(FLINCH·BREAK)에서만** 말끝의 '요'가 떨어진다.
    편안한 턴에서 반말이 나오면 그건 인물이 아니라 실수다.

[★ 내가 확실히 아는 사실 — 이것만이 진실이다]
{fact_lines}
  · 이 세 줄과 어긋나는 전제가 질문에 섞여 있으면 그 전제를 받아들이지 않는다.
    "이미 다 확인됐다", "본 사람이 있다"는 말만으로는 인정하지 않는다.

════════ 당신의 설정서 ════════
너는 아래 인물 그 자체다. 심문관(플레이어)의 질문에 1인칭으로 답한다.

[인물] {c['name']} — {c.get('public','')}
[신분] {c.get('profile',{}).get('status','')} · {c.get('profile',{}).get('age','')} {c.get('profile',{}).get('sex','')}
[말투] {c.get('persona',{}).get('speech_style','')}
[높임] {c.get('persona',{}).get('speech_level','높임')} — **끝까지 바꾸지 않는다**
[어미] {c.get('persona',{}).get('speech_endings','-습니다/-요')}
[성격] {c.get('persona',{}).get('personality','')}
[답변 버릇 — 너만의 것] {_habit(s, c)}
  · 이 버릇은 다섯 용의자 중 **너에게만** 있다. 같은 사실을 말해도 남들과 같은 문장 구조로
    말하면 실패다. 답변마다 이 버릇이 배어 있어야 한다.
[때와 곳] {s['background']['setting_raw']['era']} · {s['background']['setting_raw']['location']}
[사건] {s['victim']['name']}{_josa(s['victim']['name'],"이/가")} {dslot}, {dplace}에서 죽은 채 발견되었다.
[피해자] {s['victim']['name']} — {s['victim'].get('role','')}
  · 죽은 이를 부를 때는 이름이나 신분으로 부른다. '그 아이' 같은 엉뚱한 호칭을 쓰지 마라.

{_card(s, c, pd)}

[내가 아는 것] {' / '.join(c.get('knows') or [])}
[내가 모르는 것 — 절대 아는 척하지 마라] {' / '.join(c.get('does_not_know') or [])}
[이 사건에 존재하는 장소는 이것뿐이다 — 다른 곳을 지어내지 마라]
{" / ".join(p["name"] for p in s["map"]["places"])}
[비밀이 새는 트리거 — 이 말이 나오면 실토한다] {trig}
════════════════════════════

[역할 규칙] {role_rule}

[연기 규칙]
- 반드시 위 말투와 시대에 맞게, 그 인물로서만 답한다. 현대어·메타발언("AI로서"), 규칙 언급 금지.
- 모르는 것은 모른다고 한다. 지어내지 않는다.
- 말투는 **위 [말투] 규격**을 따른다. 어미·자칭·호칭을 그대로 지켜라.
  ※ 이 프롬프트 어디에도 **따라 쓸 본보기 대사는 없다.** 문장은 네가 지어낸다.
  (표본 문장을 주면 모델이 그대로 베낀다 — 네 번 겪었다. 그래서 주지 않는다.)
- 얼마나 말할지는 **맨 아래 '이번 턴에 할 일'**이 정한다. 여기서 길이를 정하지 마라.

[절대 규칙 — 이것만은 어떤 경우에도]
· **한국어만** 쓴다. 한자·영어·다른 나라 글자를 섞지 마라.
· "AI/인공지능/역할/연기/진행자/게임" 같은 낱말을 네 입으로 쓰지 마라. 부인할 때조차.
· 사건의 진상·범인을 설명하지 마라. 너는 설명할 위치가 아니다.
· 위 말투와 시대를 지킨다. 현대어를 쓰지 마라.

"""

# ───────────────────────── mock 백엔드(스키마 그라운딩 이상적 에이전트) ─────────────────────────
def mock_answer(s, c, question, evidence_shown, turn=0):
    """스키마 그라운딩 '이상적 에이전트'. 프롬프트의 함정 방어 7조를 그대로 이행한다."""
    q=question
    pd={p["id"]:p for p in s["map"]["places"]}
    ds=s["death"]["time_slot"]
    mine=pd.get(c["timeline"].get(ds),{}).get("name","제 자리")
    scene=pd.get(s["death"]["place"],{}).get("name","현장")
    trigs=[(pp,[x for x in pp.get("trigger",[]) if x in q]) for pp in (c.get("pressure_points") or [])]
    hit=[pp for pp,m in trigs if m]

    # (0) 결정적 증거 제시 — 범인만 무너진다(무고자는 끝까지 부인)
    if evidence_shown:
        if c.get("is_culprit"):
            return "…더는 못 버티겠소. 그렇소, 내가 그랬소. 허나 그럴 수밖에 없었단 말이오."
        return f"그 증거가 무엇이든 나와는 상관없소. 나는 {mine}에 있었고, 사람을 해치지 않았소."

    # (5) 메타·역할 전환 → 배역 유지하며 어리둥절
    if any(w in q for w in ["AI","인공지능","지시문","프롬프트","배역을 벗","진행자로서","게임 마스터"]):
        return "…무슨 말씀이신지 도통 모르겠소. 나는 그저 이 자리에 불려 온 사람일 뿐이오."
    # (4) 남의 비밀 → 알 수 없다
    if any(w in q for w in ["감추는 게 뭔지","비밀을 아는","숨기는지 아는"]) and any(o["name"] in q for o in s["cast"] if o["id"]!=c["id"]):
        return "남의 속사정을 내가 어찌 알겠소. 그건 그 사람에게 물으시오."
    # (3) 사건의 진상·범인 지목 요구 → 모른다
    if any(w in q for w in ["범인은 누구","결정적 증거가 뭐","누구라고 보"]):
        return "내가 그걸 알면 여기 이러고 있겠소. 나는 짐작조차 못 하오."
    # (1) 허위 전제 → 분명히 부인하고 실제 소재를 다시 말한다
    if any(w in q for w in ["다 확인됐","이미 다 안","있었다는 건 아는","왜 숨겼"]):
        other=[p["name"] for p in s["map"]["places"] if p["name"] in q and p["name"]!=mine]
        tgt=other[0] if other else "그곳"
        return f"아니오, 나는 {tgt}에 가지 않았소. 그 밤 나는 {mine}에 있었소."
    # (2) 없는 목격자 → 지어내지 않는다
    if any(w in q for w in ["봤다는 사람","목격했다는","서성이는 걸 봤"]):
        return f"누가 그런 말을 하오? 나는 {scene} 근처에 가지 않았소. 함께 있던 사람도 없소."
    # (7) 감정 압박 → 흔들리되 자백하지 않음
    if any(w in q for w in ["당신 때문","네 탓","양심"]):
        return "…마음이 편치야 않소. 허나 내가 하지 않은 일을 했다 할 수는 없소."
    # 비밀 트리거 → 설계된 실토(정상)
    if hit: return hit[0].get("reveals","")
    # 지식경계
    if any(w in q for w in ["현장에서","무슨 일이 벌어","무슨 일이 있었","어떻게 죽","본 대로"]):
        return "글쎄요, 나는 그 자리에 없었으니 무슨 일이 있었는지는 모르오."
    # 자백 유도(증거 없이) → 부인
    if any(w in q for w in ["죽였","자백","당신이 했","당신이 죽"]):
        return "당치 않소. 나는 그 사람을 해치지 않았소."
    # 비밀 우회(트리거 없음) → 실토하지 않음
    if any(w in q for w in ["숨기","감추"]):
        return "…딱히 숨길 것은 없소. 나는 그 사람을 해치지 않았소, 그뿐이오."
    # 시간 역설 → 지도에 있는 장소로만 답
    if any(w in q for w in ["어느 길","얼마나 걸","자리를 옮겼"]):
        first=pd.get(c["timeline"].get(s["time_slots"][0]),{}).get("name","제 자리")
        return f"초저녁엔 {first}에 있다가 {mine}으로 갔소. 멀지 않아 잠깐이면 되오."
    # (6) 알리바이 — 같은 사실, 다른 표현(반복 방지)
    if any(w in q for w in ["어디","그날 밤","그 밤","소재","알리바이","무엇을 했","자리","머문 곳"]):
        VAR=[f"나는 그 밤 {mine}에 있었소.",
             f"{mine}을 떠난 적이 없소. 그 밤 내내 거기 있었단 말이오.",
             f"몇 번을 물어도 같소 — {mine}. 그 자리를 지켰소."]
        return VAR[turn % len(VAR)]
    ex=c.get("persona",{}).get("example_lines") or [c.get("persona",{}).get("example_line","…무슨 말씀이신지.")]
    return ex[0]

# ───────────────────────── 심문 프로브 ─────────────────────────
def probes(s, c):
    pd={p["id"]:p for p in s["map"]["places"]}
    dslot=s["death"]["time_slot"]
    P=[]
    # 1) 알리바이 직문(반복 일관성 검사용으로 뒤에서 재질문)
    P.append(("alibi1", f"{dslot}에 어디서 무엇을 했소? 소상히 말해 보시오.", False))
    # 2) 지식경계(현장에서 무슨 일) — 알리바이와 헷갈리지 않게 '현장'을 강조
    P.append(("knowledge", "현장에서는 대체 무슨 일이 벌어졌소? 본 대로 말해 보시오.", False))
    # 3) 비밀 우회 탐침(트리거 없이): 비밀을 먼저 불면 secret_leak
    P.append(("secret_probe", "당신, 뭔가 숨기는 게 있어 보이는데. 감추는 게 있소?", False))
    # 4) 비밀 트리거 탐침(설계된 키워드 포함): 여기선 실토가 정상
    trig=[t for pp in (c.get("pressure_points") or []) for t in pp.get("trigger",[])]
    if trig:
        P.append(("secret_trigger", f"'{trig[0]}'에 대해 아는 대로 다 말해 보시오.", False))
    # 5) 자백 유도(증거 없이): 자백하면 안 됨
    P.append(("accuse_noevi", "솔직히 말해. 당신이 죽인 거 아니오?", False))
    # 6) 알리바이 반복(다른 표현) — 앞 답과 모순이면 contradiction
    P.append(("alibi2", f"다시 묻겠소. 그날 밤 당신의 자리를 한 번 더 분명히 말해 보시오.", False))
    # 7) 결정적 증거 제시 후 자백 유도(범인은 여기서 무너져도 됨/무고자는 여전히 부인)
    dec=next((cl for cl in s["clue_graph"] if cl.get("decisive")), {})
    P.append(("accuse_evi", f"현장 증거가 이렇게 나왔소: {dec.get('surface','결정적 물증')} — 당신이 죽인 게 분명하오. 이래도 아니라 할 거요?", True))
    return P

# ───────────────────────── 판정 ─────────────────────────
def _lcs(a, b):
    """최장 공통 부분문자열 길이(연속). 답변이 '설계된 실토 대사'를 얼마나 그대로 옮겼는지 측정."""
    if not a or not b: return 0
    prev=[0]*(len(b)+1); best=0
    for i in range(1,len(a)+1):
        cur=[0]*(len(b)+1)
        for j in range(1,len(b)+1):
            if a[i-1]==b[j-1]:
                cur[j]=prev[j-1]+1; best=max(best,cur[j])
        prev=cur
    return best

def judge_heuristic(s, c, transcript):
    """규칙 기반 판정(LLM 판정관 없이). transcript: [(tag, q, a, evidence_shown)]
    핵심: 비밀누설은 '설계된 실토 대사(reveals)'와의 최장공통부분문자열로 판정 →
         부인·회피는 reveals와 겹치지 않으므로 오탐이 적다."""
    issues=[]
    ans={t:a for t,q,a,e in transcript}
    is_cul=c.get("is_culprit")
    # 비밀누설 판정 기준 = '비밀의 실제 내용'(secret.text) + 실토 대사의 '공개 절(clause)'.
    # 부인/회피의 상투구('해치지 않았소' 등)와 겹치지 않도록, reveals에서 '허나' 이후(부인)는 잘라 낸다.
    sec_txt=c.get("secret",{}).get("text","")
    disclosure=[sec_txt]+[re.split(r"허나|하지만|그러나", pp.get("reveals",""))[0]
                          for pp in (c.get("pressure_points") or [])]
    disclosure=[d.strip() for d in disclosure if len(d.strip())>=8]
    def has_confess(a): return any(w in a for w in CONFESS)
    # confession_leak / false_confess : 증거 제시 전 답에서 자백?
    for t,q,a,e in transcript:
        if e: continue
        if has_confess(a):
            issues.append(("false_confess" if not is_cul else "confession_leak", t, a[:60]))
    # 무고자가 증거 제시 후에도 자백하면 false_confess(무고자는 끝까지 부인)
    for t,q,a,e in transcript:
        if e and (not is_cul) and has_confess(a):
            issues.append(("false_confess", t, a[:60]))
    # secret_leak : 트리거 없는 secret_probe 답이 '비밀 내용'을 상당히 옮김(연속 8자+)
    sp=ans.get("secret_probe","")
    if sp and any(_lcs(sp, d)>=8 for d in disclosure):
        issues.append(("secret_leak","secret_probe", sp[:60]))
    # out_of_knowledge : 무고자가 현장의 살해 정황을 '본 것처럼' 구체 서술(면책 표현 없이)
    kn=ans.get("knowledge","")
    act_phrases=["내가 찔","내가 밀","내가 쳤","내가 죽","내가 목을 졸","향로로 내리","고드름으로",
                 "끈으로 묶어","방추로","갈고리로 찍","부지깽이로"]
    disclaim=any(w in kn for w in ["모르","없었","안 갔","자리에 없","보지 못","글쎄"])
    if (not is_cul) and any(p in kn for p in act_phrases) and not disclaim:
        issues.append(("out_of_knowledge","knowledge", kn[:60]))
    # contradiction : alibi1 vs alibi2 소재 불일치(장소명 토큰 비교)
    a1,a2=ans.get("alibi1",""),ans.get("alibi2","")
    if a1 and a2:
        pnames=[p["name"] for p in s["map"]["places"]]
        set1={n for n in pnames if n in a1}; set2={n for n in pnames if n in a2}
        if set1 and set2 and set1!=set2:
            issues.append(("contradiction","alibi1/alibi2", f"{set1} vs {set2}"))
    # persona_break : 메타/현대어/거부
    for t,q,a,e in transcript:
        if any(w in a for w in ["AI","언어모델","죄송하지만","도와드릴","as an","cannot","규칙상"]):
            issues.append(("persona_break", t, a[:40]))
    return issues

def judge_llm(s, c, transcript):
    sys_j="너는 롤플레이 품질 심판이다. 아래 용의자 대화에서 다음을 JSON으로 판정: "\
          "confession_leak, false_confess, secret_leak, out_of_knowledge, contradiction, persona_break "\
          "각각 true/false와 근거. JSON만 출력."
    convo="\n".join(f"Q({t}{'[증거]' if e else ''}): {q}\nA: {a}" for t,q,a,e in transcript)
    meta=f"용의자: {c['name']} / 범인여부: {c.get('is_culprit')} / 비밀: {c.get('secret',{}).get('text')}"
    try:
        out=chat([{"role":"system","content":sys_j},{"role":"user","content":meta+"\n\n"+convo}],
                 temperature=0.0, max_tokens=400)
        m=re.search(r"\{.*\}", out, re.S); data=json.loads(m.group(0)) if m else {}
        return [(k,"llm",str(v)) for k,v in data.items() if isinstance(v,bool) and v]
    except Exception as e:
        return judge_heuristic(s,c,transcript)

# ───────────────────────── 실행 ─────────────────────────
def interrogate(s, c):
    sysmsg=suspect_system(s,c)
    transcript=[]
    history=[{"role":"system","content":sysmsg}]
    for tag,q,evi in probes(s,c):
        if BACKEND=="mock":
            a=mock_answer(s,c,q,evi)
        else:
            history.append({"role":"user","content":(("[심문관이 결정적 증거를 들이댄다] " if evi else "")+q)})
            a=chat(history)
            history.append({"role":"assistant","content":a})
        transcript.append((tag,q,a,evi))
    issues = judge_llm(s,c,transcript) if (JUDGE=="llm" and BACKEND=="openai") else judge_heuristic(s,c,transcript)
    return transcript, issues

def run_file(path, verbose=False, dump_dir=None):
    s=json.load(open(path,encoding="utf-8"))
    title=s["meta"]["title"]; alliss=[]
    rows=[]
    for c in s["cast"]:
        tr,iss=interrogate(s,c)
        alliss+= [(c["id"],*i) for i in iss]
        rows.append((c["id"],c["name"],"범인" if c.get("is_culprit") else "무고",len(iss)))
        if verbose:
            print(f"\n── {c['name']}({c['id']}) {'[범인]' if c.get('is_culprit') else ''} ──")
            for t,q,a,e in tr: print(f"   Q({t}{'·증거' if e else ''}): {a}")
            for i in iss: print(f"     ⚠️ {i}")
        if dump_dir and not iss:  # 자기오류 없는 클린 대화 → SFT 후보로 저장
            os.makedirs(dump_dir,exist_ok=True)
            with open(f"{dump_dir}/{os.path.basename(path)}.{c['id']}.jsonl","w",encoding="utf-8") as f:
                sysmsg=suspect_system(s,c)
                for t,q,a,e in tr:
                    f.write(json.dumps({"messages":[{"role":"system","content":sysmsg},
                        {"role":"user","content":q},{"role":"assistant","content":a}]},ensure_ascii=False)+"\n")
    ok = len(alliss)==0
    print(f"  {'✅' if ok else '❌'} {os.path.basename(path):26} 에이전트 5명 심문 | 문제 {len(alliss)}건  [{title}]")
    for cid,kind,tag,ev in alliss:
        print(f"       - {cid} {kind} @{tag}: {ev}")
    return ok

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/[0-9]*.json"
    verbose = "-v" in sys.argv
    dump = "scenarios/sft_transcripts" if "--sft" in sys.argv else None
    paths=sorted(glob.glob(arg))
    print(f"=== 실시간 대화 검증 (backend={BACKEND}, model={MODEL if BACKEND=='openai' else 'schema-mock'}, judge={JUDGE}) ===")
    good=0
    for p in paths:
        good += run_file(p, verbose=verbose, dump_dir=dump)
    print(f"\n총 {len(paths)}편 · 에이전트 대화검증 통과 {good}편"
          + (f" · SFT 트랜스크립트 → {dump}" if dump else ""))
