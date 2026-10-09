# -*- coding: utf-8 -*-
"""
build.py — 시나리오 하나(또는 전부)를 **다시 빌드**한다.

스키마를 손으로 고친 뒤, 또는 src/의 도구를 고친 뒤에 돌린다.
파이프라인 순서는 src/hand_pipeline.sh에 적혀 있다.

    python3 build.py                      # 50편 전부 (몇 분 걸린다)
    python3 build.py 91_dsl_demo.json     # 한 편만
"""
import _boot, subprocess, sys, glob, os        # noqa: F401

args = [a for a in sys.argv[1:] if not a.startswith("-")]
files = ([a if "/" in a else f"scenarios/{a}" for a in args]
         or sorted(glob.glob("scenarios/[0-9]*.json")))
sh = os.path.join("src", "hand_pipeline.sh")
for i, f in enumerate(files, 1):
    print(f"[{i}/{len(files)}] {os.path.basename(f)}")
    subprocess.run(["bash", sh, f], stdout=subprocess.DEVNULL)
print("빌드 완료. python3 check.py 로 검증하세요.")
