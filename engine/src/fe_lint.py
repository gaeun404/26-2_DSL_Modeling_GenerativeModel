# -*- coding: utf-8 -*-
"""
fe_lint.py — 프론트엔드 연동 전 스키마 무결성 검사.

기존 게이트(verify/run_all)는 **추리 논리**가 맞는지를 본다.
이 린터는 **프론트가 화면을 그릴 수 있는지**를 본다 — 게임의 주요 장면마다
필요한 필드가 빠짐없이 있고, 서로 가리키는 id가 실제로 존재하는지.

검사 묶음
  N  나레이션      — 쪽/삽화/자막 길이/종(種) 지시
  S  구간 나레이션  — 사건공개·현장·피해자·용의자·라운드·이벤트·지목·엔딩 대사
  R  라운드 전환    — 라운드 수 정합, 이벤트, 배너 문구
  C  단서 공개      — 공개 라운드, 카드, 전달 방식, 그림 지시
  E  엔딩·진상      — 등급 구간, 진상 낭독, 범행 재연
  T  심문(채팅)     — 인물별 대사 스펙, 질문 횟수, 압박 트리거
  X  상호참조       — id 참조가 전부 실제 대상으로 풀리는지
  A  에셋           — 그림/음성/BGM 참조가 스펙에 존재하는지
  F  필러·시대착오   — 자동생성 껍데기 문구, 배경과 안 맞는 어휘

사용:
    python fe_lint.py                  # 전 편
    python fe_lint.py out/38_*.json    # 한 편(항목별 상세)
"""
import json, glob, re, sys, collections

# ── 시대착오 검사용: 현대 어휘가 근대 이전 배경에 있으면 잡는다 ────────────
MODERN_WORDS = ["서버", "휴대폰", "스마트폰", "노트북", "컴퓨터", "와이파이", "CCTV",
                "메신저", "이메일", "슬랙", "스타트업", "오픈오피스", "엘리베이터",
                "카카오톡", "인터넷", "앱 ", "USB", "카드키"]
MODERN_OK = re.compile(r"현대|20\d\d년대|근대|1920|1930|스타트업")

FILLER_PATTERNS = [
    (r"^(.+)의 공기$", "장소 설명이 '○○의 공기' 껍데기"),
    (r"그 일을 마음에 담아 둔 채, 겉으로는 아무렇지 않은 척했다", "인물 소개 템플릿 반복"),
]


def _bad_josa(text):
    """받침 없는 명사 + '이었다' (예: 여배우이었다 → 여배우였다)"""
    out = []
    for m in re.finditer(r"(.)이었다", text):
        ch = m.group(1)
        if "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 == 0:
            out.append(text[max(0, m.start() - 10):m.start() + 5])
    return out


def _sn_beats(sn):
    """story_narration 안의 대사들을 평평하게 훑는다."""
    for k, v in (sn or {}).items():
        if isinstance(v, dict) and "text" in v:
            yield v
        elif isinstance(v, dict):
            for x in v.values():
                if isinstance(x, dict) and "text" in x:
                    yield x


def lint(s):
    iss = []          # (코드, 메시지)
    info = {}
    err = lambda code, msg: iss.append((code, msg))

    rounds = s["config"]["rounds"]
    cast_ids = {c["id"] for c in s["cast"]}
    place_ids = {p["id"] for p in s["map"]["places"]}
    clue_ids = {c["id"] for c in s["clue_graph"]}
    ui = s.get("ui", {})
    # 인물 참조에서 정상으로 인정하는 특수 id
    #   V/victim  = 피해자(관계망에서 '피해자와의 관계'로 쓰인다)
    #   all       = 전원(타임라인에서 '모두가 아는 일')
    ref_ok = cast_ids | {"V", "victim", s["victim"]["name"]}
    ref_ok_all = ref_ok | {"all"}

    # ── N 나레이션 ──────────────────────────────────────────────
    nar = s["intro"]["narration"]
    uin = ui.get("narration", {})
    pages = uin.get("pages", [])
    info["N"] = f"{len(nar)}비트 / {len(pages)}쪽"
    if not nar:
        err("N", "intro.narration이 비었다")
    beat_nos = {b.get("beat") for b in nar}
    page_beats = {p.get("beat") for p in pages}
    # 한 비트가 글자수 한도(96자) 때문에 여러 쪽으로 갈리는 것은 정상이다.
    # 검사할 것은 "모든 쪽이 실제 비트를 가리키는가 / 모든 비트가 쪽을 갖는가".
    for b in sorted(page_beats - beat_nos):
        err("N", f"page.beat {b} — intro.narration에 없는 비트")
    for b in sorted(beat_nos - page_beats):
        err("N", f"beat {b} — 대응하는 쪽(page)이 없다")
    if uin.get("over_limit_pages"):
        err("N", f"자막 글자수 초과 쪽: {uin['over_limit_pages']}")
    if not uin.get("full_text"):
        err("N", "ui.narration.full_text 없음(낭독용 전체 대사)")
    for b in nar:
        if not b.get("render"):
            err("N", f"beat {b.get('beat')} — render(그림 지시) 없음")
        elif not b["render"].get("shot"):
            err("N", f"beat {b.get('beat')} — render.shot 없음")
        if b.get("focus") and b["focus"] not in cast_ids | {"world", "victim"}:
            err("N", f"beat {b.get('beat')} — focus '{b['focus']}'가 인물/world/victim 아님")
    for p in pages:
        if not (p.get("image") or {}).get("prompt_en"):
            err("N", f"page {p.get('page')} — 삽화 프롬프트(prompt_en) 없음")

    # ── R 라운드 전환 ───────────────────────────────────────────
    info["R"] = f"{rounds}라운드 · 이벤트 {len(s.get('events', []))}건"
    ph = s.get("phases", [])
    if not ph:
        err("R", "phases(진행 단계) 없음")
    for e in s.get("events", []):
        r = e.get("round")
        if r is None or not (1 <= r <= rounds):
            err("R", f"이벤트 '{e.get('name')}' 라운드 {r} — 1~{rounds} 범위 밖")
        if not e.get("effect"):
            err("R", f"이벤트 '{e.get('name')}' — effect(무슨 일이 벌어지는지) 없음")
    # 대질 — 전용 화면과 이벤트 게이트가 맞물려 있는지
    cx = s.get("cross_examination") or {}
    scr_ids = {x.get("id") for x in ui.get("screens", [])}
    if cx.get("pairs"):
        if "confront" not in scr_ids:
            err("R", "대질 쌍이 있는데 confront 전용 화면이 없다")
        ur = cx.get("unlock_round")
        evr = [e.get("round") for e in s.get("events", []) if e.get("round")]
        if not ur:
            err("R", "cross_examination.unlock_round 없음")
        elif evr and ur != min(evr):
            err("R", f"대질 해금 {ur}라운드 ≠ 이벤트 {min(evr)}라운드")
        for x in cx["pairs"]:
            if ur and x.get("round_min", 1) < ur:
                err("R", f"대질 {x.get('id')} round_min {x.get('round_min')} < 해금 {ur}")
        if not (cx.get("locked_copy") or {}).get("body"):
            err("R", "대질 잠금 안내 문구(locked_copy) 없음")
        for x in cx["pairs"]:
            ex = x.get("exchange") or []
            if len(ex) < 4:
                err("R", f"대질 {x.get('id')} — 주고받는 대본이 {len(ex)}줄 "
                         f"(둘이 부딪히려면 4줄 이상)")
            whos = {l.get("who") for l in ex}
            if whos != {"A", "B"}:
                err("R", f"대질 {x.get('id')} — 한쪽만 말한다(who={whos})")
            for l in ex:
                if not l.get("line") or not l.get("beat") or not l.get("tone"):
                    err("R", f"대질 {x.get('id')} — 대본 줄에 line/beat/tone 누락")
                if l.get("cast_id") not in cast_ids:
                    err("X", f"대질 {x.get('id')} 대본의 cast_id '{l.get('cast_id')}' 없음")
            if not (x.get("reveals") or {}).get("note"):
                err("R", f"대질 {x.get('id')} — 무엇이 드러나는지(reveals) 없음")

    hud = ui.get("hud", {}).get("copy", {})
    if "{r}" not in str(hud.get("round", "")):
        err("R", "hud.copy.round에 {r} 자리표시자 없음")
    if not hud.get("round_banner"):
        err("R", "hud.copy.round_banner(라운드 전환 배너) 없음")

    # ── S 구간 나레이션 ─────────────────────────────────────────
    sn = ui.get("story_narration") or {}
    if not sn:
        err("S", "ui.story_narration 없음 — 게임 중반 나레이션이 통째로 빠졌다")
    else:
        need = ["case_open", "crime_scene", "victim_card", "accuse"]
        for k in need:
            b = sn.get(k)
            if not (b or {}).get("text"):
                err("S", f"story_narration.{k} 대사 없음")
        si = sn.get("suspect_intro") or {}
        for cid in cast_ids:
            if not (si.get(cid) or {}).get("text"):
                err("S", f"용의자 {cid} 공개 나레이션 없음")
        for k in ("round_start", "round_end"):
            m = sn.get(k) or {}
            for r in range(1, rounds + 1):
                if not (m.get(str(r)) or {}).get("text"):
                    err("S", f"{r}라운드 {k} 나레이션 없음")
        ev = sn.get("event") or {}
        for e in s.get("events", []):
            if str(e.get("round")) not in ev:
                err("S", f"{e.get('round')}라운드 이벤트 나레이션 없음")
        eg = sn.get("ending") or {}
        for g in ((s.get("ending") or {}).get("grades") or []):
            if not (eg.get(g.get("name")) or {}).get("text"):
                err("S", f"엔딩 등급 '{g.get('name')}' 나레이션 없음")
        # 용의자 공개에서 비밀이 새면 게임이 끝난다
        for cid, b in si.items():
            c = next((x for x in s["cast"] if x["id"] == cid), None)
            sec = ((c or {}).get("secret") or {}).get("text", "")
            if sec and b.get("text") and sec[:18] in b["text"]:
                err("S", f"용의자 {cid} 공개 나레이션에 비밀이 새어 나온다")
    info["S"] = f"{sum(1 for _ in _sn_beats(sn))}개 대사" if sn else "없음"

    # ── C 단서 공개 ─────────────────────────────────────────────
    cards = {c["id"] for c in ui.get("clue_cards", [])}
    by_round = collections.Counter()
    dec = [c for c in s["clue_graph"] if c.get("decisive")]
    info["C"] = f"단서 {len(s['clue_graph'])} · 카드 {len(cards)} · 결정타 {len(dec)}"
    if len(dec) != 1:
        err("C", f"결정타 단서가 {len(dec)}개 — 정확히 1개여야 한다")
    for c in s["clue_graph"]:
        r = c.get("reveal_round", 1)
        by_round[r] += 1
        if not (1 <= r <= rounds):
            err("C", f"{c['id']} reveal_round {r} — 1~{rounds} 범위 밖")
        if c["id"] not in cards:
            err("C", f"{c['id']} — ui.clue_cards에 카드가 없다")
        if not c.get("render"):
            err("C", f"{c['id']} — render(그림 지시) 없음")
        pres = c.get("presentation") or {}
        if pres.get("mode") not in ("spoken", "place_panel", "illustrated"):
            err("C", f"{c['id']} — presentation.mode 이상: {pres.get('mode')}")
        if pres.get("mode") == "spoken":
            if not pres.get("speaker"):
                err("C", f"{c['id']} — spoken인데 speaker 없음")
            if not pres.get("script"):
                err("C", f"{c['id']} — spoken인데 script(대사) 없음")
        if pres.get("mode") == "place_panel" and c.get("location") not in place_ids:
            err("C", f"{c['id']} — place_panel인데 location '{c.get('location')}'이 실제 장소 아님")
        for t in (c.get("exculpates") or []):
            if t not in cast_ids:
                err("X", f"{c['id']}.exculpates '{t}' — 없는 인물")
        if c.get("points_to") and c["points_to"] not in cast_ids:
            err("X", f"{c['id']}.points_to '{c['points_to']}' — 없는 인물")
    # ★단서 획득 경로 — 자동 지급이 아닌 단서는 반드시 어느 장소 선택지에서 나와야 한다.
    #   전에는 한 장소·라운드에 하나만 두고 자리가 없으면 버려서, 32개가 얻을 길 없는
    #   고아 단서가 됐다. 공개 라운드보다 늦게 찾게 되는 것도 9개 있었다.
    _found = {}
    for ps in ui.get("place_screens", []):
        for r_, rd_ in (ps.get("rounds") or {}).items():
            for a_ in (rd_.get("actions") or []):
                if a_.get("finds"):
                    _found.setdefault(a_["finds"], []).append(int(r_))
    for c in s["clue_graph"]:
        if c.get("channel") in ("spine", "crime_scene"):
            continue                       # 라운드 시작에 저절로 들어오는 것
        rr = c.get("reveal_round", 1)
        if c["id"] not in _found:
            err("C", f"{c['id']} — 얻을 길이 없다(장소 선택지 어디에도 finds가 없음)")
        elif min(_found[c["id"]]) > rr:
            err("C", f"{c['id']} — {rr}라운드 공개인데 조사는 "
                     f"{min(_found[c['id']])}라운드부터 가능")

    if dec and dec[0].get("reveal_round", 1) != rounds:
        err("C", f"결정타가 {dec[0].get('reveal_round')}라운드 — 마지막({rounds})에 나와야 한다")
    for r in range(1, rounds + 1):
        if by_round[r] == 0:
            err("C", f"{r}라운드에 공개되는 단서가 하나도 없다")

    # ── E 엔딩·진상 ─────────────────────────────────────────────
    end = s.get("ending", {})
    grades = end.get("grades", [])
    info["E"] = f"등급 {len(grades)}단"
    if len(grades) < 2:
        err("E", "ending.grades가 2단 미만")
    mins = sorted(g.get("min", -1) for g in grades)
    if mins and mins[0] != 0:
        err("E", f"최저 등급 기준점이 {mins[0]} — 0점부터 받아 주는 등급이 있어야 한다")
    for g in grades:
        if not g.get("text"):
            err("E", f"등급 '{g.get('name')}' — 엔딩 글 없음")
    if not end.get("truth_reveal"):
        err("E", "ending.truth_reveal(진상 낭독) 없음")
    rs = ui.get("reveal_sequence", {})
    if not rs.get("beats"):
        err("E", "ui.reveal_sequence.beats(진상 낭독 컷) 없음")
    if not rs.get("full_text"):
        err("E", "ui.reveal_sequence.full_text 없음")
    mr = ui.get("murder_reenactment", {})
    cuts = mr.get("cuts") or []
    if not cuts:
        err("E", "ui.murder_reenactment.cuts(범행 재연 컷) 없음")
    if cuts and not any("트릭" in str(c.get("label", "")) for c in cuts):
        err("E", "재연에 트릭 컷이 없다 — 트릭이 어떻게 작동했는지 보여 주는 컷이 있어야 한다")
    for c in cuts:
        for f in ("text", "camera", "emotion", "continuity"):
            if not c.get(f):
                err("E", f"재연 {c.get('no')}컷 — {f} 없음")
        if len((c.get("image") or {}).get("prompt_ko", "")) < 80:
            err("E", f"재연 {c.get('no')}컷 — 그림 묘사가 너무 짧다(80자 미만)")
    rb = rs.get("beats") or []
    if rb and not any("트릭" in str(b.get("label", "")) for b in rb):
        err("E", "진상 낭독에 트릭 박이 없다")
    for b in rb:
        if b.get("duration_sec", 0) > 20:
            err("E", f"진상 '{b.get('label')}' 박이 {b['duration_sec']}초 — 텍스트 벽이다(20초 이하로)")
    if mr.get("culprit") and mr["culprit"] not in cast_ids:
        err("X", f"murder_reenactment.culprit '{mr['culprit']}' — 없는 인물")

    # ── T 심문(채팅) ────────────────────────────────────────────
    scards = {c["id"] for c in ui.get("suspect_cards", [])}
    info["T"] = f"인물 {len(s['cast'])} · 카드 {len(scards)} · 질문 {s['config'].get('turns_per_round')}회/라운드"
    if not s["config"].get("turns_per_round"):
        err("T", "config.turns_per_round(라운드당 질문 횟수) 없음")
    for c in s["cast"]:
        cid = c["id"]
        if cid not in scards:
            err("T", f"{cid} — ui.suspect_cards에 카드가 없다")
        for f in ("persona", "alibi_narration", "knows", "bio", "life_story"):
            if not c.get(f):
                err("T", f"{cid} — {f} 없음")
        pp = c.get("pressure_points") or []
        if not pp:
            err("T", f"{cid} — pressure_points(정곡 트리거) 없음")
        for x in pp:
            if len(x.get("trigger", [])) < 3:
                err("T", f"{cid} — 정곡 트리거 낱말이 3개 미만")
        per = c.get("persona") or {}
        for f in ("speech_style", "example_lines"):
            if not per.get(f):
                err("T", f"{cid} — persona.{f} 없음")
        if not (c.get("voice_spec") or {}):
            err("T", f"{cid} — voice_spec(음성 스펙) 없음")
        tl = c.get("timeline") or {}
        for sl in s["time_slots"]:
            if tl.get(sl) not in place_ids:
                err("X", f"{cid}.timeline[{sl}] '{tl.get(sl)}' — 없는 장소")

    # ── X 상호참조 ──────────────────────────────────────────────
    if s["death"]["place"] not in place_ids:
        err("X", f"death.place '{s['death']['place']}' — 없는 장소")
    sol = s.get("solution", {})
    if sol.get("culprit") and sol["culprit"] not in cast_ids:
        err("X", f"solution.culprit '{sol['culprit']}' — 없는 인물")
    for r in s.get("relation_web", []):
        for k in ("a", "b"):
            if r.get(k) not in ref_ok:
                err("X", f"relation_web {r.get('a')}↔{r.get('b')} — '{r.get(k)}'가 없는 인물")
    ps = {p["place_id"] for p in ui.get("place_screens", [])}
    for pid in place_ids:
        if pid not in ps:
            err("X", f"장소 {pid} — ui.place_screens에 화면이 없다")
    for t in s.get("timeline_events", []):
        w = t.get("who")
        if w and w not in ref_ok_all:
            err("X", f"timeline_events who '{w}' — 없는 인물")

    # ── A 에셋 참조 ─────────────────────────────────────────────
    sfx = set((ui.get("audio", {}).get("sfx") or {}).keys())
    music = set((ui.get("audio", {}).get("music") or {}).keys())
    cues = set((s.get("bgm", {}).get("cues") or {}).keys())
    pcues = set((s.get("bgm", {}).get("place_cues") or {}).keys())
    info["A"] = f"효과음 {len(sfx)} · 음악 {len(music)} · 큐 {len(cues)}"
    for scr in ui.get("screens", []):
        for ref in (scr.get("sfx") or []):
            key = ref.split(".")[-1]
            if ref.startswith("ui.audio.sfx.") and key not in sfx:
                err("A", f"화면 {scr['id']} — 효과음 '{key}' 스펙에 없음")
        b = scr.get("bgm") or ""
        m = re.match(r"^cues\.(\w+)", b)
        if m and m.group(1) not in cues:
            err("A", f"화면 {scr['id']} — BGM 큐 '{m.group(1)}' 없음")
    for pid in place_ids:
        if pid not in pcues:
            err("A", f"장소 {pid} — bgm.place_cues 없음")
    ct = set((s.get("bgm", {}).get("character_themes") or {}).keys())
    for cid in cast_ids:
        if cid not in ct:
            err("A", f"인물 {cid} — bgm.character_themes 없음")
    if not (s.get("voice", {}).get("cast") or {}):
        err("A", "voice.cast(인물 음성) 없음")
    for cid in cast_ids:
        if cid not in (s.get("voice", {}).get("cast") or {}):
            err("A", f"인물 {cid} — voice.cast 항목 없음")

    # ── F 필러·시대착오·조사 ─────────────────────────────────────
    era = s["background"]["setting_raw"].get("era", "") + " " + s["meta"].get("era", "")
    raw = json.dumps(s, ensure_ascii=False)
    # 시대착오 검사는 '시나리오 내용'만 본다. ui.screens/ui.hud 등 공용 UI 문구에는
    # "예) 2010년대 스타트업 사무실" 같은 안내 예시가 들어 있어 제외한다.
    story = {k: v for k, v in s.items() if k != "ui"}
    story_raw = json.dumps(story, ensure_ascii=False)
    nfill = 0
    for p in s["map"]["places"]:
        if re.match(r"^(.+)의 공기$", (p.get("desc") or "").strip()):
            err("F", f"장소 '{p['name']}' — 설명이 '○○의 공기' 껍데기")
            nfill += 1
    for pat, label in FILLER_PATTERNS[1:]:
        n = len(re.findall(pat, raw))
        if n:
            err("F", f"{label} {n}회")
            nfill += n
    if not MODERN_OK.search(era):
        for w in MODERN_WORDS:
            n = story_raw.count(w)
            if n:
                err("F", f"시대착오 — '{era.strip()}' 배경에 '{w}' {n}회")
    bj = _bad_josa(story_raw)
    if bj:
        err("F", f"조사 오류(받침 없는 명사+이었다) {len(bj)}건: {bj[0].strip()}")
    info["F"] = "깨끗" if nfill == 0 and not bj else f"필러 {nfill} · 조사 {len(bj)}"

    return (len(iss) == 0), iss, info


NAMES = {"N": "나레이션", "S": "구간나레이션", "R": "라운드전환", "C": "단서공개", "E": "엔딩·진상",
         "T": "심문(채팅)", "X": "상호참조", "A": "에셋참조", "F": "필러·시대"}

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and args[0].endswith(".json"):
        s = json.load(open(args[0], encoding="utf-8"))
        ok, iss, info = lint(s)
        print(f"=== 프론트 연동 점검: {s['meta']['title']} ===\n")
        for k in "NSRCETXAF":
            bad = [m for c, m in iss if c == k]
            print(f"  [{'✅' if not bad else '❌'}] {NAMES[k]:10} {info.get(k,'')}")
            for m in bad:
                print(f"        - {m}")
        print(f"\n{'✅ 전 항목 통과' if ok else f'❌ 문제 {len(iss)}건'}")
    else:
        tot = 0
        badf = 0
        cat = collections.Counter()
        for p in sorted(glob.glob("scenarios/[0-9]*.json")):
            s = json.load(open(p, encoding="utf-8"))
            ok, iss, info = lint(s)
            tot += len(iss)
            badf += (0 if ok else 1)
            for c, _ in iss:
                cat[NAMES[c]] += 1
            mark = "✅" if ok else "❌"
            extra = f"  {sorted({NAMES[c] for c, _ in iss})}" if iss else ""
            print(f"  {mark} {p.split('/')[-1]:28} 문제 {len(iss):3}건{extra}")
        n = len(glob.glob("scenarios/[0-9]*.json"))
        print(f"\n총 문제 {tot}건 · 문제 있는 편 {badf}/{n}")
        if cat:
            print("항목별:", dict(cat.most_common()))
