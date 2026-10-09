# -*- coding: utf-8 -*-
"""
compare_audits.py — 여러 번 돌린 감사 결과를 **한 표로 놓고 비교한다.**

왜 필요한가
  audit.py는 한 번 돌릴 때마다 결과를 따로 남긴다. 그런데 우리가 알고 싶은 것은
  "이번이 지난번보다 나아졌나", "API가 로컬보다 나은가", "어느 질문 세트에서 무너지나"다.
  파일을 눈으로 대조하면 놓친다. 실제로 VOICE-ending이 9→4로 준 것도 손으로 셌다.

  같은 질문 세트를 돌렸다면 **턴 수가 같으니 그대로 비교**할 수 있고,
  다르면 100턴당으로 환산해서 견준다.

무엇을 보여주나
  ① 규칙별 건수 — 실행끼리 나란히, 늘고 준 것을 화살표로
  ② 질문 세트별 — 어느 심문 방식에서 무너지는가
  ③ 인물별 — 특정 인물만 계속 어긋나는가 (말체 배정이 잘못된 신호)
  ④ 새로 생긴 문제 / 사라진 문제

사용:
    python compare_audits.py audit_findings.json audit2_findings.json
    python compare_audits.py audit*_findings.json --label 이전,이후
"""
import json, sys, glob, os, collections


def load(path):
    """audit.py가 남긴 findings → (규칙별 건수, 세트별, 인물별, 턴 수)"""
    d = json.load(open(path, encoding="utf-8"))
    rule = collections.Counter()
    by_set = collections.defaultdict(collections.Counter)
    by_cast = collections.defaultdict(collections.Counter)
    turns = 0
    for fn, per in d.items():
        for cid, rows in per.items():
            for r in rows:
                if r.get("label") != "_tic":
                    turns += 1
                for k, _ in (r.get("bad") or []):
                    rule[k] += 1
                    by_set[r.get("label", "?")][k] += 1
                    by_cast[f"{fn[:6]}:{cid}"][k] += 1
    return rule, by_set, by_cast, turns


def _arrow(a, b):
    if a == b:
        return "  ="
    return f" {'▼' if b < a else '▲'}{abs(b-a)}"


def main(paths, labels):
    runs = [load(p) for p in paths]
    names = labels or [os.path.basename(p).replace("_findings.json", "") for p in paths]
    turns = [r[3] for r in runs]

    print(f"{'규칙':18}" + "".join(f"{n[:12]:>14}" for n in names))
    print(f"{'(턴 수)':18}" + "".join(f"{t:>14}" for t in turns))
    print("-" * (18 + 14 * len(runs)))
    allk = sorted({k for r in runs for k in r[0]},
                  key=lambda k: -sum(r[0][k] for r in runs))
    for k in allk:
        row = f"{k:18}"
        for i, r in enumerate(runs):
            v = r[0][k]
            # 턴 수가 다르면 100턴당으로 환산해 견준다
            per100 = v / turns[i] * 100 if turns[i] else 0
            cell = f"{v}({per100:.0f})"
            if i > 0:
                cell += _arrow(runs[i - 1][0][k], v)
            row += f"{cell:>14}"
        print(row)
    tot = [sum(r[0].values()) for r in runs]
    print("-" * (18 + 14 * len(runs)))
    print(f"{'합계':18}" + "".join(f"{t:>14}" for t in tot))

    if len(runs) >= 2:
        a, b = set(runs[0][0]), set(runs[-1][0])
        gone = sorted(k for k in a - b)
        new = sorted(k for k in b - a)
        if gone:
            print("\n사라진 문제:", ", ".join(gone))
        if new:
            print("새로 생긴 문제:", ", ".join(new))

    # 질문 세트별 — 어디서 무너지나
    last = runs[-1]
    if last[1]:
        print(f"\n[{names[-1]}] 질문 세트별")
        for st, c in sorted(last[1].items(), key=lambda x: -sum(x[1].values())):
            if not sum(c.values()):
                continue
            print(f"  {st:12} {sum(c.values()):3}건  "
                  + ", ".join(f"{k}×{v}" for k, v in c.most_common(3)))

    # 인물별 — 한 사람만 계속 어긋나면 배정이 잘못된 것이다
    if last[2]:
        worst = sorted(last[2].items(), key=lambda x: -sum(x[1].values()))[:5]
        if worst and sum(worst[0][1].values()):
            print(f"\n[{names[-1]}] 인물별 (많은 순)")
            for who, c in worst:
                if not sum(c.values()):
                    continue
                print(f"  {who:16} {sum(c.values()):3}건  "
                      + ", ".join(f"{k}×{v}" for k, v in c.most_common(2)))
            print("  ※ 한 인물에만 몰리면 그 인물의 말체 배정이 어긋났다는 신호다.")


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    labels = None
    for a in sys.argv[1:]:
        if a.startswith("--label"):
            labels = a.split("=", 1)[-1].split(",") if "=" in a else None
    if labels is None and "--label" in sys.argv:
        i = sys.argv.index("--label")
        if i + 1 < len(sys.argv):
            labels = sys.argv[i + 1].split(",")
            args = [x for x in args if x != sys.argv[i + 1]]
    paths = []
    for a in args:
        paths += sorted(glob.glob(a))
    if not paths:
        print("비교할 findings 파일이 없습니다. 예: python compare_audits.py audit_findings.json audit2_findings.json")
        sys.exit(1)
    main(paths, labels)
