# -*- coding: utf-8 -*-
"""
playtest.py — **실제 LLM으로** 한 판을 끝까지 돌린다. OpenAI 키가 필요하다.

키는 저장소 뿌리의 `.apikey` 파일에서 읽는다(깃에 올라가지 않는다).
    echo "sk-..." > .apikey

    python3 playtest.py                      # 91편 3라운드
    python3 playtest.py --rounds 2           # 비용 절약
    python3 playtest.py --style 증거파
"""
import _boot, os, sys                          # noqa: F401

if not os.path.exists(".apikey") and not os.environ.get("MM_API_KEY"):
    print("키가 없습니다. 저장소 뿌리에 .apikey 파일을 두거나 MM_API_KEY를 설정하세요.")
    sys.exit(1)

import llm_playtest                            # noqa: E402
sys.argv = [sys.argv[0]] + sys.argv[1:]
llm_playtest.main()
