# -*- coding: utf-8 -*-
"""
story_narration.py — 게임 **전 구간**에 나레이션을 넣는다.

■ 왜 만들었나 (찬열이형 지시, 2026-08-24)
    "novel에 자세히 써져 있는 것처럼 앞에 인트로 부분 나레이션도 몰입감 넘치게 해야 되는데
     스키마에는 없더라. 라운드 전환, 용의자 공개, 엔딩 등등에서 나레이션이 나와야 하는
     부분이 있으면 novel 내용 참고해서 다 잘 넣어 줘야 프론트엔드랑 연동이 잘되지"

    그동안 나레이션은 **오프닝(intro.narration 9비트)과 엔딩 진상(reveal_sequence 6박)**
    두 군데만 있었다. 그 사이의 화면들 — 사건 공개, 현장 진입, 피해자 카드, 용의자 공개,
    라운드 시작/종료, 중반 이벤트, 지목 직전, 등급 엔딩 — 은 UI 문구만 있고
    **이야기를 이어 주는 목소리가 없었다.** 그래서 게임 중반이 건조했다.

    novel(바이블)에는 그 내용이 이미 다 글로 적혀 있다 — 인물의 인생, 라운드별 단서의 결,
    중반 이벤트, 등급별 엔딩. 이 스크립트는 **같은 재료로 나레이션 대사를 지어**
    스키마 `ui.story_narration`에 넣는다. 프론트는 화면마다 여기서 대사를 꺼내 쓰면 된다.

■ 넣는 자리 (화면 → 키)
    case_open      사건 공개        · 1개
    crime_scene    현장 진입        · 1개
    victim_card    피해자 카드      · 1개
    suspect_intro  용의자 공개      · 인물 수만큼(5개)
    round_start    라운드 시작      · 라운드 수만큼
    round_end      라운드 종료      · 라운드 수만큼
    event          중반 이벤트      · 이벤트가 걸린 라운드
    accuse         지목 직전        · 1개
    ending         등급 엔딩        · 등급 수만큼(4개)

사용:
    python story_narration.py                    # 전 편
    python story_narration.py out/38_*.json      # 한 편
    python story_narration.py --check            # 개수만 점검
"""
import json, glob, re, sys

from ui import _j, _je          # 조사 도우미 재사용


# ── 문장 도구 ─────────────────────────────────────────────────────────
def _sent(text, n=2, cap=170):
    """긴 산문에서 앞 n문장만 뽑아 낭독 길이로 자른다."""
    x = re.sub(r"\s+", " ", str(text or "")).strip()
    if not x:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", x)
    out = " ".join(parts[:n]).strip()
    if len(out) > cap:
        cut = out[:cap]
        k = max(cut.rfind("."), cut.rfind("—"), cut.rfind(","))
        out = (cut[:k + 1] if k > cap * 0.55 else cut).rstrip(" ,—") + "…"
    return out


def _dur(text):
    """낭독 길이(초). 초당 5.2자."""
    return max(3, min(16, round(len(str(text)) / 5.2)))


def _beat(text, mood, prosody, shot="", **kw):
    text = re.sub(r"\s+", " ", str(text)).strip()
    d = {"text": text, "mood": mood, "prosody": prosody,
         "duration_sec": _dur(text)}
    if shot:
        d["shot"] = shot
    d.update(kw)
    return d


# 라운드 초점별 나레이션 결 — hud.copy.round_focus와 짝을 맞춘다
_ROUND_VOICE = [
    ("동선", "누가 어디에 있었는가. 그것부터 묻는다.",
     "차분하게, 판을 펴듯", "낮고 또렷하게. 서두르지 않는다"),
    ("관계", "사람과 사람 사이에는 셈이 있다. 그 셈을 들춘다.",
     "조금 낮게, 의심을 심듯", "말끝을 살짝 눌러 여운을 남긴다"),
    ("비밀", "이제 감춘 것을 묻는다. 아픈 데를 찌를 시간이다.",
     "긴장을 올려", "속도를 조금 올리고, 자음을 세게"),
    ("확인", "남은 것은 맞춰 보는 일뿐이다.",
     "단단하게 조이며", "한 마디씩 끊어 못을 박듯"),
]


# 라운드 종료 — 라운드마다 다른 말을 한다(같은 문장을 되풀이하면 기계로 읽힌다)
# ★나레이터는 **추리를 대신 해 주지 않는다** (2026-08-25).
#   전에는 "같은 시각에 두 사람이 서로 다른 말을 하고 있다"처럼 이번 라운드에서
#   무엇이 어긋났는지를 짚어 줬다. 그건 플레이어가 찾아야 할 것이고, 화면에
#   그대로 뜨면 힌트가 된다. 이제는 **밤이 흘러가는 결**만 말한다.
#   그리고 플레이어에게 지시하지도 않는다("적어 두어라" 같은 말).
_ROUND_END = [
    "첫 번째 밤이 지나간다. 다섯 사람은 저마다의 자리로 돌아갔다.",
    "밤이 더 깊어졌다. 복도의 불이 하나씩 꺼진다.",
    "말이 줄었다. 이제 누구도 먼저 입을 열지 않는다.",
    "창밖이 희끄무레해진다. 남은 시간이 많지 않다.",
]



# 중반 이벤트 꼬리말 — 종류마다 다른 말을 붙인다 (2026-08-25)
_EV_TAIL = {
    "새증언":   "감추려던 쪽은 아직 그 사실을 모른다.",
    "두번째사건": "한 번은 우연이라 하겠으나, 두 번은 그렇지 않다.",
    "인물이탈":  "돌아온 얼굴이 나갈 때와 같지 않다.",
    "외부개입":  "바깥의 시간이 이 방으로 밀고 들어온다.",
    "증거소실":  "없어진 것을 아쉬워할 사람은 하나뿐이다.",
    "자백번복":  "한 번 흔들린 말은 다시 서지 않는다.",
}

_ADNOM = re.compile(r"(은|는|ㄴ|린|던|을|ㄹ|한|된)$")     # 관형형 어미 — 명사가 아니다


def _dedup_intro(nm, pub, life):
    """용의자 공개에서 **같은 말을 두 번 하지 않게** 한다 (2026-08-25).

    화면에는 `{이름}. {공개 신분}. {인생 앞머리}` 세 토막이 이어 붙는다.
    그런데 public과 bio는 출처가 달라도 같은 사실을 적어 둔 자리가 많다 —

        서민재. 부회장 — 응용통계학과, 별명 '민재일호'. …
        서민재은 응용통계학과의 ESTJ로, …          ← 이름·학과가 두 번째

    91편 다섯 명 전원, 그리고 인물 카드가 촘촘한 편일수록 심하다.
    ① 앞머리 주어가 **바로 그 이름**이면 뗀다(다른 이름이면 두는 게 맞다 —
       38편은 공개 호칭이 '재투성이'고 본명이 '엘라'다).
    ② public에 이미 나온 낱말이 `X의` 꼴로 또 나오면 그 낱말만 뺀다.
    ③ 조사를 달고 있는 낱말이 겹칠 때는 **앞의 수식어로 조사를 옮긴다.**
       단 앞말이 관형형이면(…시달린 아우로) 손대지 않는다 — 문장이 깨진다.
    ④ `별명은 X —` 꼴은 유래 설명이 뒤따르므로 `그 별명은`으로 바꿔 살린다.
    안전장치: 손본 결과가 너무 짧아지면 원문을 그대로 쓴다.
    """
    x = (life or "").strip()
    if not x:
        return x
    orig = x
    known = {w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", pub or "")}
    if not known:
        return x

    # ① 이름 주어
    x = re.sub(rf"^{re.escape(nm)}\s*(은|는|이|가)\s+", "", x)

    # ④ 별명 되풀이 — 줄표 뒤에 유래가 이어질 때만 '그 별명은'으로 살린다.
    #    쉼표면 뒤는 별개의 사실이므로 통째로 뗀다("별명은 연우사마, 자칭 성격은…").
    #    앞 쉼표는 **되돌려 놓는다** — 삼키면 'ESFP로그 별명은'처럼 붙어 버린다.
    def _nick(m):
        lead = m.group(1) or ""
        if m.group(2) not in known:
            return m.group(0)
        return f"{lead} 그 별명은 " if m.group(3) == "—" else lead
    x = re.sub(r"(,?)\s*별명은?\s*'?([^\s,'—]+)'?\s*(—|,)\s*", _nick, x, count=1)

    # ② 관형격 되풀이
    x = re.sub(r"([가-힣A-Za-z0-9]{2,})의\s+",
               lambda m: "" if m.group(1) in known else m.group(0), x, count=2)

    # ③ 조사를 단 낱말이 겹칠 때 — 앞 수식어로 조사를 옮긴다
    #    조사를 옮길 때는 **받침에 맞춰 다시 고른다** — '막내'+'으로'는 틀린 말이다.
    _PAIR = {"으로": ("으로", "로"), "로": ("으로", "로"), "은": ("은", "는"),
             "는": ("은", "는"), "이다": ("이다", "다"), "다": ("이다", "다")}

    def _carry(m):
        prev, word, josa = m.group(1), m.group(2), m.group(3)
        if word not in known or _ADNOM.search(prev):
            return m.group(0)
        ch = prev[-1]
        has = "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28
        a, b = _PAIR.get(josa, (josa, josa))
        return f"{prev}{a if has else b},"
    #    ★낱말은 **최소로** 잡는다. 욕심내면 '운영부장으'+'로'로 잘려 겹침을 놓친다.
    x = re.sub(r"([가-힣A-Za-z0-9]{2,})\s+([가-힣]{2,}?)(으로|로|이다|다|은|는),", _carry, x, count=1)

    # 앞머리가 `…로,`로 시작해 주어를 잃었으면 한 문장으로 끊어 준다
    #   ★단, 그 앞머리가 **public에 이미 나온 말**이면 통째로 뗀다 (2026-08-26).
    #     '러닝 복장으로 온 진취적 ESTP. ESTP다.'처럼 같은 낱말을 두 번 읽었다.
    def _close(m):
        head = m.group(1).rstrip()
        if head in known or any(w in known for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", head)):
            return ""
        ch = head[-1]
        pat = "이다. " if ("가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28) else "다. "
        return head + pat
    x = re.sub(r"^([가-힣A-Za-z0-9 ']{2,20}?)(으로|로),\s*", _close, x)
    x = re.sub(r"\s{2,}", " ", x).strip(" ,—")

    if len(x) < max(15, len(orig) * 0.35):
        return orig
    return x


_NUM = {2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱", 8: "여덟"}


def _num(n):
    """사람을 셀 때는 고유어로 — "5사람"이 아니라 "다섯 사람"."""
    return _NUM.get(n, str(n))


def _bare(name):
    """장소 이름에서 괄호 설명을 뗀다 — 낭독에 괄호가 들어가면 읽히지 않는다."""
    return re.sub(r"\s*[(（][^)）]*[)）]", "", str(name or "")).strip()


def _where(s):
    """이 밤이 벌어진 **공간의 이름**.

    ★2026-08-25 — 나레이션 틀에 "이 집 안에", "성은 그 밤의 일을 삼킨 채"처럼
      저택·성을 전제한 말이 박혀 있었다. 50편 가운데 현대 대학 도서관도 있고
      커피집도 있는데 전부 '집'과 '성'으로 불렸다(전 편 251건).
      배경을 가리지 않으려면 **그 편의 현장 이름**을 쓰면 된다.
    """
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    return _bare(pn.get((s.get("death") or {}).get("place"), "")) or "그 자리"


def _spoiler_words(c):
    """이 인물의 비밀·살해동기에서 '흘리면 안 되는 낱말'을 뽑는다."""
    blob = " ".join([
        ((c.get("secret") or {}).get("text") or ""),
        ((c.get("secret") or {}).get("type") or ""),
        (c.get("kill_motive") or ""),
        (c.get("motive_label") or ""),
    ])
    return {w for w in re.findall(r"[가-힣]{3,}", blob)}, blob


def _safe_intro(c, cap=165):
    """용의자 공개 나레이션 본문 — **비밀이 든 문장은 통째로 뺀다.**

    life_story는 바이블용이라 인물의 비밀까지 적혀 있다. 그대로 앞 두 문장을
    가져다 쓰면 공개 나레이션에서 비밀이 새어 게임이 끝난다(실제로 6편에서 샜다).
    비밀·동기의 낱말이 겹치는 문장은 건너뛰고, 안전한 문장만 골라 잇는다.
    """
    words, blob = _spoiler_words(c)
    src = str(c.get("life_story") or c.get("bio") or "")
    src = re.sub(r"\s+", " ", src).strip()
    picked = []
    for sent in re.split(r"(?<=[.!?])\s+", src):
        if not sent.strip():
            continue
        hits = sum(1 for w in words if w in sent)
        leak = hits >= 2 or any(blob[i:i + 8] and blob[i:i + 8] in sent
                                for i in range(0, max(0, len(blob) - 8), 4))
        if leak:
            continue
        picked.append(sent.strip())
        if len(" ".join(picked)) >= cap or len(picked) >= 2:
            break
    out = " ".join(picked).strip()
    if len(out) > cap:
        cut = out[:cap]
        k = max(cut.rfind("."), cut.rfind("—"), cut.rfind(","))
        out = (cut[:k + 1] if k > cap * 0.55 else cut).rstrip(" ,—") + "…"
    return out


def build(s):
    cast = s["cast"]
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    d = s["death"]
    vic = s["victim"]
    vname = vic["name"]
    place = pn.get(d["place"], "")
    rounds = int(s["config"].get("rounds", 3))
    bg = (s.get("background") or {})
    atmo = bg.get("atmosphere", "")
    intro = s.get("intro") or {}
    ui = s.get("ui") or {}
    focus_list = ((ui.get("hud") or {}).get("copy") or {}).get("round_focus") or []
    clues = s["clue_graph"]

    out = {
        "note": "게임 전 구간의 나레이션 대사. 오프닝(ui.narration)과 엔딩 진상"
                "(ui.reveal_sequence) 사이를 메운다. 화면마다 여기서 대사를 꺼내 쓴다.",
        "narrator": (ui.get("narration") or {}).get("narrator")
                    or {"role": "이야기를 들려주는 사람 — 등장인물이 아니다"},
        "usage": "프론트: 화면 진입 시 해당 키의 text를 나레이터 음성으로 낭독하고, "
                 "자막은 mood에 맞춰 띄운다. skippable=false인 것은 건너뛰지 않는다.",
    }

    # ① 사건 공개 ─────────────────────────────────────────────────
    out["case_open"] = _beat(
        f"{_sent(atmo, 1, 120)} "
        f"이 밤에 한 사람이 죽었다. 그리고 그 자리에 있던 {_num(len(cast))} 사람은, "
        f"저마다 그 밤에 대해 할 말이 있다.",
        mood="무겁게 문을 여는", prosody="느리게. 첫 문장 뒤 한 박 쉰다",
        shot="사건 제목이 도장 찍히듯 떠오르는 검은 화면",
        skippable=False)

    # ② 현장 진입 ─────────────────────────────────────────────────
    first_insp = next((x for x in (d.get("scene_inspection") or [])), "")
    first_insp = re.sub(r"^【[^】]*】\s*", "", first_insp)   # 머리표(【검안】)는 낭독에서 뗀다
    scene_desc = _sent(d.get("scene_description"), 2, 150)
    # 50편 중 20편은 scene_description이 장소 이름으로 시작한다 — 앞에 또 붙이면
    # "뒤뜰 마구간 곁. 뒤뜰 마구간 곁. …"이 된다.
    #    ★장소 이름이 설명 안에 이미 들어 있으면 앞에 또 붙이지 않는다.
    #      "세미나실(중도 6층). 불 켜진 세미나실. …"이 됐다.
    _pb = _bare(place)
    head = "" if (scene_desc.startswith(place) or _pb and _pb in scene_desc[:40]) else f"{place}. "
    out["crime_scene"] = _beat(
        f"{head}{scene_desc} {first_insp}",
        mood="서늘하게", prosody="낮게 깔고, 검안 대목에서 또박또박",
        shot="현장 전경 → 증거 목록으로 시선 이동",
        skippable=True)

    # ③ 피해자 카드 ───────────────────────────────────────────────
    out["victim_card"] = _beat(
        f"죽은 이는 {vname}. {vic.get('role','')}. "
        f"{_sent(vic.get('bio'), 2, 160)}",
        mood="담담하게, 그러나 안타깝게",
        prosody="이름을 부를 때 한 박 쉰다",
        shot="피해자 초상 → 신분·발견 장소·사인 4칸",
        skippable=True)

    # ④ 용의자 공개 ───────────────────────────────────────────────
    #    novel의 '인물' 절과 같은 재료(공개 신분 + 인생 앞머리)를 쓴다.
    #    ★비밀·동기는 절대 넣지 않는다 — 여기서 흘리면 게임이 끝난다.
    intro_map = {}
    for c in cast:
        nm = c["name"]
        pub = c.get("public") or (c.get("profile") or {}).get("status") or ""
        life = _dedup_intro(nm, pub, _safe_intro(c, 165))
        intro_map[c["id"]] = _beat(
            f"{nm}. {pub}. {life}",
            mood="인물마다 결을 달리해 — 이 사람의 처지가 묻어나게",
            prosody="이름을 먼저 또렷이, 그다음 낮춰서",
            shot=f"{nm}의 초상 카드가 앞으로 나온다",
            cast_id=c["id"], name=nm,
            spoiler_ban="비밀·살해 동기·알리바이의 참거짓은 절대 말하지 않는다",
            skippable=True)
    out["suspect_intro"] = intro_map

    # ⑤ 라운드 시작/종료 ──────────────────────────────────────────
    starts, ends = {}, {}
    for r in range(1, rounds + 1):
        key, line, mood, pros = _ROUND_VOICE[min(r - 1, len(_ROUND_VOICE) - 1)]
        focus = focus_list[r - 1] if r - 1 < len(focus_list) else key
        opened = [c for c in clues if c.get("reveal_round") == r]
        n_new = len(opened)
        #    라운드마다 다른 머리말 — 전에는 2라운드부터 전부 "밤이 깊어 간다."였다
        head = ["이제 묻기 시작한다.", "밤이 깊어 간다.",
                "자정을 넘겼다.", "창밖이 희끄무레하다."][min(r - 1, 3)]
        starts[str(r)] = _beat(
            f"{r}라운드. {head} {line}"
            + (f" 이번 라운드에 새로 드러나는 것이 {n_new}가지 있다." if n_new else ""),
            mood=mood, prosody=pros,
            shot=f"{r}라운드 배너 — {focus}",
            focus=focus, new_clues=n_new, skippable=True)

        if r < rounds:
            tail = _ROUND_END[min(r - 1, len(_ROUND_END) - 1)]
            ends[str(r)] = _beat(
                f"{r}라운드가 끝났다. {tail}",
                mood="한 박 쉬어 가며", prosody="느리게, 정리하듯",
                shot="라운드 정리 화면", skippable=True)
        else:
            ends[str(r)] = _beat(
                f"마지막 라운드가 끝났다. 더 물을 수 없다. "
                f"이제 이 밤의 이름을 대야 할 때다.",
                mood="조이며", prosody="한 마디씩 끊어",
                shot="지목 화면으로 넘어가기 직전", skippable=False)
    out["round_start"] = starts
    out["round_end"] = ends

    # ⑥ 중반 이벤트 ───────────────────────────────────────────────
    evmap = {}
    for e in (s.get("events") or []):
        r = e.get("round")
        if r is None:
            continue
        # ★꼬리말을 **이벤트 종류에 맞춰** 붙인다 (2026-08-25).
        #   여섯 종류 전부에 "판이 뒤집힌다. 지금까지 세운 셈을 다시 세워야 한다"를
        #   붙여 두었더니, 무슨 일이 났는지와 무관한 상투구가 됐다.
        tail = _EV_TAIL.get(e.get("kind"), "이 밤의 결이 한 번 꺾인다.")
        evmap[str(r)] = _beat(
            f"그런데 — {_sent(e.get('text'), 2, 150)} {tail}",
            mood="갑자기 조이는", prosody="'그런데'에서 뚝 끊고 한 박 쉰 뒤 빠르게",
            shot="이벤트 연출 — 화면이 한 번 흔들린다",
            event_kind=e.get("kind", ""), event_name=e.get("name", ""), skippable=False)
    out["event"] = evmap

    # ⑦ 지목 직전 ─────────────────────────────────────────────────
    out["accuse"] = _beat(
        f"다섯 사람이 앞에 서 있다. 그중 하나가 {vname}{_j(vname,'을/를')} 죽였고, "
        f"지금도 아무 일 없다는 얼굴을 하고 있다. "
        f"이름을 대라. 한 번 댄 이름은 되돌릴 수 없다.",
        mood="가장 무겁게", prosody="아주 느리게. 마지막 문장은 못을 박듯",
        shot="용의자 5인이 나란히 선 화면", skippable=False)

    # ⑧ 등급 엔딩 ─────────────────────────────────────────────────
    grades = {}
    for g in ((s.get("ending") or {}).get("grades") or []):
        nm = g.get("name", "")
        grades[nm] = _beat(
            f"{g.get('text','')}",
            mood={"미궁": "가라앉으며", "절반의 진실": "씁쓸하게",
                  "밝혀진 밤": "차분하게", "완전한 해명": "맑게 풀리며"}.get(nm, "차분하게"),
            prosody="여운을 길게. 마지막 음을 흘린다",
            shot="등급 이름 → 엔딩 글 → 점수 내역",
            grade=nm, min_score=g.get("min", 0), skippable=True)
    out["ending"] = grades

    return out


def enrich(path, check=False):
    s = json.load(open(path, encoding="utf-8"))
    sn = build(s)
    n = (4 + len(sn["suspect_intro"]) + len(sn["round_start"]) + len(sn["round_end"])
         + len(sn["event"]) + len(sn["ending"]))
    if not check:
        s.setdefault("ui", {})["story_narration"] = sn
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    tot = sum(b["duration_sec"] for b in _walk(sn))
    print(f"  {path.split('/')[-1][:28]:30s} 나레이션 {n:2}개 · 총 {tot}초")
    return n


def _walk(sn):
    for k, v in sn.items():
        if isinstance(v, dict) and "text" in v:
            yield v
        elif isinstance(v, dict):
            for x in v.values():
                if isinstance(x, dict) and "text" in x:
                    yield x


if __name__ == "__main__":
    check = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    tot = 0
    for f in files:
        tot += enrich(f, check)
    print(f"\n{len(files)}편 · 나레이션 총 {tot}개")
