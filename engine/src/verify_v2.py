# -*- coding: utf-8 -*-
"""
verify_v2.py — 보드게임 분석에서 나온 **새 구조 전용** 검증 규칙.

왜 별도 모듈인가:
  기존 22편은 구식 스키마다. verify.py를 건드리면 22편이 한꺼번에 깨진다.
  새 필드(incidents / role / objectives / belongings / events / scoring)를
  **가진 시나리오만** 여기서 추가로 검사한다. 없는 필드는 조용히 건너뛴다.

검사 항목
  TRICK-*     오인 살인이 억지가 아닌가
  CONCEAL-*   '범인이 아닌 은폐자'가 정합한가, 충분히 범인처럼 보이는가
  OBJ-*       AI 용의자들의 목표가 서로 충돌하는가 (충돌이 없으면 심문이 밋밋)
  SCORE-*     만점 경로가 실제로 존재하는가
  INCIDENT-*  두 사건이 분리 가능한가
  BELONG-*    모든 소지품이 도달 가능한가
  EVENT-*     중반 반전 카드가 제자리에 있는가

사용:
    from verify_v2 import verify_v2
    ok, report = verify_v2(scenario)
단독:
    python verify_v2.py out/23_옹고집.json
"""
import json, sys

MISID_MIN_CONDITIONS = 3      # 오인 조건이 3개 미만이면 억지
CONCEAL_MIN_SIGNALS   = 2     # 은폐자가 범인처럼 보이는 근거 최소치
OBJ_MIN_CONFLICTS     = 2     # 목표 충돌 쌍 최소치


def verify_v2(s):
    R = []
    def chk(name, cond, note=""):
        R.append((name, bool(cond), note))

    cast = s.get("cast", [])
    by_id = {c["id"]: c for c in cast}
    clues = s.get("clue_graph", [])
    clue_ids = {cl.get("id") for cl in clues}
    culprit = next((c for c in cast if c.get("is_culprit")), None)

    # ── 오인 살인 ─────────────────────────────────────────────
    trick = s.get("trick", {})
    if trick.get("type") == "misidentification":
        conds = trick.get("conditions") or []
        chk("TRICK-misid_conditions", len(conds) >= MISID_MIN_CONDITIONS,
            f"오인 조건 {len(conds)}개 (최소 {MISID_MIN_CONDITIONS}) — 적으면 억지가 된다")

        tgt = (culprit or {}).get("mmo", {}).get("motive_target")
        chk("TRICK-motive_target", bool(tgt) and tgt in by_id,
            f"범인의 동기 대상={tgt} — 오인 살인은 동기가 **표적**을 향해야 한다")
        chk("TRICK-victim_not_target", tgt != "victim",
            "범인의 동기가 피해자를 향하면 오인이 아니다")

        # 표적이 실제로 그 자리에 있을 뻔했는가 = 표적의 방/자리가 현장인가
        dp = s.get("death", {}).get("place")
        tgt_owns_scene = any(p.get("id") == dp and p.get("owner") == tgt
                             for p in s.get("map", {}).get("places", []))
        chk("TRICK-scene_is_target_room", tgt_owns_scene,
            f"현장({dp})이 표적({tgt})의 공간이어야 착각이 성립한다")

        # 피해자가 왜 거기 있었는지 설명이 있어야 한다(우연이면 억지)
        reason = (s.get("victim", {}) or {}).get("presence_reason", "")
        chk("TRICK-victim_presence_explained", len(reason) >= 40,
            "피해자가 그 자리에 있던 이유가 설명돼야 한다(우연이면 억지)")

        # 오인 조건이 단서로 회수되는가
        blob = " ".join((cl.get("surface", "") + cl.get("implies", "")) for cl in clues)
        hit = sum(1 for cnd in conds if any(w in blob for w in cnd.split()[:2]))
        chk("TRICK-conditions_in_clues", hit >= 2,
            f"오인 조건 중 {hit}개만 단서로 회수됨 — 플레이어가 트릭을 재구성할 수 없다")

    # ── 은폐자 ────────────────────────────────────────────────
    conc = [c for c in cast if c.get("role") == "concealer"]
    if conc:
        chk("CONCEAL-not_culprit", all(not c.get("is_culprit") for c in conc),
            "은폐자는 범인이 아니어야 한다(둘이 같으면 반전이 사라진다)")
        for c in conc:
            acts = c.get("cover_actions") or []
            chk(f"CONCEAL-has_actions[{c['id']}]", len(acts) >= 2,
                f"은폐 행위 {len(acts)}건 — 현장 조작이 최소 2건은 있어야 흔적이 남는다")
            for a in acts:
                cid = a.get("creates_clue")
                if cid:
                    chk(f"CONCEAL-creates[{cid}]", cid in clue_ids,
                        f"은폐가 만든 단서 {cid}가 clue_graph에 없다")
                did = a.get("destroys_clue")
                if did:
                    chk(f"CONCEAL-destroys[{did}]", did not in clue_ids,
                        f"은폐가 지운 단서 {did}가 아직 clue_graph에 남아 있다")
            # 범인처럼 보이는 근거
            signals = len(acts) + sum(
                1 for cl in clues
                if cl.get("points_to") == c["id"] or c["id"] in (cl.get("suspects") or []))
            chk(f"CONCEAL-looks_guilty[{c['id']}]", signals >= CONCEAL_MIN_SIGNALS,
                f"유죄로 보이는 근거 {signals}개 — 충분히 속아야 반전이 산다")

    # ── AI 목표 충돌 ──────────────────────────────────────────
    withobj = [c for c in cast if c.get("objectives")]
    if withobj:
        chk("OBJ-all_have", len(withobj) == len(cast),
            f"목표 보유 {len(withobj)}/{len(cast)}명 — 전원에게 있어야 한다")
        chk("OBJ-culprit_inverted",
            any("않" in (o.get("desc") or "") or o.get("invert")
                for o in (culprit or {}).get("objectives", [])),
            "범인의 목표는 반대여야 한다(잡히지 않기)")
        # hidden_from 이 서로를 가리키면 충돌
        conflicts = 0
        for a in cast:
            for sec in (a.get("secrets") or []):
                for t in (sec.get("hidden_from") or []):
                    if t in by_id and t != a["id"]:
                        conflicts += 1
        chk("OBJ-conflict_pairs", conflicts >= OBJ_MIN_CONFLICTS,
            f"비밀-대상 충돌 {conflicts}쌍 (최소 {OBJ_MIN_CONFLICTS}) — 없으면 심문이 밋밋하다")

    # ── 배점 ──────────────────────────────────────────────────
    sc = s.get("scoring")
    if sc:
        nsec = sum(len(c.get("secrets") or []) for c in cast)
        expect = sc.get("culprit_correct", 0) + sc.get("secret_revealed_each", 0) * nsec
        chk("SCORE-max_consistent", sc.get("max") == expect,
            f"만점 {sc.get('max')} vs 계산값 {expect} (범인 {sc.get('culprit_correct')} + 비밀 {nsec}개)")
        # 모든 비밀이 도달 가능한가
        unreachable = [c["id"] for c in cast
                       if (c.get("secrets") and not c.get("pressure_points"))]
        chk("SCORE-secrets_reachable", not unreachable,
            f"심문으로 도달 불가한 비밀 보유자: {unreachable}")

    # ── ★ 실토 규칙 — 버티기로 판이 멈추지 않는가 ──────────────
    #   실제 보드게임 플레이에서 나온 최대 문제: 전원이 비밀을 지키느라
    #   아무 정보도 열지 않아 진행이 멈춘다. 비밀은 '찾아내면 반드시 열리는 문'이어야 한다.
    dr = s.get("disclosure_rule")
    has_secrets = any(c.get("secrets") for c in cast)
    if has_secrets:
        chk("DISCLOSE-rule_present", bool(dr),
            "실토 규칙이 없다 — 전원이 버티면 게임이 멈춘다")
        if dr:
            chk("DISCLOSE-secrets_only", dr.get("applies_to") == "secrets_only",
                "강제 실토는 **비밀만** 대상이어야 한다. 범행 자백까지 포함하면 추리가 사라진다")
            kinds = {t.get("kind") for t in (dr.get("triggers") or [])}
            chk("DISCLOSE-two_paths", {"pressure_point", "evidence_shown"} <= kinds,
                f"실토 경로 {kinds} — 심문(정곡)과 증거제시 **양쪽**이 있어야 한다")

        for c in cast:
            for i, sec in enumerate(c.get("secrets") or []):
                fb = sec.get("forced_by") or []
                chk(f"DISCLOSE-forced_by[{c['id']}#{i}]", len(fb) >= 1,
                    f"{c['name']}의 비밀에 강제 공개 경로가 없다 — 끝까지 버틸 수 있다")
                # forced_by가 실제로 존재하는 단서/소지품을 가리키는가
                all_bel = {b.get("id") for x in cast for b in (x.get("belongings") or [])}
                ghost = [x for x in fb if x not in clue_ids and x not in all_bel]
                chk(f"DISCLOSE-forced_by_exists[{c['id']}#{i}]", not ghost,
                    f"존재하지 않는 단서를 가리킴: {ghost}")
                chk(f"DISCLOSE-line[{c['id']}#{i}]", len(sec.get("confession_line", "")) >= 15,
                    "실토 대사가 없다 — 에이전트가 무엇을 말해야 할지 모른다")

        # 범인의 '범행 자백'이 강제 실토에 섞이면 안 된다
        if culprit:
            leak = [sec for sec in (culprit.get("secrets") or [])
                    if any(w in (sec.get("confession_line") or "")
                           for w in ["내가 죽였", "내가 쳤", "내가 그랬", "제가 죽였"])]
            chk("DISCLOSE-no_confession_leak", not leak,
                "범인의 강제 실토 대사에 범행 자백이 섞였다 — 증거 없이 정답이 나온다")

    # ── 분 단위 타임라인 ──────────────────────────────────────
    tev = s.get("timeline_events") or []
    if tev:
        chk("TIME-enough_events", len(tev) >= 8,
            f"타임라인 사건 {len(tev)}개 — 촘촘해야 알리바이 교차검증이 산다")
        # 밤을 넘기는 사건이므로 자정 이후(12시 미만)는 +24시간으로 본다.
        # 그래야 21:00 → 00:10 → 04:40 이 올바른 순서로 읽힌다.
        def _t(e):
            try:
                h, m = (e.get("time", "00:00").split(":") + ["0"])[:2]
                v = int(h) + int(m) / 60.0
            except Exception:
                return 0.0
            return v + (24.0 if v < 12.0 else 0.0)
        chk("TIME-sorted", all(_t(a) <= _t(b) for a, b in zip(tev, tev[1:])),
            "타임라인이 시각 순으로 정렬돼 있지 않다(자정 넘김 보정 적용)")
        chk("TIME-has_known_from", all(e.get("known_from") for e in tev),
            "각 사건이 **무엇을 통해 알려지는지**가 없다 — 플레이어가 도달할 수 없는 정보가 생긴다")
        slots = {e.get("slot") for e in tev}
        chk("TIME-covers_slots", set(s.get("time_slots", [])) <= slots,
            f"3슬롯 중 비어 있는 구간이 있다: {set(s.get('time_slots',[])) - slots}")
        # 사망 시각이 타임라인에 있는가
        chk("TIME-has_murder", any("★" in (e.get("text") or "") for e in tev),
            "결정적 순간(★)이 타임라인에 표시돼 있지 않다")

    # ── 이중 사건 ─────────────────────────────────────────────
    inc = s.get("incidents") or []
    if len(inc) >= 2:
        for i in inc:
            own = [cl["id"] for cl in clues if cl.get("incident") == i["id"]]
            chk(f"INCIDENT-clues[{i['id']}]", len(own) >= 1,
                f"사건 {i['id']}({i.get('type')}) 전용 단서 {len(own)}개 — 분리 불가능하면 두 사건이 뒤엉킨다")
        actors = {i.get("culprit") for i in inc if i.get("culprit")}
        chk("INCIDENT-different_actors", len(actors) >= 2,
            f"사건 주체 {actors} — 같으면 이중 사건의 의미가 없다")

    # ── 소지품 ────────────────────────────────────────────────
    bel = [(c["id"], b) for c in cast for b in (c.get("belongings") or [])]
    if bel:
        bad = [f"{cid}/{b.get('id')}" for cid, b in bel if not (b.get("obtainable_by") or [])]
        chk("BELONG-reachable", not bad, f"도달 경로 없는 소지품: {bad}")
        # 두 소지품이 만나야 완성되는 조합이 있는가 (보드게임의 핵심 재미)
        combos = [b for _, b in bel if b.get("combines_with")]
        chk("BELONG-has_combo", len(combos) >= 1,
            "두 물증이 만나야 완성되는 조합이 최소 1개는 있어야 한다")
        for b in combos:
            partner = b.get("combines_with")
            chk(f"BELONG-combo_exists[{b.get('id')}]",
                any(x.get("id") == partner for _, x in bel),
                f"조합 상대 {partner}가 존재하지 않는다")
            owners = {cid for cid, x in bel if x.get("id") in (b.get("id"), partner)}
            chk(f"BELONG-combo_split[{b.get('id')}]", len(owners) >= 2,
                f"조합 물증 두 개가 같은 사람({owners}) 손에 있으면 교환의 재미가 없다")

    # ── ★ 시각 레이어 — 트릭이 그림으로 성립하는가 ─────────────
    #   실제 플레이 소감: "전부 글이라 상상해야 해서 힘들었다".
    #   그리고 가장 소름 돋는 순간은 '금색 가운 때문에 착각했다'를 알아챈 순간이었다.
    #   → 오인의 근거가 되는 물건은 눈으로 알아볼 수 있게 그려져야 한다.
    vis = s.get("visuals")
    if vis:
        objs = vis.get("key_objects") or []
        chk("VIS-key_objects", len(objs) >= 1,
            "트릭 핵심 오브젝트가 정의되지 않았다 — 그림으로 전달할 대상이 없다")
        for o in objs:
            chk(f"VIS-design[{o.get('id')}]", len(o.get("design", "")) >= 30,
                f"{o.get('name')}의 도안 지시가 부실하다 — 디자인팀이 매번 다르게 그린다")
            chk(f"VIS-identical[{o.get('id')}]", len(o.get("must_be_identical_in") or []) >= 2,
                f"{o.get('name')}이 같은 그림으로 재등장하는 자리가 명시되지 않았다 — "
                "같은 물건이 다르게 그려지면 플레이어가 잇지 못한다")

        sa = vis.get("scene_art") or {}
        shown = {m.get("condition") for m in (sa.get("must_show") or [])}
        if trick.get("type") == "misidentification":
            conds = trick.get("conditions") or []
            # 조건 문자열의 앞머리(— 앞 부분)가 must_show에 대응하는지
            heads = [c.split("—")[0].strip() for c in conds]
            missing = [h for h in heads if not any(h in x for x in shown)]
            chk("VIS-misid_all_shown", not missing,
                f"현장 일러스트에 빠진 오인 조건: {missing} — 그림에 없으면 트릭이 전달되지 않는다")
            chk("VIS-scene_hides_face",
                any("얼굴" in x for x in (sa.get("must_not_show") or [])),
                "현장 그림이 피해자 얼굴을 가리지 않으면 오인이 성립하지 않는다")
            chk("VIS-reveal_cut", len((vis.get("reveal_cut") or {}).get("frames") or []) >= 3,
                "오인 순간을 되짚는 재구성 컷이 없다 — '아하'가 터질 자리가 없다")

        # 표적의 초상화가 그 물건을 걸치고 있어야 오인의 전제가 선다
        tgt = (culprit or {}).get("mmo", {}).get("motive_target")
        if tgt:
            p = next((x for x in (vis.get("portraits") or []) if x.get("cast") == tgt), None)
            chk("VIS-target_wears_object", bool(p and p.get("must_wear")),
                f"표적({tgt})의 초상화에 오인 물건이 지정되지 않았다 — "
                "플레이어가 '그 옷'을 알아볼 근거가 없다")

        # 그림만으로 정답이 새면 안 된다
        blob = json.dumps(vis, ensure_ascii=False)
        cname = (culprit or {}).get("name", "\x00")
        leak = ("범인" in blob and cname in blob and "must_not_show" not in blob)
        chk("VIS-no_spoiler", not leak,
            "시각 지시에 범인이 노출된다")

    # ── ★ 교차 단서 — 단서가 다른 사람에게도 물리는가 ──────────
    #   A의 방에서 나온 것이 B의 비밀을 건드려야, 심문이 서로 물린다.
    #   보드게임에서 카드를 서로 보여주게 되는 이유가 정확히 이것이다.
    cross = [cl for cl in clues if cl.get("affects")]
    if cross:
        chk("CROSS-enough", len(cross) >= 3,
            f"교차 단서 {len(cross)}개 — 적으면 인물들이 서로 무관해진다")
        multi = [cl for cl in cross if len(cl.get("affects") or []) >= 2]
        chk("CROSS-multi_target", len(multi) >= 2,
            f"두 명 이상에게 걸리는 단서 {len(multi)}개 — 이게 관계를 만든다")
        # 자기 방 밖의 단서로도 건드려지는 인물이 있는가
        place_owner = {p["id"]: p.get("owner") for p in s.get("map", {}).get("places", [])}
        touched_elsewhere = set()
        for cl in cross:
            owner = place_owner.get(cl.get("location"))
            for t in (cl.get("affects") or []):
                if t != owner:
                    touched_elsewhere.add(t)
        chk("CROSS-outside_own_room", len(touched_elsewhere) >= 3,
            f"제 방 밖의 단서에 걸리는 인물 {len(touched_elsewhere)}명 — "
            "각자 제 방 단서만 있으면 '따로 노는 5명'이 된다")
        ghost = {t for cl in cross for t in (cl.get("affects") or [])} - set(by_id)
        chk("CROSS-targets_exist", not ghost, f"존재하지 않는 인물 지목: {ghost}")

    # ── ★ 장소 재방문 층 ──────────────────────────────────────
    pl = s.get("place_layers")
    if pl:
        rounds = s.get("config", {}).get("rounds", 3)
        places = [p["id"] for p in s.get("map", {}).get("places", [])]
        miss = [p for p in places if p not in (pl.get("layers") or {})]
        chk("LAYER-all_places", not miss, f"층이 정의되지 않은 장소: {miss}")
        thin = [p for p, v in (pl.get("layers") or {}).items() if len(v) < rounds]
        chk("LAYER-per_round", not thin,
            f"라운드 수({rounds})만큼 층이 없는 장소: {thin} — 재방문할 이유가 사라진다")
        # 2층 이상 단서가 실제로 존재하는가(선언만 하고 단서가 없으면 빈 약속)
        deep = [cl for cl in clues if (cl.get("layer") or 1) >= 2]
        chk("LAYER-deep_clues", len(deep) >= 3,
            f"2층 이상 단서 {len(deep)}개 — 층을 선언만 하고 내용이 없다")

    # ── ★ 페이즈 ──────────────────────────────────────────────
    ph = s.get("phases")
    if ph:
        names = [p.get("name", "") for p in ph]
        chk("PHASE-has_opening", any("오프닝" in n for n in names), "오프닝 페이즈가 없다")
        chk("PHASE-has_rounds",
            sum(1 for n in names if "라운드" in n) == s.get("config", {}).get("rounds", 3),
            f"라운드 페이즈 수가 config.rounds와 다르다: {names}")
        chk("PHASE-has_event", any("이벤트" in n for n in names),
            "중반 이벤트가 페이즈에 자리를 잡지 못했다")
        chk("PHASE-has_ending", any("엔딩" in n for n in names), "엔딩 낭독 페이즈가 없다")
        chk("PHASE-ordered", [p.get("no") for p in ph] == sorted(p.get("no", 0) for p in ph),
            "페이즈 번호가 순서대로가 아니다")

    # ── ★ 엔딩 낭독 ───────────────────────────────────────────
    en = s.get("ending")
    if en:
        gr = en.get("grades") or []
        chk("END-grades", len(gr) >= 3, f"엔딩 등급 {len(gr)}개 — 결과에 따라 달라져야 한다")
        mx = (s.get("scoring") or {}).get("max")
        if mx is not None and gr:
            chk("END-covers_max", max(g.get("min", 0) for g in gr) == mx,
                f"만점({mx})에 해당하는 엔딩이 없다")
            chk("END-covers_zero", min(g.get("min", 99) for g in gr) == 0,
                "0점(전부 놓친) 엔딩이 없다")
        chk("END-truth_reveal", len(en.get("truth_reveal", "")) >= 30,
            "엔딩에서 트릭의 진상을 명시적으로 밝히지 않는다 — 플레이어가 못 풀면 영영 모른다")
        chk("END-reconstruction", bool(en.get("reconstruction")),
            "그날 밤을 시각 순으로 재생하는 지시가 없다")

    # ── 이벤트(중반 반전) ─────────────────────────────────────
    ev = s.get("events") or []
    if ev:
        rounds = s.get("config", {}).get("rounds", 3)
        mid = [e for e in ev if 2 <= e.get("round", 0) <= rounds]
        chk("EVENT-midgame", len(mid) >= 1,
            f"중반({2}~{rounds}라운드) 이벤트 {len(mid)}개 — 판을 뒤집는 장치가 없으면 후반이 늘어진다")
        chk("EVENT-not_round1", all(e.get("round", 0) >= 2 for e in ev),
            "1라운드 이벤트는 도입과 겹쳐 효과가 죽는다")
        chk("EVENT-has_effect", all(e.get("effect") for e in ev),
            "이벤트마다 판을 어떻게 바꾸는지 명시돼야 한다")

    ok = all(c for _, c, _ in R)
    return ok, R


def _print(R, only_fail=False):
    for name, cond, note in R:
        if only_fail and cond: continue
        print(f"  [{'✅' if cond else '❌'}] {name}" + (f"  — {note}" if note else ""))


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "scenarios/23_옹고집.json"
    s = json.load(open(path, encoding="utf-8"))
    ok, R = verify_v2(s)
    print(f"=== verify_v2: {s['meta']['title']} ===")
    if not R:
        print("  (새 필드가 없는 구식 시나리오 — 검사할 항목 없음)")
    else:
        _print(R)
        n = sum(1 for _, c, _ in R if c)
        print(f"\n총 {len(R)}항목 · 통과 {n} · 미달 {len(R)-n}")
    print("✅ v2 통과" if ok else "❌ v2 미달")
