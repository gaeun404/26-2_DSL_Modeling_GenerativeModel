# -*- coding: utf-8 -*-
"""
relation_lint.py — 인물의 **서사와 관계가 실질을 갖췄는지** 검사한다.

왜 만들었나:
  실제 플레이에서 사또가 "서한동은 왜 자네를 해치려 하나?"라고 물었더니
  주인이 이렇게 답했다 — "서한동은 내 소작을 맡고 있어, 내가 그를 의심받을까 두려워하오."
  문장이 성립하지 않고, 세 인물 설명이 전부 비슷했다.

  원인은 모델이 아니라 카드였다. relationships가 자동 생성된 껍데기였다.
      "서한동(곳간과 소작을 맡은 마름). 옹서방을 둘러싸고 각자의 사정으로 얽힌 사이."
  참고할 사실이 없으니 모델이 지어낸다.

  → 관계는 **그 인물이 상대를 어떻게 보는지**, 무엇을 알고 무엇을 모르는지를
    구체적으로 적어야 한다. 그게 없으면 심문이 헛돈다.

검사 항목
  REL-covers      전원(다른 용의자 + 피해자)에 대한 서술이 있는가
  REL-depth       각 서술이 충분히 구체적인가(길이)
  REL-distinct    서술들이 서로 다른가(같은 문장 복붙이면 실격)
  REL-boilerplate 자동 생성 상투구가 남아 있지 않은가
  REL-concrete    구체 사실(과거·물건·시각·행위)이 담겼는가
  BIO-depth       life_story가 충분한가
  BIO-distinct    인물들의 life_story가 서로 구별되는가

사용:
    python relation_lint.py out/[0-9]*.json
    python relation_lint.py "scenarios/[0-9]*.json"      # 전 시나리오 한 표로
"""
import json, sys, glob, re, difflib

MIN_LEN = 45          # 관계 서술 최소 길이
MIN_BIO = 250         # life_story 최소 길이
BOILER = ["둘러싸고 각자의 사정으로 얽힌 사이", "관계가 있다", "아는 사이다"]
# 구체성의 표시 — 시간·수량·행위·물건이 언급되면 실질이 있다고 본다
CONCRETE = re.compile(r"(삼 년|지난해|그 밤|어제|열|몇|처음|다시|맡|빌|받|주|보|들|훔|팔|쫓|사|죽|"
                      r"밀리|앉|서성|캐|숨|잊|기억|약값|빚|장부|열쇠|문서|돈|은자|옷|위패|"
                      r"빼앗|잡|쥐|덮|끌|찍|적|넘|건네|시켰|다퉜|갚|약점|목격|마주)")
# 지난 일을 서술하는 문장(과거형 서술어)이 있으면 사연이 있는 것으로 본다.
# "…한 사이다", "…관계가 있다" 같은 상태 서술만으로는 걸리지 않는다.
ACTION = re.compile(r"(했|였|었|았|웠|겼|쳤|졌|랐|왔|썼)[다던고으]|하려|려 하|시키|맡기")


def lint(s):
    R = []
    def chk(name, cond, note=""):
        R.append((name, bool(cond), note))

    cast = s.get("cast", [])
    ids = {c["id"] for c in cast}
    vname = (s.get("victim") or {}).get("name", "")

    for c in cast:
        rel = c.get("relationships") or {}
        # 관계가 아닌 메모성 항목(victim_secret 등)은 검사 대상이 아니다
        rel = {k: v for k, v in rel.items() if k in ids or k == "victim"}
        who = f"{c['name']}({c['id']})"

        # 전원 + 피해자를 다루는가
        need = (ids - {c["id"]}) | {"victim"}
        miss = sorted(need - set(rel))
        chk(f"REL-covers[{c['id']}]", not miss,
            f"{who}: 빠진 상대 {miss}" if miss else f"{who}: {len(rel)}명")

        vals = [v for v in rel.values() if isinstance(v, str)]
        short = [k for k, v in rel.items() if isinstance(v, str) and len(v) < MIN_LEN]
        chk(f"REL-depth[{c['id']}]", not short,
            f"{who}: 너무 짧은 서술 {short} (최소 {MIN_LEN}자)")

        boiler = [k for k, v in rel.items()
                  if isinstance(v, str) and any(b in v for b in BOILER)]
        chk(f"REL-boilerplate[{c['id']}]", not boiler,
            f"{who}: 자동 생성 상투구 {boiler}")

        # 서로 다른 말인가 (복붙 탐지)
        dup = []
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                if difflib.SequenceMatcher(None, vals[i], vals[j]).ratio() >= 0.75:
                    dup.append((i, j))
        chk(f"REL-distinct[{c['id']}]", not dup,
            f"{who}: 거의 같은 서술 {len(dup)}쌍")

        vague = [k for k, v in rel.items()
                 if isinstance(v, str)
                 and not (CONCRETE.search(v) or ACTION.search(v))]
        chk(f"REL-concrete[{c['id']}]", not vague,
            f"{who}: 구체 사실이 없는 서술 {vague}")

        chk(f"BIO-depth[{c['id']}]", len(c.get("life_story") or "") >= MIN_BIO,
            f"{who}: life_story {len(c.get('life_story') or '')}자 (최소 {MIN_BIO})")

    # 인물들의 인생이 서로 구별되는가
    bios = [(c["id"], c.get("life_story") or "") for c in cast]
    sim = []
    for i in range(len(bios)):
        for j in range(i + 1, len(bios)):
            if difflib.SequenceMatcher(None, bios[i][1], bios[j][1]).ratio() >= 0.6:
                sim.append((bios[i][0], bios[j][0]))
    chk("BIO-distinct", not sim, f"비슷한 인생 {sim}")

    ok = all(c for _, c, _ in R)
    return ok, R


def _one(path, verbose=True):
    s = json.load(open(path, encoding="utf-8"))
    ok, R = lint(s)
    fails = [(n, note) for n, c, note in R if not c]
    if verbose:
        print(f"=== {s['meta']['title']} ===")
        if not fails:
            print("  ✅ 관계·서사 전부 실질을 갖춤")
        for n, note in fails:
            print(f"  ❌ {n}  — {note}")
        print(f"  총 {len(R)}항목 · 미달 {len(fails)}")
    return ok, len(R), len(fails)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    paths = sorted(glob.glob(arg))
    if len(paths) <= 1:
        _one(paths[0] if paths else arg)
    else:
        print(f"{'파일':26} {'미달':>5} {'주요 사유'}")
        print("-" * 78)
        tot_ok = 0
        for p in paths:
            s = json.load(open(p, encoding="utf-8"))
            ok, R = lint(s)
            fails = [(n, note) for n, c, note in R if not c]
            kinds = sorted({n.split("[")[0] for n, _ in fails})
            tot_ok += ok
            print(f"{p.split('/')[-1]:26} {len(fails):5}  {', '.join(kinds) if kinds else '—'}")
        print("-" * 78)
        print(f"통과 {tot_ok}/{len(paths)}편")
        print("REL-boilerplate = 자동 생성 상투구 / REL-depth = 서술이 짧음 / "
              "REL-concrete = 구체 사실 없음")
