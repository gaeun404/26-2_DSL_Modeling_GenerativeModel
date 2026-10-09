# -*- coding: utf-8 -*-
"""ui_view.py — **화면이 읽는 모양으로 다시 쓴다.**

시나리오 원본(`scenarios/91_dsl_demo.json`)은 사람이 읽고 그림을 그리려고 만든
문서다. 이미지 자리에는 URL이 아니라 프롬프트가 들어 있고, 지도 좌표는 소수
두 개이며, 무엇보다 **정답이 들어 있다** — is_culprit·solution·points_to·
reveal_sequence.

프론트(web/)가 읽는 모양은 다르다. `src/types/scenario.ts` 가 그 계약이다.
이 파일이 둘 사이를 옮긴다. 옮기면서 두 가지를 한다.

  ① **정답을 뗀다.** 지목(POST /accuse) 전까지 브라우저로 나가는 것에는
     범인·진상·재연·트릭·비밀·어느 선택지에 단서가 있는지가 없다.
     `server.py` 머리말의 규칙 그대로다 — 화면에 뜨는 것만 내려보낸다.

  ② **그림과 소리를 붙인다.** `ui_assets` 가 ID로 URL을 만들어 준다.

지목한 뒤에 열리는 진상·재연은 `reveal_view()` · `reenactment_view()` 가 따로
만든다. 그 둘은 /accuse 응답에만 실린다.
"""
import ui_assets as A

GRID = 3          # 지도는 3 × 3 판이다 (UI MapBoard)


def _narr(s, *keys):
    """story_narration 에서 글 한 덩이. server.py 의 _sn 과 같은 셈이다."""
    node = (s.get("ui") or {}).get("story_narration") or {}
    for k in keys:
        node = (node or {}).get(k) if isinstance(node, dict) else None
    return ((node or {}).get("text") or "") if isinstance(node, dict) else ""


# ── 작은 손질 ─────────────────────────────────────────────────────────
def _fields(fields):
    """카드의 라벨-값 목록. **hidden_value 는 떼고 보낸다** — 사인 정답이 거기 있다."""
    return [{"label": f.get("label", ""), "value": f.get("value", "")}
            for f in (fields or [])]


def _group_pages(pages, target=130):
    """오프닝을 읽을 만한 덩이로 묶는다.

    ★왜 (2026-08-29, 시연 제보) — "인트로가 너무 늘어진다."
      91편 오프닝은 611자를 열네 쪽에 나눠 담고 있었다. 쪽당 마흔네 자.
      한 문장 읽고 누르기를 열네 번 하면 사건이 시작되기도 전에 지친다.

      서버는 /session 응답(`_opening`)에서 이미 이렇게 묶고 있었다. 그런데
      화면이 읽는 것은 시나리오 뷰의 narration.pages 라, 거기는 여전히 열네
      쪽이었다. 같은 셈을 여기에도 둔다 — **삽화는 묶음의 첫 쪽 것**을 쓴다.
    """
    out, buf, first = [], "", None
    def flush():
        nonlocal buf, first
        if buf.strip():
            out.append((buf.strip(), first))
        buf, first = "", None
    for p in pages:
        t = (p.get("text") or "").strip()
        if not t:
            continue
        if buf and len(buf) + len(t) > target:
            flush()
        if not buf:
            first = p
        buf = (buf + " " + t).strip()
    flush()
    return out


def _grid_positions(places):
    """소수 좌표를 3 × 3 칸으로. 같은 칸이 겹치면 가까운 빈 칸으로 민다."""
    if not places:
        return {}
    xs = [float((p.get("pos") or [0, 0])[0]) for p in places]
    ys = [float((p.get("pos") or [0, 0])[1]) for p in places]

    def band(v, lo, hi):
        if hi <= lo:
            return 1
        return min(GRID, int((v - lo) / ((hi - lo) / GRID)) + 1)

    lox, hix, loy, hiy = min(xs), max(xs), min(ys), max(ys)
    out, taken = {}, set()
    for p, x, y in zip(places, xs, ys):
        col = band(x, lox, hix)
        row = GRID + 1 - band(y, loy, hiy)          # y가 클수록 위쪽 줄
        if (row, col) in taken:                     # 겹치면 빈 칸을 찾는다
            free = [(r, c) for r in range(1, GRID + 1)
                    for c in range(1, GRID + 1) if (r, c) not in taken]
            free.sort(key=lambda rc: (rc[0] - row) ** 2 + (rc[1] - col) ** 2)
            row, col = free[0] if free else (row, col)
        taken.add((row, col))
        out[p["id"]] = {"row": row, "col": col}
    return out


# ── 화면이 읽는 시나리오 ──────────────────────────────────────────────
def scenario_view(s, scenario_id, held=None, accused=False):
    """정답을 뺀 시나리오. 프론트 `types/scenario.ts` 의 Scenario 모양.

    `held` 에 지금 손에 든 단서 id를 주면 **그것만** 카드로 싣는다. 안 주면 전부다.
    수첩은 서버가 주는 대로 자란다 — /search·/next_round·/confront 응답에 카드가
    딸려 온다.

    `accused` 는 이미 지목한 판인가. 지목한 뒤에는 진상·재연을 함께 싣는다 —
    그래야 새로고침해도 진상 화면이 그대로 열린다. 지목 전에는 절대 싣지 않는다.
    """
    ui = s.get("ui") or {}
    photos = (s.get("assets") or {}).get("photos") or {}
    cast_by_id = {c["id"]: c for c in (s.get("cast") or [])}

    # 오프닝 나레이션 — 덩이로 묶고 프롬프트를 URL로 갈아 끼운다
    nar = ui.get("narration") or {}
    pages = []
    for i, (text, src) in enumerate(_group_pages(nar.get("pages") or []), 1):
        img = (src or {}).get("image") or {}
        pages.append({
            "page": i, "beat": (src or {}).get("beat"),
            "text": text, "sentences": [],
            "chars": len(text), "over_limit": False,
            "mood": (src or {}).get("mood", ""),
            "focus": (src or {}).get("focus", ""),
            # 한글 읽는 속도를 글자당 90ms로 보고 여유 1.2초
            "auto_ms": min(9000, len(text) * 90 + 1200),
            "image": {"w": img.get("w"), "h": img.get("h"),
                      "scene": img.get("scene", ""),
                      "prompt_ko": "", "prompt_en": "",
                      "url": A.story((src or {}).get("page")) or ""},
        })

    # 피해자 카드 — 초상은 사진, 현장은 사건 뒤 그림
    vc = ui.get("victim_card") or {}
    victim = s.get("victim") or {}
    death = s.get("death") or {}
    # ★'이름' 칸을 앞에 세운다 (2026-08-29, 시연 제보 — "피해자 카드가 비어 있다").
    #   카드 fields 는 [신분 / 발견 장소 / 발견 시각 / 사인 / 발견자]로,
    #   **이름이 없었다.** 화면은 '이름' 라벨을 찾다 못 찾고 빈칸을 그렸다.
    vfields = [{"label": "이름", "value": victim.get("name", "")}] + _fields(vc.get("fields"))
    victim_card = {
        "name": victim.get("name", ""),
        "role": victim.get("role", ""),
        "bio": victim.get("bio", ""),
        "found_place": next((x.get("title", "") for x in (ui.get("place_screens") or [])
                             if x.get("place_id") == death.get("place")),
                            death.get("place", "")),
        "found_time": death.get("time_slot", ""),
        "fields": vfields,
        "bio_short": vc.get("bio_short", ""),
        "portrait": A.portrait("victim", photos) or "",
        "body_art": A.scene_after() or "",
    }

    # 용의자 카드 — 얼굴 · 표정 세 벌 · 전신 · 테마곡
    suspect_cards = []
    for c in (ui.get("suspect_cards") or []):
        cid = c.get("id")
        suspect_cards.append({
            "id": cid,
            "name": c.get("name", ""),
            "list_sub": c.get("list_sub", ""),
            "fields": _fields(c.get("fields")),
            "alibi_quote": c.get("alibi_quote", ""),
            "alibi_label": c.get("alibi_label", ""),
            # ★소개글 (2026-08-29, 시연 제보 — "캐릭터 상세 설명이 잘려 있다").
            #   실은 잘린 게 아니라 **아예 안 내려가고 있었다.** /session 응답에만
            #   있고 시나리오 뷰에는 없어서, 상세 화면은 채울 것이 없었다.
            "intro": _narr(s, "suspect_intro", cid),
            "portrait": A.portrait(cid, photos) or "",
            "faces": A.faces(cid),
            "standing": A.fullbody(cid) or "",
            "voice": c.get("voice") or {},
            "theme": A.character_theme(cid) or "",
        })

    # 단서 카드 — **아직 손에 없는 것은 싣지 않는다.**
    #   카드에는 "어디서 어떻게 얻는지"와 설명이 다 적혀 있다. 열여덟 장을 통째로
    #   내려보내면 수첩을 열지 않아도 브라우저 개발자도구에 사건이 다 있다.
    clue_cards = []
    for c in (ui.get("clue_cards") or []):
        cid = c.get("id")
        if held is not None and cid not in held:
            continue
        f = {x.get("label", ""): x.get("value", "") for x in (c.get("fields") or [])}
        clue_cards.append({
            "clue_id": cid,
            "name": c.get("name", ""),
            "list_sub": c.get("list_sub", ""),
            "type": f.get("종류") or c.get("name", ""),
            "acquired_place": f.get("획득 장소", ""),
            "acquired_method": f.get("획득 방법", ""),
            "description": c.get("description", ""),
            "image": A.clue(cid) or "",
            "full_image": A.clue_full(cid) or "",
        })

    # 장소 화면 — **선택지는 이름만.** 무엇이 나오는지(finds)와 결과 문장은
    # 서버가 /search 응답으로 준다. 미리 내려보내면 개발자도구로 답이 보인다.
    place_screens = []
    for ps in (ui.get("place_screens") or []):
        pid = ps.get("place_id")
        talk = ps.get("talk") or {}
        cast_id = ps.get("standing_cast_id") or talk.get("cast_id")
        rounds = {}
        for rk, rv in (ps.get("rounds") or {}).items():
            rounds[rk] = {
                "layer_note": (rv or {}).get("layer_note", ""),
                "actions": [{"index": i, "id": f"a{i}",
                             "label": a.get("label", ""),
                             "button": a.get("button", "조사"),
                             "result_lines": [], "highlight_last": False,
                             "finds": None, "sfx": []}
                            for i, a in enumerate((rv or {}).get("actions") or [])],
            }
        place_screens.append({
            "place_id": pid,
            "name": ps.get("title", ""),
            "title": ps.get("title", ""),
            "rounds": rounds,
            "background_image": A.place(pid) or "",
            "map_thumb": A.place_thumb(pid) or "",
            "cast_id": cast_id,
            "character_name": ps.get("standing_character") or talk.get("name") or "",
            "character_image": (A.fullbody(cast_id) or "") if cast_id else "",
            "talk_label": talk.get("label") or "",
            "talk_note": talk.get("note") or "",
            "bgm": A.place_cue(pid) or "",
        })

    # 지도 — 소수 좌표를 칸으로
    mp = s.get("map") or {}
    grid = _grid_positions(mp.get("places") or [])
    places = [{
        "id": p["id"], "name": p.get("name", ""),
        "pos": grid.get(p["id"], {"row": 1, "col": 1}),
        "unlock_round": 1,                      # 이 편은 처음부터 여섯 방이 다 열린다
        "desc": p.get("desc", ""),
        "thumb": A.place_thumb(p["id"]) or "",
        "owner": p.get("owner"),
    } for p in (mp.get("places") or [])]

    end = s.get("ending") or {}
    stars = s.get("stars") or {}

    return {
        "scenarioId": scenario_id,
        "title": (s.get("meta") or {}).get("title", ""),
        "origin": (s.get("meta") or {}).get("origin", ""),
        "era": (s.get("meta") or {}).get("era", ""),
        "difficulty": stars.get("n", 3),
        "cover_image": A.place("PC") or "",

        "config": {
            "suspects": (s.get("config") or {}).get("suspects", len(cast_by_id)),
            "rounds": (s.get("config") or {}).get("rounds", 3),
            "attempts": (s.get("config") or {}).get("attempts", 3),
            "turns_per_round": (s.get("config") or {}).get("turns_per_round", 8),
        },

        "ui": {
            "screens": [],
            "narration": {
                "page_count": nar.get("page_count", len(pages)),
                "pages": pages,
                "limits": nar.get("limits") or {},
                "video_pages": nar.get("video_pages") or [],
                "incident_page": nar.get("incident_page", 0),
                "full_text": nar.get("full_text", ""),
                "narrator": nar.get("narrator") or {},
            },
            "victim_card": victim_card,
            "suspect_cards": suspect_cards,
            "clue_cards": clue_cards,
            "place_screens": place_screens,
            # 진상·재연은 **지목한 뒤에만** 실린다. 그 전에는 빈 자리다.
            "reveal_sequence": (reveal_view(s, photos) if accused
                                else {"beats": [], "full_text": ""}),
            "murder_reenactment": (reenactment_view(s) if accused else
                                   {"cuts": [], "total_sec": 0, "culprit": "",
                                    "culprit_name": "", "sfx_spec": {},
                                    "art_note": "", "no_skip": True}),
            "audio": A.audio_book(),
            "hud": (ui.get("hud") or {}).get("copy") or {},
        },

        "death": {
            "scene_description": (s.get("death") or {}).get("scene_description", ""),
            "scene_inspection": (s.get("death") or {}).get("scene_inspection") or [],
        },

        # 단서 그래프는 통째로 답이다(points_to·exculpates). 내려보내지 않는다.
        "clue_graph": [],

        "map": {"max_move_per_slot": mp.get("max_move_per_slot", 1),
                "places": places},

        "events": [{"round": e.get("round"), "name": e.get("name", ""),
                    "kind": e.get("kind", ""), "text": e.get("text", ""),
                    "effect": ""}                 # 효과 문구에 인물 ID가 적혀 있다
                   for e in (s.get("events") or [])],

        "choices": {"culprit": [c["id"] for c in (s.get("cast") or [])],
                    "weapon": (s.get("choices") or {}).get("weapon") or []},

        "scoring": {k: (s.get("scoring") or {}).get(k)
                    for k in ("culprit_correct", "wrong_accusation_penalty",
                              "secret_revealed_each", "max")},

        "ending": {"truth_reveal": (end.get("truth_reveal", "") if accused else ""),
                   "grades": [{"min": g.get("min", 0), "name": g.get("name", ""),
                               "text": g.get("text", "")}
                              for g in (end.get("grades") or [])]},

        "hud": (ui.get("hud") or {}),
        "toasts": ui.get("toasts") or {},
        "interrogation": {}, "search": {}, "bgm": {}, "voice": {}, "phases": [],
    }


# ── 지목 뒤에만 열리는 것 ─────────────────────────────────────────────
def reveal_view(s, photos=None):
    """S-22 진상. `getRevealPages` 가 읽는 모양 — beats[].pages[].{text,image}.

    ★그림을 재연과 나눠 쓴다.
      진상 여섯 박에 재연 여섯 컷을 그대로 얹으면, 진상을 다 읽고 재연으로 넘어갈 때
      **같은 그림에 같은 제목**이 한 번 더 나온다 — 제보 "that night은 왜 또 나오지?"가
      그 자리에서 났다.

      진상은 말로 밝히는 자리다. 그림은 딱 한 곳, **범인이 드러나는 박**에만 둔다.
      나머지는 글만 둔다. 여섯 컷은 재연(reenactment_view)이 통째로 가져간다.
    """
    rs = (s.get("ui") or {}).get("reveal_sequence") or {}
    culprit = next((c["id"] for c in (s.get("cast") or []) if c.get("is_culprit")), None)
    beats = []
    for b in (rs.get("beats") or []):
        label = b.get("label", "")
        # '범인' 박에서만 얼굴을 보여 준다 — 게임 중 처음 드러나는 자리다
        img = (A.portrait(culprit, photos) or "") if ("범인" in label and culprit) else ""
        beats.append({
            "no": b.get("no"),
            "title": label,
            "caption": "",
            "pages": [{"text": b.get("text", ""), "image": img}],
            "duration_sec": b.get("duration_sec", 8),
        })
    return {"beats": beats, "full_text": rs.get("full_text", "")}


def reenactment_view(s):
    """S-23 재연. `getReenactmentCuts` 가 읽는 모양 — cuts[].{cut,title,image,duration_sec}."""
    mr = (s.get("ui") or {}).get("murder_reenactment") or {}
    cuts = []
    for c in (mr.get("cuts") or []):
        no = c.get("no")
        cuts.append({
            "cut": no, "title": c.get("label", ""), "text": c.get("text", ""),
            "image": A.reenact(no) or "",
            "duration_sec": c.get("duration_sec", 5),
        })
    return {"cuts": cuts, "total_sec": mr.get("total_sec", 0),
            "culprit": mr.get("culprit", ""), "culprit_name": mr.get("culprit_name", ""),
            "art_note": mr.get("art_note", ""), "no_skip": mr.get("skip") is False,
            "sfx_spec": {}}


# ── 사건 목록(불러오기 전용) ──────────────────────────────────────────
def _drop_shared_opening(text, other):
    """두 줄이 같은 문장으로 시작하면 뒤 줄에서 그 문장을 뗀다."""
    text, other = (text or "").strip(), (other or "").strip()
    if not text or not other:
        return text
    cut = text.find(". ")
    if cut < 0:
        return text
    head = text[:cut + 1]
    if other.startswith(head) and len(text) > len(head) + 4:
        return text[cut + 1:].strip()
    return text

def library_card(s, file_name, has_assets=True):
    """S-04 사건 기록실 카드 한 장. **엔딩 문구는 미끼만, 진상은 넣지 않는다.**

    ★두 가지가 여기로 새고 있었다 (2026-08-31, 제보 —
      "「트릭이 꼬여있다~~」 여기 삭제했었고, 회장이 피해자인 걸 보여주지 않는 걸로 바꿨는데?").

      하나. 「트릭이 꼬여 있다 · 쉬움」은 8/30 에 없앤 글인데, 그때 막은 것은
      /scenarios 쪽 문 하나뿐이었다. 기록실 카드(/scenarios/library)는 같은
      별점 소개문을 다른 이름(endingLine1)으로 그대로 내보내고 있었다.
      난이도를 설명하는 글이라 바로 옆 난이도 딱지와 두 번 겹친다.

      둘. **피해자는 빨간 화면에서 드러난다**(가은 문서 M-12). 그런데
      incidentLine 에 death.scene_description 을 그대로 실었더니, 판을 열기도
      전인 기록실·사건 공개 화면에서 「한도윤이 의자에서 미끄러진 채 쓰러져
      있다」가 먼저 떴다. 누가 죽었는지가 첫 화면에 적혀 있으면 빨간 화면이
      알려 줄 것이 없다.

      사건 공개 나레이션은 이미 이름 없이 쓰여 있다 —
      「이 밤에 한 사람이 죽었다」. 그것을 쓴다.
    """
    meta, stars = s.get("meta") or {}, s.get("stars") or {}
    bg = s.get("background") or {}
    sn = ((s.get("ui") or {}).get("story_narration") or {})
    opening_line = ((sn.get("case_open") or {}).get("text") or "").strip()
    return {
        "id": file_name,
        "title": meta.get("title", ""),
        "origin": meta.get("origin", ""),
        "backgroundLine": (bg.get("atmosphere") or "").strip(),
        # 이름도 사인도 없는 한 줄. 현장 묘사는 빨간 화면 뒤(S-08)에서 처음 나온다.
        #   두 줄이 같은 문장으로 시작하면(둘 다 「시험기간의 중앙도서관 6층.」)
        #   겹쳐 읽혀서, 앞 줄과 겹치는 첫 문장은 떼고 보낸다.
        "incidentLine": _drop_shared_opening(
            opening_line or (bg.get("atmosphere") or "").strip(),
            (bg.get("atmosphere") or "").strip()),
        # 별점 소개문은 난이도 이야기라 여기 두면 딱지와 겹친다 — 비운다.
        "endingLine1": "",
        "endingLine2": (s.get("difficulty") or {}).get("tier", ""),
        "suspects": len(s.get("cast") or []),
        "rounds": (s.get("config") or {}).get("rounds", 3),
        "difficulty": stars.get("n", 3),
        "coverImage": (A.place("PC") or "") if has_assets else "",
        "category": "modern",
        "createdAt": 0,
    }
