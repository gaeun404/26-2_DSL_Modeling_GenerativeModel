"""
대량 검증 하네스 — 폴더의 모든 시나리오를 verify + difficulty_gate로 돌려 집계.
시나리오가 쌓일수록(생성기 반복 실행) 통과율·자주 터지는 규칙을 한눈에 본다.
사용:
  python validate_batch.py                 # out/*.json + 루트 예시 전부
  python validate_batch.py "scenarios/*.json"    # glob 지정
"""
import json, glob, sys, collections
from verify import verify
from difficulty import difficulty_gate

def run(paths):
    n = vp = dp = bp = 0
    rulefail = collections.Counter()
    diffail = collections.Counter()
    for p in sorted(paths):
        try:
            s = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print(f"  ⛔ {p}: JSON 오류 {e}"); rulefail["JSON_PARSE"] += 1; n += 1; continue
        ok, report = verify(s)
        gok, greasons = difficulty_gate(s)
        n += 1; vp += ok; dp += gok; bp += (ok and gok)
        for rule, passed, msg in report:
            if not passed: rulefail[rule] += 1
        for r in greasons:
            diffail[r.split("(")[0].split("→")[0].strip()[:28]] += 1
        status = "✅ 둘다통과" if (ok and gok) else ("⚠️ 검증만" if ok else "❌ 검증실패")
        print(f"  {status}  {p}")

    print("\n" + "=" * 52)
    print(f"총 {n}편 | 검증통과 {vp} ({pct(vp,n)}) | 난이도통과 {dp} ({pct(dp,n)}) | 둘다 {bp} ({pct(bp,n)})")
    if rulefail:
        print("\n[검증 실패 항목]")
        for rule, c in rulefail.most_common(): print(f"  {c:>3}회  {rule}")
    if diffail:
        print("\n[난이도 미달 사유]")
        for r, c in diffail.most_common(): print(f"  {c:>3}회  {r}")
    print("=" * 52)
    return bp, n

def pct(a, b): return f"{100*a//b if b else 0}%"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        paths = glob.glob(sys.argv[1])
    else:
        paths = glob.glob("scenarios/*.json") + ["golden_sample.json", "scenario2.json", "scenario3.json"]
    run(paths)
