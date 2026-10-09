# -*- coding: utf-8 -*-
"""
novelize.py — **판정자가 놀고 간 판을 소설처럼 읽게 만든다.**

  python3 novelize.py log.json                 # 여섯 판 전부
  python3 novelize.py log.json --who 심리       # 한 판만
  python3 novelize.py log.json --out 판.md      # 파일로

■ 왜
  log.json 은 기계가 읽을 것으로 쌓여 있어 사람이 읽기 어렵다.
  판이 어떻게 흘렀는지 — 무엇을 뒤졌고, 무엇을 보고 누구를 물었고,
  그 자리에서 무엇이 흔들렸고, 끝에 누구를 짚었는지 — 를
  **한 밤의 이야기**로 이어 붙인다. 수치는 맨 끝에 한 줄로만 둔다.
"""
import json, sys, argparse, collections

W = 78


def _j(w, pair="을/를"):
    """받침을 보고 조사를 고른다 — 'S2이(가) 나왔다'가 나오던 자리."""
    a, b = pair.split("/")
    ch = str(w or " ")[-1]
    if "0" <= ch <= "9":
        ch = {"0": "영", "1": "일", "2": "이", "3": "삼", "4": "사",
              "5": "오", "6": "육", "7": "칠", "8": "팔", "9": "구"}[ch]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


def _cut(x, n):
    x = str(x or "").replace("\n", " ").strip()
    return x if len(x) <= n else x[:n - 1] + "…"


_MEAN = {
    "ANSWER": "순순히 답했다",
    "DEFLECT": "말을 돌렸다",
    "FLINCH": "말이 흔들렸다",
    "ADMIT": "끝내 털어놓았다",
    "BREAK": "무너졌다",
}


def one(lg, wide=False):
    who = lg["who"]
    out = [f"\n{'═' * W}", f"  {who}의 밤", f"{'═' * W}"]
    dial = {(d["r"], d["cast"], d["q"]): d for d in (lg.get("dialogue") or [])}

    rnd = 0
    for j in lg.get("journal") or []:
        r = j.get("r") or 1
        if r != rnd:
            rnd = r
            out.append(f"\n── {rnd}라운드 ──")
        did = j.get("did")
        base = j.get("근거") or "—"
        if did == "뒤졌다":
            got = j.get("얻은 것")
            got = ", ".join(got) if isinstance(got, list) else (got or "")
            where = j.get("어디", "")
            line = f"  {where}{_j(where)} 뒤졌다."
            line += (f" {got}{_j(got, '이/가')} 나왔다." if got else " 나오는 것이 없었다.")
            if base not in ("—", "규칙"):
                line += f"  (무엇을 보고: {base})"
            out.append(line)
        elif did == "물었다":
            nm = j.get("누구", "")
            q = j.get("질문", "")
            k = j.get("단서")
            head = f"  {nm}에게 물었다"
            head += f" — 「{_cut(q, 70 if wide else 46)}」"
            if k:
                head += f"  [{k}{_j(k)} 내밀며]"
            out.append(head)
            d = next((v for kk, v in dial.items() if kk[1] == nm and _cut(kk[2], 20) in str(q)[:40]), None)
            if d and d.get("a") and wide:
                out.append(f"       “{_cut(d['a'], 300)}”")
            out.append(f"       → {_MEAN.get(j.get('반응'), j.get('반응',''))}"
                       + (f" · 압박 {d['gauge']}" if d and d.get("gauge") is not None else ""))
            got = j.get("얻은 것")
            if got:
                for x in (got if isinstance(got, list) else [got]):
                    out.append(f"       ★비밀이 열렸다 — {_cut(x, 60)}")
        elif did == "맞대 놓았다":
            out.append(f"  {j.get('누구','')}를 맞대 놓았다 — 「{_cut(j.get('질문'), 50)}」")
            if j.get("얻은 것"):
                out.append(f"       → {_cut(j['얻은 것'], 70)}")

    cx = lg.get("confront")
    if cx and cx.get("lines"):
        out.append(f"\n  [그 자리 — {cx['a']} ↔ {cx['b']}]")
        for nm, beat, line in cx["lines"]:
            out.append(f"    [{beat}] {nm}: {_cut(line, 66)}")
        if cx.get("note"):
            out.append(f"    드러난 것 — {_cut(cx['note'], 66)}")

    r = lg["result"]
    v = lg.get("verdict") or {}
    out.append(f"\n── 이름을 대다 ──")
    out.append(f"  「{r['named']}」  {'— 맞았다.' if r['correct'] else '— 빗나갔다.'}")
    if v.get("why"):
        out.append(f"  까닭 — {v['why']}")
    if lg.get("secrets"):
        out.append(f"  연 비밀 {len(lg['secrets'])}개")
        for x in lg["secrets"]:
            out.append(f"    · {x['cast']} ({x['how']}) — {_cut(x['text'], 56)}")
    else:
        out.append("  연 비밀 없음 — 다섯 사람 모두 감춘 채로 밤이 끝났다.")
    mv = r["moves"]
    out.append(f"  「{r['points']}점」 · 단서 {r['clues']} · "
               f"탐색 {mv.get('search',0)} · 심문 {mv.get('ask',0)} · 대질 {mv.get('confront',0)}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--who", nargs="*", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--wide", action="store_true", help="대사까지 길게 (기록에 있을 때)")
    a = ap.parse_args()

    logs = json.load(open(a.log, encoding="utf-8"))
    if a.who:
        logs = [l for l in logs if l["who"] in a.who]

    parts = []
    n_sec = collections.Counter()
    for lg in logs:
        parts.append(one(lg, wide=a.wide))
        n_sec[lg["who"]] = len(lg.get("secrets") or [])

    tot = ["\n" + "═" * W, "  여섯 밤을 나란히 놓고", "═" * W]
    hit = sum(1 for l in logs if l["result"]["correct"])
    tot.append(f"  이름을 맞힌 판 {hit}/{len(logs)}")
    tot.append("  연 비밀 — " + " · ".join(f"{k} {v}" for k, v in n_sec.items()))
    body = "\n".join(parts + tot)

    if a.out:
        open(a.out, "w", encoding="utf-8").write(body)
        print(f"  {a.out} 에 적었다 ({len(body):,}자)")
    else:
        print(body)


if __name__ == "__main__":
    main()
