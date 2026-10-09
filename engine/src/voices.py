# -*- coding: utf-8 -*-
"""
voices.py — 인물마다 **기계적으로 구별되는 말투**를 준다.

왜 필요한가
  13편 다섯 인물의 말투 지시는 이랬다.
      조심스러운 존댓말 / 단정한 하오체 / 정중한 하오체 / 낮고 단호한 하오체 / 수다스러운 하오체
  넷이 하오체다. 앞에 붙은 형용사('단정한', '정중한', '낮고 단호한')는
  **문장에 흔적을 남기지 않는다.** 그래서 다섯 사람이 전부 "…하오", "…소"로 끝나고
  누가 말했는지 구별이 안 된다.

  형용사로는 안 된다. 모델이 실제로 따를 수 있는 것은
  **종결어미·자칭·호칭·버릇** 같은 눈에 보이는 표지뿐이다.

무엇을 주는가 (한 인물에 다섯 가지)
  ① 말체    종결어미 체계 자체 — 합쇼체 / 하오체 / 하게체 / 해요체 / 소인체 / 해라체
  ② 자칭    나·내 / 저·제 / 소인 / 이 몸
  ③ 호칭    심문관을 뭐라 부르는가 — 나리 / 어르신 / 판관님 …
  ④ 버릇    문장을 끊는지 잇는지, 곱씹는지, 말끝을 흐리는지 (되묻기는 금지 — 물음표 금지 규칙)
  ⑤ 금지    이 인물이 절대 쓰지 않는 말투

★ **본보기 대사는 주지 않는다.** 네 번 당했다 — 예문을 넣으면 그대로 베낀다.
  주는 것은 어미 목록과 규칙뿐이고, 문장은 모델이 짓는다.

사용:
    python voices.py "scenarios/[0-9]*.json"       # 전편에 말투 배정
    python voices.py --check                 # 배정이 서로 구별되는지 검사
"""
import json, glob, sys, re

# ── 말체 — 종결어미 체계가 서로 다른 것들만 모았다 ────────────────────
KITS_OLD = [
    dict(key="하게체", desc="윗사람이 아랫사람에게 쓰는 점잖은 말",
         endings=["-네", "-하게", "-인가", "-겠나"], self=["나", "내"],
         ban="'-습니다', '-요'로 끝내지 마라"),
    dict(key="하오체", desc="대등하게 높이는 말",
         endings=["-하오", "-소", "-구려", "-오이다"], self=["나", "내"],
         ban="'-습니다', '-네', '-요'로 끝내지 마라"),
    dict(key="합쇼체", desc="가장 깍듯이 높이는 말",
         endings=["-습니다", "-습니까", "-옵니다"], self=["저", "제"],
         ban="'-하오', '-네', '-다'로 끝내지 마라"),
    dict(key="해요체", desc="부드럽게 높이는 말",
         endings=["-어요", "-예요", "-지요", "-까요"], self=["저", "제"],
         ban="'-하오', '-습니다', '-네'로 끝내지 마라"),
    dict(key="소인체", desc="아랫것이 상전에게 몸을 낮추는 말",
         endings=["-옵니다", "-이옵니까", "-습지요"], self=["소인", "쇤네"],
         ban="'나', '내'라고 자칭하지 마라. '-하오', '-네'로 끝내지 마라"),
    dict(key="올시다체", desc="장사치·떠돌이가 예스럽게 차리는 말 — 하오체에 '올시다'를 섞는다",
         endings=["-올시다", "-이올시다", "-하오", "-소"], self=["저", "제"],
         ban="'-하오', '-네', '-요'로 끝내지 마라"),
    dict(key="노라체", desc="중·무당처럼 세속 밖에 선 이의 예스러운 말",
         endings=["-노라", "-로다", "-니라", "-거늘"], self=["나", "이 몸"],
         ban="'-습니다', '-요', '-하오'로 끝내지 마라"),
]
# 서양 고전(유럽 동화·그리스 신화) — **번역투**로 간다.
#   '소인', '쇤네', '나리', '올시다'는 조선 신분제의 말이다.
#   중세 유럽 성에 그 말이 들어가면 그 순간 이야기가 깨진다.
#   대신 번역 소설에서 쓰이는 결로 어미만 갈라 놓는다.
KITS_WEST = [
    dict(key="격식체", desc="깍듯하게 차리는 말",
         endings=["-습니다", "-습니까", "-입니다"], self=["저", "제"],
         ban="'-하오', '-네', 반말로 끝내지 마라"),
    dict(key="정중체", desc="번역 소설의 점잖은 말",
         endings=["-하오", "-소", "-소이다"], self=["나", "내"],
         ban="'-습니다', '-요'로 끝내지 마라"),
    dict(key="탄식체", desc="한숨이 섞인 예스러운 말 — 정중체와 어미는 닮았으나 결이 무겁다",
         endings=["-구려", "-더이다", "-오이다", "-하오"], self=["이 사람", "나"],
         ban="'-습니다', '-요', '-네'로 끝내지 마라"),
    dict(key="다정체", desc="부드럽고 젊은 말",
         endings=["-어요", "-예요", "-죠"], self=["저", "제"],
         ban="'-하오', '-습니다', '-네'로 끝내지 마라"),
    dict(key="노숙체", desc="나이 든 이의 예스러운 말",
         endings=["-네", "-로군", "-는가", "-일세"], self=["나", "내"],
         ban="'-습니다', '-요'로 끝내지 마라"),
    dict(key="공손체", desc="차분히 풀어 설명하는 말",
         endings=["-답니다", "-지요"], self=["저", "제"],
         ban="'-하오', '-네'로 끝내지 마라"),
    dict(key="완곡체", desc="놀라움과 여운이 묻어나는 말 — 단정하지 않는다",
         endings=["-군요", "-네요", "-더군요", "-는군요"], self=["저", "제"],
         ban="'-하오', '-소', '-습니다', '-네'로 끝내지 마라"),
]

KITS_NEW = [
    dict(key="합니다체", desc="딱딱한 격식체",
         endings=["-습니다", "-입니다", "-습니까"], self=["저", "제"],
         ban="'-요', 반말로 끝내지 마라"),
    dict(key="해요체", desc="부드러운 존댓말",
         endings=["-어요", "-예요", "-죠", "-까요"], self=["저", "제"],
         ban="'-습니다'로만 끝내지 마라"),
    dict(key="반존대", desc="존대와 반말이 섞이는 말",
         endings=["-요", "-지", "-거든", "-잖아요"], self=["나", "내"],
         ban="'-습니다'로 끝내지 마라"),
    dict(key="건조체", desc="군더더기 없이 끊는 말",
         endings=["-습니다", "-죠", "-니다"], self=["저"],
         ban="감탄사·군말을 붙이지 마라"),
    dict(key="노년체", desc="예스럽고 느린 말",
         endings=["-네", "-지", "-구먼", "-는가"], self=["나", "내"],
         ban="'-습니다', '-요'로 끝내지 마라"),
    dict(key="설명체", desc="겪은 일을 풀어 설명하는 말",
         endings=["-더라고요", "-네요", "-던데요"], self=["저", "제"],
         ban="'-습니다', 반말로 끝내지 마라"),
]

# 말체를 **무늬**로도 적어 둔다. '모릅니다'는 '-ㅂ니다'라 문자열 비교로는
# '-습니다'가 아니라고 잘못 잡힌다. 검사는 이 무늬로 한다.
ENDING_RE = {'하게체': '(네|하게|인가|겠나|일세|는가|던가|게나)$', '하오체': '(하오|오|소|구려|소이다|오이다)$', '합쇼체': '(니다|니까|옵니다)$', '해요체': '(요|죠|예요|어요|지요|까요|네요)$', '소인체': '(옵니다|옵니까|습지요|니다|니까)$', '올시다체': '(올시다|이올시다|올습니다|하오|오|소|지요)$', '노라체': '(노라|로다|니라|거늘|도다)$', '격식체': '(니다|니까)$',
 '탄식체': '(구려|더이다|오이다|로소이다|하오|오|소)$', '정중체': '(하오|오|소|소이다)$', '다정체': '(요|죠|예요|어요)$', '노숙체': '(네|로군|는가|일세|구먼|지)$', '공손체': '(답니다|지요|니다|소|오)$',
 '완곡체': '(군요|네요|더군요|는군요|군|네)$', '합니다체': '(니다|니까)$', '반존대': '(요|지|거든|잖아요|는데)$', '건조체': '(니다|죠)$', '노년체': '(네|지|구먼|는가)$'}

# ── 버릇 — 성격에서 뽑되, 서로 겹치지 않게 ────────────────────────────
# ★2026-08-25 — 표면 표지(말끝·조사)만 적혀 있어 프롬프트에 넣어도 문장에 안 드러났다.
#   **구조적 행동**(무엇을 먼저 말하는가, 얼마나 길게)을 함께 적는다.
#   stress_agent가 이 문장을 그대로 프롬프트에 넣는다 — 여기가 유일한 출처다.
HABITS = [
    "짧게 툭툭 끊는다. 한 답변이 두세 문장을 넘지 않고 군말·감정 수식을 붙이지 않는다. "
    "대신 마지막 한 문장에 뼈가 있다.",
    "해명이 길다. 묻지 않은 앞뒤 사정까지 이어 붙이며 결백한 이유를 시시콜콜 덧붙인다 — "
    "길어질수록 수상해 보인다는 걸 본인만 모른다.",
    "말끝을 자주 흐린다. '…'으로 문장을 맺고, 단정해야 할 자리에서 얼버무린다.",
    # ★ '되묻는 버릇'은 뺐다(2026-08-24). 심문 답변에서 물음표를 금지했는데
    #   이 버릇이 정면으로 어긋나, 인물이 자꾸 플레이어에게 되물었다.
    #   회피하는 느낌은 살리되 질문은 하지 않는 버릇으로 바꾼다.
    "상대가 쓴 낱말을 한 번 낮게 되뇐 뒤에야 답한다. 되묻지는 않는다 — 혼잣말이다.",
    "제 분야의 이치부터 꺼낸다. 무엇을 물어도 자기 일(직업·기술·살림)의 지식을 "
    "한 자락 깔고 나서 답한다 — 강의하듯, 그러나 짧게.",
    "감정이 먼저 나온다. 사실을 말하기 전에 억울함·분노·서러움이 한 문장 앞서고, "
    "그 다음에야 답이 나온다. 말이 빨라진다.",
    # ★ '감탄사가 앞에 붙는다'는 버릇은 뺐다. 두 번 재는 동안 그 버릇을 받은 인물이
    #   다섯 번 다 [감정] 줄을 통째로 빠뜨렸다. 버릇이 출력 계약을 깨서는 안 된다.
    "말을 아끼고 재다가 답한다. 확실한 것만 조심스럽게 말하고, "
    "애매한 것은 '…까지는 모르겠습니다'로 선을 긋는다. 남 얘기는 특히 아낀다.",
    "말이 빨라 조사를 자주 생략한다. 문장이 성글고 토막처럼 떨어진다.",
]

# ── 심문관을 뭐라 부르는가 — 신분에 따라 다르다 ──────────────────────
def _address(c, reg):
    """심문관을 뭐라 부르는가 — 배경에 맞는 말이어야 한다."""
    st = ((c.get("profile") or {}).get("status") or c.get("public") or "")
    low = any(w in st for w in ["몸종", "비복", "하녀", "하인", "노비", "머슴",
                                "마름", "종", "심부름", "무당"])
    high = any(w in st for w in ["토호", "부자", "영주", "성주", "양반", "진사", "상궁",
                                 "주인", "장로", "왕", "귀족"])
    if reg == "modern":
        return "수사관님" if low else "형사님"
    if reg == "west":
        # 서양 고전에는 '나리'가 없다. 직함으로 부른다.
        return "재판관님" if not high else "재판관"
    return "나리" if low else ("판관" if high else "어르신")


def _register(s):
    """말투 계열을 고른다 — east(한국·동아시아 고전) / west(서양 고전) / modern(근현대).

    ★ 이걸 안 나누면 중세 유럽 하녀가 '쇤네'라고 말한다."""
    blob = ((s.get("meta") or {}).get("era") or "") + " " + \
           json.dumps((s.get("background") or {}).get("setting_raw") or {}, ensure_ascii=False)
    # ★ 순서가 중요하다. '19세기 유럽'은 '근대'라는 말 때문에 현대로 새기 쉽다.
    #   서양인지부터 보고, 그다음에 한국 근현대인지 본다.
    if any(w in blob for w in ["유럽", "서구", "그리스", "독일", "북유럽", "중세",
                               "왕국", "성채", "북구"]):
        return "west"
    if any(w in blob for w in ["현대", "2020", "2010", "1920", "스타트업",
                               "사무실", "회사", "오피스", "경성"]):
        return "modern"
    return "east"


def _rank(c):
    """신분 등급. 높을수록 낮춰 말할 자격이 있다."""
    p = c.get("profile") or {}
    st = (p.get("status") or "") + " " + (c.get("public") or "") + " " + (p.get("relation") or "")
    if any(w in st for w in ["비복", "몸종", "하녀", "하인", "노비", "머슴", "종년", "심부름"]):
        return 0
    if any(w in st for w in ["마름", "집사", "관리인", "사환", "행수", "청지기"]):
        return 1
    if any(w in st for w in ["승려", "탁발", "무당", "박수", "도사", "중",
                             "마녀", "사제", "여사제", "점쟁이"]):
        return 3          # 세속 밖 — 등급이 아니라 결이 다르다
    if any(w in st for w in ["손님", "떠도는", "객주", "상인", "장사", "나그네", "손"]):
        return 2
    if any(w in st for w in ["토호", "부자", "영주", "성주", "주인", "장로", "대감",
                             "좌수", "제조", "양반", "진사", "유지",
                             "왕", "왕비", "공주", "시장", "읍장", "귀족", "사제", "신관"]):
        return 5
    return 4              # 집안 사람(아내·딸·조카 등)


def _prefer(c, reg):
    """이 인물에게 어울리는 말체를 **순서대로** 고른다."""
    p = c.get("profile") or {}
    r = _rank(c)
    young = any(x in (p.get("age") or "") for x in ["10대", "20대", "30대"])
    female = (p.get("sex") or "") == "여"
    elder = any(x in (p.get("age") or "") for x in ["40대", "50대", "60대", "70대"])
    if reg == "modern":
        if r <= 1:   return ["해요체", "설명체", "합니다체", "건조체"]
        if elder:    return ["노년체", "건조체", "합니다체"]
        if young and female: return ["해요체", "반존대", "설명체", "합니다체"]
        return ["합니다체", "건조체", "설명체", "반존대", "해요체"]
    if reg == "west":
        # 아랫사람은 나이가 많아도 낮춰 말할 자격이 없다. 집사가 '-일세'라고 하면
        # 모델이 그 어긋남을 스스로 고치려다 하오체로 샌다(실제로 그랬다).
        if r <= 1:   return ["격식체", "공손체", "다정체"]
        if elder:    return ["노숙체", "정중체", "격식체", "공손체"]
        if r == 3:   return ["탄식체", "공손체", "정중체"]
        if young and female: return ["다정체", "공손체", "정중체"]
        if r >= 5:   return ["정중체", "노숙체", "격식체", "탄식체"]
        return ["정중체", "탄식체", "공손체", "격식체", "다정체"]
    if r == 0:       return ["소인체", "합쇼체", "해요체"]
    if r == 1:       return ["합쇼체", "소인체", "올시다체"]
    if r == 3:       return ["노라체", "올시다체", "하오체"]        # 승려·무당
    if r == 2:       return ["올시다체", "하오체", "합쇼체"]        # 손님·장사치
    if r == 5:
        # 상전이라도 젊은 여성은 하게체를 쓰지 않는다
        return (["하오체", "해요체"] if (young and female) else
                ["하게체", "하오체"] if elder or not female else ["하오체", "하게체"])
    # 집안 사람
    if young and female: return ["해요체", "하오체", "올시다체"]
    return ["하오체", "합쇼체", "올시다체"]


def detect(c):
    """이 인물이 **이미 쓰고 있는** 말체를 알아본다.

    ★ 시나리오는 손으로 쓰인 대사를 갖고 있다(알리바이·실토 대사).
      말체를 새로 배정해 놓고 그 대사를 그대로 두면,
      카드가 "합쇼체로 말하라" 해놓고 바로 아래 '…두었소'를 보여 주는 꼴이 된다.
      모델은 눈앞의 문장을 베낀다. 그래서 **있는 것을 먼저 읽는다.**"""
    lines = [c.get("alibi_narration", "")]
    for sec in (c.get("secrets") or []):
        lines.append(sec.get("confession_line", ""))
    for pp in (c.get("pressure_points") or []):
        lines.append(pp.get("reveals", ""))
    per = c.get("persona") or {}
    lines += [per.get("example_line", "")] + list(per.get("example_lines") or [])
    hit = {}
    for ln in [x for x in lines if x and len(x) > 8]:
        for sent in re.split(r"(?<=[.?!…])\s+", ln):
            sent = sent.strip(" .?!…\"”'’」』")
            if not sent:
                continue
            for form, rx in ENDING_RE.items():
                if re.search(rx, sent):
                    hit[form] = hit.get(form, 0) + 1
    return hit


def assign(s):
    """한 시나리오 안에서 **서로 다른 말체**가 되도록 배정한다."""
    reg = _register(s)
    kits = {k["key"]: k for k in
            (KITS_OLD if reg == "east" else KITS_WEST if reg == "west" else KITS_NEW)}
    cast = s["cast"]
    # 신분이 뚜렷한 사람부터 골라야 어울리는 말체를 먼저 가져간다
    order = sorted(range(len(cast)),
                   key=lambda i: (-abs(_rank(cast[i]) - 2), cast[i]["id"]))
    HAO_FAMILY = {"하오체", "정중체", "탄식체", "올시다체", "공손체"}
    taken, out = set(), {}
    # ① 이미 쓰고 있는 말체를 먼저 존중한다. 손으로 쓴 대사를 살리는 길이다.
    # 아랫사람이 쓸 수 없는 '내려 말하는' 말체. 이미 그렇게 쓰여 있어도 지켜 주지 않는다.
    DOWNWARD = {"하게체", "노숙체", "노년체", "노라체"}
    keep = {}
    for c in cast:
        h = detect(c)
        low = _rank(c) <= 1
        cand = [f for f, n in sorted(h.items(), key=lambda x: -x[1])
                if f in kits and n >= 2 and not (low and f in DOWNWARD)]
        if cand and cand[0] in HAO_FAMILY and len(taken & HAO_FAMILY) >= 2:
            cand = [f for f in cand if f not in HAO_FAMILY]
        if cand and cand[0] not in taken:
            keep[c["id"]] = cand[0]
            taken.add(cand[0])
    for i in order:
        c = cast[i]
        if c["id"] in keep:
            out[c["id"]] = kits[keep[c["id"]]]
            continue
        DOWN0 = {"하게체", "노숙체", "노년체", "노라체"}
        ok_down = (_rank(c) >= 5
                   or any(x in ((c.get("profile") or {}).get("age") or "")
                          for x in ["50대", "60대", "70대"]))
        hao_n = len(taken & HAO_FAMILY)
        pick = next((k for k in _prefer(c, reg)
                     if k in kits and k not in taken
                     and (ok_down or k not in DOWN0)
                     and not (hao_n >= 2 and k in HAO_FAMILY)), None)
        if not pick:
            # ★ '내려 말하는' 말체(하게체·노숙체·노년체·노라체)는 아랫사람이 쓸 수 없다.
            #   30대 떠돌이가 판관에게 '-일세'라고 하면 어색하고, 모델이 스스로 고치려다
            #   딴 말체로 샌다. 남은 것 중에서도 자격 없는 사람에게는 주지 않는다.
            DOWN = {"하게체", "노숙체", "노년체", "노라체"}
            hi = (_rank(c) >= 5
                  or any(x in ((c.get("profile") or {}).get("age") or "")
                         for x in ["50대", "60대", "70대"]))
            hao_n = len(taken & HAO_FAMILY)
            rest = [k for k in kits if k not in taken and (hi or k not in DOWN)
                    and not (hao_n >= 2 and k in HAO_FAMILY)] \
                or [k for k in kits if k not in taken and (hi or k not in DOWN)]
            pick = rest[0] if rest else next(k for k in kits if k not in taken)
        taken.add(pick)
        out[c["id"]] = kits[pick]

    # 버릇도 겹치지 않게 — 성격 글자수로 갈라 결정적으로 고른다
    for n, c in enumerate(cast):
        kit = out[c["id"]]
        per = (c.get("persona") or {}).get("personality") or ""
        h = HABITS[(len(per) + n * 3) % len(HABITS)]
        j = 0
        used = {(x.get("persona") or {}).get("habit") for x in cast[:n]}
        while h in used and j < len(HABITS):
            h = HABITS[(HABITS.index(h) + 1) % len(HABITS)]
            j += 1
        p = c.setdefault("persona", {})
        p["voice"] = {
            "form": kit["key"],
            "form_desc": kit["desc"],
            "endings": kit["endings"],
            "self": kit["self"],
            "address": _address(c, reg),
            "habit": h,
            "ban": OTHER_BAN.get(kit["key"], kit["ban"]) + "로 끝내지 마라",
            "ending_re": ENDING_RE.get(kit["key"], ""),
        }
        p["habit"] = h
        # 같은 어미 계열이 둘이면 **자칭**이라도 달라야 구별된다
        same = [x for x in cast[:n]
                if ((x.get("persona") or {}).get("voice") or {}).get("form") in HAO_FAMILY]
        if kit["key"] in HAO_FAMILY and same:
            used_self = {tuple(((x.get("persona") or {}).get("voice") or {}).get("self") or [])
                         for x in same}
            if tuple(kit["self"]) in used_self:
                alt = ["저", "제"] if kit["self"][0] in ("나", "내") else ["나", "내"]
                p["voice"]["self"] = alt
        # 옛 필드도 함께 갱신 — 카드 다른 곳에서 쓰인다
        p["speech_style"] = f"{kit['key']} ({kit['desc']})"
    return len(cast)


# 말체마다 **버려야 할 남의 어미**를 못 박는다.
#   노숙체 금지가 "'-습니다','-요' 쓰지 마라"뿐이라 모델이 하오체로 샜다.
#   막지 않은 길이 있으면 반드시 그리로 간다.
OTHER_BAN = {
    "하게체": "'-습니다' '-요' '-하오' '-소' '-구려' '-옵니다'",
    "하오체": "'-습니다' '-네' '-요' '-옵니다' '-답니다'",
    "합쇼체": "'-하오' '-소' '-네' '-요' '-구려'",
    "해요체": "'-하오' '-소' '-습니다' '-네' '-구려'",
    "소인체": "'-하오' '-소' '-네' '-요' — 자칭도 '나/내' 금지",
    "올시다체": "'-습니다' '-네' '-요'",
    "노라체": "'-습니다' '-요' '-하오' '-소' '-네'",
    "격식체": "'-하오' '-소' '-구려' '-네' '-요' '-옵니다'",
    "정중체": "'-습니다' '-요' '-네' '-답니다' '-구려'",
    "탄식체": "'-습니다' '-요' '-네'",
    "다정체": "'-하오' '-소' '-습니다' '-네' '-구려'",
    "노숙체": "'-습니다' '-요' '-하오' '-소' '-구려' '-답니다'",
    "공손체": "'-네' '-구려' '-요'",
    "완곡체": "'-하오' '-소' '-습니다' '-답니다'",
    "합니다체": "'-요' '-네' '-지' 반말",
    "반존대": "'-습니다' '-네'",
    "건조체": "'-요' '-네' 감탄사",
    "노년체": "'-습니다' '-요' '-하오' '-소'",
    "설명체": "'-습니다' 반말 '-네'",
}


def block(c):
    """카드에 넣을 말투 규격. **본보기 문장은 주지 않는다.**"""
    v = (c.get("persona") or {}).get("voice")
    if not v:
        return ""
    return "\n".join([
        f"[말투 — 이것이 너를 다른 사람과 구별한다. 한 문장도 어기지 마라]",
        f"· 말체: **{v['form']}** ({v['form_desc']})",
        f"· 문장은 반드시 이 어미로 끝낸다: {' / '.join(v['endings'])}",
        f"· 자기를 부를 때: **{' · '.join(v['self'])}**",
        f"· 심문하는 이를 부를 때: **{v['address']}**",
        f"· 버릇: {v['habit']}",
        f"· 금지: {v['ban']}",
        f"· 다른 인물의 말체를 흉내 내지 마라. 흔들리면 그 인물이 아니게 된다.",
    ])


# ── 검사 — 한 판 안에서 말투가 정말 갈리는가 ─────────────────────────
# 배경에 어울리지 않는 낱말 — 이게 섞이면 그 순간 이야기가 깨진다
WRONG_WORDS = {
    "west": ["쇤네", "소인", "올시다", "사또", "대감", "마님", "옵니다",
             r"(?<!재)판관", r"(?<![가-힣])나리"],
    "modern": ["쇤네", "소인", "올시다", "하오", "구려", "노라", "사또",
               r"(?<![가-힣])나리"],
    "east": [],
}


def check(s):
    cast = s["cast"]
    forms = [((c.get("persona") or {}).get("voice") or {}).get("form") for c in cast]
    habits = [((c.get("persona") or {}).get("voice") or {}).get("habit") for c in cast]
    bad = []
    if None in forms:
        bad.append(f"말투가 없는 인물 {[c['id'] for c,f in zip(cast,forms) if not f]}")
    if len(set(forms)) < len(forms):
        dup = [f for f in set(forms) if forms.count(f) > 1]
        bad.append(f"같은 말체를 쓰는 인물이 있다: {dup}")
    if len(set(habits)) < len(habits):
        bad.append("같은 버릇을 가진 인물이 있다")
    # 배경에 안 맞는 말이 섞였는가
    reg = _register(s)
    for c in cast:
        v = (c.get("persona") or {}).get("voice") or {}
        # ★ 금지어 목록에는 '-옵니다', '-하오'가 **쓰지 말라는 뜻으로** 적혀 있다.
        #   그걸 배경 위반으로 세면 온 편이 실패한다. 실제로 쓰는 항목만 본다.
        blob = json.dumps({k: v.get(k) for k in ("form", "form_desc", "endings",
                                                 "self", "address", "habit")},
                          ensure_ascii=False)
        hit = [w for w in WRONG_WORDS.get(reg, []) if re.search(w, blob)]
        if hit:
            bad.append(f"{c['name']}: {reg} 배경에 안 맞는 말 {hit}")
    return (not bad), bad


if __name__ == "__main__":
    if "--check" in sys.argv:
        for p in sorted(glob.glob("scenarios/[0-9]*.json")):
            s = json.load(open(p, encoding="utf-8"))
            ok, bad = check(s)
            if not ok:
                print(f"  ❌ {p.split('/')[-1]:26} {'; '.join(bad)}")
        print("말투 검사 끝")
        sys.exit(0)
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        n = assign(s)
        json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        forms = " / ".join(f"{c['name']}:{c['persona']['voice']['form']}" for c in s["cast"])
        print(f"  {p.split('/')[-1]:26} {forms}")
