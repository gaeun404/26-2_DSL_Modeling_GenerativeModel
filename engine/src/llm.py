# -*- coding: utf-8 -*-
"""
LLM 백엔드 추상화 — 같은 생성기를 두 방식으로 돌릴 수 있게.
  MM_BACKEND=vllm      : dsl04 GPU의 vLLM(OpenAI 호환 서버). 무료. (기본)
  MM_BACKEND=anthropic : Claude API (유료). export ANTHROPIC_API_KEY 필요.

환경변수:
  MM_BACKEND   vllm | anthropic         (기본 vllm)
  MM_MODEL     모델명                    (vllm 기본 'Qwen/Qwen2.5-72B-Instruct', anthropic 기본 'claude-sonnet-4-5')
  MM_BASE_URL  vLLM 엔드포인트           (기본 http://localhost:8000/v1)
  MM_API_KEY   vLLM 더미 키              (기본 'EMPTY')

임포트 시 무거운 SDK를 불러오지 않는다(지연 로딩) — 백엔드 미설치 환경에서도 파일 임포트는 안전.
"""
import os

BACKEND = os.environ.get("MM_BACKEND", "vllm").lower()

def default_model():
    if BACKEND == "openai":
        return os.environ.get("MM_MODEL", "gpt-4o-mini")
    if BACKEND == "anthropic":
        return os.environ.get("MM_MODEL", "claude-sonnet-4-5")
    return os.environ.get("MM_MODEL", "Qwen/Qwen2.5-72B-Instruct")

_client = None

def _get_client():
    global _client
    if _client is not None:
        return _client
    if BACKEND == "openai":
        from openai import OpenAI
        _client = OpenAI()          # OPENAI_API_KEY 사용
    elif BACKEND == "anthropic":
        import anthropic
        _client = anthropic.Anthropic()
    else:  # vllm / openai 호환
        from openai import OpenAI
        _client = OpenAI(
            base_url=os.environ.get("MM_BASE_URL", "http://localhost:8000/v1"),
            api_key=os.environ.get("MM_API_KEY", "EMPTY"))
    return _client

def complete(system, messages, max_tokens=6000, model=None, temperature=0.9):
    """
    system: str
    messages: [{"role":"user"/"assistant","content":str}, ...]
    반환: 응답 텍스트(str)
    """
    model = model or default_model()
    cli = _get_client()
    if BACKEND == "openai":
        msgs = [{"role": "system", "content": system}] + messages
        try:
            r = cli.chat.completions.create(model=model, messages=msgs,
                                            max_tokens=max_tokens, temperature=temperature)
        except TypeError:
            r = cli.chat.completions.create(model=model, messages=msgs,
                                            max_completion_tokens=max_tokens)
        return r.choices[0].message.content
    if BACKEND == "anthropic":
        kw = dict(model=model, max_tokens=max_tokens, system=system, messages=messages)
        try:
            r = cli.messages.create(**kw, temperature=temperature)
        except TypeError:
            # 새 SDK는 temperature 인자를 받지 않는다 — 빼고 다시 부른다
            r = cli.messages.create(**kw)
        return "".join(getattr(b, "text", "") for b in r.content)
    else:
        msgs = [{"role": "system", "content": system}] + messages
        r = cli.chat.completions.create(model=model, messages=msgs,
                                        max_tokens=max_tokens, temperature=temperature)
        return r.choices[0].message.content
