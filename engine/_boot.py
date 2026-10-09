# -*- coding: utf-8 -*-
"""공통 부트스트랩 — 어느 폴더에서 실행하든 저장소 뿌리를 기준으로 잡는다."""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)                       # scenarios/ · docs/ 상대경로가 늘 맞는다
sys.path.insert(0, os.path.join(ROOT, "src"))
os.makedirs(".runtime", exist_ok=True)
