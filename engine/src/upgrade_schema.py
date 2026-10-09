# -*- coding: utf-8 -*-
"""
upgrade_schema.py — 구식 시나리오(01~22편)를 **보드게임 구조(v2)**로 올린다.

왜 필요한가
  23편만 새 구조다. 나머지 22편에는
      secrets[] / belongings[] / objectives[] / timeline_events /
      incidents / events / scoring / disclosure_rule / phases / ending /
      visuals / place_layers
  가 통째로 없다. 그래서 다른 편을 켜면 **옛 로직으로 도는 것**이다.
  특히 secrets[].forced_by가 없으면 stance.py가 ADMIT을 못 건다.
  = 형이 실제 플레이에서 겪은 "아무도 입을 안 열어 판이 멈춘다"가 그대로 재현된다.

무엇을 지어내지 않는가
  이 도구는 **없는 사실을 창작하지 않는다.** 이미 시나리오 안에 있는 것
  (secret, pressure_points, clue_graph, timeline, map, solution)을 다시 엮어
  새 구조의 자리에 앉힐 뿐이다. 창작이 필요한 자리(오인 살인의 조건 등)는
  건드리지 않고 비워 둔다 — 억지로 채우면 검증은 통과하고 게임은 죽는다.

사용:
    python upgrade_schema.py out/13_푸른수염.json
    python upgrade_schema.py "scenarios/[0-9]*.json"
"""
import json, glob, sys, re

THEFT = re.compile(r"(훔|빼돌|절도|도둑|은식기|팔아|가로채)")
STOP = set("그것 이것 저것 하는 있는 것도 것을 하고 했다 사실 그런 이런".split())
# 이름 자리에 오면 안 되는 말 — 부사·군말
ADV = set("몰래 다시 함께 이미 아직 가장 매우 서로 마침 겨우 결국 도리어 하필 그날 그때".split())
JOSA_TAIL = ("을", "를", "이", "가", "은", "는", "에", "의", "와", "과", "도", "로", "께", "에서", "에게")
VERB_TAIL = ("다", "려", "긴", "한", "어", "여", "린", "운", "된", "진", "친", "혀", "고",
             "아", "야", "워", "서", "져", "켜", "쳐", "며", "면", "지", "기")


def _noun(w):
    """낱말에서 조사를 떼고, 서술어처럼 보이면 버린다."""
    for j in sorted(JOSA_TAIL, key=len, reverse=True):
        if w.endswith(j) and len(w) > len(j) + 1:
            w = w[: -len(j)]
            break
    if len(w) < 2 or w in STOP or w in ADV or w.endswith(VERB_TAIL):
        return ""
    return w


def _j(w, pair="을/를"):
    a, b = pair.split("/")
    if not w:
        return b
    ch = w[-1]
    if not ("가" <= ch <= "힣"):
        return b
    jong = (ord(ch) - 0xAC00) % 28
    if pair == "으로/로":
        return b if jong in (0, 8) else a
    return a if jong else b


def _toks(t):
    return {w for w in re.findall(r"[가-힣]{2,}", t or "") if w not in STOP}


def _overlap(a, b):
    A, B = _toks(a), _toks(b)
    return len(A & B)


# ── ① 비밀 단서 찾기 — 그 인물의 비밀을 드러내는 단서 ────────────────
def _secret_clue(c, s, taken=()):
    """clue_graph에서 이 인물의 비밀을 가리키는 단서를 고른다.
    장소 채널 단서가 대개 '그 방에서 나온 물건'이라 여기에 해당한다."""
    sec = (c.get("secret") or {}).get("text", "")
    own_place = next((p["id"] for p in s["map"]["places"] if p.get("owner") == c["id"]), None)
    best, score = None, 0
    for cl in s.get("clue_graph", []):
        # ★ 결정적 단서는 비밀의 짐이 될 수 없다.
        #   그것은 살인을 푸는 열쇠지 '부끄러운 사정'이 아니다.
        #   짐 카드로 만들면 그 카드를 쥔 순간 사건이 끝나 버리고,
        #   실토 규칙(비밀만 강제 공개)에도 어긋난다.
        if (cl.get("channel") not in ("location","record","physical") or cl.get("id") in taken
                or cl.get("decisive") or cl.get("points_to")):
            continue
        v = _overlap(cl.get("surface", ""), sec)
        if cl.get("id", "").startswith("S"):
            v += 1
        if v > score:
            best, score = cl, v
    return best, own_place


def _item_name(surface, pname="제 방", stype=""):
    """짐 카드에 적을 **짧은 이름**.

    단서 문장에서 명사구가 깔끔하게 떨어질 때만 그것을 쓰고,
    아니면 만들지 않는다 — 문장을 억지로 잘라 '오라비만', '이름' 같은
    부스러기를 이름에 넣느니, 장소와 성격으로 부르는 편이 낫다.
    자세한 내용은 어차피 reveals에 그대로 실린다.
    """
    t = (surface or "").strip().rstrip(". ")
    cand = ""
    if "," in t:                       # '별채에서 나온, …낡은 편지' 꼴
        cand = t.split(",")[-1].strip()
    elif "—" not in t and "에서 나온" in t:
        cand = t.split("에서 나온", 1)[1].strip()
    cand = re.sub(r"^(그|이|저)\s+", "", cand).strip(" .")
    # 문장이거나 매달린 말이면 쓰지 않는다
    ok = (cand and 2 <= len(cand) <= 24
          and not re.search(r"(다|요|소|오)$", cand)
          and not re.search(r"(은|린|힌|긴|난|든|준|된|과|와|의|을|를|이|가)$", cand))
    if ok:
        return cand
    label = stype or "감춘 사정"
    return f"{pname}에서 나온 것 ({label})"


# ── ② 누구에게 감추는가 — 얽힘에서 적대적인 상대를 고른다 ────────────
ADVERSARIAL = {"약점", "의심", "목격", "다툼", "자리 다툼", "빚"}


def _hidden_from(c, s):
    picks = []
    for e in (s.get("relation_web") or []):
        if e.get("type") not in ADVERSARIAL:
            continue
        if e["a"] == c["id"]:
            picks.append(e["b"])
        elif e["b"] == c["id"]:
            picks.append(e["a"])
    if picks:
        return picks[:1]
    other = [x["id"] for x in s["cast"] if x["id"] != c["id"]]
    return other[:1]


# ── ③ 목표 ───────────────────────────────────────────────────────────
def _objectives(c, s):
    sec = (c.get("secret") or {}).get("text", "")
    short = sec if len(sec) <= 26 else sec[:24] + "…"
    if c.get("is_culprit"):
        return [
            {"desc": "진범으로 지목되지 않는다", "priority": 1, "invert": True,
             "tactics": ["알리바이를 되풀이한다", "다른 이의 수상한 점을 먼저 꺼낸다"]},
            {"desc": f"{short} — 이것을 끝까지 감춘다", "priority": 2,
             "tactics": ["묻지 않은 것은 말하지 않는다", "화제를 사건 쪽으로 돌린다"]},
        ]
    return [
        {"desc": f"{short} — 이것을 감춘다", "priority": 1,
         "tactics": ["모르는 일이라 잡아뗀다", "다른 이야기로 넘긴다"]},
        {"desc": "진범을 찾아내 내 혐의를 벗는다", "priority": 2,
         "tactics": ["내가 본 것을 말한다", "남의 어긋난 말을 짚는다"]},
    ]


# ── ④ 분 단위 타임라인 ───────────────────────────────────────────────
def _timeline(s):
    slots = s["time_slots"]
    pd = {p["id"]: p["name"] for p in s["map"]["places"]}
    cast = s["cast"]
    dslot = s["death"]["time_slot"]
    # 무대에 맞는 말 — '성'은 성이 있는 이야기에만
    loc = str(((s.get("background") or {}).get("setting_raw") or {}).get("location", ""))
    era = str(((s.get("background") or {}).get("setting_raw") or {}).get("era", ""))
    modern = any(k in era + loc for k in ("현대", "202", "192", "사무실", "도시", "대학", "학교"))
    stage = "장내" if modern else ("성 안" if "성" in loc else "집 안")
    ev = [{"time": "20:00", "slot": slots[0], "who": "all",
           "text": f"{stage}가 조용해지고 사람들이 제 자리로 흩어진다." if stage != "장내"
                   else "저마다의 일로 하루가 저물고, 사람들이 흩어져 있다.",
           "known_from": "모두가 아는 일"}]
    t = 20 * 60 + 20
    for c in cast:                                   # 초저녁 각자의 자리
        pl = pd.get((c.get("timeline") or {}).get(slots[0]), "제 자리")
        ev.append({"time": f"{t//60:02d}:{t%60:02d}", "slot": slots[0], "who": c["id"],
                   "text": f"{pl}에 있었다.", "known_from": "본인 진술"})
        t += 10
    # ★ 결정적 순간
    cul = next((c for c in cast if c.get("is_culprit")), None)
    dp = pd.get(s["death"]["place"], "현장")
    ev.append({"time": "23:00", "slot": dslot, "who": (cul or {}).get("id", "all"),
               "text": f"★{dp}에서 {s['victim']['name']}{_j(s['victim']['name'],'이/가')} 살해된다.",
               "known_from": "검안 결과와 현장"})
    t = 23 * 60 + 20
    for c in cast:                                   # 사망 시각대의 자리
        if cul and c["id"] == cul["id"]:
            continue
        pl = pd.get((c.get("timeline") or {}).get(dslot), "제 자리")
        ev.append({"time": f"{t//60:02d}:{t%60:02d}", "slot": dslot, "who": c["id"],
                   "text": f"{pl}에 있었다.", "known_from": "본인 진술과 증언"})
        t += 10
    ev.append({"time": "05:00", "slot": slots[-1], "who": "all",
               "text": f"{dp}에서 주검이 발견되어 {'장내가' if modern else ('성이' if '성' in loc else '온 집이')} 발칵 뒤집힌다.",
               "known_from": "모두가 아는 일"})
    return ev


# ── ⑤ 교차 단서 — 한 단서가 다른 사람에게도 물리게 ───────────────────
def _cross(s, owned):
    """owned = {인물id: 그 인물의 비밀 단서}. 이미 1:1로 짝지어 둔 것을 쓴다.

    한 단서는 **주인 + 또 한 사람**을 건드려야 한다.
    말이 겹치는 사람이 없으면 relation_web의 얽힘 상대를 쓴다 —
    지어낸 관계가 아니라 이미 시나리오에 있는 얽힘이다."""
    cast = s["cast"]
    by_id = {c["id"]: c for c in cast}
    owner_of = {p.get("owner"): p["id"] for p in s["map"]["places"] if p.get("owner")}
    ties = {}
    for e in (s.get("relation_web") or []):
        ties.setdefault(e["a"], []).append(e["b"])
        ties.setdefault(e["b"], []).append(e["a"])
    n = 0
    used = set()          # 이미 남의 단서에 걸린 사람 — 되도록 겹치지 않게 편다
    for cid, cl in owned.items():
        if not cl:
            continue
        surf = cl.get("surface", "")
        others = [c for c in cast if c["id"] != cid]
        def _score(c):
            v = _overlap(surf, (c.get("secret") or {}).get("text", "") + " " +
                         (c.get("kill_motive") or ""))
            if c["id"] in ties.get(cid, []):
                v += 1                       # 이미 얽힌 사이면 자연스럽다
            if c["id"] in used:
                v -= 3                       # 한 사람에게 몰리면 나머지가 따로 논다
            return v
        oth = max(others, key=_score)
        if _score(oth) <= 0:
            cand = [x for x in ties.get(cid, []) if x in by_id and x != cid and x not in used]
            cand += [x for x in ties.get(cid, []) if x in by_id and x != cid]
            oth = by_id[cand[0]] if cand else oth
        used.add(oth["id"])
        cl["affects"] = [cid, oth["id"]]
        # 원래 장소가 적혀 있으면 건드리지 않는다.
        # (서재 문갑에서 나온 물건을 주인 방으로 옮기면 장소가 텅 빈다)
        if not cl.get("location"):
            cl["location"] = owner_of.get(cid)
        n += 1
    # 층은 장소 단서에만 매기면 모자란다 — 뒤 라운드 단서는 모두 깊은 층이다
    for cl in s.get("clue_graph", []):
        cl["layer"] = max(1, min(3, cl.get("reveal_round", 1)))
    return n


# ── ⑥ 장소 층 ────────────────────────────────────────────────────────
def _layers(s):
    rounds = s.get("config", {}).get("rounds", 3)
    out = {}
    for p in s["map"]["places"]:
        f = list(p.get("features") or [])
        base = [f[0] if f else f"{p['name']}의 겉모습"]
        base.append(f[1] if len(f) > 1 else f"{p['name']}을(를) 다시 보면 눈에 걸리는 것")
        base.append(f[2] if len(f) > 2 else f"{p['name']}에서 마지막까지 남는 자취")
        out[p["id"]] = base[:rounds] + base[:1] * max(0, rounds - 3)
    return {"note": "라운드마다 같은 장소에서 다른 것이 나온다", "layers": out}


# ── ⑦ 나머지 뼈대 ────────────────────────────────────────────────────
def _phases(s):
    rounds = s.get("config", {}).get("rounds", 3)
    ph = [{"no": 0, "name": "오프닝",
           "content": "나레이션 낭독 → 인물 공개 정보 → 현장 검안", "time": "약 5분"}]
    no = 1
    for r in range(1, rounds + 1):
        ph.append({"no": no, "name": f"{r}라운드",
                   "content": f"장소 {r}층 조사 → 심문 → 라운드 정리", "time": "약 10분"})
        no += 1
        if r == 1:
            ph.append({"no": no, "name": "★이벤트",
                       "content": "판을 흔드는 사실이 하나 터진다", "time": "약 1분"})
            no += 1
    ph.append({"no": no, "name": "지목", "content": "각자 범인·흉기·동기를 적어 낸다", "time": "약 3분"})
    ph.append({"no": no + 1, "name": "엔딩 낭독",
               "content": "점수에 따른 엔딩을 읽고, 그날 밤을 시각 순으로 재생한다", "time": "약 5분"})
    return ph


def _ending(s, mx):
    sol = s.get("solution", {})
    cul = next((c for c in s["cast"] if c.get("is_culprit")), {})
    # 이 밤이 벌어진 공간의 이름 — 배경마다 다르므로 현장에서 가져온다
    _pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    _wh = re.sub(r"\s*[(（][^)）]*[)）]", "",
                 _pn.get((s.get("death") or {}).get("place"), "")).strip() or "그 자리"
    _wh = _wh + ("은" if ("가" <= _wh[-1] <= "힣" and (ord(_wh[-1]) - 0xAC00) % 28) else "는")
    return {
        "grades": [
            # ★배경을 가리지 않는 말로 (2026-08-25). 예전엔 '성'과 '집'이 박혀 있어
            #   현대 대학 도서관 편에서도 성이 잠겼다.
            {"min": 0, "name": "미궁",
             "text": f"아무도 진상에 닿지 못했다. {_wh} 그 밤의 일을 삼킨 채 문을 닫는다."},
            # ★ 등급 글은 점수만 보고 고른다. '범인을 못 밝혔다'처럼
            #   지목 결과를 단정하면, 맞힌 사람에게 틀렸다는 말이 나간다.
            {"min": max(1, mx // 3), "name": "절반의 진실",
             "text": "몇 가지는 드러났으나, 그 밤이 감추고 있던 것의 절반은 그대로 묻혔다."},
            {"min": max(2, mx * 2 // 3), "name": "밝혀진 밤",
             "text": "많은 것이 제자리를 찾았다. 다만 끝내 열리지 않은 입이 남아 있다."},
            {"min": mx, "name": "완전한 해명",
             "text": "감춰진 것이 하나도 남지 않았다. 모든 사정이 제자리를 찾았다."},
        ],
        "truth_reveal": (sol.get("reason") or "")[:400] or
                        f"진범은 {cul.get('name','')}이었다. " + (s.get("trick", {}).get("desc") or ""),
        "reconstruction": {
            "note": "그날 밤을 시각 순으로 되짚어 보여 준다",
            "from": "timeline_events",
        },
    }


# ── 중반 이벤트 — 판을 흔드는 방식은 하나가 아니다 ──────────────────
#   여섯 갈래를 두고 시나리오마다 다른 것을 뽑는다. 제목으로 씨앗을 고정해
#   다시 돌려도 같은 결과가 나온다.
#   ※ 전부 **이미 시나리오에 있는 사실**로만 만든다. 없는 사건을 지어내지 않는다.
EVENT_KINDS = [
    ("새 증언", "새증언",
     "{who}{j_ga} 감추던 것이 남의 입에서 먼저 나온다.",
     "{cid}의 비밀 단서가 즉시 공개되고, 그 인물의 압박이 한 단계 오른다"),
    ("사라진 물건", "증거소실",
     "{place}에 있던 {thing}{j_thing} 없어졌다. 누군가 밤사이 손을 댔다.",
     "{place}{j_eul} 다시 뒤져야 한다. 그 자리를 오간 사람이 좁혀진다"),
    ("자리를 뜬 사람", "인물이탈",
     "{who}{j_ga} 심문 자리를 벗어나 {place} 쪽으로 갔다가 돌아왔다.",
     "{cid}에게 그 사이 무엇을 했는지 물을 수 있게 된다. 압박이 오른다"),
    ("밖에서 온 기별", "외부개입",
     "바깥에서 기별이 왔다. 날이 밝기 전에 {place}{j_eul} 봉해야 한다는 전갈이다.",
     "남은 심문 턴이 줄고, {place} 조사는 이번 라운드가 마지막이 된다"),
    ("앞말 뒤집기", "자백번복",
     "{who}{j_ga} 앞서 한 말을 스스로 거두었다. 앞뒤가 맞지 않는다.",
     "{cid}의 진술 모순이 성립한다. 그 인물의 압박이 오른다"),
    ("두 번째 소동", "두번째사건",
     "{place}에서 소동이 인다. 다친 사람은 없으나 자리가 흐트러졌다.",
     "{place}의 다음 층 단서가 앞당겨 열린다"),
]


def _events(s):
    """★ 손으로 쓴 이벤트(_hand_events)는 건드리지 않는다.
    자동 생성이 사람이 쓴 것을 덮으면 좋은 장면이 사라진다 — 한 번 겪었다."""
    if s.get("_hand_events") and s.get("events"):
        return s["events"]
    import hashlib
    cast = s["cast"]
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    seed = hashlib.sha256(((s.get("meta") or {}).get("title") or "x").encode()).digest()[0]
    kind = EVENT_KINDS[seed % len(EVENT_KINDS)]
    name, klass, text, effect = kind

    # 이벤트에 쓸 인물·장소·물건은 **이미 있는 것**에서 고른다
    c = next((x for x in cast if not x.get("is_culprit") and x.get("pressure_points")), cast[0])
    others = [x for x in cast if not x.get("is_culprit")] or cast
    c = others[seed % len(others)]
    own = next((p for p in s["map"]["places"] if p.get("owner") == c["id"]), None)
    place = (own or {}).get("name") or pn.get(s["death"]["place"], "현장")
    bel = (c.get("belongings") or [{}])[0]
    thing = bel.get("name") or "그 방의 물건"
    # ★물건 이름이 장소를 되풀이하지 않게 한다 (2026-08-25).
    #   소지품 이름이 "바깥 객방에서 나온 것 (고리대)" 꼴이라
    #   "바깥 객방에 있던 바깥 객방에서 나온 것 (고리대)가 없어졌다"가 됐다.
    thing = re.sub(r"^\s*" + re.escape(place) + r"에서 나온 것\s*", "", thing).strip()
    m = re.match(r"^\(?([^()]+)\)?$", thing)
    if m:
        thing = m.group(1).strip()
    thing = thing or "그 방의 물건"

    f = dict(who=c["name"], j_ga=_j(c["name"], "이/가"), cid=c["id"],
             place=place, thing=thing,
             j_eul=_j(place, "을/를"),
             j_thing=_j(thing, "이/가"))   # 물건의 조사는 인물 것과 다르다
    return [{
        "round": 2, "name": name, "kind": klass,
        "text": text.format(**f),
        "effect": effect.format(**f),
    }]


def _visuals(s):
    w = s["death"].get("weapon", "흉기")
    dp = next((p for p in s["map"]["places"] if p["id"] == s["death"]["place"]), {})
    return {
        "key_objects": [{
            "id": "V1", "name": w,
            "design": (f"{w} — 현장에서 사라졌다가 되돌아오는 물건. 손잡이의 흠집과 얼룩까지 "
                       f"매번 똑같이 그린다. 플레이어가 두 장면을 잇는 단 하나의 실마리다."),
            "must_be_identical_in": ["현장 일러스트", "증거 카드", "엔딩 재구성 컷"],
        }],
        "scene_art": {
            "must_show": [{"condition": f"{dp.get('name','현장')}의 배치",
                           "why": "장소를 눈으로 익혀야 동선 이야기가 통한다"},
                          {"condition": "주검의 자세",
                           "why": "상처 방향과 저항 여부가 그림으로 읽혀야 한다"},
                          {"condition": "사라진 물건의 빈자리",
                           "why": "없어진 것이 보여야 플레이어가 찾을 생각을 한다"}],
            "must_not_show": ["범인의 얼굴", "범인을 특정할 수 있는 옷·장신구"],
        },
    }


# ── 실행 ─────────────────────────────────────────────────────────────
def upgrade(s):
    if any(c.get("secrets") for c in s["cast"]):
        return 0                                   # 이미 v2
    cast = s["cast"]
    changed = 0

    # 비밀 단서를 인물에 **1:1**로 배정한다. 겹치면 심문이 한 사람에게 몰린다.
    taken, owned = set(), {}
    for c in cast:
        cl, _ = _secret_clue(c, s, taken)
        owned[c["id"]] = cl
        if cl:
            taken.add(cl.get("id"))

    # 짝지을 단서가 없는 인물에게는 **단서를 만들어 준다.**
    #   지어내는 것이 아니라, 이미 있는 것(제 방의 자취 + 제 비밀)을
    #   플레이어가 탐색으로 찾을 수 있는 자리에 놓는 것이다.
    #   이게 없으면 그 인물은 단서로 추궁당할 방법이 아예 없다.
    exist = {cl.get("id") for cl in s["clue_graph"]}
    seq = 1
    for c in cast:
        if owned[c["id"]]:
            continue
        pl = next((p for p in s["map"]["places"] if p.get("owner") == c["id"]), None)
        while f"X{seq}" in exist:
            seq += 1
        feats = (pl or {}).get("features") or []
        trace = feats[0] if feats else f"{c['name']}의 자취"
        cl = {"id": f"X{seq}", "channel": "location", "medium": "탐색",
              "location": (pl or {}).get("id"),
              "surface": f"{(pl or {}).get('name', '그 방')}에서 나온 {trace} — "
                         f"{(c.get('secret') or {}).get('text','')}",
              "implies": f"{c['name']}에게 감춘 사정이 있다",
              "weight": "secret", "points_to": None, "exculpates": [],
              "reveal_round": 2, "decisive": False}
        s["clue_graph"].append(cl)
        exist.add(cl["id"])
        owned[c["id"]] = cl

    for i, c in enumerate(cast):
        cl = owned[c["id"]]
        own_place = next((p["id"] for p in s["map"]["places"] if p.get("owner") == c["id"]), None)
        pp = (c.get("pressure_points") or [{}])[0]
        bid = f"B{i+1}"
        pname = next((p["name"] for p in s["map"]["places"] if p["id"] == own_place), "제 방")
        # ★ 소지품은 **전원**이 갖는다. 하나도 없으면 그 인물은 끝까지 버틸 수 있고,
        #   실제 플레이에서 판이 멈추는 원인이 바로 그것이었다.
        if cl:
            item_name = _item_name(cl.get("surface"), pname,
                                   (c.get("secret") or {}).get("type", ""))
            reveals = cl.get("surface", "")
        else:
            feats = next((p.get("features") or [] for p in s["map"]["places"]
                          if p["id"] == own_place), [])
            item_name = _item_name(feats[0] if feats else "", pname,
                                   (c.get("secret") or {}).get("type", ""))
            reveals = f"{pname}에서 나온 {item_name} — {(c.get('secret') or {}).get('text','')}"
        c["belongings"] = [{
            "id": bid, "name": item_name, "reveals": reveals,
            "obtainable_by": [f"탐색:{pname}", f"심문:{(pp.get('trigger') or ['비밀'])[0]}"],
            "combines_with": None,
        }]
        forced = [x for x in [(cl or {}).get("id"), bid] if x]
        c["secrets"] = [{
            "text": (c.get("secret") or {}).get("text", ""),
            "type": (c.get("secret") or {}).get("type", ""),
            "hidden_from": _hidden_from(c, s),
            "points_if_kept": 1,
            "forced_by": forced,
            "confession_line": pp.get("reveals", ""),
            "note": "이것은 사정의 비밀이지 범행 자백이 아니다.",
        }]
        c["objectives"] = _objectives(c, s)
        changed += 1

    # 두 물증이 만나야 완성되는 조합 — 범인의 것과, 말이 가장 많이 겹치는 남의 것
    cul = next((c for c in cast if c.get("is_culprit")), None)
    if cul and cul.get("belongings"):
        mine = cul["belongings"][0]
        others = [(c, b) for c in cast if c["id"] != cul["id"] for b in (c.get("belongings") or [])]
        if others:
            oc, ob = max(others, key=lambda t: _overlap(mine["reveals"], t[1]["reveals"]))
            mine["combines_with"] = ob["id"]
            ob["combines_with"] = mine["id"]

    # 이중 사건 — 절도성 비밀이 있으면 별건으로 세운다
    thief = next((c for c in cast
                  if not c.get("is_culprit") and THEFT.search((c.get("secret") or {}).get("text", ""))), None)
    murder_clue = next((cl for cl in s["clue_graph"] if cl.get("channel") == "crime_scene"), None)
    thief_clue = owned.get(thief["id"]) if thief else None
    if thief and murder_clue and thief_clue:
        s["incidents"] = [
            {"id": "I1", "type": "murder", "culprit": cul["id"] if cul else None,
             "desc": f"{s['victim']['name']}의 죽음"},
            {"id": "I2", "type": "theft", "culprit": thief["id"],
             "desc": (thief.get("secret") or {}).get("text", "")},
        ]
        murder_clue["incident"] = "I1"
        thief_clue["incident"] = "I2"

    s["timeline_events"] = _timeline(s)
    _cross(s, owned)
    s["place_layers"] = _layers(s)
    s["visuals"] = _visuals(s)
    s["events"] = _events(s)

    nsec = sum(len(c.get("secrets") or []) for c in cast)
    s["scoring"] = {"culprit_correct": 5, "wrong_accusation_penalty": 2, "secret_revealed_each": 1,
                    "max": 5 + nsec, "note": "범인 지목 5점 + 비밀 1개당 1점"}
    s["disclosure_rule"] = {
        "applies_to": "secrets_only",
        "note": "정곡을 찔리거나 증거가 나오면 **비밀은** 실토한다. 범행 자백은 여기 해당하지 않는다.",
        "triggers": [
            {"kind": "pressure_point", "desc": "비밀의 트리거 낱말이 질문에 정확히 들어왔을 때"},
            {"kind": "evidence_shown", "desc": "forced_by에 적힌 단서·소지품을 손에 쥐고 들이댔을 때"},
        ],
    }
    s["phases"] = _phases(s)
    s["ending"] = _ending(s, s["scoring"]["max"])
    # ★라운드당 행동 예산 (2026-08-25 실험으로 12 → 8).
    #   전에는 12였는데 실측 사용률이 42%라 자원 제약이 없었고,
    #   그래서 "다 해 보면 언제나 확신에 이르는" 판이 됐다(정공법 50/50 만점).
    #   50편 스윕 결과 8이 균형점 — 적중 86% / 확신 76%.
    #   ★탐색과 심문이 **같은 주머니**를 쓴다. 대질(1회 토큰)·감식은 예산 밖.
    s.setdefault("config", {})["turns_per_round"] = 8
    s["config"]["action_budget"] = {
        "per_round": 8,
        "shared_by": ["search", "interrogate"],
        "cost": {"search": 1, "interrogate": 1},
        "outside_budget": {
            "confront": "한 판 1회 토큰(이벤트 해금 뒤). 예산 안에 두면 영영 안 쓰인다",
            "inspect": "이미 찾은 것을 더 보는 파생 행동",
            "combine": "수첩에서 생각하는 일 — 행동이 아니다",
        },
        "note": "'방을 더 뒤질까, 사람을 더 팔까'가 이 예산 위에서 결정된다.",
    }
    s["_schema"] = 2
    return changed


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/13_푸른수염.json"
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        n = upgrade(s)
        if n:
            json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  {p.split('/')[-1]:26} {'v2로 올림 — 인물 '+str(n)+'명' if n else '이미 v2'}")
