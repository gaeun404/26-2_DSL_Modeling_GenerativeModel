# -*- coding: utf-8 -*-
"""
check.py — 검증 전부를 한 번에 돌린다. 키가 필요 없다.

    python3 check.py            # 여덟 가지 전부
    python3 check.py --fast     # 무거운 몬테카를로는 건너뛴다
"""
import _boot, subprocess, sys, os              # noqa: F401

FAST = "--fast" in sys.argv
SUITE = [
    ("run_all",       "논리·난이도·플레이가능·비밀도달·UX·관계 + 54항목", not FAST),
    ("fe_lint",       "프론트 연동 9개 항목", True),
    ("ux_lint",       "게임 요소가 실제로 작동하는가", True),
    ("eval_play",     "한 판이 끝까지 굴러가는가", True),
    ("eval_policies", "성급한 지목이 맞아떨어지지 않는가", True),
    ("relation_lint", "관계 서술이 상투구가 아닌가", True),
    ("agent_lint",    "인물 카드에 자백 어휘가 새지 않았는가", True),
]

bad = 0
for name, what, run in SUITE:
    if not run:
        print(f"  ⏭  {name:15} {what}  (--fast 로 건너뜀)")
        continue
    p = subprocess.run([sys.executable, os.path.join("src", f"{name}.py")],
                       capture_output=True, text=True)
    tail = [x for x in p.stdout.strip().split("\n") if x.strip()][-1:] or [""]
    print(f"  {'✅' if p.returncode == 0 else '❌'} {name:15} {tail[0].strip()[:66]}")
    bad += (p.returncode != 0)

print("\n검증 완료." if not bad else f"\n실패 {bad}건 — 위 항목을 보세요.")
sys.exit(1 if bad else 0)
