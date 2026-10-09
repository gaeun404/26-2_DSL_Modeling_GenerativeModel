# -*- coding: utf-8 -*-
"""
fun.py — '재미' 검증기.

논리(verify)·난이도(simulate)는 "풀리는가"를 본다. 하지만 풀린다고 재미있진 않다.
이 검증기는 **탐색하는 재미 / 심문하는 재미 / 반전 / 페이싱**을 측정 가능한 성질로 쪼갠다.

측정 지표 (각 0~10, 가중합 → 100점)

[탐색의 재미]
  F1 발견밀도      라운드마다 발견할 것이 충분한가(단서·탐색특징·검색항목)
  F2 장소보상      모든 장소가 고유한 보상을 주는가(빈 방 = 재미없음)
  F3 아하연결      두 정보를 이어야 뜻이 생기는 조합이 있는가(단독으로 답 주는 단서만 있으면 심심)
  F4 검색깊이      검색어가 새 검색어를 낳는 체인의 길이

[심문의 재미]
  F5 정곡가능성    비밀 트리거를 플레이어가 '유추'할 수 있나(단서·나레이션에 실마리가 있나)
                   너무 없으면 못 찾고(답답), 너무 노골적이면 뻔함 → 적정 구간이 최고점
  F6 교차검증      A의 말로 B를 깰 수 있는 쌍이 몇 개인가(심문이 서로 물리는 맛)
  F7 반응다양성    인물 5명의 말투·성격·감정이 서로 다른가(다 비슷하면 누굴 심문해도 똑같음)
  F8 압박곡선      라운드별 태도 변화가 설계돼 있나(act_directions)

[반전]
  F9 오도(misdirection)  '가장 수상해 보이는 자' ≠ 범인 인가
  F10 비밀다양성   5명의 비밀이 서로 다른 종류인가(전부 횡령이면 지루)

[페이싱]
  F11 정보분산     라운드별 공개량이 고르게 퍼졌나(한 라운드에 몰리면 나머지가 비어 지루)
  F12 감정진폭     나레이션 정서가 다채롭게 움직이나

사용:
  python fun.py                    # 전편 점수표
  python fun.py out/19_장화홍련.json  # 한 편 상세 진단 + 개선 제안
"""
import json, glob, sys
from collections import Counter

W = {  # 가중치(합 100)
 "F1":8,"F2":8,"F3":10,"F4":6,
 "F5":10,"F6":12,"F7":8,"F8":6,
 "F9":12,"F10":6,
 "F11":8,"F12":6,
}

def _clip(x): return max(0.0, min(10.0, x))

def metrics(s):
    m={}; note={}
    cast=s["cast"]; clues=s["clue_graph"]; places=s["map"]["places"]
    rounds=s.get("config",{}).get("rounds",3)
    cul=next(c for c in cast if c.get("is_culprit"))
    pn={p["id"]:p["name"] for p in places}
    search=(s.get("search") or {})

    # ── F1 발견밀도: 라운드당 열리는 단서 + 상시 탐색 가능한 특징
    per_round=Counter(cl.get("reveal_round") for cl in clues)
    feats=sum(len(p.get("features") or []) for p in places)
    avg=sum(per_round.get(r,0) for r in range(1,rounds+1))/rounds
    m["F1"]=_clip(avg*1.6 + feats*0.12)
    note["F1"]=f"라운드당 평균 {avg:.1f}개 공개 · 장소 탐색거리 {feats}개"

    # ── F2 장소보상: location 단서가 있는 장소 비율 + 현장 관찰 깊이
    loc_places={cl.get("location") for cl in clues if cl.get("channel")=="location"}
    # deduce.py가 빈 방에 넣어 준 고유 발견도 '보상'이다(2026-08-24)
    rew=set(((s.get("place_rewards") or {}).get("rewards") or {}).keys())
    covered=(loc_places | rew) & set(pn)
    ratio=len(covered)/max(1,len(places))
    insp=len(s.get("death",{}).get("scene_inspection") or [])
    m["F2"]=_clip(ratio*8 + min(insp,5)*0.5)
    empty=[pn[p] for p in pn if p not in covered]
    note["F2"]=(f"보상 있는 장소 {len(covered)}/{len(places)}"
                f"(단서 {len(loc_places & set(pn))} + 고유발견 {len(rew & set(pn))})"
                + (f" · 빈 장소: {empty}" if empty else ""))

    # ── F3 아하연결: 단독으론 뜻이 안 서고 '조합'해야 하는 정보쌍
    #   (weapon단서 × 인물 특성) / (context × decisive) / (red_herring × 진짜)
    wpn=[c for c in clues if c.get("weight")=="weapon"]
    ctx=[c for c in clues if c.get("weight")=="context"]
    dec=[c for c in clues if c.get("decisive")]
    rh=[c for c in clues if c.get("weight")=="red_herring"]
    links=len(wpn)*len(ctx) + len(ctx)*len(dec) + min(len(rh),3)
    # ★deduce.py가 넣는 명시적 조합 레시피가 이 지표의 본체다(2026-08-24).
    #   전에는 weight=="context"에만 기대서, 그 어휘를 안 쓰는 편은 늘 3.3점이었다.
    cb=((s.get("clue_combos") or {}).get("combos")) or []
    m["F3"]=_clip(links*0.5 + len(cb)*1.7)
    note["F3"]=(f"명시 조합 {len(cb)}개 · 흉기{len(wpn)}×정황{len(ctx)}×결정적{len(dec)} "
                f"· 레드헤링 {len(rh)}")

    # ── F4 검색깊이
    chains=search.get("chains") or []
    longest=max([len(c) for c in chains], default=0)
    m["F4"]=_clip(len(chains)*0.7 + longest*1.2)
    note["F4"]=f"검색 체인 {len(chains)}개 · 최장 {longest}단계"

    # ── F5 정곡가능성: 트리거 낱말이 '공개 정보'에 실마리로 등장하는 비율
    public=" ".join([b.get("text","") for b in s.get("intro",{}).get("narration",[])]
                    +[cl.get("surface","")+cl.get("implies","") for cl in clues]
                    +[c.get("bio","") for c in cast]
                    +[p.get("desc","")+" ".join(p.get("features",[])) for p in places])
    hit=tot=0
    for c in cast:
        for pp in (c.get("pressure_points") or []):
            for t in pp.get("trigger",[]):
                tot+=1
                if t in public: hit+=1
    r=hit/max(1,tot)
    # 비대칭 평가: '실마리가 없어 못 묻는' 쪽이 '조금 친절한' 쪽보다 훨씬 나쁘다.
    #   r<0.45  → 가파르게 감점(플레이어가 무엇을 물어야 할지 모름 = 답답함)
    #   0.45~0.9 → 만점 구간(유추 가능하고, 턴이 제한된 게임에선 실마리가 있어야 함)
    #   r>0.9   → 완만히 감점(전부 떠먹여 주면 '캐낸 맛'이 옅어짐)
    if r < 0.45:   m["F5"]=_clip(10 - (0.45-r)*20)
    elif r <= 0.90: m["F5"]=10.0
    else:          m["F5"]=_clip(10 - (r-0.90)*12)
    note["F5"]=f"트리거 단서노출률 {r:.0%} (적정 45~90%)"

    # ── F6 교차검증: 진술이 서로 물리는 쌍
    ds=s["death"]["time_slot"]
    pairs=0; detail=[]
    for l in (cul.get("lies") or []):
        fp=l.get("false_place")
        wit=[c["name"] for c in cast if c["id"]!=cul["id"] and c.get("timeline",{}).get(ds)==fp]
        pairs+=len(wit)
        if wit: detail.append(f"{cul['name']}의 거짓알리바이({pn.get(fp,'')})↔{','.join(wit)}")
    # 서로를 배제해 주는 증언 — ★스키마는 weight=="exculpating"이 아니라
    #   weight=="alibi" + exculpates=[...] 를 쓴다. 예전 코드가 없는 값을 세느라
    #   이 항이 늘 0이었다(2026-08-24 수정).
    exo=sum(len(cl.get("exculpates") or []) for cl in clues)
    # 대질 쌍 — crossref.py가 넣는 '맞대면 어긋나는 진술' 개수
    xp=len(((s.get("cross_examination") or {}).get("pairs")) or [])
    # 관계도에서 서로 얽힌 정도
    rels=sum(len(c.get("relationships") or {}) for c in cast)/max(1,len(cast))
    m["F6"]=_clip(pairs*2.0 + xp*0.7 + exo*0.5 + rels*0.3)
    note["F6"]=(f"거짓알리바이 {pairs}쌍 · 대질 {xp}쌍 · 배제증언 {exo}개"
                + (f" · {detail[0]}" if detail else ""))

    # ── F7 반응다양성: 말투·성격·음성 분화
    styles={(c.get("persona",{}) or {}).get("speech_style","") for c in cast}
    pers={(c.get("persona",{}) or {}).get("personality","") for c in cast}
    voices={( (s.get("voice",{}).get("cast",{}).get(c["id"],{}) or {}).get("pitch"),
              (s.get("voice",{}).get("cast",{}).get(c["id"],{}) or {}).get("tempo")) for c in cast}
    m["F7"]=_clip(len(styles)*1.1 + len(pers)*1.1 + len(voices)*0.9)
    note["F7"]=f"말투 {len(styles)}종 · 성격 {len(pers)}종 · 음역 {len(voices)}종"

    # ── F8 압박곡선
    acts=[len(c.get("act_directions") or []) for c in cast]
    ok=sum(1 for a in acts if a>=rounds)
    m["F8"]=_clip(ok/max(1,len(cast))*10)
    note["F8"]=f"라운드별 행동지침 보유 {ok}/{len(cast)}명"

    # ── F9 오도: '플레이어 눈에' 가장 수상해 보이는 자가 범인이면 뻔함
    #   ※ MMO는 정답 키라 쓰지 않는다. 공개 신호(나레이션 묘사·알리바이 부재·
    #      레드헤링 지목·현장 근접 진술)만으로 '보이는 의심도'를 계산.
    exon_by_clue=set()
    for cl in clues:
        if cl.get("weight")=="exculpating":
            ex=cl.get("exculpates") or []
            exon_by_clue.update(ex if isinstance(ex,list) else [ex])
    def perceived(c):
        sc=0.0
        # (1) 나레이션이 악역/수상하게 묘사 → 눈에 띄게 의심
        for b in s.get("intro",{}).get("narration",[]):
            if b.get("focus")==c["id"]:
                if b.get("mood") in ("음험","차가움","교활","탐욕","음침","수상","거칠","인색"): sc+=3
                elif b.get("mood") in ("불안","비굴","원한"): sc+=1.5
        # (2) 알리바이 증언이 없다 → 의심
        if c["id"] not in exon_by_clue: sc+=3
        # (3) 공개 진술상 현장을 드나든 사람
        if s["death"]["place"] in (c.get("timeline") or {}).values(): sc+=2
        # (4) 레드헤링이 그 사람 방을 가리키거나 그를 암시
        for cl in clues:
            if cl.get("weight")=="red_herring":
                if cl.get("points_to")==c["id"]: sc+=2
                own=next((p for p in places if p.get("owner")==c["id"]), None)
                if own and cl.get("location")==own["id"]: sc+=0.7
        # (5) 외부자·이방인은 본능적으로 의심받음
        pub=(c.get("public","") or "")+(c.get("profile",{}).get("status","") or "")
        if any(k in pub for k in ["떠돌","이방","외부","낯선","객","무당","도굴"]): sc+=1.5
        return sc
    ranked=sorted(cast, key=perceived, reverse=True)
    rank=[c["id"] for c in ranked].index(cul["id"])
    gap=perceived(ranked[0])-perceived(cul)
    # 범인이 눈에 띄는 1위면 뻔함. 2~3위면 최고. 꼴찌면 단서가 너무 없어 허탈
    base={0:3.5,1:9.0,2:10.0,3:8.0,4:5.5}.get(rank,5.0)
    m["F9"]=_clip(base + min(gap,3)*0.4)
    note["F9"]=(f"체감 의심도에서 범인은 {rank+1}위/{len(cast)} "
                f"(1위={ranked[0]['name']}, 격차 {gap:.1f}) — 2~3위가 이상적")

    # ── F10 비밀다양성
    types={(c.get("secret",{}) or {}).get("type","") for c in cast}
    m["F10"]=_clip(len(types)*2.0)
    note["F10"]=f"비밀 유형 {len(types)}종: {', '.join(sorted(t for t in types if t))[:46]}"

    # ── F11 정보분산: 라운드 공개량이 고르게
    vals=[per_round.get(r,0) for r in range(1,rounds+1)]
    if sum(vals)==0: m["F11"]=0; note["F11"]="공개 단서 없음"
    else:
        mean=sum(vals)/len(vals)
        var=sum((v-mean)**2 for v in vals)/len(vals)
        m["F11"]=_clip(10 - var*1.1)
        note["F11"]=f"라운드별 공개 {vals} (편차 작을수록 좋음)"

    # ── F12 감정진폭
    moods=[b.get("mood") for b in s.get("intro",{}).get("narration",[])]
    m["F12"]=_clip(len(set(moods))*1.5)
    note["F12"]=f"나레이션 정서 {len(set(moods))}종: {', '.join(sorted(set(m2 for m2 in moods if m2)))[:40]}"

    total=sum(m[k]*W[k] for k in W)/10.0
    return m, note, round(total,1)

def grade(t):
    if t>=85: return "🌟 매우 재미있음"
    if t>=72: return "🟢 재미있음"
    if t>=60: return "🟡 무난"
    if t>=48: return "🟠 밋밋"
    return "🔴 지루함"

TIPS={
 "F1":"라운드당 공개 단서를 늘리거나 장소 features를 추가",
 "F2":"보상 없는 장소에 location 단서를 넣을 것(빈 방 금지)",
 "F3":"'정황(context)' 단서를 추가해 흉기·결정적 단서와 조합되게",
 "F4":"검색 항목의 unlocks를 이어 체인을 길게",
 "F5":"트리거 낱말을 단서·나레이션에 은근히 흘리거나(너무 낮을 때) 덜 노골적으로(너무 높을 때)",
 "F6":"범인의 거짓 알리바이 장소에 목격자를 두고, 알리바이 증언을 늘릴 것",
 "F7":"인물 말투·성격·음역을 더 갈라놓을 것",
 "F8":"act_directions(라운드별 행동지침) 보강",
 "F9":"나레이션·MMO에서 '가짜 유력자'를 더 수상하게, 범인은 덜 수상하게",
 "F10":"비밀 유형을 서로 다르게(횡령만 반복 금지)",
 "F11":"단서 reveal_round를 고르게 재배치",
 "F12":"나레이션 비트의 mood를 다양하게",
}

def report(s, verbose=True):
    m,note,total=metrics(s)
    if verbose:
        print(f"=== 재미 진단: {s['meta']['title']} ({s['meta']['origin']}) ===")
        print(f"총점 {total}/100  {grade(total)}\n")
        groups=[("탐색의 재미",["F1","F2","F3","F4"]),("심문의 재미",["F5","F6","F7","F8"]),
                ("반전",["F9","F10"]),("페이싱",["F11","F12"])]
        names={"F1":"발견밀도","F2":"장소보상","F3":"아하연결","F4":"검색깊이","F5":"정곡가능성",
               "F6":"교차검증","F7":"반응다양성","F8":"압박곡선","F9":"오도(반전)","F10":"비밀다양성",
               "F11":"정보분산","F12":"감정진폭"}
        for gname,keys in groups:
            print(f"[{gname}]")
            for k in keys:
                bar="█"*int(round(m[k]))+"·"*(10-int(round(m[k])))
                print(f"  {names[k]:6} {m[k]:4.1f} {bar}  {note[k]}")
            print()
        weak=sorted(m.items(), key=lambda kv: kv[1])[:3]
        print("개선 우선순위:")
        for k,v in weak:
            if v<8: print(f"  · {names[k]}({v:.1f}) → {TIPS[k]}")
    return total

def check_fun(s, floor=60):
    """게이트로 쓸 때: 총점이 기준 미만이면 실패."""
    _,_,t=metrics(s)
    return t>=floor, t

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else None
    if arg and arg.endswith(".json"):
        report(json.load(open(arg,encoding="utf-8")))
    else:
        rows=[]
        for p in sorted(glob.glob("scenarios/[0-9]*.json")):
            s=json.load(open(p,encoding="utf-8"))
            m,note,t=metrics(s)
            rows.append((p.split("/")[-1],t,m))
        print(f"{'파일':24} {'총점':>5}  {'탐색':>4} {'심문':>4} {'반전':>4} {'페이':>4}  판정")
        print("-"*74)
        for name,t,m in sorted(rows,key=lambda r:-r[1]):
            ex=sum(m[k]*W[k] for k in ["F1","F2","F3","F4"])/sum(W[k] for k in ["F1","F2","F3","F4"])
            iq=sum(m[k]*W[k] for k in ["F5","F6","F7","F8"])/sum(W[k] for k in ["F5","F6","F7","F8"])
            tw=sum(m[k]*W[k] for k in ["F9","F10"])/sum(W[k] for k in ["F9","F10"])
            pc=sum(m[k]*W[k] for k in ["F11","F12"])/sum(W[k] for k in ["F11","F12"])
            print(f"{name:24} {t:5.1f}  {ex:4.1f} {iq:4.1f} {tw:4.1f} {pc:4.1f}  {grade(t)}")
        print("-"*74)
        avg=sum(r[1] for r in rows)/len(rows)
        print(f"평균 {avg:.1f}/100 · 60점 미만 {sum(1 for r in rows if r[1]<60)}편")
