# -*- coding: utf-8 -*-
"""
agents.py — **성격이 다른 판정자 여럿을 같은 밤에 풀어놓고 견준다.**

  python3 agents.py                       # 여섯 성격 전부, 91편
  python3 agents.py --who 형사 심리        # 둘만
  python3 agents.py --scenario 38_cinderella.json
  python3 agents.py --full 기자            # 한 성격의 판을 처음부터 끝까지
  python3 agents.py --rounds 2 --model gpt-4o-mini

  .apikey 가 없으면 규칙으로 돌린다(대사는 자리표시자).

무엇을 보나
  · 성격마다 **다른 질문**이 나오는가 — 틀에 박힌 한 문장이 되풀이되지 않는가
  · 대질 상대와 그 자리의 질문이 갈리는가
  · 무엇을 얻고(단서·비밀) 누구를 짚는가
  · 놓친 자리는 어디인가
"""
import _boot, sys, json, glob, argparse, collections    # noqa: F401
import play_agents as PA
from game_engine_v2 import GameSession

W = 78


def rule(ch="─"):
    print(ch * W)


def _cut(x, n):
    x = str(x or "").replace("\n", " ")
    return x if len(x) <= n else x[:n - 1] + "…"


# ── 한 성격이 한 판을 논다 ────────────────────────────────────────────
def play(s, who, llm_p, llm_s, rounds=None, verbose=False):
    g = GameSession(s)
    R = rounds or g.max_rounds
    sysmsg = PA.player_system(who, s)
    F = PA.forms(s)                 # 이 편의 말투로 된 질문 본
    tried, feed, stat = set(), [], {"regen": 0, "stripped": 0, "fallback": 0, "api_fail": 0}
    asked_q = set()          # (사람, 질문 몸통) — 같은 것을 두 번 묻지 못하게
    hist = {cid: [] for cid in g.cast}
    log = {"who": who, "persona": who, "moves": [], "questions": [], "confront": None,
           "secrets": [], "flow": [], "journal": [], "ungrounded": []}
    journal = log["journal"]        # 내가 무엇을 왜 했고 무엇이 나왔는가

    # ★이름으로 답해도 알아듣는다 (2026-08-27).
    #   실측 — 변호사와 과학수사가 한 판 내내 규칙 대체로만 굴러갔다.
    #   까닭은 단순했다. 판정자가 {"place":"세미나실(중도 6층)"},
    #   {"cast":"서민재"}처럼 **이름**으로 답했는데 코드가 id만 받았다.
    #   사람이라면 그렇게 부르는 것이 당연하다 — 받아 주는 쪽이 맞다.
    def _pid(x):
        x = str(x or "").strip()
        for p_ in s["map"]["places"]:
            if x == p_["id"]:
                return p_["id"]
        for p_ in s["map"]["places"]:
            if x and (x == p_["name"] or x in p_["name"] or p_["name"] in x):
                return p_["id"]
        return None

    def _cid(x):
        x = str(x or "").strip()
        if x in g.cast:
            return x
        for cid_, c_ in g.cast.items():
            if x and (x == c_["name"] or c_["name"] in x):
                return cid_
        for cid_, c_ in g.cast.items():
            if x and x in str(c_.get("public") or ""):
                return cid_
        return None

    def _kid(x):
        x = str(x or "").strip()
        if x in g.held_clues:
            return x
        up = x.upper()
        for k_ in g.held_clues:
            if up == str(k_).upper():
                return k_
        for cl_ in (s.get("clue_graph") or []):
            if cl_.get("id") in g.held_clues and x and x[:10] in str(cl_.get("surface") or ""):
                return cl_["id"]
        return None

    def _fallback_q(i, has_clue):
        """규칙이 밀어 줄 때 쓰는 질문 — **한 문장만 되풀이하지 않는다.**
        실측: 두 성격이 한 판 내내 「이건 어떻게 된 일인지 설명해 주시겠어요」만 물었다."""
        nowish = "주세요" in F["scene"]
        if has_clue:
            pool = ([F["evi"], "이건 언제 보신 겁니까.", "여기 적힌 대로가 맞습니까.",
                     "이걸 보고도 같은 말씀이십니까."] if nowish else
                    [F["evi"], "이것을 언제 보았소.", "여기 적힌 대로가 맞소.",
                     "이것을 보고도 같은 말이오."])
        else:
            pool = ([F["scene"], F["place"], "그 자리를 언제 떠나셨습니까.",
                     "그때 곁에 누가 있었습니까."] if nowish else
                    [F["scene"], F["place"], "그 자리를 언제 떴소.",
                     "그때 곁에 누가 있었소."])
        return pool[i % len(pool)]

    import re as _re

    def _qkey(cid, q):
        """질문의 **몸통**만 남긴다. '다시', '아까'만 바꿔 붙인 되풀이를 같은 것으로 본다."""
        x = _re.sub(r"[^가-힣A-Za-z0-9]", "", str(q or ""))
        for w in ("다시", "아까", "그러면", "혹시", "한번", "좀"):
            x = x.replace(w, "")
        return (cid, x[:22])

    def say(txt):
        log["flow"].append(txt)
        if verbose:
            print(txt)

    def decide():
        """다음 한 수. LLM이 못 내면 손으로 짠 규칙으로 되돌아간다."""
        view = PA.player_view(s, g, tried, feed, journal, asked_q)
        if llm_p:
            try:
                raw = llm_p.chat([{"role": "system", "content": sysmsg},
                                  {"role": "user", "content":
                                   "[지금 상황]\n"
                                   + json.dumps(view, ensure_ascii=False, indent=1)
                                   + "\n\n다음 한 수를 JSON 한 줄로 답하라."}])
                d = PA.parse_move(raw)
                if d:
                    return d
                stat["fallback"] += 1
            except Exception as e:
                # 호출이 막혔다고 판이 통째로 죽으면 안 된다 — 규칙으로 이어 간다
                stat["api_fail"] += 1
                if stat["api_fail"] == 1:
                    print(f"\n  [{who}] 호출이 막혀 규칙으로 이어 갑니다 — {str(e)[:60]}")
        # 되돌아가는 규칙 — 성격마다 조금 다르게.
        #   키가 없을 때도 판이 갈리도록, 성격마다 다른 짝을 맞대 놓는다.
        un = [p for p in view["places"] if not p["searched_this_round"]]
        want_search = who in ("과학수사", "형사")
        if view["confront"]["unlocked"] and view["confront"]["tokens_left"] > 0:
            ids = [c["id"] for c in view["cast"]]
            off = list(PA.PERSONAS).index(who)
            a_, b_ = ids[off % len(ids)], ids[(off + 1 + off // len(ids)) % len(ids)]
            if a_ == b_:
                b_ = ids[(off + 2) % len(ids)]
            qs = [F["cx"], PA.rel_q(F, "상대"),
                  ("서로의 말이 어긋나는 대목을 말씀해 주세요."
                   if "주세요" in F["scene"] else "서로의 말이 어긋나는 대목을 말해 보시오."),
                  F["scene"]]
            return {"action": "confront", "cast": a_, "with": b_,
                    "question": qs[off % len(qs)], "why": "규칙"}
        if un and (view.get("findable_left") or 0) > 0 \
                and (want_search or view["turns_left"] > 4):
            return {"action": "search", "place": un[0]["id"], "why": "규칙"}
        # 사람을 돌려 가며 판다 — 한 사람만 붙잡으면 판이 한쪽으로 쏠린다
        nb = view["notebook"]
        n_asked = collections.Counter(x["cast"] for x in feed)
        order = sorted(view["cast"], key=lambda c: (n_asked[c["name"]], c["id"]))
        for c in order:
            for e in nb:
                if f"{c['id']}+{e['id']}" not in view["already_tried"]:
                    return {"action": "ask", "cast": c["id"], "clue": e["id"],
                            "question": _fallback_q(len(feed), True),
                            "from": "규칙 — 아직 안 내민 단서", "why": "규칙"}
        return {"action": "next", "why": "규칙"}

    def do_ask(d):
        cid = _cid(d.get("cast"))
        if not cid:
            cid = min(g.cast, key=lambda x: (x in g.met, 0))
        c = g.cast[cid]
        m = g.meet(cid)
        if m.get("first_meet") and m.get("alibi"):
            say(f"   [첫 대면 · 예산 0] {c['name']} — “{_cut(m['alibi'], 90)}”")
        k = _kid(d.get("clue"))
        cl = next((x for x in s["clue_graph"] if x["id"] == k), None) if k else None
        q0 = str(d.get("question") or F["scene"])
        # ★같은 사람에게 같은 질문을 두 번 하지 못한다 (2026-08-27).
        #   실측 — 「암전 시간에 무슨 일이 있었는지 다시 말씀해 주시겠어요」를 유가람에게
        #   **일곱 번** 물었다. 비밀이 이미 열린 뒤에도 계속. 판의 3분의 1이 그 한 문장에 탔다.
        #   턴을 쓰지 않고 되돌린다 — 대신 왜 안 되는지 알려 준다.
        if _qkey(cid, q0) in asked_q:
            feed.append({"cast": c["name"], "clue": None, "stance": "SKIP",
                         "means": f"{c['name']}에게 그 질문은 이미 했다 — 같은 답이 돌아온다. "
                                  f"**다른 것을 묻거나 다른 사람에게 가라**"})
            return False
        bad = PA.ungrounded(q0, g)
        if bad and llm_p:
            # ★알 리가 없는 말을 물었다 — 한 번 되돌려 준다 (2026-08-27).
            #   "그건 아직 못 들은 얘기다"라고 알려 주고 다시 짓게 한다.
            try:
                raw = llm_p.chat([
                    {"role": "system", "content": sysmsg},
                    {"role": "user", "content":
                     f"[되돌린다] 방금 질문에 **네가 알 수 없는 말**이 있었다 — "
                     f"{', '.join(bad)}.\n너는 그 말을 어디서도 듣거나 보지 못했다. "
                     f"지금 아는 것만 가지고 다시 물어라.\n"
                     f"[네가 아는 것]\n"
                     + json.dumps({"notebook": PA.player_view(s, g, tried, feed)["notebook"],
                                   "cast": [{"name": c2["name"], "public": c2["public"],
                                             "alibi": c2["alibi"]}
                                            for c2 in g.state()["cast"] if c2["met"]]},
                                  ensure_ascii=False, indent=1)
                     + "\n\nJSON 한 줄로만 답하라."}])
                d2 = PA.parse_move(raw)
                if d2 and d2.get("question"):
                    log["ungrounded"].append({"words": bad, "before": _cut(q0, 50),
                                              "after": _cut(d2["question"], 50), "fixed": True})
                    d = {**d, **d2}
                    q0 = str(d2["question"])
                    bad = PA.ungrounded(q0, g)
            except Exception:
                stat["api_fail"] += 1
        if bad:
            log["ungrounded"].append({"words": bad, "before": _cut(q0, 50),
                                      "after": None, "fixed": False})
        q = q0
        if cl:
            tried.add((cid, cl["id"]))
            q = f"「{cl['surface']}」 — {q}"
        asked_q.add(_qkey(cid, q0))
        before = set(g.disclosed_secrets.get(cid, set()))
        st = g.interrogate(cid, q, evidence_shown=bool(cl))
        if "error" in st:
            return False
        try:
            line = (PA.suspect_reply(llm_s, s, g, c, q, st, hist[cid], stat)
                    if llm_s else "(대사는 키가 있으면 실제 문장으로 나온다)")
        except Exception:
            stat["api_fail"] += 1
            line = "(대사를 받지 못했다 — 호출 실패)"
        new = set(g.disclosed_secrets.get(cid, set())) - before
        for sec in new:
            log["secrets"].append({"cast": c["name"], "text": sec,
                                   "how": "증거" if cl else "추궁"})
        log.setdefault("dialogue", []).append(
            {"r": g.current_round, "cast": c["name"], "clue": (cl or {}).get("id"),
             "q": q, "a": line, "stance": st["stance"],
             "gauge": st.get("gauge_after"), "opened": sorted(new)})
        log["questions"].append({"cast": c["name"], "clue": (cl or {}).get("id"),
                                 "q": q0, "stance": st["stance"],
                                 "why": _cut(d.get("why"), 40)})
        feed.append({"cast": c["name"], "clue": (cl or {}).get("id"),
                     "stance": st["stance"],
                     "means": {"ADMIT": "실토했다 — 비밀이 열렸다",
                               "FLINCH": ("흔들렸다 — 정곡은 맞았다. "
                                          "**같은 자리를 두 번 더 물으면 열린다.** "
                                          "화제를 바꾸면 지금까지 판 것이 헛일이다"),
                               "BREAK": ("무너졌다 — 더는 버티지 못한다. "
                                         "**결정적인 자리를 짚었다는 뜻이다.** "
                                         "이 사람을 다시 보라"),
                               "DEFLECT": "회피했다 — 헛짚었다",
                               "ANSWER": "사실만 답했다"}.get(st["stance"], "")})
        journal.append({"r": g.current_round, "did": "물었다",
                        "누구": c["name"], "단서": (cl or {}).get("id"),
                        "질문": _cut(q0, 50), "근거": _cut(d.get("from"), 30),
                        "까닭": _cut(d.get("why"), 30),
                        "반응": st["stance"],
                        "얻은 것": [ _cut(x, 30) for x in new ] or None})
        say(f"   [{c['name']} · {st['stance']} · 압박 {st['gauge_after']}] "
            f"Q. {_cut(q0, 60)}")
        if verbose:
            print(f"      A. {_cut(line, 200)}")
        for sec in new:
            say(f"      > 비밀이 열렸다 — {_cut(sec, 60)}")
        return True

    def do_search(d):
        pid = _pid(d.get("place"))
        if not pid:
            return False
        # ★같은 방을 또 뒤지는 것은 수가 아니다 (2026-08-27).
        #   이미 뒤진 방은 0턴이라 예산이 줄지 않는다. 그래서 한 성격이
        #   한 판에 **120번을 뒤지고 질문은 한 번도 못 했다.**
        #   그런 수는 받지 않고, 왜 안 되는지 알려 준다.
        if (pid, g.current_round) in g.searched:
            nm0 = next((p["name"] for p in s["map"]["places"] if p["id"] == pid), pid)
            feed.append({"cast": None, "clue": None, "stance": "SKIP",
                         "means": f"{nm0}은 이번 라운드에 이미 뒤졌다 — 또 뒤져도 나올 것이 없다"})
            return False
        r = g.search(pid)
        if r.get("error"):
            return False
        got = [c["id"] for c in (r.get("clues") or [])]
        nm = next((p["name"] for p in s["map"]["places"] if p["id"] == pid), pid)
        journal.append({"r": g.current_round, "did": "뒤졌다", "어디": nm,
                        "근거": _cut(d.get("from"), 30), "까닭": _cut(d.get("why"), 30),
                        "얻은 것": got or None})
        say(f"   [탐색] {nm} — " + (", ".join(got) if got else "나온 것 없음"))
        return True

    def do_confront(d):
        if g.confront_tokens <= 0 or log["confront"] is not None:
            feed.append({"cast": None, "clue": None, "stance": "SKIP",
                         "means": "대질은 한 판에 한 번뿐이다 — 이미 썼으니 다시 고를 수 없다"})
            return False
        if g.current_round < g.confront_unlock_round:
            feed.append({"cast": None, "clue": None, "stance": "SKIP",
                         "means": "대질은 아직 잠겨 있다 — 판이 한 번 뒤집혀야 열린다"})
            return False
        a, b = _cid(d.get("cast")), _cid(d.get("with"))
        if not a or not b or a == b:
            feed.append({"cast": None, "clue": None, "stance": "SKIP",
                         "means": "맞대 놓을 두 사람을 제대로 고르지 않았다"})
            return False
        q = str(d.get("question") or F["cx"])
        r = g.confront(a, b, q)
        if "error" in r:
            return False
        cx = r.get("cross_exam") or {}
        log["confront"] = {
            "a": g.cast[a]["name"], "b": g.cast[b]["name"], "q": q,
            "round": g.current_round, "curated": r.get("is_curated_pair"),
            "note": ((cx.get("reveals") or {}).get("note") or ""),
            "gained": (cx.get("gained_clue") or {}).get("id"),
            "lines": [(l["name"], l["beat"], l["line"]) for l in (cx.get("exchange") or [])],
        }
        journal.append({"r": g.current_round, "did": "맞대 놓았다",
                        "누구": f"{g.cast[a]['name']} ↔ {g.cast[b]['name']}",
                        "질문": _cut(q, 40), "근거": _cut(d.get("from"), 30),
                        "얻은 것": log["confront"]["note"][:40] or None})
        say(f"   [대질] {g.cast[a]['name']} ↔ {g.cast[b]['name']} — {_cut(q, 50)}")
        if verbose:
            for l in (cx.get("exchange") or []):
                print(f"      [{l['beat']}] {l['name']}: {_cut(l['line'], 70)}")
        return True

    # ── 라운드 ──
    for rnd in range(1, R + 1):
        say(f"\n── {rnd}라운드")
        if rnd > 1:
            nx = g.next_round()
            if nx.get("given"):
                say(f"   [자동 공개] {', '.join(nx['given'])}")
        for done in (g.apply_event(rnd) or []):
            for sec in done["secrets"]:
                log["secrets"].append({"cast": ", ".join(g.cast[c]["name"] for c in done["cast"]),
                                       "text": sec, "how": "이벤트"})
                say(f"   [이벤트] 비밀이 열렸다 — {_cut(sec, 56)}")
        guard = 0
        while g.state()["turns_left"] > 0 and guard < 40:
            guard += 1
            d = decide()
            # ★못 쓰는 대질을 고르면 **호출을 더 쓰지 않고** 그 자리에서 바꾼다.
            #   전에는 그대로 실행해 보고 실패시키느라 한 판에 80번을 골랐다.
            if str(d.get("action")) == "confront" and (
                    g.confront_tokens <= 0 or log["confront"] is not None
                    or g.current_round < g.confront_unlock_round):
                feed.append({"cast": None, "clue": None, "stance": "SKIP",
                             "means": ("대질은 한 판에 한 번뿐이다 — 이미 썼다"
                                       if g.confront_tokens <= 0 or log["confront"]
                                       else "대질은 아직 잠겨 있다")})
                d = {"action": "ask", "from": "대질을 못 쓰니 사람을 판다",
                     "why": "규칙", "cast": None}
                cid3 = min(g.cast, key=lambda x: (x in g.met, 0))
                k3 = next((e["id"] for e in g.notebook if (cid3, e["id"]) not in tried), None)
                d.update({"cast": cid3, "clue": k3,
                          "question": _fallback_q(len(feed), bool(k3))})
            log["moves"].append(d.get("action"))
            act = str(d.get("action"))
            ok = (do_search(d) if act == "search" else
                  do_ask(d) if act == "ask" else
                  do_confront(d) if act == "confront" else False)
            if act == "next":
                break
            # ★대질을 뺐던 것이 화근이었다 (2026-08-27).
            #   토큰을 다 쓴 뒤에도 판정자가 계속 대질을 골랐고, 그 수는
            #   아무 일도 하지 않은 채 라운드를 갉아먹었다. 실측 — 기자가
            #   대질 80번, 질문 2번. **못 하는 수는 무엇이든 밀어 준다.**
            if not ok:
                # 못 하는 수를 냈으면 규칙으로 한 번 밀어 준다
                stat["fallback"] += 1
                un = [p for p in s["ui"]["place_screens"]
                      if (p["place_id"], g.current_round) not in g.searched]
                if un:
                    do_search({"place": un[0]["place_id"], "from": "규칙"})
                else:
                    cid2 = min(g.cast, key=lambda x: (x in g.met, 0))
                    k2 = next((e["id"] for e in g.notebook
                               if (cid2, e["id"]) not in tried), None)
                    do_ask({"cast": cid2, "clue": k2, "from": "규칙",
                            "question": _fallback_q(len(feed), bool(k2))})

    # ── 지목 ──
    # ★대질을 끝내 안 쓰고 판을 접는 일이 잦다 (2026-08-27).
    #   횟수를 쓰지 않는 행동이라 안 쓰면 그냥 버리는 것이다.
    #   마지막에 한 번은 쓰게 밀어 준다 — 짝은 아직 안 만난 사람이 없는 쪽으로.
    if log["confront"] is None and g.confront_tokens > 0 \
            and g.current_round >= g.confront_unlock_round:
        pairs = [p for p in g.cx_pairs if all(x in g.met for x in p)] or list(g.cx_pairs)
        if pairs:
            off = list(PA.PERSONAS).index(who)
            a_, b_ = pairs[off % len(pairs)]
            do_confront({"cast": a_, "with": b_, "from": "안 쓰면 버리는 행동이라",
                         "question": F["cx"]})
            log["confront_forced"] = True

    # ── 지목 — **판정자가 제 입으로 이름을 댄다** (2026-08-27) ────────
    #   전에는 손에 쥔 단서를 세어 최다를 골랐다. 그러면 '무엇을 쥐었나'만
    #   보는 셈이고, **쥔 것으로 무엇을 읽어 냈나**는 볼 수 없다.
    #   같은 단서를 쥐고도 성격마다 다른 이름을 대는지가 이 실험의 알맹이다.
    say_named = None
    if llm_p and not stat["api_fail"]:
      try:
        view = PA.player_view(s, g, tried, feed, journal, asked_q)
        raw = llm_p.chat([
            {"role": "system", "content": sysmsg},
            {"role": "user", "content":
             "[마지막 — 이름을 대라]\n"
             + json.dumps({"cast": view["cast"], "notebook": view["notebook"]},
                          ensure_ascii=False, indent=1)
             + "\n\n이 밤에 사람을 죽인 것은 누구인가. 수첩에 적힌 것만 근거로 삼는다.\n"
               'JSON 한 줄로만 답하라 — {"culprit":"C1","weapon":"흉기","why":"근거 한 줄"}'}])
        d = PA.parse_move(raw) or {}
        if d.get("culprit") in g.cast:
            say_named = d["culprit"]
            log["verdict"] = {"cast": d["culprit"], "why": _cut(d.get("why"), 90),
                              "weapon": _cut(d.get("weapon"), 30)}
        else:
            stat["fallback"] += 1
      except Exception:
        stat["api_fail"] += 1

    tally = collections.Counter()
    #   ★엔진의 단서 목록을 본다 — 대질·소지품처럼 **판 도중에 생긴 단서**는
    #     시나리오 JSON에 없다. s["clue_graph"]만 보면 그것들이 셈에서 빠진다.
    herr_hit = set()
    for cl in g.clue_graph.values():
        if cl.get("id") in g.held_clues and cl.get("points_to"):
            if cl.get("weight") == "alibi":      # 결백 증언 — 지목 셈에 안 든다
                continue
            if cl.get("weight") == "red_herring":   # 같은 사람 미끼는 한 번만
                if cl["points_to"] in herr_hit:
                    continue
                herr_hit.add(cl["points_to"]); tally[cl["points_to"]] += 2
                continue
            tally[cl["points_to"]] += 3 if (cl.get("decisive") or cl.get("weight") == "decisive") else 1
    by_clue = tally.most_common(1)[0][0] if tally else list(g.cast)[0]
    named = say_named or by_clue
    cul = next((c["id"] for c in s["cast"] if c.get("is_culprit")), None)
    correct = named == cul
    n_sec = sum(len(v) for v in g.disclosed_secrets.values())
    sc = s.get("scoring") or {}
    pts = min((sc.get("culprit_correct", 5) if correct else 0)
              + n_sec * sc.get("secret_revealed_each", 1), sc.get("max", 10))
    dec = {cl["id"] for cl in (s.get("clue_graph") or []) if cl.get("decisive")}
    log["result"] = {
        "named": g.cast.get(named, {}).get("name", named),
        "correct": correct,
        "clues": len(g.held_clues), "secrets": n_sec,
        "confident": bool(dec & set(g.held_clues)),
        "points": pts, "max": sc.get("max", 10),
        "by_clue": g.cast.get(by_clue, {}).get("name", by_clue),
        "self_named": bool(say_named),
        "missed": sorted({cl["id"] for cl in (s.get("clue_graph") or [])} - set(g.held_clues)),
        "moves": collections.Counter(log["moves"]),
        "ungrounded": len([x for x in log["ungrounded"] if not x["fixed"]]),
        "ungrounded_fixed": len([x for x in log["ungrounded"] if x["fixed"]]),
        "stat": stat,
    }
    return log


# ── 견주기 ────────────────────────────────────────────────────────────
def table(logs, s):
    cul = next((c["name"] for c in s["cast"] if c.get("is_culprit")), "?")
    print()
    rule("═")
    print("  성격마다 어떤 판이 됐나")
    rule("═")
    print(f"  {'판정자':9} {'탐색':>3} {'심문':>3} {'단서':>3} {'비밀':>3} "
          f"{'대질':13} {'지목':7} {'결과':5} {'근거':5} {'점수':>4}")
    rule()
    for lg in logs:
        r = lg["result"]
        mv = r["moves"]
        cx = lg["confront"] or {}
        pair = f"{cx.get('a','—')}↔{cx.get('b','')}" if cx else "—"
        print(f"  {lg['who']:9} {mv.get('search',0):>3} {mv.get('ask',0):>3} "
              f"{r['clues']:>3} {r['secrets']:>3} {_cut(pair,13):13} "
              f"{_cut(r['named'],6):7} {'적중' if r['correct'] else '빗나감':5} "
              f"{'결정타' if r['confident'] else ' 감 ':5} {r['points']:>3}점")
    rule()
    hit = sum(1 for l in logs if l["result"]["correct"])
    n_sec = sum(l["result"]["secrets"] for l in logs)
    print(f"  진범 : {cul}   ·   {len(logs)} 중 {hit}이 짚었다"
          f"   ({hit / max(1, len(logs)) * 100:.0f}%)")
    print(f"  연 비밀 — 판당 {n_sec / max(1, len(logs)):.1f}개 "
          f"(다섯 중) · 모두 {n_sec}개")

    # ── 쥔 것과 읽어 낸 것이 갈렸는가 ──
    #   단서가 가리키는 사람과 판정자가 댄 이름이 다르면, 그 자리가 볼 만하다.
    gap = [l for l in logs if l["result"].get("self_named")
           and l["result"]["named"] != l["result"]["by_clue"]]
    if gap:
        print("\n  단서가 가리킨 사람과 **다른 이름**을 댄 판정자")
        for l in gap:
            v = l.get("verdict") or {}
            print(f"     {l['who']:9} 단서는 {l['result']['by_clue']} → 「{l['result']['named']}」")
            print(f"        까닭 — {v.get('why','')}")
    elif any(l["result"].get("self_named") for l in logs):
        print("  (모두 손에 쥔 단서가 가리키는 사람을 그대로 짚었다)")

    # ── 질문이 정말 갈렸는가 ──
    print()
    rule("═")
    print("  같은 질문을 하지는 않았는가")
    rule("═")
    allq = [(l["who"], q["q"]) for l in logs for q in l["questions"] if q["q"]]
    heads = collections.Counter(q[:14] for _, q in allq)
    dup = sum(n - 1 for n in heads.values() if n > 1)
    print(f"  질문 {len(allq)}개 · 서로 다른 첫머리 {len(heads)}가지 · 겹친 것 {dup}개")
    for who in [l["who"] for l in logs]:
        mine = [q for w, q in allq if w == who]
        uniq = len({q[:14] for q in mine})
        print(f"     {who:9} {len(mine):>3}개 · 서로 다른 {uniq:>3}가지")

    # ── 성격마다 무엇을 물었나 ──
    print()
    rule("═")
    print("  성격마다 무엇을 물었나 (세 개씩)")
    rule("═")
    for lg in logs:
        base = lg.get("persona") or lg["who"].split("#")[0]
        print(f"\n  ── {lg['who']} ({PA.PERSONAS.get(base, {}).get('color', '')})")
        seen = set()
        n = 0
        for q in lg["questions"]:
            if not q["q"] or q["q"][:12] in seen:
                continue
            seen.add(q["q"][:12])
            n += 1
            mark = {"ADMIT": "실토", "FLINCH": "흔들림", "BREAK": "무너짐",
                    "DEFLECT": "회피", "ANSWER": "답함"}.get(q["stance"], "")
            ev = f" [{q['clue']}]" if q["clue"] else ""
            print(f"     → {q['cast']}에게{ev} — 「{_cut(q['q'], 52)}」  ({mark})")
            if n >= 3:
                break
        v = lg.get("verdict")
        if v:
            print(f"     ◆ 지목 — {lg['result']['named']} · 「{_cut(v.get('why'), 60)}」")
        cx = lg["confront"]
        if cx:
            print(f"     ▸ 대질 {cx['a']} ↔ {cx['b']} — 「{_cut(cx['q'], 46)}」")
            if cx.get("note"):
                print(f"       드러난 것 — {_cut(cx['note'], 60)}")

    # ── 알 리 없는 것을 묻지는 않았나 ──
    print()
    rule("═")
    print("  알 리 없는 것을 묻지는 않았나")
    rule("═")
    any_ug = False
    for lg in logs:
        r = lg["result"]
        if not (r["ungrounded"] or r["ungrounded_fixed"]):
            continue
        any_ug = True
        print(f"     {lg['who']:9} 되돌려 고침 {r['ungrounded_fixed']} · 그대로 나감 {r['ungrounded']}")
        for x in lg["ungrounded"][:2]:
            print(f"        [{', '.join(x['words'])}] 「{x['before']}」")
            if x["after"]:
                print(f"           → 「{x['after']}」")
    if not any_ug:
        print("     없다 — 모두 아는 것으로만 물었다")

    # ── 수를 어떤 차례로 두었나 ──
    print()
    rule("═")
    print("  무엇을 보고 다음 수를 두었나 (앞 다섯 수)")
    rule("═")
    for lg in logs:
        print(f"\n  ── {lg['who']}")
        for j in lg["journal"][:5]:
            got = j.get("얻은 것")
            got = (", ".join(got) if isinstance(got, list) else str(got or "")) or "—"
            if j["did"] == "뒤졌다":
                print(f"     {j['r']}R {j['did']} {j.get('어디','')} "
                      f"· 근거 {j.get('근거') or '—'} → {got}")
            else:
                print(f"     {j['r']}R {j['did']} {j.get('누구','')} "
                      f"· 근거 {j.get('근거') or '—'} · 「{j.get('질문','')}」 "
                      f"→ {j.get('반응','')} {got if got != '—' else ''}")

    # ── 비밀은 어떻게 열렸나 ──
    print()
    rule("═")
    print("  비밀은 어떻게 열렸나")
    rule("═")
    by = collections.Counter()
    for lg in logs:
        for sec in lg["secrets"]:
            by[(lg["who"], sec["how"])] += 1
    if by:
        for (who, how), n in sorted(by.items()):
            print(f"     {who:9} {how:4} {n}개")
    else:
        print("     하나도 안 열렸다")

    print()
    rule("═")
    print("  한 판을 처음부터 보려면:  python3 agents.py --full 형사")
    rule("═")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="91_dsl_demo.json")
    ap.add_argument("--who", nargs="*", default=list(PA.PERSONAS))
    ap.add_argument("--full", default=None, help="한 성격의 판을 다 보여 준다")
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--out", default=None, help="기록을 JSON으로 남긴다")
    ap.add_argument("--repeat", type=int, default=1,
                    help="성격마다 몇 판씩 — 한 판만 보면 널뛴다(적중 5/6 다음 판 1/6)")
    a = ap.parse_args()

    path = a.scenario if "/" in a.scenario else f"scenarios/{a.scenario}"
    if not glob.glob(path):
        print(f"그런 시나리오가 없습니다: {path}")
        sys.exit(1)
    s = json.load(open(path, encoding="utf-8"))

    #   용의자는 길게, 판정자는 JSON 한 줄이면 된다 — 상한을 따로 준다
    llm = PA.open_llm(model=a.model)               # 용의자용 (길게)
    llm_p = PA.open_llm(model=a.model, tokens=200) # 판정자용 (한 줄)
    if not llm:
        print("  .apikey 가 없어 규칙으로 돌립니다 — 질문은 틀에서 나옵니다.")
    who = [a.full] if a.full else [w for w in a.who if w in PA.PERSONAS]

    print()
    rule("═")
    print(f"  「{s['meta']['title']}」  ·  판정자 {len(who)}명이 저마다의 방식으로 판다")
    print("  " + " · ".join(f"{w}({PA.PERSONAS[w]['color']})" for w in who))
    rule("═")

    logs = []
    for w in who:
        for i in range(max(1, a.repeat)):
            tag = w if a.repeat <= 1 else f"{w}#{i + 1}"
            if not a.full:
                print(f"\n  … {tag} 돌리는 중", end="", flush=True)
            lg = play(s, w, llm_p, llm, rounds=a.rounds, verbose=bool(a.full))
            lg["who"] = tag
            lg["persona"] = w
            logs.append(lg)
            if a.out:      # 한 판이 끝날 때마다 덮어써 둔다 — 뒤에서 죽어도 남는다
                try:
                    json.dump(logs, open(a.out, "w", encoding="utf-8"),
                              ensure_ascii=False, indent=1)
                except Exception:
                    pass
            if not a.full:
                r = lg["result"]
                print(f" ✓  단서 {r['clues']} · 비밀 {r['secrets']} · "
                      f"{r['named']} {'적중' if r['correct'] else '빗나감'}")

    try:
        table(logs, s)
    except Exception as e:
        print(f"\n  (표를 그리다 걸렸습니다 — 기록은 남아 있습니다: {e})")
    if llm:
        tin = llm.tokens_in + (llm_p.tokens_in if llm_p else 0)
        tout = llm.tokens_out + (llm_p.tokens_out if llm_p else 0)
        calls = llm.calls + (llm_p.calls if llm_p else 0)
        cost = tin / 1e6 * 0.15 + tout / 1e6 * 0.60
        print(f"  호출 {calls}회 · 약 {cost * 1400:.0f}원")
    if a.out:
        json.dump(logs, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  기록 — {a.out}")


if __name__ == "__main__":
    main()
