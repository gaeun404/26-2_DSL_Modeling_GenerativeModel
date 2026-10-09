# -*- coding: utf-8 -*-
"""
search_label.py — **탐색 선택지가 그 방에 실제로 있는 물건을 가리키게 한다.**

■ 왜 (2026-08-26, 자동 플레이 관찰)
  판정자 에이전트를 끝까지 돌려 보니 선택지에 이런 것들이 떠 있었다.

      지하 사물함 구역에서   · 창가를 뒤져 본다        ← 창이 없는 지하다
      옆 빈 세미나실에서     · 비면 리허설을 훑어본다   ← 물건이 아니라 문장 조각
      재현의 지정석에서      · 준비 메모를 훑어본다 / 메모를 들여다본다  ← 같은 것이 두 번

  ui.py 는 단서가 걸린 자리에만 그 단서의 물건 이름을 쓰고, 나머지 칸은
  장소 설명에서 낱말을 긁어 채운다. 그런데 ui.py 가 도는 시점에는 아직
  그림 명세(art.must_show)가 없다 — **화면에 무엇이 보이는지 모르는 채로**
  누를 것을 만들고 있었다. 그래서 그림에 없는 물건이 선택지에 올라온다.

■ 무엇을 하나
  단서가 걸리지 않은 '헛 선택지'만 손본다. 그 방 그림에 **반드시 보이는
  것**(art.must_show)과 장소의 features 에서 물건을 꺼내 갈아 끼운다.
  단서가 걸린 선택지(finds)는 한 글자도 건드리지 않는다.

사용:
    python3 search_label.py                      # 전 편
    python3 search_label.py ../scenarios/91_dsl_demo.json
"""
import json, glob, re, sys


def _j(w, pair="을/를"):
    a, b = pair.split("/")
    ch = (w or " ")[-1]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


_TAIL = re.compile(r"[은는이가을를도만의과와에서로]$")


def _thing(phrase):
    """설명 한 토막에서 **손으로 만질 수 있는 이름**만 남긴다.

    '얼룩덜룩 지운 자국이 남은 화이트보드 — 구석에 지우다 만 낙서 자국'
      → '화이트보드'
    '책상 밑 지우개 가루' → '지우개 가루'
    """
    x = re.split(r"[—(]", str(phrase or ""))[0].strip()
    x = re.sub(r"\s+", " ", x)
    if not x:
        return ""
    toks = x.split(" ")
    last = _TAIL.sub("", toks[-1])
    if len(last) < 3 and len(toks) >= 2:
        prev = _TAIL.sub("", toks[-2])
        if len(prev) >= 2:
            return f"{prev} {last}".strip()
    return last


def _pool(ps, place):
    """이 방에서 고를 수 있는 물건 — 그림에 보이는 것이 먼저."""
    out, seen = [], set()
    for src in ((ps.get("art") or {}).get("must_show") or []) + list(place.get("features") or []):
        w = _thing(src)
        if len(w) >= 2 and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def _obj_of(label):
    """'지우개 가루를 뒤져 본다' → ('지우개 가루', '를 뒤져 본다')"""
    m = re.match(r"^(.*?)(을|를)\s+(.+)$", str(label or ""))
    return (m.group(1), m.group(3)) if m else (None, None)


def fix(path, verbose=True):
    s = json.load(open(path, encoding="utf-8"))
    places = {p["id"]: p for p in s.get("map", {}).get("places", [])}
    n_fixed = 0

    for ps in (s.get("ui") or {}).get("place_screens", []):
        place = places.get(ps.get("place_id")) or {}
        pool = _pool(ps, place)
        if not pool:
            continue
        # 그 방에서 '진짜'로 인정하는 이름들 — 그림·features 안에 있는 말
        blob = " ".join(((ps.get("art") or {}).get("must_show") or [])
                        + list(place.get("features") or []))
        rounds = ps.get("rounds") or []
        rounds = rounds if isinstance(rounds, list) else list(rounds.values())
        for rd in rounds:
            used = set()
            for act in (rd.get("actions") or []):
                obj, verb = _obj_of(act.get("label"))
                if act.get("finds") or not obj:
                    if obj:
                        used.add(obj)
                    continue
                # 같은 것을 두 번 누르게 두지 않는다 —
                # '메모'와 '준비 메모', '펌프대'와 '시럽 펌프대'는 같은 자리다.
                dup = any(obj in u or u in obj for u in used)
                ok = (obj in blob) and not dup and len(obj) >= 2
                if ok:
                    used.add(obj)
                    continue
                new = next((w for w in pool
                            if not any(w in u or u in w for u in used) and w != obj), None)
                if not new:
                    used.add(obj)
                    continue
                used.add(new)
                act["label"] = f"{new}{_j(new)} {verb}"
                act["result_lines"] = [
                    re.sub(rf"^{re.escape(obj)}(은|는|이|가|을|를)",
                           lambda m: new + _j(new, {"은": "은/는", "는": "은/는",
                                                    "이": "이/가", "가": "이/가",
                                                    "을": "을/를", "를": "을/를"}[m.group(1)]),
                           ln)
                    for ln in (act.get("result_lines") or [])]
                n_fixed += 1

    json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if verbose:
        print(f"  {path.split('/')[-1][:28]:30s} 헛 선택지 {n_fixed}개를 그 방 물건으로 바꿈")
    return n_fixed


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("../scenarios/[0-9]*.json"))
    tot = sum(fix(f) for f in files)
    print(f"\n{len(files)}편 · 모두 {tot}개")
