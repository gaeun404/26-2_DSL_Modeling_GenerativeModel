# -*- coding: utf-8 -*-
"""
ending_book.py — **엔딩을 두 갈래로 가르고, 못 연 비밀을 마지막에 털어놓게 한다.**

■ 어디서 배웠나 (2026-08-25, 보드게임 카페 실물 대본 관찰)
  시판 머더미스터리 한 편의 「엔딩 북」이 이렇게 되어 있었다.

      · 결과에 따라 **읽는 파트가 갈린다** —
          진범이 최다 득표  → A (진범의 1인칭 자백 독백 → 경찰 도착 → "긴 밤이 밝았다")
          그 외가 최다 득표 → B (엉뚱한 사람이 붙잡히고, 진범은 조용히 빠져나간다)
        두 갈래 다 "(결과: 진범 구속에 성공/실패)"로 못을 박는다.
      · 그다음 **공통 마무리** — 정해진 순서로 각자 자기 비밀을 발표하고,
        「비밀을 들켜서는 안 되는 상대」에게 "내 비밀을 눈치챘었습니까?"라고 묻는다.
      · 진상 페이지에는 이런 단서가 붙어 있었다 —
        "(무슨 일이 일어난 것인지 도저히 모르겠다는 경우에 읽어 주세요)"
        그리고 끝에 "이외에도 다섯 명 사이에는 숨겨진 진실이 더 존재합니다."

  배울 점이 셋이었다.
    ① **엔딩 서사가 결과에 따라 갈린다.** 우리는 등급 이름만 바뀌고 진상은 늘 같았다.
       범인을 놓쳐도 같은 낭독을 듣는다면, 맞힌 보람이 문장으로 돌아오지 않는다.
    ② **못 연 비밀은 마지막에 본인이 털어놓는다.** 우리는 그냥 묻혔다.
       열지 못한 비밀이 무엇이었는지조차 모르고 끝나면 아쉬움이 남지 않는다.
    ③ **`hidden_from`이 채점에 쓰인다.** 우리 스키마에도 그 칸이 있는데
       엔진의 대질 판정에만 쓰이고 엔딩에서는 한 번도 읽히지 않았다.

■ 넣는 것
    ending.branches.caught    범인을 짚었을 때의 마무리 서사
    ending.branches.escaped   놓쳤을 때의 마무리 서사
    ending.reveal_order       비밀 발표 순서 — 인물마다 두 벌(이미 연 것 / 못 연 것)
    ending.hidden_from_check  누가 누구에게 끝내 들키지 않았어야 하는가

사용:
    python3 ending_book.py                    # 전 편
    python3 ending_book.py out/91_dsl_demo.json
"""
import json, glob, sys


def _j(w, pair="을/를"):
    a, b = pair.split("/")
    ch = (w or " ")[-1]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


def build(s):
    cast = s["cast"]
    cul = next((c for c in cast if c.get("is_culprit")), cast[0])
    others = [c for c in cast if c["id"] != cul["id"]]
    vic = (s.get("victim") or {}).get("name", "피해자")
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    place = pn.get((s.get("death") or {}).get("place"), "그 자리")
    cn = cul["name"]

    # ── ① 두 갈래 ────────────────────────────────────────────────
    branches = {
        "note": "지목 결과에 따라 **읽는 쪽이 갈린다.** 둘 중 하나만 낭독한다.",
        "caught": {
            "when": "지목한 이름이 진범과 같을 때",
            "label": "붙잡힌 밤",
            "beats": [
                f"이름이 불렸을 때, {cn}{_j(cn,'은/는')} 웃지도 부인하지도 않았다.",
                f"「…언제부터 알고 계셨습니까.」 그것이 {cn}의 첫 마디였다.",
                f"{cn}{_j(cn,'은/는')} 그 밤의 일을 처음부터 되짚어 말했다. "
                f"길지 않았다. 이미 여러 번 속으로 되뇌어 본 사람의 말투였다.",
                f"바깥에서 사람들이 들어왔다. {place}의 불이 모두 켜졌다.",
                "긴 밤이 밝았다.",
            ],
            "result_line": "(결과 : 진범을 짚었다)",
        },
        "escaped": {
            "when": "지목한 이름이 진범과 다를 때",
            "label": "빠져나간 밤",
            "beats": [
                "이름이 불린 사람은 그 자리에서 아니라고 했다. 아무도 그 말을 믿지 않았다.",
                "그 사람이 데려나가는 동안, 남은 이들은 서로를 보지 않았다.",
                f"— 정말 그런 걸까?",
                f"{place}의 불이 하나씩 꺼졌다. 한 사람만이 그 어둠을 오래 바라보았다.",
                "긴 밤이 밝았다. 그리고 아무 일도 없었다는 듯 아침이 왔다.",
            ],
            "result_line": "(결과 : 진범은 이 밤을 빠져나갔다)",
        },
    }

    # ── ② 비밀 발표 — 못 연 것은 본인이 털어놓는다 ────────────────
    order = []
    for c in [cul] + others:
        secs = [x.get("text", "") for x in (c.get("secrets") or []) if x.get("text")]
        if not secs:
            continue
        nm = c["name"]
        order.append({
            "cast_id": c["id"], "name": nm,
            "secrets": secs,
            "if_opened": (f"{nm}{_j(nm,'은/는')} 짧게 고개를 끄덕인다. "
                          f"「아까 말씀드린 그대로입니다.」"),
            "if_closed": (f"{nm}{_j(nm,'은/는')} 잠깐 망설이다 제 입으로 말한다. "
                          f"「…끝까지 안 물으시더군요.」"),
            "note": "이미 연 비밀은 짧게 넘기고, **못 연 비밀만** 본인이 밝힌다.",
        })

    # ── ③ 누구에게는 끝내 들키지 말았어야 했는가 ──────────────────
    nm_of = {c["id"]: c["name"] for c in cast}
    checks = []
    for c in cast:
        for sec in (c.get("secrets") or []):
            for hid in (sec.get("hidden_from") or []):
                if hid in nm_of:
                    checks.append({
                        "cast_id": c["id"], "name": c["name"],
                        "hidden_from": hid, "hidden_from_name": nm_of[hid],
                        "line": (f"{c['name']}{_j(c['name'],'이/가')} "
                                 f"{nm_of[hid]}에게 묻는다 — "
                                 f"「제 일을, 눈치채고 계셨습니까.」"),
                    })

    # ── ④ 그날 밤 재생 — novel에는 분 단위로 적혀 있는데 화면엔 없었다 ────
    #    엔딩에서 "그날 밤을 시각 순으로 재생한다"고 해 놓고, 정작 낭독할
    #    대사가 스키마에 없었다. timeline_events를 **읽을 수 있는 문장**으로 만든다.
    nm_of = {c["id"]: c["name"] for c in cast}
    nm_of["all"] = "모두"
    nm_of[(s.get("victim") or {}).get("id", "V")] = vic
    replay = []
    for e in (s.get("timeline_events") or []):
        who = nm_of.get(e.get("who"), e.get("who") or "")
        tx = str(e.get("text") or "").strip()
        if not tx:
            continue
        line = (f"{e.get('time','')}  {tx}" if who in ("모두", "")
                else f"{e.get('time','')}  {who}{_j(who,'은/는')} {tx}")
        replay.append({
            "time": e.get("time", ""), "who": e.get("who"), "name": who,
            "line": line,
            "known_from": e.get("known_from", ""),
            "is_murder": bool(e.get("is_murder")) or ("쓰러" in tx and vic in tx),
        })

    # ── ⑤ 그 밤에 **실제로** 있었던 일 — 재연에만 나오는 줄 ──────────────
    #   ★2026-08-26. timeline_events 는 '플레이어가 알아낼 수 있는 일'만 담는다.
    #     그래서 재연을 끝까지 읽어도 **범행 장면이 한 줄도 없었다.**
    #     누가 언제 무엇을 넣었는지가 빠진 재연은 사건의 재연이 아니다.
    #     범인의 거짓말(lies[].truth)과 죽음의 수법(death.method)을
    #     제자리에 꽂아 넣는다. 이 줄은 **엔딩에서만** 열린다.
    hidden = []
    for li in (cul.get("lies") or []):
        tx = str(li.get("truth") or "").strip()
        if tx:
            hidden.append(f"{cn}{_j(cn,'은/는')} 실은 — {tx}")
    meth = str((s.get("death") or {}).get("method") or "").strip()
    if meth and not any(meth[:12] in h for h in hidden):
        hidden.append(f"수법 — {meth}")
    if not hidden:
        hidden.append(f"{cn}{_j(cn,'이/가')} {vic}{_j(vic,'을/를')} 해쳤다.")

    def _like(a, b):
        """두 문장이 얼마나 같은 낱말을 쓰는가 — 꽂을 자리를 고르는 데만 쓴다."""
        wa = {a[i:i+4] for i in range(max(0, len(a) - 3))}
        return sum(1 for i in range(max(0, len(b) - 3)) if b[i:i+4] in wa)

    m_at = next((i for i, r in enumerate(replay) if r["is_murder"]), len(replay))
    for h in hidden:
        best, sc = m_at, 0
        for i, r in enumerate(replay[:m_at]):
            v = _like(h, r["line"])
            if v > sc:
                best, sc = i + 1, v
        at = replay[best - 1]["time"] if best else ""
        replay.insert(best, {
            "time": at, "who": cul["id"], "name": cn, "line": h,
            "known_from": "재연에서만 드러난다", "is_murder": False,
            "hidden_until_end": True,
        })
        m_at = next((i for i, r in enumerate(replay) if r["is_murder"]), len(replay))

    return {
        "branches": branches,
        "replay": {
            "label": "그날 밤",
            "note": ("엔딩 뒤에 시각 순으로 되짚는다. 한 줄에 한 시각. "
                     "**어떻게 알게 된 것인지**(known_from)를 작게 곁들이면 "
                     "플레이어가 놓친 자리가 어디였는지 스스로 안다. "
                     "hidden_until_end 가 붙은 줄은 **아무도 못 본 대목**이다 — "
                     "재연에서 처음 열리며, 다른 줄과 다르게 보여 준다."),
            "lines": replay,
        },
        "reveal_order": {
            "note": ("지목이 끝난 뒤, 정해진 순서로 각자 제 비밀을 밝힌다. "
                     "**플레이어가 연 비밀은 짧게 넘어가고, 못 연 비밀만 본인이 털어놓는다.** "
                     "다 못 열었어도 무엇이었는지는 알고 끝난다."),
            "order": order,
        },
        "hidden_from_check": {
            "note": ("비밀마다 **끝내 들켜서는 안 되는 상대**가 정해져 있다. "
                     "그 사람 앞에서 비밀이 열렸는지를 마지막에 확인한다 — "
                     "지금은 연출로만 쓰고, 채점에 넣을지는 밸런스를 보고 정한다."),
            "checks": checks,
        },
        "truth_optional": {
            "label": "진상",
            "when": "무슨 일이 있었는지 도무지 모르겠다는 경우에만 펼친다",
            "note": ("★진상은 **선택해서 보는 것**으로 둔다. "
                     "짚어 낸 사람에게까지 처음부터 다 읽어 주면 맞힌 보람이 사라진다."),
        },
    }


def enrich(path):
    s = json.load(open(path, encoding="utf-8"))
    s.setdefault("ending", {}).update(build(s))
    json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    e = s["ending"]
    print(f"  {path.split('/')[-1][:28]:30s} 갈래 2 · 비밀 발표 "
          f"{len(e['reveal_order']['order'])}명 · 들키지 말 것 "
          f"{len(e['hidden_from_check']['checks'])}건")
    return len(e["hidden_from_check"]["checks"])


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    tot = sum(enrich(f) for f in files)
    print(f"\n{len(files)}편 · '들켜서는 안 되는 상대' 관계 {tot}건")
