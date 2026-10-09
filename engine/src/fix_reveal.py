# -*- coding: utf-8 -*-
"""fix_reveal.py — **진상 낭독과 재연 자막을 사람 말로 다시 쓴다.**

■ 왜 (2026-08-30, 제보 — "마지막에 사건 설명이랑 재연도 말투가 너무 AI 티가 나")

  진상 낭독은 시나리오 조각에 **틀에 박힌 접속구를 붙여** 만들고 있었다.
  그래서 50편이 같은 문장을 쓴다 —

      "이 밤의 모든 어긋남이 그 한 사람에게로 모인다."      ← 50편 전부
      "까닭은 이것이다."                                    ← 50편 전부
      "그리고 {범인}은 자기 자리를 만들어 두었다 —"          ← 50편 전부
      "아무도 그 걸음을 세지 않았다."                        ← 조건이 없으면
      "완벽에 가장 가까웠던 밤이다 — 가장 가까웠을 뿐이다."   ← 다섯 개 돌려쓰기

  전부 **뜻은 없고 분위기만 있는 말**이다. 사건을 설명하는 자리에서
  설명 대신 여운을 넣으면, 한 시간 파고든 사람이 마지막에 아무것도 못 듣는다.

  게다가 조각을 붙이다 보니 같은 말이 두 번 나왔다 —
      "시간차 독살 — 암전 15분. 암전 15분 — 홍보 영상 시사 동안…"

■ 어떻게 바꾸나
  실제 추리물의 진상 파트는 **형사가 사건을 정리해 읽는 투**다.
  수식 없이, 순서대로, 확인할 수 있는 사실만. 여운은 이야기가 알아서 만든다.

      누가 죽였나 → 왜 → 어떤 수법으로 → 그 사이 자기는 어디에 있었나 → 무엇에 걸렸나

  없는 사실은 지어내지 않는다. 전부 시나리오가 이미 들고 있는 값이다.
"""
import json, glob, re, os, argparse

_NOUN_END = re.compile(r"(됨|함|음|짐|림|김)\s*$")


def _fin(t):
    """명사형으로 끝나는 조각을 문장으로 — '발견됨' → '발견됐다'."""
    t = str(t or "").strip().rstrip(".")
    if not t:
        return ""
    m = _NOUN_END.search(t)
    if m:
        tail = {"됨": "됐다", "함": "했다", "음": "었다", "짐": "졌다",
                "림": "렸다", "김": "겼다"}[m.group(1)]
        t = t[:m.start()] + tail
    # ★없는 어미를 붙이지 않는다. 「…'S' 표시」에 '다'를 붙이면 「표시다」가 된다.
    #   수사 요약문은 명사구로 끝나도 어색하지 않다 — 그대로 둔다.
    return t + ("" if t.endswith(("…", ")", "'", '"', "」")) else ".")


def _j(w, pair):
    a, b = pair.split("/")
    ch = str(w or " ")[-1]
    if not ("가" <= ch <= "힣"):
        return a
    return a if (ord(ch) - 0xAC00) % 28 else b


def _clean(t):
    return re.sub(r"\s+", " ", str(t or "")).strip()


def _dedupe(name, cond):
    """'시간차 독살 — 암전 15분' 뒤에 '암전 15분 — …'이 또 오는 것을 막는다."""
    name = _clean(name)
    cond = _clean(cond)
    head = re.split(r"\s*[—–-]\s*", name)[0].strip()
    tail = name[len(head):].strip(" —–-")
    if tail and cond.startswith(tail):
        cond = cond[len(tail):].strip(" —–-,.")
    return head, cond


def _place(s, pid):
    for ps in (s.get("ui") or {}).get("place_screens") or []:
        if ps.get("place_id") == pid:
            return ps.get("title") or ""
    for p in (s.get("map") or {}).get("places") or []:
        if p.get("id") == pid:
            return p.get("name") or p.get("title") or ""
    return ""


def build_reveal(s):
    cul = next((c for c in s["cast"] if c.get("is_culprit")), None)
    if not cul:
        return None
    dec = next((c for c in (s.get("clue_graph") or []) if c.get("decisive")), None)
    d = s.get("death") or {}
    sol = s.get("solution") or {}
    tr = s.get("trick") or {}
    cn = cul.get("name") or "범인"
    who = _clean(cul.get("public") or (cul.get("profile") or {}).get("status") or "")
    vic = (s.get("victim") or {}).get("name") or "피해자"
    place = _place(s, d.get("place"))
    motive = _clean(cul.get("kill_motive") or sol.get("motive_label") or "")
    conds = [c for c in (tr.get("conditions") or []) if str(c).strip()]
    tr_head, cond0 = _dedupe(tr.get("name") or "", conds[0] if conds else "")
    cond1 = _clean(conds[1]) if len(conds) > 1 else ""

    # ★진상에서 **범인을 밝히지 않는다** (2026-08-31, 제보 —
    #   "사건의 진상에서 사인이랑 상황만, 뒤에 범행 재연부터 범인 나오고,
    #    그 다음에 범인 모습은 ARREST 화면에서 보이게").
    #   맞는 순서다. 이름을 먼저 대 버리면 재연은 이미 아는 이야기의 삽화가 된다.
    #   진상은 **무슨 일이 있었나**까지만 말하고, 누가 했는지는 재연이 맡는다.
    #   그래서 동기 박도 뺐다 — 동기는 사람에 붙는 것이라 이름 없이는 말할 수 없다.

    # ① 그날 밤
    b1 = f"{d.get('time_slot','')}, {place}. {vic}{_j(vic,'은/는')} 아직 살아 있었다."

    # ② 사인 — 무엇이 그를 죽였나
    wp = _clean(d.get("weapon") or "")
    b2 = (f"{vic}{_j(vic,'을/를')} 죽인 것은 {wp}{_j(wp,'이었다/였다')}."
          if wp else f"{vic}{_j(vic,'은/는')} 그 밤에 죽었다.")

    # ③ 상황 — 어떻게 그런 일이 되었나 (수법)
    b3 = f"수법은 {tr_head}{_j(tr_head,'이었다/였다')}." if tr_head else ""
    if cond0:
        b3 = (b3 + " " + _fin(cond0)).strip()

    # ④ 그 사이 — 아무도 못 본 까닭
    b4 = _fin(cond1) if cond1 else _fin(_clean((tr or {}).get("desc") or ""))

    # ⑤ 걸린 자리 — 결정타 하나
    dsurf = _clean((dec or {}).get("implies") or (dec or {}).get("surface") or "")
    if len(dsurf) > 150:
        dsurf = dsurf[:149].rstrip() + "…"
    b5 = _fin(dsurf) if dsurf else "지워지지 않은 것이 하나 있었다."

    texts = [b1, b2, b3, b4, b5]
    labels = ["그날 밤", "사인", "상황", "그 사이", "걸린 자리"]
    return texts, labels


def build_reenact_first(s):
    """재연 1컷 — 「{범인}은 마음을 정했다」는 50편 공통 문장이라 뺀다."""
    cul = next((c for c in s["cast"] if c.get("is_culprit")), None)
    if not cul:
        return None
    d = s.get("death") or {}
    motive = _clean(cul.get("kill_motive") or
                    (s.get("solution") or {}).get("motive_label") or "")
    if not motive:
        return None
    return f"{d.get('time_slot','')}. {_fin(motive)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--scenario", default=None)
    a = ap.parse_args()
    files = ([f"scenarios/{a.scenario}"] if a.scenario else
             [f for f in sorted(glob.glob("scenarios/*.json")) if "catalog" not in f])
    n = 0
    for f in files:
        s = json.load(open(f, encoding="utf-8"))
        rv = s.get("ui", {}).get("reveal_sequence") or {}
        got = build_reveal(s)
        if not got or not rv.get("beats"):
            continue
        texts, labels = got
        old_beats = rv["beats"]
        rv["beats"] = []
        for i, (tx, lb) in enumerate(zip(texts, labels)):
            # 연출값(그림·소리)은 있던 것을 물려받는다 — 글만 새로 쓴다
            base = dict(old_beats[i]) if i < len(old_beats) else {}
            base.pop("emphasis", None)
            base.update({"no": i + 1, "label": lb, "text": _clean(tx),
                         "duration_sec": max(4, min(14, round(len(_clean(tx)) / 5.2)))})
            rv["beats"].append(base)
        rv["beats"][-1]["emphasis"] = True
        rv["culprit_named"] = False      # 진상에는 범인이 나오지 않는다
        rv["order"] = labels
        rv["full_text"] = "\n\n".join(b["text"] for b in rv["beats"])
        rv["note"] = ("엔딩 진상. 형사가 사건을 정리해 읽는 투 — 수식 없이, 순서대로, "
                      "확인할 수 있는 사실만. **범인은 여기서 밝히지 않는다** — "
                      "이름은 재연에서, 얼굴은 ARREST 화면에서. (2026-08-31 개편)")
        rv.pop("closing_line_policy", None)

        rn = s.get("ui", {}).get("murder_reenactment") or {}
        first = build_reenact_first(s)
        if first and rn.get("cuts"):
            rn["cuts"][0]["text"] = _clean(first)

        if a.check:
            print(f"── {os.path.basename(f)}")
            for b in rv["beats"]:
                print(f"   [{b['label']}] {b['text']}")
            print()
        else:
            json.dump(s, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        n += 1
    print(f"{'고칠' if a.check else '고친'} 진상 {n}편")


if __name__ == "__main__":
    main()
