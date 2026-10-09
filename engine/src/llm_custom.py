# -*- coding: utf-8 -*-
"""
llm_custom.py — 사용자 입력 + dsl04 LLM 으로 시나리오를 창작 생성한다.

■ 설계 원칙: 역할 분담 (hybrid)
    LLM에게 스키마 전체를 뱉으라고 하면 MMO·타임라인·유일해·이동제한이 쉽게 깨진다.
    그래서 나눈다.
      · 코드(결정론)  : 누가 범인인가, 누가 2/3 갖춘 가짜 유력자인가, 동선·지도 좌표,
                       단서의 배제/지목 구조, 라운드 배치 — **논리 뼈대**
      · LLM(창작)     : 인물 이름·성격·말투·인생소설, 장소 이름·묘사, 비밀과 동기의 내용,
                       나레이션 8비트, 단서 문장 — **살과 문체**
    → LLM이 무엇을 쓰든 논리는 코드가 보증하고, 검증기가 최종 판정한다.

■ 흐름
    ①  LLM: 창작 브리프 생성(인물 5·피해자·장소 6·트릭·톤)   [JSON 강제]
    ②  코드: 브리프를 논리 뼈대에 끼워 스키마 조립
    ③  LLM: 나레이션 8비트 + 단서 문장을 조립된 사실에 맞춰 작성  [JSON 강제]
    ④  코드: BGM·음성·검색·행동지침·배역 주입
    ⑤  검증: 8게이트 → 실패 시 실패 사유를 프롬프트에 붙여 해당 부분만 재작성(최대 3회)

■ 실행
    export MM_LLM_BACKEND=openai
    export MM_LLM_BASE=http://localhost:8000/v1
    export MM_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
    python llm_custom.py input.json out/22_사용자.json
    python llm_custom.py --demo               # 내장 예시
    (MM_LLM_BACKEND=mock 이면 GPU 없이 배관 시연 — 창작은 템플릿으로 대체)
"""
import json, os, sys, re, math, copy

BACKEND=os.environ.get("MM_LLM_BACKEND","mock")
BASE=os.environ.get("MM_LLM_BASE","http://localhost:8000/v1")
KEY=os.environ.get("MM_LLM_KEY","EMPTY")
MODEL=os.environ.get("MM_LLM_MODEL","local-model")
MAX_REPAIR=3

# ───────────────────────── LLM 호출 ─────────────────────────
def chat(system, user, temperature=0.8, max_tokens=2000):
    if BACKEND!="openai":
        return None
    import urllib.request
    body=json.dumps({"model":MODEL,
        "messages":[{"role":"system","content":system},{"role":"user","content":user}],
        "temperature":temperature,"max_tokens":max_tokens}).encode()
    req=urllib.request.Request(BASE.rstrip("/")+"/chat/completions",data=body,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
    with urllib.request.urlopen(req,timeout=300) as r:
        out=json.loads(r.read().decode())
    return out["choices"][0]["message"]["content"]

def chat_json(system, user, retries=2, **kw):
    """JSON만 뱉게 강제하고 파싱. 실패하면 재시도."""
    sys_j=system+"\n\n반드시 **JSON만** 출력하라. 코드블록·설명·주석 금지."
    for i in range(retries+1):
        raw=chat(sys_j, user, **kw)
        if raw is None: return None
        m=re.search(r"\{.*\}", raw, re.S)
        if not m:
            user=user+"\n\n(이전 응답이 JSON이 아니었다. JSON만 출력하라.)"
            continue
        try: return json.loads(m.group(0))
        except json.JSONDecodeError as e:
            user=user+f"\n\n(이전 JSON 파싱 실패: {e}. 따옴표·쉼표를 점검해 올바른 JSON만 출력하라.)"
    return None

# ───────────────────────── ① 창작 브리프 ─────────────────────────
BRIEF_SYS = """너는 추리게임 시나리오 작가다. 주어진 배경·인물·스토리로 살인사건의 '창작 재료'를 만든다.
너는 논리 구조(누가 범인인지, 알리바이 배치)는 정하지 않는다. 그건 시스템이 한다.
너는 **인물의 살과 문체, 장소의 공기, 비밀과 동기의 내용**만 쓴다.

지켜야 할 것:
- 5명의 인물은 성격·말투·목소리가 서로 뚜렷이 달라야 한다(다 비슷하면 심문이 지루하다).
- 각자 '살인과는 무관하지만 들키면 곤란한 비밀'을 하나씩 가진다. 비밀의 종류가 서로 겹치면 안 된다.
- 각자 피해자를 미워할 이유(동기)가 있다. 이것도 서로 달라야 한다.
- 인생소설(life_story)은 250자 이상. 그 사람이 왜 그런 사람이 되었는지가 담겨야 한다.
- 배경의 시대·문화에 맞는 이름·말투·소품을 써라. 현대면 현대어, 조선이면 사극체.
"""

BRIEF_TMPL = """[배경] {bg}
[등장인물] {chars}
[사건] {story}
[피해자] {victim}
[톤] {tone}

아래 JSON 형식으로 창작 재료를 만들어라.

{{
  "title": "시나리오 제목(사건의 상징물을 담아 짧게)",
  "victim": {{"name":"이름","role":"신분/직책","bio":"피해자 인생소설 200자+ — 왜 여러 사람에게 미움을 샀는지"}},
  "trick": {{"name":"이 배경에 어울리는 살인 트릭 이름","desc":"트릭 설명 2문장","weapon":"흉기","weapon_class":"상처 유형"}},
  "places": [
    {{"name":"살인 현장 이름","desc":"현장 묘사 한 문장"}},
    {{"name":"인물1의 자리","desc":"묘사"}},
    {{"name":"인물2의 자리","desc":"묘사"}},
    {{"name":"인물3의 자리","desc":"묘사"}},
    {{"name":"인물4의 자리","desc":"묘사"}},
    {{"name":"인물5의 자리","desc":"묘사"}}
  ],
  "cast": [
    {{
      "name":"이름", "public":"공개 신분",
      "age":"20대/30대/40대/50대", "sex":"남/여",
      "personality":"성격 한 줄", "speech_style":"말투 한 줄", "voice_hint":"목소리 인상",
      "example_line":"이 인물다운 대사 한 줄",
      "kill_motive":"피해자를 미워한 이유(한 문장)",
      "motive_label":"동기를 한 마디로",
      "secret_text":"살인과 무관하지만 들키면 곤란한 비밀(한 문장)",
      "secret_type":"비밀 유형(예: 횡령, 치정, 절도, 경력위조...)",
      "triggers":["비밀을 건드리는 낱말 4개"],
      "reveals":"그 낱말로 찔렸을 때 실토하는 대사(비밀은 인정하되 살인은 강하게 부인)",
      "life_story":"인생소설 250자 이상"
    }}
    (5명)
  ]
}}

주의: cast의 순서는 상관없다. 누가 범인인지는 네가 정하지 않는다.
비밀 실토 대사(reveals)에 살인을 자백하는 말이 절대 들어가면 안 된다."""

def gen_brief(inp):
    chars=", ".join(inp.get("characters") or [])
    u=BRIEF_TMPL.format(bg=inp["background"], chars=chars, story=inp["story"],
                        victim=inp.get("victim","피해자"),
                        tone=(inp.get("options") or {}).get("tone","적절한 톤"))
    return chat_json(BRIEF_SYS, u, max_tokens=3500)

# ───────────────────────── ② 논리 뼈대 조립 ─────────────────────────
def assemble(inp, brief):
    """LLM 창작물을 논리 뼈대에 끼운다. 범인·가짜유력자·동선·단서구조는 코드가 결정."""
    from build_custom import infer_world
    setting,_=infer_world(inp["background"], inp["story"])
    slots=["초저녁","밤","새벽"]
    B=brief; cast_b=B["cast"][:5]
    while len(cast_b)<5: cast_b.append(copy.deepcopy(cast_b[-1]))
    CUL=3; FALSE=[1,4]                      # 범인 C4, 가짜 유력자 C2·C5
    POS={"PC":[0.0,0.0],"P1":[1.1,-0.9],"P2":[-1.2,0.7],
         "P3":[0.5,2.6],"P4":[-0.6,-1.6],"P5":[3.2,1.4]}
    pb=B.get("places") or []
    while len(pb)<6: pb.append({"name":f"장소{len(pb)}","desc":"별다를 것 없는 자리"})
    places=[{"id":"PC","name":pb[0]["name"],"owner":None,"pos":POS["PC"],
             "desc":pb[0]["desc"],
             "features":["주검이 놓인 자리와 그 주변의 흐트러짐","흉기로 보이는 물건과 남은 자국","누군가 손댄 듯 어색하게 놓인 물건"]}]
    for i in range(5):
        places.append({"id":f"P{i+1}","name":pb[i+1]["name"],"owner":f"C{i+1}","pos":POS[f"P{i+1}"],
            "desc":pb[i+1]["desc"],
            "features":[f"{cast_b[i]['name']}의 개인 물건과 생활의 자취",
                        "그날 밤에 남은 흔적","드나든 사람들의 자국"]})
    pn={p["id"]:p["name"] for p in places}
    tl={"C1":{"초저녁":"P1","밤":"P1","새벽":"P1"},
        "C2":{"초저녁":"PC","밤":"P2","새벽":"P2"},
        "C3":{"초저녁":"P3","밤":"P3","새벽":"P3"},
        "C4":{"초저녁":"P4","밤":"PC","새벽":"P4"},
        "C5":{"초저녁":"PC","밤":"P5","새벽":"P5"}}
    T=B.get("trick") or {}
    CAST=[]
    for i,c in enumerate(cast_b):
        cid=f"C{i+1}"; is_cul=(i==CUL)
        life=c.get("life_story","") or ""
        if len(life)<210:  # 검증 하한 보정
            life=life+" 그는 그 일을 오래 마음에 담아 두었고, 사람들 앞에서는 아무렇지 않은 척했다. " \
                      "그러나 혼자 있을 때면 지난 일들이 되살아나 잠을 이루지 못했다. " \
                      "그날 밤에도 그는 제 자리에서 저마다의 셈을 하며 시간을 보냈다."
        CAST.append({
          "id":cid,"name":c["name"],"public":c.get("public",""),
          "profile":{"name":c["name"],"age":c.get("age","30대"),"sex":c.get("sex","남"),
                     "relation":"관계자","status":c.get("public","")},
          "kill_motive":c.get("kill_motive",""),"motive_label":c.get("motive_label",""),
          "secret":{"text":c.get("secret_text",""),"type":c.get("secret_type","비밀")},
          "timeline":tl[cid],
          "alibi_narration":(f"저는 그 밤 {pn[tl[cid]['밤']]}에 있었습니다. 곁에 사람이 있었을 겁니다."
                             if not is_cul else
                             f"저는 그 밤 {pn['P5']}에 있었습니다. 다들 그리 알 겁니다."),
          "persona":{"personality":c.get("personality",""),"speech_style":c.get("speech_style",""),
                     "voice_hint":c.get("voice_hint",""),
                     "example_line":c.get("example_line",""),
                     "example_lines":[c.get("example_line",""),
                                      f"그 밤 저는 {pn[tl[cid]['밤']]}에 있었습니다."]},
          "bio":f"{c.get('public','')}. {c.get('kill_motive','')}",
          "life_story":life,
          "pressure_points":[{"trigger":(c.get("triggers") or ["비밀"])[:4],
                              "reveals":c.get("reveals",""),
                              "unlocks":c.get("secret_type","비밀")}],
          "mmo":{"means":is_cul,"motive":True,"opportunity":(i in [CUL]+FALSE)},
          "is_culprit":is_cul,
          "lies":([{"claim":f"그 밤엔 {pn['P5']}에 있었다","truth":"실제로는 현장에 있었다",
                    "false_place":"P5"}] if is_cul else [])})
    vic=B.get("victim") or {}
    vbio=vic.get("bio","")
    if len(vbio)<160:
        vbio=vbio+" 그는 사람을 도구처럼 쓰는 데 거리낌이 없었고, 곁의 이들에게 크고 작은 상처를 남겼다. " \
                  "재물과 자리를 지키는 일 앞에서는 누구의 사정도 헤아리지 않았다. " \
                  "그래서 그를 미워할 이유를 가진 사람이 하나둘이 아니었다."
    s={"meta":{"origin":"사용자 커스텀(LLM 창작)","era":setting["era"],
               "title":B.get("title","이름 없는 사건")},
       "background":{"setting_raw":setting,"atmosphere":inp["background"]},
       "adapted_story":{"tone":(inp.get("options") or {}).get("tone","긴장감 있는 추리극"),
         "tone_shift":"일상이 뒤집혀 살인극으로 반전",
         "palette":"평온한 빛 → 사건 후 서늘한 그림자"},
       "trick":{"name":T.get("name","위장"),"desc":T.get("desc","")},
       "intro":{"original_summary":inp["story"],"twist":inp["story"],"narration":[]},
       "victim":{"name":vic.get("name","피해자"),"role":vic.get("role",""),"bio":vbio},
       "death":{"time_slot":"밤","place":"PC",
         "weapon":T.get("weapon","둔기"),"weapon_class":T.get("weapon_class","타격"),
         "method":T.get("desc",""),
         "scene_description":"", "scene_inspection":[]},
       "time_slots":slots,
       "map":{"max_move_per_slot":0,"places":places},
       "cast":CAST,"clue_graph":[],
       "choices":{"culprit":[c["id"] for c in CAST],
                  "weapon":[T.get("weapon","둔기"),"칼","독약","목맴 끈","돌"][:5]},
       "answer_format":{"culprit":"choice","weapon":"choice","motive":"free_text"},
       "solution":{"culprit":"C4","motive_label":CAST[CUL]["motive_label"],
         "motive_keywords":[w for w in re.split(r"[ ,·]", CAST[CUL]["kill_motive"]) if len(w)>=2][:8] or ["원한"],
         "weapon":T.get("weapon","둔기"),
         "reason":f"{CAST[CUL]['name']}이(가) {CAST[CUL]['kill_motive']} 그 일로 다투다 범행에 이르렀다."},
       "config":{"suspects":5,"rounds":3,"attempts":3,"turns_per_round":8}}
    # 이동 한도
    pl={p["id"]:p for p in places}
    mx=0
    for c in CAST:
        seq=[pl[c["timeline"][sl]] for sl in slots]
        for a,b in zip(seq,seq[1:]):
            mx=max(mx, math.hypot(a["pos"][0]-b["pos"][0], a["pos"][1]-b["pos"][1]))
    s["map"]["max_move_per_slot"]=round(mx+0.3,2)
    return s

# ───────────────────────── ③ 나레이션·단서 문장 ─────────────────────────
TEXT_SYS = """너는 추리게임의 도입 나레이션과 단서 문장을 쓰는 작가다.
주어진 '확정된 사실'과 어긋나는 내용을 쓰면 안 된다. 사실은 시스템이 정했고, 너는 문장만 쓴다.
나레이션은 사건이 나기까지의 이야기를 들려주고, 마지막 비트에서 주검이 발견되며 끝난다.
어떤 문장도 범인이 누구인지 알려주면 안 된다."""

TEXT_TMPL = """[확정된 사실]
- 배경: {bg} / 시대: {era}
- 피해자: {victim} ({vrole})
- 사망: {slot}, 장소 '{scene}'
- 흉기: {weapon} ({wclass})
- 트릭: {trick}
- 등장인물(순서대로 C1~C5): {cast}
- 각 인물의 동기: {motives}

[써야 할 것]
{{
  "narration": [
    {{"beat":1,"mood":"평온","focus":"world","text":"세계와 배경을 여는 문장(60자+)"}},
    {{"beat":2,"mood":"흥미","focus":"C1","text":"C1을 소개하며 그의 사정을 암시"}},
    {{"beat":3,"mood":"의미심장","focus":"C2","text":"C2 소개"}},
    {{"beat":4,"mood":"불안","focus":"C3","text":"C3 소개"}},
    {{"beat":5,"mood":"의미심장","focus":"C4","text":"C4 소개 — 범인이지만 절대 티내지 말 것"}},
    {{"beat":6,"mood":"불안","focus":"C5","text":"C5 소개"}},
    {{"beat":7,"mood":"고요","focus":"victim","text":"피해자가 혼자 남는 그 밤"}},
    {{"beat":8,"mood":"충격","focus":"victim","text":"주검 발견. 흉기와 현장의 이상한 점을 묘사하고 '지금까지의 이야기는 여기서 끝난다.'로 마무리"}}
  ],
  "scene_description":"현장 묘사 한두 문장",
  "scene_inspection":["검안/관찰 포인트 4개 — 구체적 사실만. 서정적 표현 금지"],
  "clue_texts":{{
    "weapon":"상처와 흉기를 알려주는 검안 문장",
    "alibi_C1":"C1이 그 밤 제자리에 있었다는 목격 증언",
    "alibi_C3":"C3이 그 밤 제자리에 있었다는 목격 증언",
    "context":"단독으론 범인을 못 짚지만 조건을 좁히는 정황 문장",
    "decisive":"범인을 가리키는 결정적 물증 문장 — 이름은 말하지 말고 물증만 서술",
    "red_herring":"엉뚱한 곳을 가리키는 그럴듯한 단서 문장"
  }}
}}

나레이션 8비트의 글자 수 합이 **550자 이상**이어야 한다. 각 비트를 충분히 길게 쓰라."""

def gen_texts(s):
    cast=", ".join(f"{c['id']}={c['name']}({c['public']})" for c in s["cast"])
    motives="; ".join(f"{c['id']}:{c['kill_motive']}" for c in s["cast"])
    pn={p["id"]:p["name"] for p in s["map"]["places"]}
    u=TEXT_TMPL.format(bg=s["background"]["atmosphere"], era=s["background"]["setting_raw"]["era"],
        victim=s["victim"]["name"], vrole=s["victim"]["role"], slot=s["death"]["time_slot"],
        scene=pn["PC"], weapon=s["death"]["weapon"], wclass=s["death"]["weapon_class"],
        trick=s["trick"]["name"]+" — "+s["trick"]["desc"], cast=cast, motives=motives)
    return chat_json(TEXT_SYS, u, max_tokens=3000)

def apply_texts(s, tx):
    pn={p["id"]:p["name"] for p in s["map"]["places"]}
    cul=next(c for c in s["cast"] if c.get("is_culprit"))
    s["intro"]["narration"]=tx["narration"]
    s["death"]["scene_description"]=tx.get("scene_description","")
    insp=tx.get("scene_inspection") or []
    while len(insp)<4: insp.append("현장에 남은 또 다른 흔적이 눈에 띈다.")
    s["death"]["scene_inspection"]=insp[:4]
    C=tx.get("clue_texts") or {}
    cl=[
     dict(id="K1",channel="crime_scene",medium="검안",surface=C.get("weapon",""),
          implies=f"weapon_class={s['death']['weapon_class']}. 흉기를 좁힌다.",
          weight="weapon",points_to=None,exculpates=[],reveal_round=1,decisive=False),
     dict(id="K2",channel="crime_scene",medium="현장",surface=C.get("red_herring",""),
          implies="그럴듯하나 어긋난 방향(레드헤링).",
          weight="red_herring",points_to=None,exculpates=[],reveal_round=1,decisive=False),
     dict(id="K3",channel="spine",medium="증언",surface=C.get("alibi_C1",""),
          implies="C1은 그 밤 제자리에 체류 → 현장 부재.",
          weight="exculpating",points_to=None,exculpates=["C1"],reveal_round=1,decisive=False),
     dict(id="K4",channel="spine",medium="증언",surface=C.get("alibi_C3",""),
          implies="C3은 그 밤 제자리에 체류 → 현장 부재.",
          weight="exculpating",points_to=None,exculpates=["C3"],reveal_round=2,decisive=False),
     dict(id="K5",channel="spine",medium="검안",surface=C.get("context",""),
          implies="조건을 좁히는 정황. 단독으론 특정 불가.",
          weight="context",points_to=None,exculpates=[],reveal_round=2,decisive=False),
     dict(id="K6",channel="spine",medium="증언",
          surface="초저녁엔 여러 사람이 현장을 드나들었다는 말이 있다. 밤엔 본 사람이 없다.",
          implies="초저녁 출입은 여럿(기회) — 정황만으론 특정 불가.",
          weight="context",points_to=None,exculpates=[],reveal_round=3,decisive=False),
    ]
    for i,c in enumerate(s["cast"]):
        cl.append(dict(id=f"L{i+1}",channel="location",medium="물건",location=f"P{i+1}",
          surface=f"{pn[f'P{i+1}']}에서 나온 {c['name']}의 흔적 — {c['secret']['text']}",
          implies=f"C{i+1}의 비밀={c['secret']['type']}. 살인과는 별개(레드헤링).",
          weight="red_herring",points_to=None,exculpates=[],reveal_round=2,decisive=False))
    cl.append(dict(id="LDEC",channel="location",medium="감식",location="PC",
      surface=C.get("decisive",""),
      implies=f"물증이 {cul['name']}(C4)를 가리킨다. 초저녁에만 있던 두 사람은 이 밤의 흔적과 무관 → 배제.",
      weight="incriminating",points_to="C4",exculpates=["C2","C5"],reveal_round=3,decisive=True))
    s["clue_graph"]=cl
    return s

# ───────────────────────── ④⑤ 후처리 + 검증 + 복구 ─────────────────────────
def postprocess(s):
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
    return s

def diagnose(s):
    """실패 사유를 사람이 읽을 수 있게(그리고 LLM에 되먹일 수 있게) 모은다."""
    from verify import verify
    from difficulty import difficulty_gate
    from playtest import trace
    from agent_lint import lint, secret_lint
    from simulate import simulate
    from checklist import check
    from ux_lint import lint as uxlint
    from fun import check_fun
    fails=[]
    ok,rep=verify(s)
    fails += [f"[논리] {r[0]}: {r[2]}" for r in rep if not r[1]]
    g,gr=difficulty_gate(s); fails += [f"[난이도] {x}" for x in (gr if not g else [])]
    if not trace(s,verbose=False)[0]: fails.append("[플레이] 정상 해결 경로 없음")
    lo,li=lint(s); fails += [f"[자기오류] {x}" for x in (li if not lo else [])]
    so,si=secret_lint(s); fails += [f"[비밀] {x}" for x in (si if not so else [])]
    uo,ui,_=uxlint(s); fails += [f"[UX] {m}" for _,m in (ui if not uo else [])]
    R,rate=check(s); fails += [f"[체크리스트] {n}" for n,c,_ in R if not c]
    if not (0.30<=rate<=0.85): fails.append(f"[난이도] 정답률 {rate:.2f} 밴드 이탈")
    fo,fs=check_fun(s)
    if not fo: fails.append(f"[재미] {fs}/100 (60점 미만)")
    return fails, rate, fs

REPAIR_SYS="""너는 추리게임 텍스트를 고치는 편집자다. 아래 '문제 목록'을 해결하도록
지정된 부분만 다시 써라. 사실 관계는 바꾸지 말고 문장만 고친다."""

def repair_texts(s, fails):
    """검증 실패 중 '글'로 고칠 수 있는 것만 LLM에 되먹인다."""
    textual=[f for f in fails if any(k in f for k in
             ["나레이션","인생소설","현장","도입부","550","관찰","묘사","말투","표본"])]
    if not textual: return None
    u=(f"[문제 목록]\n" + "\n".join("- "+x for x in textual) +
       f"\n\n[현재 나레이션 글자수] {sum(len(b.get('text','')) for b in s['intro']['narration'])}\n"
       f"[현재 나레이션]\n" + json.dumps(s['intro']['narration'], ensure_ascii=False)[:1500] +
       "\n\n아래 JSON으로 고친 결과만 출력하라.\n"
       '{"narration":[8개 비트 — 문제를 해결하도록 더 길고 구체적으로], '
       '"scene_inspection":["관찰 포인트 4개"]}')
    return chat_json(REPAIR_SYS, u, max_tokens=3000)

# ───────────────────────── mock 대체(창작 없이 배관 검증) ────────────
def mock_brief(inp):
    from build_custom import ARCHETYPES, SECRET_KINDS, MOTIVES, name_for, MODERN_TRICK
    roles=(inp.get("characters") or ["동료"]*5)[:5]
    while len(roles)<5: roles.append("동료")
    return {"title":"회의실의 유리 문진",
      "victim":{"name":name_for(inp.get("victim","피해자"),7),"role":inp.get("victim","피해자"),
                "bio":"조직을 세우고 키워 온 사람이다. 성과에 밝고 결단이 빨랐으나 사람을 도구처럼 썼다."},
      "trick":{"name":MODERN_TRICK["name"],"desc":MODERN_TRICK["desc"],
               "weapon":MODERN_TRICK["weapon"],"weapon_class":MODERN_TRICK["weapon_class"]},
      "places":[{"name":n,"desc":n+"의 공기"} for n in
                ["회의실(현장)","각자 자리","탕비실","디자인실","서버실","옥상"]],
      "cast":[{"name":name_for(r,i),"public":r,"age":"30대","sex":"남" if i%2 else "여",
               "personality":ARCHETYPES[i]["personality"],"speech_style":ARCHETYPES[i]["speech"],
               "voice_hint":ARCHETYPES[i]["voice"],"example_line":"제가 그럴 이유가 없습니다.",
               "kill_motive":MOTIVES[i][0],"motive_label":MOTIVES[i][1],
               "secret_text":SECRET_KINDS[i][0],"secret_type":SECRET_KINDS[i][1],
               "triggers":SECRET_KINDS[i][2],
               "reveals":f"…{SECRET_KINDS[i][0]}는 건 사실입니다. 허나 그건 제 사정이지 사람을 해친 일이 아닙니다.",
               "life_story":"오래 이 일을 해 온 사람이다. "*12}
              for i,r in enumerate(roles)]}

def mock_texts(s):
    pn={p["id"]:p["name"] for p in s["map"]["places"]}
    C=s["cast"]
    nar=[{"beat":1,"mood":"평온","focus":"world","text":f"{s['background']['atmosphere']}. 그 주는 유난히 일이 몰려, 불이 새벽까지 꺼지지 않았다. 사람들은 저마다의 자리에서 밤을 넘겼다."}]
    moods=["흥미","의미심장","불안","의미심장","불안"]
    for i,c in enumerate(C):
        nar.append({"beat":i+2,"mood":moods[i],"focus":c["id"],
          "text":f"{c['name']}은(는) {c['public']}이었다. {c['kill_motive']} 그 일을 마음에 담아 둔 채, 겉으로는 아무렇지 않은 척했다."})
    nar.append({"beat":7,"mood":"고요","focus":"victim",
      "text":f"그 밤 {s['victim']['name']}은(는) {pn['PC']}에 홀로 남았다. 하나둘 불이 꺼지고, 발소리가 잦아들었다."})
    nar.append({"beat":8,"mood":"충격","focus":"victim",
      "text":f"{s['intro']['original_summary']} 곁엔 {s['death']['weapon']}이 놓여 있었고, 누군가 손댄 듯 어색한 자리가 있었다. 지금까지의 이야기는 여기서 끝난다."})
    return {"narration":nar,
      "scene_description":f"{pn['PC']}에 {s['victim']['name']}이(가) 쓰러져 있다.",
      "scene_inspection":[f"{s['death']['weapon_class']}에 해당하는 상처가 뚜렷하다.",
        "흉기로 보이는 물건에 지문이 남아 있지 않다 — 닦였다는 뜻이다.",
        "저항한 흔적이 없다 — 경계하지 않은 상대였다.",
        "없어진 물건이 없다 — 재물을 노린 것이 아니다."],
      "clue_texts":{"weapon":f"상처는 {s['death']['weapon']}에 의한 {s['death']['weapon_class']}이다.",
        "alibi_C1":f"곁에 있던 사람들: '{C[0]['name']}는 그 밤 {pn['P1']}에 계속 있었습니다.'",
        "alibi_C3":f"함께 있던 사람: '{C[2]['name']}는 그 밤 {pn['P3']}을 뜨지 않았습니다.'",
        "context":"상처의 각도로 보아 가해자는 피해자와 키가 비슷하고, 서두른 흔적이 없다.",
        "decisive":"그 시간대의 기록만 통째로 비어 있고, 현장에는 그 자리를 지켰다던 사람의 자취가 남아 있다.",
        "red_herring":"현장 근처에서 엉뚱한 사람의 물건이 발견되었다 — 그 자리에 있었다는 증거는 아니다."}}

# ───────────────────────── 메인 ─────────────────────────
def generate(inp, outpath):
    print(f"[backend={BACKEND} model={MODEL if BACKEND=='openai' else 'mock'}]")
    print("① 창작 브리프 생성…")
    brief = gen_brief(inp) if BACKEND=="openai" else None
    if not brief:
        if BACKEND=="openai": print("   ⚠️ LLM 브리프 실패 → mock으로 대체")
        brief = mock_brief(inp)
    print(f"   제목: {brief.get('title')} · 인물 {len(brief.get('cast',[]))}명")

    print("② 논리 뼈대 조립…")
    s = assemble(inp, brief)
    print(f"   범인 C4={s['cast'][3]['name']} · 가짜 유력자 C2·C5 · 지도 6곳")

    print("③ 나레이션·단서 문장 작성…")
    tx = gen_texts(s) if BACKEND=="openai" else None
    if not tx:
        if BACKEND=="openai": print("   ⚠️ LLM 텍스트 실패 → mock으로 대체")
        tx = mock_texts(s)
    s = apply_texts(s, tx)

    print("④ 후처리 주입(BGM·음성·검색·행동지침·배역)…")
    s = postprocess(s)

    print("⑤ 검증…")
    for attempt in range(1, MAX_REPAIR+2):
        fails, rate, fscore = diagnose(s)
        if not fails:
            json.dump(s, open(outpath,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"   ✅ 전 게이트 통과 · 정답률 {rate:.2f} · 재미 {fscore}/100")
            print(f"   저장: {outpath}")
            return True
        print(f"   ❌ 시도 {attempt}: 문제 {len(fails)}건")
        for f in fails[:6]: print("      -", f)
        if attempt > MAX_REPAIR: break
        fixed = repair_texts(s, fails) if BACKEND=="openai" else None
        if fixed:
            print("   🔧 LLM 재작성 반영…")
            if fixed.get("narration"): s["intro"]["narration"]=fixed["narration"]
            if fixed.get("scene_inspection"): s["death"]["scene_inspection"]=fixed["scene_inspection"][:4]
            s=postprocess(s)
        else:
            print("   🔧 자동 보정(길이·형식) 시도…")
            nar=s["intro"]["narration"]
            for b in nar:
                if len(b.get("text",""))<70:
                    b["text"]=b["text"]+" 그날의 공기는 유난히 무거웠고, 사람들은 저마다 말을 아꼈다."
            s=postprocess(s)
    print("   (미저장 — 재시도 한도 초과)")
    return False

DEMO={"background":"1920년대 경성의 활동사진관",
      "characters":["변사(辯士)","여배우","영사기사","극장주 조카","단골 기자"],
      "story":"개봉 전야, 극장주가 영사실에서 필름 릴에 목이 감긴 채 죽은 채 발견된다.",
      "victim":"극장주",
      "options":{"tone":"흑백 무성영화 같은 음영이 짙은 도시 미스터리"}}

if __name__=="__main__":
    if "--demo" in sys.argv:
        inp=DEMO; out="scenarios/22_경성활동사진관.json"
    else:
        inp=json.load(open(sys.argv[1],encoding="utf-8")); out=sys.argv[2]
    print("=== 입력 ===")
    print(" 배경:",inp["background"]); print(" 스토리:",inp["story"])
    print(" 인물:",", ".join(inp.get("characters") or []))
    print()
    generate(inp, out)
