# -*- coding: utf-8 -*-
"""
relate.py — 인물의 **관계와 서사를 시나리오 사실에서 파생**해 실질 있게 쓴다.

왜 필요한가
  기존 enrich_agents.py는 이렇게 썼다.
      "서한동(곳간과 소작을 맡은 마름). 옹서방을 둘러싸고 각자의 사정으로 얽힌 사이."
  참고할 사실이 한 줄도 없으니, 심문에서 "서한동은 왜 자네를 해치려 하나?"라고 물으면
  모델이 지어낸다 — "서한동은 내 소작을 맡고 있어, 내가 그를 의심받을까 두려워하오."
  문장이 성립하지 않는다. 모델 탓이 아니라 카드 탓이다.

무엇을 넣는가 (전부 시나리오 안에 이미 있는 사실)
  ① 정체    상대의 공개 신분·profile.relation
  ② 내력    내 life_story/bio 중 그 사람 이름이 나오는 문장 (손으로 쓴 사실이 있으면 최우선)
  ③ 그 밤   시간대별 동선 대조 — 같은 자리에 있었나, 언제부터 안 보였나
  ④ 아는 것 1라운드 공개 단서 중 그 사람을 가리키는 것
  ⑤ 감추는 것  내 비밀 중 hidden_from에 그가 든 것
  ⑥ 모르는 것  ★ 가장 중요. 지어내지 않고 "모르오"라고 말할 근거를 준다.

⑥이 없으면 모델은 빈칸을 상상으로 메운다. 관계 서술은 반드시 모름으로 끝난다.

사용:
    python relate.py out/23_옹고집.json          # 한 편
    python relate.py "scenarios/[0-9]*.json"           # 전편
    python relate.py "scenarios/*.json" --force        # 기존 서술도 덮어씀(손으로 쓴 것 보존은 --keep)
"""
import json, glob, sys, re, difflib

# ── 조사 ─────────────────────────────────────────────────────────────
def _j(w, pair="을/를"):
    a, b = pair.split("/")
    if not w:
        return b
    ch = w[-1]
    if not ("가" <= ch <= "힣"):
        return b
    jong = (ord(ch) - 0xAC00) % 28
    if pair == "으로/로":            # ㄹ 받침은 '로'를 쓴다 — '막내딸로'
        return b if jong in (0, 8) else a
    return a if jong else b


def _sentences(text):
    if not text:
        return []
    return [t.strip() for t in re.split(r"(?<=[.?!])\s+", text) if t.strip()]


# ── ② 내력: 손으로 쓴 서사에서 그 사람 이야기를 찾아온다 ───────────────
def _history(a, b, s):
    """A의 life_story/bio 중 B를 **이름으로** 언급한 문장.
    손으로 쓴 사실이라 가장 값지다. 다만 A 자신을 설명하는 문장이 상대 신분을
    스치듯 담은 경우(예: '벨은 몰락한 상인의 막내딸로…')를 걸러야 한다."""
    keys = [b["name"]]
    rel = (b.get("profile") or {}).get("relation")
    if rel and len(rel) >= 3:
        keys.append(rel)
    found = []
    for src in (a.get("life_story"), a.get("bio")):
        for sent in _sentences(src):
            if a["name"] in sent:              # A 자신을 설명하는 문장은 관계가 아니다
                continue
            if any(k and k in sent for k in keys) and sent not in found:
                found.append(sent)
        if found:
            break
    return " ".join(found[:2])


def _v(a, b, n):
    """짝마다 문장 짜임을 달리 고르는 번호. 사실이 비슷해도 글이 붙지 않게 한다."""
    return (sum(ord(x) for x in (a["id"] + b["id"])) + len(b["name"])) % n


_STAND = ["내게는 {r}{j} 되는 사람", "여기서 {r} 자리에 있는 사람", "{r}. 그 자리로 얼굴을 익혔다"]
_LOOK = ["겉으로 보아 {p}", "{p}. 남들도 그리 본다", "{p} — 적어도 겉은 그렇다"]


def _standing(a, b, s):
    """내력이 없을 때 — 상대의 **겉보기 됨됨이**로 적는다.
    persona.personality는 인물마다 다르므로, 서술이 서로 붙어 버리는 것을 막는다."""
    br = (b.get("profile") or {}).get("relation") or ""
    per = (b.get("persona") or {}).get("personality") or ""
    st = (b.get("profile") or {}).get("status") or ""
    bits = []
    if br:
        bits.append(_STAND[_v(a, b, 3)].format(r=br, j=_j(br, "이/가")))
    elif st:
        bits.append(f"{st}")
    if per:
        bits.append(_LOOK[_v(a, b, 3)].format(p=per.rstrip(".")))
    if not bits:
        ap = a.get("public") or ""
        return f"이 일로 얼굴을 마주해 온 사이다{'. 나는 ' + ap + _j(ap,'으로/로') + ' 엮여 있다' if ap else ''}."
    return ". ".join(bits) + "."


# ★ 남의 대사를 **따옴표째** 실으면 그 말투를 베낀다.
#   합쇼체 인물의 카드에 하오체 문장이 넷 실려 있었고, 그 인물이 하오체로 흘렀다.
#   그래서 **간접화법**으로 바꾼다 — 정보는 그대로, 말투는 지운다.
_PLAIN = [("았소", "았다"), ("었소", "었다"), ("였소", "였다"), ("겠소", "겠다"),
          ("하오", "한다"), ("이오", "이다"), ("소이다", "다"), ("올시다", "이다"),
          ("구려", "다"), ("구먼", "다"), ("군요", "다"), ("답니다", "다"),
          ("습니다", "다"), ("입니다", "이다"), ("어요", "었다"), ("예요", "이다"),
          ("지요", "다"), ("네요", "다"), ("더이다", "었다"), ("노라", "았다"),
          ("옵니다", "다"), ("습지요", "다"), ("이었네", "이었다"), ("었네", "었다"),
          ("썼소", "썼다"), ("갔소", "갔다"), ("왔소", "왔다"), ("봤소", "봤다"),
          ("했소", "했다"), ("줬소", "줬다"), ("놨소", "놨다"), ("샀소", "샀다"),
          ("있소", "있다"), ("없소", "없다"), ("좋소", "좋다"), ("모르오", "모른다"),
          ("아니오", "아니다"), ("마시오", "말라"), ("보시오", "보라"), ("잤소", "잤다"), ("컸소", "컸다"), ("떴소", "떴다"), ("쳤소", "쳤다"), ("섰소", "섰다")]


def _indirect(text):
    """남의 말을 **말투 없이** 옮긴다. 따옴표를 없애고 평서형으로 접는다."""
    t_ = (text or "").strip().strip('“”"\'')
    out = []
    for sent in re.split(r"(?<=[.?!])\s+", t_):
        sent = sent.strip().rstrip(".?! ")
        if not sent:
            continue
        for a, b in _PLAIN:
            if sent.endswith(a):
                sent = sent[: -len(a)] + b
                break
        # 자칭도 3인칭으로
        sent = re.sub(r"(^|[\s“'])(나는|내가|저는|제가)([\s,])", r"\1그는\3", sent)
        out.append(sent)
    return ". ".join(out)


_SAY = ["그가 사람들 앞에서 하는 말은 이렇다 — {t}.",
        "그는 이렇게 말하고 다닌다 — {t}.",
        "묻는 사람마다 같은 대답을 들었을 것이다 — {t}."]


def _claims(b, a=None):
    """그가 사람들 앞에서 하는 말 — 공개 진술이라 카드에 적어도 정보 누설이 아니다.
    인물마다 다르므로 서술이 구별된다."""
    al = (b.get("alibi_narration") or "").strip().rstrip(".")
    if not al:
        line = ((b.get("persona") or {}).get("example_line") or "").strip().rstrip(".")
        if not line or len(line) < 8:
            return ""
        return f"그가 입버릇처럼 하는 말 — {_indirect(line)}."
    al = _indirect(al)
    if len(al) > 70:
        al = al[:68] + "…"
    return _SAY[_v(a, b, 3) if a else 0].format(t=al)


# ── ③ 그 밤: 동선 대조 ────────────────────────────────────────────────
def _that_night(a, b, s, pd):
    slots = s.get("time_slots") or []
    at, bt = a.get("timeline") or {}, b.get("timeline") or {}
    dslot = (s.get("death") or {}).get("time_slot")
    together, apart_after = [], None
    for sl in slots:
        pa, pb = at.get(sl), bt.get(sl)
        if pa and pa == pb:
            together.append((sl, pd.get(pa, {}).get("name", pa)))
        elif together and apart_after is None:
            apart_after = sl
    out = []
    if together:
        seg = ", ".join(f"{sl}엔 {nm}" for sl, nm in together)
        out.append(f"그 밤 {seg}에 같이 있었다")
        if apart_after:
            out.append(f"{apart_after}부터는 따로였고, 그 뒤 그가 어디 있었는지는 내 눈으로 보지 못했다")
        else:
            out.append("그 밤 내내 서로 눈에 띄는 자리였다")
    else:
        mine = pd.get(at.get(dslot), {}).get("name")
        if mine:
            out.append([f"{dslot}에 나는 {mine}에 있었고, 그는 내 눈에 띄지 않았다",
                        f"그 밤 내가 {mine}{_j(mine,'을/를')} 뜨지 않는 동안 그를 본 사람은 내가 아니다",
                        f"{mine}에 있던 나로서는 {dslot}의 그를 보지 못했다"][_v(a, b, 3)])
        else:
            out.append("그 밤 그와 마주친 기억이 없다")
    return ". ".join(out) + "."


# ── ④ 공개된 사실 중 그를 가리키는 것 ─────────────────────────────────
def _public_note(b, s):
    ks, weak = [], []
    for k in (s.get("clue_graph") or []):
        if k.get("reveal_round", 1) != 1:
            continue
        surf = k.get("surface") or ""
        if not (b["name"] and b["name"] in surf):
            continue
        # 증언 단서는 _claims와 겹치고 문장이 어색하다 — 뒤로 미룬다
        (weak if k.get("channel") in ("testimony", "witness") else ks).append(surf)
    ks = ks or weak
    if not ks:
        return ""
    t = ks[0]
    t = _indirect(re.sub(r"^[^:：]{0,20}[:：]\s*", "", t))   # '누가 말한다:' 머리를 뗀다
    t = t if len(t) <= 60 else t[:58] + "…"
    return f"처음부터 드러나 있던 일 — {t}"


# ── ⑤ 그 앞에서 특히 감춰야 하는 것 ──────────────────────────────────
def _hide_from(a, b):
    outs = []
    for sec in (a.get("secrets") or []):
        if b["id"] in (sec.get("hidden_from") or []):
            tx = sec.get("text", "")
            outs.append(tx if len(tx) <= 40 else tx[:38] + "…")
    if not outs:
        return ""
    tail = outs[-1]
    return ("이 사람 앞에서는 " + " / ".join(outs) +
            _j(tail, "을/를") + " 특히 감춰야 한다")


# ── ⑥ 모르는 것 (반드시 들어간다) ────────────────────────────────────
def _unknown(a, b, s, pd):
    """★ 이 대목이 없으면 모델은 빈칸을 상상으로 메운다.
    '모르오'라고 말할 근거를 인물마다 다르게 준다."""
    dslot = (s.get("death") or {}).get("time_slot")
    dplace = (s.get("death") or {}).get("place")
    bt = (b.get("timeline") or {})
    at = (a.get("timeline") or {})
    bp = pd.get(bt.get(dslot), {}).get("name")
    ap = pd.get(at.get(dslot), {}).get("name")
    q = []
    if bt.get(dslot) == dplace and at.get(dslot) != dplace:
        q.append(f"그가 {dslot}에 어째서 {bp}에 있었는지")
    elif bp and bp != ap:
        q.append(f"그가 {dslot} 내내 {bp}에 있었다는 말이 참인지")
    else:
        q.append("그가 내 눈을 피해 무엇을 했는지")
    if b.get("secrets") or (b.get("secret") or {}).get("text"):
        q.append("감추는 것이 있다면 무엇인지")
    if b.get("belongings"):
        q.append(f"그가 지닌 것 가운데 내가 못 본 것이 있는지")
    return "내가 모르는 것 — " + ", ".join(q[:2])


# ── 피해자에 대한 서술 ────────────────────────────────────────────────
def _victim_rel(a, s, pd, web=None):
    v = s.get("victim") or {}
    vn = v.get("name", "피해자")
    bits = [f"{vn}({v.get('public') or v.get('role') or '망자'})"]
    hist = ""
    keys = [vn] + ([v.get("public")] if v.get("public") else [])
    for src in (a.get("life_story"), a.get("bio")):
        for sent in _sentences(src):
            if any(k and k in sent for k in keys):
                hist = sent
                break
        if hist:
            break
    if hist:
        bits.append(hist)
    km = a.get("kill_motive") or a.get("motive_label")
    if km:
        bits.append(f"내가 그를 두고 품은 마음 — {km}")
    vtie = (web or {}).get("V")               # 피해자와의 숨은 얽힘
    if vtie:
        bits.append(vtie[1].rstrip("."))
    dslot = (s.get("death") or {}).get("time_slot")
    dp = pd.get((s.get("death") or {}).get("place"), {}).get("name")
    mine = pd.get((a.get("timeline") or {}).get(dslot), {}).get("name")
    if dp and mine and dp != mine:
        bits.append(f"그가 {dp}에서 죽은 {dslot}에 나는 {mine}에 있었다")
    bits.append("내가 모르는 것 — 그가 마지막에 누구를 만났는지")
    return ". ".join(b.rstrip(".") for b in bits) + "."


_MEM = ["{p} 앞에서 마주친 적이 있다. 그는 {m}. 그 모습부터 눈에 들어오는 사람이다",
        "{p} 쪽을 지나며 몇 번 보았다. {m} — 그게 그 사람 버릇이다",
        "함께 있을 때면 그는 {m}. {p}에서도 그랬다"]


def _memory(a, b, s, pd):
    """둘만의 구체 기억 한 줄 — 상대의 자리와 버릇에서 짠다."""
    bp = None
    for pl in s["map"]["places"]:
        if pl.get("owner") == b["id"]:
            bp = pl["name"].split("(")[0]
            break
    # ★버릇의 출처는 **voices.py 하나**다 (2026-08-25).
    #   persona.mannerisms / persona.habit은 옛 필드라 지금은 비어 있고, 그때 쓴
    #   문장만 relationships에 굳어 남았다. 그래서 91편에서 반존대로 말하는
    #   인물을 두 사람이 나란히 "어려운 한자말을 즐겨 쓴다"고 소개했다 —
    #   모델이 지어낸 것이 아니라 카드에 그렇게 적혀 있었다.
    man = (((b.get("persona") or {}).get("voice") or {}).get("habit") or
           (b.get("persona") or {}).get("mannerisms") or
           (b.get("persona") or {}).get("habit") or "").strip().rstrip(".")
    man = man.split(".")[0].strip()          # 첫 마디만 — 길면 소개가 아니라 낭독이 된다
    # ★1인칭을 3인칭으로 바꾼다 (2026-08-25).
    #   "그는 **제** 분야의 이치부터 꺼낸다"라고 적어 두었더니, 유가람이 그 문장을
    #   자기 얘기로 읽고 "함께 있을 때면 제 분야의 이치부터 꺼내는 경우가 많았어요"
    #   라고 답했다. 남의 버릇이 화자의 버릇으로 둔갑한다. 250개 중 52개가 이 꼴이다.
    man = re.sub(r"(^|[^가-힣])제(?=\s)", r"\1자기", man)
    man = re.sub(r"(^|[^가-힣])내(?=\s)", r"\1자기", man)
    man = re.sub(r"(^|[^가-힣])나(?=[는가])", r"\1자기", man)
    if not bp or not man or len(man) < 4:
        return ""
    return _MEM[_v(a, b, 3)].format(p=bp, m=man)


# ── 조립 ─────────────────────────────────────────────────────────────
def build_rel(a, b, s, pd, web=None):
    pub = b.get("public") or (b.get("profile") or {}).get("relation") or ""
    head = f"{b['name']}({pub})" if pub and pub not in b["name"] and b["name"] not in pub else b["name"]
    parts = [head]
    hist = _history(a, b, s)
    parts.append(hist if hist else _standing(a, b, s))
    tie = (web or {}).get(b["id"])            # 두 사람만의 얽힘 — 서술을 갈라놓는 대목
    if tie:
        parts.append(tie[1].rstrip("."))
    mem = _memory(a, b, s, pd)
    if mem:
        parts.append(mem)
    parts.append(_that_night(a, b, s, pd))
    for extra in (_claims(b, a), _public_note(b, s), _hide_from(a, b)):
        if extra:
            parts.append(extra)
    parts.append(_unknown(a, b, s, pd))
    txt = ". ".join(p.rstrip(". ") for p in parts if p) + "."
    return re.sub(r"\.\.+", ".", txt)


# ── life_story 보강 ──────────────────────────────────────────────────
MIN_BIO = 250

# 인물마다 **글의 짜임 자체가 다르게** — 같은 틀에 낱말만 바꿔 끼우면
# 다섯 사람의 인생이 전부 같은 문장이 되어 카드가 헛돈다.
BIO_SHAPES = [
    "이 자리에 오기까지 오래 걸렸다. {role}. {motive} 그 일이 있고부터 {name}{josa_neun} 말수가 줄었다. "
    "누구에게도 하지 못한 말이 하나 있다 — {secret}. 들키면 여기서 끝이라는 걸 안다.",

    "{name}{josa_eun} 남들보다 눈치가 빠르다. {role}{josa_ro} 지내며 사람들의 낯빛을 읽는 데 익숙해졌다. "
    "그런 사람이 하필 제 일 하나는 감추지 못하고 있다 — {secret}. {motive} 그 말을 들은 날은 웃어 넘겼다.",

    "{role}. 여기 들어온 뒤로 크게 소리를 낸 적이 없다. {motive} 그때도 아무 말 하지 않았다. "
    "대신 속으로 셈을 했다. 감추고 있는 것이 있다 — {secret}. 그것 하나로 지금 자리가 무너진다.",

    "{name}{josa_eun} 셈에 밝다. {role}{josa_ro} 얻은 것보다 잃은 것을 더 오래 기억한다. "
    "{motive} 그 뒤로 사람을 믿지 않게 되었다. 아무도 모르는 일이 하나 있다 — {secret}.",

    "오래 눌려 지냈다. {role}. 처음엔 참을 만했고, 나중엔 참는 것이 습관이 되었다. "
    "{motive} 그 말이 마지막이었다고 생각한다. 감춘 일도 있다 — {secret}. 둘 다 입 밖에 낸 적이 없다.",
]


def life_seed(i, name, role, motive, secret):
    """인물 순번마다 다른 짜임으로 인생 서사의 뼈대를 만든다."""
    sh = BIO_SHAPES[i % len(BIO_SHAPES)]
    role = role or "이 일을 맡은 사람"
    return sh.format(name=name, role=role,
                     motive=(motive or "말 못 할 사정이 있었다").rstrip(".") + ".",
                     secret=(secret or "누구에게도 말하지 않은 일이 있다").rstrip("."),
                     josa_neun=_j(name, "은/는"), josa_eun=_j(name, "은/는"),
                     josa_ro=_j(role, "으로/로"))

def deepen_bio(c, s, pd):
    """짧은 life_story를 시나리오 사실로 늘린다. 지어내지 않고 있는 것만 엮는다."""
    cur = c.get("life_story") or c.get("bio") or ""
    # 같은 문장을 반복해 길이만 채운 것(mock 생성물)은 길이로 쳐 주지 않는다
    uniq, seen = [], set()
    for sent in _sentences(cur):
        if sent in seen:
            continue
        seen.add(sent)
        uniq.append(sent)
    cur = " ".join(uniq)
    if len(cur) >= MIN_BIO:
        return cur
    p = c.get("profile") or {}
    idx = next((i for i, x in enumerate(s["cast"]) if x["id"] == c["id"]), 0)
    seg = [cur.rstrip()] if cur else []
    sec = (c.get("secret") or {}).get("text")
    seg.append(life_seed(idx, c["name"], c.get("public") or p.get("status"),
                         c.get("kill_motive"), sec))
    if p.get("age") or p.get("sex"):
        seg.append(f"나이는 {p.get('age','')}, {p.get('sex','')}자다.".replace("  ", " "))
    per = (c.get("persona") or {}).get("personality")
    if per:
        seg.append(f"사람들은 그를 두고 {per.rstrip('.')}고들 한다.")
    slots = s.get("time_slots") or []
    tl = c.get("timeline") or {}
    walk = [f"{sl}엔 {pd.get(tl[sl],{}).get('name',tl[sl])}에 있었다" for sl in slots if tl.get(sl)]
    if walk:
        seg.append("그 밤의 행적은 이렇다. " + ", ".join(walk) + ".")
    if c.get("alibi_narration"):
        seg.append(f"묻는다면 이렇게 말할 것이다 — “{c['alibi_narration'].rstrip('.')}.”")
    for pp in (c.get("pressure_points") or [])[:1]:
        tg = ", ".join((pp.get("trigger") or [])[:3])
        if tg:
            seg.append(f"다만 {tg} 같은 말이 나오면 속이 서늘해진다.")
    out = " ".join(x for x in seg if x).strip()
    return out


# ── 실행 ─────────────────────────────────────────────────────────────
BOILER = "둘러싸고 각자의 사정으로 얽힌 사이"

def rewrite(s, force=False):
    cast = s["cast"]
    pd = {p["id"]: p for p in s["map"]["places"]}
    hand = s.get("_relationships") or {}          # 손으로 쓴 것은 언제나 우선
    try:
        import relweb
        if not s.get("relation_web"):
            s["relation_web"] = relweb.build_web(s)
    except Exception:
        relweb = None
    n = 0
    for a in cast:
        web = relweb.views_for(s, a["id"]) if relweb else {}
        rel = dict(a.get("relationships") or {})
        for b in cast:
            if b["id"] == a["id"]:
                continue
            cur = rel.get(b["id"], "")
            keep = cur and BOILER not in cur and len(cur) >= 45 and not force
            if keep:
                continue
            rel[b["id"]] = build_rel(a, b, s, pd, web)
            n += 1
        curv = rel.get("victim", "")
        if force or not curv or len(curv) < 45:
            rel["victim"] = _victim_rel(a, s, pd, web)
            n += 1
        if a["id"] in hand:                        # 손으로 쓴 서술로 덮는다
            rel.update(hand[a["id"]])
        # 관계가 아닌 메모(victim_secret 등)는 따로 뺀다 — 관계 자리에 두면 카드가 어그러진다
        ids = {x["id"] for x in cast}
        notes = {k: v for k, v in rel.items() if k not in ids and k != "victim"}
        if notes:
            a.setdefault("relationship_notes", {}).update(notes)
            rel = {k: v for k, v in rel.items() if k in ids or k == "victim"}
        a["relationships"] = rel
        nb = deepen_bio(a, s, pd)
        if nb and nb != a.get("life_story"):
            a["life_story"] = nb

    # 인생이 서로 붙어 버린 경우(같은 틀로 낱말만 갈아 끼운 시나리오)
    # 겹치는 무리를 통째로 골라, 각자 다른 짜임으로 **새로 쓴다**.
    # 앞에 덧붙이면 같은 말이 두 번 나와 더 나빠진다.
    dupes = set()
    for i in range(len(cast)):
        for k in range(i):
            if difflib.SequenceMatcher(None, cast[i].get("life_story") or "",
                                       cast[k].get("life_story") or "").ratio() >= 0.6:
                dupes.add(i); dupes.add(k)
    for i in sorted(dupes):
        c = cast[i]
        c["life_story"] = ""                      # 찍어 낸 틀을 버린다
        c["life_story"] = deepen_bio(c, s, pd)
        n += 1
    return n


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    force = "--force" in sys.argv
    arg = args[0] if args else "scenarios/[0-9]*.json"
    tot = 0
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        n = rewrite(s, force=force)
        json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        tot += n
        print(f"  {p.split('/')[-1]:28} 관계 {n}건 다시 씀")
    print(f"\n총 {tot}건")
