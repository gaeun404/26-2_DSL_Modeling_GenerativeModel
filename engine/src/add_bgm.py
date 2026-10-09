# -*- coding: utf-8 -*-
"""
add_bgm.py — 시나리오마다 '다른 음악'이 나오도록 BGM 스펙을 스키마에 주입.

문제: 기존 JSON엔 BGM 지시가 없어 모든 시나리오의 곡이 똑같이 나옴.
해결: background.setting_raw(문화·시대) + adapted_story(톤/반전) + 사건 내용에서
      **문화권별 악기·음계·템포**와 **게임 국면별 큐(cue)**를 생성해 s["bgm"]에 넣는다.

구조:
  s["bgm"] = {
    "palette": {culture_key, instruments[], scale, tempo_range, texture, percussion, avoid[]},
    "cues": { intro, discovery, investigation, interrogation, climax, reveal, ending }
             각 cue = {name, when, bpm, key_mode, instruments[], dynamics, loop_sec, mood, prompt}
  }
`prompt`는 음악생성 모델(Suno/MusicGen 등)에 그대로 넣는 영문+한글 혼합 프롬프트.
사용: python add_bgm.py            # out/[0-9]*.json 전부
"""
import json, glob, sys, re

# ── 문화권별 악기·음계 팔레트 ──────────────────────────────────────────
PALETTES = {
 "korea_folk": {
   "label":"한국 전통(민속)",
   "instruments":["대금","해금","거문고","아쟁","장구","소리북","박(拍)"],
   "scale":"계면조(minor-like pentatonic), 시김새(꺾는 음) 강조",
   "tempo_range":[52,96], "texture":"단선율 중심 + 장단(진양조·중모리)",
   "percussion":"장구·북 장단(진양조 6/4 → 자진모리 12/8로 가속)",
   "avoid":["서양 오케스트라 금관","드럼킷","신스 패드"],
   "en":"Korean traditional folk: daegeum bamboo flute, haegeum fiddle, geomungo zither, janggu drum, gyemyeonjo pentatonic mode"},
 "korea_court": {
   "label":"한국 궁중(정악)",
   "instruments":["편종","편경","당피리","대금","아쟁","좌고"],
   "scale":"평조(平調) 정악, 느리고 장중한 지속음",
   "tempo_range":[40,66], "texture":"느린 합주·긴 지속음, 여백이 큰 정악",
   "percussion":"좌고·박의 드문 타격(구조 표시)",
   "avoid":["빠른 타악","민속 장단","서양 화성 진행"],
   "en":"Korean court music (jeongak): pyeonjong bells, pyeongyeong stone chimes, dangpiri, daegeum, ajaeng, very slow solemn sustained tones"},
 "korea_buddhist": {
   "label":"한국 불교 사찰 · 판소리",
   "instruments":["범종","목탁","요령","태평소","소리북","징"],
   "scale":"판소리 계면조 + 범패(불교 성악)풍 선율",
   "tempo_range":[44,88], "texture":"타종 잔향 위 독창적 선율(판소리 창)",
   "percussion":"목탁의 규칙적 각(却), 소리북 장단",
   "avoid":["경쾌한 팝 리듬","전자음"],
   "en":"Korean Buddhist temple & pansori: temple bell, moktak woodblock, taepyeongso shawm, sorikbuk drum, beompae chant timbre"},
 "china_tang": {
   "label":"동아시아 당나라풍",
   "instruments":["비파","고쟁","얼후","소(퉁소)","편종","목어"],
   "scale":"중국 5음(궁상각치우), 화사한 장식음",
   "tempo_range":[56,100], "texture":"비파 트레몰로 + 고쟁 글리산도의 화사한 층",
   "percussion":"작은 북과 목어의 가벼운 점묘",
   "avoid":["한국 장구 장단","서양 화성"],
   "en":"Tang-dynasty Chinese: pipa tremolo, guzheng glissando, erhu, xiao flute, pentatonic gong-shang mode, lush and dreamy"},
 "japan_ancient": {
   "label":"동아시아 고도(일본 고전)",
   "instruments":["샤쿠하치","비와","고토","타이코","린(요령)"],
   "scale":"인센(in-sen)·미야코부시 음계(반음 포함 어두운 5음)",
   "tempo_range":[40,80], "texture":"긴 정적과 단발 타격, 바람소리 같은 무음(ma)",
   "percussion":"타이코의 드문 저음 타격, 잔향 길게",
   "avoid":["밝은 장조 선율","연속적 리듬 루프"],
   "en":"Ancient Japanese: shakuhachi breathy flute, biwa lute strikes, koto, taiko low hits, in-sen scale,長い間(ma) silence, desolate"},
 "medieval_europe": {
   "label":"중세 유럽",
   "instruments":["류트","리코더","비엘(fiddle)","프살테리","핸드드럼","하디거디"],
   "scale":"도리안·에올리안 선법(modal), 평행 5도",
   "tempo_range":[60,112], "texture":"모달 선법 위 드론(지속저음)",
   "percussion":"탬버린·프레임드럼의 6/8 춤곡 리듬",
   "avoid":["현대 화성","전자 신스"],
   "en":"Medieval European: lute, recorder, vielle, psaltery, hurdy-gurdy drone, Dorian/Aeolian modal, 6/8 dance rhythm"},
 "nordic": {
   "label":"북유럽",
   "instruments":["니켈하르파","하르당에르 피들","칸텔레","프레임드럼","보컬 요이크"],
   "scale":"단선법 + 공명현(sympathetic strings)의 서늘한 배음",
   "tempo_range":[48,92], "texture":"얼음처럼 맑은 공명, 넓은 잔향",
   "percussion":"프레임드럼의 느린 심장박동",
   "avoid":["따뜻한 금관","라틴 리듬"],
   "en":"Nordic: nyckelharpa, hardanger fiddle, kantele, frame drum, sympathetic-string shimmer, icy reverb, joik-like vocal"},
 "modern_europe": {
   "label":"근대 유럽 도시",
   "instruments":["현악 4중주","피아노","뮤직박스","아코디언","첼레스타"],
   "scale":"낭만기 단조, 반음계적 긴장",
   "tempo_range":[54,100], "texture":"실내악 규모, 뮤직박스의 애처로운 오르골",
   "percussion":"거의 없음(현·피아노의 리듬)",
   "avoid":["민속 타악","전통 아시아 악기"],
   "en":"19th-century European chamber: string quartet, piano, music box, accordion, celesta, romantic minor, chromatic tension"},
 "modern_city": {
   "label":"현대 도시 스릴러",
   "instruments":["저역 신스 패드","일렉트릭 피아노","뮤트 기타","콘트라베이스","브러시 드럼","앰비언트 노이즈"],
   "scale":"단조 재즈 화성 + 지속 저역, 반음계적 긴장",
   "tempo_range":[58,104], "texture":"도시의 밤 같은 건조한 공간감, 리버브 짧게",
   "percussion":"브러시 스네어·킥의 절제된 맥박",
   "avoid":["국악기","중세 악기","오케스트라 팡파르"],
   "en":"Contemporary urban thriller: deep synth pad, Rhodes electric piano, muted guitar, upright bass, brushed drums, minor jazz harmony, dry city-night atmosphere"},
 "modern_office": {
   "label":"현대 오피스·테크",
   "instruments":["신스 아르페지오","프리페어드 피아노","글리치 퍼커션","서브 베이스","스트링 패드"],
   "scale":"미니멀 반복 음형, 무표정한 장2도 진행",
   "tempo_range":[62,110], "texture":"형광등 아래의 무기질적 반복, 클릭·타이핑 같은 점묘",
   "percussion":"글리치·클릭 노이즈의 미세한 그리드",
   "avoid":["따뜻한 어쿠스틱","민속 악기","드라마틱 금관"],
   "en":"Modern tech-office score: minimal synth arpeggio, prepared piano, glitch percussion, sub bass, string pad, fluorescent-light coldness, ticking clicks"},
 "greek_myth": {
   "label":"고대 그리스",
   "instruments":["리라","키타라","아울로스","프레임드럼","크로탈라"],
   "scale":"고대 그리스 선법(도리안·프리지안), 헤테로포니",
   "tempo_range":[50,96], "texture":"현의 뜯음 + 겹리드의 애가(哀歌)",
   "percussion":"프레임드럼·크로탈라의 의식적 박",
   "avoid":["중세 유럽 악기","동아시아 음색"],
   "en":"Ancient Greek: lyra, kithara, aulos double-reed, frame drum, krotala, Dorian/Phrygian mode, lament heterophony"},
}

def pick_palette(s):
    sr=s["background"]["setting_raw"]; cul=(sr.get("culture") or "")+" "+(sr.get("era") or "")+" "+(sr.get("location") or "")
    if "궁중" in cul or "수성궁" in cul or "별궁" in cul: return "korea_court"
    if "불교" in cul or "사찰" in cul or "절" in cul or "몽은사" in cul: return "korea_buddhist"
    if "당나라" in cul: return "china_tang"
    if "고도" in cul or "라쇼몽" in cul or "나생문" in cul or "도읍" in cul: return "japan_ancient"
    if "그리스" in cul: return "greek_myth"
    if "북유럽" in cul or "북구" in cul: return "nordic"
    if any(k in cul for k in ["스타트업","사무실","오피스","회사","연구소","IT","테크"]): return "modern_office"
    if any(k in cul for k in ["현대","21세기","오늘날","도시","아파트","서울","2020"]): return "modern_city"
    if "근대" in cul or "19세기" in cul: return "modern_europe"
    if "유럽" in cul or "독일" in cul or "중세" in cul or "서구" in cul: return "medieval_europe"
    return "korea_folk"

# ── 국면별 큐 정의(문화 무관 골격 + 팔레트로 색칠) ───────────────────
CUE_SPEC=[
 ("intro",        "원작 나레이션(옛날 옛적에~)",       0.55,"밝고 설화적, 향수 어린",              "loop 60~90초, 서사에 방해되지 않게 낮은 볼륨"),
 ("discovery",    "시체 발견·반전의 순간",              1.00,"충격·정적·불협, 급정지",              "one-shot 8~15초 스팅어 + 여운"),
 ("investigation","현장/장소 탐색",                     0.62,"차분한 긴장, 관찰의 집중",            "loop 90~120초, 반복 청취 견디게 절제"),
 ("interrogation","용의자 심문(대화)",                  0.70,"인물 심리·미묘한 압박",               "loop 60~90초, 대사 가리지 않게 중역대 비움"),
 ("climax",       "결정적 단서 공개 / 최종 지목",        0.92,"고조되는 확신과 두려움",              "loop 45~60초, 점층 빌드업"),
 ("reveal",       "진범 공개·자백",                     0.85,"비극적 카타르시스, 동기의 슬픔",       "one-shot 30~45초"),
 ("ending",       "사건 종결·에필로그",                 0.45,"체념과 여운, 원작으로의 회귀",         "loop 60초, 페이드아웃"),
]

# ── 톤 수식자: 같은 문화권이라도 '작품 내용'에 따라 음악이 달라지게 ──────
# (tone/tone_shift/trick 키워드 → 템포 가감, 시그니처 악기, 선법/질감 변형)
TONE_MODS=[
 # (키워드들, 라벨, 템포계수, 추가 악기, 선법·질감 지시)
 (["익살","정겨","활기","흥"],   "해학·활기",   1.18, ["소리북","꽹과리"], "자진모리로 빠르게, 밝은 평조 섞기(사건 후엔 급반전)"),
 (["애처","애절","애틋","비극","슬픔"],"애가(哀歌)", 0.86, ["아쟁","해금"],   "긴 시김새·낮은 음역의 흐느끼는 선율, 계면조 심화"),
 (["음산","스산","음습","서늘","으스스"],"음산·괴담", 0.80, ["징","박(拍)"],   "무음(여백)과 잔향 강조, 불협 지속음, 저역 드론"),
 (["기묘","기이","도술","신비","몽환"],"기이·신비", 0.92, ["대금","요령"],   "미세한 음정 흔들림(하모닉스), 비현실적 잔향"),
 (["우아","화사","나른","아름"],   "우아·화사",   0.95, ["편경","고쟁"],   "부드러운 장식음, 넓은 여백, 맑은 배음"),
 (["무섭","조마조마","불안","긴장"],"불안·서스펜스",1.05,["프레임드럼","저현"],"심장박동 같은 저역 펄스, 반음 접근"),
 (["장엄","의식","성스"],        "장엄·의식",   0.88, ["범종","징"],     "긴 타종 잔향 위 느린 창(唱), 장중한 지속음"),
 (["차갑","얼음","겨울","눈"],    "한랭·결빙",   0.90, ["칸텔레","글라스하프"],"고음역 공명·서리 같은 배음, 잔향 길게"),
]
def tone_mod(s):
    blob=" ".join([s.get("adapted_story",{}).get("tone",""),
                   s.get("adapted_story",{}).get("tone_shift",""),
                   s.get("adapted_story",{}).get("palette",""),
                   s.get("trick",{}).get("name",""), s.get("trick",{}).get("desc","")])
    hits=[m for m in TONE_MODS if any(k in blob for k in m[0])]
    if not hits: return ("표준",1.0,[],"기본 선법 유지")
    # 가장 먼저 매칭된 둘까지 결합
    lab="+".join(h[1] for h in hits[:2])
    mult=1.0
    for h in hits[:2]: mult*=h[2]
    inst=[];
    for h in hits[:2]: inst+=h[3]
    note=" / ".join(h[4] for h in hits[:2])
    return (lab, round(mult,3), inst, note)

def build_bgm(s):
    key=pick_palette(s); P=PALETTES[key]
    ad=s.get("adapted_story",{}); sr=s["background"]["setting_raw"]
    tone=ad.get("tone",""); shift=ad.get("tone_shift",""); pal=ad.get("palette","")
    trick=s.get("trick",{}).get("name","")
    lo,hi=P["tempo_range"]
    tlab,tmult,tinst,tnote=tone_mod(s)
    # 작품별 고유 시드(제목 해시) — 같은 문화·톤이어도 미세하게 다르게
    seed=sum(ord(ch) for ch in s["meta"]["title"])%7-3   # -3..+3 BPM
    cues={}
    for cid,when,inten,mood,form in CUE_SPEC:
        bpm=int(round((lo+(hi-lo)*inten)*tmult))+seed
        bpm=max(32,min(160,bpm))
        # 국면별 편성: 저강도=소편성, 고강도=전체 + 톤 시그니처 악기
        n=max(2,min(len(P["instruments"]), 2+int(inten*4)))
        inst=(P["instruments"][:n] if inten<0.8 else list(P["instruments"]))
        for x in tinst:
            if x not in inst: inst.append(x)
        mode=(P["scale"] if cid in ("intro","ending") else P["scale"]+" · 불협/긴장 추가")+f" · [{tlab}] {tnote}"
        prompt=(f"{P['en']}. Scene: {when}. Mood: {mood} ({tlab}). "
                f"Tempo {bpm} BPM. Instruments: {', '.join(inst)}. "
                f"Setting: {sr.get('era','')}, {sr.get('location','')}. "
                f"Story: {s['meta']['origin']} — {trick}. "
                f"Overall tone: {tone}"+(f" shifting to: {shift}" if cid in ('discovery','climax','reveal') else "")+
                f". No vocals with lyrics. Avoid: {', '.join(P['avoid'])}.")
        cues[cid]={"name":f"{s['meta']['title']} — {when}","when":when,"bpm":bpm,
                   "key_mode":mode,"instruments":inst,
                   "dynamics":("pp~mp" if inten<0.6 else ("mf" if inten<0.85 else "f~ff")),
                   "form":form,"mood":mood,"prompt":prompt}
    tlab2,tmult2,tinst2,tnote2=tone_mod(s)
    return {"palette":{"culture_key":key,"label":P["label"],"tone_modifier":tlab2,"tone_note":tnote2,"signature_add":tinst2,"instruments":P["instruments"],
                       "scale":P["scale"],"tempo_range":P["tempo_range"],"texture":P["texture"],
                       "percussion":P["percussion"],"avoid":P["avoid"],
                       "reference_en":P["en"],
                       "derived_from":{"era":sr.get("era"),"location":sr.get("location"),
                                       "culture":sr.get("culture"),"tone":tone,"tone_shift":shift,
                                       "color_palette":pal,"trick":trick}},
            "cues":cues}

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/[0-9]*.json"
    from collections import Counter
    cnt=Counter()
    for p in sorted(glob.glob(arg)):
        s=json.load(open(p,encoding="utf-8"))
        s["bgm"]=build_bgm(s)
        cnt[s["bgm"]["palette"]["culture_key"]]+=1
        json.dump(s,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        print(f"  ♪ {p.split('/')[-1]:26} → {s['bgm']['palette']['label']:18} "
              f"{s['bgm']['cues']['interrogation']['bpm']}BPM · {', '.join(s['bgm']['cues']['intro']['instruments'][:3])}")
    print(f"\n문화권 분포: {dict(cnt)}  (총 {sum(cnt.values())}편 · 서로 다른 음악 팔레트 {len(cnt)}종)")
