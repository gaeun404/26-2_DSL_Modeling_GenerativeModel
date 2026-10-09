# -*- coding: utf-8 -*-
"""전체 검증 러너 — 넘버링된 모든 시나리오에 6단 게이트 + 몬테카를로를 돌려 한 표로 요약.
사용: python run_all.py            # out/[0-9]*.json 전부
     python run_all.py "scenarios/*.json"
"""
import json, glob, sys
from verify import verify
from difficulty import difficulty_gate
from playtest import trace
from agent_lint import lint, secret_lint
from simulate import simulate, tier
from checklist import check
from fun import check_fun
from ux_lint import lint as uxlint
from relation_lint import lint as rellint   # 관계·서사가 실질을 갖췄나

# 콘솔 표에서만 쓰는 색 — 스키마에는 넣지 않는다(2026-08-25)
_TIER_MARK = {"어려움": "🔴", "중": "🟡", "쉬움": "🟢"}


def run(paths, N=400):
    print(f"{'파일':22} {'v':2} {'난':2} {'플':2} {'린':2} {'비':2} {'UX':2} {'관':2} {'체크':6} {'재미':5} {'정답률·티어':13}")
    print("-"*90)
    allok=0
    for p in sorted(paths):
        s=json.load(open(p,encoding="utf-8"))
        v=verify(s)[0]; g=difficulty_gate(s)[0]; pl=trace(s,verbose=False)[0]
        l=lint(s)[0]; sec=secret_lint(s)[0]
        ux=uxlint(s)[0]
        rel=rellint(s)[0]
        fok,fscore=check_fun(s)
        R,_=check(s); npass=sum(1 for _,c,_ in R if c)
        rate=simulate(s,N); t,_=tier(rate)
        ok = v and g and pl and l and sec and ux and rel and fok and npass==len(R) and 0.30<=rate<=0.85
        allok += ok
        M=lambda b:"✅" if b else "❌"
        tmark = _TIER_MARK.get(t, "") + " " + t
        print(f"{p.split('/')[-1]:22} {M(v)} {M(g)} {M(pl)} {M(l)} {M(sec)} {M(ux)} {M(rel)} {npass:2}/{len(R):2} {fscore:5.1f} {rate:.2f} {tmark:11}")
    print("-"*90)
    print(f"전부 통과: {allok}/{len(paths)}편")
    print("v=논리 난=난이도 플=플레이가능 린=자기오류 비=비밀이중도달 UX=게임요소작동 관=관계·서사실질 체크=52항목 재미=100점 · 티어: 어려움<0.45<중<0.62<쉬움")

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/[0-9]*.json"
    run(glob.glob(arg))
