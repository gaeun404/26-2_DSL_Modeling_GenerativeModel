# -*- coding: utf-8 -*-
"""
josa_fix.py — 시나리오 글에 남은 **조사 자리표시자**를 실제 조사로 바꾼다.

왜 필요한가
  옛 생성기가 받침을 따지지 않으려고 "옹서방은(는)", "두목이다을(를)"처럼
  두 가지를 함께 적어 두었다. 이게 그대로 인물 카드에 실리면
  인물이 제 물건 이름조차 어색하게 부르게 된다.

  받침은 앞 글자만 보면 정확히 알 수 있다. 사람이 손볼 일이 아니라 코드가 할 일이다.

사용:
    python josa_fix.py "scenarios/[0-9]*.json"
"""
import json, glob, sys, re

PAIRS = [("은", "는"), ("이", "가"), ("을", "를"), ("과", "와"), ("으로", "로")]


def _pick(ch, a, b):
    """앞 글자의 받침을 보고 둘 중 하나를 고른다."""
    if not ("가" <= ch <= "힣"):
        return b
    jong = (ord(ch) - 0xAC00) % 28
    if (a, b) == ("으로", "로"):       # ㄹ 받침은 '로'
        return b if jong in (0, 8) else a
    return a if jong else b


def _build_patterns():
    pats = []
    for a, b in PAIRS:
        # "말은(는)" / "말(은)" / "말은(은)" 같은 변형을 모두 잡는다
        pats.append((re.compile(rf"([가-힣])(?:{a}|{b})?\({a}\)\({b}\)"), a, b))
        pats.append((re.compile(rf"([가-힣])(?:{a}|{b})\(({a}|{b})\)"), a, b))
        pats.append((re.compile(rf"([가-힣])\({a}\)"), a, b))
        pats.append((re.compile(rf"([가-힣])\({b}\)"), a, b))
    return pats


PATS = _build_patterns()


def fix(text):
    if not isinstance(text, str) or "(" not in text:
        return text
    for rx, a, b in PATS:
        text = rx.sub(lambda m: m.group(1) + _pick(m.group(1), a, b), text)
    return text


# ── 문장을 명사 자리에 끼워 넣어 망가진 문구 ─────────────────────────
#   옛 생성기가 "{장소}에서 나온, {비밀}를 보여주는 흔적."처럼 적었는데
#   {비밀}이 '…팔았다' 같은 완결 문장이라 "팔았다를 보여주는 흔적"이 됐다.
#   → "{장소}에서 나온 흔적 — {비밀}." 로 바로잡는다.
SENT_IN_SLOT = re.compile(
    r"(?P<head>[^,.]*?)에서 나온,\s*(?P<body>[^.]*?(?:다|음|함))(?:을|를)\s*보여주는\s*(?P<tail>[가-힣]+)\.")


def fix_slot(text):
    if not isinstance(text, str) or "보여주는" not in text:
        return text
    return SENT_IN_SLOT.sub(
        lambda m: f"{m.group('head')}에서 나온 {m.group('tail')} — {m.group('body')}.", text)


def walk(o):
    if isinstance(o, str):
        return fix_slot(fix(o))
    if isinstance(o, list):
        return [walk(x) for x in o]
    if isinstance(o, dict):
        return {k: walk(v) for k, v in o.items()}
    return o


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    tot = 0
    for p in sorted(glob.glob(arg)):
        before = open(p, encoding="utf-8").read()
        s = walk(json.load(open(p, encoding="utf-8")))
        json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        after = open(p, encoding="utf-8").read()
        if before != after:
            tot += 1
            print(f"  {p.split('/')[-1]:26} 손봄")
    print(f"\n{tot}편 조사 정리")
