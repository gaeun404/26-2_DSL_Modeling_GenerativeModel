"""
시나리오 검증기 (rule-based). 생성된 scenario.json이 게임으로 내보낼 수 있는지 판정.
사용: from verify import verify;  ok, report = verify(scenario)
     python verify.py 91_dsl_demo.json   # 단독 테스트
규칙 R1~R9 + 흉기/보기/지도 정합.
"""
import json, sys, math

def verify(s):
    R = []   # (규칙, 통과여부, 메시지)
    def chk(rule, cond, msg=""):
        R.append((rule, bool(cond), msg)); return bool(cond)

    # ---- 기본 구조 ----
    cast = s.get("cast", [])
    ids = [c["id"] for c in cast]
    culprits = [c for c in cast if c.get("is_culprit")]
    chk("STRUCT-cast5", len(cast) == s.get("config",{}).get("suspects",5),
        f"용의자 {len(cast)}명")
    chk("STRUCT-oneculprit", len(culprits) == 1, f"범인 {len(culprits)}명")
    if not culprits:
        return False, R
    culprit = culprits[0]
    slots = s.get("time_slots", [])
    places = {p["id"]: p for p in s.get("map",{}).get("places",[])}
    death = s.get("death",{})

    # ---- R1 타임라인 무모순 ----
    tl_ok = True
    for c in cast:
        tl = c.get("timeline",{})
        if set(tl.keys()) != set(slots):
            tl_ok = False
        # 한 슬롯에 한 장소(dict라 자동), 장소가 map에 존재
        for slot, pid in tl.items():
            if pid not in places: tl_ok = False
    chk("R1-timeline_complete", tl_ok, "모든 인물이 모든 시간대에 유효한 장소 1곳")
    # 범인은 사망 시간대에 사망 장소에 있어야
    chk("R1-culprit_at_scene",
        culprit.get("timeline",{}).get(death.get("time_slot")) == death.get("place"),
        "범인이 사망 시각·장소에 위치")

    # ---- R1b 알리바이-지도 정합: 인접 슬롯 간 이동이 물리적으로 가능 ----
    def dist(a,b):
        pa,pb = places.get(a,{}).get("pos"), places.get(b,{}).get("pos")
        if not pa or not pb: return 0
        return math.hypot(pa[0]-pb[0], pa[1]-pb[1])
    move_ok = True
    max_move = s.get("map",{}).get("max_move_per_slot", 9999)
    for c in cast:
        tl = [c["timeline"].get(sl) for sl in slots]
        for a,b in zip(tl, tl[1:]):
            if a and b and dist(a,b) > max_move: move_ok = False
    chk("R1b-alibi_map", move_ok, "인접 시간대 이동이 지도상 가능(거리 제한 내)")

    # ---- R3 균등 의심: 전원 동기+비밀 ----
    chk("R3-equal_suspicion",
        all(c.get("kill_motive") and c.get("secret",{}).get("text") for c in cast),
        "모든 용의자가 살인동기+비밀 보유")

    # ---- 범인 거짓 알리바이 교차검증 가능성 (lies[].false_place 있을 때만) ----
    for l in (culprit.get("lies") or []):
        fp = l.get("false_place")
        if fp:
            wit = [c["id"] for c in cast if c["id"] != culprit["id"] and c.get("timeline", {}).get(death.get("time_slot")) == fp]
            chk("LIE-catchable", bool(wit),
                f"범인의 거짓 알리바이 장소 {fp}에 목격 가능한 인물 {wit}" if wit
                else f"거짓 알리바이 장소 {fp}에 교차검증할 인물이 없어 못 잡음")

    # ---- R4 범인만 거짓말 ----
    chk("R4-only_culprit_lies",
        culprit.get("lies") and all((not c.get("lies")) for c in cast if not c.get("is_culprit")),
        "범인만 lies 보유, 무고자는 없음")

    # ---- R2 유일해 (레드헤링 제외, 배제단서로 소거) ----
    clues = s.get("clue_graph", [])
    exon = set()
    for cl in clues:
        if cl.get("weight") == "red_herring": continue
        ex = cl.get("exculpates")
        if ex:
            exon.update(ex if isinstance(ex, list) else [ex])
    remaining = [i for i in ids if i not in exon]
    chk("R2-unique_solution",
        len(remaining) == 1 and remaining[0] == culprit["id"] == s.get("solution",{}).get("culprit"),
        f"소거 후 남은 용의자 {remaining} (정답 {s.get('solution',{}).get('culprit')})")

    # ---- MMO(수단·동기·기회) 모델 ----
    def full_mmo(c):
        m = c.get("mmo", {})
        return bool(m.get("means")) and bool(m.get("motive")) and bool(m.get("opportunity"))
    has_mmo = all("mmo" in c for c in cast)
    chk("MMO-present", has_mmo, "전원 mmo(means·motive·opportunity) 보유")
    full = [c["id"] for c in cast if full_mmo(c)]
    chk("MMO-culprit_full", full_mmo(culprit), "범인은 수단·동기·기회 3개 완비")
    chk("MMO-unique_full", full == [culprit["id"]],
        f"3개 완비 용의자는 범인 1명뿐 (완비자 {full})")
    chk("MMO-motive_all", all(c.get("mmo",{}).get("motive") for c in cast),
        "모든 용의자가 동기 보유(균등 의심)")
    chk("MMO-innocent_gap",
        all((not full_mmo(c)) for c in cast if not c.get("is_culprit")),
        "무고자는 각자 최소 한 다리(수단/기회)가 비어 있음")

    # ---- 이동·시간 정합 (지도 동선) ----
    ds, dp = death.get("time_slot"), death.get("place")
    # opportunity=false 인 자는 사망 시각에 현장에 있으면 안 됨(동선 모순)
    bad_opp = [c["id"] for c in cast
               if c.get("mmo", {}).get("opportunity") is False and c.get("timeline", {}).get(ds) == dp]
    chk("MOVE-opp_scene", not bad_opp,
        f"opportunity=false인데 사망시각 현장에 있는 자: {bad_opp}" if bad_opp else "opportunity와 동선 정합")
    # 알리바이(현장에 없었음)로 배제된 자만 검사 — 수단 부족으로 배제된 '가짜 유력자'(현장엔 있음)는 제외
    alibi_exon = set()
    for cl in clues:
        if cl.get("weight") == "exculpating" and cl.get("exculpates"):
            alibi_exon.update(cl["exculpates"] if isinstance(cl["exculpates"], list) else [cl["exculpates"]])
    bad_exon = [i for i in alibi_exon if next((c for c in cast if c["id"] == i), {}).get("timeline", {}).get(ds) == dp]
    chk("MOVE-exon_scene", not bad_exon,
        f"알리바이 배제자가 현장에 있음(모순): {bad_exon}" if bad_exon else "알리바이 배제자는 현장에 없음")
    # 범인은 사망 시각 현장에 있고 opportunity=true 여야
    chk("MOVE-culprit_opp", culprit.get("mmo", {}).get("opportunity") is True,
        "범인 opportunity=true(현장에 있을 수 있었음)")

    # ---- 범인 비밀 분리(조기자백 방지) ----
    # 범인의 '비밀'이 곧 범행이면, 심문 초반에 트리거만 건드려도 자백해 게임이 붕괴한다.
    cul_sec = (culprit.get("secret",{}) or {}).get("text","")
    cul_rev = " ".join(pp.get("reveals","") for pp in (culprit.get("pressure_points") or []))
    ACT_WORDS = ["죽였","살해","목을 졸","찔러","독을 탔","빠뜨","물에 넣","끌어낸","내리쳐","내가 한 짓","내가 그랬"]
    scene_name = places.get(death.get("place"),{}).get("name","")
    chk("SECRET-not_crime",
        not any(w in cul_sec for w in ACT_WORDS),
        f"범인 비밀이 범행 자체가 아님(살인과 분리): '{cul_sec[:26]}'")
    chk("SECRET-no_confess_reveal",
        not any(w in cul_rev for w in ACT_WORDS),
        "범인 pressure_points 실토문에 자백 어휘 없음(트리거로 자백 유발 금지)")
    cul_trig = [t for pp in (culprit.get("pressure_points") or []) for t in pp.get("trigger",[])]
    # 위험한 건 '범행 동작'을 직접 가리키는 트리거(장소명 우연 일치는 무해).
    ACT_TRIGGERS = ["묶", "끌어", "실행", "찔", "밀어", "졸라", "빠뜨", "내리쳐", "살해", "죽인"]
    risky = [t for t in cul_trig if t in ACT_TRIGGERS]
    chk("SECRET-safe_triggers",
        not risky,
        f"범인 트리거에 범행 동작어 없음 (위험어: {risky})" if risky else "범인 트리거가 안전(비밀만 여는 말)")

    # ---- R5 결정적 단서: 범인 지목 + 후반 라운드 ----
    dec = [cl for cl in clues if cl.get("decisive")]
    chk("R5-decisive",
        any(cl.get("points_to") == culprit["id"] and (cl.get("reveal_round") or 0) >= 2 for cl in dec),
        "결정적 단서가 범인 지목 & 라운드2+ 공개")

    # ---- 디자인팀 인계 필드(BGM·이미지 생성용) ----
    bg = s.get("background", {}); ad = s.get("adapted_story", {})
    sr = bg.get("setting_raw", {})
    chk("DESIGN-background",
        bool(sr.get("era")) and bool(sr.get("location")),
        "background.setting_raw.era/location 존재(이미지·BGM 월드레퍼런스)")
    chk("DESIGN-tone",
        bool(ad.get("tone")) and bool(ad.get("tone_shift")),
        "adapted_story.tone/tone_shift 존재(초기·사건후 BGM 조건)")
    chk("DESIGN-place_desc",
        all(p.get("desc") for p in s.get("map",{}).get("places",[])),
        "모든 장소에 desc(장소별 배경 이미지 프롬프트)")

    # ---- BGM(음악 생성용): 문화권 팔레트 + 국면별 큐 ----
    bgm = s.get("bgm", {})
    bp = bgm.get("palette", {}); bc = bgm.get("cues", {})
    NEED_CUES = ["intro","discovery","investigation","interrogation","climax","reveal","ending"]
    chk("BGM-palette",
        bool(bp.get("culture_key")) and len(bp.get("instruments") or []) >= 3 and bool(bp.get("scale")),
        f"문화권 음악 팔레트(악기≥3·음계) 보유: {bp.get('label','없음')}")
    chk("BGM-cues",
        all(k in bc for k in NEED_CUES),
        f"국면별 BGM 큐 {len(bc)}/7 (intro·discovery·investigation·interrogation·climax·reveal·ending)")
    chk("BGM-cue_fields",
        all(bc.get(k,{}).get("bpm") and bc.get(k,{}).get("prompt") and (bc.get(k,{}).get("instruments") or [])
            for k in NEED_CUES),
        "각 큐에 bpm·악기편성·생성 프롬프트 존재")
    # 장소별 BGM(사건 전/후) — 장소를 누를 때마다 다른 곡
    plc = bgm.get("place_cues", {})
    n_places = len(s.get("map",{}).get("places",[]))
    chk("BGM-place_cues",
        len(plc) == n_places and all(v.get("pre_murder") and v.get("post_murder") for v in plc.values()),
        f"장소별 큐 {len(plc)}/{n_places}곳 · 각 장소 사건 전/후 2버전")
    chk("BGM-scene_cue",
        any(v.get("is_crime_scene") for v in plc.values()),
        "살인 현장 전용 큐(무선율·저역 압박) 존재")
    # 인물 테마(심문 중 라이트모티프)
    cth = bgm.get("character_themes", {})
    chk("BGM-character_themes",
        len(cth) == len(cast) and len({v.get("leitmotif_instrument") for v in cth.values()}) >= 3,
        f"용의자별 테마 {len(cth)}/{len(cast)}명 · 리드악기 분화")
    # 이벤트 큐(단서 오픈·지목·정답/오답)
    evc = bgm.get("event_cues", {})
    NEED_EV = ["clue_found","clue_decisive","accusation","verdict_correct","verdict_wrong"]
    chk("BGM-event_cues",
        all(k in evc for k in NEED_EV),
        f"이벤트 큐 {len(evc)}종(단서·결정적단서·탐정지목·정답·오답 포함)")
    # 통일감: 모든 트랙이 하나의 주제 선율 변주여야 자연스럽다
    mt = bgm.get("main_theme", {})
    all_cues = (list(bc.values()) + list(evc.values()) + list(cth.values())
                + [v["pre_murder"] for v in plc.values()] + [v["post_murder"] for v in plc.values()])
    chk("BGM-main_theme",
        bool(mt.get("id")) and bool(mt.get("motif_desc")) and bool(mt.get("key_center")),
        f"시나리오 공통 주제 선율 정의: {mt.get('motif_desc','없음')[:40]}")
    chk("BGM-theme_unity",
        all(c.get("theme_variation") == mt.get("id") for c in all_cues),
        f"전 트랙({len(all_cues)}곡)이 같은 주제의 변주 — 시나리오 내 톤 통일")

    # ---- 검색창(고문서·검안 사전): 낯선 용어를 플레이어가 직접 조회 ----
    sch = s.get("search", {})
    sidx = sch.get("index") or []
    terms = {t.get("term") for t in sidx}
    chk("SEARCH-index", len(sidx) >= 15, f"검색 항목 {len(sidx)}개(≥15)")
    chk("SEARCH-forensic",
        any(t.get("category") in ("검안","약재") for t in sidx),
        "검안·약재 전문용어 항목 존재(검안서 해독용)")
    chk("SEARCH-chain",
        len(sch.get("chains") or []) >= 1,
        f"검색어가 새 검색어를 낳는 체인 {len(sch.get('chains') or [])}개(검색→추론→재검색 순환)")
    chk("SEARCH-no_spoiler",
        all(t.get("spoiler_safe") is not False for t in sidx)
        and not any(s.get("solution",{}).get("culprit","") in (t.get("entry") or "") for t in sidx),
        "검색 항목이 범인을 직접 지목하지 않음(스포일러 안전)")
    chk("SEARCH-no_result",
        len(sch.get("no_result_responses") or []) >= 1,
        "헛검색 시 '결과 없음' 응답 정의")

    # ---- 인생소설(에이전트 정보 공백 방지) ----
    LIFE_MIN = 200
    bad_life = [c["id"] for c in cast if len(c.get("life_story","") or "") < LIFE_MIN]
    chk("BIBLE-cast_life", not bad_life,
        f"인생소설 부족(≥{LIFE_MIN}자) 인물: {bad_life}" if bad_life else "전원 긴 인생소설 보유")
    vbio = s.get("victim",{}).get("bio","") or ""
    chk("BIBLE-victim_life", len(vbio) >= 150,
        "피해자 인생소설(victim.bio ≥150자) 보유" if len(vbio)>=150 else f"피해자 인생소설 부족({len(vbio)}자)")

    # ---- 장소별 특징(크라임씬 탐색·UI 연출) ----
    bad_feat = [p["id"] for p in s.get("map",{}).get("places",[]) if len(p.get("features") or []) < 2]
    chk("SCENE-place_features", not bad_feat,
        f"탐색 특징(≥2) 부족 장소: {bad_feat}" if bad_feat else "모든 장소에 탐색 특징 2+")
    # 사망 현장은 관찰 포인트가 특히 풍부해야
    chk("SCENE-crime_rich",
        len(death.get("scene_inspection") or []) >= 3 and bool(death.get("scene_description")),
        "현장 묘사+관찰 포인트 3+ (크라임씬 상세)")

    # ---- 페이싱: 각 라운드 스파인 단서 ≥1 ----
    rounds = s.get("config",{}).get("rounds",3)
    spine_rounds = [cl.get("reveal_round") for cl in clues if cl.get("channel") in ("spine","crime_scene")]
    chk("PACE-spine_each_round",
        all(r in spine_rounds for r in range(1, rounds+1)),
        f"라운드별 스파인 단서 존재 {sorted(set(spine_rounds))}")


    # ---- 음성(TTS): 나레이션 + 인물별 목소리 ----
    vo = s.get("voice", {})
    nar = vo.get("narrator", {}); vc = vo.get("cast", {})
    chk("VOICE-narrator",
        bool(nar.get("pitch")) and bool(nar.get("tempo")) and bool(nar.get("reference_en")),
        f"나레이션 음성 사양(피치·속도·TTS프롬프트): {nar.get('reference','없음')[:28]}")
    chk("VOICE-narration_beats",
        len(vo.get("narration_beats") or []) >= len(s.get("intro",{}).get("narration",[])),
        f"나레이션 비트별 연출 {len(vo.get('narration_beats') or [])}개")
    chk("VOICE-cast",
        len(vc) == len(cast) and all(v.get("reference_en") and v.get("pitch") for v in vc.values()),
        f"용의자별 음성 사양 {len(vc)}/{len(cast)}명")
    chk("VOICE-distinct",
        len({(v.get("gender"), v.get("age_band"), v.get("pitch")) for v in vc.values()}) >= 3,
        "용의자 음성이 서로 구분됨(성별·연령·피치 조합 3종+)")

    # ---- 라운드별 행동 지침(에이전트 감정 곡선·반복 방지) ----
    rounds_n = s.get("config",{}).get("rounds",3)
    chk("ACT-directions",
        all(len(c.get("act_directions") or []) == rounds_n for c in cast),
        f"전원 라운드별({rounds_n}) 행동지침(goal·conceal·concede·tone) 보유")

    # ---- 흉기 정합 ----
    ch = s.get("choices",{})
    sol = s.get("solution",{})
    chk("WEAPON-in_choices", sol.get("weapon") in ch.get("weapon",[]) and death.get("weapon")==sol.get("weapon"),
        "정답 흉기가 보기에 있고 death와 일치")
    chk("WEAPON-clue_exists",
        any(cl.get("weight")=="weapon" for cl in clues), "흉기 좁히는 단서 존재")

    # ---- 보기·동기 정합 (동기는 자유서술: 보기 불필요) ----
    chk("CHOICE-culprit", sol.get("culprit") in ch.get("culprit",[]) and len(ch.get("culprit",[]))==5,
        "범인 보기 5개 + 정답 포함")
    chk("CHOICE-weapon5", len(ch.get("weapon",[]))==5, "흉기 보기 5개")
    chk("MOTIVE-freetext",
        bool(sol.get("motive_label")) and culprit.get("motive_label")==sol.get("motive_label"),
        "정답 동기(자유서술 채점 기준)와 범인 동기 일치")

    ok = all(p for _,p,_ in R)
    return ok, R

def _print(report):
    for rule, p, msg in report:
        print(f"  [{'PASS' if p else 'FAIL'}] {rule:28} {msg}")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "91_dsl_demo.json"
    s = json.load(open(path, encoding="utf-8"))
    ok, report = verify(s)
    _print(report)
    print("\n결과:", "✅ 통과 (게임 가능)" if ok else "❌ 실패 (재생성 필요)")
    sys.exit(0 if ok else 1)
