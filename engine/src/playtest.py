# -*- coding: utf-8 -*-
"""
자동 플레이테스트(결정적, API 불필요) — '합리적 플레이어'가 라운드를 진행하며
용의자를 어떻게 좁혀 가는지 추적해, 이 사건이 '제대로 풀리는지'를 판정.
- 라운드별 공개 단서 → 후보 소거 추적
- 마지막 라운드에서만 1명으로 확정되는가(조기붕괴/미해결 방지)
- 가짜 유력자가 결정적 단서 직전까지 살아남는가(추론 간극)
- 범인의 거짓 알리바이가 교차검증으로 잡히는가
판정: PLAYABLE(정상 해결) / UNPLAYABLE(문제) + 사람이 읽는 플레이 트레이스.

사용: python playtest.py out/G_전우치전.json     # 한 편 상세 트레이스
     python playtest.py "scenarios/*.json"            # 여러 편 요약 판정
"""
import json, sys, glob
from difficulty import candidates_after

def name_of(s, cid):
    for c in s["cast"]:
        if c["id"] == cid: return c.get("name", cid)
    return cid

def trace(s, verbose=True):
    rounds = s["config"]["rounds"]
    culprit = s["solution"]["culprit"]
    cast_ids = [c["id"] for c in s["cast"]]
    reasons = []; ok = True

    if verbose:
        print(f"\n{'='*60}\n[{s['meta'].get('title','')}] 원작 {s['meta'].get('origin','')} · 트릭 {s.get('trick',{}).get('name','-')}")
        print(f"피해자 {s['victim']['name']} — {s['death'].get('place')}에서 {s['death'].get('time_slot')}에 사망")
        print(f"용의자: " + ", ".join(f"{c['id']}={c['name']}" for c in s['cast']))
        cs = [cl for cl in s["clue_graph"] if cl.get("channel")=="crime_scene"]
        print(f"\n[현장 검시] {s['death'].get('scene_description','')[:80]}...")
        for cl in cs:
            print(f"  · {cl['surface'][:70]}")

    trace_rows = []
    for R in range(1, rounds+1):
        withdec = candidates_after(s, R, True)
        nodec   = candidates_after(s, R, False)
        newly = [cl for cl in s["clue_graph"]
                 if (cl.get("reveal_round") or 0) == R and cl.get("channel") in ("spine","crime_scene")]
        trace_rows.append((R, withdec, nodec, newly))
        if verbose:
            print(f"\n[라운드 {R}] 공개 단서:")
            for cl in newly:
                w = cl.get("weight")
                tag = {"exculpating":"배제","incriminating":"지목","weapon":"흉기","red_herring":"교란"}.get(w, w)
                print(f"  · ({tag}) {cl['surface'][:66]}")
            nm = [name_of(s, i) for i in withdec]
            print(f"  → 이 시점 남은 용의자 {len(withdec)}명: {nm}")
            print(f"    (결정적 단서 무시하면 {len(nodec)}명: {[name_of(s,i) for i in nodec]})")

    # ── 판정 ──
    solved_round = next((R for R,wd,_,_ in trace_rows if len(wd)==1), None)
    final_nodec = trace_rows[-1][2]
    if solved_round != rounds:
        ok=False; reasons.append(f"마지막 R{rounds} 아닌 R{solved_round}에 확정(조기붕괴/미해결)")
    if solved_round and trace_rows[solved_round-1][1] != [culprit]:
        ok=False; reasons.append("확정된 용의자가 정답 범인이 아님")
    if len(final_nodec) <= 1:
        ok=False; reasons.append("알리바이 소거만으로 풀림(추론 간극 없음)")
    # 가짜 유력자(결정적 직전까지 생존)
    survivors = trace_rows[-1][2]  # nodec at final = 결정적 없이 남는 후보
    false_alive = [i for i in survivors if i != culprit]
    if not false_alive:
        ok=False; reasons.append("결정적 단서 직전 살아남는 가짜 유력자 없음")
    # 범인 거짓말 교차검증
    catchable = True
    for c in s["cast"]:
        if c.get("is_culprit"):
            for l in (c.get("lies") or []):
                fp = l.get("false_place")
                if fp:
                    wit = [x["id"] for x in s["cast"] if x["id"]!=c["id"] and x.get("timeline",{}).get(s["death"]["time_slot"])==fp]
                    if not wit: catchable=False
    if not catchable:
        ok=False; reasons.append("범인 거짓 알리바이를 교차검증할 목격자 없음")

    if verbose:
        print(f"\n[해결 과정] 범인 {name_of(s,culprit)} 지목.")
        print(f"  · 결정적 단서 없이 끝까지 남는 가짜 유력자: {[name_of(s,i) for i in false_alive]}")
        print(f"  · 마지막 라운드 결정적 단서가 이 가짜 유력자를 배제하고 범인을 확정")
        print(f"  · 흉기 {s['solution'].get('weapon')} / 동기 '{s['solution'].get('motive_label')}'")
        print(f"\n판정: {'✅ PLAYABLE (정상 해결)' if ok else '❌ UNPLAYABLE'}")
        for r in reasons: print("  -", r)
    return ok, reasons

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/G_전우치전.json"
    paths = glob.glob(arg)
    if len(paths) == 1:
        trace(json.load(open(paths[0], encoding="utf-8")), verbose=True)
    else:
        print("=== 플레이테스트 일괄 판정 ===")
        npass = 0
        for p in sorted(paths):
            try:
                ok, rs = trace(json.load(open(p, encoding="utf-8")), verbose=False)
            except Exception as e:
                ok, rs = False, [f"예외 {e}"]
            npass += ok
            print(f"  {'✅ PLAYABLE ' if ok else '❌ 문제     '} {p}" + ("" if ok else "  | " + "; ".join(rs)))
        print(f"\n총 {len(paths)}편 | 플레이가능 {npass}편 ({round(100*npass/len(paths))}%)")
