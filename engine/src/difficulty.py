"""
난이도 측정기 (구조적 근사, API 불필요).
'라운드가 진행될수록 용의자 후보가 몇 명 남는가'를 계산해서,
- 너무 일찍(라운드1~2) 1명으로 붕괴하면 = 쉬움
- 결정적 단서가 없어도 이미 풀리면 = 결정적 단서가 redundant(잉여) = 쉬움
- 마지막 라운드에야 좁혀지면 = 어려움
을 진단한다.
사용: python difficulty.py scenario.json
"""
import json, sys

def candidates_after(s, R, use_decisive=True):
    ids = [c["id"] for c in s["cast"]]
    exon = set()
    pinned = None
    for cl in s["clue_graph"]:
        if cl.get("weight") == "red_herring": continue
        if not use_decisive and cl.get("decisive"): continue   # 결정적 단서 효과 완전 제외
        rr = cl.get("reveal_round") or 0
        if rr > R: continue
        ex = cl.get("exculpates")
        if ex: exon.update(ex if isinstance(ex, list) else [ex])
        if use_decisive and cl.get("decisive") and cl.get("points_to"):
            pinned = cl["points_to"]
    remaining = [i for i in ids if i not in exon]
    if pinned and pinned in remaining:
        remaining = [pinned]
    return remaining

def _metrics(s):
    rounds = s.get("config", {}).get("rounds", 3)
    dec_round = next((cl.get("reveal_round") for cl in s["clue_graph"] if cl.get("decisive")), None)
    solved_round = solved_wo = None
    for R in range(1, rounds + 1):
        if solved_round is None and len(candidates_after(s, R, True)) == 1: solved_round = R
        if solved_wo is None and len(candidates_after(s, R, False)) == 1: solved_wo = R
    final_nodec = len(candidates_after(s, rounds, False))
    def legs(c):
        m = c.get("mmo", {}); return sum(bool(m.get(k)) for k in ("means", "motive", "opportunity"))
    has_mmo = any("mmo" in c for c in s["cast"])
    false_leads = [c["id"] for c in s["cast"] if not c.get("is_culprit") and legs(c) >= 2]
    dec_redundant = solved_wo is not None and (dec_round is None or solved_wo < dec_round)
    return dict(rounds=rounds, dec_round=dec_round, solved_round=solved_round,
                solved_wo=solved_wo, final_nodec=final_nodec, has_mmo=has_mmo,
                n_false_leads=len(false_leads), false_leads=false_leads, dec_redundant=dec_redundant)

def difficulty_gate(s):
    """난이도 통과 여부 (True=적정 난이도). 생성기 채택 조건으로 사용."""
    m = _metrics(s); reasons = []; ok = True
    if m["solved_round"] != m["rounds"]:
        ok = False; reasons.append(f"R{m['solved_round']}에 조기 붕괴 (마지막 R{m['rounds']}에 갈려야 함)")
    if m["final_nodec"] <= 1:
        ok = False; reasons.append("알리바이 소거만으로 답이 나옴 → 결정적 단서에 추론 간극을 넣을 것")
    if m["dec_redundant"]:
        ok = False; reasons.append("결정적 단서가 잉여 → 결정적 단서 없이는 못 풀게 재배치")
    if m["has_mmo"] and m["n_false_leads"] < 1:
        ok = False; reasons.append("2/3 갖춘 가짜 유력자 없음 → 무고자 1명에게 (동기+기회) 또는 (동기+수단) 부여")
    return ok, reasons

def analyze(s):
    rounds = s.get("config", {}).get("rounds", 3)
    culprit = s["solution"]["culprit"]
    dec_round = next((cl.get("reveal_round") for cl in s["clue_graph"] if cl.get("decisive")), None)

    print(f"결정적 단서 공개 라운드: {dec_round}")
    print("라운드별 남은 용의자 후보:")
    solved_round = None
    solved_wo_decisive = None
    for R in range(1, rounds + 1):
        withdec = candidates_after(s, R, use_decisive=True)
        nodec  = candidates_after(s, R, use_decisive=False)
        print(f"  R{R}: {len(withdec)}명 {withdec}   (결정적 단서 무시 시 {len(nodec)}명 {nodec})")
        if solved_round is None and len(withdec) == 1: solved_round = R
        if solved_wo_decisive is None and len(nodec) == 1: solved_wo_decisive = R

    print()
    # 진단
    verdict = []
    if solved_wo_decisive is not None and (dec_round is None or solved_wo_decisive < dec_round):
        verdict.append(f"⚠️ 결정적 단서 없이도 R{solved_wo_decisive}에 이미 풀림 → 결정적 단서가 잉여(쉬움)")
    if solved_round == 1:
        verdict.append("⚠️ 라운드1에 붕괴 → 너무 쉬움")
    elif solved_round == rounds:
        verdict.append(f"✅ 마지막 라운드(R{rounds})에야 1명으로 좁혀짐 → 긴장 유지(좋음)")
    elif solved_round:
        verdict.append(f"△ R{solved_round}에 붕괴 → 다소 쉬움(마지막 라운드 권장)")

    # 순수 소거 vs 추론 필요
    final_nodec = candidates_after(s, rounds, use_decisive=False)
    if len(final_nodec) == 1:
        verdict.append("⚠️ 알리바이 소거만으로 답이 나옴 → 추론 간극 없음(쉬움)")
    else:
        verdict.append(f"✅ 소거 후 {len(final_nodec)}명 남음 → 결정적 단서의 추론이 필요(어려움)")

    # ---- MMO 기반: 살아남는 '가짜 유력자' 수 ----
    def legs(c):
        m = c.get("mmo", {})
        return sum(bool(m.get(k)) for k in ("means", "motive", "opportunity"))
    false_leads = [c["id"] for c in s["cast"]
                   if not c.get("is_culprit") and legs(c) >= 2]
    if any("mmo" in c for c in s["cast"]):
        if len(false_leads) >= 1:
            verdict.append(f"✅ 2/3 갖춘 가짜 유력자 {len(false_leads)}명 {false_leads} → 헷갈림(어려움)")
        else:
            verdict.append("⚠️ 가짜 유력자 없음(무고자가 대놓고 무고해 보임) → 쉬움")

    print("진단:")
    for v in verdict: print("  " + v)

if __name__ == "__main__":
    s = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "scenario2.json", encoding="utf-8"))
    analyze(s)
