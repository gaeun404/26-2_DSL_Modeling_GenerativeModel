# -*- coding: utf-8 -*-
"""
spread_hints.py — **범인을 가리키는 실마리를 갈래마다 하나씩 흩는다.**

■ 왜 (2026-08-27, 판정자 에이전트 여섯 판 관찰)
  성격이 다른 판정자 여섯을 풀어놨더니 **여섯 명 모두 엉뚱한 사람을 짚었다.**
  근거가 하나같이 똑같았다 —

      「유가람의 자기소개에 '좋아하는 향: 니코틴'이 적혀 있고,
        회장 컵에서 고농도 니코틴이 검출되었기 때문입니다」

  단서를 세어 보니 까닭이 뚜렷했다. 91편 열여덟 장 가운데

      진범을 가리키는 단서 : KD 한 장         (3라운드, 장소 탐색)
      미끼가 가리키는 단서 : K5 한 장         (1라운드, 자동 공개)
      나머지 열여섯 장     : 아무도 가리키지 않음

  결정타 한 장을 못 찾으면 남는 실마리는 **미끼뿐**이다. 그러니 여섯이
  똑같이 미끼를 물었다. 이건 판정자가 멍청해서가 아니라 판이 그렇게 짜여서다.

■ 무엇을 하나
  이미 있는 단서 가운데 **본문에 범인이 이미 드러나 있는 것**을 찾아
  가리키는 대상만 채워 넣는다. 새 단서를 만들지 않는다 — 없던 사실을
  보태면 그건 다른 게임이 된다.

      · 이름이 적혀 있다           「…성하는 휴식 시작 40초 만에 되돌아갔다」
      · 직책이 적혀 있다           「사물함 열쇠는 홍보부장 것 하나뿐이다」
      · 제 것이라 밝힌 소지품      (심문에서 실토해야 나오는 물건)

  그리고 **갈래를 갈라 준다.** 라운드 자동 공개 / 장소 탐색 / 심문 실토 —
  한 갈래에서만 나오면 그 갈래를 안 쓰는 사람은 영영 못 짚는다.
  대질에서 나오는 단서는 엔진이 그 자리에서 만들므로 여기서 손대지 않는다.

  결정타는 3점, 여기서 채운 것은 1점이다(엔진 셈법). 그러니 결정타의 값은
  그대로 남고, 두루 모은 사람만 결정타 없이도 겨우 이름에 닿는다.

사용:
    python3 spread_hints.py                      # 전 편
    python3 spread_hints.py ../scenarios/91_dsl_demo.json
    python3 spread_hints.py --check              # 고치지 않고 세어만 본다
"""
import json, glob, re, sys

MAX_ADD = 1          # ★3 → 1 (2026-08-28). 250판 전수 스윕에서 열여덟 편이
#   다섯 방식 전원 적중으로 나왔다. 범인을 가리키는 단서가 다섯 장까지 쌓이면
#   어디로 굴러도 범인이 나온다. 결정타 + 보조 하나면 갈래는 열리고 판은 남는다.
MIN_ROUND = 2        # ★1라운드 단서는 건드리지 않는다 (2026-08-27).
#   처음엔 라운드를 가리지 않고 채웠더니 eval_policies가 곧바로 물었다 —
#   「1라운드에 성급 지목이 적중 — 너무 뻔함」 4편. 첫 밤은 동선을 재는 밤이고
#   이름은 아직 떠오르지 않아야 한다. 실마리는 2라운드부터 흩는다.
MARK = "spread_hints"   # 이 도구가 채운 자리 — 다시 돌릴 때 지우고 새로 잡는다
CHANNEL_GROUP = {
    "spine": "라운드 자동 공개",
    "crime_scene": "라운드 자동 공개",
    "location": "장소 탐색",
    "record": "장소 탐색",
    "physical": "장소 탐색",
    "belongings": "심문 실토",
}


def _role_head(pub):
    return re.split(r"[—,·(]", str(pub or ""))[0].strip()


def _implicates(cl, cul, roles_of_others, others):
    """이 단서 본문에 **범인이 이미 드러나** 있는가. 없던 사실을 보태지 않는다."""
    surf = str(cl.get("surface") or "")
    name = cul["name"]
    # ★여러 사람을 한꺼번에 부르는 단서는 임자를 가리키지 못한다.
    #   91편의 '운영진 자기소개 페이지'가 그렇다 — 여섯 사람이 다 적혀 있다.
    named = sum(1 for o in others
                if o["name"] in surf or (len(o["name"]) > 1 and o["name"][1:] in surf))
    if named >= 2 and (name in surf or name[1:] in surf):
        # 다만 **범인만 한 일**이 적혀 있으면 그건 가리키는 것이 맞다.
        #   「…지원·은민·승원이 차례로 찍혔다 … 성하는 40초 만에 되돌아갔다」
        #   여섯 이름이 다 나오는 명부와 이것은 다르다.
        act = ("되돌아|돌아갔|혼자|먼저|나갔|들어갔|가져|만지작|숨기|챙기|"
               "다녀|되짚|남았|빠져나")
        near = False
        for m in re.finditer(re.escape(name[1:] if len(name) > 1 else name), surf):
            if re.search(act, surf[m.end():m.end() + 30]):
                near = True
                break
        if not near:
            return None
    # ① 이름 — 성만 적힌 경우까지 (차연우 → '성하')
    for n in {name, name[1:], name[-2:]}:
        if len(n) >= 2 and n in surf:
            return f"이름 '{n}'이 적혀 있다"
    # ② 직책 — 다른 사람과 겹치지 않는 직책일 때만
    role = _role_head(cul.get("public"))
    for w in re.findall(r"[가-힣]{2,}", role):
        if w and w in surf and w not in roles_of_others:
            return f"직책 '{w}'가 적혀 있다"
    # ③ 제 소지품 — 실토해야 나오는 물건은 임자가 분명하다
    if cl.get("channel") == "belongings":
        for b in (cul.get("belongings") or []):
            if b.get("id") == cl.get("id") or (b.get("name") and b["name"] in surf):
                return "본인이 실토하며 내놓는 물건이다"
    return None


def _jo(w, pair="이/가"):
    a, b = pair.split("/")
    ch = str(w or " ")[-1]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


def name_decisive(s, cast, cul):
    """★결정타가 임자를 **이름으로** 부르게 한다 (2026-08-28).

    91편 자동 플레이에서 배운 것 — 결정타를 손에 쥐고 그 내용을 정확히 읽고도
    미끼를 짚었다. 미끼는 이름으로 부르는데("좋아하는 향: 니코틴(유가람)")
    결정타는 직책이나 정황으로만 불렀기 때문이다. 읽는 사람에게는 이름이 이긴다.
    **한 걸음 더 생각해야 닿는 결정타는 결정타가 아니다.**

    본문에 이름이 없으면 꼬리 한 문장을 붙인다. 없던 사실을 보태는 것이 아니라
    points_to 로 이미 정해져 있는 임자를 **글로도** 말하게 하는 것뿐이다.
    """
    nm = cul["name"]
    fixed = []
    for d in (s.get("clue_graph") or []):
        if not d.get("decisive"):
            continue
        surf = str(d.get("surface") or "")
        if nm in surf or (len(nm) > 1 and nm[1:] in surf):
            continue
        med = str(d.get("medium") or "") + str(d.get("channel") or "")
        #   글쓰기 동사는 함부로 쓰지 않는다 — 발자국 단서에 '적을 수 있었던
        #   사람'이 붙는 사고가 났다. '임자'는 문서든 물건이든 자국이든 통한다.
        if any(w in med for w in ("증언", "소문", "spine")):
            tail = f" 말끝이 가리키는 것은 {nm} 하나다."
        else:
            tail = f" 이것의 임자로 남는 것은 {nm}뿐이다."
        d["surface"] = surf.rstrip() + tail
        d["named_by"] = MARK
        fixed.append(d["id"])
    return fixed


def fix(path, check=False, verbose=True):
    s = json.load(open(path, encoding="utf-8"))
    cast = s.get("cast") or []
    cul = next((c for c in cast if c.get("is_culprit")), None)
    if not cul:
        return 0
    cid = cul["id"]
    roles_of_others = " ".join(_role_head(c.get("public")) for c in cast if c["id"] != cid)

    # 지난번에 이 도구가 채운 자리는 지우고 새로 잡는다(규칙이 바뀌면 결과도 바뀌어야 한다)
    cleared = 0
    for cl in (s.get("clue_graph") or []):
        if cl.get("points_to_by") == MARK:
            cl.pop("points_to", None)
            cl.pop("points_to_by", None)
            cleared += 1
    # 표시가 없던 시절에 채운 자리도 걷어낸다 (2026-08-28 확대) —
    #   라운드를 가리지 않는다. 본문에서 자동으로 유도되는 범인 단서는 전부 걷고
    #   아래에서 MAX_ADD 만큼만 다시 채운다. 그래야 편마다 개수가 같아진다.
    #   손으로 지은 서사 단서(본문에 이름이 없는 testimony 등)와 결정타는 남는다.
    for cl in (s.get("clue_graph") or []):
        if (cl.get("points_to") == cid and not cl.get("decisive")
                and cl.get("weight") not in ("alibi_break", "testimony")
                and _implicates(cl, cul, roles_of_others,
                                [c for c in cast if c["id"] != cid])):
            cl.pop("points_to", None)
            cleared += 1

    have = [c for c in (s.get("clue_graph") or []) if c.get("points_to") == cid]
    groups_have = {CHANNEL_GROUP.get(c.get("channel"), "그 밖") for c in have}

    cands = []
    for cl in (s.get("clue_graph") or []):
        if cl.get("points_to") or cl.get("weight") == "red_herring":
            continue
        if (cl.get("reveal_round") or 1) < MIN_ROUND:
            continue
        why = _implicates(cl, cul, roles_of_others,
                          [c for c in cast if c["id"] != cid])
        if why:
            grp = CHANNEL_GROUP.get(cl.get("channel"), "그 밖")
            # 아직 비어 있는 갈래를 먼저, 그다음 이른 라운드부터
            cands.append((grp in groups_have, cl.get("reveal_round") or 9, cl["id"], grp, why, cl))
    cands.sort()

    added = []
    for _, _, kid, grp, why, cl in cands:
        if len(added) >= MAX_ADD:
            break
        if not check:
            cl["points_to"] = cid
            cl["points_to_by"] = MARK
        added.append((kid, grp, why))
        groups_have.add(grp)

    named = [] if check else name_decisive(s, cast, cul)

    if (added or cleared or named) and not check:
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if verbose:
        nm = path.split("/")[-1][:26]
        base = len(have)
        print(f"  {nm:28s} 가리키던 단서 {base} → {base + len(added)} "
              f"· 갈래 {len(groups_have)}가지")
        for kid, grp, why in added:
            print(f"       + {kid:5s} [{grp}] {why}")
        for kid in named:
            print(f"       ✎ {kid:5s} 결정타에 이름을 박음")
    return len(added)



def audit(path, verbose=True):
    """**결정타가 임자를 이름으로 가리키는가**를 본다.

    ★2026-08-27. 91편에서 판정자 여섯이 내리 헛짚었다. 까닭은 구조가 아니라
      **글**이었다. 결정타는 임자를 직책으로만 불렀고(「사물함 열쇠는 홍보부장
      것 하나뿐이다」) 미끼는 이름으로 불렀다(「좋아하는 향: 니코틴(유가람)」).
      읽는 사람에게는 이름이 이긴다. 결정타를 손에 쥐고도 미끼를 짚었다.
      한 걸음 더 생각해야 닿는 결정타는 결정타가 아니다.
    """
    s = json.load(open(path, encoding="utf-8"))
    cast = s.get("cast") or []
    cul = next((c for c in cast if c.get("is_culprit")), None)
    if not cul:
        return []
    bad = []
    dec = [c for c in (s.get("clue_graph") or []) if c.get("decisive")]
    for d in dec:
        surf = str(d.get("surface") or "")
        if cul["name"] not in surf and (len(cul["name"]) < 2 or cul["name"][1:] not in surf):
            bad.append(("결정타가 이름을 부르지 않는다", d["id"], surf[:52]))
    # 미끼를 걷어내는 글이 어디엔가 있는가
    herr = [c for c in (s.get("clue_graph") or []) if c.get("weight") == "red_herring"]
    for h in herr:
        who = h.get("points_to")
        if not who:
            continue
        cleared = any(who in (c.get("exculpates") or []) for c in (s.get("clue_graph") or []))
        if not cleared:
            nm = next((c["name"] for c in cast if c["id"] == who), who)
            bad.append((f"미끼({nm})를 걷어낼 글이 없다", h["id"], str(h.get("surface"))[:52]))
    if verbose and bad:
        print(f"  {path.split('/')[-1][:26]:28s}")
        for why, kid, surf in bad:
            print(f"       ! [{kid}] {why} — {surf}…")
    return bad

if __name__ == "__main__":
    check = "--check" in sys.argv
    if "--audit" in sys.argv:
        files = ([a for a in sys.argv[1:] if not a.startswith("--")]
                 or sorted(glob.glob("../scenarios/[0-9]*.json") + glob.glob("../scenarios/91_*.json")))
        tot = sum(len(audit(f)) for f in files)
        print(f"\n{len(files)}편 · 걸린 것 {tot}건")
        sys.exit(0)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("../scenarios/[0-9]*.json") + glob.glob("../scenarios/91_*.json"))
    tot = sum(fix(f, check=check) for f in files)
    print(f"\n{len(files)}편 · 새로 가리키게 한 단서 {tot}장"
          + (" (세어만 봤다)" if check else ""))
