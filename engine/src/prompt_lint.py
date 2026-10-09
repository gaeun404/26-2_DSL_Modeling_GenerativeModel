# -*- coding: utf-8 -*-
"""
prompt_lint.py — **조립된 프롬프트**에 서로 부딪치는 지시가 없는지 본다.

왜 만들었나
  같은 병으로 세 번 넘어졌다.
    1차  가드가 "먼저 말하지 마라", 프롬프트가 "정곡 찔리면 실토하라"  → 모델이 입을 닫았다
    2차  "230~350자로 답하라"                                    → 같은 말을 세 번 되풀이했다
    3차  stance는 "실마리를 남겨라", turn_schema는 "최대 2문장",
         카드는 "한두 문장으로 짧고 자연스럽게" + 짧은 예문         → 전부 한 줄로 끊겼다

  모델은 부딪치는 지시를 만나면 **가장 안전한 쪽(입 다물기·짧게)으로 도망친다.**
  그러니 사람이 눈으로 볼 게 아니라, 프롬프트를 조립해 놓고 기계가 봐야 한다.

검사 항목
  LEN-single-owner   길이 지시는 **한 곳(이번 턴에 할 일)**에서만 나온다
  LEN-no-example     짧은 예문으로 길이를 가르치지 않는다
  ADMIT-not-blocked  실토하는 턴에 "죄를 시인하지 마라"가 함께 있지 않다
  GUILT-guarded      실토 턴이 아니면 죄를 시인하지 말라는 제동이 있다
  NO-REFUSAL-SAMPLE  거부 문구를 예시로 가르치지 않는다 (모델이 그대로 베낀다)
  SECRET-not-listed  카드에 비밀이 '먼저 말해도 되는 것'처럼 놓여 있지 않다

사용:
    python prompt_lint.py                       # 전 시나리오 × 전 인물 × 전 태도
    python prompt_lint.py out/13_푸른수염.json
"""
import json, glob, sys, re

# 길이를 지시하는 말투 — 어디에 있든 잡아낸다
LEN_PAT = re.compile(
    r"(한두 문장|한 문장으로|두세 문장|네다섯 문장|대여섯 문장|최대 \d문장|"
    r"\d+~\d+자|\d문장을 넘기지|짧게 답|짧고 자연스럽게|간결하게)")
# 길이 지시가 **허용되는** 구역
OWNER_HEADS = ("[이번 턴에 할 일", "[한 턴에 담을 것", "[이번 턴은",
               "[출력 형식", "[대사]", "[감정]", "[행동]")   # 출력 규격 자리는 예외
REFUSAL = re.compile(r"(대답할 수 없|말할 수 없|답할 수 없|하고 싶지 않소|내 입으로 말할 일이 아니)")
# 따라 쓸 **대사 본보기**가 프롬프트에 있으면 모델은 반드시 그대로 베낀다.
#   지금까지 네 번 당했다: 거부 문구 / 회피 문구 / 짧은 예문 / "…그 이야긴 하고 싶지 않소".
QUOTED_LINE = re.compile(r"(예:|예를 들어)\s*[\"“']([^\"”']{8,})")


def _blocks(text):
    """대괄호 제목을 기준으로 프롬프트를 구역으로 자른다."""
    out, head, buf = [], "(머리말)", []
    for ln in text.splitlines():
        if ln.startswith("[") or ln.startswith("▶") or ln.startswith("════"):
            out.append((head, "\n".join(buf)))
            head, buf = ln.strip(), []
        else:
            buf.append(ln)
    out.append((head, "\n".join(buf)))
    return out


def lint_prompt(text, stance):
    R = []
    def chk(name, cond, note=""):
        R.append((name, bool(cond), note))

    # ① 길이 지시가 여러 주인을 갖는가
    owners = set()
    for head, body in _blocks(text):
        for m in LEN_PAT.finditer(head + "\n" + body):
            owners.add("허용" if head.startswith(OWNER_HEADS) else head[:26])
    stray = sorted(o for o in owners if o != "허용")
    chk("LEN-single-owner", not stray,
        f"길이를 지시하는 곳이 더 있다: {stray} — 턴 지시 한 곳만 정해야 한다")

    # ② 짧은 예문으로 길이를 가르치지 않는가
    ex = re.search(r"(예:|표본:)(.{0,120})", text, re.S)
    chk("LEN-no-example", not (ex and LEN_PAT.search(text[:ex.start()][-160:])),
        "예문 바로 앞에 길이 지시가 붙어 있다 — 모델은 예문 길이를 그대로 베낀다")

    # ③ 실토 턴이 막혀 있지 않은가
    blocked = ("죄를 시인하거나" in text) or re.search(r"시인하지 마라", text)
    if stance in ("ADMIT", "BREAK"):
        ok = (not blocked) or ("살인만은" in text)
        chk("ADMIT-not-blocked", ok,
            "실토하는 턴에 '죄를 시인하지 마라'가 함께 들어 있다 — 지시가 부딪친다")
    else:
        chk("GUILT-guarded", blocked,
            "평상 턴인데 죄를 시인하지 말라는 제동이 없다")

    # ④ 거부 문구를 예시로 가르치지 않는가
    hits = [m.group(0) for m in REFUSAL.finditer(text)]
    allowed = text.count("금지") + text.count("쓰지 마라")
    chk("NO-REFUSAL-SAMPLE", not hits or allowed >= len(hits),
        f"거부 문구가 본보기처럼 놓여 있다: {hits} — 모델이 그대로 베낀다")

    # ⑤ 따라 쓸 대사 본보기가 있는가 (있으면 반드시 베낀다)
    quoted = [m.group(2)[:30] for m in QUOTED_LINE.finditer(text)]
    chk("NO-QUOTED-SAMPLE", not quoted,
        f"따라 쓸 대사 본보기가 있다: {quoted} — 모델은 예문을 그대로 베낀다")

    ok = all(c for _, c, _ in R)
    return ok, R


def run(paths):
    from stress_agent import suspect_system
    from turn_schema import format_block
    from stance import directive
    STANCES = ["ANSWER", "DEFLECT", "FLINCH", "ADMIT", "BREAK"]
    bad = 0
    seen = {}
    for p in sorted(paths):
        s = json.load(open(p, encoding="utf-8"))
        pdm = {x["id"]: x for x in s["map"]["places"]}
        for c in s["cast"]:
            mine = [pdm[c["timeline"][sl]]["name"] for sl in s["time_slots"]]
            for st in STANCES:
                lt = st in ("ADMIT", "BREAK")
                d = directive({"stance": st, "secret": (c.get("secrets") or [{}])[0],
                               "denied_before": True}, c, mine)
                full = (suspect_system(s, c) + "\n\n"
                        + format_block(c, 0, allow_guilt_tint=False, forced_disclosure=lt)
                        + "\n\n" + d)
                ok, R = lint_prompt(full, st)
                if not ok:
                    bad += 1
                    for n, cond, note in R:
                        if not cond:
                            seen.setdefault((n, note), []).append(f"{p.split('/')[-1]}:{c['id']}:{st}")
    for (n, note), where in sorted(seen.items()):
        print(f"  ❌ {n}  — {note}")
        print(f"     {len(where)}곳 (예: {', '.join(where[:3])})")
    total = len(paths) * 5 * 5
    print(f"\n조립 프롬프트 {total}개 중 문제 {bad}개")
    return bad == 0


if __name__ == "__main__":
    sys.path.insert(0, ".")
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    ok = run(glob.glob(arg))
    print("✅ 프롬프트에 부딪치는 지시 없음" if ok else "❌ 프롬프트 충돌")
    sys.exit(0 if ok else 1)
