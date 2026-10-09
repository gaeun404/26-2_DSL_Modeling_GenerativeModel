"""
동기 자유서술 채점기.
1) 키워드 매칭(오프라인, 빠름): solution.motive_keywords 중 2개↑ 적중 or motive_label 포함 → 정답
2) 애매하면 LLM 보조 판정(선택, API 있을 때)
사용:
  from score_motive import score_motive
  ok, detail = score_motive(scenario, "약재 횡령이 들킬까봐 죽였다")
"""
import json, re

def _norm(t): return re.sub(r"\s+", "", t)

def score_motive(sc, player_text, use_llm=True):
    sol = sc.get("solution", {})
    kws = sol.get("motive_keywords", [])
    label = sol.get("motive_label", "")
    t = _norm(player_text)
    hits = [k for k in kws if _norm(k) in t]
    # 1) 오프라인 키워드 규칙
    if label and _norm(label) in t:
        return True, f"정답 동기 라벨 '{label}' 포함"
    if len(hits) >= 2:
        return True, f"핵심어 {hits} 적중"
    if len(hits) == 1:
        # 1개면 애매 → LLM 보조
        if not use_llm:
            return False, f"핵심어 {hits} 1개(부족)"
    # 2) LLM 보조 판정
    if use_llm:
        try:
            import anthropic
            client = anthropic.Anthropic()
            prompt = (f"추리게임 동기 채점. 정답 동기 라벨='{label}', 핵심어={kws}, "
                      f"정답 설명='{sol.get('reason','')[:200]}'. "
                      f"플레이어가 적은 동기: '{player_text}'. "
                      "플레이어가 '왜 죽였는가'의 핵심을 맞혔으면 correct=true. "
                      "표현이 달라도 의미가 같으면 정답. JSON만: {\"correct\": true/false, \"why\":\"한줄\"}")
            r = client.messages.create(model="claude-sonnet-4-5", max_tokens=200,
                                       messages=[{"role":"user","content":prompt}])
            txt = r.content[0].text; a,b = txt.find("{"), txt.rfind("}")
            res = json.loads(txt[a:b+1])
            return bool(res.get("correct")), "LLM판정: " + res.get("why","")
        except Exception as e:
            return len(hits) >= 1, f"LLM 불가({type(e).__name__}), 키워드 {hits}"
    return False, "동기 불일치"

if __name__ == "__main__":
    import sys
    sc = json.load(open(sys.argv[1] if len(sys.argv)>1 else "scenario3.json", encoding="utf-8"))
    print("정답 라벨:", sc["solution"].get("motive_label"), "| 핵심어:", sc["solution"].get("motive_keywords"))
    for test in ["약재를 횡령한 게 들킬까 봐", "돈 때문에", "복수하려고", "약재 횡령이 발각될 위기라서 은폐하려고"]:
        ok, d = score_motive(sc, test, use_llm=False)
        print(f"  '{test}' → {'⭕' if ok else '❌'}  ({d})")
