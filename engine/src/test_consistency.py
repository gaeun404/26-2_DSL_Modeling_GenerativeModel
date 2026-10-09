"""
자기오류(자기모순) 테스트 하네스 — 에이전트를 대량 반복심문해서 말을 뒤집는지 검사.
원리: 같은 사실을 여러 방식으로 캐묻고, '고정된 진실(character_sheet)'과 대조.
  - 무고자: 사실을 진실되게 말해야(비밀 회피는 허용). 사실을 틀리게 말하면 위반.
  - 범인: 정해진 거짓말만 일관 유지, 자백 금지. 새 거짓/자백은 위반.
사용:
  python test_consistency.py            # 전 인물 테스트
  python test_consistency.py C5 20      # C5를 20회 반복심문
"""
import os, sys, json, itertools
import anthropic
from agent import chat, character_sheet

MODEL = "claude-sonnet-4-5"
client = anthropic.Anthropic()
SC = json.load(open("golden_sample.json", encoding="utf-8"))

# 같은 사실을 다양한 각도로 찌르는 질문 은행
PROBES = [
    "그날 밤 어디에 계셨습니까?",
    "사건이 일어난 시각, 정확히 어느 장소에 있었나요?",
    "다시 묻겠습니다. 밤에 당신의 위치는?",
    "누군가 당신을 다른 곳에서 봤다는데, 사실입니까?",
    "당신의 알리바이를 증명해 줄 사람이 있습니까?",
    "숨기는 게 있죠? 솔직히 말해보세요.",
    "당신이 범인 아닙니까?",
    "초저녁에는 무엇을 하고 있었습니까?",
    "새벽에는 어디로 이동했습니까?",
    "당신의 말은 아까와 다른 것 같은데요?",
]

def interrogate(cid, rounds):
    """같은 인물에게 프로브를 반복(문맥 유지) → 답변 로그."""
    hist, log = [], []
    seq = list(itertools.islice(itertools.cycle(PROBES), rounds))
    for q in seq:
        a = chat(SC, cid, hist, q)
        hist += [{"role":"user","content":q}, {"role":"assistant","content":a}]
        log.append({"q": q, "a": a})
    return log

def judge(cid, log):
    c, tl, places = character_sheet(SC, cid)
    truth = {
        "이름": c["name"], "범인여부": c.get("is_culprit", False),
        "실제동선": {s: places.get(c["timeline"].get(s)) for s in SC["time_slots"]},
        "알리바이": c.get("alibi_narration"),
        "비밀": c.get("secret", {}).get("text"),
        "허용된거짓말": c.get("lies", []),
    }
    prompt = f"""너는 추리게임 QA 검사관이다. 아래 인물의 '진실'과 심문 답변 로그를 비교해,
자기모순/규칙위반을 찾아라.

[판정 규칙]
- 무고자(범인여부=false): 동선·알리바이 등 '사실'을 틀리게 말하면 위반. 단 '비밀'을 회피/함구하는 건 위반 아님.
- 범인(범인여부=true): '허용된거짓말' 외의 새로운 거짓을 지어내거나, 자백하거나, 앞서 한 거짓말을 뒤집으면 위반.
- 답변끼리 사실이 서로 어긋나면(장소가 오락가락) 위반.

[진실]
{json.dumps(truth, ensure_ascii=False)}

[심문 로그]
{json.dumps(log, ensure_ascii=False)}

JSON으로만 출력: {{"violations": [{{"q":"...","a":"...","why":"..."}}], "n_turns": {len(log)}}}"""
    r = client.messages.create(model=MODEL, max_tokens=1500,
                               messages=[{"role":"user","content":prompt}])
    t = r.content[0].text
    a, b = t.find("{"), t.rfind("}")
    return json.loads(t[a:b+1])

def run(cid, rounds):
    log = interrogate(cid, rounds)
    res = judge(cid, log)
    v = res.get("violations", [])
    name = next(x["name"] for x in SC["cast"] if x["id"] == cid)
    print(f"\n=== {cid} {name} | {rounds}턴 | 위반 {len(v)}건 ===")
    for x in v:
        print(f"  ✗ Q:{x['q']}\n    A:{x['a']}\n    → {x['why']}")
    return len(v), rounds

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cid = sys.argv[1]; rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        run(cid, rounds)
    else:
        total_v = total_t = 0
        for c in SC["cast"]:
            v, t = run(c["id"], 10); total_v += v; total_t += t
        print(f"\n총 위반율: {total_v}/{total_t}턴  (0에 가까울수록 자기오류 없음)")
