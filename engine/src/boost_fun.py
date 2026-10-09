# -*- coding: utf-8 -*-
"""
boost_fun.py — 재미 지표의 구조적 약점을 논리를 깨지 않고 보강.

fun.py 진단 결과 전 편에 공통으로 낮은 지표 4개를 고친다.

  F5 정곡가능성 — 비밀 트리거 낱말이 공개 정보에 전혀 안 나와서
                 플레이어가 "무엇을 물어야 할지" 유추할 방법이 없다.
                 → 그 인물의 '장소 탐색 특징'에 트리거 낱말을 은근히 심는다.
                   (방을 뒤지면 '무엇을 캐물어야 할지'가 보이는 구조 = 탐색→심문 연결)

  F9 오도       — 범인이 체감 의심도 1위라 뻔하다.
                 → 가짜 유력자를 가리키는 레드헤링 단서를 추가하고,
                   나레이션에서 가짜 유력자를 더 수상하게 묘사한다.
                   (레드헤링은 유일해 판정에서 제외되므로 논리 안전)

  F3 아하연결   — 단독으로 뜻이 서는 단서만 있어 '조합의 쾌감'이 없다.
                 → 배제도 지목도 하지 않는 '정황(context)' 단서를 추가.
                   흉기·결정적 단서와 맞물려야 뜻이 생긴다.

  F11 정보분산  — 라운드별 공개량이 쏠려 빈 라운드가 생긴다.
                 → 새로 추가되는 단서를 가장 빈약한 라운드에 배치.

안전장치: 수정 후 전 게이트를 다시 돌려, 하나라도 깨지면 그 편은 **되돌린다**.
사용: python boost_fun.py
"""
import json, glob, copy
from collections import Counter

def _next_id(clues, prefix):
    nums=[int(c["id"][len(prefix):]) for c in clues
          if c["id"].startswith(prefix) and c["id"][len(prefix):].isdigit()]
    return f"{prefix}{max(nums+[0])+1}"

def _thin_round(clues, rounds):
    cnt=Counter(c.get("reveal_round") for c in clues)
    return min(range(1,rounds+1), key=lambda r: cnt.get(r,0))

def boost(s):
    """재미 약점 보강. 반환: 변경 로그"""
    log=[]
    cast=s["cast"]; clues=s["clue_graph"]; places=s["map"]["places"]
    rounds=s.get("config",{}).get("rounds",3)
    cul=next(c for c in cast if c.get("is_culprit"))
    own={p.get("owner"):p for p in places if p.get("owner")}
    pn={p["id"]:p["name"] for p in places}

    # ── F5: 트리거 낱말을 소유 장소 features에 심어 '물어볼 거리'를 보이게 ──
    public=" ".join([b.get("text","") for b in s.get("intro",{}).get("narration",[])]
                    +[c.get("surface","")+c.get("implies","") for c in clues]
                    +[c.get("bio","") for c in cast]
                    +[p.get("desc","")+" ".join(p.get("features",[])) for p in places])
    HINT={
      "치정":"남몰래 주고받은 편지 한 장","정보유출":"외부로 보낸 자료의 사본",
      "횡령":"셈이 어긋난 장부 한 귀퉁이","절도":"제자리에 없는 물건의 빈자리",
      "도굴·장물":"출처를 알 수 없는 물건 꾸러미","밀수":"장부에 없는 짐의 흔적",
    }
    for c in cast:
        pl=own.get(c["id"])
        if not pl: continue
        trigs=[t for pp in (c.get("pressure_points") or []) for t in pp.get("trigger",[])]
        if not trigs: continue
        # 공개 정보에 하나도 안 나오는 경우에만 심는다(너무 노골적이 되지 않게)
        if any(t in public for t in trigs): continue
        t0=trigs[0]
        sec=(c.get("secret",{}) or {})
        hint=HINT.get(sec.get("type",""), f"'{t0}'와 얽힌 자취")
        feat=f"한쪽에 밀쳐 둔 {hint} — '{t0}'이라는 말이 눈에 걸린다"
        if feat not in pl["features"]:
            pl["features"].append(feat)
            log.append(f"F5 {c['name']}: '{t0}' 실마리를 {pl['name']}에 심음")

    # ── F9: 가짜 유력자를 더 수상하게(레드헤링 지목 + 나레이션 묘사) ──
    def legs(c):
        m=c.get("mmo",{}) or {}
        return sum(bool(m.get(k)) for k in ("means","motive","opportunity"))
    false_leads=[c for c in cast if not c.get("is_culprit") and legs(c)>=2]
    if false_leads:
        fl=false_leads[0]
        # (a) 레드헤링이 그를 지목 — 유일해 판정에서 제외되므로 논리 안전
        if not any(cl.get("weight")=="red_herring" and cl.get("points_to")==fl["id"] for cl in clues):
            nid=_next_id(clues,"K")
            r=_thin_round(clues,rounds)
            clues.append({"id":nid,"channel":"spine","medium":"소문",
              "surface":f"사람들 사이에 도는 말: '그날 {fl['name']}가 피해자와 크게 다투는 걸 봤다더라.'",
              "implies":f"{fl['name']}에게 혐의가 쏠리는 정황. 다만 소문일 뿐 확증은 아니다(레드헤링).",
              "weight":"red_herring","points_to":fl["id"],"exculpates":[],
              "reveal_round":r,"decisive":False})
            log.append(f"F9 가짜 유력자 {fl['name']}를 지목하는 소문 단서 추가(R{r})")
        # (b) 나레이션에서 더 수상하게
        for b in s.get("intro",{}).get("narration",[]):
            if b.get("focus")==fl["id"] and b.get("mood") not in ("음험","교활","수상","차가움"):
                b["mood"]="음험"
                log.append(f"F9 나레이션에서 {fl['name']}를 더 수상하게(mood→음험)")
                break

    # ── F3: 정황(context) 단서 추가 — 조합해야 뜻이 서는 정보 ──
    n_ctx=sum(1 for c in clues if c.get("weight")=="context")
    if n_ctx<2:
        wpn=next((c for c in clues if c.get("weight")=="weapon"), None)
        r=_thin_round(clues,rounds)
        nid=_next_id(clues,"K")
        wc=s.get("death",{}).get("weapon_class","")
        clues.append({"id":nid,"channel":"crime_scene","medium":"검안",
          "surface":f"상처의 각도와 높이로 보아, 가해자는 피해자보다 키가 크거나 비슷하며 "
                    f"한쪽 손을 주로 쓰는 사람이다. 서두른 흔적도 없다.",
          "implies":f"체격·습관·침착함이라는 조건({wc}). 단독으론 누구인지 알 수 없고, "
                    f"다른 단서와 맞물려야 범위가 좁혀진다.",
          "weight":"context","points_to":None,"exculpates":[],
          "reveal_round":r,"decisive":False})
        log.append(f"F3 정황 단서(체격·습관) 추가 — 흉기·결정적 단서와 조합 (R{r})")

    # ── F11: 라운드 쏠림 완화 — 레드헤링 일부를 빈약한 라운드로 이동 ──
    cnt=Counter(c.get("reveal_round") for c in clues)
    vals=[cnt.get(r,0) for r in range(1,rounds+1)]
    if max(vals)-min(vals)>=3:
        rich=max(range(1,rounds+1), key=lambda r: cnt.get(r,0))
        poor=min(range(1,rounds+1), key=lambda r: cnt.get(r,0))
        movable=[c for c in clues if c.get("reveal_round")==rich
                 and c.get("weight")=="red_herring" and not c.get("decisive")]
        if movable:
            movable[0]["reveal_round"]=poor
            log.append(f"F11 레드헤링 1개를 R{rich}→R{poor}로 이동(공개량 균등화)")
    return log

def gates_ok(s):
    from verify import verify
    from difficulty import difficulty_gate
    from playtest import trace
    from agent_lint import lint, secret_lint
    from simulate import simulate
    from checklist import check
    from ux_lint import lint as uxlint
    if not verify(s)[0]: return False,"verify"
    if not difficulty_gate(s)[0]: return False,"difficulty"
    if not trace(s,verbose=False)[0]: return False,"playtest"
    if not lint(s)[0]: return False,"agent_lint"
    if not secret_lint(s)[0]: return False,"secret_lint"
    if not uxlint(s)[0]: return False,"ux"
    R,_=check(s)
    if sum(1 for _,c,_ in R if c)!=len(R): return False,"checklist"
    rate=simulate(s,400)
    if not (0.30<=rate<=0.85): return False,f"rate {rate:.2f}"
    return True,""

if __name__=="__main__":
    from fun import metrics
    tot_before=tot_after=0; n=0
    for p in sorted(glob.glob("scenarios/[0-9]*.json")):
        s=json.load(open(p,encoding="utf-8"))
        before=metrics(s)[2]
        cand=copy.deepcopy(s)
        log=boost(cand)
        if not log:
            print(f"  · {p.split('/')[-1]:24} {before:5.1f} (변경 없음)")
            tot_before+=before; tot_after+=before; n+=1; continue
        ok,why=gates_ok(cand)
        if ok:
            after=metrics(cand)[2]
            json.dump(cand,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
            print(f"  ✅ {p.split('/')[-1]:24} {before:5.1f} → {after:5.1f}  (+{after-before:.1f})")
            for l in log: print(f"       · {l}")
            tot_before+=before; tot_after+=after
        else:
            print(f"  ⏭  {p.split('/')[-1]:24} {before:5.1f} 보강 시도했으나 게이트 실패({why}) → 되돌림")
            tot_before+=before; tot_after+=before
        n+=1
    print(f"\n평균 재미 {tot_before/n:.1f} → {tot_after/n:.1f}")
