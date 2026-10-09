# -*- coding: utf-8 -*-
"""공통 마감 헬퍼 — 시나리오 dict을 받아 지도 이동한도 자동조임 + 전 게이트 검증 + 저장."""
import json, math, os
from verify import verify, _print
from difficulty import difficulty_gate
from simulate import simulate, tier
from agent_lint import lint, secret_lint

def finalize(S, outpath, hard=False):
    os.makedirs("scenarios", exist_ok=True)
    if hard:
        S["config"]["attempts"]=2
    pl={p["id"]:p for p in S["map"]["places"]}
    mv=0
    for c in S["cast"]:
        tl=[pl[c["timeline"][sl]]["pos"] for sl in S["time_slots"]]
        for a,b in zip(tl,tl[1:]): mv=max(mv,math.hypot(a[0]-b[0],a[1]-b[1]))
    S["map"]["max_move_per_slot"]=round(mv+0.5,2)
    ok,rep=verify(S); gok,gr=difficulty_gate(S)
    lok,li=lint(S); sok,si=secret_lint(S)
    if not ok: _print([r for r in rep if not r[1]])
    if li: print("  lint:",li)
    if si: print("  secret:",si)
    rate=simulate(S,600); t,_=tier(rate)
    print(f"검증{'✅' if ok else '❌'} 난이도{'✅' if gok else '❌'} 린트{'✅' if lok else '❌'} 비밀{'✅' if sok else '❌'} · 정답률 {rate:.2f} {t}")
    for r in gr: print("  [난이도]",r)
    if ok and gok and lok and sok:
        json.dump(S,open(outpath,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        print("저장:",outpath)
        return True
    print("(미저장)")
    return False
