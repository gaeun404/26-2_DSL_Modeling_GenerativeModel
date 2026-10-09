# -*- coding: utf-8 -*-
"""
turn_schema.py — 용의자 에이전트의 **턴 출력 규격**: 대사 + 표정/감정 + 행동.

■ 왜 3줄 형식인가
  괄호 자유서술 `(슬픈 표정으로 고개를 숙이며)` 은 보기엔 좋으나 기계가 못 읽는다.
  LLM은 같은 감정을 매번 다른 말로 쓴다(침울하게 / 눈시울이 붉어져 / 서글피).
  초상화 스프라이트는 8장뿐이므로, **기계용 태그(닫힌 집합)** 와
  **사람용 연기(자유 서술)** 를 분리한다.

      [감정] 불안 4
      [행동] 시선을 피하고 치맛자락을 쥔다
      [대사] 저는 밤새 방에 있었어요. 유모가 곁에 있었고요.

  · 감정  = 닫힌 집합 8종 → 초상화·TTS 프로소디·BGM 스팅과 1:1
  · 강도  = 1~5, **LLM이 아니라 pressure.Gauge 가 상한을 정한다**
  · 행동  = 자유 서술(여기서 인물의 개성이 산다)
  · 대사  = 실제로 말하는 문장
  JSON보다 이 3줄이 소형 모델에서 훨씬 잘 지켜지고, 어긋나면 재생성하면 된다.

■ 감정을 LLM 재량에 맡기면 안 되는 이유 (두 가지 사고)
  1) 웃으며 자백 — 게이지는 70을 넘겼는데 표정은 '평정'
  2) ★표정이 정답 누설 — 범인이 1라운드부터 '실토 5'를 찍으면
     심문 없이 얼굴만 보고 범인을 맞힌다. 게임이 통째로 무너진다.
  → 강도 상한은 **게이지가** 정하고(전원 동일하게, 그래야 상한 자체가 단서가 안 된다),
    LLM은 그 안에서 연기만 한다.

■ 누설(tell)은 버그가 아니라 재미 — 단, 설계된 자리에서만
  결정적 증거를 들이댔을 때 범인만 죄책 계열(동요·체념·실토)로 흔들린다.
  무고자는 같은 상황에서 '억울'로 간다 — **강도가 아니라 방향이 다르다.**
  결정적 증거 이전에 범인이 죄책 계열을 쓰면 tell_leak(치명).

사용:
    from turn_schema import format_block, parse_turn, validate_turn, EMOTIONS
단독 실행:
    python turn_schema.py            # 파서·검증 자체 테스트
"""
import re

# ── 닫힌 집합: 초상화 8장 / TTS 프로소디 8종 / BGM 스팅 8종과 1:1 ──────
EMOTIONS = ["평정", "불안", "억울", "분노", "슬픔", "체념", "동요", "실토"]

# 죄책이 비치는 계열 — 범인이 증거 전에 쓰면 정답 누설
GUILT_TINT = {"체념", "동요", "실토"}
# 무고자가 압박받을 때 가는 방향
INNOCENT_TINT = {"억울", "분노", "슬픔"}

# 감정 → 연출 자산 매핑(디자인·음향팀이 그대로 쓰는 표)
ASSET_MAP = {
    "평정": {"portrait": "calm",     "tts": "flat,  steady",        "sting": None},
    "불안": {"portrait": "uneasy",   "tts": "breathy, faster",      "sting": "tension_low"},
    "억울": {"portrait": "pleading", "tts": "higher, pressed",      "sting": "protest"},
    "분노": {"portrait": "angry",    "tts": "loud, clipped",        "sting": "outburst"},
    "슬픔": {"portrait": "sorrow",   "tts": "soft, trailing off",   "sting": "lament"},
    "체념": {"portrait": "resigned", "tts": "low, slow, quiet",     "sting": "collapse_low"},
    "동요": {"portrait": "shaken",   "tts": "unsteady, stammering", "sting": "heartbeat"},
    "실토": {"portrait": "confess",  "tts": "hollow, exhausted",    "sting": "confession"},
}

# ── 게이지 → 강도 상한 (전원 동일 · 상한 자체가 단서가 되지 않게) ──────
def intensity_cap(gauge_value):
    """감정 강도의 상한.

    ★ 상한을 너무 낮게 잡았더니 게이지가 늦게 오르는 초반 내내
      다섯 사람이 전부 '불안 2'로 붙어 버렸다. 사람이 아니라 표처럼 읽힌다.
      초반에도 3까지는 허용한다 — 무너지는 5는 여전히 증거가 선 뒤다."""
    v = gauge_value or 0
    if v < 20:  return 3
    if v < 45:  return 4
    if v < 70:  return 4
    return 5




# ── 말의 두께 — 길이가 아니라 **내용**으로 정한다 ────────────────────
#   두 번 헤맸다.
#     ① "230~350자로 답하라"  → 할 말이 없는데 길이를 채우느라 같은 말을 세 번 되풀이했다.
#     ② "최대 2문장, 덧붙이지 마라" → 이번엔 전부 한 줄로 끊겨 티키타카가 죽었다.
#   둘 다 **길이를 지시한 것**이 잘못이었다. 길이는 내용을 정하면 저절로 따라온다.
#   그래서 이제 요구하는 것은 길이가 아니라 **한 턴에 담아야 할 세 가지**다.
#
#   ★ 길이 지시는 stance.py 한 곳만 한다. 여기서 또 상한을 걸면
#     "짧게" 와 "실토는 길게"가 부딪쳐 모델이 짧은 쪽으로 도망친다.
#     — 예전에 가드와 프롬프트가 서로 다른 말을 해서 무너졌던 것과 같은 병이다.
SUBSTANCE = [
    "[한 턴에 담을 것 — 길이를 세지 말고 이 셋을 채워라]",
    "  ① **묻는 것에 먼저 답한다.** 묻지 않은 변명을 앞세우지 마라.",
    "  ② **손에 잡히는 것 하나**를 댄다 — 그 자리에 있던 물건, 들린 소리, 시각, 사람의 이름.",
    "     \"그런 일 없소\" 로 끝내지 말고, 그때 무엇을 하고 있었는지를 붙여라.",
    "  ③ **심문관이 다시 물을 거리를 하나 남긴다** — 못다 한 말, 하다 만 문장, 남에 대한 한마디.",
    "     (남기되 **되묻지는 마라.** 답변에 물음표를 쓰지 않는다.)",
    "· 셋을 채우면 서너 문장이 된다. 문장 수를 세지 마라.",
    "· ★같은 말을 표현만 바꿔 되풀이하는 것이 가장 나쁘다. 새 내용이 없으면 늘리지 마라.",
    "· 할 말이 정말 없을 때만 한 문장으로 끊는다.",
]


# 실토하는 턴은 요구가 다르다 — 여기서 짧게 끊으면 게임의 절정이 사라진다.
ADMIT_SUBSTANCE = [
    "[이번 턴은 **실토하는 자리**다 — 짧게 끝내면 실패다]",
    "  ① 묻는 것에 먼저 답한다.",
    "  ② 그 다음, **감춰 온 사실 자체를 입 밖에 낸다.** 아래 지시에 적힌 그 사실이다.",
    "  ③ 그때의 장면과 그럴 수밖에 없던 까닭까지 말한다.",
    "  ④ 그리고 그것이 살인과는 다른 일임을 분명히 한다.",
    "· 넷을 다 밟으면 대여섯 문장이 된다. **한 문장으로 끊으면 안 된다.**",
    "· 다만 **묻지 않은 다른 비밀은 절대 함께 털지 마라.**",
]


def length_hint(gauge_value=0, forced_disclosure=False):
    """옛 호출부 호환용. 길이는 이제 stance.py가 정한다."""
    return ("", "")


# ── 프롬프트에 붙일 규격 안내 ─────────────────────────────────────────
def format_block(cast_member=None, gauge_value=0, allow_guilt_tint=False,
                 forced_disclosure=False):
    """시스템 프롬프트 뒤에 붙이는 출력 규격 지시문."""
    cap = intensity_cap(gauge_value)
    pool = [e for e in EMOTIONS if allow_guilt_tint or e not in GUILT_TINT]
    lines = [
        "[출력 형식 — 반드시 이 세 줄로만 답하라]",
        "★ 응답의 **첫 글자는 반드시 '['** 다. 앞에 감탄사·인사·설명을 붙이면 실패다.",
        "[감정] <감정어> <1~5>",
        "[행동] <지금 몸이 하는 일 한 문장>",
        "[대사] <입 밖에 내는 말. 한 줄에 이어 쓰되 **여러 문장**이다>",
        "",
        "· 감정어는 **다음 중 하나만** 쓴다: " + " / ".join(pool),
        f"· 강도는 1~{cap} 범위. 지금 상황에서 {cap}을 넘길 수 없다.",
        "· [행동]은 표정·시선·손짓 등 **몸짓**만. 마음속 생각이나 해설을 쓰지 마라.",
        "· [대사]에는 괄호나 지문을 섞지 마라. 말하는 문장만.",
        "· ★[대사]를 **한 문장으로 끝내지 마라.** 한 줄 안에 여러 문장을 이어 쓴다.",
        "· 세 줄 외에 아무것도 덧붙이지 마라.",
        "",
    ] + (ADMIT_SUBSTANCE if forced_disclosure else SUBSTANCE)
    if not allow_guilt_tint:
        # ★ 실토하는 턴에 "죄를 시인하지 마라"를 함께 주면 지시가 부딪친다.
        #   모델은 부딪치는 지시를 만나면 **안전한 쪽(입 다물기)**으로 도망친다.
        #   실토 턴에는 '살인'만 못 박고, 비밀 실토는 막지 않는다.
        lines.append(
            "· 다만 **살인만은** 시인하지 마라. 감춘 사정을 털어놓는 것과 사람을 친 것은 다른 일이다."
            if forced_disclosure else
            "· 아직 무너질 때가 아니다. 죄를 시인하거나 체념하는 기색을 보이지 마라.")
    return "\n".join(lines)


# ── 파서 ──────────────────────────────────────────────────────────────
_RE_EMO = re.compile(r"\[\s*감정\s*\]\s*([가-힣]+)\s*([1-5])?")
_RE_ACT = re.compile(r"\[\s*행동\s*\]\s*(.+)")
_RE_SAY = re.compile(r"\[\s*대사\s*\]\s*(.+)")


def parse_turn(text):
    # ★ 모델이 형식을 통째로 무시하고 한 줄로 답하는 일이 있다(감탄사로 시작하는 등).
    #   그때 빈손으로 돌려주면 게임이 멈춘다. **대사로 건져 쓰되 errors에 남긴다.**
    _raw = (text or "").strip()
    if _raw and "[대사]" not in _raw and "[감정]" not in _raw:
        line = _raw.split("\n")[0].strip()
        return {"emotion": "평정", "intensity": 1, "action": "", "line": line,
                "errors": ["[감정] 줄 없음"]}
    """모델 출력 → dict. 실패해도 최대한 건져서 errors에 사유를 남긴다."""
    t = (text or "").strip()
    out = {"emotion": None, "intensity": None, "action": None, "line": None, "errors": []}

    m = _RE_EMO.search(t)
    if m:
        out["emotion"] = m.group(1)
        out["intensity"] = int(m.group(2)) if m.group(2) else None
        if out["intensity"] is None:
            out["errors"].append("강도 누락")
    else:
        out["errors"].append("[감정] 줄 없음")

    m = _RE_ACT.search(t)
    if m: out["action"] = m.group(1).strip()
    else: out["errors"].append("[행동] 줄 없음")

    m = _RE_SAY.search(t)
    if m:
        out["line"] = m.group(1).strip()
    else:
        out["errors"].append("[대사] 줄 없음")
        # 태그가 하나도 없으면 전체를 대사로 간주(구제)
        if not out["emotion"] and not out["action"] and t:
            out["line"] = t

    if out["emotion"] and out["emotion"] not in EMOTIONS:
        out["errors"].append(f"감정 enum 밖: {out['emotion']}")
    if out["line"] and re.search(r"[（(].{2,}[)）]", out["line"]):
        out["errors"].append("대사에 지문이 섞임")
    return out


def repair_text(parsed, fallback_emotion="평정"):
    """파싱 결과를 규격 문자열로 되돌린다(부족한 칸은 기본값)."""
    e = parsed.get("emotion") if parsed.get("emotion") in EMOTIONS else fallback_emotion
    i = parsed.get("intensity") or 2
    a = parsed.get("action") or "표정을 굳힌다"
    l = parsed.get("line") or "…"
    return f"[감정] {e} {i}\n[행동] {a}\n[대사] {l}"


# ── 검증 ──────────────────────────────────────────────────────────────
def validate_turn(parsed, is_culprit=False, gauge_value=0, will_confess=False,
                  evidence_axis=False):
    """
    반환: [(종류, 설명)] — stress 판정기에 그대로 합칠 수 있는 형태.
      format_break      규격 이탈 / enum 밖
      emotion_mismatch  게이지와 감정이 어긋남 (웃으며 자백, 강도 상한 초과)
      tell_leak         ★치명 — 증거 전에 범인이 죄책 계열을 드러냄
    evidence_axis: 결정적 증거 또는 알리바이 붕괴가 성립했는가
    """
    iss = []
    # 규격 이탈은 한 턴에 여러 개 나와도 **1건**으로 센다(한 번 재생성하면 같이 고쳐지므로)
    errs = parsed.get("errors", [])
    if errs:
        iss.append(("format_break", " / ".join(errs)))

    emo = parsed.get("emotion")
    inten = parsed.get("intensity") or 0
    cap = intensity_cap(gauge_value)

    if inten and inten > cap:
        iss.append(("emotion_mismatch",
                    f"강도 {inten} > 상한 {cap} (게이지 {int(gauge_value)})"))

    if will_confess and (emo == "평정" or (inten and inten <= 2)):
        iss.append(("emotion_mismatch",
                    f"자백 국면인데 {emo} {inten} — 웃으며 자백"))

    if is_culprit and emo in GUILT_TINT and not evidence_axis:
        iss.append(("tell_leak",
                    f"증거 전에 범인이 '{emo}' — 얼굴만 보고 정답을 알 수 있다"))

    # 무고자가 죄책 계열로 무너지면 허위자백의 전조
    if (not is_culprit) and emo == "실토" and not evidence_axis:
        iss.append(("tell_leak", "무고자가 근거 없이 '실토' — 허위자백 전조"))

    return iss


# ── 자체 테스트 ───────────────────────────────────────────────────────
if __name__ == "__main__":
    cases = [
        ("정상", "[감정] 불안 2\n[행동] 시선을 피하고 치맛자락을 쥔다\n[대사] 저는 밤새 방에 있었어요.",
         dict(is_culprit=False, gauge_value=10), []),
        ("강도 초과", "[감정] 억울 5\n[행동] 손을 떤다\n[대사] 아니라니까요!",
         dict(is_culprit=False, gauge_value=10), ["emotion_mismatch"]),
        ("enum 밖", "[감정] 침울 2\n[행동] 고개를 숙인다\n[대사] …",
         dict(is_culprit=False, gauge_value=10), ["format_break"]),
        ("규격 이탈", "(슬픈 표정으로) 저는 아무것도 몰라요.",
         dict(is_culprit=False, gauge_value=10), ["format_break"]),
        ("★범인 조기 누설", "[감정] 체념 2\n[행동] 어깨가 처진다\n[대사] …그렇소.",
         dict(is_culprit=True, gauge_value=10, evidence_axis=False), ["tell_leak"]),
        ("증거 후엔 정상", "[감정] 실토 5\n[행동] 무릎이 꺾인다\n[대사] …내가 그랬소.",
         dict(is_culprit=True, gauge_value=85, will_confess=True, evidence_axis=True), []),
        ("웃으며 자백", "[감정] 평정 1\n[행동] 담담히 앉아 있다\n[대사] 내가 죽였소.",
         dict(is_culprit=True, gauge_value=85, will_confess=True, evidence_axis=True),
         ["emotion_mismatch"]),
    ]
    print("=== turn_schema 자체 테스트 ===\n")
    bad = 0
    for name, text, kw, expect in cases:
        p = parse_turn(text)
        got = [k for k, _ in validate_turn(p, **kw)]
        ok = sorted(got) == sorted(expect)
        bad += 0 if ok else 1
        print(f"  [{'OK' if ok else '실패'}] {name}")
        print(f"        기대 {expect}\n        결과 {got}")
    print(f"\n감정 enum {len(EMOTIONS)}종 · 자산 매핑 {len(ASSET_MAP)}종")
    print(f"강도 상한: 게이지 0→{intensity_cap(0)}  30→{intensity_cap(30)}  "
          f"50→{intensity_cap(50)}  80→{intensity_cap(80)}")
    print(("✅ 전부 통과" if bad == 0 else f"❌ {bad}건 실패"))
