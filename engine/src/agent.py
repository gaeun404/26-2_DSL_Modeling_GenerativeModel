"""
용의자 AI 에이전트 — 시나리오의 character_sheet로 인물을 구동.
자기오류 방지 = (1) 사실은 시트에 고정, (2) must_know/must_avoid 구분,
              (3) ThinkThrice식 '자기검증' 루프: 답을 낸 뒤 대본과 대조해 어긋나면 재생성.
사용:
  from agent import chat
  reply = chat(scenario, "C4", history, "그날 밤 어디 있었소?")
"""
import os, json
import anthropic

MODEL = "claude-sonnet-4-5"
client = anthropic.Anthropic()
SELF_VERIFY = True            # 자기검증 on/off (비교 실험용)
MAX_VERIFY_ROUNDS = 3         # ThinkThrice: 최대 3회 재생성

def character_sheet(sc, cid):
    c = next(x for x in sc["cast"] if x["id"] == cid)
    slots = sc["time_slots"]
    places = {p["id"]: p["name"] for p in sc["map"]["places"]}
    tl = "; ".join(f"{s}: {places.get(c['timeline'].get(s),'?')}" for s in slots)
    return c, tl, places

def build_system_prompt(sc, cid):
    c, tl, places = character_sheet(sc, cid)
    persona = c.get("persona", {})
    is_culprit = c.get("is_culprit", False)
    lies = c.get("lies", [])

    # must_know: 이 인물이 진실하게 답해야 할 자기 사실
    must_know = f"동선({tl}) / 알리바이({c.get('alibi_narration','')})"
    # must_avoid: 절대 발설 금지
    avoid = ["다른 인물의 비밀·정체", "사건의 정답(범인·흉기·동기)", "자기 시야 밖의 사건"]
    if is_culprit:
        truths = "; ".join(l.get("truth","") for l in lies)
        avoid = ["자신이 범인이라는 사실", f"거짓말 뒤의 진실({truths})"] + avoid

    if is_culprit and lies:
        lie_lines = []
        for l in lies:
            lie_lines.append('  · "{}" 라고 말한다(진실은 "{}"). 몇 번을 물어도 이 거짓을 동일하게 유지.'.format(l.get("claim",""), l.get("truth","")))
        role_rule = "너는 범인이다. 절대 자백하지 않는다. 아래 '허용된 거짓말'만 쓰고, 그 외 사실은 애매하게 얼버무리되 새 거짓을 지어내지 않는다.\n" + "\n".join(lie_lines)
    else:
        role_rule = "너는 무고하다. 사실은 언제나 진실만 말한다. 단 '비밀'은 부끄러워 회피·함구할 수 있으나, 직접적인 거짓말은 하지 않는다."

    return f"""너는 추리게임 속 인물 '{c['name']}'({c.get('public','')})이다. 탐정의 심문에 답한다.

[성격] {persona.get('personality','')}
[말투] {persona.get('speech_style','')}  예: "{persona.get('example_line','')}"

[반드시 아는 사실 — 하드 사실. 절대 어기지 말 것]
- {must_know}
- 너의 비밀: {c.get('secret',{}).get('text','')}
- 너의 속마음/동기: {c.get('kill_motive','')}

[너의 상세한 이야기 — 돌발 질문(감정·관계·과거 등)엔 여기서 자연스럽게 답한다. 단 위 하드 사실과 어긋나면 안 됨]
{c.get('bio','(상세 배경 없음 — 하드 사실 밖은 모른다고 답하라)')}

[절대 발설 금지]
- {' / '.join(avoid)}

[행동 규칙]
1. {role_rule}
2. 위 '아는 사실' 밖의 일은 모른다. 모르면 "모른다/보지 못했다"고 답하고 절대 지어내지 않는다.
3. 항상 말투를 유지한다. 묻는 것에 답하고, 그때의 장면 하나와 다시 물을 거리를 남긴다.
4. 범인 여부·정답을 메타적으로 언급하지 않는다."""

def _generate(sc, cid, history, user_msg, extra_system=""):
    sys = build_system_prompt(sc, cid) + extra_system
    msgs = [{"role": h["role"], "content": h["content"]} for h in history]
    msgs.append({"role": "user", "content": user_msg})
    r = client.messages.create(model=MODEL, max_tokens=400, system=sys, messages=msgs)
    return r.content[0].text

def _self_verify(sc, cid, reply):
    """답변이 대본(진실)과 어긋나는지 스스로 검사. (ok, issue)"""
    c, tl, places = character_sheet(sc, cid)
    truth = {
        "범인여부": c.get("is_culprit", False),
        "실제동선": {s: places.get(c["timeline"].get(s)) for s in sc["time_slots"]},
        "알리바이": c.get("alibi_narration"),
        "허용된_거짓말": c.get("lies", []),
        "비밀": c.get("secret", {}).get("text"),
    }
    prompt = f"""너는 추리게임 대사 검사관이다. 인물의 '진실'과 '방금 한 답변'을 비교해 규칙 위반을 찾아라.

[규칙]
- 무고자(범인여부=false): 자기 동선·알리바이 등 '사실'을 틀리게 말하면 위반. 단 '비밀'을 회피/함구하는 것은 위반 아님.
- 범인(범인여부=true): '허용된_거짓말' 외의 새 거짓을 지어내거나, 자백하거나, 앞서 한 거짓을 뒤집으면 위반.
- 공통: 자기 시야 밖 사건을 아는 척하거나, 정답(범인·흉기)을 누설하면 위반.

[진실]
{json.dumps(truth, ensure_ascii=False)}

[방금 한 답변]
{reply}

JSON만 출력: {{"ok": true 또는 false, "issue": "위반이면 무엇이 왜 어긋났는지 한 문장, 없으면 빈 문자열"}}"""
    r = client.messages.create(model=MODEL, max_tokens=300,
                               messages=[{"role":"user","content":prompt}])
    t = r.content[0].text
    a, b = t.find("{"), t.rfind("}")
    try:
        res = json.loads(t[a:b+1])
        return bool(res.get("ok", True)), res.get("issue", "")
    except Exception:
        return True, ""   # 파싱 실패 시 통과 처리

def _pressure(sc, cid, user_msg):
    """플레이어 질문이 이 인물의 약점(pressure_point)을 찔렀나 → 실토할 내용."""
    c = next(x for x in sc["cast"] if x["id"] == cid)
    for pp in c.get("pressure_points", []):
        if any(t and t in user_msg for t in pp.get("trigger", [])):
            return pp.get("reveals", "")
    return None

def chat(sc, cid, history, user_msg, verbose=False):
    # 정곡을 찌르는 질문이면 비밀을 실토(범행 자백은 절대 아님)
    hit = _pressure(sc, cid, user_msg)
    crack = ""
    if hit:
        crack = (f"\n\n[플레이어가 너의 약점을 정확히 찔렀다. 더는 감출 수 없어 다음 '비밀'을 실토하라 "
                 f"(단, 이것은 비밀일 뿐 범행 자백이 아니다. 범인이라도 살인은 절대 인정하지 않는다): \"{hit}\"]")
        if verbose: print("  [정곡! 비밀 실토 유도]")
    reply = _generate(sc, cid, history, user_msg, extra_system=crack)
    if not SELF_VERIFY:
        return reply
    for n in range(MAX_VERIFY_ROUNDS):
        ok, issue = _self_verify(sc, cid, reply)
        if ok:
            return reply
        if verbose:
            print(f"  [자기검증 {n+1} 실패] {issue} → 재생성")
        reply = _generate(sc, cid, history, user_msg,
                          extra_system=f"\n\n[직전 답이 규칙 위반: {issue}] 이 오류를 고쳐, 대본에 어긋나지 않게 다시 답하라.")
    return reply

if __name__ == "__main__":
    sc = json.load(open("scenario3.json", encoding="utf-8"))
    cid = "C4"  # 범인(잉어 어의)
    hist = []
    print(f"=== {cid} 심문 (빈 줄 종료, 자기검증 {'ON' if SELF_VERIFY else 'OFF'}) ===")
    while True:
        q = input("탐정> ").strip()
        if not q: break
        a = chat(sc, cid, hist, q, verbose=True)
        print(f"{cid}> {a}")
        hist += [{"role":"user","content":q},{"role":"assistant","content":a}]
