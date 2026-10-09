# -*- coding: utf-8 -*-
"""
secret_clue.py — **비밀을 여는 단서를 그 비밀에 맞게 다시 짝짓는다.**

■ 왜 (2026-08-25)
  비밀은 `secrets[].forced_by`에 적힌 단서를 **손에 쥐고 들이대야** 열린다.
  그런데 그 짝이 번호 순으로 매겨져 있어, 내용이 서로 맞지 않는 자리가 많았다.

      노하람의 비밀 : 방학 유럽여행 항공권을 이미 결제했다
      여는 단서 K0  : 학회 노션 자기소개 페이지 — '좋아하는 향: 니코틴'(유가람)…
                      → 항공권 이야기가 한 글자도 없다

  플레이어는 단서 본문을 읽고 "이건 저 사람 이야기구나" 하고 내민다.
  본문에 그 사람의 낱말이 없으면 **내밀 근거가 없다.** 찍기가 된다.
  전 50편에서 비밀을 여는 장소 단서 256개 중 51개(20%)가 이 꼴이었고,
  그래서 한 판에 비밀이 0~1개밖에 안 열렸다.

■ 어떻게
  비밀 본문 + 트리거 낱말과 **가장 많이 겹치는 단서**로 다시 짝짓는다.
  한 단서가 두 비밀을 열지 않도록 욕심내지 않고 하나씩 나눠 가진다.
  이미 잘 맞는 짝은 건드리지 않는다.

  ★소지품(B*)은 그대로 둔다 — 그건 실토로 얻는 두 번째 경로다.
  ★맞는 단서가 없으면 **바꾸지 않고 남겨 둔다.** 억지로 붙이면 더 나쁘다.
    남은 것은 화면에 보고되므로, 시나리오를 손볼 때 참고한다.

사용:
    python3 secret_clue.py                    # 전 편
    python3 secret_clue.py --check            # 고치지 않고 점검만
    python3 secret_clue.py out/91_dsl_demo.json
"""
import json, glob, re, sys

SEARCHABLE = ("location", "record", "physical")
_STOP = {"있다", "있었다", "했다", "하는", "그것", "이것", "사람", "그날", "그때",
         "때문", "이라", "라고", "한다", "된다", "되었", "위해", "대해", "않았",
         "않는", "이다", "라는", "하고", "에서", "에게", "으로"}


def _words(t):
    return {w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", str(t or ""))
            if w not in _STOP}


def _score(sec, c, cl):
    """이 단서가 이 비밀을 여는 것으로 **알아볼 수 있는가.**"""
    surf = cl.get("surface", "")
    sw = _words(surf)
    if not sw:
        return 0
    trig = {x for pp in (c.get("pressure_points") or [])
            for x in (pp.get("trigger") or []) if x}

    n = 0
    # ① 트리거 낱말이 본문에 그대로 있으면 가장 강한 표지다
    n += 6 * sum(1 for x in trig if x and x in surf)
    # ② 비밀 본문과 겹치는 낱말
    n += 2 * len(_words(sec.get("text")) & sw)
    # ③ 이름이 적혀 있으면 확실하다
    if c["name"] in surf:
        n += 5
    # ④ 그 사람의 방에서 나오는 단서면 조금 더
    return n


def remap(path, check=False):
    s = json.load(open(path, encoding="utf-8"))
    cg = {cl["id"]: cl for cl in s.get("clue_graph", [])}
    pool = [cl for cl in s.get("clue_graph", [])
            if cl.get("channel") in SEARCHABLE and not cl.get("decisive")]

    # ① 지금 짝이 얼마나 맞는지 먼저 잰다
    want = []                       # (점수, 인물, 비밀, 단서) — 다시 붙일 후보
    keep = set()                    # 이미 잘 맞아 그대로 두는 단서
    for c in s["cast"]:
        for sec in (c.get("secrets") or []):
            cur = [x for x in (sec.get("forced_by") or []) if x in cg]
            best_cur = max((_score(sec, c, cg[x]) for x in cur), default=0)
            if best_cur >= 6:                     # 트리거가 본문에 있다 — 좋은 짝
                keep.update(cur)
                continue
            for cl in pool:
                v = _score(sec, c, cl)
                if v >= 6:
                    want.append((v, c, sec, cl))

    # ② 점수가 높은 짝부터 나눠 가진다 — 한 단서는 한 비밀만 연다
    want.sort(key=lambda x: -x[0])
    used, done, fixed = set(keep), set(), []
    for v, c, sec, cl in want:
        k = (c["id"], sec.get("text", "")[:20])
        if k in done or cl["id"] in used:
            continue
        old = [x for x in (sec.get("forced_by") or []) if x in cg]
        new = [x for x in (sec.get("forced_by") or []) if x not in cg]   # 소지품은 남긴다
        sec["forced_by"] = [cl["id"]] + new
        used.add(cl["id"]); done.add(k)
        fixed.append((c["name"], old[0] if old else "-", cl["id"]))

    # ③ 아직도 못 찾은 것
    blind = []
    for c in s["cast"]:
        for sec in (c.get("secrets") or []):
            cur = [x for x in (sec.get("forced_by") or []) if x in cg]
            if not cur or max(_score(sec, c, cg[x]) for x in cur) < 6:
                blind.append(c["name"])

    if not check and fixed:
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    tag = f"다시 짝지음 {len(fixed)}"
    if blind:
        tag += f" · 아직 겨냥 불가 {len(blind)}({', '.join(blind)})"
    print(f"  {path.split('/')[-1][:28]:30s} {tag}")
    for nm, a, b in fixed:
        print(f"      {nm} : {a} → {b}")
    return len(fixed), len(blind)



# ── 겨냥할 표지가 없는 비밀에 한 줄을 붙인다 ──────────────────────────
#   짝을 아무리 다시 지어도, 그 비밀을 가리키는 단서가 **아예 없는** 편이 있다.
#   91편에서 노하람의 비밀은 '항공권'인데 단서 어디에도 항공권 이야기가 없었다.
#   그런 자리에는 이미 있는 단서에 **한 줄만** 덧붙인다 — 새 단서를 만들지 않는다.
#   붙이는 말은 그 단서의 매체에 맞춘다(문서면 '적혀 있다', 물건이면 '나왔다').
_MARK = {
    "record":   "같은 자리에 {t}에 관한 줄이 하나 더 있다.",
    "location": "그 곁에 {t}에 관한 자취가 남아 있다.",
    "physical": "그것과 함께 {t}에 관한 것이 나왔다.",
}


def mark_blind(path, check=False):
    s = json.load(open(path, encoding="utf-8"))
    cg = {cl["id"]: cl for cl in s.get("clue_graph", [])}
    added = []
    for c in s["cast"]:
        for sec in (c.get("secrets") or []):
            cur = [x for x in (sec.get("forced_by") or []) if x in cg]
            if not cur:
                continue
            if max(_score(sec, c, cg[x]) for x in cur) >= 6:
                continue                       # 이미 겨냥할 수 있다
            cl = cg[cur[0]]
            trig = [x for pp in (c.get("pressure_points") or [])
                    for x in (pp.get("trigger") or [])
                    if x and x not in cl.get("surface", "")]
            if not trig:
                continue
            tail = _MARK.get(cl.get("channel"), _MARK["record"]).format(t=trig[0])
            surf = (cl.get("surface") or "").rstrip()
            if not surf.endswith((".", "…", "!")):
                surf += "."
            cl["surface"] = surf + " " + tail
            added.append((c["name"], cl["id"], trig[0]))
    if not check and added:
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for nm, cid, tg in added:
        print(f"      + {nm} ← {cid} : …{tg}")
    return len(added)


if __name__ == "__main__":
    check = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    f_tot = b_tot = m_tot = 0
    for f in files:
        a, b = remap(f, check)
        f_tot += a; b_tot += b
        if b and "--mark" in sys.argv:
            m_tot += mark_blind(f, check)
    print(f"\n{len(files)}편 · 다시 짝지은 비밀 {f_tot}개 · 겨냥 불가였던 것 {b_tot}개"
          + (f" · 표지를 붙인 것 {m_tot}개" if "--mark" in sys.argv else ""))
