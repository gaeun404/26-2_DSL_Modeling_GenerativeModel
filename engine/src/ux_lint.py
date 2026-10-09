# -*- coding: utf-8 -*-
"""
ux_lint.py — 게임 UI 요소가 '실제로 작동하는지' 검사.

논리·재미가 좋아도, 장소를 눌렀는데 볼 게 없거나 / 메모창에 적을 게 없거나 /
검색창에 단서 속 낱말을 쳤는데 없다고 나오면 게임이 무너진다.
이 린터는 **플레이어가 실제로 하는 조작** 기준으로 스키마를 검사한다.

검사 항목
  U1 장소 클릭      모든 장소가 눌렀을 때 볼 것(desc·features)과 단서를 주는가
  U2 현장 클릭      살인 현장은 관찰 포인트가 특히 풍부한가
  U3 단서→검색 연결 단서·검안서에 나온 낯선 낱말이 검색창에 실제로 있는가  ★가장 중요
  U4 검색 결과      검색 항목에 내용·해설이 비어 있지 않은가
  U5 메모창         메모에 적을 '사실 조각'이 충분한가(용의자·장소·시간·단서 축)
  U6 심문 진입      모든 용의자가 심문 가능한 상태인가(말투·트리거·알리바이)
  U7 지도 이동      좌표·이동제한이 실제로 의미 있는가(전부 도달 가능/불가 아님)
  U8 라운드 진행    라운드마다 새로 열리는 것이 있는가(빈 라운드 금지)
  U9 정답 제출      범인·흉기 보기와 동기 채점 기준이 준비됐는가
  U10 오디오 연결   장소·인물·이벤트에 재생할 BGM 큐가 매핑돼 있는가

사용: python ux_lint.py            # 전편
     python ux_lint.py out/19_장화홍련.json
"""
import json, glob, sys, re, math

SEARCHABLE = ("location", "record", "physical")   # 뒤져야 나오는 채널(채널 분화 후)
JOSA = ("으로써","으로서","에서는","에게서","이라는","라는","에서","에게","으로","까지","부터","이나","라도",
        "이며","하며","이고","과의","와의","의","을","를","이","가","은","는","과","와","도","에","로","만","야","랑")
def _strip_josa(w):
    for j in JOSA:
        if len(w)>len(j)+1 and w.endswith(j): return w[:-len(j)]
    return w
def _tokens(text):
    """단서 문장에서 '플레이어가 모를 만한 낱말' 후보 추출(조사 제거)."""
    if not text: return []
    return [_strip_josa(w) for w in re.findall(r"[가-힣]{2,6}", text)]

def lint(s):
    issues=[]; info={}
    places=s["map"]["places"]; clues=s["clue_graph"]; cast=s["cast"]
    pn={p["id"]:p["name"] for p in places}
    search=(s.get("search") or {}); idx=search.get("index") or []
    terms=set()
    for t in idx:
        terms.add(t.get("term",""))
        for a in (t.get("aliases") or []): terms.add(a)
    terms={t for t in terms if t}

    # U1 장소 클릭
    loc_clue={cl.get("location") for cl in clues if cl.get("channel") in SEARCHABLE}
    _rw = (s.get("place_rewards") or {}).get("rewards") or {}
    _rewarded = set(_rw.keys()) if isinstance(_rw, dict) else {
        x.get("place") for x in _rw if isinstance(x, dict)}
    for p in places:
        if not p.get("desc"): issues.append(("U1", f"{p['name']}: 클릭해도 보여줄 desc 없음"))
        if len(p.get("features") or [])<2: issues.append(("U1", f"{p['name']}: 탐색 특징 2개 미만"))
        if p["id"] not in loc_clue:
            # 살인 현장은 scene_inspection(관찰 포인트)이 곧 탐색 보상이므로 예외
            if p["id"]==s.get("death",{}).get("place") and len(s.get("death",{}).get("scene_inspection") or [])>=3:
                pass
            elif p["id"] in _rewarded:
                # deduce.py가 이 방에 **고유 발견**을 심어 둔다 — 빈 방이 아니다
                pass
            else:
                issues.append(("U1", f"{p['name']}: 탐색해도 나오는 단서가 없음(빈 방)"))
    info["U1"]=f"장소 {len(places)}곳 · 단서 있는 곳 {len(loc_clue & set(pn))}"

    # U2 현장 클릭
    d=s.get("death",{})
    if len(d.get("scene_inspection") or [])<3: issues.append(("U2","현장 관찰 포인트 3개 미만"))
    if not d.get("scene_description"): issues.append(("U2","현장 묘사 없음"))
    info["U2"]=f"현장 관찰 {len(d.get('scene_inspection') or [])}개"

    # U3 단서→검색 연결 (핵심)
    #   검안/단서 문장에 등장하는 '전문어 후보'가 검색창에 있는지.
    corpus=" ".join([*(d.get("scene_inspection") or []), d.get("scene_description",""),
                     *[cl.get("surface","") for cl in clues]])
    # 전문어로 볼 만한 것: 검색 index에 등록된 검안/약재/수사 용어들이 실제 단서에 쓰였는지 역방향 확인
    forensic=[t for t in idx if t.get("category") in ("검안","약재","수사")]
    used=[t for t in forensic if any(a and a in corpus for a in [t.get("term")]+ (t.get("aliases") or []))]
    if not used:
        issues.append(("U3","검안·수사 용어가 단서 문장과 하나도 연결되지 않음(검색창을 쓸 이유가 없음)"))
    # 반대로: 단서에 나온 낱말인데 검색하면 '결과 없음'이 뜨는 핵심어
    NOT_FORENSIC={"침상","책상","진상","조상","상투","상자","평상","비상구","형상","세상","상황",
                  "자국과","이상","상처럼","상당","상반","무상","일상"}
    key_terms=set()
    for line in (d.get("scene_inspection") or []):
        for w in _tokens(line):
            if w in NOT_FORENSIC: continue
            if len(w)>=2 and (w.endswith("흔") or w.endswith("자국") or
                              any(k in w for k in ["골절","중독","익사","교살","자상","시반","강직","혈흔","화상","손상"])):
                key_terms.add(w)
    missing=[w for w in key_terms if w not in terms
             and not any(w in t or (len(t) >= 2 and t in w) for t in terms)]
    for w in sorted(missing)[:4]:
        issues.append(("U3", f"검안서에 '{w}'가 나오는데 검색창엔 없음 → 결과 없음 뜸"))
    info["U3"]=f"검색 연결된 전문어 {len(used)}개 · 미연결 핵심어 {len(missing)}개"

    # U4 검색 결과 내용
    thin=[t.get("term") for t in idx if len((t.get("entry") or ""))<20]
    if thin: issues.append(("U4", f"내용이 빈약한 검색 항목 {len(thin)}개: {thin[:3]}"))
    if not (search.get("no_result_responses")): issues.append(("U4","'결과 없음' 문구 없음"))
    info["U4"]=f"검색 항목 {len(idx)}개"

    # U5 메모창: 적을 사실 조각(축)
    axes={"용의자":len(cast), "장소":len(places), "시간대":len(s.get("time_slots",[])),
          "단서":len(clues), "비밀":sum(1 for c in cast if c.get("secret",{}).get("text"))}
    for k,v in axes.items():
        if v<3: issues.append(("U5", f"메모 축 '{k}'가 {v}개뿐 — 적을 거리가 부족"))
    info["U5"]="메모 축 " + ", ".join(f"{k}{v}" for k,v in axes.items())

    # U6 심문 진입
    for c in cast:
        if not (c.get("persona",{}) or {}).get("speech_style"): issues.append(("U6",f"{c['name']}: 말투 없음"))
        if not c.get("alibi_narration"): issues.append(("U6",f"{c['name']}: 알리바이 진술 없음"))
        if not (c.get("pressure_points") or []): issues.append(("U6",f"{c['name']}: 정곡 질문 트리거 없음"))
        if len((c.get("persona",{}) or {}).get("example_lines") or [])<2:
            issues.append(("U6",f"{c['name']}: 말투 표본 부족"))
    info["U6"]=f"심문 가능 용의자 {len(cast)}명"

    # U7 지도 이동이 의미 있는가
    mm=s["map"].get("max_move_per_slot")
    if not mm: issues.append(("U7","이동 제한 없음 — 지도가 의미 없음"))
    else:
        def dist(a,b):
            pa,pb=a.get("pos"),b.get("pos")
            if not pa or not pb: return 0
            return math.hypot(pa[0]-pb[0],pa[1]-pb[1])
        pairs=[(a,b) for i,a in enumerate(places) for b in places[i+1:]]
        reach=sum(1 for a,b in pairs if dist(a,b)<=mm)
        ratio=reach/max(1,len(pairs))
        info["U7"]=f"이동한도 {mm} · 인접 도달 가능 쌍 {reach}/{len(pairs)} ({ratio:.0%})"
        if ratio>=0.98: issues.append(("U7","모든 장소가 서로 도달 가능 — 이동 제한이 사실상 무의미"))
        if ratio<=0.15: issues.append(("U7","대부분 이동 불가 — 동선 추리가 막힘"))

    # U8 라운드 진행
    rounds=s.get("config",{}).get("rounds",3)
    for r in range(1,rounds+1):
        n=sum(1 for cl in clues if cl.get("reveal_round")==r)
        if n==0: issues.append(("U8", f"라운드 {r}에 새로 열리는 단서가 없음"))
    info["U8"]="라운드별 공개 " + str([sum(1 for cl in clues if cl.get("reveal_round")==r) for r in range(1,rounds+1)])

    # U9 정답 제출
    ch=s.get("choices",{}); sol=s.get("solution",{})
    if len(ch.get("culprit",[]))!=len(cast): issues.append(("U9","범인 보기 수가 용의자 수와 다름"))
    if len(ch.get("weapon",[]))<3: issues.append(("U9","흉기 보기 부족"))
    if not sol.get("motive_keywords"): issues.append(("U9","동기 자유서술 채점 키워드 없음"))
    info["U9"]=f"범인보기 {len(ch.get('culprit',[]))} · 흉기보기 {len(ch.get('weapon',[]))} · 동기키워드 {len(sol.get('motive_keywords') or [])}"

    # U10 오디오 연결
    bgm=s.get("bgm",{})
    pc=bgm.get("place_cues") or {}; ct=bgm.get("character_themes") or {}; ev=bgm.get("event_cues") or {}
    for p in places:
        if p["id"] not in pc: issues.append(("U10", f"{p['name']}: 재생할 장소 BGM 없음"))
    for c in cast:
        if c["id"] not in ct: issues.append(("U10", f"{c['name']}: 심문 BGM 없음"))
    for need in ["clue_found","clue_decisive","accusation","verdict_correct","verdict_wrong"]:
        if need not in ev: issues.append(("U10", f"이벤트 '{need}' BGM 없음"))
    info["U10"]=f"장소큐 {len(pc)} · 인물테마 {len(ct)} · 이벤트 {len(ev)}"

    # 탐정 배역(있으면 확인)
    det=s.get("detective") or {}
    if not det.get("role"): issues.append(("U11","플레이어 배역(탐정 역할) 미정의"))
    elif len(det.get("address_by_suspects") or {})!=len(cast):
        issues.append(("U11","용의자별 플레이어 호칭 누락"))
    info["U11"]=det.get("role","없음")

    return (len(issues)==0), issues, info

NAMES={"U1":"장소 클릭","U2":"현장 클릭","U3":"단서→검색 연결","U4":"검색 결과","U5":"메모창",
       "U6":"심문 진입","U7":"지도 이동","U8":"라운드 진행","U9":"정답 제출","U10":"오디오 연결",
       "U11":"플레이어 배역"}

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else None
    if arg and arg.endswith(".json"):
        s=json.load(open(arg,encoding="utf-8"))
        ok,iss,info=lint(s)
        print(f"=== UX 점검: {s['meta']['title']} ===\n")
        for k in sorted(info, key=lambda x:int(x[1:])):
            bad=[m for c,m in iss if c==k]
            print(f"  [{'✅' if not bad else '❌'}] {NAMES[k]:12} {info[k]}")
            for m in bad: print(f"        - {m}")
        print(f"\n{'✅ 전 항목 통과' if ok else f'❌ 문제 {len(iss)}건'}")
    else:
        tot=0; bad_files=0
        from collections import Counter
        cat=Counter()
        for p in sorted(glob.glob("scenarios/[0-9]*.json")):
            s=json.load(open(p,encoding="utf-8"))
            ok,iss,info=lint(s)
            tot+=len(iss); bad_files += (0 if ok else 1)
            for c,_ in iss: cat[NAMES[c]]+=1
            mark="✅" if ok else "❌"
            print(f"  {mark} {p.split('/')[-1]:26} 문제 {len(iss):2}건" +
                  (f"  {sorted({NAMES[c] for c,_ in iss})}" if iss else ""))
        print(f"\n총 문제 {tot}건 · 문제 있는 편 {bad_files}/20")
        if cat: print("항목별:", dict(cat))
