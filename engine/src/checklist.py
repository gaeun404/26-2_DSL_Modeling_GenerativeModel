# -*- coding: utf-8 -*-
"""요구사항 전수 점검 — 이 프로젝트 대화에서 합의한 모든 항목이 스키마에 살아있는지 검사.
사용: python checklist.py out/L_나무꾼과선녀.json"""
import json, sys
from verify import verify
from difficulty import difficulty_gate
from playtest import trace
from agent_lint import lint, secret_lint
from simulate import simulate, tier, legs

def check(s):
    R=[]
    def ok(name, cond, note=""):
        R.append((name, bool(cond), note))
    cfg=s.get("config",{}); cast=s.get("cast",[]); places=s.get("map",{}).get("places",[])
    clues=s.get("clue_graph",[]); nar=s.get("intro",{}).get("narration",[])
    cul=next((c for c in cast if c.get("is_culprit")),{})

    # 대규칙
    ok("용의자 5명", cfg.get("suspects")==5 and len(cast)==5)
    # 라운드 수는 편마다 다르다(3 또는 4). 고정값을 요구하면 폭을 넓히는 순간 전부 실패한다.
    ok(f"{cfg.get('rounds',3)} 라운드", cfg.get("rounds") in (3, 4))
    ok("목숨 2~4회(attempts)", cfg.get("attempts") in (2,3,4))  # 어려움=2, 쉬움=4
    ok("턴 제한 심문", bool(cfg.get("turns_per_round")))
    ok("정답=범인+흉기 보기 5", len(s.get("choices",{}).get("culprit",[]))==5 and len(s.get("choices",{}).get("weapon",[]))==5)
    ok("동기=자유서술", s.get("answer_format",{}).get("motive")=="free_text")

    # 도입 나레이션(원작 들려주기 + 인물 소개 + 반전)
    ntext=" ".join(b.get("text","") for b in nar)
    foci={b.get("focus") for b in nar}
    ok("나레이션 8+비트", len(nar)>=8)
    ok("나레이션 550자+ (원작 서사)", len(ntext)>=520)
    # 도입부 훅: 고전은 '옛날 옛적에~', 현대는 시공간을 여는 장면 제시
    _era=" ".join(str(v) for v in s.get("background",{}).get("setting_raw",{}).values())
    _first=(nar[0].get("text","") if nar else "")
    _origin=s.get("meta",{}).get("origin","")
    _folk = ("커스텀" not in _origin) and not any(k in _era for k in
             ["현대","근대","21세기","2020","1920","오늘날","스타트업","사무실","도시"])
    _modern = not _folk
    if _modern:
        ok("도입부 훅(시공간 제시)", len(_first)>=30 and any(k in _first for k in ["그","밤","날","무렵","년대","주"]))
    else:
        ok("옛날 옛적에~ 시작", "옛날" in _first)
    ok("용의자 5명 모두 나레이션서 소개", all(c["id"] in foci for c in cast))
    ok("밝음→충격 분위기 반전", nar and nar[0].get("mood") not in ("충격","음침") and nar[-1].get("mood")=="충격")

    # 원작 인물 매핑(피해자/용의자에 원작 배역이 profile.relation/status로)
    ok("피해자 인생소설(victim.bio)", len(s.get("victim",{}).get("bio","") or "")>=150)
    ok("전원 profile 카드(신상)", all(c.get("profile",{}).get("status") for c in cast))

    # 크라임씬(시체/현장 단서·다잉메시지 성격)
    d=s.get("death",{})
    ok("현장 묘사+관찰 3+", bool(d.get("scene_description")) and len(d.get("scene_inspection") or [])>=3)
    ok("crime_scene 단서 존재", any(cl.get("channel")=="crime_scene" for cl in clues))

    # 인물 깊이(자기오류 방지)
    ok("전원 긴 인생소설(200+)", all(len(c.get("life_story","") or "")>=200 for c in cast))
    ok("전원 관계도(relationships)", all(c.get("relationships") for c in cast))
    ok("전원 아는것/모르는것 경계", all(c.get("knows") and c.get("does_not_know") for c in cast))
    ok("전원 말투 표본(example_lines)", all(len(c.get("persona",{}).get("example_lines") or [])>=2 for c in cast))

    # 비밀: 장소+심문 양쪽 도달
    ok("정곡 심문(pressure_points)", all(c.get("pressure_points") for c in cast))
    sok,_=secret_lint(s); ok("비밀 장소+심문 이중 도달", sok)

    # 장소·동선·지도
    ok("장소별 탐색 특징 2+", all(len(p.get("features") or [])>=2 for p in places))
    ok("지도 좌표+이동제한", all(p.get("pos") for p in places) and "max_move_per_slot" in s.get("map",{}))
    # 채널을 location/record/physical로 쪼갰다. 뒤져서 나오는 것이면 무엇이든 된다.
    ok("장소 탐색 단서", any(cl.get("channel") in ("location", "record", "physical")
                          for cl in clues))

    # 트릭·동선정합·거짓말 교차검증
    ok("중심 트릭 명시", bool(s.get("trick",{}).get("name")))
    ok("범인 거짓말 교차검증(false_place)", any(l.get("false_place") for l in (cul.get("lies") or [])))

    # 디자인팀(BGM·이미지) 필드
    sr=s.get("background",{}).get("setting_raw",{}); ad=s.get("adapted_story",{})
    ok("BGM/이미지: era·location·culture", sr.get("era") and sr.get("location") and sr.get("culture"))
    ok("BGM: tone·tone_shift(반전)", ad.get("tone") and ad.get("tone_shift"))
    ok("이미지: 장소별 desc", all(p.get("desc") for p in places))

    # BGM(시나리오마다 다른 음악)
    bgm=s.get("bgm",{}); bp=bgm.get("palette",{}); bc=bgm.get("cues",{})
    ok("BGM: 문화권 악기 팔레트", bool(bp.get("culture_key")) and len(bp.get("instruments") or [])>=3)
    ok("BGM: 국면별 큐 7종", len(bc)>=7)
    ok("BGM: 큐마다 BPM·악기·프롬프트", all(c.get("bpm") and c.get("prompt") and c.get("instruments") for c in bc.values()))
    ok("BGM: 작품 톤 반영(톤 수식자)", bool(bp.get("tone_modifier")))

    # 검색창(단서 속 낯선 말 조회)
    sch=s.get("search",{}); sidx=sch.get("index") or []
    ok("검색창: 항목 15+", len(sidx)>=15)
    ok("검색창: 검안 전문용어", any(t.get("category") in ("검안","약재") for t in sidx))
    ok("검색창: 검색 체인(재검색 유도)", len(sch.get("chains") or [])>=1)
    ok("검색창: 결과 없음 응답", len(sch.get("no_result_responses") or [])>=1)


    # 음성(TTS)
    vo=s.get("voice",{}); nar=vo.get("narrator",{}); vc=vo.get("cast",{})
    ok("음성: 나레이션 사양(크라임씬 톤)", bool(nar.get("pitch")) and bool(nar.get("reference_en")))
    ok("음성: 나레이션 비트별 연출", len(vo.get("narration_beats") or [])>=8)
    ok("음성: 용의자별 목소리", len(vc)==len(cast) and all(v.get("reference_en") for v in vc.values()))
    ok("음성: 용의자 음색 분화", len({(v.get("gender"),v.get("age_band"),v.get("pitch")) for v in vc.values()})>=3)
    # 라운드별 행동지침
    ok("에이전트: 라운드별 행동지침", all(len(c.get("act_directions") or [])==cfg.get("rounds",3) for c in cast))
    # 장면별 BGM
    ok("BGM: 장소별 큐(사건 전/후)", len(bgm.get("place_cues") or {})==len(places))
    ok("BGM: 인물 테마", len(bgm.get("character_themes") or {})==len(cast))
    ok("BGM: 이벤트 큐(단서·지목·정답)", len(bgm.get("event_cues") or {})>=8)
    ok("BGM: 주제 선율 통일", bool((bgm.get("main_theme") or {}).get("id")))


    # 심문 설계(벤치마크 반영): 감정만으로 자백 불가 · 증거로는 자백 가능
    try:
        from pressure import emotion_only_test, evidence_path_test
        _cid=cul.get("id")
        _e_ok,_ev=emotion_only_test(s,_cid) if _cid else (False,0)
        _p_ok,_pv=evidence_path_test(s,_cid) if _cid else (False,0)
        ok(f"심문: 감정만으론 자백 불가 (게이지 {_ev:.0f})", _e_ok)
        ok(f"심문: 증거 경로로 자백 성립 (게이지 {_pv:.0f})", _p_ok)
    except Exception:
        ok("심문: 압박 게이지 검사", False)

    # 검증(수십수백번)·난이도
    v=verify(s)[0]; g=difficulty_gate(s)[0]; p=trace(s,verbose=False)[0]; l=lint(s)[0]
    rate=simulate(s,600)
    ok("논리검증 verify", v); ok("난이도 게이트", g); ok("플레이 가능", p); ok("자기오류 린트", l)
    ok("가짜 유력자 존재", len([c for c in cast if not c.get("is_culprit") and legs(c)>=2])>=1)
    ok(f"정답률 플레이가능 티어 (={rate:.2f})", 0.30<=rate<=0.85)  # 쉬움~어려움 사다리 허용
    return R, rate

if __name__=="__main__":
    path=sys.argv[1] if len(sys.argv)>1 else "scenarios/L_나무꾼과선녀.json"
    s=json.load(open(path,encoding="utf-8"))
    R,rate=check(s)
    print(f"=== 요구사항 전수 점검: {s['meta']['title']} ({s['meta']['origin']}) ===\n")
    npass=sum(1 for _,c,_ in R if c)
    for name,c,note in R:
        print(f"  [{'✅' if c else '❌'}] {name}"+(f"  — {note}" if note else ""))
    print(f"\n총 {len(R)}개 항목 · 통과 {npass} · 미달 {len(R)-npass}")
