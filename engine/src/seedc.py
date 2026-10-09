# -*- coding: utf-8 -*-
"""
seedc.py — **시드 → 완제품 시나리오** 컴파일러.

왜 필요한가
  24~44를 손으로 지으며 같은 기계 실수를 여덟 번 반복해서 고쳤다:
  범인이 사망 시각에 현장에 없거나, 거짓 알리바이를 아무도 반박 못 하거나,
  무고자의 MMO 다리가 다 차 있거나, 소거만으로 답이 나오거나,
  나레이션이 550자에 못 미치거나. 창작이 아니라 **조립**의 실수들이다.

  그래서 창작(인물·비밀·문장·트릭)은 시드에 쓰고, 조립 규칙은 여기서 보장한다.
  시드가 규칙을 어기면 **컴파일 단계에서 바로 알려 준다** — 게이트까지 갈 것도 없이.

무엇을 보장하나
  · 범인: timeline[사망슬롯]=현장, MMO 전부 참, lies의 false_place는
    다른 인물이 실제로 있는 곳 + 그 인물 knows에 부인 한 줄 자동 추가
  · 무고자: MMO 한 다리 비움(가짜 유력자는 means=False)
  · 소거 구조: 배제 증언 2~3 + 마지막 남는 대조자(foil)는 결정타가 가른다
  · 결정타: 마지막 라운드, points_to=범인, exculpates=[foil, 가짜 유력자]
  · 나레이션: '옛날 옛적' 훅 · 총 550자↑ · 문장 50자↓ 검사
  · motive_label: solution과 범인 카드 일치
  · 좌표: places에 pos 없으면 원둘레 자동 배치

시드 형식은 아래 SEED_DOC 참고. 사용:
    from seedc import compile_seed
    compile_seed(SEED, "scenarios/45_aladdin.json")
"""
import json, math, re, sys

REQ_CAST = ("id", "name", "public", "profile", "kill_motive", "motive_label",
            "secret", "alibi_narration", "knows", "does_not_know",
            "persona", "bio", "life_story")


def _err(msg):
    raise SystemExit(f"[시드 오류] {msg}")


def _auto_pos(places):
    n = len(places)
    for i, p in enumerate(places):
        if "pos" not in p:
            ang = 2 * math.pi * i / max(1, n)
            p["pos"] = [round(1.6 * math.cos(ang), 2), round(1.6 * math.sin(ang), 2)]
    return places


def compile_seed(seed, outpath):
    from skeleton import skeleton

    cast = seed["cast"]
    if len(cast) != 5:
        _err(f"용의자는 5명이어야 한다 (지금 {len(cast)})")
    for c in cast:
        for k in REQ_CAST:
            if not c.get(k):
                _err(f"{c.get('id','?')} {c.get('name','?')} — '{k}' 비어 있음")
        ex = (c["persona"].get("example_lines") or [])
        if len(ex) < 3:
            _err(f"{c['name']} — example_lines 3줄 필요 (지금 {len(ex)})")
        if len(c["life_story"]) < 300:
            _err(f"{c['name']} — life_story 300자 필요 (지금 {len(c['life_story'])})")

    culprit = [c for c in cast if c.get("role") == "culprit"]
    fake = [c for c in cast if c.get("role") == "fake_lead"]
    foil = [c for c in cast if c.get("role") == "foil"]
    if len(culprit) != 1: _err("role='culprit' 정확히 1명")
    if len(fake) != 1: _err("role='fake_lead' 정확히 1명")
    if len(foil) != 1: _err("role='foil' 정확히 1명 (결정타가 마지막에 가르는 대조자)")
    cul, fk, fo = culprit[0], fake[0], foil[0]
    plain = [c for c in cast if c not in (cul, fk, fo)]

    places = _auto_pos(seed["places"])
    pid = {p["id"] for p in places}
    dslot = seed["death"].get("time_slot", "밤")
    dplace = seed["death"]["place"]
    slots = seed.get("time_slots", ["초저녁", "밤", "새벽"])

    # ── 동선 조립 ────────────────────────────────────────────────
    own = {}
    for p in places:
        if p.get("owner"):
            own[p["owner"]] = p["id"]
    for c in cast:
        home = c.get("home") or own.get(c["id"])
        if not home:
            _err(f"{c['name']} — 거처가 없다 (places owner 또는 cast.home)")
        if home not in pid: _err(f"{c['name']} home '{home}' 없음")
        tl = dict(c.get("timeline") or {})
        for sl in slots:
            tl.setdefault(sl, home)
        c["timeline"] = tl
    cul["timeline"][dslot] = dplace           # 범인은 사망 시각에 현장

    # ── MMO ──────────────────────────────────────────────────────
    cul["mmo"] = {"means": True, "motive": True, "opportunity": True}
    cul["is_culprit"] = True
    fk["mmo"] = dict(c_means=False) and {"means": False, "motive": True, "opportunity": True}
    for i, c in enumerate([fo] + plain):
        gap = ["opportunity", "means"][i % 2]
        c["mmo"] = {"means": True, "motive": True, "opportunity": True}
        c["mmo"][gap] = False
    for c in cast:
        c.setdefault("is_culprit", False)
        c.setdefault("lies", [])
        # 정곡 질문 트리거: 비밀을 찌르는 낱말 → 그 인물 말투의 실토 한 단락
        pp = c.get("pressure")
        if not pp:
            _err(f"{c['name']} — pressure 필요: [{{trigger:[낱말 3개↑], reveals:'실토 대사'}}]")
        for x in pp:
            if len(x.get("trigger", [])) < 3:
                _err(f"{c['name']} — pressure trigger 낱말 3개 이상")
            if len(x.get("reveals", "")) < 20:
                _err(f"{c['name']} — pressure reveals 실토 대사가 너무 짧다")
            x.setdefault("unlocks", (c.get("secret") or {}).get("type", "비밀"))
        c["pressure_points"] = pp

    # ── 범인의 거짓말: 반박자 자동 배선 ──────────────────────────
    lie = seed.get("lie")
    if not lie:
        _err("seed['lie'] 필요: {claim, truth, witness(인물 id)}")
    wit = next((c for c in cast if c["id"] == lie["witness"]), None)
    if not wit or wit is cul: _err("lie.witness는 범인이 아닌 인물 id")
    fplace = wit["timeline"][dslot]
    cul["lies"] = [{"claim": lie["claim"], "truth": lie["truth"], "false_place": fplace}]
    deny = lie.get("deny") or f"그 밤 {cul['name']}{_j(cul['name'],'은/는')} 내 곁에 오지 않았다 — {lie['claim'][:20]}…는 말은 사실이 아니다."
    if deny not in wit["knows"]:
        wit["knows"].append(deny)

    # ── 단서 역할 검사 ───────────────────────────────────────────
    clues = seed["clues"]
    ids = [c["id"] for c in clues]
    if len(ids) != len(set(ids)): _err("단서 id 중복")
    dec = [c for c in clues if c.get("decisive")]
    if len(dec) != 1: _err("결정타 정확히 1개")
    dec = dec[0]
    dec["points_to"] = cul["id"]
    dec.setdefault("exculpates", [])
    for x in (fo["id"], fk["id"]):
        if x not in dec["exculpates"]:
            dec["exculpates"].append(x)
    rumor = [c for c in clues if c.get("weight") == "red_herring" and c.get("points_to")]
    if not rumor: _err("가짜 유력자를 미는 소문(red_herring+points_to) 1개 필요")
    for r in rumor:
        r["points_to"] = fk["id"]
    # 배제 증언: plain 전원 + (선택) fake — foil은 결정타 전엔 배제 금지
    exc_targets = {x for c in clues if not c.get("decisive")
                   for x in (c.get("exculpates") or [])}
    for c in plain:
        if c["id"] not in exc_targets:
            _err(f"{c['name']}({c['id']}) 배제 증언 없음 — spine 단서에 exculpates 추가")
    if fo["id"] in exc_targets:
        _err(f"foil {fo['name']}은 결정타 전에 배제되면 안 된다")
    rounds = seed.get("rounds", 3)
    for c in clues:
        c.setdefault("reveal_round", 1)
        c.setdefault("points_to", None)
        c.setdefault("exculpates", [])
        c.setdefault("decisive", False)
    dec["reveal_round"] = rounds

    # ── 나레이션 검사 ────────────────────────────────────────────
    nar = seed["intro"]["narration"]
    total = sum(len(b["text"]) for b in nar)
    if total < 550: _err(f"나레이션 {total}자 — 550자 필요")
    first = nar[0]["text"]
    era_all = seed["meta"].get("era", "") + seed["background"]["setting_raw"].get("location", "")
    modern = any(k in era_all for k in ("현대", "202", "192"))
    if not modern and "옛날" not in first[:12]:
        _err("나레이션 1컷은 '옛날 옛적'류 훅으로")
    for b in nar:
        for s_ in re.split(r"(?<=[.?!])\s+", b["text"]):
            if len(s_) > 60:
                _err(f"나레이션 문장 60자 초과: {s_[:30]}…")

    # ── solution 정합 ────────────────────────────────────────────
    sol = seed["solution"]
    sol["culprit"] = cul["id"]
    sol["motive_label"] = cul["motive_label"]
    if sol["weapon"] not in seed["choices"]["weapon"]:
        _err("solution.weapon이 choices.weapon에 없음")

    S = skeleton(
        meta=seed["meta"], background=seed["background"], adapted=seed["adapted"],
        trick=seed["trick"], intro=seed["intro"], victim=seed["victim"],
        death=seed["death"], places=places, cast=cast, clues=clues,
        choices=seed["choices"], solution=sol)
    S["time_slots"] = slots
    S["config"]["rounds"] = rounds
    json.dump(S, open(outpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"컴파일 OK → {outpath}  (용의자 5 · 단서 {len(clues)} · {rounds}라운드)")
    return S


def _j(w, pair="을/를"):
    a, b = pair.split("/")
    if not w: return b
    ch = w[-1]
    if not ("가" <= ch <= "힣"): return b
    return a if (ord(ch) - 0xAC00) % 28 else b
