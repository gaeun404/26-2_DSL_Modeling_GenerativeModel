# -*- coding: utf-8 -*-
"""
guard.py — 생성 단계에서 **코드로 보장**하는 안전장치.

■ 왜 필요한가
  지금까지 우리는 프롬프트로 "AI라고 말하지 마", "한국어만 써"라고 **부탁**했다.
  부탁은 보장이 아니다. 1회차에서 두 모델 모두 중국어를 흘렸고 배역을 벗었다.
  시나리오는 이미 '생성-검증' 구조로 만드는데, 대화만 검증 없이 내보내는 건 구조적 모순이다.
  턴 단위로 같은 걸 한다.

■ 3단 방어
  1단 · 디코딩 봉쇄(suppress_tokens)
        한글·숫자·기본 문장부호가 아닌 토큰을 vocab에서 통째로 막는다.
        → 한자·가나·키릴이 **물리적으로 생성 불가능**해진다. garbled 근본 차단.
  2단 · 금칙어 봉쇄(bad_words_ids)
        "AI · 인공지능 · 언어모델 · 진행자 · 프롬프트 · 지시문" 토큰열 차단.
        (표기 변형까지 다 막지는 못하므로 3단과 짝을 이룬다)
  3단 · 사후 검사 + 재생성
        뽑은 답을 검사해 걸리면 **플레이어에게 보여주지 않고** 다시 뽑는다.
        회차마다 경고를 세게 붙인다. 마지막엔 안전한 대사로 대체(fallback).

■ 부수 효과
  실제 게임은 이 가드를 거친 답만 보여주므로, 가드 없이 한 방에 뽑아 채점하던
  기존 stress 결과는 **실제보다 나쁘게** 나온 면이 있다. 이제 둘을 비교할 수 있다.

사용:
    from guard import Guard
    g = Guard(llm.tok, scenario, cast_member)         # 모델 로딩 후 1회
    text, info = g.generate(llm, messages)            # 매 턴
단독 실행:
    python guard.py            # 토크나이저 없이 검사기만 테스트
"""
import os, re, json, unicodedata

# ── 허용 문자: 한글 · 라틴 알파벳/숫자 · 공백 · 문장부호 ────────────────
_ALLOWED_RANGES = [
    (0x0020, 0x007E),   # ASCII 인쇄 가능
    (0x00A0, 0x00A0),
    (0x1100, 0x11FF),   # 한글 자모
    (0x3130, 0x318F),   # 호환 자모
    (0xAC00, 0xD7A3),   # 한글 음절
    (0x2010, 0x2027),   # ‐ – — ‘ ’ “ ” … 등
    (0x2030, 0x205E),
    (0x3001, 0x3003),   # 、。〃
    (0x300C, 0x300F),   # 「」『』
    (0xFF01, 0xFF02), (0xFF0C, 0xFF0E), (0xFF1A, 0xFF1F),  # 전각 문장부호 일부
]

def _allowed_char(ch):
    o = ord(ch)
    if ch in "\n\r\t": return True
    return any(a <= o <= b for a, b in _ALLOWED_RANGES)

def has_foreign(text, threshold=1):
    """한글·라틴·문장부호가 아닌 '글자'가 threshold개 이상이면 True."""
    n = 0
    for ch in text or "":
        if _allowed_char(ch): continue
        if unicodedata.category(ch).startswith(("L", "N")):   # 글자·숫자류만 셈
            n += 1
            if n >= threshold: return True
    return False


# ── 금칙 표현 (사후 검사용 — 디코딩 봉쇄보다 넓게) ─────────────────────
META_WORDS = ["AI", "A.I", "인공지능", "언어모델", "언어 모델", "챗봇", "모델로서",
              "시스템 프롬프트", "프롬프트", "지시문", "assistant", "OpenAI",
              "게임 진행자", "진행자", "게임 마스터", "역할을 수행", "연기하고", "연기하는",
              "롤플레이", "시뮬레이션"]
REFUSAL = ["대답할 수 없", "답변할 수 없", "죄송합니다만", "도와드릴 수 없",
           "제공할 수 없", "부적절한 요청", "답변드리기 어렵"]

# 디코딩 단계에서 아예 막을 핵심 낱말(표기 변형이 적은 것만)
BAN_SEED = ["AI", "인공지능", "언어모델", "챗봇", "지시문", "시스템 프롬프트",
            "게임 진행자", "게임 마스터", "롤플레이", "assistant"]


def build_suppress_tokens(tok, cache_dir=".guard_cache", model_key=""):
    """vocab을 훑어 '허용 문자만으로 이루어지지 않은' 토큰 id 목록을 만든다.
    15만 토큰 스캔에 1~3초. 모델별로 캐시한다."""
    os.makedirs(cache_dir, exist_ok=True)
    key = re.sub(r"[^\w.-]", "_", model_key or getattr(tok, "name_or_path", "tok"))
    path = os.path.join(cache_dir, f"suppress_{key}.json")
    if os.path.exists(path):
        try: return json.load(open(path))
        except Exception: pass
    bad = []
    size = getattr(tok, "vocab_size", None) or len(tok)
    for i in range(size):
        try: s = tok.decode([i])
        except Exception: continue
        if not s: continue
        # 특수토큰은 건드리지 않는다
        if s.startswith("<") and s.endswith(">"): continue
        if any((not _allowed_char(ch)) and unicodedata.category(ch).startswith(("L", "N"))
               for ch in s):
            bad.append(i)
    try: json.dump(bad, open(path, "w"))
    except Exception: pass
    return bad


def build_bad_words(tok, words=None):
    """금칙 낱말의 토큰열. 앞 공백 유무 두 가지를 모두 등록한다."""
    out = []
    for w in (words or BAN_SEED):
        for form in (w, " " + w):
            try:
                ids = tok(form, add_special_tokens=False).input_ids
            except Exception:
                continue
            if ids and ids not in out:
                out.append(ids)
    return out


# ── 사후 검사 ─────────────────────────────────────────────────────────
class Checker:
    """시나리오 맥락까지 아는 검사기. 걸리면 (사유, 안내문)을 돌려준다."""

    def __init__(self, s=None, cast_member=None):
        self.s = s; self.c = cast_member or {}
        self.recent = []          # 최근 답들 — 자기 말을 되풀이하는지 본다
        self.secret_words = []
        if s and cast_member:
            sec = cast_member.get("secret") or {}
            # 비밀 본문에서 명사구를 대충 뽑아 조기 누설 감시에 쓴다
            body = sec.get("content") or sec.get("text") or ""
            self.secret_words = [w for w in re.findall(r"[가-힣]{2,}", body)][:12]

    @staticmethod
    def _keywords(text, n=6):
        """비밀 문장에서 뼈대가 되는 낱말을 뽑는다(2자 이상 한글)."""
        import re as _re
        stop = {"그리고","하지만","이것","저것","때문","그것","자신","사람","이야기"}
        ws = [w for w in _re.findall(r"[가-힣]{2,}", text or "") if w not in stop]
        return ws[:n]

    def check(self, text, acting=False, secret_unlocked=True, require_disclosure=None,
              check_echo=False):
        """★ 기본은 **불변식만** 본다: 한국어·메타·거부·형식.
        '언제 실토할지' 같은 이야기 타이밍은 stance.py가 정한다 —
        가드가 사후 검사로 그걸 강제하려다 GPT-4o-mini의 답까지 버렸다."""
        t = (text or "").strip()
        if not t:
            return ("empty", "빈 답변이다. 인물로서 한 마디라도 하라.")
        if has_foreign(t, threshold=1):
            return ("garbled", "한국어가 아닌 글자가 섞였다. **한글만** 써서 다시 답하라.")
        for w in REFUSAL:
            if w in t:
                return ("refusal", "기계적인 거부 문구를 쓰지 마라. 인물로서 말을 돌리거나 입을 다물어라.")
        for w in META_WORDS:
            if w in t:
                return ("meta", f"'{w}' 같은 말은 이 인물이 알 리 없다. "
                                "그 낱말을 쓰지 말고, 어리둥절해하며 인물로서 답하라.")
        if acting:
            from turn_schema import parse_turn
            p = parse_turn(t)
            if p["errors"]:
                return ("format", "형식이 틀렸다. 반드시 [감정]/[행동]/[대사] 세 줄로만 답하라.")
        # ★ 실토해야 하는 턴인데 뭉개고 넘어가는 것을 막는다.
        #   실제 플레이에서 "그 아이가 죽은 뒤에 내가 그랬지…" 식으로 얼버무려
        #   무슨 말인지 알 수 없는 실토가 나왔다. 분명하지 않으면 다시 뽑는다.
        if require_disclosure:
            body = t
            if acting:
                from turn_schema import parse_turn as _pt
                body = (_pt(t).get("line") or t)
            hit = sum(1 for w in require_disclosure if w in body)
            if hit < 1:
                return ("vague",
                        "지금은 실토할 자리다. 얼버무리지 말고 **무엇을 했는지 한 문장으로 분명히** 말하라. "
                        "'그것', '그 일' 같은 말로 뭉개지 말고 사실을 그대로 대라.")
        # ★ 자기 변명을 매 턴 되풀이하는 것을 막는다.
        #   실제 플레이에서 "짐작 가는 사람이 없소?"라고 물었는데
        #   "나는 죽이지 않았소 / 옷을 아궁이에 넣었소"를 네 턴 내리 반복했다.
        #   질문이 달라졌는데 답이 같으면 그건 대화가 아니다.
        if check_echo and self.recent:
            import difflib as _dl
            body = t
            if acting:
                from turn_schema import parse_turn as _pt2
                body = (_pt2(t).get("line") or t)
            for prev in self.recent[-3:]:
                if _dl.SequenceMatcher(None, body, prev).ratio() >= 0.72:
                    return ("echo",
                            "앞서 한 말을 거의 그대로 되풀이했다. "
                            "**지금 물은 것에 먼저 답하라.** 묻지 않은 변명을 앞세우지 말고, "
                            "이미 한 말은 다시 하지 마라.")
        if not secret_unlocked and self.secret_words:
            hit = [w for w in self.secret_words if w in t]
            if len(hit) >= 2:
                return ("secret", "아직 털어놓을 때가 아니다. 그 이야기는 꺼내지 말고 말을 돌려라.")
        # 통과한 답만 기억한다(다음 턴의 자기복제 판정 기준)
        if acting:
            from turn_schema import parse_turn as _pt3
            self.recent.append(_pt3(t).get("line") or t)
        else:
            self.recent.append(t)
        return (None, None)


# ── 생성 가드 ─────────────────────────────────────────────────────────
class Guard:
    def __init__(self, tok, s=None, cast_member=None, model_key="", max_retry=2,
                 use_suppress=True, use_bad_words=True):
        self.tok = tok
        self.checker = Checker(s, cast_member)
        self.max_retry = max_retry
        self.suppress = build_suppress_tokens(tok, model_key=model_key) if use_suppress else []
        self.bad_words = build_bad_words(tok) if use_bad_words else []
        self.stats = {"retry": 0, "fallback": 0, "caught": {}}

    def gen_kwargs(self):
        kw = {}
        if self.suppress:  kw["suppress_tokens"] = self.suppress
        if self.bad_words: kw["bad_words_ids"] = self.bad_words
        return kw

    def generate(self, llm, messages, acting=False, secret_unlocked=True, fallback=None,
                 require_disclosure=None, admit_line=None):
        """admit_line: 실토 턴의 뼈대 문장.
        실토 턴에서 세 번 실패하면 **거절 문구가 아니라 이 문장으로** 대체한다.
        거절로 대체하면 대화가 죽고, 모델이 그 거절을 다음 턴에도 따라 한다."""
        """llm.chat(messages, **kw) 를 감싸 검사·재생성한다."""
        last = ""
        for attempt in range(self.max_retry + 1):
            msgs = list(messages)
            if attempt:
                msgs.append({"role": "user", "content": self._nudge})
            try:
                out = llm.chat(msgs, **self.gen_kwargs())
            except TypeError:                       # 구버전 chat() 호환
                out = llm.chat(msgs)
            last = out
            why, nudge = self.checker.check(out, acting=acting,
                                            secret_unlocked=secret_unlocked,
                                            require_disclosure=require_disclosure)
            if why is None:
                return out, {"attempts": attempt + 1, "caught": None}
            self.stats["caught"][why] = self.stats["caught"].get(why, 0) + 1
            self.stats["retry"] += 1
            self._nudge = f"[진행자 경고 · {attempt+1}차] {nudge} 다시 답하라."
        # 끝내 못 고치면 안전한 대사로 대체 — 망가진 답을 플레이어에게 보이지 않는다
        self.stats["fallback"] += 1
        if fallback: return fallback, {"attempts": self.max_retry + 1, "caught": why, "fallback": True}
        # 실토 턴이면 뼈대 문장으로 대체한다 — 거절로 떨어지면 안 된다
        if admit_line:
            safe = (f"[감정] 체념 3\n[행동] 잠시 눈을 감았다 뜬다\n[대사] {admit_line}"
                    if acting else admit_line)
            return safe, {"attempts": self.max_retry + 1, "caught": why,
                          "fallback": True, "used_skeleton": True}
        # 대체 문구가 늘 같으면 두 모델이 똑같아 보여 비교가 무의미해진다. 조금씩 다르게.
        import random as _rd
        _acts = ["입을 다물고 시선을 내린다", "고개를 젓는다", "손끝을 만지작거린다",
                 "숨을 고르고 눈을 감는다", "턱을 굳힌다"]
        # 대체 문구는 '거절'이 아니라 '되묻기'여야 한다.
        # 거절 문구를 쓰면 모델이 그걸 배워 다음 턴에도 거절한다(실제로 그렇게 됐다).
        _lines = ["…무슨 말씀인지 잘 모르겠소. 다시 물어 주시오.",
                  "…그게 무슨 뜻이오?",
                  "…내가 무엇을 답해야 하는지 모르겠소.",
                  "…글쎄, 나는 잘 모르는 일이오.",
                  "…어인 말씀이신지."]
        safe = (f"[감정] 불안 2\n[행동] {_rd.choice(_acts)}\n[대사] {_rd.choice(_lines)}"
                if acting else f"…({_rd.choice(_acts)}) {_rd.choice(_lines)}")
        return safe, {"attempts": self.max_retry + 1, "caught": why, "fallback": True}

    _nudge = "다시 답하라."

    def report(self):
        c = self.stats["caught"]
        return (f"가드: 재생성 {self.stats['retry']}회 · 대체 {self.stats['fallback']}회"
                + (" · 유형 " + ", ".join(f"{k}{v}" for k, v in sorted(c.items(), key=lambda x: -x[1]))
                   if c else ""))


# ── 자체 테스트(토크나이저 불필요) ────────────────────────────────────
if __name__ == "__main__":
    ck = Checker()
    cases = [
        ("정상", "나는 그 밤 내 방에 있었소.", None),
        ("중국어 누출", "说实不能回答 그건 소인이", "garbled"),
        ("일본어 누출", "そうですね 잘 모르겠소.", "garbled"),
        ("메타 시인", "저는 용의자를 연기하는 인공지능입니다.", "meta"),
        ("메타 부인도 차단", "저는 AI가 아니라 허씨요.", "meta"),
        ("기계적 거부", "죄송합니다만 대답할 수 없습니다.", "refusal"),
        ("숫자·영문은 허용", "1920년 A동 앞에서 보았소.", None),
    ]
    print("=== guard 검사기 테스트 ===\n")
    bad = 0
    for name, text, expect in cases:
        why, _ = ck.check(text)
        ok = (why == expect)
        bad += 0 if ok else 1
        print(f"  [{'OK' if ok else '실패'}] {name:14} 기대 {str(expect):8} 결과 {why}")
    print("\n=== 형식 검사(acting) ===")
    for name, text, expect in [
        ("규격 준수", "[감정] 불안 2\n[행동] 손을 쥔다\n[대사] 방에 있었소.", None),
        ("괄호 자유서술", "(슬픈 표정으로) 방에 있었소.", "format"),
    ]:
        why, _ = ck.check(text, acting=True)
        ok = (why == expect); bad += 0 if ok else 1
        print(f"  [{'OK' if ok else '실패'}] {name:14} 기대 {str(expect):8} 결과 {why}")
    print(f"\n허용 문자 구간 {len(_ALLOWED_RANGES)}개 · 금칙 표현 {len(META_WORDS)+len(REFUSAL)}개 "
          f"· 디코딩 봉쇄 씨앗 {len(BAN_SEED)}개")
    print("✅ 전부 통과" if bad == 0 else f"❌ {bad}건 실패")
