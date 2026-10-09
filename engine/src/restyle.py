# -*- coding: utf-8 -*-
"""
restyle.py — 시나리오에 쓰인 **대사를 그 인물의 말체로 고쳐 쓴다.**

왜 필요한가
  voices.py가 인물마다 말체를 정했다. 그런데 시나리오에는 예전에 손으로 쓴
  대사가 그대로 남아 있다 — 알리바이, 실토 대사, 트리거 반응.
  그 대사들은 거의 다 하오체다. 그러니 카드가 이렇게 된다.

      [말투] 합쇼체 — 반드시 '-습니다'로 끝내라
      ...
      겉으로 하는 말: "나는 초저녁부터 새벽까지 사랑채에서 바둑을 두었소."

  **모델은 눈앞의 문장을 베낀다.** 규칙보다 예문이 세다. 네 번 겪었다.
  그러니 규칙을 바꿨으면 문장도 함께 바꿔야 한다.

무엇을 고치나
  alibi_narration · secrets[].confession_line · pressure_points[].reveals ·
  persona.example_line / example_lines
  — 뜻은 한 글자도 바꾸지 않고 **말체만** 바꾼다.

두 갈래로 돈다
  ① 규칙 변환   흔한 어미는 표로 바꾼다. 공짜고 빠르다.
  ② API 다듬기  표로 안 되는 문장만 모델에 맡긴다(--api). 바꾼 결과를 다시 검사해,
                여전히 어긋나면 원문을 그대로 둔다 — 뜻이 상하는 것보다 낫다.

쓰는 법
    python restyle.py --dry-run                # 몇 개나 어긋나는지만 센다
    python restyle.py                          # 규칙 변환만 (공짜)
    export MM_API_KEY=... ; python restyle.py --api    # 남은 것까지 모델로
"""
import json, glob, sys, os, re, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")
import voices

FIELDS = ("alibi_narration", "confession_line", "reveals", "example_line")

# ── ① 규칙 변환 — 하오체가 대부분이라 여기서 많이 잡힌다 ──────────────
#   어미만 손대고 어순·낱말은 건드리지 않는다.
RULES = {
    "합쇼체": [(r"였소\b", "였습니다"), (r"았소\b", "았습니다"), (r"었소\b", "었습니다"),
              (r"하오\b", "합니다"), (r"이오\b", "입니다"), (r"오이다\b", "옵니다"),
              (r"구려\b", "습니다"), (r"([가-힣])소\b", r"\1습니다"),
              (r"([가-힣])요\b", r"\1습니다"), (r"([가-힣])네\b", r"\1습니다")],
    "격식체": [(r"였소\b", "였습니다"), (r"았소\b", "았습니다"), (r"었소\b", "었습니다"),
              (r"하오\b", "합니다"), (r"이오\b", "입니다"), (r"구려\b", "습니다"),
              (r"([가-힣])소\b", r"\1습니다")],
    "합니다체": [(r"였소\b", "였습니다"), (r"이오\b", "입니다"), (r"([가-힣])소\b", r"\1습니다"),
               (r"([가-힣])요\b", r"\1습니다")],
    "해요체": [(r"였소\b", "였어요"), (r"았소\b", "았어요"), (r"었소\b", "었어요"),
              (r"하오\b", "해요"), (r"이오\b", "이에요"), (r"구려\b", "네요"),
              (r"([가-힣])소\b", r"\1어요"), (r"습니다\b", "어요")],
    "다정체": [(r"였소\b", "였어요"), (r"았소\b", "았어요"), (r"었소\b", "었어요"),
              (r"하오\b", "해요"), (r"이오\b", "이에요"), (r"습니다\b", "어요"),
              (r"([가-힣])소\b", r"\1어요")],
    "하게체": [(r"였소\b", "였네"), (r"았소\b", "았네"), (r"었소\b", "었네"),
              (r"하오\b", "하네"), (r"이오\b", "일세"), (r"구려\b", "구먼"),
              (r"습니다\b", "네"), (r"([가-힣])소\b", r"\1네")],
    "노숙체": [(r"였소\b", "였네"), (r"았소\b", "았네"), (r"었소\b", "었네"),
              (r"하오\b", "하네"), (r"이오\b", "일세"), (r"습니다\b", "네"),
              (r"([가-힣])소\b", r"\1네")],
    "노년체": [(r"였소\b", "였지"), (r"이오\b", "이지"), (r"습니다\b", "네"),
              (r"([가-힣])소\b", r"\1네")],
    "공손체": [(r"였소\b", "였답니다"), (r"이오\b", "이지요"), (r"하오\b", "한답니다"),
              (r"구려\b", "군요"), (r"([가-힣])소\b", r"\1지요")],
    "소인체": [(r"였소\b", "였사옵니다"), (r"이오\b", "이옵니다"), (r"하오\b", "하옵니다"),
              (r"습니다\b", "옵니다"), (r"([가-힣])소\b", r"\1옵니다")],
    "올시다체": [(r"이오\b", "올시다"), (r"였소\b", "였올습니다"), (r"습니다\b", "올습니다")],
    "노라체": [(r"였소\b", "였노라"), (r"이오\b", "이니라"), (r"하오\b", "하노라"),
              (r"습니다\b", "노라"), (r"([가-힣])소\b", r"\1노라")],
    "정중체": [(r"습니다\b", "소"), (r"([가-힣])어요\b", r"\1오"), (r"네\b", "구려")],
    "하오체": [(r"습니다\b", "소"), (r"([가-힣])어요\b", r"\1오")],
    "건조체": [(r"([가-힣])요\b", r"\1니다"), (r"([가-힣])소\b", r"\1습니다")],
    "반존대": [(r"습니다\b", "요"), (r"([가-힣])소\b", r"\1지")],
}
# 자칭도 함께 갈아 끼운다 — 말체만 바꾸고 '나'가 남으면 여전히 어긋난다
SELF_SWAP = {"저": [("나는", "저는"), ("내가", "제가"), ("나를", "저를"), ("내 ", "제 ")],
             "나": [("저는", "나는"), ("제가", "내가"), ("저를", "나를"), ("제 ", "내 ")],
             "소인": [("나는", "소인은"), ("내가", "소인이"), ("저는", "소인은"), ("제가", "소인이")]}


def _fits(text, vo):
    """이 문장이 그 말체인가."""
    rx = vo.get("ending_re")
    if not rx or not text:
        return True
    sents = [x.strip(" .?!…\"”'’」』") for x in re.split(r"(?<=[.?!…])\s+", text) if x.strip()]
    if not sents:
        return True
    bad = [t for t in sents if not re.search(rx, t)]
    return len(bad) <= len(sents) // 2


def by_rule(text, vo):
    form = vo.get("form")
    out = text
    for pat, rep in RULES.get(form, []):
        out = re.sub(pat, rep, out)
    first = (vo.get("self") or ["저"])[0]
    for a, b in SELF_SWAP.get(first, []):
        out = out.replace(a, b)
    return out


# ── ② API 다듬기 ──────────────────────────────────────────────────────
SYS = """너는 한국어 문장의 **말투만** 고치는 교정가다.

지켜야 할 것
· 뜻·사실·이름·장소·숫자를 한 글자도 바꾸지 마라. 문장 수도 그대로 둔다.
· 오직 **종결어미와 자기 호칭**만 바꾼다.
· 설명하지 말고 고친 문장만 출력한다. 따옴표도 붙이지 마라."""


def by_api(text, vo, llm):
    u = (f"[바꿀 말체] {vo['form']} ({vo.get('form_desc','')})\n"
         f"[반드시 이 어미로 끝낸다] {' / '.join(vo.get('endings') or [])}\n"
         f"[자기를 부르는 말] {' · '.join(vo.get('self') or [])}\n"
         f"[하지 말 것] {vo.get('ban','')}\n\n"
         f"[원문]\n{text}\n\n[고친 문장만 출력]")
    out = llm.chat([{"role": "system", "content": SYS}, {"role": "user", "content": u}])
    return (out or "").strip().strip('"“”')


def restyle(s, llm=None, verbose=True):
    fixed = rule_ok = api_ok = left = 0
    for c in s["cast"]:
        vo = (c.get("persona") or {}).get("voice") or {}
        if not vo:
            continue
        targets = []
        if c.get("alibi_narration"):
            targets.append((c, "alibi_narration", None))
        for sec in (c.get("secrets") or []):
            if sec.get("confession_line"):
                targets.append((sec, "confession_line", None))
        for pp in (c.get("pressure_points") or []):
            if pp.get("reveals"):
                targets.append((pp, "reveals", None))
        per = c.get("persona") or {}
        if per.get("example_line"):
            targets.append((per, "example_line", None))
        for i, _ in enumerate(per.get("example_lines") or []):
            targets.append((per["example_lines"], i, None))

        for holder, key, _ in targets:
            cur = holder[key]
            if _fits(cur, vo):
                continue
            fixed += 1
            new = by_rule(cur, vo)
            if _fits(new, vo):
                holder[key] = new
                rule_ok += 1
                if verbose:
                    print(f"   규칙 {c['name']}/{key}: {cur[:34]} → {new[:34]}")
                continue
            if llm:
                try:
                    got = by_api(cur, vo, llm)
                except Exception as e:
                    got = ""
                    if verbose:
                        print(f"   ⚠️ API 실패 {c['name']}/{key}: {str(e)[:50]}")
                if got and _fits(got, vo) and abs(len(got) - len(cur)) < len(cur) * 0.7:
                    holder[key] = got
                    api_ok += 1
                    if verbose:
                        print(f"   API  {c['name']}/{key}: {cur[:30]} → {got[:30]}")
                    continue
            left += 1
            if verbose:
                print(f"   그대로 둠 {c['name']}/{key} ({vo.get('form')}): {cur[:40]}")
    return dict(total=fixed, rule=rule_ok, api=api_ok, left=left)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default="scenarios/[0-9]*.json")
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    llm = None
    if a.api and not a.dry_run:
        from llm_api import ApiLLM
        llm = ApiLLM(max_new_tokens=400, temperature=0.3)

    tot = dict(total=0, rule=0, api=0, left=0)
    for p in sorted(glob.glob(a.path)):
        s = json.load(open(p, encoding="utf-8"))
        if a.dry_run:
            n = 0
            for c in s["cast"]:
                vo = (c.get("persona") or {}).get("voice") or {}
                for t in [c.get("alibi_narration", "")] + \
                         [x.get("confession_line", "") for x in (c.get("secrets") or [])] + \
                         [x.get("reveals", "") for x in (c.get("pressure_points") or [])]:
                    if t and not _fits(t, vo):
                        n += 1
            print(f"  {os.path.basename(p):26} 어긋난 대사 {n}개")
            tot["total"] += n
            continue
        print(f"\n═══ {os.path.basename(p)}")
        r = restyle(s, llm)
        json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        for k in tot:
            tot[k] += r[k]
    if a.dry_run:
        print(f"\n합계 어긋난 대사 {tot['total']}개 "
              f"(API로 다듬으면 대략 {tot['total']*0.0004:.2f} 달러)")
    else:
        print(f"\n어긋남 {tot['total']}개 · 규칙으로 {tot['rule']} · API로 {tot['api']} "
              f"· 그대로 둠 {tot['left']}")
        print("※ alibi_narration이 바뀌었으니 relate.py를 다시 돌리세요.")
