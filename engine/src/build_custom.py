# -*- coding: utf-8 -*-
"""
build_custom.py — 사용자 입력(배경·인물·짧은 스토리)으로 추리게임 한 편을 설계한다.

입력 예:
{
  "background": "2020년대 서울, 야근이 일상인 스타트업 사무실",
  "characters": ["까칠한 CTO","말 많은 디자이너","조용한 인턴","돈 밝히는 영업팀장","퇴사 앞둔 개발자"],
  "story": "투자 유치 발표 전날 밤, 대표가 회의실에서 죽은 채 발견된다.",
  "victim": "대표",
  "options": {"tone":"차갑고 건조한 도시 스릴러","difficulty":"중"}
}

동작:
  ① 입력에서 세계(era/location/culture)·트릭·흉기 결정
  ② 5인에게 동기·비밀·MMO 배분(범인 1명만 3개 완비, 가짜 유력자 2명)
  ③ 현장(무소유) + 인물별 장소로 지도 구성(이동제한이 의미 있게 좌표 배치)
  ④ 라운드별 단서 그래프(결정적 단서 R3, 알리바이 증언, 레드헤링)
  ⑤ 도입 나레이션 8비트(평온→충격, 사용자 스토리를 실제로 들려줌)
  ⑥ 후처리 주입(BGM·음성·검색·행동지침·탐정 배역)
  ⑦ 8게이트 검증 → 통과분만 저장

사용:
  python build_custom.py custom_input.json out/21_커스텀.json
  python build_custom.py --demo            # 내장 예시로 생성
"""
import json, sys, math, os, re

# ── 배경에서 세계 추정 ────────────────────────────────────────────
def infer_world(bg, story):
    blob=bg+" "+story
    # 주의: 짧은 낱말('성')로 부분일치를 보면 '경성'이 중세로 잡힌다 → 구체적인 말만 쓴다.
    if any(k in blob for k in ["스타트업","사무실","오피스","회사","IT기업","테크","연구소"]):
        era="현대(2020년대)"; culture="현대 한국 도시·오피스"; modern=True
    elif any(k in blob for k in ["경성","일제강점기","1920","1930","개화기","근대"]):
        era="근대(1920~30년대 경성)"; culture="근대 한국 도시"; modern=True
    elif any(k in blob for k in ["19세기","빅토리아","벨 에포크"]):
        era="근대 유럽(19세기)"; culture="근대 유럽 도시"; modern=True
    elif any(k in blob for k in ["조선","사또","양반","한옥","저잣거리"]):
        era="조선"; culture="한국 전통"; modern=False
    elif any(k in blob for k in ["중세","영주","왕국","성채","기사단","수도원"]):
        era="중세 유럽"; culture="서구 중세"; modern=False
    elif any(k in blob for k in ["현대","서울","아파트","도시","21세기","오늘날","2020"]):
        era="현대(2020년대)"; culture="현대 한국 도시"; modern=True
    else:
        era="현대(2020년대)"; culture="현대 도시"; modern=True
    return {"era":era, "location":bg, "culture":culture}, modern

# ── 현대/고전별 트릭·흉기 프리셋 ──────────────────────────────────
MODERN_TRICK=dict(
  name="휴대폰 두고 알리바이 위조(phone_left_behind)",
  desc="범인은 휴대폰을 제자리에 둔 채 현장에 다녀와, 기지국·앱 기록상 다른 곳에 있던 것처럼 꾸몄다. "
       "그러나 그 시간대만 잠금 해제·걸음 수가 통째로 비어 있다.",
  weapon="유리 문진(둔기)", weapon_class="둔기 타격",
  method="회의실에서 유리 문진으로 뒤통수를 가격해 살해하고, 휴대폰을 제자리에 두어 알리바이를 만듦",
  decisive="휴대폰은 자리에 있었지만 그 시간대만 잠금 해제·걸음 수 기록이 완전히 비어 있다. "
           "게다가 사각지대 통로의 앞뒤 카메라에 같은 인물이 프레임 밖으로 사라졌다 나타난다.")

# ── 인물 원형(성격·말투·음성) ────────────────────────────────────
ARCHETYPES=[
 dict(personality="까칠하고 단호하며 계산적이다", speech="딱딱하고 짧은 존댓말", voice="낮고 건조한 음성"),
 dict(personality="수다스럽고 눈치 빠르다", speech="빠르고 친근한 반존대", voice="높고 빠른 음성"),
 dict(personality="조용하고 소심하며 방어적이다", speech="조심스럽고 작은 존댓말", voice="가늘고 떨리는 음성"),
 dict(personality="능글맞고 잇속에 밝다", speech="넉살 좋은 존댓말", voice="걸걸하고 능청스러운 음성"),
 dict(personality="지쳐 있고 냉소적이다", speech="힘 빠진 존댓말", voice="낮고 가라앉은 음성"),
]
SECRET_KINDS=[
 ("사내 정보를 경쟁사에 넘겼다","정보유출",["유출","경쟁사","자료","넘겼"]),
 ("회사 돈을 개인 계좌로 빼돌렸다","횡령",["횡령","자금","계좌","빼돌"]),
 ("경력과 학력을 위조해 입사했다","경력위조",["경력","위조","학력","이력서"]),
 ("사내 관계를 숨기고 있었다","사내연애",["관계","연애","사귀","숨긴"]),
 ("몰래 이직을 준비하며 자료를 복사했다","이직준비",["이직","복사","면접","준비"]),
]
MOTIVES=[
 ("해고를 통보받아 앞길이 막혔다","해고 통보에 대한 분노"),
 ("공을 가로채여 성과를 빼앗겼다","성과를 빼앗긴 원한"),
 ("비리를 들켜 폭로당할 처지였다","비리 발각 — 입막음"),
 ("지분과 보상을 두고 다퉜다","지분 다툼"),
 ("오래 모욕당하며 눌려 지냈다","누적된 모욕에 대한 앙갚음"),
]

def name_for(role, i):
    """역할 문자열에서 이름을 만든다(사용자가 이름을 줬으면 그대로)."""
    if re.search(r"[가-힣]{2,4}\s*\(", role): return role.split("(")[0].strip()
    SURNAME=["강","윤","한","서","임","오","백","조"]
    GIVEN=["도현","세라","민준","가온","태윤","해수","지호","은결"]
    return f"{SURNAME[i%len(SURNAME)]}{GIVEN[i%len(GIVEN)]}"

def build(inp):
    bg=inp["background"]; story=inp["story"]
    roles=inp.get("characters") or ["동료 A","동료 B","동료 C","동료 D","동료 E"]
    roles=(roles+["동료"]*5)[:5]
    victim_role=inp.get("victim") or "피해자"
    opt=inp.get("options") or {}
    setting,modern=infer_world(bg,story)
    T=MODERN_TRICK
    tone=opt.get("tone") or "차갑고 건조한 도시 스릴러"
    slots=["초저녁","밤","새벽"]

    # 인물 구성: C4를 범인, C2·C5를 가짜 유력자(2/3), C1·C3는 알리바이 확정
    cast=[]
    for i,role in enumerate(roles):
        cid=f"C{i+1}"; a=ARCHETYPES[i%5]
        sec_txt,sec_type,sec_trig=SECRET_KINDS[i%5]
        kill,label=MOTIVES[i%5]
        cast.append(dict(id=cid, name=name_for(role,i), public=role, arche=a,
                         secret=dict(text=sec_txt,type=sec_type), trig=sec_trig,
                         kill=kill, label=label))
    CUL=3   # index of culprit (C4)
    FALSE=[1,4]  # 가짜 유력자
    # 장소: PC(현장) + 5인 자리. 실제 동선은 가깝게, 나머지는 멀게(이동제한 의미)
    POS={"PC":[0.0,0.0],"P1":[1.1,-0.9],"P2":[-1.2,0.7],"P3":[0.5,2.6],"P4":[-0.6,-1.6],"P5":[3.2,1.4]}
    PLACE_NAMES=["회의실(현장)","각자 자리(오픈오피스)","탕비실","디자인실","서버실","옥상 흡연장"]
    places=[dict(id="PC",name=PLACE_NAMES[0],owner=None,pos=POS["PC"],
                 desc="투자 발표 자료가 띄워진 채 꺼진 대형 모니터, 넘어진 의자와 흩어진 출력물",
                 features=["뒤통수 함몰 상처와 쓰러진 자리","넘어진 의자와 흩어진 발표 자료","닦인 듯 지문이 없는 유리 문진"])]
    for i in range(5):
        pid=f"P{i+1}"
        places.append(dict(id=pid,name=PLACE_NAMES[i+1],owner=f"C{i+1}",pos=POS[pid],
            desc=f"{cast[i]['name']}이(가) 주로 머무는 {PLACE_NAMES[i+1]}, 개인 물건과 업무 흔적",
            features=[f"{cast[i]['name']}의 개인 물건과 업무 자취", "그날 밤 남은 흔적", "동료들이 오간 자리"]))
    pn={p["id"]:p["name"] for p in places}

    # 동선: 범인만 밤에 현장. 알리바이 확정자(C1,C3)는 자기 자리 고정.
    tl={}
    tl["C1"]={"초저녁":"P1","밤":"P1","새벽":"P1"}
    tl["C2"]={"초저녁":"PC","밤":"P2","새벽":"P2"}   # 초저녁만 현장(가짜 유력자)
    tl["C3"]={"초저녁":"P3","밤":"P3","새벽":"P3"}
    tl["C4"]={"초저녁":"P4","밤":"PC","새벽":"P4"}   # 범인
    tl["C5"]={"초저녁":"PC","밤":"P5","새벽":"P5"}   # 초저녁만 현장(가짜 유력자)

    def mk(c,i):
        cid=c["id"]; a=c["arche"]; is_cul=(i==CUL)
        mmo=dict(means=is_cul, motive=True, opportunity=(i in [CUL]+FALSE))
        life=(f"{c['name']}은(는) {c['public']}으로 이 조직에 들어와, 밤낮없이 일하며 자리를 지켜 온 사람이다. "
              f"겉으로는 {a['personality'][:12]} 인상을 주지만, 속으로는 {c['kill']} "
              f"그 일로 오래 마음을 앓았고, 아무에게도 말하지 못한 사정이 하나 있다 — {c['secret']['text']}. "
              f"그것이 드러나면 이 바닥에서 다시 일하기 어렵다는 걸 알기에, 그는 늘 조심스럽게 처신했다. "
              f"투자 발표를 앞둔 그 주에는 야근이 이어졌고, 사무실의 공기는 눌린 듯 팽팽했다. "
              f"그날 밤에도 그는 자기 자리에서 화면을 들여다보며, 저마다의 셈을 하고 있었다.")
        pp=[dict(trigger=c["trig"],
                 reveals=f"…{c['secret']['text']}는 건… 사실입니다. 허나 그건 제 사정이지, 사람을 해친 일이 아닙니다.",
                 unlocks=c["secret"]["type"])]
        d=dict(id=cid,name=c["name"],public=c["public"],
               profile=dict(name=c["name"],age=f"{20+ (i%3)*10}대",sex="여" if i%2 else "남",
                            relation="동료",status=c["public"]),
               kill_motive=c["kill"], motive_label=c["label"], secret=c["secret"],
               timeline=tl[cid],
               alibi_narration=("저는 밤엔 제 자리에 있었습니다. 옆자리 동료들이 봤을 겁니다."
                                if not is_cul else
                                "저는 밤엔 서버실에 있었습니다. 휴대폰 기록을 보시면 아실 겁니다."),
               persona=dict(personality=a["personality"],speech_style=a["speech"],
                            voice_hint=a["voice"],
                            example_line=f"제가 그럴 이유가 어디 있습니까.",
                            example_lines=[f"제가 그럴 이유가 어디 있습니까.",
                                           "그날 밤엔 제 자리에 있었습니다."]),
               bio=f"{c['public']}. {c['kill']}",
               life_story=life, pressure_points=pp, mmo=mmo, is_culprit=is_cul, lies=[])
        if is_cul:
            d["lies"]=[dict(claim="밤엔 서버실에 있었고 휴대폰 기록이 그걸 증명한다",
                            truth="휴대폰만 두고 회의실로 가 유리 문진으로 대표를 가격했다",
                            false_place="P5")]
            d["alibi_narration"]="저는 밤엔 서버실에 있었습니다. 휴대폰 기록을 보시면 아실 겁니다."
            d["persona"]["example_lines"]=["제 휴대폰 기록을 보십시오.","그 시간에 저는 서버실에 있었습니다."]
        return d

    CAST=[mk(c,i) for i,c in enumerate(cast)]
    vic_name=name_for(victim_role,7)
    clues=[
      dict(id="K1",channel="crime_scene",medium="부검",surface="뒤통수의 함몰 상처 — 무겁고 단단한 물건에 맞은 것.",
           implies="weapon_class=둔기. 회의실에 있던 유리 문진이 유력.",weight="weapon",points_to=None,exculpates=[],reveal_round=1,decisive=False),
      dict(id="K2",channel="crime_scene",medium="현장",surface="유리 문진에 지문이 하나도 없다 — 닦인 것이다.",
           implies="누군가 손댄 뒤 지웠다. 다만 누구인지는 알 수 없다(함정).",weight="red_herring",points_to=None,exculpates=[],reveal_round=1,decisive=False),
      dict(id="K3",channel="spine",medium="증언",surface=f"옆자리 동료들: '{CAST[0]['name']}씨는 밤새 자리에 있었어요. 계속 화면 보고 있었고요.'",
           implies="C1은 자기 자리에 체류 → 현장 부재.",weight="exculpating",points_to=None,exculpates=["C1"],reveal_round=1,decisive=False),
      dict(id="K4",channel="spine",medium="증언",surface=f"야근하던 팀원: '{CAST[2]['name']}씨는 밤새 디자인실에 있었습니다. 같이 작업했어요.'",
           implies="C3은 디자인실에 체류 → 현장 부재.",weight="exculpating",points_to=None,exculpates=["C3"],reveal_round=2,decisive=False),
      dict(id="K5",channel="spine",medium="부검",surface="사망 추정 시각은 밤. 저항 흔적이 없어 경계하지 않은 상대로 보인다.",
           implies="가까운 동료의 소행을 시사(누구인지까지는 특정 못 함).",weight="context",points_to=None,exculpates=[],reveal_round=2,decisive=False),
      dict(id="K6",channel="spine",medium="증언",surface="보안팀: '초저녁엔 회의실에 여러 명이 드나들었습니다. 밤엔 기록이 없고요.'",
           implies="초저녁 현장 출입은 여럿(기회) — 정황만으론 특정 불가.",weight="context",points_to=None,exculpates=[],reveal_round=3,decisive=False),
    ]
    for i in range(5):
        cid=f"C{i+1}"; pid=f"P{i+1}"
        clues.append(dict(id=f"L{i+1}",channel="location",medium="물건",location=pid,
            surface=f"{pn[pid]}에서 나온 {CAST[i]['name']}의 개인적 흔적 — {CAST[i]['secret']['text']}",
            implies=f"{cid}의 비밀={CAST[i]['secret']['type']}. 살인과는 별개(레드헤링).",
            weight="red_herring",points_to=None,exculpates=[],reveal_round=2,decisive=False))
    clues.append(dict(id="LDEC",channel="location",medium="디지털포렌식",location="PC",
        surface=T["decisive"],
        implies=f"휴대폰만 자리에 있었고 사람은 없었다 → {CAST[CUL]['name']}(C4)를 지목. "
                f"초저녁에만 현장에 있던 두 사람은 이 밤의 기록과 무관 → 배제.",
        weight="incriminating",points_to="C4",exculpates=["C2","C5"],reveal_round=3,decisive=True))

    narr=[
      dict(beat=1,mood="평온",focus="world",scene=bg,
           text=f"{bg}. 투자 유치 발표를 앞둔 그 주, 사무실의 불은 새벽까지 꺼지지 않았다. 사람들은 저마다 화면 앞에 붙어 앉아 밤을 넘겼다."),
      dict(beat=2,mood="흥미",focus="C1",scene="첫 번째 인물",
           text=f"{CAST[0]['name']}은(는) {CAST[0]['public']}이었다. {CAST[0]['kill_motive']} 그 일을 마음에 담아 두고 있었다."),
      dict(beat=3,mood="의미심장",focus="C2",scene="두 번째 인물",
           text=f"{CAST[1]['name']}은(는) {CAST[1]['public']}. {CAST[1]['kill_motive']} 겉으론 웃었지만 속은 달랐다."),
      dict(beat=4,mood="불안",focus="C3",scene="세 번째 인물",
           text=f"{CAST[2]['name']}은(는) {CAST[2]['public']}으로, {CAST[2]['kill_motive']} 아무에게도 그 말을 하지 못했다."),
      dict(beat=5,mood="의미심장",focus="C4",scene="네 번째 인물",
           text=f"{CAST[3]['name']}은(는) {CAST[3]['public']}이었다. {CAST[3]['kill_motive']} 그 밤 그의 자리엔 휴대폰만 놓여 있었다."),
      dict(beat=6,mood="불안",focus="C5",scene="다섯 번째 인물",
           text=f"{CAST[4]['name']}은(는) {CAST[4]['public']}. {CAST[4]['kill_motive']} 발표를 앞두고 유난히 예민해져 있었다."),
      dict(beat=7,mood="고요",focus="victim",scene="혼자 남은 대표",
           text=f"그 밤 {vic_name} 대표는 회의실에 홀로 남아 발표 자료를 손봤다. 복도의 불이 하나둘 꺼지고, 사무실은 조용해졌다."),
      dict(beat=8,mood="충격",focus="victim",scene="회의실의 주검",
           text=f"{story} 뒤통수엔 무거운 것에 맞은 자국이 있었고, 유리 문진에서는 지문이 말끔히 지워져 있었다. 지금까지의 이야기는 여기서 끝난다."),
    ]

    # 이동 제한: 실제 필요 이동만 허용
    pl={p["id"]:p for p in places}
    def d(a,b): return math.hypot(a["pos"][0]-b["pos"][0], a["pos"][1]-b["pos"][1])
    mx=0
    for c in CAST:
        seq=[pl[c["timeline"][sl]] for sl in slots]
        for a,b in zip(seq,seq[1:]): mx=max(mx,d(a,b))

    s={
      "meta":{"origin":"사용자 커스텀","era":setting["era"],"title":inp.get("title") or "회의실의 유리 문진"},
      "background":{"setting_raw":setting,"atmosphere":f"{bg}. 발표를 앞둔 긴장과 피로가 겹친 공간"},
      "adapted_story":{"tone":tone,
        "tone_shift":"야근의 일상이 뒤집혀 회의실의 둔기 살인극으로 반전",
        "palette":"형광등의 창백한 백색·모니터 불빛 → 사건 후 검붉은 자국과 꺼진 화면"},
      "trick":{"name":T["name"],"desc":T["desc"]},
      "intro":{"original_summary":f"{bg}에서 투자 발표를 앞두고 야근이 이어지던 나날.",
               "twist":story,"narration":narr},
      "victim":{"name":vic_name,"role":victim_role,
        "bio":(f"{vic_name}은(는) 이 조직을 세우고 키워 온 대표다. 성과에 밝고 결단이 빨라 회사를 여기까지 끌고 왔으나, "
               f"그 과정에서 사람을 도구처럼 쓰는 일이 잦았다. 공을 가로채고, 해고를 통보하고, 지분과 보상을 두고 다투며 "
               f"곁의 사람들에게 크고 작은 상처를 남겼다. 투자 유치를 앞두고는 더욱 예민해져, 팀원들의 비리와 약점까지 "
               f"들추어 쥐고 흔들었다. 발표만 성공하면 모든 것이 정리된다고 믿었기에, 그는 마지막까지 회의실에 홀로 남아 "
               f"자료를 다듬었다. 그러나 그가 쥐고 있던 약점들은, 누군가에게는 목숨보다 무거운 것이었다.")},
      "death":{"time_slot":"밤","place":"PC","weapon":T["weapon"],"weapon_class":T["weapon_class"],
        "method":T["method"],
        "scene_description":"회의실 테이블 앞에 대표가 쓰러져 있다. 뒤통수에 함몰 상처가 있고, 곁에 유리 문진이 놓여 있다.",
        "scene_inspection":[
          "뒤통수의 함몰 상처 — 무겁고 단단한 물건에 맞은 것.",
          "유리 문진에 지문이 하나도 없다 — 닦였다는 뜻.",
          "저항 흔적이 없다 — 경계하지 않은 상대가 뒤에서 접근했다.",
          "책상엔 발표 자료가 그대로다 — 자료를 노린 것이 아니다."]},
      "time_slots":slots,
      "map":{"max_move_per_slot":round(mx+0.3,2),"places":places},
      "cast":CAST,"clue_graph":clues,
      "choices":{"culprit":[c["id"] for c in CAST],
                 "weapon":[T["weapon"],"노트북(둔기)","커터칼","넥타이(교살)","수면제"]},
      "answer_format":{"culprit":"choice","weapon":"choice","motive":"free_text"},
      "solution":{"culprit":"C4","motive_label":CAST[CUL]["motive_label"],
        "motive_keywords":["비리","발각","폭로","입막음","해고","성과","지분"]+CAST[CUL]["secret"]["type"].split(),
        "weapon":T["weapon"],
        "reason":f"{CAST[CUL]['name']}이(가) {CAST[CUL]['kill_motive']} 그 일로 대표와 갈등하던 끝에, "
                 f"휴대폰을 자리에 둔 채 회의실로 가 유리 문진으로 뒤통수를 가격했다. "
                 f"휴대폰은 자리에 있었지만 그 시간대만 사용 기록이 비어 있고, 사각지대 통로의 앞뒤 카메라가 그를 가리킨다."},
      "config":{"suspects":5,"rounds":3,"attempts":3,"turns_per_round":8},
    }
    return s

def postprocess_and_verify(s, outpath):
    from add_bgm import build_bgm
    from add_bgm2 import build_v2
    from add_search import build_search
    from add_voice import build_voice
    from add_acts import dirs_for
    from add_detective import build as build_det
    from enrich_agents import enrich_cast
    s["bgm"]=build_bgm(s); s["bgm"]=build_v2(s)
    s["search"]=build_search(s); s["voice"]=build_voice(s)
    for c in s["cast"]: c["act_directions"]=dirs_for(s,c)
    s["detective"]=build_det(s); enrich_cast(s)
    # ★ 관계·서사는 여기서 실질을 갖춘다.
    #   enrich_cast는 빈칸만 메운다("…얽힌 사이"). 그대로 두면 심문에서
    #   모델이 상대를 지어낸다. relweb이 두 사람만의 얽힘을 만들고,
    #   relate가 그것을 시나리오 사실과 엮어 인물 시점으로 다시 쓴다.
    from relweb import build_web
    from relate import rewrite as rewrite_relations
    if not s.get("relation_web"): s["relation_web"]=build_web(s)
    rewrite_relations(s)

    from verify import verify, _print
    from difficulty import difficulty_gate
    from playtest import trace
    from agent_lint import lint, secret_lint
    from simulate import simulate, tier
    from checklist import check
    from fun import check_fun
    from ux_lint import lint as uxlint
    ok,rep=verify(s); g=difficulty_gate(s); l=lint(s); sec=secret_lint(s)
    pl=trace(s,verbose=False)[0]; ux=uxlint(s); f_ok,f_score=check_fun(s)
    R,rate=check(s); npass=sum(1 for _,c,_ in R if c)
    t,_=tier(rate)
    print(f"  논리 {'✅' if ok else '❌'} | 난이도 {'✅' if g[0] else '❌'} | 플레이 {'✅' if pl else '❌'} | "
          f"자기오류 {'✅' if l[0] else '❌'} | 비밀 {'✅' if sec[0] else '❌'} | UX {'✅' if ux[0] else '❌'}")
    print(f"  체크리스트 {npass}/{len(R)} · 재미 {f_score}/100 · 정답률 {rate:.2f} {t}")
    if not ok: _print([r for r in rep if not r[1]])
    for r in g[1]: print("   [난이도]",r)
    for x in (l[1]+sec[1])[:5]: print("   [린트]",x)
    for k,m in ux[1][:6]: print("   [UX]",k,m)
    allok = ok and g[0] and pl and l[0] and sec[0] and ux[0] and f_ok and npass==len(R) and 0.30<=rate<=0.85
    if allok:
        json.dump(s,open(outpath,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        print("  저장:",outpath)
    else:
        print("  (미저장 — 게이트 미통과)")
    return allok

DEMO={
  "background":"2020년대 서울, 야근이 일상인 스타트업 사무실",
  "characters":["까칠한 CTO","말 많은 디자이너","조용한 인턴","돈 밝히는 영업팀장","퇴사 앞둔 개발자"],
  "story":"투자 유치 발표 전날 밤, 대표가 회의실에서 죽은 채 발견된다.",
  "victim":"대표",
  "options":{"tone":"차갑고 건조한 도시 스릴러"}
}

if __name__=="__main__":
    if "--demo" in sys.argv:
        inp=DEMO; out=sys.argv[sys.argv.index("--demo")+1] if len(sys.argv)>sys.argv.index("--demo")+1 else "scenarios/21_커스텀_스타트업.json"
    else:
        inp=json.load(open(sys.argv[1],encoding="utf-8")); out=sys.argv[2]
    print("=== 사용자 입력 ===")
    print(" 배경:",inp["background"]); print(" 스토리:",inp["story"])
    print(" 인물:",", ".join(inp.get("characters") or []))
    print("\n=== 생성 ===")
    s=build(inp)
    print(f" 세계: {s['background']['setting_raw']['era']} / {s['background']['setting_raw']['culture']}")
    print(f" 트릭: {s['trick']['name']}")
    print(f" 배역: (후처리에서 결정)")
    print("\n=== 검증 ===")
    postprocess_and_verify(s, out)
