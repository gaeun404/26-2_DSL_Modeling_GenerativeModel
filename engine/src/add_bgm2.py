# -*- coding: utf-8 -*-
"""
add_bgm2.py — BGM을 '장면 단위'로 확장(v2).

v1(add_bgm.py)은 게임 전체 흐름 7큐만 있었다. 실제 플레이는 장소를 누르고, 단서가 열리고,
범인을 지목하는 '순간'마다 음악이 달라져야 한다. 그래서 아래를 추가한다:

  s["bgm"]["place_cues"][장소id] = {
       pre_murder:{...},  post_murder:{...}   ← 사건 전/후 같은 장소라도 다른 곡
  }
  s["bgm"]["character_themes"][용의자id] = {...}   ← 심문 시 그 인물 테마(라이트모티프)
  s["bgm"]["event_cues"][이벤트]        = {...}   ← 단서 오픈·지목·정답·오답·목숨 감소 등
  s["bgm"]["state_rule"]                          ← 사건 전→후 전환 규칙

모든 큐에 bpm·악기·다이내믹·길이·생성 프롬프트 포함.
사용: python add_bgm2.py     (add_bgm.py를 먼저 돌려 palette가 있어야 함)
"""
import json, glob, sys

# 장소 성격 → 음악 질감 (desc/features 키워드로 판별)
PLACE_FLAVOR=[
 (["현장","주검","시체","쓰러","진흙","피"],      "현장",   0.50,"저역 드론과 정적, 선율 최소화. 숨죽인 공기",           ["저현","징"]),
 (["곳간","창고","쌀","곡식","금고","장부","셈"], "곳간·셈", 0.62,"규칙적인 점묘(셈하는 소리), 건조한 타현",             ["목어","프살테리"]),
 (["방적","물레","실","바느질","수틀","산실"],    "길쌈",   0.58,"물레 돌듯 반복되는 오스티나토, 가는 고음현",          ["칸텔레","고쟁"]),
 (["무덤","움막","토굴","시신","도굴","병자"],    "죽음가까이",0.46,"음습한 저역, 바람 같은 노이즈, 불규칙한 정적",        ["샤쿠하치","저현"]),
 (["주막","저자","수레","여관","주막","장터","화톳불"],"저자",0.72,"사람 소리 같은 활기, 가벼운 장단(사건 후엔 텅 빔)",   ["소리북","탬버린"]),
 (["안방","처소","규방","침소","이부자리","경대"],"규방",   0.55,"부드러운 실내악, 낮은 볼륨의 사적인 선율",           ["해금","류트"]),
 (["서재","장서각","문서","서안","책","장부"],    "서재",   0.52,"종이 넘기는 듯한 미세 타현, 사색적",                ["거문고","프살테리"]),
 (["연못","물","강","우물","눈","얼음","항구"],   "물·냉기",0.48,"넓은 잔향과 물방울 같은 하모닉스",                  ["칸텔레","글라스하프"]),
 (["숲","산","고갯","오두막","성문","폐허"],      "야외",   0.56,"바람과 거리감, 먼 잔향의 단선율",                   ["대금","리코더"]),
 (["절","사찰","불단","향","굿당","제단"],        "성소",   0.44,"타종 잔향 위 느린 성가, 장중",                     ["범종","징"]),
]
def flavor(p):
    blob=(p.get("name","")+" "+p.get("desc","")+" "+" ".join(p.get("features",[])))
    for keys,lab,inten,tex,inst in PLACE_FLAVOR:
        if any(k in blob for k in keys): return lab,inten,tex,inst
    return "일반",0.55,"절제된 배경, 탐색을 방해하지 않는 지속음",[]

# 인물 성격 → 라이트모티프 성격
PERSONA_FLAVOR=[
 (["호방","의로","활기","넉살","능글","익살"], "당당·능청", 1.10,"자신만만한 순차 선율, 밝은 음정"),
 (["여리","순정","애처","지쳐","곱","무르"],   "가련",     0.88,"가늘고 흔들리는 고음, 여린 시김새"),
 (["차갑","표독","신경질","계산","깐깐","위압"],"냉철·계산", 0.95,"각진 짧은 음형, 반복되는 단호한 리듬"),
 (["음침","무뚝뚝","음험","서늘","교활"],      "음험",     0.85,"낮고 굼뜬 저역, 반음 미끄러짐"),
 (["겁","비굴","눈치","움츠","소심","방어"],   "겁·불안",   1.05,"짧게 끊기는 불규칙 리듬, 떨리는 트레몰로"),
 (["수수께끼","신비","고요","기이"],           "수수께끼",  0.92,"음정이 흐릿한 하모닉스, 비현실적 잔향"),
]
def persona_flavor(c):
    blob=(c.get("persona",{}).get("personality","")+" "+c.get("persona",{}).get("speech_style",""))
    for keys,lab,mult,tex in PERSONA_FLAVOR:
        if any(k in blob for k in keys): return lab,mult,tex
    return "표준",1.0,"중립적인 단선율"

def cue(name,when,bpm,inst,dyn,form,mood,prompt_extra,P,sr,title,theme=None):
    """모든 큐는 시나리오 공통 '주제 선율(main theme)'의 변주로 생성한다 → 앨범처럼 통일감."""
    th=""
    if theme:
        th=(f"IMPORTANT — all tracks in this scenario share ONE main theme: \"{theme['motif_desc']}\" "
            f"in {theme['key_center']}, hook: {theme['hook']}. This track is a VARIATION of that theme "
            f"(same intervals/contour, different tempo·instrumentation·mood). ")
    return {"name":name,"when":when,"bpm":int(max(32,min(160,bpm))),
            "instruments":inst,"dynamics":dyn,"form":form,"mood":mood,
            "theme_variation":(theme or {}).get("id"),
            "prompt":f"{P['reference_en']}. {th}Scene: {when}. Mood: {mood}. Tempo {int(bpm)} BPM. "
                     f"Instruments: {', '.join(inst)}. Setting: {sr.get('era','')}, {sr.get('location','')}. "
                     f"{prompt_extra} No vocals with lyrics. Avoid: {', '.join(P.get('avoid',[]))}."}

# ── 시나리오 공통 주제 선율 정의(통일감의 근거) ─────────────────────────
KEY_CENTERS=["D minor-ish (계면조 D)","A minor-ish (계면조 A)","E minor-ish","G minor-ish","B minor-ish","C minor-ish"]
def main_theme(s,P):
    """제목·톤·트릭에서 이 시나리오만의 '주제 선율' 사양을 만든다(모든 큐가 이걸 변주)."""
    title=s["meta"]["title"]; ad=s.get("adapted_story",{})
    seed=sum(ord(ch) for ch in title)
    key=KEY_CENTERS[seed%len(KEY_CENTERS)]
    lead=P["instruments"][0]
    # 원작의 정서에서 주제의 성격을 뽑음
    tone=ad.get("tone","")
    if any(k in tone for k in ["익살","활기","정겨"]): contour="상행 4도 도약 뒤 순차 하행(밝고 씩씩한 4마디)"
    elif any(k in tone for k in ["애처","애절","애틋","비극"]): contour="하행 3도-2도의 한숨형 모티프(탄식하듯 4마디)"
    elif any(k in tone for k in ["음산","스산","으스스","서늘","음습"]): contour="좁은 음역을 맴도는 반음 흔들림(불안한 3마디)"
    elif any(k in tone for k in ["우아","화사","몽환","나른"]): contour="넓게 퍼지는 완만한 아치형 선율(유려한 4마디)"
    else: contour="단순한 5음 순차 상행 후 여운(설화적 4마디)"
    return {"id":f"theme_{seed%1000}","key_center":key,"lead_instrument":lead,
            "motif_desc":f"{title}의 주제 — {contour}",
            "hook":f"{lead}로 제시되는 4마디 핵심 동기(모든 트랙이 이 동기를 변형해 사용)",
            "rule":"장소·상황 큐는 전부 이 동기의 변주(템포·조성·편성·질감만 변경). "
                   "동기를 버리고 새 선율을 쓰지 말 것 — 앨범 통일감 유지.",
            "variation_map":{
              "pre_murder":"원형 그대로, 밝고 느슨하게",
              "post_murder":"같은 동기를 단조·저역으로, 템포 낮춰 어둡게",
              "character":"동기의 앞 2마디만 그 인물 악기로",
              "clue":"동기의 끝 2마디를 짧게 따서 스팅어로",
              "decisive":"동기 전체를 전 합주로 확대(클라이맥스)",
              "verdict_correct":"동기를 처음으로 완전 종지(해소)",
              "verdict_wrong":"동기를 미완결로 끊음(불협 정지)"}}

def build_v2(s):
    bgm=s.get("bgm")
    if not bgm or "palette" not in bgm:
        raise SystemExit("먼저 add_bgm.py를 실행해 palette를 만들어야 합니다.")
    P=bgm["palette"]; sr=s["background"]["setting_raw"]; title=s["meta"]["title"]
    lo,hi=P["tempo_range"]; INST=P["instruments"]
    TH=main_theme(s,P)
    dp=s["death"]["place"]
    byid={c["id"]:c for c in s["cast"]}

    # ── 1) 장소별 큐 (사건 전 / 사건 후) ─────────────────────────────
    place_cues={}
    for p in s["map"]["places"]:
        lab,inten,tex,addinst=flavor(p)
        base=lo+(hi-lo)*inten
        n=max(2,min(len(INST),3+int(inten*2)))
        inst=list(INST[:n])
        for x in addinst:
            if x not in inst: inst.append(x)
        owner=byid.get(p.get("owner"))
        own_txt=f"{owner['name']}의 자리" if owner else "공용/현장"
        is_scene = (p["id"]==dp)

        pre=cue(f"{p['name']} — 사건 전", f"[{lab}] {p['name']} 탐색(살인 전)",
                base*1.0, inst, "pp~mp",
                "loop 90~120초, 반복 청취용(선율 절제)",
                f"평온하고 일상적인 {lab}의 공기. {own_txt}",
                f"Peaceful daily atmosphere before the murder. Texture: {tex}. Place: {p.get('desc','')[:80]}.",
                P,sr,title,TH)
        post=cue(f"{p['name']} — 사건 후", f"[{lab}] {p['name']} 탐색(살인 후)",
                 base*0.88, inst+(["징"] if "징" not in inst else []), "pp~mp",
                 "loop 90~120초, 같은 모티프를 어둡게 변주(전곡과 짝)",
                 f"같은 곳이 서늘하게 바뀐 {lab}. 온기가 빠지고 의심이 앉음",
                 f"Same place AFTER the murder: same motif but darker, minor/dissonant variation, colder reverb, "
                 f"sustained low drone. Texture: {tex}.",
                 P,sr,title,TH)
        if is_scene:
            post["mood"]="주검이 놓인 자리. 숨죽인 정적과 저역의 압박"
            post["bpm"]=int(max(32,base*0.72))
            post["dynamics"]="ppp~p"
            post["form"]="loop 60~90초, 거의 무선율(앰비언트)"
            post["prompt"]=(f"{P['reference_en']}. [Scenario main theme: {TH['motif_desc']} in {TH['key_center']}; this track is the darkest, most stripped VARIATION of it] Scene: the murder scene where the body lies. "
                            f"Almost no melody — sustained low drone, sparse single strikes with long decay, "
                            f"breath-like noise, oppressive silence. Tempo {post['bpm']} BPM. "
                            f"Instruments: {', '.join(inst)}. Setting: {sr.get('era','')}. No vocals. ")
            pre["mood"]=f"아직 아무 일도 없던 {lab}. 곧 무너질 평온"
        place_cues[p["id"]]={"place_name":p["name"],"flavor":lab,"owner":p.get("owner"),
                             "is_crime_scene":is_scene,"pre_murder":pre,"post_murder":post}

    # ── 2) 인물 테마(심문 중 그 사람 테마가 깔림) ───────────────────
    themes={}
    for i,c in enumerate(s["cast"]):
        plab,pmult,ptex=persona_flavor(c)
        lead=INST[i%len(INST)]                       # 인물마다 다른 리드 악기
        support=[INST[(i+2)%len(INST)],INST[(i+4)%len(INST)]]
        bpm=(lo+(hi-lo)*0.62)*pmult
        themes[c["id"]]={
          "character":c["name"],"persona_flavor":plab,"leitmotif_instrument":lead,
          **cue(f"{c['name']} 테마", f"{c['name']} 심문",
                bpm, [lead]+support, "p~mf",
                "loop 60~90초, 대사 위 재생(중역대 비우기)",
                f"{plab}한 인물의 속내. 압박이 올라가면 레이어 추가",
                f"Character leitmotif for a suspect who is {plab}. Lead instrument {lead}. Texture: {ptex}. "
                f"Keep midrange clear for dialogue. Add tension layer when pressed.",
                P,sr,title,TH)}
        # 압박 단계(심문이 격해질 때 얹는 레이어)
        themes[c["id"]]["pressure_layer"]={
          "when":"정곡을 찌르는 질문/비밀 실토 직전","bpm_shift":"+6~10 BPM",
          "add":"저역 펄스(심장박동) + 고음 지속음","dynamics":"mf~f",
          "prompt":f"Add tension layer over the {c['name']} theme: low heartbeat pulse, high sustained string, "
                   f"rising dissonance as the interrogator closes in."}

    # ── 3) 이벤트 큐(단서 오픈·지목·정답/오답 등) ────────────────────
    ev={}
    ev["round_start"]=cue("라운드 시작","새 라운드 개시(수사 재개)",lo+(hi-lo)*0.66,INST[:4],"mf",
        "one-shot 5~8초 + 배경으로 페이드","다시 조여오는 시간",
        "Short transitional sting announcing a new investigation round, then settle into ambience.",P,sr,title,TH)
    ev["clue_found"]=cue("단서 발견","일반 단서 오픈",lo+(hi-lo)*0.70,INST[:3],"mp~mf",
        "one-shot 3~5초 스팅어","작은 발견의 쾌감, 짧은 상승",
        "Short discovery sting: a bright rising figure on the lead instrument, curiosity satisfied.",P,sr,title,TH)
    ev["clue_forensic"]=cue("검안 단서","검안서/시체 관련 단서 오픈",lo+(hi-lo)*0.55,INST[:3]+["징"],"mp",
        "one-shot 4~6초","서늘한 사실의 무게",
        "Cold clinical sting for a forensic finding: single low strike with long decay, sparse and clinical.",P,sr,title,TH)
    ev["clue_decisive"]=cue("결정적 단서","결정적 단서 오픈(진실의 문)",lo+(hi-lo)*0.95,INST,"f",
        "one-shot 10~15초 + 여운","모든 것이 맞물리는 순간, 확신과 전율",
        "Revelation sting: full ensemble, ascending, everything clicks into place — awe and dread combined.",P,sr,title,TH)
    ev["red_herring"]=cue("헛단서","레드헤링(오해를 부르는 단서)",lo+(hi-lo)*0.68,INST[:3],"mp",
        "one-shot 3~5초","그럴듯하지만 어긋난 울림(반음 어긋난 종지)",
        "Deceptive sting: sounds like a discovery but ends on an unresolved/slightly wrong interval.",P,sr,title,TH)
    ev["search_hit"]=cue("검색 성공","검색창에서 낱말을 찾아냄",lo+(hi-lo)*0.60,INST[:2],"p~mp",
        "one-shot 2~3초","책장을 넘겨 답을 찾은 작은 만족",
        "Tiny UI sting: paper/page-like soft pluck, satisfying but understated.",P,sr,title,TH)
    ev["search_miss"]=cue("검색 실패","검색 결과 없음",lo+(hi-lo)*0.50,INST[:2],"pp",
        "one-shot 1~2초","헛짚음. 힘없이 떨어지는 두 음",
        "Tiny negative sting: two descending muted notes, gentle dead end.",P,sr,title,TH)
    ev["accusation"]=cue("탐정 추리·지목","범인 지목 단계(최종 추리)",lo+(hi-lo)*0.88,INST,"mf~f",
        "loop 45~60초, 점층 빌드업(지목 전까지 반복)","머릿속에서 조각이 맞춰지는 탐정의 시간",
        "Detective deduction theme: driving ostinato under the lead melody, steadily building, "
        "the sound of a mind assembling the truth. Tense but controlled.",P,sr,title,TH)
    ev["verdict_correct"]=cue("정답","범인·흉기·동기 적중",lo+(hi-lo)*0.85,INST,"f",
        "one-shot 15~25초","해소와 씁쓸함이 겹친 승리",
        "Resolution: the main motif finally resolves to a consonance, triumphant but tinged with sorrow.",P,sr,title,TH)
    ev["verdict_wrong"]=cue("오답","지목 실패",lo+(hi-lo)*0.45,INST[:3],"mp>pp",
        "one-shot 6~10초","무너지는 확신. 급격히 식는 공기",
        "Failure sting: the motif collapses — descending, harmony hollows out, sudden thinning.",P,sr,title,TH)
    ev["life_lost"]=cue("목숨 감소","기회 1회 소진",lo+(hi-lo)*0.40,INST[:2]+["징"],"mp",
        "one-shot 3~4초","되돌릴 수 없는 한 번의 타격",
        "Single heavy strike with long decay signalling a lost attempt.",P,sr,title,TH)
    ev["time_low"]=cue("턴 부족","남은 심문 턴이 얼마 없음",lo+(hi-lo)*0.80,INST[:3],"mf",
        "loop 20~30초","재촉하는 맥박",
        "Urgency loop: quickening pulse, narrowing register, subtle ticking.",P,sr,title,TH)

    bgm["main_theme"]=TH
    # v1 흐름 큐에도 주제 변주 표기 및 프롬프트 앞머리 삽입
    for k,c in bgm.get("cues",{}).items():
        c["theme_variation"]=TH["id"]
        if "shares ONE main theme" not in c.get("prompt",""):
            c["prompt"]=(f"[Scenario main theme: {TH['motif_desc']} in {TH['key_center']}; this track is a VARIATION of it] "+c.get("prompt",""))
    bgm["place_cues"]=place_cues
    bgm["character_themes"]=themes
    bgm["event_cues"]=ev
    bgm["state_rule"]={
      "states":["pre_murder","post_murder"],
      "switch_on":"intro 나레이션 마지막 비트(시체 발견) 직후 post_murder로 전환",
      "rule":"같은 장소라도 state에 따라 place_cues[장소].pre_murder / .post_murder 를 재생. "
             "두 곡은 같은 모티프의 밝은/어두운 변주여야 하며(테마 통일), 전환은 discovery 스팅어로 덮어 crossfade.",
      "layering":"장소 BGM(베이스) + 심문 시 character_themes(상위 레이어) + 이벤트 스팅어(원샷 오버레이)",
      "mix":"대사 중엔 장소 BGM -6dB, 이벤트 스팅어는 -3dB 우선"}
    return bgm

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/[0-9]*.json"
    for p in sorted(glob.glob(arg)):
        s=json.load(open(p,encoding="utf-8"))
        s["bgm"]=build_v2(s)
        json.dump(s,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        b=s["bgm"]
        n_all=len(b["cues"])+len(b["event_cues"])+len(b["character_themes"])+len(b["place_cues"])*2
        flav=", ".join(sorted({v["flavor"] for v in b["place_cues"].values()}))
        print(f"  ♪ {p.split('/')[-1]:26} 총 {n_all:2}곡 "
              f"(흐름{len(b['cues'])}+장소{len(b['place_cues'])}×2+인물{len(b['character_themes'])}+이벤트{len(b['event_cues'])}) · 장소색: {flav}")
    print("\n장소별(사건 전/후) · 인물 테마 · 이벤트 스팅어까지 주입 완료")
