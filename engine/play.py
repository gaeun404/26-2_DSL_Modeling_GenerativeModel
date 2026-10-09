# -*- coding: utf-8 -*-
"""
play.py — **키 없이** 한 판을 돌려 본다.

용의자가 언제 흔들리고 언제 실토하는지는 코드(stance + pressure)가 정하므로,
LLM 없이도 게임이 굴러가는 모습을 그대로 볼 수 있다. 대사만 자리표시자로 나온다.

    python3 play.py                          # 91편, 정공법
    python3 play.py 38_cinderella.json
    python3 play.py --style 탐색파 --rounds 2
    python3 play.py --list                   # 시나리오 목록
"""
import _boot, sys, glob, json, argparse       # noqa: F401


class _Stub:
    """대사 대신 자리표시자를 돌려준다. 판이 굴러가는지만 본다."""
    calls = tokens_in = tokens_out = 0

    def chat(self, msgs):
        _Stub.calls += 1
        return "(대사는 LLM이 만든다 — playtest.py를 쓰면 실제 문장이 나온다)"


def main():
    import llm_playtest as L
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", nargs="?", default="91_dsl_demo.json")
    ap.add_argument("--style", default="정공법", help=" / ".join(L.STYLES))
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        cat = json.load(open("scenarios/catalog.json", encoding="utf-8"))
        for c in cat.get("cases", []):
            print(f"  {c.get('file',''):28} {c.get('title','')}")
        return

    path = a.scenario if "/" in a.scenario else f"scenarios/{a.scenario}"
    if not glob.glob(path):
        print(f"그런 시나리오가 없습니다: {path}\n  python3 play.py --list 로 목록을 봅니다.")
        sys.exit(1)
    L.run(path, _Stub(), rounds=a.rounds, verbose=True, style=a.style)


if __name__ == "__main__":
    main()
