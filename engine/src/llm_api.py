# -*- coding: utf-8 -*-
"""
llm_api.py — 로컬 모델이 기준을 못 넘을 때의 **대안 경로**.

언제 쓰나:
  run_shootout.sh의 결론이 "로컬로는 부족하다"로 나올 때만.
  그 전에는 쓰지 않는다 — 비용이 들고, 학교 GPU를 쓰는 이유가 사라진다.

설계 원칙:
  · stress_local.LocalLLM 과 **같은 인터페이스**(.chat / .tok)를 흉내 낸다.
    그래야 stress_local.py·guard.py를 한 줄도 안 고치고 갈아 끼울 수 있다.
  · OpenAI 호환 엔드포인트면 어느 업체든 붙는다(base_url만 바꾼다).
  · ★키는 코드·채팅에 절대 넣지 않는다. 환경변수로만 읽는다.★
      export MM_API_KEY=...            # 키
      export MM_API_BASE=https://...   # 엔드포인트(생략 시 OpenAI 기본)
      export MM_API_MODEL=...          # 모델 이름

가드와의 관계:
  API는 suppress_tokens·bad_words_ids 같은 디코딩 제어를 대개 지원하지 않는다.
  그래서 guard.Guard를 쓸 때 use_suppress=False, use_bad_words=False로 만들고
  **3단(사후 검사 + 재생성)만** 쓴다. 그것만으로도 대부분 걸러진다.

사용:
    from llm_api import ApiLLM
    llm = ApiLLM()                       # 환경변수에서 읽음
    llm.chat([{"role":"user","content":"..."}])

    # stress_local과 함께
    python stress_local.py "../scenarios/23_*.json" --api --guard --acting
"""
import os, time, json, urllib.request, urllib.error


class _FakeTok:
    """guard.Guard가 토크나이저를 요구하지만, API 경로에선 디코딩 제어를 안 쓴다.
    Guard(use_suppress=False, use_bad_words=False)와 짝을 이룬다."""
    name_or_path = "api"
    def __call__(self, text, **kw):
        class O: input_ids = []
        return O()
    def decode(self, ids): return ""


class ApiLLM:
    def __init__(self, model=None, base=None, key=None, path=None,
                 max_new_tokens=220, temperature=0.7, timeout=90, retries=3):
        self.key = key or os.environ.get("MM_API_KEY")
        if not self.key:
            raise RuntimeError(
                "MM_API_KEY 환경변수가 없습니다.\n"
                "  export MM_API_KEY='...'      # 키는 코드나 채팅에 넣지 마세요\n"
                "  export MM_API_BASE='https://...'\n"
                "  export MM_API_MODEL='...'")
        self.base = (base or os.environ.get("MM_API_BASE")
                     or "https://api.openai.com/v1").rstrip("/")
        # 업체마다 완성 API 경로가 다르다(OpenAI 호환이어도 접두어가 붙는 곳이 있다).
        # 예: 네이버 CLOVA Studio는 OpenAI 호환 경로를 따로 둔다.
        self.path = (path or os.environ.get("MM_API_PATH") or "/chat/completions")
        self.model = model or os.environ.get("MM_API_MODEL") or "gpt-4o-mini"
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.retries = retries
        self.tok = _FakeTok()
        self.calls = 0
        self.tokens_in = 0
        self.tokens_out = 0
        print(f"[API] {self.model} @ {self.base}{self.path}", flush=True)

    def chat(self, messages, **ignored):
        """ignored: suppress_tokens 등 디코딩 옵션은 API에서 무시된다."""
        payload = {"model": self.model, "messages": messages,
                   "max_tokens": self.max_new_tokens,
                   "temperature": self.temperature, "top_p": 0.9}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base + self.path, data=data,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.key}"})
        last = None
        for i in range(self.retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    out = json.loads(r.read().decode("utf-8"))
                self.calls += 1
                u = out.get("usage") or {}
                self.tokens_in += u.get("prompt_tokens", 0)
                self.tokens_out += u.get("completion_tokens", 0)
                return (out["choices"][0]["message"]["content"] or "").strip()
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "ignore")[:200]
                last = f"HTTP {e.code}: {body}"
                if e.code in (429, 500, 502, 503, 529):
                    time.sleep(2 ** i)          # 백오프 후 재시도
                    continue
                break
            except Exception as e:
                last = f"{type(e).__name__}: {e}"
                time.sleep(2 ** i)
        raise RuntimeError(f"API 호출 실패: {last}")

    def report(self):
        return (f"[API] 호출 {self.calls}회 · 입력 {self.tokens_in:,} 토큰 "
                f"· 출력 {self.tokens_out:,} 토큰")


def make_guard(scenario=None, cast_member=None, max_retry=2):
    """API용 가드 — 디코딩 봉쇄를 끄고 사후 검사·재생성만 쓴다."""
    from guard import Guard
    return Guard(_FakeTok(), scenario, cast_member,
                 max_retry=max_retry, use_suppress=False, use_bad_words=False)


if __name__ == "__main__":
    if not os.environ.get("MM_API_KEY"):
        print("환경변수 확인:")
        for k in ("MM_API_KEY", "MM_API_BASE", "MM_API_MODEL", "MM_API_PATH"):
            v = os.environ.get(k)
            print(f"  {k:14} {'설정됨' if v else '없음'}" +
                  (f" ({v})" if v and k != "MM_API_KEY" else ""))
        print("\n키가 없으면 이 파일은 아무것도 하지 않습니다. 이것이 의도된 동작입니다.")
        raise SystemExit
    llm = ApiLLM()
    print(llm.chat([{"role": "system", "content": "너는 조선 시대 하인 막동이다. 한국어로만 답하라."},
                    {"role": "user", "content": "그 밤 자네는 어디 있었나?"}]))
    print(llm.report())
