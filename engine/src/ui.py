# -*- coding: utf-8 -*-
"""
ui.py — 시나리오 JSON에 **화면(UI) 층**을 붙인다.

왜 필요한가
  지금 JSON에는 사건·인물·단서·음악이 다 들어 있다. 그런데 **화면에 실제로 뜨는 글자**가
  하나도 없다. 버튼에 뭐라고 쓸지, 조사했는데 아무것도 없을 때 뭐라고 보여 줄지,
  피해자 카드에 어떤 칸이 있는지 — 전부 만드는 사람 머릿속에만 있다.
  그러면 시나리오를 100편 뽑아도 화면은 한 편씩 손으로 만들어야 한다.

  음악도 같다. 지금 bgm은 '장면'별로는 있는데 **'화면'별로는 없다.**
  타이틀·세계관 입력·로딩·수첩·메모는 곡이 아예 없어서, 만드는 사람이
  아무 곡이나 돌려 쓰다 보니 "다 비슷하다"는 말이 나온다.

무엇을 붙이나 (전부 `ui` 아래)
  screens          화면 15종 — 화면마다 문구·요소·BGM·효과음
  narration        오프닝 나레이션 **전문** — 컷마다 그림 지시·BGM·효과음·길이·영상 여부
  reveal_sequence  엔딩 진상 나레이션 **전문** — 5비트(코난식 몰아치기)
  victim_card      피해자 카드 (신분/발견 장소/발견 시각/사인 — 사인은 가려 둔다)
  suspect_cards    용의자 카드 5장 (신분/나이/관계/알리바이 한 마디/초상 지시)
  clue_cards       단서 카드 전부 (종류/획득 장소/획득 방법/설명/목록 한 줄)
  place_screens    장소 조사 화면 — 라운드마다 선택지 4개와 **결과 문장까지**
  hud              상단 바·사건 개요 패널·하단 내비
  notebook         사건수첩 3탭 문구
  toasts           알림 문구
  audio            화면용 BGM(새로 만든 것) + UI 효과음 묶음

원작은 보호기간이 끝난 이야기이고, 여기 문구는 전부 우리가 쓴 것이다.

사용:
    python ui.py out/13_푸른수염.json
    python ui.py --all
    python ui.py --all --report
"""
import os, json, sys, os, re, glob, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")

# ── 조사 ──────────────────────────────────────────────────────────────
def _j(w, pair="을/를"):
    a, b = pair.split("/")
    if not w:
        return b
    ch = w.strip()[-1]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


def _je(w):
    """받침 있으면 '으로', 없으면 '로'"""
    if not w:
        return "로"
    ch = w.strip()[-1]
    if not ("가" <= ch <= "힣"):
        return "로"
    j = (ord(ch) - 0xAC00) % 28
    return "로" if j in (0, 8) else "으로"


# ── 짧은 물건 이름 뽑기 ───────────────────────────────────────────────
# 관형형(꾸미는 말)로 끝나는 토막 — 이름으로 쓰면 '나온', '밴' 같은 것이 나온다
_ADNOM = re.compile(r"(한|던|는|린|운|온|간|든|킨|인|친|밴|난|된|길|을|ㄹ)$")
_VERBISH = re.compile(r"(다|고|서|며|어|아|자|니|면)$")

# 눈에 보이는 물건 이름. 긴 것부터 맞춰 본다.
OBJ_WORDS = """
열쇠 꾸러미|출입기록|비밀 통로|밀실 통로|성경책|은식기|앞치마|물동이|약재|약병|독병|
칼집|검집|대검|장부|기록|유서|편지|서찰|쪽지|메모|열쇠|도면|지도|초상|액자|그림|
발자국|핏자국|혈흔|옷자락|저고리|두루마기|치마|버선|짚신|신발|봇짐|여장|채비|
찻잔|사발|그릇|항아리|단지|병|잔|촛대|촛농|등잔|호롱|
문갑|서랍|책장|궤짝|궤|함|화덕|아궁이|우물|
비녀|반지|가락지|목걸이|브로치|노리개|장신구|
자창|상처|시반|검험|주검|시신|
재물|엽전|은자|돈|셈|
발자취|먼지 자국|자국|흔적|자취|통로|사다리|밧줄|끈|
칼|검|낫|도끼|몽둥이|독|약|책|일기|문과 창|문|창|벽|
재고 장부|연습지|추포령|방문|도포|안섶|경대|바둑판|서책|궤짝|등롱|약탕기|장작|물기|
굿상|무구|향|놋그릇|이름표|서안|잔사|위 내용물|잔|탕기|약장|이불|베개|요강|
발자국|짚신 자국|바퀴 자국|핏방울|그을음|재|숯|기름|밧줄 자국|끈 자국|
호패|서찰|장계|첩지|명패|인장|도장|부적|염주|묵주|십자가|
""".replace("\n", "").strip("|").split("|")
OBJ_WORDS = [w for w in OBJ_WORDS if w]
OBJ_WORDS.sort(key=len, reverse=True)

_THIN = {"흔적", "자취", "것", "물건", "물건들", "셈", "자국", "터", "모습", "일", "쪽"}
# 가구·붙박이 — 들고 다니는 증거가 같은 문장에 있으면 그쪽을 먼저 쓴다
_FURNITURE = {"서안", "책장", "문갑", "서랍", "약장", "화덕", "아궁이", "우물", "궤짝", "궤",
              "함", "항아리", "단지", "벽", "문", "창", "문과 창", "경대", "이불", "베개"}


def _head(chunk):
    """관형형 수식을 떼고 **머리 명사**만 남긴다."""
    toks = [x for x in re.sub(r"[,·—–]", " ", str(chunk or "")).split() if x]
    if not toks:
        return ""
    cut = 0
    for i, t in enumerate(toks[:-1]):
        if _ADNOM.search(t) and not _VERBISH.search(t):
            cut = i + 1
    head = toks[cut:] or toks[-1:]
    if len(head) >= 2 and len(head[-1]) <= 3 and len(head[-2]) <= 3:
        return f"{head[-2]} {head[-1]}"
    return head[-1]


def _obj(phrase, fallback="방 안", bare=False):
    """문장에서 **화면에 올릴 만한 물건 이름**을 뽑는다."""
    t = re.sub(r"^\s*【[^】]*】\s*", "", str(phrase or ""))
    t = re.sub(r"[【】\[\]()“”‘’\"']", " ", t).strip()
    if not t:
        return fallback
    # ① 아는 물건 이름이 있으면 그것을 쓴다 (앞의 꾸밈말 한 개까지 붙인다)
    best = None
    for tier in (0, 1, 2):
        for w in OBJ_WORDS:
            rank = 2 if w in _THIN else (1 if w in _FURNITURE else 0)
            if rank != tier:
                continue
            i = t.find(w)
            if i < 0:
                continue
            if best is None or i < best[0]:
                best = (i, w)
        if best:
            break
    if best:
        i, w = best
        pre = t[:i].strip().split()
        mod = ""
        if pre:
            p = pre[-1]
            if 2 <= len(p) <= 5 and not _VERBISH.search(p) and not p.endswith(("이", "가", "를", "은", "는")):
                mod = p
        if bare:
            return w
        name = f"{mod} {w}".strip()
        return name if len(name) <= 12 else w
    # ② 없으면 머리 명사
    h = _head(re.split(r"(?<=[.?!])\s+", t)[0])
    if h in _THIN or not h:
        # 너무 밋밋하면 문장의 첫 명사 덩어리를 쓴다
        first = t.split()[0].rstrip("의이가은는을를에서")
        h = f"{first} {h}".strip() if first and h else (h or fallback)
    return h or fallback


def _nouns(text, limit=4):
    """장소 설명에서 **조사할 만한 물건**들을 뽑는다."""
    t = re.sub(r"[【】\[\]()]", " ", str(text or ""))
    out = []
    for w in OBJ_WORDS:
        # ★낱말 경계를 본다 (2026-08-25).
        #   그냥 `w in t`로 찾으면 **독서실의 '독'**, **문어의 '문'**,
        #   **창가의 '창'**이 물건으로 잡힌다. 그래서 현대 대학 복도에
        #   「독을 훑어본다」(항아리)라는 선택지가 생겼다.
        if (w not in out and w not in _THIN
                and re.search(r"(?<![가-힣])" + re.escape(w) + r"(?![가-힣])", t)):
            out.append(w)
        if len(out) >= limit:
            break
    # 설명에 '와/과'로 이어진 것도 줍는다
    for ch in re.split(r"[,·]|와 |과 ", t):
        h = _head(ch)
        if h and h not in out and h not in _THIN and 2 <= len(h) <= 7:
            out.append(h)
        if len(out) >= limit:
            break
    return out[:limit]


_HEARSAY = re.compile(r"(증언|소문|말|이야기|얘기|녹음)$")


def _clue_obj(cl):
    """이 단서가 **실제로 어디에 붙어 있는가**를 단서 문장에서 뽑는다.

    ★2026-08-25 — 예전에는 선택지 이름이 장소 features에서 나오고, 단서는
      **자리 번호로만** 붙었다. 그래서 「명패를 들여다본다」를 눌렀는데
      노트북 영상 파일이 나오는 일이 생겼다(91편 K10·S3·K9).
      선택지에 적힌 물건과 나오는 단서가 다르면 플레이어는 게임을 못 믿는다.
    """
    x = re.sub(r"^【[^】]*】\s*", "", str(cl.get("surface") or "")).strip()
    x = re.split(r"\s*[—:.,]\s*", x)[0].strip()
    if not x:
        return None
    w = x.split()
    # 뒤에서부터 잘라 오되, **연결 조사로 시작하는 토막**은 버린다.
    #   "…독서실 학생들 사이에 도는 말" → '사이에 도는 말'(×) → '도는 말'(○)
    #   "…주문 내역과 픽업대 CCTV"      → '내역과 픽업대 CCTV'(×) → '픽업대 CCTV'(○)
    _CONN = re.compile(r"(에서|에게|에|과|와|으로|로|부터|까지|보다)$")
    _ADN = re.compile(r"(린|던|한|된|온|난|간)$")     # 관형형 — 이름의 첫머리로 어색하다
    for n in (3, 2, 1):
        if len(w) < n:
            continue
        cand = " ".join(w[-n:]).strip("'\"“”「」")
        head = w[-n]
        if _CONN.search(head):
            continue
        if n == 3 and _ADN.search(head):
            continue
        if 2 <= len(cand) <= 16:
            return cand
    return None


VERBS = ["살펴본다", "조사한다", "들여다본다", "훑어본다", "뒤져 본다"]
VERBS_PAST = {"살펴본다": "살펴봤다", "조사한다": "조사했다", "들여다본다": "들여다봤다",
              "훑어본다": "훑어봤다", "뒤져 본다": "뒤져 봤다"}
CALM = ["흐트러진 데 없이 제자리에 있다.",
        "손댄 자국 없이 가지런하다.",
        "겉으로는 여느 때와 다르지 않다.",
        "먼지가 앉은 그대로다.",
        "눈에 걸리는 것이 없다."]
NOTHING = ["특별한 것은 발견되지 않았다.",
           "이렇다 할 것은 없다.",
           "여기서는 더 나올 것이 없어 보인다.",
           "지금은 걸리는 것이 없다."]
GENERIC = [("바닥", "살펴본다"), ("창가", "들여다본다"),
           ("문 언저리", "훑어본다"), ("방 전체", "둘러본다")]


def _anomaly(clue):
    """단서 문장에서 '그런데 …' 뒤에 붙일 어긋난 대목을 뽑는다."""
    t = re.sub(r"^\s*【[^】]*】\s*", "", str(clue.get("surface") or "")).strip()
    t = re.split(r"(?<=[.?!])\s+", t)[0]
    t = t.rstrip(".")
    # 남의 말을 옮긴 단서면 따옴표 안을 쓰지 않는다
    q = re.search(r"[‘“'\"]([^’”'\"]{6,60})", t)
    if q:
        return f"이런 말이 적혀 있다 — “{q.group(1).strip()}”"
    if not t:
        return "여느 때와 다른 것이 눈에 든다"
    if len(t) > 64:
        t = t[:62].rstrip() + "…"
    return t


_BADEND = re.compile(r"(다|소|요|오|네|까|라|지|군|구려|이다)\.?$")
_VAGUE = ("또 다른", "사람들 사이", "누군가", "떠도는", "같은 말")


def _clue_name(cl, place, kind):
    """단서 카드에 올릴 이름. 증언은 '누구의 말'로, 물건은 물건 이름으로."""
    surf = re.sub(r"^\s*【[^】]*】\s*", "", str(cl.get("surface") or "")).strip()
    if kind == "증언":
        head = surf.split(":")[0].strip() if ":" in surf[:40] else ""
        if head and not any(v in head for v in _VAGUE) and len(head) <= 12:
            who = re.sub(r"(이|가|은|는)?\s*(덧붙인다|말한다|증언한다|말)$", "", head).strip()
            return f"{who}의 진술"[:14] if who else "증언"
        if "소문" in surf[:20] or "도는 말" in surf[:20]:
            return "떠도는 소문"
        return "엇갈린 증언"
    tag = ""
    m = re.match(r"\s*【([^】]{1,12})】", str(cl.get("surface") or ""))
    if m:
        tag = m.group(1).strip()
    if tag and any(k in tag for k in ("검안", "검험", "감정", "부검")):
        return tag
    nm = _obj(surf, fallback="")
    nm = nm.rstrip(".").strip()
    if _BADEND.search(nm) or len(nm) < 2:
        nm = _pick_noun(surf) or tag or f"{place} {kind}".strip() or kind
    return nm


def _pick_noun(text):
    """조사가 붙은 낱말 가운데 앞쪽 것을 이름으로 쓴다 — 마지막 기댈 곳."""
    for m in re.finditer(r"([가-힣]{2,6})(이|가|을|를|은|는|에서|엔|의)\s", str(text or "")):
        w = m.group(1)
        if w in _THIN or _BADEND.search(w):
            continue
        return w
    for w in re.findall(r"[가-힣]{2,6}", str(text or "")):
        if w not in _THIN and not _BADEND.search(w):
            return w
    return ""


# ── 종류/획득 ─────────────────────────────────────────────────────────
KIND_BY_MEDIUM = {"검험서": "검험", "검안": "검험", "물건": "물증", "문서": "기록",
                  "장부": "기록", "편지": "기록", "말": "증언", "소문": "증언",
                  "증언": "증언", "기록": "기록"}
KIND_BY_CHANNEL = {"crime_scene": "현장", "location": "물증", "record": "기록",
                   "physical": "물증", "spine": "증언", "testimony": "증언"}


def _kind(cl):
    m = str(cl.get("medium") or "")
    for k, v in KIND_BY_MEDIUM.items():
        if k in m:
            return v
    return KIND_BY_CHANNEL.get(cl.get("channel"), "단서")


# ── UI 효과음 묶음 ────────────────────────────────────────────────────
def _sfx_lib(pal, title):
    """화면 조작용 효과음. bgm.event_cues(사건용)와 겹치지 않는 것만 만든다."""
    ins = ", ".join((pal.get("signature_add") or [])[:2] or (pal.get("instruments") or [])[:2])
    base = f"{pal.get('reference_en','')}".split(":")[0].strip() or "period"
    def s(name, when, en, sec):
        return {"name": name, "when": when, "length": f"{sec}초",
                "prompt_en": f"{en}; timbre of {base} instruments ({ins}); "
                             f"{sec}s one-shot, dry, no reverb tail beyond 0.2s, no melody"}
    return {
        "ui_hover":       s("버튼 위로", "버튼에 커서가 닿을 때", "very soft tick, felt not heard", 0.1),
        "ui_click":       s("버튼 누름", "일반 버튼", "short muted wooden click", 0.15),
        "ui_click_major": s("주요 버튼", "사건 시작·생성하기·지목", "weighted low thud with a small metallic ring", 0.5),
        "ui_back":        s("돌아가기", "이전 화면", "reversed soft click, slightly lower", 0.2),
        "tab_switch":     s("탭 전환", "수첩 탭을 옮길 때", "paper flick, single sheet", 0.25),
        "notebook_open":  s("수첩 열기", "사건수첩을 펼칠 때", "leather-bound book opening, cover creak", 0.8),
        "notebook_close": s("수첩 닫기", "사건수첩을 덮을 때", "book closing, soft dust puff", 0.7),
        "page_turn":      s("장 넘김", "카드·목록을 넘길 때", "single page turn, thick old paper", 0.4),
        "memo_write":     s("메모 적기", "메모 입력 중", "quill nib scratching on paper, brief", 0.35),
        "card_open":      s("카드 펼침", "인물·단서 카드를 열 때", "card sliding out with a faint chime", 0.5),
        "portrait_focus": s("인물 선택", "용의자 카드를 고를 때", "soft breath-like swell with a single low string pluck", 0.7),
        "case_stamp":     s("사건 확정", "제목이 도장 찍히듯 뜰 때",
                            "single massive stamp hit, like a seal pressed onto parchment, "
                            "deep and final, short bell shimmer after", 1.4),
        "title_appear":   s("제목 등장", f"'{title}' 글자가 뜰 때", "slow deep swell rising into a single sustained bell", 2.5),
        "loading_tick":   s("로딩 진행", "각색 중 상태 줄이 바뀔 때", "tiny irregular tick, like a distant clock", 0.2),
        "narration_next": s("나레이션 넘김", "다음 컷", "soft airy whoosh, page-like", 0.4),
        "murder_moment":  dict(name="범행의 순간", when="엔딩 재연 3컷 — 실제 범행",
                               length="3초",
                               prompt_en=_kill_sfx(pal.get("_weapon_class"), "")[1]
                               + "; 3s one-shot, sound design not gore, hard cut to silence"),
        "story_impact":   s("쿠쿠쿵", "원작 이야기가 사건으로 뒤집히는 순간",
                            "three descending low impacts, kuu-kuu-kung, deep taiko-like hits with "
                            "a long sub-bass tail and a sharp string stab on the third", 2.2),
        "blood_wipe":     s("혈흔 전환", "화면이 붉게 번지며 넘어갈 때",
                            "wet low smear with a sharp inhale, blood spreading across the frame", 1.6),
        "map_open":       s("지도 펼침", "지도를 열 때", "large folded paper unfolding", 0.9),
        "counter_up":     s("단서 수 증가", "발견한 단서 숫자가 오를 때", "single bright pip, one number higher", 0.3),
        "toast_in":       s("알림 등장", "새 단서 알림이 뜰 때", "soft magnifying-glass shimmer, two notes rising", 0.9),
        "typing":         s("대사 타이핑", "대사가 한 자씩 찍힐 때", "faint dry ticks, loopable at 18 chars per second", 1.0),
        "life_tick":      s("생명 감소", "남은 생명이 줄 때", "single dull heartbeat with a metallic scrape", 0.8),
    }


def _ui_music(pal, title, theme):
    """화면 전용 곡 — 지금 bgm에 없어서 다들 아무 곡이나 돌려 쓰던 자리."""
    ins = ", ".join((pal.get("instruments") or [])[:4])
    ref = pal.get("reference_en", "")
    avoid = ", ".join(pal.get("avoid") or [])
    hook = (theme or {}).get("motif_desc", "")

    def m(name, when, bpm, mood, en, form):
        return {"name": f"{title} — {name}", "when": when, "bpm": bpm, "mood": mood,
                "form": form, "theme_variation": (theme or {}).get("id"),
                "prompt_en": f"{en}; {ref}; {ins}; {bpm} BPM; instrumental, no vocals; {form}",
                "prompt": f"[main theme: {hook}] {ref}. Scene: {when}. Mood: {mood}. "
                          f"Tempo {bpm} BPM. Instruments: {ins}. {en}. "
                          f"No vocals with lyrics. Avoid: {avoid}."}
    return {
        "title": m("타이틀", "타이틀 화면 — 아직 아무 일도 일어나지 않았다", 58,
                   "고요하고 무겁다. 곧 무슨 일이 일어날 것 같은 정적",
                   "sparse title theme: one sustained low drone, the main motif played once "
                   "very slowly on a solo instrument, long silences between phrases",
                   "loop 70~100초"),
        "world_input": m("세계관 입력", "어떤 이야기로 시작할지 고르는 화면", 74,
                         "설레는 기다림. 아직 이야기가 정해지지 않은 백지",
                         "curious open theme: light arpeggio over a soft pad, unresolved ending "
                         "so it loops without settling",
                         "loop 60~90초"),
        "loading": m("각색 중", "이야기를 각색하는 로딩 화면", 96,
                     "무언가 짜여 가는 느낌. 재촉하지 않되 멈춰 있지도 않다",
                     "mechanical yet warm loop: repeating short figure that adds one voice "
                     "every 8 bars, like pieces being placed",
                     "loop 30~45초 · 이음매 없이"),
        "notebook": m("사건수첩", "수첩을 펼쳐 인물·단서를 들여다볼 때", 64,
                      "혼자 정리하는 시간. 방해하지 않는 낮은 배경",
                      "very low-profile study loop: single instrument, wide spacing, almost ambient, "
                      "mixed low so text stays readable",
                      "loop 120초+ · 반복 청취용"),
        "accuse": m("지목", "범인을 지목하기 직전", 100,
                    "돌이킬 수 없는 선택 앞. 맥박이 올라간다",
                    "tightening theme: ostinato that speeds imperceptibly, low strings pressing up, "
                    "no resolution",
                    "loop 45~60초"),
    }


# ── 화면 ──────────────────────────────────────────────────────────────
def _screens(s, pn, hud):
    t = s["meta"]["title"]
    origin = s["meta"].get("origin", "")
    pal = (s.get("bgm") or {}).get("palette") or {}
    return [
        dict(id="title", name="타이틀", when="게임을 켰을 때",
             bgm="ui.audio.music.title",
             sfx=["ui.audio.sfx.title_appear", "ui.audio.sfx.ui_click_major"],
             copy=dict(brand="MURDER MYSTERY", sub="CASE FILES",
                       tagline="모든 이야기에는 숨겨진 진실이 있다.",
                       buttons=["사건 시작", "이어서 조사하기"],
                       footer="ⓒ 생성형 추리극"),
             elements=["로고", "부제", "표어", "버튼 2개", "배경 정지화면(어두운 서재)"],
             art=dict(prompt_ko="어두운 서재, 촛불 하나, 펼쳐진 사건 서류. 인물 없음.",
                      prompt_en="dark study, single candle, open case file on a desk, no people, "
                                "heavy vignette, muted gold on black")),

        dict(id="world_input", name="세계관 입력", when="새 사건을 시작할 때",
             bgm="ui.audio.music.world_input",
             sfx=["ui.audio.sfx.typing", "ui.audio.sfx.ui_click_major"],
             copy=dict(header="CASE ARCHIVE", index="01",
                       question="어떤 이야기에서 사건을 시작할까요?",
                       placeholder=f"예) {origin}",
                       helper="알고 있는 옛이야기·동화·전설이면 무엇이든 좋습니다. "
                              "원하는 배경을 직접 적어도 됩니다 — 예) 2010년대 스타트업 사무실, 조선 왕실 수라간",
                       button="생성하기 →",
                       library_button="이미 준비된 사건 보기",
                       found_line="「{origin}」 사건이 이미 준비되어 있습니다. 바로 시작할까요?",
                       found_buttons=["바로 시작", "새로 각색하기"],
                       error="이야기를 찾지 못했습니다. 다른 이름으로 적어 주세요."),
             elements=["입력창", "예시 문구", "생성 버튼", "준비된 사건 보기"],
             branch={
                 "source": "scenarios/catalog.json (catalog.py가 만든다)",
                 "rule": "입력을 공백 제거·소문자화해 catalog.cases[].aliases와 맞춰 본다. "
                         "걸리면 **각색하지 않고 그 편을 그대로 연다** — 로딩도 '불러오는 중'으로.",
                 "on_hit": "loading(mode=load) → 곧장 나레이션",
                 "on_miss": "loading(mode=adapt) → 생성 파이프라인",
                 "adapt_pipeline": ["generate.py (원작·자유 설정 → 핵심 스키마)",
                                    "spread → relate → voices → presence → soundtrack",
                                    "pace → ui → make_novel (노벨)",
                                    "verify 통과 못 하면 그 자리에서 재생성"],
                 "adapt_note": "입력은 원작 이름일 수도, 자유 배경 설정일 수도 있다. "
                               "지금은 API 파이프라인, 나중엔 파인튜닝한 커스텀 모델이 이 자리를 대신한다.",
             }),

        dict(id="library", name="준비된 사건", when="목록에서 고를 때",
             bgm="ui.audio.music.world_input",
             sfx=["ui.audio.sfx.page_turn", "ui.audio.sfx.card_open"],
             copy=dict(header="CASE ARCHIVE", title="이미 준비된 사건",
                       hint="원작을 골라 바로 시작할 수 있습니다.",
                       sort=["최근순", "난이도순", "이야기 계열"],
                       card="{title} · 용의자 {suspects}명 · {rounds}라운드 · {difficulty}",
                       button="이 사건으로 시작"),
             elements=["표지 카드 격자(640×400)", "난이도 뱃지", "정렬", "시작 버튼"],
             ref="scenarios/catalog.json"),

        dict(id="loading", name="각색 중", when="시나리오를 만드는 동안",
             bgm="ui.audio.music.loading",
             sfx=["ui.audio.sfx.loading_tick"],
             copy=dict(title="이야기를 각색하는 중…",
                       status_lines=["등장인물들을 불러오고 있습니다",
                                     "사건의 진실을 숨기고 있습니다",
                                     "단서를 배치하고 있습니다",
                                     "그날 밤의 동선을 맞추고 있습니다"],
                       title_load="사건 기록을 여는 중…",
                       status_lines_load=["사건 기록을 펴고 있습니다",
                                          "그날 밤의 사람들을 부르고 있습니다"],
                       footer="잠시 후 사건이 시작됩니다.",
                       progress=True),
             modes={"adapt": "새 원작 — 커스텀 생성(모델 준비 중). 상태 줄 4개, 길게",
                    "load": "이미 만들어 둔 편 — 상태 줄 2개, 2~3초면 끝난다"},
             elements=["진행 막대", "상태 줄(차례로 바뀜)", "원작 제목 표시"]),

        dict(id="case_open", name="사건 공개", when="각색(또는 불러오기)이 끝난 직후",
             bgm="cues.intro (주제 선율 첫 제시 — 낮게 한 번만)",
             sfx=["ui.audio.sfx.case_stamp", "ui.audio.sfx.title_appear",
                  "ui.audio.sfx.ui_click_major"],
             copy=dict(
                 header=f"CASE — {origin}",
                 title=t,
                 setting=(pal.get("derived_from", {}) or {}).get("era", "")
                         + " · " + ((pal.get("derived_from", {}) or {}).get("location", "") or ""),
                 logline=(s.get("intro") or {}).get("twist", ""),
                 ready_lines=[f"용의자는 {len(s['cast'])}명.",
                              "그중 한 사람은, 지금도 거짓말을 준비하고 있습니다."],
                 button="사건을 연다",
                 reroll_button="다른 밤으로 다시 빚는다",
                 reroll_helper="같은 이야기에서, 전혀 다른 사건이 태어납니다.",
                 reroll_confirm="지금의 사건은 사라집니다. 같은 이야기로 새로운 밤을 빚을까요?",
                 reroll_confirm_buttons=["다시 빚는다", "이 밤을 남긴다"]),
             elements=["검은 화면", "제목이 도장 찍히듯 떠오른다", "배경 한 줄",
                       "사건 한 줄", "마지막 두 줄(한 박자 늦게)",
                       "주 버튼(사건을 연다)", "부 버튼(다른 밤으로 다시 빚는다 — 작게, 아래)"],
             staging=["검은 화면 1초 — 무음",
                      "쿵(case_stamp)과 함께 제목 「{title}」이 찍힌다",
                      "제목 아래 가는 금선이 좌우로 그어진다",
                      "배경 한 줄이 밝아진다",
                      "사건 한 줄이 밝아진다",
                      "1초 쉬고 — ready_lines 두 줄이 또박또박",
                      "버튼이 마지막에 떠오른다 — 부 버튼은 반 박자 더 늦게, 작게"],
             note="각색 결과를 처음 보여 주는 순간. 여기서 마음을 잡아야 한다."),

        dict(id="narration", name="오프닝 나레이션", when="사건 전 이야기",
             bgm="cues.intro → 마지막 컷에서 cues.discovery",
             sfx=["ui.audio.sfx.narration_next", "ui.audio.sfx.blood_wipe"],
             copy=dict(next="다음 >", skip="건너뛰기 >",
                       skip_confirm="나레이션을 건너뛰시겠습니까? 사건 개요는 수첩에서 볼 수 있습니다."),
             elements=["삽화(컷마다 교체)", "글상자", "다음/건너뛰기"],
             ref="ui.narration"),

        dict(id="blood_transition", name="혈흔 전환", when="이야기가 사건으로 뒤집히는 순간",
             bgm="cues.discovery",
             sfx=["ui.audio.sfx.blood_wipe"],
             copy=dict(line=(s.get("intro") or {}).get("twist", "")[:80]),
             elements=["붉게 번지는 전환 연출", "한 문장"],
             art=dict(prompt_en="blood spreading across a black frame, wet edges, "
                                "single line of text revealed underneath")),

        dict(id="crime_scene", name="현장", when="사건 현장을 처음 볼 때",
             bgm="place_cues." + s["death"]["place"] + ".post_murder",
             sfx=["ui.audio.sfx.card_open", "ui.audio.sfx.counter_up"],
             copy=dict(title=pn.get(s["death"]["place"], "현장"),
                       sidebar_title="증거 목록",
                       hint="목록을 눌러 자세히 봅니다.",
                       button="계속하기 >"),
             elements=["현장 일러스트(전체)", "증거 목록 사이드바", "계속하기"],
             evidence_list=[{"label": _obj(x, fallback="현장"), "text": x}
                            for x in (s["death"].get("scene_inspection") or [])],
             art=dict(prompt_ko=s["death"].get("scene_description", ""),
                      must_show=[m["condition"] for m in
                                 ((s.get("visuals") or {}).get("scene_art") or {}).get("must_show", [])],
                      must_not_show=((s.get("visuals") or {}).get("scene_art") or {}).get("must_not_show", []))),

        dict(id="victim_card", name="피해자 카드", when="현장 다음",
             bgm="cues.discovery", sfx=["ui.audio.sfx.card_open"],
             copy=dict(header="VICTIM", button="계속하기 >"),
             elements=["초상", "신분/발견 장소/발견 시각/사인 4칸", "계속하기"],
             ref="ui.victim_card"),

        dict(id="suspect_select", name="용의자 소개", when="피해자 카드 다음",
             bgm="character_themes.* (카드를 고르면 그 인물 테마로 교체)",
             sfx=["ui.audio.sfx.portrait_focus", "ui.audio.sfx.card_open"],
             copy=dict(header="SUSPECTS", hint="인물을 선택해 확인하세요.",
                       button="조사를 시작한다 >"),
             elements=[f"초상 카드 {len(s['cast'])}장", "선택 강조", "시작 버튼"],
             ref="ui.suspect_cards"),

        dict(id="hud_round", name="라운드 화면", when="라운드가 도는 동안 늘",
             bgm="cues.investigation",
             sfx=["ui.audio.sfx.toast_in", "ui.audio.sfx.life_tick"],
             copy=hud["copy"], elements=hud["elements"], ref="ui.hud"),

        dict(id="map", name="지도", when="장소를 고를 때",
             bgm="cues.investigation", sfx=["ui.audio.sfx.map_open", "ui.audio.sfx.ui_click"],
             copy=dict(title="지도", hint="조사할 장소를 고르세요.",
                       locked="아직 갈 수 없는 곳입니다.",
                       visited="이미 살펴본 곳"),
             elements=["장소 아이콘", "이번 라운드에 새로 열린 곳 표시", "돌아가기"],
             places=[{"id": p["id"], "name": p["name"], "desc": p.get("desc", "")}
                     for p in s["map"]["places"]]),

        dict(id="place_search", name="장소 조사", when="한 장소를 들여다볼 때",
             bgm="place_cues.{place_id}", sfx=["ui.audio.sfx.ui_click", "ui.audio.sfx.counter_up"],
             copy=dict(back="← 지도", notebook="사건수첩",
                       counter="발견한 단서 {found} / ?",
                       continue_label="계속 조사", found_label="단서 보기",
                       # 심문 진입 — 그 방 주인이 서 있을 때만 뜬다
                       talk="{name}에게 묻는다", talk_none="이 곳엔 사람이 없다"),
             elements=["장소 일러스트", "그 장소 주인의 서 있는 그림(있으면)",
                       "선택지 4개 이상(그 장소·라운드에 단서가 몰리면 늘어난다)", "결과 글상자", "발견한 단서 수",
                       "심문하기 버튼(주인이 있을 때)"],
             ref="ui.place_screens"),

        # ★조사 중 언제든 여는 **용의자 화면** (2026-08-25).
        #   수첩에서 인물 탭을 뺐다 — 수첩은 단서를 모으는 곳이지 상태창이 아니다.
        #   인물은 여기서 본다. 심문의 정식 경로도 여기다.
        dict(id="suspects", name="용의자", when="조사 중 언제든 — 하단 내비",
             bgm="cues.investigation",
             sfx=["ui.audio.sfx.portrait_focus", "ui.audio.sfx.card_open"],
             copy=dict(title="용의자", hint="인물을 골라 자세히 봅니다.",
                       alibi_label="알리바이",
                       not_met="아직 만나지 않았습니다.",
                       talk="이 사람에게 묻는다",
                       talk_note="장소를 눌러 들어가는 길은 지름길일 뿐이다. "
                                 "제 방이 없는 인물도 여기서 만난다.",
                       confront_hint="맞대 놓기는 아래 내비의 [대질]에서 한다.",
                       cleared="혐의를 벗었습니다"),
             elements=["초상 카드(만나지 않은 인물은 실루엣)", "신분·나이·관계",
                       "알리바이 — 첫 대면에 들은 그 문장",
                       "이 인물에게서 얻은 소지품", "공개된 비밀",
                       "「이 사람에게 묻는다」 버튼"],
             ref="ui.suspect_cards",
             note="압박 게이지 같은 수치는 심문 화면에만 둔다. 여기는 읽는 자리다."),

        dict(id="interrogation", name="심문", when="인물에게 물을 때 — "
             "① 하단 내비 [용의자]에서(누구나) ② 장소를 눌러 그 방 주인에게(지름길)",
             bgm="character_themes.{cast_id}", sfx=["ui.audio.sfx.typing"],
             copy=dict(placeholder="무엇을 묻겠습니까?",
                       send="묻는다", press="몰아붙인다", show_evidence="증거를 들이댄다",
                       turns_left="이 라운드에 남은 행동 {n}회",
                       evidence_picker="들이댈 단서를 고르세요."),
             elements=["인물 초상(표정 3단: 평정/흔들림/무너짐)", "대사 글상자",
                       "감정 표시", "질문 입력", "증거 들이대기"]),

        # ★대질 전용 화면(2026-08-25) — 심문 안의 버튼이 아니라 화면 하나를 준다.
        #   두 사람을 나란히 세워야 하고, 한 판에 한 번뿐인 결정이라
        #   장소·수첩에 묻어 두면 무게가 안 산다.
        dict(id="confront", name="대질", when="중반 이벤트가 터진 뒤부터 — 한 판에 한 번",
             bgm="cues.climax", sfx=["ui.audio.sfx.portrait_focus",
                                     "ui.audio.sfx.ui_click_major",
                                     "event_cues.accusation"],
             copy=dict(header="CONFRONTATION", title="맞대 놓기",
                       hint="두 사람을 한자리에 세운다. 어긋난 말이 있다면 여기서 드러난다.",
                       pick_a="누구를 앉힐까요?", pick_b="누구와 맞대 놓을까요?",
                       claim_a="{a}의 말", claim_b="{b}의 말",
                       ask="무엇을 묻겠습니까?",
                       submit="맞대 놓는다",
                       warn="대질은 한 판에 **한 번**뿐입니다. 행동 예산은 쓰지 않지만, 되돌릴 수 없습니다.",
                       cancel="조금 더 생각한다",
                       cost="남은 대질 {n}회 · 행동 1",
                       locked_title="아직 맞대 놓을 수 없다",
                       locked_body="사람을 맞대 놓으려면 판이 한 번 뒤집혀야 한다.",
                       hit_title="말이 어긋납니다",
                       miss_title="그 말로는 걸리지 않는다",
                       miss_body="두 사람의 말은 어긋나지 않았다. 기회만 썼다.",
                       need_heard="아직 두 사람의 말을 다 듣지 못했습니다.",
                       to_result="계속 >"),
             elements=["좌우 인물 초상 2인(마주 보게)", "각자의 진술 카드 2장",
                       "가운데 어긋난 대목 표시", "질문 입력",
                       "남은 대질 횟수·턴 비용", "확인 창(되돌릴 수 없음)",
                       "★주고받는 대본 재생 — cross_examination.pairs[].exchange[]를 "
                       "한 줄씩 띄운다. 말하는 쪽 초상을 밝히고 반대쪽은 어둡게",
                       "beat 표시 — alibi: 진술→반박→동요→쐐기→함구 / timeline: 진술→겹침→깨달음→균열→머뭇→함구 / witness: 목격→부인→구체→흔들림 / relation: 부인→흘림→반발→되받음→실토",
                       "결과: 드러난 것(reveals) 카드 + 양쪽 압박 상승"],
             exchange_note="한 질문에 **둘 다** 답한다. exchange[]의 who로 좌/우를 가르고, "
                           "tone은 연기·자막 연출 지시다. 마지막 실토에서 reveals가 열린다.",
             ref="cross_examination"),

        dict(id="notebook", name="사건수첩", when="언제든",
             bgm="ui.audio.music.notebook",
             sfx=["ui.audio.sfx.notebook_open", "ui.audio.sfx.tab_switch",
                  "ui.audio.sfx.page_turn", "ui.audio.sfx.memo_write"],
             copy=dict(title="사건수첩", back="← 돌아가기", settings="설정"),
             elements=["탭 3개(인물/단서/메모)", "왼쪽 목록", "가운데 상세", "오른쪽 메모"],
             ref="ui.notebook"),

        dict(id="accuse", name="범인 지목", when="마지막 라운드가 끝난 뒤",
             bgm="ui.audio.music.accuse",
             sfx=["ui.audio.sfx.ui_click_major", "ui.audio.sfx.life_tick"],
             copy=dict(title="범인 지목", question="이 사건의 범인은 누구입니까?",
                       weapon_q="흉기는 무엇이었습니까?", motive_q="왜 죽였습니까?",
                       warn="한 번 지목하면 되돌릴 수 없습니다.",
                       submit="지목한다", cancel="조금 더 조사한다"),
             elements=["용의자 5장", "흉기 고르기", "동기 적기", "확인 창"]),

        dict(id="reveal", name="진상", when="지목 뒤",
             bgm="cues.reveal", sfx=["ui.audio.sfx.blood_wipe", "ui.audio.sfx.card_open"],
             copy=dict(header="THE TRUTH", next="다음 >", to_ending="엔딩 보기 >"),
             elements=["그날 밤 재구성 컷", "시간 순 자막", "결정타 단서 강조"],
             ref="ui.reveal_sequence"),

        dict(id="reenactment", name="범행 재연", when="진상 낭독이 끝난 직후",
             bgm="cues.reveal → 범행 컷에서 뚝 끊김 → cues.ending",
             sfx=["ui.audio.sfx.murder_moment", "ui.audio.sfx.blood_wipe"],
             copy=dict(header="THAT NIGHT", caption="그날 밤, 실제로 있었던 일",
                       no_skip="(건너뛸 수 없음)"),
             elements=["재연 컷 6장(자동 진행)", "컷마다 한 줄 자막", "범인 얼굴 첫 공개"],
             ref="ui.murder_reenactment"),

        dict(id="ending", name="엔딩", when="재연이 끝난 뒤",
             bgm="cues.ending", sfx=["ui.audio.sfx.page_turn"],
             copy=dict(score="점수 {pts} / {max}", grade_label="엔딩",
                       secrets="밝혀낸 비밀 {n}개",
                       buttons=["다시 조사하기", "다른 이야기로 시작하기", "기록 저장"]),
             elements=["등급 이름", "엔딩 글", "점수 내역", "버튼 3개"]),
    ]



# ── 나레이션 페이지 나누기 ────────────────────────────────────────────
# ── 나레이션 글자창 한도 ──────────────────────────────────────────────
# 실제 화면에서 78자짜리 쪽이 세 줄째부터 잘려 나왔다(07편 1쪽, 2026-08-24).
# 프론트가 재는 실제 글자창 용량에 맞춰 **환경변수로 조절**한다.
#     MM_PAGE_MAX=80 MM_SENT_MAX=40 ./hand_pipeline.sh out/07_hansel_gretel.json
# 한도를 줄이면 쪽(장면)이 늘어나고, 쪽마다 그림이 하나씩 붙는다.
PAGE_MAX = int(os.environ.get("MM_PAGE_MAX", 88))   # 두 문장 합친 한도(공백 포함)
SENT_MAX = int(os.environ.get("MM_SENT_MAX", 44))   # 한 문장 한도 (2 × 44 = 88)
PAGE_IMG  = (1045, 600)   # 스토리 그림 규격
SCENE_IMG = (1045, 600)   # 현장·주검 그림
PLACE_IMG = (1045, 600)   # 장소 조사 배경
MAP_THUMB = (320, 200)    # 지도에 박히는 장소 그림
PORTRAIT  = (512, 768)    # 인물 초상
STANDING  = (600, 1200)   # 장소에 세우는 전신
THUMB     = (256, 256)    # 단서 썸네일

# 이어지는 말끝 → 끝나는 말끝. 쉼표 앞이 이 꼴이면 거기서 문장을 끊는다.
_CONN = [
    ("이었고", "이었다"), ("였고", "였다"), ("았고", "았다"), ("었고", "었다"),
    ("했고", "했다"), ("하고", "했다"), ("이고", "이다"),
    ("았으며", "았다"), ("었으며", "었다"), ("하며", "했다"), ("이며", "이다"),
    ("았지만", "았다"), ("었지만", "었다"), ("하지만", "했다"),
    ("았는데", "았다"), ("었는데", "었다"), ("인데", "이다"),
    ("아서", "았다"), ("어서", "었다"), ("해서", "했다"), ("여서", "였다"),
    ("았으나", "았다"), ("었으나", "었다"), ("하나", "한다"),
    ("터라", "터였다"), ("길래", "었다"),
    # 쉼표 뒤가 아니라 문장 한가운데서 이어지는 꼴도 끊는다(2026-08-24 보강)
    ("았으니", "았다"), ("었으니", "었다"), ("하니", "했다"),
    ("았다가", "았다"), ("었다가", "었다"),
    ("면서", "었다"), ("으면서", "었다"),
    ("자마자", "았다"), ("더니", "었다"),
    ("거니와", "었다"), ("는가 하면", "었다"),
    # '-ㄴ 채'로 이어지는 꼴 — 03편 1쪽이 90자 한 문장으로 남아 글자창을 넘겼다
    ("못한 채", "못했다"), ("않은 채", "않았다"), ("한 채", "했다"),
    ("진 채", "졌다"), ("난 채", "났다"), ("둔 채", "두었다"),
]


def _sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.?!])\s+", str(text or "").strip()) if x.strip()]


def _split_long(sent, depth=0):
    """긴 문장을 **말끝을 갈아 끼워** 두 문장으로 나눈다. 못 나누면 그대로 둔다."""
    if len(sent) <= SENT_MAX or depth >= 2:
        return [sent]
    best = None
    for m in re.finditer(r"[,，]\s*", sent):
        head = sent[:m.start()].rstrip()
        for a, b in _CONN:
            if head.endswith(a):
                # 가운데에 가까운 쉼표를 고른다
                d = abs(m.start() - len(sent) // 2)
                if best is None or d < best[0]:
                    best = (d, m.end(), head[:-len(a)] + b + ".")
                break
    if not best:
        # 쉼표가 없어도 **연결어미 자리**에서 끊는다.
        #   "…길을 표시했으나 두 번째로 버려진 날엔…" 처럼 쉼표 없이 이어지는 70자 문장이
        #   그대로 남아 글자창을 넘겼다(07편 2쪽).
        for a, b in _CONN:
            for m in re.finditer(re.escape(a) + r"\s+", sent):
                if m.start() < 6 or len(sent) - m.end() < 6:
                    continue                     # 너무 치우친 자리는 문장이 토막 난다
                d = abs(m.start() - len(sent) // 2)
                cand = sent[:m.start()] + b + "."
                if best is None or d < best[0]:
                    best = (d, m.end(), cand)
            if best:
                break
    if not best:
        return [sent]
    _, cut, head = best
    tail = sent[cut:].strip()
    if not tail:
        return [sent]
    tail = tail[0] + tail[1:]
    return _split_long(head, depth + 1) + _split_long(tail, depth + 1)


def _paginate(sents):
    """한 쪽에 두 문장, 합쳐 96자 이내. 넘치면 한 문장만 놓는다."""
    flat = []
    for s0 in sents:
        flat += _split_long(s0)
    pages, i = [], 0
    while i < len(flat):
        a = flat[i]
        if i + 1 < len(flat) and len(a) + 1 + len(flat[i + 1]) <= PAGE_MAX:
            pages.append([a, flat[i + 1]]); i += 2
        else:
            pages.append([a]); i += 1
    return pages


# ── 나레이션 전문 ─────────────────────────────────────────────────────
def _incident_hit(text):
    """이 쪽에서 사건이 터지는가 — 원작 이야기가 뒤집히는 지점."""
    return any(k in text for k in ("사건이 일어난", "사건이 터진", "여기서 끝난",
                                   "쓰러져", "주검", "죽어", "죽은 채", "숨진"))


def _narration(s, pal):
    beats = (s.get("intro") or {}).get("narration") or []
    df = pal.get("derived_from", {}) or {}
    pages, seq = [], 0
    for bi, b in enumerate(beats, 1):
        for pg in _paginate(_sentences(b.get("text", ""))):
            seq += 1
            body = " ".join(pg)
            pages.append({
                "page": seq, "beat": bi,
                "text": body,
                "sentences": pg,
                "chars": len(body),
                "over_limit": len(body) > PAGE_MAX,
                "mood": b.get("mood", ""), "focus": b.get("focus", ""),
                "image": {
                    "w": PAGE_IMG[0], "h": PAGE_IMG[1],
                    "scene": b.get("scene", ""),
                    "prompt_ko": f"{b.get('scene','')}. {df.get('location','')}. {df.get('color_palette','')}",
                    "prompt_en": f"storybook illustration, {b.get('scene','')}, "
                                 f"{df.get('culture','')} setting, painterly, warm candlelit palette, "
                                 f"no text, 1045x600 landscape",
                    "note": "밝은 대목은 밝게 그린다. 뒤집힐 때 낙차가 커진다.",
                },
                "render": "still",
                "duration_sec": max(3, round(len(body) / 5.2)),
                "bgm": "cues.intro",
                "sfx": ["ui.audio.sfx.narration_next"],
            })
    # 사건이 터지는 쪽을 찾아 표시한다 — 없으면 마지막 쪽
    hit = next((p for p in pages if _incident_hit(p["text"])), pages[-1] if pages else None)
    for p_ in pages:
        p_["render"] = "still"
    if hit:
        hit["is_incident"] = True
        hit["bgm"] = "cues.intro → (끊김) → cues.discovery"
        hit["sfx"] = ["ui.audio.sfx.story_impact", "ui.audio.sfx.blood_wipe"]
        hit["image"]["prompt_en"] = hit["image"]["prompt_en"].replace(
            "warm candlelit palette", "cold desaturated palette, the moment it turns")
        hit["image"]["note"] = "여기서 그림도 색이 식는다. 앞쪽 밝은 그림과 나란히 놓고 확인할 것."
        hit["transition"] = {
            "order": ["원작 BGM(cues.intro) 0.4초에 걸쳐 뚝 끊는다",
                      "무음 0.2초",
                      "쿠쿠쿵 (ui.audio.sfx.story_impact) — 저역 3연타",
                      "혈흔 전환 (ui.audio.sfx.blood_wipe)",
                      "머더미스터리 BGM(cues.discovery) 들어온다"],
            "total_sec": 3.2,
            "note": "임팩트가 글자보다 먼저 온다. 소리를 듣고 나서 문장을 읽게.",
        }
    # 몇 쪽마다 영상으로 갈지 — 가운데 대목
    n = len(pages)
    for p_ in pages:
        if 0.35 * n <= p_["page"] <= 0.7 * n:
            p_["render"] = "video"
    return {
        "note": f"한 쪽에 두 문장, 공백 포함 {PAGE_MAX}자 이내. 그림은 쪽마다 하나 "
                f"({PAGE_IMG[0]}×{PAGE_IMG[1]}).",
        "limits": {"chars_per_page": PAGE_MAX, "sentences_per_page": 2,
                   "chars_per_sentence": SENT_MAX,
                   "image": {"w": PAGE_IMG[0], "h": PAGE_IMG[1]}},
        "narrator": {
            "role": "이야기를 들려주는 사람 — 등장인물이 아니다",
            "tone": "옛이야기를 읊듯 낮고 느리게. 사건이 드러나기 전까지는 따뜻하게",
            "pitch": "낮음", "tempo": "느림(0.9배)",
            "prompt_en": "narrator voice, warm low storyteller tone, unhurried, Korean, "
                         "turns cold and quiet at the incident page",
        },
        "next_label": "다음 >", "skip_label": "건너뛰기 >",
        "pages": pages,
        "page_count": n,
        "image_count": n,
        "video_pages": [p_["page"] for p_ in pages if p_["render"] == "video"],
        "incident_page": next((p_["page"] for p_ in pages if p_.get("is_incident")), None),
        "over_limit_pages": [p_["page"] for p_ in pages if p_["over_limit"]],
        "full_text": "\n\n".join(p_["text"] for p_ in pages),
        # 옛 도구 호환 — 컷 단위도 남겨 둔다
        "beats": [{"no": i, "text": b.get("text", ""), "mood": b.get("mood", ""),
                   "scene": b.get("scene", "")} for i, b in enumerate(beats, 1)],
    }


# ── 진상 낭독 ─────────────────────────────────────────────────────────
def _sent(text, n=2, cap=200):
    """긴 글에서 앞 n문장만. 진상 낭독이 텍스트 벽이 되지 않게 자른다."""
    x = re.sub(r"\s+", " ", str(text or "")).strip()
    if not x:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", x)
    out = " ".join(parts[:n]).strip()
    if len(out) > cap:                      # 그래도 길면 문장 경계에서 자른다
        cut = out[:cap]
        k = max(cut.rfind("."), cut.rfind("—"), cut.rfind(","))
        out = (cut[:k + 1] if k > cap * 0.5 else cut).rstrip(" ,—") + "…"
    return out


# 마무리 한 줄 — **직접 쓴 문장만 쓴다.**
#   참고작(크라임씬)의 "그렇게 완전범죄를 꿈꿨다"를 그대로 가져다 쓰지 않는다.
#   같은 자리에서 같은 일을 하되(범인의 자신감 → 곧 무너질 것의 예고) 우리 문장으로.
_ALMOST_PERFECT = [
    "그렇게 그 밤은, 아무 일도 없던 밤으로 묻힐 뻔했다.",
    "계산은 빈틈이 없었다. 그 하나만 아니었다면.",
    "아무도 묻지 않았다면, 그것으로 끝날 일이었다.",
    "완벽에 가장 가까웠던 밤이다 — 가장 가까웠을 뿐이다.",
    "그 밤의 셈은 거의 맞아떨어졌다. 거의.",
]


def _reveal(s, pn):
    """엔딩 진상 낭독.

    ■ 2026-08-24 개편 (찬열이형 지시)
      순서를 **범인 → 동기 → 트릭 → 어떻게 빠져나갔나 → 마무리**로 바꿨다.
      전에는 '정적 → 의심 → 결정타 → 이름 → 전부' 순서였는데
        · 결정타 단서 원문을 통째로 읽어 한 박이 57초짜리 텍스트 벽이었고
        · 마지막 '전부' 박이 77초로 해설서 낭독에 가까웠다.
      이제 박마다 **한 가지 일만** 하고, 길이를 문장 수로 묶는다.
    """
    sol = s.get("solution") or {}
    cul = next((c for c in s["cast"] if c.get("is_culprit")), None)
    dec = next((c for c in s["clue_graph"] if c.get("decisive")), None)
    d = s["death"]
    cn = cul["name"] if cul else "범인"
    who = (cul.get("public") or (cul.get("profile") or {}).get("status") or "") if cul else ""
    vic = s["victim"]["name"]
    place = pn.get(d["place"], "")
    wp = _weapon_prose(d.get("weapon", ""))
    tr = s.get("trick") or {}
    tr_name = tr.get("name", "")
    tr_cond = tr.get("conditions") or []
    motive = _sent(cul.get("kill_motive") if cul else "", 2, 190) or \
             (sol.get("motive_label") or "")
    _, escape = _split_method(d.get("method", ""), place)
    # 마무리 문구는 편마다 다르게(제목 글자수로 고른다 — 무작위를 쓰지 않는다)
    closer = _ALMOST_PERFECT[len(s["meta"].get("title", "")) % len(_ALMOST_PERFECT)]

    beats = [
        dict(no=1, label="그날 밤", bgm="cues.reveal#1_still",
             text=f"{d['time_slot']}, {place}. {vic}{_j(vic,'은/는')} 아직 살아 있었다.",
             shot="현장 전경 — 아직 아무 일도 없다",
             sfx=["ui.audio.sfx.narration_next"]),

        dict(no=2, label="범인", bgm="cues.reveal#2_name",
             text=f"{vic}{_j(vic,'을/를')} 죽인 사람은 {cn}"
                  + (f", {who}{_j(who,'이/')}다." if who else "다.")
                  + " 이 밤의 모든 어긋남이 그 한 사람에게로 모인다.",
             shot="범인의 얼굴이 어둠에서 드러난다 — 게임 중 처음",
             sfx=["ui.audio.sfx.portrait_focus"], emphasis=True),

        dict(no=3, label="동기", bgm="cues.reveal#3_why",
             text=f"까닭은 이것이다. {motive}"
                  + ("" if str(motive).endswith(('.', '다', '…')) else "."),
             shot="동기가 된 물건·문서·관계가 화면에 뜬다",
             sfx=["ui.audio.sfx.card_open"]),

        dict(no=4, label="트릭", bgm="cues.reveal#4_trick",
             text=(f"그리고 {cn}{_j(cn,'은/는')} 자기 자리를 만들어 두었다 — {tr_name}. "
                   + (_sent(tr_cond[0], 1, 110) if tr_cond else "")).strip(),
             shot="트릭의 원리를 보여 주는 도해 컷 — 재연 4컷과 같은 그림",
             sfx=["event_cues.clue_decisive"], emphasis=True),

        dict(no=5, label="빠져나간 길", bgm="cues.reveal#5_exit",
             text=f"{wp}{_je(wp)} 일을 마친 뒤, {escape} "
                  + (_sent(tr_cond[1], 1, 110) if len(tr_cond) > 1 else
                     "아무도 그 걸음을 세지 않았다."),
             shot="현장을 떠나는 동선 — 재연 5컷과 이어진다",
             sfx=["ui.audio.sfx.page_turn"]),

        dict(no=6, label="그리고 남은 하나", bgm="cues.reveal#6_crack",
             text=f"{closer} "
                  + (f"그러나 {_sent(dec.get('implies') or dec.get('surface'), 1, 150)}"
                     if dec else "그러나 지워지지 않은 것이 하나 있었다."),
             shot="결정타 단서 하나만 화면에 남는다",
             sfx=["ui.audio.sfx.blood_wipe"], emphasis=True),
    ]
    for b in beats:
        b["text"] = re.sub(r"\s+", " ", b["text"]).strip()
        b["duration_sec"] = max(4, min(14, round(len(b["text"]) / 5.2)))
    return {
        "note": "엔딩 진상. 여섯 박 — 정적 → 범인 → 동기 → 트릭 → 빠져나간 길 → 남은 하나. "
                "박마다 한 가지 일만 한다(전에는 한 박이 57~77초짜리 텍스트 벽이었다).",
        "order": ["그날 밤", "범인", "동기", "트릭", "빠져나간 길", "그리고 남은 하나"],
        "narrator": "오프닝과 같은 목소리. 여기서는 빠르고 단단하게.",
        "closing_line_policy": "마무리 문구는 참고작 대사를 쓰지 않고 자체 문장(_ALMOST_PERFECT)에서 고른다.",
        "beats": beats,
        "full_text": "\n\n".join(b["text"] for b in beats),
    }


# ── 살인 재연 (엔딩 컷) ───────────────────────────────────────────────
# 흉기 갈래 → 범행 순간의 소리
_KILL_SFX = {
    "자상": ("blade strike", "single sharp blade thrust with cloth tear, wet impact implied "
             "by sound design not gore, hard cutoff into silence"),
    "독":   ("poison pour", "liquid trickling into a cup, a faint clink, then a long uneasy "
             "silence broken by a single body slump"),
    "교살": ("strangle", "rope creak and strained cloth, muffled struggle, then stillness"),
    "타격": ("blunt hit", "single heavy blunt impact with a low thud resonance, object "
             "clattering to the floor"),
    "추락": ("fall", "short scuffle, a cry cut off, distant heavy landing with dust"),
    "화상": ("fire", "sudden roar of flames, crackling, a door slamming"),
    "익사": ("drown", "violent water splashing that slows into gentle lapping"),
}


def _kill_sfx(weapon_class, weapon=""):
    for k, v in _KILL_SFX.items():
        if k in str(weapon_class or "") or k in str(weapon or ""):
            return v
    return ("kill moment", "abrupt violent movement implied by sound design, "
            "impact, then total silence")


_END_FIX = [("들어,", "들었다."), ("들어", "들었다"), ("들어가", "들어갔다"),
            ("내려가", "내려갔다"), ("올라가", "올라갔다"), ("다가가", "다가갔다"),
            ("다녀와", "다녀왔다"), ("타고", "탔다"), ("틈타", "틈탔다"),
            ("숨어", "숨었다"), ("나와", "나왔다"), ("빠져나가", "빠져나갔다"),
            ("찌른 뒤", "찔렀다"), ("먹인 뒤", "먹였다"), ("살해하고", "살해했다"),
            ("죽이고", "죽였다"), ("꾸미고", "꾸몄다"), ("위장하고", "위장했다"),
            ("하고", "했다"), ("두고", "두었다"), ("남기고", "남겼다"),
            ("지우고", "지웠다"), ("잠그고", "잠갔다"), ("걸고", "걸었다")]


def _finish(clause):
    """연결어미로 끝나는 토막을 끝나는 문장으로 만든다."""
    c = clause.strip().rstrip(".").rstrip(",").rstrip()
    if not c:
        return c
    for a, b in _END_FIX:
        if c.endswith(a):
            return c[: -len(a)] + b
    if re.search(r"(다|함|음|임)$", c):
        return c
    if c.endswith("위장"):
        return c + "했다"
    # 일반 연결어미 — 낱말 목록으로는 못 잡는 것들을 무늬로 끝맺는다.
    #   "…한스와 마주쳤고" → "…한스와 마주쳤다"  (재연 2컷이 이 꼴로 잘려 나왔다)
    m = re.search(r"(았|었|였)(고|으며|며|는데|지만|다가|자|으나|나)$", c)
    if m:
        return c[: m.start()] + m.group(1) + "다"
    # 축약 과거형 — '치었고'는 '쳤고'로 줄어 위 무늬에 안 걸린다.
    #   'ㅆ' 받침(종성 20)이면 과거형으로 보고 연결어미를 '-다'로 끝맺는다.
    m = re.search(r"([가-힣])(고|으며|며|는데|지만|다가|자|으나|나)$", c)
    if m and (ord(m.group(1)) - 0xAC00) % 28 == 20:
        return c[: m.start()] + m.group(1) + "다"
    m = re.search(r"(하|되)(고|며|면서|자|는데|지만)$", c)
    if m:
        return c[: m.start()] + m.group(1) + ("였다" if m.group(1) == "하" else "었다")
    return c + "."  # 더 못 고치면 그대로 둔다


def _split_method(method, place):
    """death.method → (접근 문장, 위장 문장). 범행 자체는 3컷이 따로 그린다."""
    parts = [x.strip() for x in re.split(r"[,，]", str(method or "")) if x.strip()]
    if not parts:
        return f"{place}에 몰래 들었다.", "아무 일 없던 듯 자리를 떴다."
    kill_re = r"찌|찔|먹이|먹인|조르|졸라|내리치|밀어|베|살해|해치|독을|비상을|숨통|목을|눌러"
    kill_i = next((i for i, x in enumerate(parts) if re.search(kill_re, x)), None)
    app = parts[: kill_i] if kill_i is not None else parts[:1]
    stg = parts[kill_i + 1:] if kill_i is not None else parts[1:]
    approach = _finish(", ".join(app)) if app else f"그 밤, 아무도 모르게 {place}{_je(place)} 향했다"
    if stg:
        stage = _finish(", ".join(stg))
    else:
        stage = "흔적을 지우고 아무 일 없던 듯 자리를 떴다"
    if not approach.endswith("."):
        approach += "."
    if not stage.endswith("."):
        stage += "."
    return approach, stage


def _weapon_prose(weapon):
    """'대검(자상)' → '대검' — 문장에 넣을 때는 괄호를 뗀다."""
    return re.sub(r"\s*\([^)]*\)", "", str(weapon or "")).strip()


def _lighting(slot):
    """시간대 → 빛. 그림 팀이 컷마다 같은 광원을 쓰도록 못박는다."""
    return {
        "밤":   ("촛불·등불 하나뿐인 어둠. 그림자가 길고 윤곽만 남는다",
                 "single candle/lantern source, deep shadows, rim-lit silhouettes"),
        "새벽": ("푸르스름한 여명. 아직 등불이 살아 있어 두 광원이 섞인다",
                 "cold blue pre-dawn light mixing with a dying lantern, two light sources"),
        "저녁": ("해가 진 직후의 남은 붉은 빛과 막 켠 등불",
                 "last red dusk glow with freshly lit lanterns"),
        "초저녁": ("해가 진 직후의 남은 붉은 빛과 막 켠 등불",
                 "last red dusk glow with freshly lit lanterns"),
        "낮":   ("창으로 드는 직사광. 먼지가 빛줄기에 뜬다",
                 "hard daylight through a window, dust motes in the beam"),
        "아침": ("차고 맑은 아침 빛. 그림자가 짧다",
                 "clear cold morning light, short shadows"),
    }.get(str(slot or "").strip(), ("등불 하나의 어둠", "single lantern in darkness"))


def _look(ap):
    """범인 인상착의를 한 줄로 — 컷마다 같은 사람으로 그려지도록."""
    ko = " · ".join(x for x in [ap.get("build"), ap.get("hair"),
                                ap.get("face"), ap.get("clothing")] if x)
    return ko or "인상착의 미상"


def _cast_access(s, pn):
    """인물마다 만날 수 있는 길을 정리한다.

    장소 클릭만으로는 **제 방이 없는 용의자**와 대화할 수 없다(50편 중 5편).
    그래서 [용의자] 화면을 보편 경로로 두고, 장소는 지름길로 표시한다.
    """
    owner = {p.get("owner"): p["id"] for p in s["map"]["places"] if p.get("owner")}
    out = {}
    for c in s["cast"]:
        pid = owner.get(c["id"])
        out[c["id"]] = {
            "name": c["name"],
            "notebook": True,                      # 언제나 수첩에서 만난다
            "place": pid,                          # 제 방(있으면) — 지름길
            "place_name": pn.get(pid) if pid else None,
            "note": (f"{pn.get(pid)}에서도 만날 수 있다." if pid
                     else "제 방이 없다 — [용의자] 화면에서만 만난다."),
        }
    return out


def _reenactment(s, pn):
    """게임이 끝난 뒤 — **범인이 실제로 죽이는 그 밤**을 컷으로 보여 준다.

    ■ 2026-08-24 개편 (디자인팀 피드백: "묘사가 더 자세히 써지면 잘 만들어질 것 같다")
      · 컷 5장 → **6장**. 트릭이 어떻게 작동했는지 보여 주는 컷을 새로 넣었다.
        게임에서 가장 궁금했던 것(어떻게 알리바이를 만들었나)이 그림으로 풀린다.
      · 컷마다 프롬프트를 **피사체·행동·소품·광원·카메라·표정**으로 쪼개 적는다.
        전에는 "…향하는 뒷모습" 한 줄이라 그림 팀이 매번 다르게 해석했다.
      · `continuity`로 컷 사이에 반드시 같아야 하는 것(얼굴·옷·흉기·장소)을 못박는다.
    """
    d = s["death"]
    cul = next((c for c in s["cast"] if c.get("is_culprit")), None)
    if not cul:
        return None
    place = pn.get(d["place"], "")
    pc = next((p for p in s["map"]["places"] if p["id"] == d["place"]), {})
    feats = [f for f in (pc.get("features") or [])][:3]
    feat_ko = ", ".join(feats) if feats else "현장의 기물"
    vic = s["victim"]["name"]
    cn = cul["name"]
    ap = cul.get("appearance") or {}
    look_ko = _look(ap)
    face_en = (ap.get("prompt_en") or "").replace("seated for questioning, ", "") \
                                         .replace("waist-up, neutral background", "full scene")
    lit_ko, lit_en = _lighting(d.get("time_slot"))
    method = d.get("method", "")
    approach, stage = _split_method(method, place)
    sfx_name, sfx_en = _kill_sfx(d.get("weapon_class"), d.get("weapon"))
    motive = (cul.get("kill_motive") or (s.get("solution") or {}).get("motive_label") or "")
    wp = _weapon_prose(d.get("weapon", ""))
    tr = s.get("trick") or {}
    tr_name = tr.get("name", "")
    tr_desc = tr.get("desc", "")
    tr_cond = (tr.get("conditions") or [])
    tense = (ap.get("under_pressure") or "얼굴이 굳는다")

    CONT = f"범인 얼굴·옷차림은 [{look_ko}]으로 6컷 내내 동일. 흉기 [{wp}]는 같은 물건으로."

    def cut(no, label, text, shot_ko, shot_en, bgm, sfx, dur,
            face=True, camera="", emotion="", note=""):
        return {
            "no": no, "label": label, "text": text,
            "duration_sec": dur,
            "camera": camera, "emotion": emotion,
            "lighting": lit_ko,
            "continuity": CONT,
            "image": {
                "w": PAGE_IMG[0], "h": PAGE_IMG[1],
                "prompt_ko": shot_ko,
                "prompt_en": f"{shot_en}, {lit_en}, painterly cinematic realism, "
                             f"no text, no watermark, 1045x600 landscape"
                             + ("" if face else ", culprit's face hidden in shadow"),
                "show_culprit_face": face,
                "negative_en": "modern objects, text, watermark, extra limbs, "
                               "gore, blood spray, cartoon style",
            },
            "bgm": bgm, "sfx": sfx, "note": note,
        }

    cuts = [
        cut(1, "그 밤 — 결심",
            f"{d['time_slot']}. {cn}{_j(cn,'은/는')} 마음을 정했다. {motive}.",
            f"[피사체] {cn}({look_ko})의 얼굴이 게임에서 처음으로 어둠 속에 또렷이 드러난다. "
            f"[행동] 한 손으로 문설주를 짚고 서서 {place} 쪽을 응시한다. "
            f"[표정] 결심이 선 뒤의 무표정 — 눈만 흔들리지 않는다. {tense}. "
            f"[광원] {lit_ko}. 얼굴 절반만 빛을 받는다. "
            f"[카메라] 가슴 위 클로즈업, 눈높이. 배경은 흐리게.",
            f"{face_en}, face finally revealed, half-lit by candlelight, resolved unblinking eyes, "
            f"one hand braced on a doorframe, chest-up close-up at eye level, shallow depth of field",
            "cues.reveal (낮게 깔린다)", ["ui.audio.sfx.narration_next"], 6,
            camera="가슴 위 클로즈업 · 눈높이 · 얕은 심도",
            emotion="결심 — 두려움을 누른 무표정",
            note="게임 내내 감춰 온 얼굴을 여기서 처음 보여 준다"),

        cut(2, "접근",
            approach,
            f"[피사체] {cn}의 뒷모습. 얼굴은 보이지 않는다. "
            f"[행동] {place}({pc.get('desc','')})로 향한다. 치맛자락/옷자락이 걸음에 쓸린다. "
            f"[소품] 아직 흉기는 손에 없다 — 현장에 있는 {feat_ko}{_j(feat_ko,'이/가')} 미리 보인다. "
            f"[광원] {lit_ko}. 인물은 역광으로 검게. "
            f"[카메라] 뒤에서 따라가는 전신 롱숏, 낮은 앵글.",
            f"the culprit seen from behind walking toward {place}, backlit into near-silhouette, "
            f"garment hem dragging with each step, empty hands, "
            f"full-body long shot from behind at a low angle, the location's props ({feat_ko}) visible ahead",
            "cues.reveal (걸음마다 조인다)", ["ui.audio.sfx.loading_tick"], 7, face=False,
            camera="뒤따라가는 전신 롱숏 · 낮은 앵글",
            emotion="긴장 — 되돌릴 수 있는 마지막 순간"),

        cut(3, "범행",
            f"{vic}{_j(vic,'은/는')} 눈치채지 못했다. {wp}{_je(wp)} — 한순간이었다.",
            f"[피사체] {cn}{_j(cn,'과/와')} {vic}, 둘 다 실루엣으로만. "
            f"[행동] {wp}{_je(wp)} 내리치는 바로 그 순간에서 정지. "
            f"[수위] 직접적 유혈·상처는 그리지 않는다. 벽에 비친 그림자와 실루엣까지만. "
            f"[소품] {wp}의 윤곽이 분명히 읽혀야 한다 — 플레이어가 흉기를 알아보는 컷이다. "
            f"[광원] {lit_ko}. 등 뒤 광원으로 두 사람이 검게 찍힌다. "
            f"[카메라] 벽에 진 그림자를 크게 잡는다. 인물은 화면 아래 3분의 1.",
            f"the murder moment in {place}: two figures rendered only as silhouettes and wall shadows, "
            f"the culprit's raised {d.get('weapon_class','')} clearly readable in outline, "
            f"frozen at the instant of impact, violence implied never graphic, no blood, "
            f"shadow-play composition with figures in the lower third",
            "음악이 뚝 끊긴다", ["ui.audio.sfx.murder_moment"], 5, face=False,
            camera="벽 그림자 위주 · 인물은 하단 1/3",
            emotion="공포와 충동이 겹친 한순간",
            note="화면이 한 박자 정지 — 소리(범행음)만. 잔혹 묘사는 실루엣까지"),

        cut(4, "트릭 — 어떻게 빠져나갔나",
            f"그리고 {cn}{_j(cn,'은/는')} 빠져나갈 길을 이미 만들어 두었다. {tr_name}. "
            + (tr_cond[0] if tr_cond else ""),
            f"[무엇을 보여 주는가] 이 컷은 **트릭의 원리**를 그림 하나로 설명한다. "
            f"플레이어가 게임 내내 궁금해한 '어떻게 알리바이가 성립했나'의 답이다. "
            f"[트릭] {tr_name} — {tr_desc[:150]} "
            f"[핵심 조건] {' / '.join(tr_cond[:2]) if tr_cond else ''} "
            f"[연출] 화면을 둘로 가르거나(좌: 사람들이 믿은 것 / 우: 실제로 있었던 일), "
            f"또는 같은 공간을 위에서 내려다본 도해처럼 그려 동선을 화살표 없이 빛의 길로 보여 준다. "
            f"[광원] {lit_ko}. 트릭의 열쇠가 되는 사물에만 빛을 모은다. "
            f"[카메라] 부감(위에서 내려다보기) 또는 분할 구도.",
            f"a diagrammatic reveal shot explaining the trick '{tr_name}': "
            f"split composition contrasting what witnesses believed with what actually happened, "
            f"or a high-angle overhead view of the location showing the culprit's true path, "
            f"the key object of the deception isolated in a pool of light, "
            f"clean graphic staging, high-angle or split-frame",
            "cues.reveal (주제 선율이 뒤집혀 돌아온다)",
            ["ui.audio.sfx.card_open", "event_cues.clue_decisive"], 8,
            camera="부감 또는 분할 구도",
            emotion="서늘한 납득 — '아, 그래서'",
            note="★신설 컷. 게임에서 가장 궁금했던 트릭의 원리를 여기서 그림으로 푼다. "
                 "얼굴보다 '구조'를 보여 주는 컷이라 인물은 작게 넣어도 된다"),

        cut(5, "위장",
            stage,
            f"[피사체] {cn}. 얼굴이 다시 보인다 — 방금 사람을 죽인 얼굴치고 너무 침착하다. "
            f"[행동] 쓰러진 {vic} 곁에서 현장을 꾸민다. 손끝이 정확하고 서두르지 않는다. "
            f"[소품] {feat_ko}{_j(feat_ko,'을/를')} 제자리에 놓거나 옮긴다. 이 물건들이 나중에 단서가 된다. "
            f"[수위] 주검은 화면 가장자리에 일부만. 얼굴과 상처는 보이지 않는다. "
            f"[광원] {lit_ko}. 촛불이 흔들려 그림자가 함께 흔들린다. "
            f"[카메라] 손을 중심으로 한 중간 클로즈업, 인물 얼굴은 화면 위쪽.",
            f"the culprit calmly staging the scene, face visible and unsettlingly composed, "
            f"precise unhurried hands rearranging {feat_ko}, the victim only partially in frame at the edge, "
            f"no wounds visible, guttering candle making shadows sway, "
            f"medium close-up centered on the hands",
            "무음 → 저역 드론만", ["ui.audio.sfx.page_turn"], 7,
            camera="손 중심 중간 클로즈업",
            emotion="이상할 만큼 침착함 — 그래서 더 섬뜩하다"),

        cut(6, "그리고 아침",
            f"아침이 왔다. {place}의 문이 열리기 전까지, 아무도 몰랐다.",
            f"[피사체] 사람 없음. {place}만. "
            f"[구도] ★첫 장면(현장 일러스트)과 **똑같은 카메라 위치·화각**으로 그린다. "
            f"플레이어가 '아, 그 방이다'를 알아보는 것이 이 컷의 전부다. "
            f"[상태] 밤의 흔적이 그대로 남아 있다 — {feat_ko}. 다만 빛만 바뀌었다. "
            f"[광원] 차고 맑은 아침 빛. 밤의 등불은 꺼져 있다. "
            f"[카메라] 현장 일러스트와 동일. 움직이지 않는다.",
            f"the exact same view of {place} as the original crime scene illustration, "
            f"identical camera position and focal length, now empty of people, "
            f"cold clear morning light replacing the night lantern, "
            f"the night's traces still in place ({feat_ko}), still and silent",
            "cues.ending 으로 넘어간다", ["ui.audio.sfx.blood_wipe"], 6,
            camera="첫 현장 일러스트와 동일 구도(고정)",
            emotion="정적 — 아무 일도 없었던 것처럼",
            note="현장 일러스트와 같은 구도로 — 플레이어가 '아, 그 방'을 알아보게"),
    ]
    return {
        "note": "지목·진상 낭독이 끝난 뒤, 범인이 실제로 죽이던 그 밤을 재연한다. "
                "게임 중 금지였던 범인 얼굴이 여기서 처음 공개된다.",
        "when": "reveal_sequence가 끝난 직후, 엔딩 등급 화면 직전",
        "skip": "건너뛸 수 없다 — 이 장면이 보상이다",
        "culprit": cul["id"], "culprit_name": cn,
        "cuts": cuts,
        "total_sec": sum(c["duration_sec"] for c in cuts),
        "art_note": f"컷 6장 · {PAGE_IMG[0]}×{PAGE_IMG[1]} · "
                    f"2·3컷만 얼굴 감춤(실루엣), 나머지는 얼굴 공개 · "
                    f"4컷(트릭)은 인물보다 구조를 보여 주는 도해형 컷",
        "continuity": CONT,
        "look": {"culprit_ko": look_ko, "culprit_en": face_en,
                 "lighting_ko": lit_ko, "lighting_en": lit_en,
                 "place_props": feats},
        "sfx_spec": {"name": sfx_name, "prompt_en": sfx_en},
    }


# ── 카드들 ────────────────────────────────────────────────────────────
def _finder(s, pn):
    """발견자 — 그 시각 현장 가까이 있던 사람 중 범인이 아닌 이."""
    d = s["death"]
    for c in s["cast"]:
        if c.get("is_culprit"):
            continue
        if (c.get("timeline") or {}).get(d["time_slot"]) == d["place"]:
            return c["name"]
    for key in ("집사", "하녀", "하인", "시종", "종", "머슴", "관리인"):
        for c in s["cast"]:
            if key in (c.get("public") or "") or key in c["name"]:
                return c["name"]
    # ★배경을 가리지 않는 말로 (2026-08-25). 예전 기본값이 "성의 사람들"이라
    #   현대 사무실·대학 배경 편에서도 성이 나왔다.
    return "그 자리에 있던 사람들" if s["cast"] else "발견자 미상"


def _victim_card(s, pn):
    d = s["death"]
    return {
        "header": "VICTIM",
        "name": s["victim"]["name"],
        "fields": [
            {"label": "신분", "value": s["victim"].get("role", "")},
            {"label": "발견 장소", "value": pn.get(d["place"], "")},
            {"label": "발견 시각", "value": d["time_slot"]},
            {"label": "사인", "value": "???", "hidden_value": d.get("weapon", ""),
             "reveal_when": "검험 단서를 확인하면 채워진다"},
            {"label": "발견자", "value": _finder(s, pn)},
        ],
        "summary": d.get("scene_description", ""),
        "bio_short": (s["victim"].get("bio") or "").split(". ")[0] + ".",
        "body_art": {
            "w": SCENE_IMG[0], "h": SCENE_IMG[1],
            "prompt_ko": f"{pn.get(d['place'],'')}에 엎드려 쓰러진 {s['victim']['name']}. "
                         f"{d.get('scene_description','')}",
            "prompt_en": "the victim lying face-down on the floor, seen from a low three-quarter "
                         "angle, period-accurate clothing, blood implied not shown in detail, "
                         "candlelit, painterly, no text, 1045x600 landscape",
            "rule": "얼굴은 보이지 않게 엎드린 자세. 상처 방향이 읽혀야 하되 잔혹하지 않게.",
            "must_show": ["주검의 자세", "사라진 물건의 빈자리"],
            "must_not_show": ["범인을 특정할 수 있는 옷·장신구"],
        },
        "portrait": {
            "w": PORTRAIT[0], "h": PORTRAIT[1],
            "photo": s["victim"].get("photo"),
            "prompt_ko": f"{s['victim']['name']} — {s['victim'].get('role','')}. 생전의 초상.",
            "prompt_en": "posthumous portrait framed in black, period-accurate, "
                         "dignified, muted palette, waist-up",
            "rule": "주검 자체는 그리지 않는다. 생전의 얼굴만 쓴다.",
        },
    }


def _alibi_line(c, s, pn):
    """카드에 올릴 알리바이 한 마디 — 본인 말투로."""
    a = (c.get("alibi_narration") or "").strip()
    if a:
        return re.split(r"(?<=[.?!])\s+", a)[0]
    tl = c.get("timeline") or {}
    slot = s["death"]["time_slot"]
    place = pn.get(tl.get(slot), "")
    end = ((c.get("persona") or {}).get("voice") or {}).get("endings") or ["-습니다"]
    tail = str(end[0]).lstrip("-")
    return f"그날 {slot}에는 {place}에 있었{tail if tail.startswith(('습','소','오')) else '습니다'}"


def _suspect_cards(s, pn):
    out = []
    for c in s["cast"]:
        pr = c.get("profile") or {}
        ap = c.get("appearance") or {}
        vs = c.get("voice_spec") or {}
        rel_short = (pr.get("relation") or "").strip()
        if not rel_short or len(rel_short) < 2:
            rel = str((c.get("relationships") or {}).get("victim") or "")
            m = re.search(r"[.!?]\s*(.{6,44}?)[.!?]", rel)
            rel_short = (m.group(1) if m else (c.get("public") or "")).strip()
        rel_short = f"{rel_short} — {c.get('public','')}" if c.get("public") and len(rel_short) < 14 else rel_short
        out.append({
            "id": c["id"], "name": c["name"],
            "list_sub": c.get("public", ""),
            "fields": [
                {"label": "신분", "value": pr.get("status") or c.get("public", "")},
                {"label": "나이", "value": pr.get("age", "")},
                {"label": "관계", "value": rel_short},
            ],
            "alibi_quote": f"“{_alibi_line(c, s, pn)}”",
            "alibi_label": "알리바이",
            "portrait": {
                "w": PORTRAIT[0], "h": PORTRAIT[1],
                "standing_w": STANDING[0], "standing_h": STANDING[1],
                "photo": c.get("photo"),      # 실존 인물 시연용 — 있으면 생성 대신 이 사진을 쓴다
                "prompt_ko": ap.get("prompt_ko", ""), "prompt_en": ap.get("prompt_en", ""),
                "expressions": {
                    "calm": ap.get("resting_expression", ""),
                    "shaken": ap.get("under_pressure", ""),
                    "broken": "고개를 떨구고 눈을 감는다",
                },
                "standing_prompt_en": (ap.get("prompt_en", "") or "").replace(
                    "waist-up", "full body, standing, facing the viewer"),
            },
            "voice": {"summary": vs.get("gender_age", ""), "prompt_en": vs.get("prompt_en", "")},
            "theme": f"character_themes.{c['id']}",
            "memo_placeholder": f"{c['name']}에 대한\n메모를 작성해 보세요.",
        })
    return out


def _clue_cards(s, pn):
    owner = {p["id"]: p.get("owner") for p in s["map"]["places"]}
    cname = {c["id"]: c["name"] for c in s["cast"]}
    used = {}
    out = []
    for cl in s["clue_graph"]:
        loc = cl.get("location") or s["death"]["place"]
        place = pn.get(loc, "")
        if cl.get("channel") == "crime_scene":
            how = "사건 시작 시 공개"
        elif owner.get(loc) and owner[loc] in cname:
            how = f"{cname[owner[loc]]} 심문 후 {place} 탐색으로 획득"
        else:
            how = f"{place} 탐색으로 획득"
        surf = re.sub(r"^\s*【[^】]*】\s*", "", cl.get("surface", "")).strip()
        head = re.split(r"(?<=[.?!])\s+", surf)[0]
        nm = _clue_name(cl, place, _kind(cl))
        if nm in used:                      # 같은 이름이 둘이면 못 알아본다
            who = next((n for n in cname.values() if n in cl.get("surface", "")), "")
            pre = who or (place if place and place not in nm else "")
            cand = f"{pre} {nm}".strip() if pre else nm
            n2, k = cand, 2
            while n2 in used:
                n2 = f"{cand} {k}"; k += 1
            nm = n2
        used[nm] = cl["id"]
        out.append({
            "id": cl["id"],
            "name": nm,
            "list_sub": (head[:28] + "…") if len(head) > 28 else head,
            "fields": [
                {"label": "종류", "value": _kind(cl)},
                {"label": "획득 장소", "value": place},
                {"label": "획득 방법", "value": how},
            ],
            "description": f"{surf}\n{place}에서 확인되었다.",
            "thumb": {"w": THUMB[0], "h": THUMB[1],
                      "prompt_ko": f"{nm} — {head}",
                      "prompt_en": f"single object study of {nm}, dark background, "
                                   f"museum-catalogue lighting, period-accurate, no text"},
            "decisive": bool(cl.get("decisive")),
            "round": cl.get("reveal_round", 1),
            "memo_placeholder": "증거물에 대한\n메모를 작성해 보세요.",
            "sfx_on_open": ("ui.audio.sfx.card_open" if not cl.get("decisive")
                            else "event_cues.clue_decisive"),
        })
    return out


# ── 장소 조사 화면 ────────────────────────────────────────────────────
def _place_screens(s, pn):
    rounds = (s.get("config") or {}).get("rounds", 3)
    layers = ((s.get("place_layers") or {}).get("layers") or {})
    owner = {p["id"]: p.get("owner") for p in s["map"]["places"]}
    cname = {c["id"]: c["name"] for c in s["cast"]}
    # 현장 검안은 시작할 때 그냥 준다 — 뒤져서 나오는 것이 아니다
    # ★spine을 뺐다 (2026-08-25).
    #   엔진은 라운드가 열리면 spine(증언)을 **저절로 지급**한다. 그런데 장소
    #   화면에도 같은 단서를 놓아 두어서, 이미 손에 든 것을 찾겠다고 예산을
    #   쓰는 일이 생겼다(91편 K5·K6·K7·K9). 얻는 길은 하나씩만 있어야 한다.
    #       자동 지급 : spine · crime_scene
    #       장소 탐색 : location · record · physical
    #       심문 실토 : belongings
    #       수첩 조합 : clue_combos
    SEARCHABLE = ("location", "record", "physical")
    by_place = {}
    for cl in s["clue_graph"]:
        if cl.get("channel") not in SEARCHABLE:
            continue
        loc = cl.get("location") or s["death"]["place"]
        by_place.setdefault(loc, []).append(cl)
    # 한 장소에 여러 개가 몰리면 라운드를 나눠 준다.
    #  ★2026-08-25 두 가지를 고쳤다.
    #    (1) 자리가 없으면 break로 **단서를 통째로 버렸다** — 전 편에서 32개가 고아가 됐다.
    #        (그 단서는 clue_graph에 있는데 게임에서 얻을 길이 없었다.)
    #    (2) 밀어내다 보니 **공개 라운드보다 늦게** 찾게 되는 것이 9개 있었다.
    #        1라운드에 공개된 단서를 2라운드에야 주울 수 있으면 앞뒤가 안 맞는다.
    #    → 한 장소·라운드에 **여러 개**를 둘 수 있게 하고(선택지 4개 중 앞자리부터),
    #      공개 라운드보다 늦게 밀지 않는다.
    #    → 한 장소·라운드에 **여러 개**를 둘 수 있게 하고, 단서는 **제 공개 라운드에 그대로** 둔다.
    #      밀어내기를 아예 없앴다 — 밀어내는 순간 공개 라운드와 어긋난다.
    hit_at = {}                       # (loc, r) -> [clue, ...]
    for loc, cls in by_place.items():
        cls.sort(key=lambda c: (c.get("reveal_round") or 1, c["id"]))
        for c in cls:
            r = min(max(c.get("reveal_round") or 1, 1), rounds)
            hit_at.setdefault((loc, r), []).append(c)

    out = []
    for p in s["map"]["places"]:
        pid = p["id"]
        lay = layers.get(pid) or p.get("features") or []
        rd = {}
        for r in range(1, rounds + 1):
            hits = hit_at.get((pid, r)) or []
            focus = lay[(r - 1) % len(lay)] if lay else p.get("desc", "")
            # ★단서가 걸린 자리에는 **그 단서의 물건 이름**을 쓴다.
            #   나머지 자리만 장소 묘사에서 끌어온다.
            n_slots = max(4, len(hits) + 1)
            objs = [None] * n_slots
            for i, h in enumerate(hits[:n_slots]):
                objs[i] = _clue_obj(h)
            pool = _nouns(" ".join([p.get("desc", "")] + list(p.get("features") or [])), 8)
            fillers = [_obj(focus, bare=True)] + list(pool) + [g for g, _v in GENERIC]
            fi = 0
            for i in range(n_slots):
                if objs[i]:
                    continue
                while fi < len(fillers) and fillers[fi] in objs:
                    fi += 1
                objs[i] = fillers[fi] if fi < len(fillers) else f"구석 {i + 1}"
                fi += 1
            acts = []
            for i, o in enumerate(objs):
                verb = ("둘러본다" if o == "방 전체" else
                        "들어 본다" if _HEARSAY.search(o) else VERBS[(i + r) % len(VERBS)])
                past = VERBS_PAST.get(verb, "들어 봤다" if verb == "들어 본다"
                                      else ("살펴봤다" if verb != "둘러본다" else "둘러봤다"))
                hit = hits[i] if i < len(hits) else None
                is_hit = hit is not None
                lines = [f"{o}{_j(o)} {past}.",
                         f"{o}{_j(o,'은/는')} {CALM[(i + r) % len(CALM)]}"]
                if is_hit:
                    lines.append(f"그런데 {_anomaly(hit)}.")
                    lines.append("새로운 단서를 발견했다.")
                else:
                    lines.append(NOTHING[(i + r) % len(NOTHING)])
                acts.append({
                    "label": f"{o}{_j(o)} {verb}" if o != "방 전체" else "방 전체를 둘러본다",
                    "result_lines": lines,
                    "highlight_last": is_hit,
                    "finds": hit["id"] if is_hit else None,
                    "button": "단서 보기" if is_hit else "계속 조사",
                    "sfx": (["event_cues.search_hit", "event_cues.clue_found",
                             "ui.audio.sfx.counter_up"] if is_hit
                            else ["event_cues.search_miss"]),
                })
            rd[str(r)] = {"layer_note": focus, "actions": acts,
                          "counter": "발견한 단서 {found} / ?"}
        ow = cname.get(owner.get(pid))
        out.append({
            "place_id": pid, "title": p["name"],
            "back": "← 지도", "notebook": "사건수첩",
            "bgm": f"place_cues.{pid}",
            "bgm_rule": "살인 전/후 두 벌. 사건 뒤에는 post_murder로 바꾼다.",
            "standing_character": ow,
            "standing_cast_id": owner.get(pid),
            "standing_note": (f"{ow}의 서 있는 그림을 왼쪽에 둔다." if ow
                              else "주인 없는 장소 — 왼쪽은 비워 둔다."),
            # 심문 진입 — 이 장소를 눌렀을 때 누구와 대화할 수 있는가
            "talk": ({"cast_id": owner.get(pid), "name": ow,
                      "label": f"{ow}에게 묻는다",
                      "note": "이 장소의 주인이다. 여기서 심문에 들어간다."}
                     if ow else
                     {"cast_id": None, "name": None, "label": None,
                      "note": "주인 없는 장소 — 심문 진입 없음. 조사만 한다."}),
            "art": {"w": PLACE_IMG[0], "h": PLACE_IMG[1],
                    "prompt_ko": p.get("desc", ""),
                    "prompt_en": f"interior of {p['name']}, period-accurate, "
                                 f"candlelit, painterly, no people, no text, 1045x600 landscape"},
            "map_thumb": {"w": MAP_THUMB[0], "h": MAP_THUMB[1],
                          "prompt_ko": f"{p['name']} — 지도에 박을 작은 그림. {p.get('desc','')[:40]}",
                          "prompt_en": f"small map icon illustration of {p['name']}, "
                                       f"simplified, dark background, no text, 320x200"},
            "standing_size": {"w": STANDING[0], "h": STANDING[1]},
            "rounds": rd,
        })
    return out


# ── HUD · 수첩 · 알림 ─────────────────────────────────────────────────
def _hud(s, pn):
    d = s["death"]
    cfg = s.get("config") or {}
    return {
        "copy": {
            "case_title": f"{s['meta'].get('origin','')} 살인사건",
            "round": "ROUND {r} / " + str(cfg.get("rounds", 3)),
            "lives": "남은 생명 {n}",
            "settings": "설정",
            "nav": ["지도", "용의자", "사건수첩", "대질", "범인 지목"],
            "summary_title": "사건 개요",
            "summary_text": (s.get("intro") or {}).get("twist", "")
                            or d.get("scene_description", ""),
            "round_banner": "{r}라운드 — {focus}",
            "round_focus": ["동선을 판다", "관계를 판다", "비밀을 판다", "마지막으로 확인한다"],
            "time_up": "이 라운드가 끝났습니다.",
        },
        "summary_fields": [
            {"label": "피해자", "value": s["victim"]["name"]},
            {"label": "장소", "value": pn.get(d["place"], "")},
            {"label": "발견 시각", "value": d["time_slot"]},
            {"label": "발견자", "value": _finder(s, pn)},
        ],
        "elements": ["사건 제목", "라운드 표시", "남은 생명", "설정",
                     "사건 개요 패널", "하단 내비 5개(지도·용의자·사건수첩·대질·범인 지목)"],
    }


def _notebook():
    return {
        "title": "사건수첩",
        "tabs": ["단서", "메모"],
        "back": "← 돌아가기", "settings": "설정",
        # ★수첩에서 **인물 탭을 뺐다** (2026-08-25).
        #   수첩은 단서를 모아 두는 곳이다. 여기에 인물 목록과 압박 게이지까지
        #   얹으니 수첩이 아니라 상태창이 됐다.
        #   인물은 하단 내비의 [용의자]에서 본다 — 알리바이도 거기 있다.
        "clue_tab": {"list_hint": "단서를 골라 자세히 봅니다.",
                     "detail_sections": ["그림", "종류·획득 장소·획득 방법", "설명"],
                     "desc_label": "설명",
                     "empty": "아직 찾은 단서가 없습니다.",
                     # ★얻는 순간 **자동으로** 적힌다 (2026-08-25).
                     #   플레이어가 단서를 다시 보려고 그 장소에 또 들어가는 일이
                     #   없어야 한다. 들어가는 데도 예산이 들기 때문이다.
                     "auto_record": {
                         "when": "단서를 얻는 모든 순간 — 장소 탐색·심문 실토·"
                                 "라운드 전환 자동 지급·수첩 조합·대질",
                         "what": "단서 **본문 그대로**(surface)와 종류·획득 장소·"
                                 "획득 방법. 그림이 있으면 함께.",
                         "never": "★추리는 적지 않는다. 이 단서가 누구를 가리키는지"
                                  "(points_to), 무엇을 뜻하는지(implies)는 "
                                  "**절대 수첩에 쓰지 않는다** — 그것을 알아내는 것이 게임이다.",
                         "revisit": "한 번 적힌 단서는 그 장소에 다시 가지 않아도 "
                                    "언제든 여기서 전문을 다시 읽을 수 있다. 예산 0.",
                         "order": "얻은 순서. 라운드 구분선을 넣는다.",
                         "memo": "단서마다 플레이어가 직접 쓰는 메모 칸이 따로 있다 — "
                                 "추리는 여기에만 쌓인다.",
                     }},
        "memo_tab": {
            "title": "메모를 작성하세요",
            "guide": ["이곳에는 인물이나 단서에 구애받지 않고 자유롭게 메모를 작성할 수 있습니다.",
                      "떠오른 생각이나 의문점, 추론, 계획 등을 기록해 보세요.",
                      "여러분의 기록이 진실에 가까워질 단서를 남길 수도 있습니다."],
            "placeholder": "여기에 적습니다.",
            "autosave": "적는 대로 저장됩니다.",
        },
        "sfx": {"open": "ui.audio.sfx.notebook_open", "close": "ui.audio.sfx.notebook_close",
                "tab": "ui.audio.sfx.tab_switch", "page": "ui.audio.sfx.page_turn",
                "write": "ui.audio.sfx.memo_write"},
    }


def _toasts():
    return [
        {"id": "clue_new", "title": "새로운 단서가 제시되었습니다.",
         "body": "{clue_name}", "footer": "사건수첩에서 확인해 보세요.",
         "icon": "돋보기", "sfx": "ui.audio.sfx.toast_in", "bgm_duck": True,
         "highlight": "clue_name"},
        {"id": "clue_decisive", "title": "결정적인 단서를 찾았습니다.",
         "body": "{clue_name}", "footer": "이것이 사건을 가릅니다.",
         "icon": "돋보기", "sfx": "event_cues.clue_decisive", "bgm_duck": True},
        {"id": "round_start", "title": "{r}라운드가 시작됩니다.",
         "body": "{focus}", "footer": "", "sfx": "event_cues.round_start"},
        # ★이벤트 토스트는 **그 이벤트에 맞는 말**을 쓴다 (2026-08-25).
        #   여섯 종류 전부에 "판이 뒤집힙니다."를 붙여 두었더니, 무슨 일이
        #   벌어졌는지는 안 알려주면서 호들갑만 떠는 문구가 됐다.
        #   title은 kind로 고르고, 본문에 실제로 일어난 일을 적는다.
        {"id": "event", "title": "{event_title}",
         "body": "{event_text}", "footer": "", "sfx": "event_cues.event_sting",
         "titles_by_kind": {
             "새증언":   "누군가 입을 열었습니다.",
             "두번째사건": "또 한 번 소동이 있었습니다.",
             "인물이탈":  "자리를 비운 사람이 있습니다.",
             "외부개입":  "밖에서 기별이 왔습니다.",
             "증거소실":  "있던 것이 없어졌습니다.",
             "자백번복":  "앞서 한 말이 뒤집혔습니다.",
         },
         "fallback_title": "무언가 달라졌습니다.",
         "note": "events[].kind로 titles_by_kind에서 고른다. 없으면 fallback_title."},
        {"id": "secret_open", "title": "비밀이 드러났습니다.",
         "body": "{cast_name} — {secret}", "footer": "", "sfx": "event_cues.secret_open"},
        {"id": "life_lost", "title": "지목에 실패했습니다.",
         "body": "남은 생명 {n}", "footer": "", "sfx": "event_cues.life_lost"},
        {"id": "exculpated", "title": "혐의를 벗었습니다.",
         "body": "{cast_name}", "footer": "용의자 목록에서 흐리게 표시됩니다.",
         "sfx": "ui.audio.sfx.page_turn"},
    ]


# ── 조립 ──────────────────────────────────────────────────────────────
def build(s):
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    pal = (s.get("bgm") or {}).get("palette") or {}
    theme = (s.get("bgm") or {}).get("main_theme") or {}
    title = s["meta"]["title"]
    hud = _hud(s, pn)
    music = _ui_music(pal, title, theme)
    pal = dict(pal); pal["_weapon_class"] = s["death"].get("weapon_class", "")
    sfx = _sfx_lib(pal, title)
    ui = {
        "_note": "화면에 실제로 뜨는 글자와, 화면마다 붙는 소리. "
                 "bgm.* 를 가리키는 값은 그 시나리오의 곡 id다.",
        "audio": {"music": music, "sfx": sfx,
                  "rule": "화면이 바뀌면 곡은 1.2초 크로스페이드. 효과음은 곡 위에 그대로 얹는다. "
                          "알림이 뜨는 동안 곡을 -6dB 낮춘다(bgm_duck)."},
        "screens": _screens(s, pn, hud),
        "narration": _narration(s, pal),
        "reveal_sequence": _reveal(s, pn),
        # 누구를 어디서 만날 수 있는가 — 프론트가 진입 경로를 그릴 때 쓴다
        "cast_access": _cast_access(s, pn),
        "murder_reenactment": _reenactment(s, pn),
        "victim_card": _victim_card(s, pn),
        "suspect_cards": _suspect_cards(s, pn),
        "clue_cards": _clue_cards(s, pn),
        "place_screens": _place_screens(s, pn),
        "hud": hud,
        "notebook": _notebook(),
        "toasts": _toasts(),
    }
    ui["art_specs"] = _art_specs(s, ui)
    # 음악 목록에 화면용도 얹어 준다 — 팀은 이 한 장만 보면 된다
    ms = (s.get("bgm") or {}).get("music_scenes")
    if isinstance(ms, list):
        ms[:] = [x for x in ms if not str(x.get("slot", "")).startswith(("ui:", "uisfx:"))]
        for k, v in music.items():
            ms.append({"slot": f"ui:{k}", "name": v["name"], "when": v["when"],
                       "kind": "music", "prompt_en": v["prompt_en"]})
        for k, v in sfx.items():
            ms.append({"slot": f"uisfx:{k}", "name": v["name"], "when": v["when"],
                       "kind": "sfx", "prompt_en": v["prompt_en"]})
    s["ui"] = ui
    sc = s.setdefault("_schema", {})
    if isinstance(sc, dict):
        sc["ui"] = "v1"
    return s


def _art_specs(s, u):
    """그림을 몇 장, 어떤 규격으로 그려야 하는가 — 제작 체크리스트."""
    n = u["narration"]
    rows = [
        dict(kind="스토리 삽화", n=n["image_count"], w=PAGE_IMG[0], h=PAGE_IMG[1],
             where="나레이션 쪽마다 한 장", note="밝게 → 사건 쪽에서 색이 식는다"),
        dict(kind="주검 그림", n=1, w=SCENE_IMG[0], h=SCENE_IMG[1],
             where="현장·피해자 카드", note="엎드려 쓰러진 자세, 얼굴 안 보이게"),
        dict(kind="현장 전경", n=1, w=SCENE_IMG[0], h=SCENE_IMG[1],
             where="현장 일러스트", note="범인 특정 요소 금지"),
        dict(kind="장소 배경", n=len(u["place_screens"]), w=PLACE_IMG[0], h=PLACE_IMG[1],
             where="장소 조사 화면", note="사람 없이"),
        dict(kind="지도 썸네일", n=len(u["place_screens"]), w=MAP_THUMB[0], h=MAP_THUMB[1],
             where="지도", note="장소마다 작은 그림"),
        dict(kind="인물 초상", n=len(u["suspect_cards"]) + 1, w=PORTRAIT[0], h=PORTRAIT[1],
             where="용의자 카드·수첩·심문", note="표정 3단(평정·흔들림·무너짐) 각각"),
        dict(kind="인물 전신", n=sum(1 for p in u["place_screens"] if p["standing_character"]),
             w=STANDING[0], h=STANDING[1], where="장소 조사 화면 왼쪽", note="주인 있는 장소만"),
        dict(kind="단서 썸네일", n=len(u["clue_cards"]), w=THUMB[0], h=THUMB[1],
             where="수첩 단서 탭", note="검은 배경 물건 단품"),
        dict(kind="재연 컷", n=len(((u.get("murder_reenactment") or {}).get("cuts")) or []),
             w=PAGE_IMG[0], h=PAGE_IMG[1], where="엔딩 — 범행 재연",
             note="범인 얼굴 공개. 범행 컷만 실루엣"),
    ]
    total = sum(r["n"] for r in rows) + len(u["suspect_cards"]) * 2  # 표정 2단 추가분
    return {"note": "이 편을 다 그리려면 아래만큼 필요하다.", "rows": rows, "total": total}


def report(s):
    u = s["ui"]
    acts = sum(len(r["actions"]) for p in u["place_screens"] for r in p["rounds"].values())
    return (f"{s['meta']['title'][:14]:16} 화면 {len(u['screens']):2} · "
            f"나레이션 {u['narration']['page_count']}쪽(영상 {len(u['narration']['video_pages'])}) · "
            f"용의자카드 {len(u['suspect_cards'])} · 단서카드 {len(u['clue_cards']):2} · "
            f"장소화면 {len(u['place_screens'])}(선택지 {acts:3}) · "
            f"UI곡 {len(u['audio']['music'])} · UI효과음 {len(u['audio']['sfx'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    paths = a.paths or (sorted(glob.glob("scenarios/[0-9]*.json")) if a.all else [])
    if not paths:
        print("사용: python ui.py out/13_푸른수염.json   또는   python ui.py --all")
        return
    ok = 0
    for p in paths:
        try:
            s = json.load(open(p, encoding="utf-8"))
            build(s)
            json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            ok += 1
            if a.report or len(paths) == 1:
                print(report(s))
        except Exception as e:
            print(f"  ✗ {os.path.basename(p)}: {type(e).__name__} {e}")
    print(f"\nui 붙임 {ok}/{len(paths)}편")


if __name__ == "__main__":
    main()
