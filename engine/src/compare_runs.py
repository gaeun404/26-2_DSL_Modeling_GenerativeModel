# -*- coding: utf-8 -*-
"""compare_runs.py — 회차 간 에이전트 검증 결과를 '정규화해서' 비교한다.

왜 필요한가:
  1회차는 시나리오 1편(용의자 5명 × 14문항 = 70턴), 2회차는 2편(140턴)이다.
  문제 '건수'를 그대로 비교하면 2회차가 무조건 나빠 보인다.
  그래서 **100턴당 문제 수**로 환산해 비교한다.

사용:
    python compare_runs.py out_stress/summary.json
    python compare_runs.py out_stress/summary.json --baseline baseline_run1.json
"""
import json, sys, argparse, os

QUESTIONS_PER_SUSPECT = 14
SUSPECTS_PER_SCENARIO = 5

# 1회차(수정 전) 실측치 — 시나리오 1편(19_장화홍련), 70턴 기준
BASELINE = {
    "note": "1회차 · 프롬프트 수정 전 · 19_장화홍련 1편(70턴)",
    "scenarios": ["19_장화홍련.json"],
    "models": [
        {"model": "Qwen/Qwen2.5-3B-Instruct", "issues": 14,
         "by_type": {"persona_break": 5, "false_premise": 2, "repeat": 2, "secret_leak": 1}},
        {"model": "Qwen/Qwen2.5-7B-Instruct", "issues": 24,
         "by_type": {"persona_break": 9, "garbled": 5, "repeat": 4, "false_premise": 2}},
        {"model": "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct", "issues": None, "by_type": {}},
    ],
}

# 치명도 — 게임을 실제로 망가뜨리는 정도
SEVERITY = {
    "false_confess": "치명", "spoiler_leak": "치명", "secret_leak": "치명",
    "persona_break": "높음", "out_of_knowledge": "높음", "contradiction": "높음",
    "false_premise": "높음", "fabrication": "높음", "never_breaks": "높음",
    "timeline_break": "중간", "garbled": "중간", "refusal_spam": "중간",
    "repeat": "낮음", "register_break": "낮음", "meta_echo": "낮음", "off_topic": "낮음",
}
ORDER = ["치명", "높음", "중간", "낮음", "-"]


def turns(summ):
    return len(summ.get("scenarios", [])) * SUSPECTS_PER_SCENARIO * QUESTIONS_PER_SUSPECT


def rate(n, t):
    return None if (n is None or not t) else n * 100.0 / t


def show(summ, title):
    t = turns(summ)
    print(f"\n{title}")
    print(f"  시나리오 {len(summ.get('scenarios', []))}편 · 총 {t}턴"
          + (f"  ({summ['note']})" if summ.get("note") else ""))
    print(f"  {'모델':42} {'건수':>5} {'100턴당':>8}")
    print("  " + "-" * 58)
    for m in summ["models"]:
        n = m.get("issues")
        if n is None:
            print(f"  {m['model']:42} {'로딩실패':>5}")
            continue
        print(f"  {m['model']:42} {n:5} {rate(n, t):8.1f}")


def diff(cur, base):
    tc, tb = turns(cur), turns(base)
    bym = {m["model"]: m for m in base["models"]}
    print(f"\n{'=' * 74}")
    print("=== 회차 비교 (100턴당 문제 수 · 낮을수록 좋음) ===")
    print(f"  {'모델':42} {'수정전':>8} {'수정후':>8} {'변화':>10}")
    print("  " + "-" * 70)
    for m in cur["models"]:
        b = bym.get(m["model"])
        rc = rate(m.get("issues"), tc)
        rb = rate(b.get("issues"), tb) if b else None
        if rc is None:
            print(f"  {m['model']:42} {'-':>8} {'로딩실패':>8}"); continue
        if rb is None:
            print(f"  {m['model']:42} {'신규':>8} {rc:8.1f} {'(기준 없음)':>12}"); continue
        d = rc - rb
        mark = "개선" if d < -0.5 else ("악화" if d > 0.5 else "동일")
        print(f"  {m['model']:42} {rb:8.1f} {rc:8.1f} {d:+7.1f} {mark}")

    # ── 유형별 ────────────────────────────────────────────────────
    # ★ 두 회차에 **공통으로 등장한 모델만** 쓴다.
    #   회차마다 모델 수가 다르면(2개 vs 3개) 총합을 그냥 나눌 수 없다.
    common = [m["model"] for m in cur["models"]
              if m["model"] in bym and m.get("issues") is not None
              and bym[m["model"]].get("issues") is not None]
    if not common:
        print("\n[유형별 생략] 두 회차에 공통으로 성공한 모델이 없습니다.")
        return
    cm = [m for m in cur["models"] if m["model"] in common]
    bm = [bym[k] for k in common]
    # 분모 = 턴 수 × 모델 수
    dc, db = tc * len(cm), tb * len(bm)
    print(f"\n=== 유형별 (100턴당 · 공통 모델 {len(common)}개 기준) ===")
    print("  대상: " + ", ".join(m.split("/")[-1] for m in common))
    kinds = set()
    for m in cm + bm:
        kinds |= set(m.get("by_type") or {})
    def sev(k): return (ORDER.index(SEVERITY.get(k, "-")), k)
    print(f"  {'유형':16} {'치명도':>6} {'수정전':>8} {'수정후':>8} {'변화':>8}")
    print("  " + "-" * 52)
    for k in sorted(kinds, key=sev):
        cb = sum((m.get("by_type") or {}).get(k, 0) for m in bm)
        cc = sum((m.get("by_type") or {}).get(k, 0) for m in cm)
        nb, nc = rate(cb, db), rate(cc, dc)
        print(f"  {k:16} {SEVERITY.get(k,'-'):>6} {nb:8.1f} {nc:8.1f} {nc-nb:+8.1f}")

    # 이번 회차에만 있는 모델은 따로 (기준이 없으므로 비교 불가)
    extra = [m for m in cur["models"] if m["model"] not in common and m.get("issues") is not None]
    if extra:
        print(f"\n=== 이번 회차 신규 모델 (100턴당 · 비교 기준 없음) ===")
        for m in extra:
            bt = m.get("by_type") or {}
            top = ", ".join(f"{k} {rate(v,tc):.1f}" for k, v in
                            sorted(bt.items(), key=lambda x: (ORDER.index(SEVERITY.get(x[0],'-')), -x[1]))[:5])
            print(f"  {m['model']}  총 {rate(m['issues'],tc):.1f}\n    {top}")

    print(f"\n[읽는 법]")
    print("  · garbled 가 0에 가까워졌으면 → 회피 예문의 희귀 토큰이 원인이었다는 진단이 맞은 것")
    print("  · persona_break 가 크게 줄고 meta_echo 가 그만큼 늘었으면 → 대부분 판정기 오판이었던 것")
    print("  · persona_break 와 meta_echo 가 둘 다 줄었으면 → 함정방어 5항 강화가 실제로 먹힌 것")
    print("  · 모델 간 격차가 크면 '모델 크기' 문제, 비슷하면 '프롬프트·설계' 문제")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary", nargs="?", default="out_stress/summary.json")
    ap.add_argument("--baseline", default="", help="이전 회차 summary.json (없으면 내장 1회차 실측치)")
    a = ap.parse_args()

    if not os.path.exists(a.summary):
        print(f"[오류] {a.summary} 없음 — 잡이 아직 안 끝났을 수 있습니다."); sys.exit(1)
    cur = json.load(open(a.summary, encoding="utf-8"))
    base = json.load(open(a.baseline, encoding="utf-8")) if a.baseline else BASELINE

    show(base, "── 이전 회차 (수정 전)")
    show(cur, "── 이번 회차 (수정 후)")
    diff(cur, base)


if __name__ == "__main__":
    main()
