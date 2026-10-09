# -*- coding: utf-8 -*-
"""
몬테카를로 플레이 시뮬레이터 — '표준 플레이어'가 N회(기본 200) 플레이했을 때의 정답률을 낸다.
정답률 0.3~0.7 이면 적정 난이도. 밴드 밖이면 튜닝 지침(턴수·목숨·단서 접근성)을 제안.
LLM 불필요: 단서 발견·성급한 지목(가짜 유력자에 목숨 소모)·마지막 추론을 확률로 모델링.

규칙 반영: rounds 라운드, 각 라운드 후 지목 가능, attempts(목숨) 소진 시 패배, turns_per_round 심문 턴.
사용: python simulate.py out/J_아랑설화.json 400
     python simulate.py "scenarios/*.json"
"""
import json, sys, glob, random

# ── 표준 플레이어 상수(시나리오 간 비교가 되도록 고정) ──
P_SPINE   = 0.78   # 라운드 공개(스파인/현장) 단서를 그 라운드에 알아챌 확률
P_LOCATION= 0.55   # 장소 탐색 단서를 찾아낼 확률(턴을 써야 함)
P_IMPULSE = 0.38   # 라운드 중간에 '유력해 보이는' 용의자를 성급히 지목할 확률
P_WEAPON_OK = 0.85 # 흉기 단서 못 찾았을 때도 흉기를 맞힐 보정(자유서술 아님)

def legs(c):
    m=c.get("mmo",{}); return sum(bool(m.get(k)) for k in ("means","motive","opportunity"))

def one_play(s, rng):
    """정답 = 범인 + 흉기 + 동기(자유서술) 를 '한 번에' 맞혀야 승리. 오답 시 목숨 1 감소."""
    cast=s["cast"]; ids=[c["id"] for c in cast]
    culprit=s["solution"]["culprit"]
    rounds=s["config"].get("rounds",3)
    lives=s["config"].get("attempts",3)
    turns=s["config"].get("turns_per_round",8)
    wchoices=s.get("choices",{}).get("weapon",[])
    clues=s["clue_graph"]
    false_leads=[c["id"] for c in cast if not c.get("is_culprit") and legs(c)>=2]
    discovered=set(); weapon_found=False

    def info():
        exon=set(); pinned=None; incrim=False
        for cl in clues:
            if cl["id"] not in discovered: continue
            if cl.get("weight")=="red_herring": continue
            ex=cl.get("exculpates")
            if ex: exon.update(ex if isinstance(ex,list) else [ex])
            if cl.get("points_to")==culprit: incrim=True
            if cl.get("decisive") and cl.get("points_to"): pinned=cl["points_to"]
        rem=[i for i in ids if i not in exon]
        if pinned and pinned in rem: rem=[pinned]
        return rem, (pinned is not None), incrim

    def accuse(guess):
        """범인·흉기·동기 동시 정답이면 True. 아니면 False(목숨 소모는 호출측)."""
        w_ok = weapon_found or (rng.random() < (1/len(wchoices) if wchoices else 0.2))
        # 동기(자유서술): 결정적 단서를 찾았으면 '왜'를 이해 → 높음, 지목 단서만이면 중간, 없으면 낮음
        _, dec, incrim = info()
        m_ok = rng.random() < (0.9 if dec else (0.55 if incrim else 0.25))
        return (guess==culprit) and w_ok and m_ok

    for R in range(1, rounds+1):
        round_clues=[cl for cl in clues if (cl.get("reveal_round") or 0)==R]
        budget=turns
        for cl in round_clues:
            if budget<=0: break
            p = P_LOCATION if cl.get("channel")=="location" else P_SPINE
            if rng.random()<p:
                discovered.add(cl["id"])
                if cl.get("weight")=="weapon": weapon_found=True
            budget-=1
        cand, dec, incrim = info()

        if R<rounds:
            # 확신(후보 1) 또는 성급한 지목 → 시도(범인+흉기+동기 동시)
            do = None
            if len(cand)==1: do=cand[0]
            else:
                tempt=[i for i in cand if i in false_leads]
                if tempt and rng.random()<P_IMPULSE: do=rng.choice(tempt)
            if do is not None:
                if accuse(do): return True
                lives-=1
                if lives<=0: return False
        else:
            # 마지막 라운드: 남은 목숨으로 후보를 소거하며 시도
            pool = cand if cand else ids
            order = [culprit]+[i for i in pool if i!=culprit] if (dec and culprit in pool) else list(pool)
            if not (dec and culprit in pool): rng.shuffle(order)
            for g in order:
                if lives<=0: return False
                if accuse(g): return True
                lives-=1
            return False
    return False

def simulate(s, N=200, seed=12345):
    rng=random.Random(seed)
    wins=sum(one_play(s, rng) for _ in range(N))
    return wins/N

def tier(rate):
    # 게임엔 난이도 사다리가 필요 — 쉬움~어려움 모두 '플레이 가능'으로 허용(0.30~0.85)
    if rate<0.30: return "❌ 너무 어려움", "턴수↑ 또는 결정적 단서 접근성↑, 목숨 여유"
    if rate<0.45: return "어려움", "가짜 유력자 2 + 장소탐색 결정적 단서(놓치기 쉬움)"
    if rate<0.62: return "중", "가짜 유력자 2 + 스파인/장소 결정적 단서"
    if rate<=0.85: return "쉬움", "가짜 유력자 1 + 스파인 결정적 단서(잘 보임)"
    return "❌ 너무 쉬움", "가짜 유력자·레드헤링 강화 또는 결정적 단서 지연"

PLAYABLE_BAND = (0.30, 0.85)  # 쉬움~어려움 티어 전체

if __name__ == "__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/*.json"
    N=int(sys.argv[2]) if len(sys.argv)>2 else 200
    paths=glob.glob(arg)
    if len(paths)==1:
        s=json.load(open(paths[0],encoding="utf-8"))
        rate=simulate(s,N)
        t,tip=tier(rate)
        print(f"[{s['meta'].get('title','')}] {N}회 플레이 정답률 = {rate:.2f}  →  {t}")
        print(f"  구성: 라운드 {s['config'].get('rounds')} · 목숨 {s['config'].get('attempts')} · 턴/라운드 {s['config'].get('turns_per_round')} · 가짜유력자 {[c['id'] for c in s['cast'] if not c.get('is_culprit') and legs(c)>=2]}")
        print(f"  튜닝: {tip}")
    else:
        print(f"=== 몬테카를로 정답률 ({N}회/편) ===")
        for p in sorted(paths):
            s=json.load(open(p,encoding="utf-8"))
            rate=simulate(s,N); t,_=tier(rate)
            print(f"  {rate:.2f}  {t:14} {p}")
