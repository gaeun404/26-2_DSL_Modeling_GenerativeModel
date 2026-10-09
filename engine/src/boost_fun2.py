# -*- coding: utf-8 -*-
"""
boost_fun2.py — 재미 2차 보강. 1차(boost_fun) 후에도 낮게 남은 세 지표를 정조준한다.

  F5 정곡가능성(평균 4.0, 19편 미달) ★가장 큰 구멍
     문제: 비밀 트리거 낱말이 공개 정보에 거의 안 나와, 플레이어가 무엇을 캐물어야 할지 모른다.
     목표: 트리거 노출률을 0.55 근처로(너무 낮으면 답답, 너무 높으면 뻔함).
     방법: 부족한 만큼만 그 인물의 '방 탐색 특징'에 트리거 낱말을 심는다.
           → 방을 뒤지면 물어볼 말이 생기는 구조(탐색과 심문이 맞물림).

  F3 아하연결(평균 6.2)
     문제: 정황(context) 단서가 1개뿐이라 '조합해서 깨닫는' 맛이 약하다.
     방법: 배제도 지목도 하지 않는 정황 단서를 2개까지 채운다(논리 무영향).

  F6 교차검증(평균 7.1, 가중치 12로 가장 큼)
     문제: 알리바이를 뒷받침·반박할 증언이 적어 심문이 서로 물리지 않는다.
     방법: 이미 배제된 인물에 대한 '보강 증언'을 추가한다.
           배제 집합이 바뀌지 않으므로 유일해·난이도에 영향이 없고,
           플레이어에겐 교차 확인할 재료가 늘어난다.

안전장치: 수정 후 전 게이트 재검증 → 하나라도 깨지면 되돌린다.
사용: python boost_fun2.py
"""
import json, glob, copy
from collections import Counter

def _public_text(s):
    return " ".join([b.get("text","") for b in s.get("intro",{}).get("narration",[])]
                    +[c.get("surface","")+c.get("implies","") for c in s["clue_graph"]]
                    +[c.get("bio","") for c in s["cast"]]
                    +[p.get("desc","")+" ".join(p.get("features",[])) for p in s["map"]["places"]])

def _next_id(clues, prefix):
    nums=[int(c["id"][len(prefix):]) for c in clues
          if c["id"].startswith(prefix) and c["id"][len(prefix):].isdigit()]
    return f"{prefix}{max(nums+[0])+1}"

def _thin_round(clues, rounds):
    cnt=Counter(c.get("reveal_round") for c in clues)
    return min(range(1,rounds+1), key=lambda r: cnt.get(r,0))

# 트리거 낱말을 방에 심을 때 쓰는 자연스러운 문장 틀
SEED_TMPL=[
 "구석에 밀쳐 둔 물건에 '{t}'라는 말이 적혀 있다",
 "서랍 안쪽에서 '{t}'와 얽힌 자취가 나온다",
 "누군가 급히 감춘 듯한 '{t}' 관련 물건이 있다",
 "벽 틈에 끼워진 쪽지에 '{t}'라는 낱말이 보인다",
]

def boost2(s):
    log=[]
    cast=s["cast"]; clues=s["clue_graph"]; places=s["map"]["places"]
    rounds=s.get("config",{}).get("rounds",3)
    own={p.get("owner"):p for p in places if p.get("owner")}

    # ── F5: 트리거 노출률을 0.55 근처로 끌어올린다 ──────────────
    pub=_public_text(s)
    trig_list=[]  # (cast, trigger, 노출여부)
    for c in cast:
        for pp in (c.get("pressure_points") or []):
            for t in pp.get("trigger",[]):
                trig_list.append((c,t,t in pub))
    total=len(trig_list); shown=sum(1 for _,_,ok in trig_list if ok)
    target=round(0.55*total)
    need=target-shown
    if need>0:
        seeded=0
        for c,t,ok in trig_list:
            if seeded>=need: break
            if ok: continue
            pl=own.get(c["id"])
            if not pl: continue
            line=SEED_TMPL[seeded%len(SEED_TMPL)].format(t=t)
            if line not in pl["features"]:
                pl["features"].append(line)
                seeded+=1
        if seeded:
            log.append(f"F5 트리거 노출 {shown}/{total} → {shown+seeded}/{total} (방 탐색에 {seeded}개 심음)")

    # ── F3: 정황 단서를 2개까지 ────────────────────────────────
    CTX_POOL=[
      ("현장 주변에 남은 발자국의 보폭이 고르다 — 서두르지 않았다는 뜻이다.",
       "침착하게 움직인 자. 우발적 다툼이 아니라 준비된 행동임을 시사(단독으론 특정 불가)."),
      ("피해자의 물건 중 없어진 것이 없다. 재물을 노린 흔적이 아니다.",
       "동기가 재물이 아니라 '입막음'이나 원한 쪽임을 시사(누구인지까지는 알 수 없음)."),
      ("사건 전후로 이 자리를 드나든 사람이 여럿이라 발자국이 겹쳐 있다.",
       "여러 명의 출입 정황. 단독으론 범위를 좁히지 못하고 다른 단서와 맞물려야 뜻이 선다."),
    ]
    n_ctx=sum(1 for c in clues if c.get("weight")=="context")
    added=0
    while n_ctx+added<2 and added<len(CTX_POOL):
        surf,impl=CTX_POOL[added]
        r=_thin_round(clues,rounds)
        clues.append({"id":_next_id(clues,"K"),"channel":"crime_scene","medium":"현장",
          "surface":surf,"implies":impl,"weight":"context",
          "points_to":None,"exculpates":[],"reveal_round":r,"decisive":False})
        added+=1
    if added: log.append(f"F3 정황 단서 {added}개 추가(조합해야 뜻이 서는 정보)")

    # ── F6: 이미 배제된 인물의 '보강 증언' 추가(배제 집합 불변 → 논리 안전) ──
    exon=set()
    for cl in clues:
        if cl.get("weight")=="exculpating":
            ex=cl.get("exculpates") or []
            exon.update(ex if isinstance(ex,list) else [ex])
    pn={p["id"]:p["name"] for p in places}
    ds=s["death"]["time_slot"]
    made=0
    for cid in list(exon)[:2]:
        c=next((x for x in cast if x["id"]==cid), None)
        if not c: continue
        where=pn.get(c.get("timeline",{}).get(ds),"제 자리")
        r=_thin_round(clues,rounds)
        clues.append({"id":_next_id(clues,"K"),"channel":"spine","medium":"증언",
          "surface":f"또 다른 사람도 같은 말을 한다: '그 시각 {c['name']}는 {where}에 있었소. "
                    f"나도 그 자리에서 봤소이다.'",
          "implies":f"{cid}의 알리바이를 뒷받침하는 두 번째 증언 — 교차 확인 가능.",
          "weight":"exculpating","points_to":None,"exculpates":[cid],
          "reveal_round":r,"decisive":False})
        made+=1
    if made: log.append(f"F6 알리바이 보강 증언 {made}개 추가(교차검증 재료)")

    # ── F9 잔여: 범인이 여전히 체감 1위인 편만 가짜 유력자를 더 부각 ──
    from fun import metrics as _m
    if _m(s)[0]["F9"]<5:
        def legs(c):
            mm=c.get("mmo",{}) or {}
            return sum(bool(mm.get(k)) for k in ("means","motive","opportunity"))
        fls=[c for c in cast if not c.get("is_culprit") and legs(c)>=2]
        if fls:
            fl=fls[-1]
            pl=own.get(fl["id"])
            if pl:
                feat=f"바닥에 떨어진 {fl['name']}의 물건 — 피해자와 다툰 그날의 자취"
                if feat not in pl["features"]:
                    pl["features"].append(feat)
            r=_thin_round(clues,rounds)
            clues.append({"id":_next_id(clues,"K"),"channel":"spine","medium":"증언",
              "surface":f"하인 하나가 덧붙인다: '{fl['name']}가 그날 몹시 화가 나 있었습니다. "
                        f"평소 같지 않았어요.'",
              "implies":f"{fl['name']}에게 시선이 쏠리는 정황(레드헤링). 감정은 증거가 아니다.",
              "weight":"red_herring","points_to":fl["id"],"exculpates":[],
              "reveal_round":r,"decisive":False})
            log.append(f"F9 {fl['name']}에게 의심 신호 추가(범인 체감순위 낮추기)")
    return log

if __name__=="__main__":
    from fun import metrics
    from boost_fun import gates_ok
    tb=ta=0; n=0
    for p in sorted(glob.glob("scenarios/[0-9]*.json")):
        s=json.load(open(p,encoding="utf-8"))
        before=metrics(s)[2]
        cand=copy.deepcopy(s)
        log=boost2(cand)
        if not log:
            print(f"  · {p.split('/')[-1]:24} {before:5.1f} (변경 없음)")
            tb+=before; ta+=before; n+=1; continue
        ok,why=gates_ok(cand)
        if ok:
            after=metrics(cand)[2]
            if after>=before:
                json.dump(cand,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
                print(f"  ✅ {p.split('/')[-1]:24} {before:5.1f} → {after:5.1f}  (+{after-before:.1f})")
                for l in log: print(f"       · {l}")
                tb+=before; ta+=after
            else:
                print(f"  ⏭  {p.split('/')[-1]:24} {before:5.1f} 점수 하락 → 되돌림")
                tb+=before; ta+=before
        else:
            print(f"  ⏭  {p.split('/')[-1]:24} {before:5.1f} 게이트 실패({why}) → 되돌림")
            tb+=before; ta+=before
        n+=1
    print(f"\n평균 재미 {tb/n:.1f} → {ta/n:.1f}")
