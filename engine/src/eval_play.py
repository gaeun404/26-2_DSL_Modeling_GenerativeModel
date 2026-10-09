# -*- coding: utf-8 -*-
"""
eval_play.py — 편마다 **플레이어 에이전트가 한 판씩 돌고**, 추리게임으로서 되는지 표로 낸다.

왜 필요한가
  50편을 뽑고 나면 "게이트 통과"만으로는 모자라다. 실제로 놀아 봐야
  난이도가 맞는지, 좁혀 가는 맛이 있는지, 논리가 끝까지 이어지는지 안다.
  autoplay를 23~50편에 하나하나 돌리고 눈으로 읽는 것은 못 할 짓이라, 여기서 한 표로 모은다.

무엇을 재나 (판마다)
  정답    에이전트가 진범을 맞혔는가
  결정라운드 결정타를 몇 라운드에 쥐었는가 (마지막 라운드가 정상)
  좁힘    라운드별 남은 용의자 수 — 5→3→2→1처럼 줄어야 재미다. 안 줄면 '평평'
  압박    결정타를 들이대고 몰아붙였을 때 범인이 무너지는가
  점수    채점(범인 5 + 비밀 각 1)
  헛라운드  아무 단서도 안 나온 라운드 수 (0이어야 한다)
  선두교체  의심 1위가 판 중에 바뀐 횟수 (0이면 처음부터 뻔했다는 뜻)

사용:
    python eval_play.py                # out/ 전부
    python eval_play.py out/2[4-9]*.json out/[3-5]*.json   # 새로 뽑은 편만
    python eval_play.py --api          # 대사까지 (ANTHROPIC/OpenAI 키 필요)
    python eval_play.py --out 플레이평가.md
"""
import json, sys, os, glob, io, re, argparse, contextlib, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")


def one(path, llm=None):
    """한 판 돌리고 지표를 뽑는다. autoplay의 기록(markdown)을 파싱한다."""
    import autoplay
    s = json.load(open(path, encoding="utf-8"))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        text = autoplay.run(s, llm, out=None)
    rounds = (s.get("config") or {}).get("rounds", 3)
    cast_n = len(s["cast"])

    correct = "맞았다" in text
    m = re.search(r"점수 (\d+)/(\d+)", text)
    pts, mx = (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    # 결정타를 쥔 라운드
    dec_round = None
    cur = 0
    for line in text.splitlines():
        h = re.match(r"## (\d+)라운드", line)
        if h:
            cur = int(h.group(1))
        if "★결정타" in line and dec_round is None:
            dec_round = cur

    # 라운드별 판단 줄 → 남은 용의자 수 + 선두
    narrowing, leaders = [], []
    for line in text.splitlines():
        if line.startswith("*") and "판단:" in line:
            names = re.findall(r"([^\s·*]+) (-?\d+\.\d)", line)
            narrowing.append(len(names))
            if names:
                leaders.append(names[0][0])
    lead_changes = sum(1 for a, b in zip(leaders, leaders[1:]) if a != b)

    # 헛라운드 — 단서 줄(`- \`)이 하나도 없는 라운드
    empty_rounds = 0
    blocks = re.split(r"## \d+라운드", text)[1:]
    for b in blocks:
        got = re.findall(r"^- `", b, flags=re.M)
        if not got:
            empty_rounds += 1

    breaks = "무너진다" in text
    flat = len(narrowing) >= 2 and narrowing[0] == narrowing[-1]

    verdict = []
    if not correct:
        verdict.append("오답")
    if dec_round is not None and dec_round != rounds:
        verdict.append(f"결정타가 {dec_round}R에 샘")
    if empty_rounds:
        verdict.append(f"헛라운드 {empty_rounds}")
    if flat:
        verdict.append("좁힘 없음(평평)")
    if not breaks:
        verdict.append("범인이 안 무너짐")
    if lead_changes == 0 and correct:
        verdict.append("처음부터 뻔함(선두교체 0)")

    return {
        "file": os.path.basename(path).replace(".json", ""),
        "title": s["meta"].get("title", ""),
        "rounds": rounds, "cast": cast_n,
        "correct": correct, "score": f"{pts}/{mx}",
        "dec_round": dec_round,
        "narrowing": "→".join(str(x) for x in narrowing) or "-",
        "lead_changes": lead_changes,
        "empty_rounds": empty_rounds,
        "breaks": breaks,
        "difficulty": (s.get("difficulty") or {}).get("label", ""),
        "issues": verdict,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    paths = []
    for x in (a.paths or ["scenarios/[0-9]*.json"]):
        paths += sorted(glob.glob(x))
    llm = None
    if a.api:
        from llm_api import ApiLLM
        llm = ApiLLM(max_new_tokens=260)

    rows, fails = [], []
    for p in paths:
        try:
            rows.append(one(p, llm))
        except Exception as e:
            fails.append((p, f"{type(e).__name__} {e}"))

    W = f"{'편':24}{'정답':4}{'점수':7}{'결정R':5}{'좁힘':14}{'교체':4}{'헛R':4}{'붕괴':4} 문제"
    L = [W, "-" * 90]
    for r in rows:
        L.append(f"{r['file'][:22]:24}"
                 f"{'○' if r['correct'] else '✗':4}"
                 f"{r['score']:7}"
                 f"{str(r['dec_round'] or '-'):5}"
                 f"{r['narrowing']:14}"
                 f"{r['lead_changes']:^4}"
                 f"{r['empty_rounds']:^4}"
                 f"{'○' if r['breaks'] else '✗':4}"
                 f" {'; '.join(r['issues']) or '—'}")
    ok = sum(1 for r in rows if not r["issues"])
    L.append("-" * 90)
    L.append(f"문제 없음 {ok}/{len(rows)}편"
             + (f" · 실행 실패 {len(fails)}" if fails else ""))
    for p, e in fails:
        L.append(f"  ✗ {p}: {e[:80]}")
    text = "\n".join(L)
    print(text)
    if a.out:
        md = ["# 플레이 평가", "",
              f"에이전트가 {len(rows)}편을 한 판씩 돌았다. 문제 없음 **{ok}/{len(rows)}편**", "",
              "| 편 | 정답 | 점수 | 결정타 라운드 | 좁힘 | 선두교체 | 헛라운드 | 붕괴 | 문제 |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            md.append(f"| {r['title']} | {'○' if r['correct'] else '✗'} | {r['score']} | "
                      f"{r['dec_round'] or '-'} | {r['narrowing']} | {r['lead_changes']} | "
                      f"{r['empty_rounds']} | {'○' if r['breaks'] else '✗'} | "
                      f"{'; '.join(r['issues']) or '—'} |")
        open(a.out, "w", encoding="utf-8").write("\n".join(md))
        print(f"\n저장: {a.out}")


if __name__ == "__main__":
    main()
