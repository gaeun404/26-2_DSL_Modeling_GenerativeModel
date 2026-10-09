# -*- coding: utf-8 -*-
"""
compare.py — **다섯 가지 플레이 방식**을 인트로부터 엔딩까지 각각 돌려 견준다.

    python3 compare.py                        # 91편, 다섯 방식
    python3 compare.py 38_cinderella.json
    python3 compare.py --full 증거파           # 한 방식만 처음부터 끝까지 자세히
    python3 compare.py --rounds 2             # 라운드를 줄여서(빠르게)
    python3 compare.py --llm                  # 실제 LLM으로 대사까지 (키 필요, 비용 발생)

키가 없어도 돈다. 누가 언제 흔들리고 실토하는지는 코드(stance+pressure)가 정하므로,
**판이 어떻게 갈리는지는 대사 없이도 그대로 관측된다.** 키를 주면 문장까지 본다.

■ 무엇을 보려는 것인가
  같은 사건인데 **어떻게 파느냐에 따라 다른 판이 되는가.**
  다섯이 전부 같은 점수·같은 지목으로 끝난다면 플레이 방식이 장식이라는 뜻이고,
  갈린다면 그 갈림이 곧 이 게임의 재미다.
"""
import _boot, sys, json, glob, argparse, collections   # noqa: F401


class Stub:
    """대사 대신 자리표시자. 판단은 엔진이 하므로 판은 그대로 굴러간다."""
    calls = tokens_in = tokens_out = 0

    def chat(self, msgs):
        Stub.calls += 1
        return "(대사는 LLM이 만든다)"


def _one(path, style, rounds, llm, verbose):
    import llm_playtest as L
    return L.run(path, llm, rounds=rounds, verbose=verbose, style=style)


def _acts(rep):
    """라운드별로 무엇을 했는지 — 탐색 몇 곳, 심문 몇 번."""
    per = collections.Counter()
    for f in rep["flow"]:
        if f["kind"] == "단서":
            per["단서"] += 1
        elif f["kind"] == "탐색":
            per["헛수고"] += 1
        elif f["kind"] == "진술":
            per["첫대면"] += 1
    per["심문"] = len(rep["turns"])
    return per


def main():
    import llm_playtest as L
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", nargs="?", default="91_dsl_demo.json")
    ap.add_argument("--full", default=None, help="이 방식 하나만 자세히 (" + " / ".join(L.STYLES) + ")")
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--llm", action="store_true", help="실제 LLM으로 대사까지")
    a = ap.parse_args()

    path = a.scenario if "/" in a.scenario else f"scenarios/{a.scenario}"
    if not glob.glob(path):
        print(f"그런 시나리오가 없습니다: {path}")
        sys.exit(1)
    s = json.load(open(path, encoding="utf-8"))

    llm = Stub()
    if a.llm:
        import os
        if not os.path.exists(".apikey") and not os.environ.get("MM_API_KEY"):
            print("--llm 을 쓰려면 저장소 뿌리에 .apikey 가 있어야 합니다.")
            sys.exit(1)
        if os.path.exists(".apikey"):
            os.environ["MM_API_KEY"] = open(".apikey", encoding="utf-8").read().strip()
        os.environ.setdefault("MM_API_MODEL", "gpt-4o-mini")
        from llm_api import ApiLLM
        llm = ApiLLM(max_new_tokens=220, temperature=0.8)

    print()
    print("═" * 78)
    print(f"  「{s['meta']['title']}」  {(s.get('stars') or {}).get('stars','')}"
          f"  ·  {a.rounds or s['config']['rounds']}라운드 · 예산 {s['config']['turns_per_round']}/R")
    print(f"  같은 사건을 다섯 사람이 저마다의 방식으로 판다. 인트로부터 엔딩까지.")
    print("═" * 78)

    # ── 한 방식만 자세히 ──────────────────────────────────────
    if a.full:
        if a.full not in L.STYLES:
            print(f"그런 방식이 없습니다: {a.full}\n  " + " / ".join(L.STYLES))
            sys.exit(1)
        print(f"\n▶ {a.full} — {L.STYLES[a.full]['note']}\n")
        _one(path, a.full, a.rounds, llm, True)
        return

    # ── 다섯을 차례로 ─────────────────────────────────────────
    reps = {}
    for st in L.STYLES:
        print(f"\n  … {st} 돌리는 중", end="", flush=True)
        reps[st] = _one(path, st, a.rounds, llm, False)
        print(" ✓")

    cul = next((c["name"] for c in s["cast"] if c.get("is_culprit")), "?")
    print("\n" + "═" * 78)
    print("  판이 어떻게 갈렸나")
    print("═" * 78)
    print(f"  {'방식':7} {'찾음':>4} {'헛탐색':>4} {'심문':>4} {'단서':>4} {'비밀':>4} "
          f"{'대질':10} {'지목':7} {'결과':6} {'근거':4} {'점수':>4}")
    print("  " + "─" * 74)
    for st, r in reps.items():
        p = _acts(r)
        res = r["result"]
        cx = r.get("confront") or {}
        pair = f"{cx.get('a','—')}↔{cx.get('b','')}" if cx else "—"
        ok = "적중" if res["correct"] else "빗나감"
        cf = "결정타" if res.get("confident") else " 감 "
        print(f"  {st:7} {p['단서']:>4} {p['헛수고']:>4} {p['심문']:>4} "
              f"{res['clues']:>4} {res['secrets']:>4} {pair[:10]:10} "
              f"{str(res['named'])[:6]:7} {ok:6} {cf:4} {res['points']:>3}점")

    # ── 무엇이 갈렸나 ─────────────────────────────────────────
    print("\n" + "─" * 78)
    named = {r["result"]["named"] for r in reps.values()}
    pts = {r["result"]["points"] for r in reps.values()}
    secs = {r["result"]["secrets"] for r in reps.values()}
    hit = sum(1 for r in reps.values() if r["result"]["correct"])
    print(f"  진범 : {cul}   ·   다섯 중 {hit}이 짚었다")
    print(f"  지목이 갈린 갈래 {len(named)}가지 {sorted(named)}")
    print(f"  점수 {min(pts)}~{max(pts)}점   ·   연 비밀 {min(secs)}~{max(secs)}개")
    if len(named) == 1 and len(pts) == 1:
        print("  ⚠ 다섯이 똑같이 끝났다 — 플레이 방식이 판을 가르지 못하고 있다")
    else:
        print("  ✅ 방식마다 다른 판이 됐다")

    # ── 방식마다 무엇을 놓쳤나 ────────────────────────────────
    # ★수첩에 실제로 적힌 것으로 센다 — flow만 보면 자동 지급 단서를 놓친다
    all_clues = {c["id"] for c in s["clue_graph"]}
    print("\n  끝내 못 본 단서 (수첩 기준)")
    for st, r in reps.items():
        got = set(r.get("held_clues") or [])
        miss = sorted(all_clues - got)
        tail = f" — {', '.join(miss[:8])}" + (" …" if len(miss) > 8 else "") if miss else " — 없음"
        print(f"    {st:7} {len(miss):2}개{tail}")

    dec = [c["id"] for c in s["clue_graph"] if c.get("decisive")]
    if dec:
        print(f"\n  결정타 {dec[0]} 를 쥔 방식")
        for st, r in reps.items():
            has = dec[0] in set(r.get("held_clues") or [])
            print(f"    {st:7} {'○ 쥐었다' if has else '× 못 찾았다'}")

    if a.llm:
        cost = llm.tokens_in / 1e6 * 0.15 + llm.tokens_out / 1e6 * 0.60
        print(f"\n  호출 {llm.calls}회 · 약 ${cost:.4f} ({cost*1400:.0f}원)")
    print("═" * 78)
    print("  한 방식을 처음부터 끝까지 보려면:  python3 compare.py --full 증거파")
    print("  화면 순서대로 걸어 보려면:        python3 walk.py --auto")
    print("═" * 78)


if __name__ == "__main__":
    main()
