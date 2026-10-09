# -*- coding: utf-8 -*-
"""
catalog.py — **이미 만들어 둔 사건 목록**을 하나로 모은다.

왜 필요한가
  세계관 입력 화면에서 사람이 '헨젤과 그레텔'이라고 적었을 때,
  우리에게 이미 그 편이 있으면 **새로 각색할 이유가 없다.** 그냥 꺼내 쓰면 된다.
  (커스텀 생성 모델은 아직 만드는 중이니, 당분간은 이쪽이 본선이다.)

무엇을 내나
  out/catalog.json — 편마다 원작 이름·다른 이름들·제목·시대·문화권·난이도·규모·표지 그림 지시
  검색은 **다른 이름(aliases)까지 맞춰 본다** — 띄어쓰기·'전'·'설화' 붙고 떨어지는 것

사용:
    python catalog.py            # 만들고 표로 보여 준다
    python catalog.py --quiet
"""
import json, glob, os, re, sys, argparse


def aliases(origin, title):
    a = set()
    o = (origin or "").strip()
    if not o:
        return []
    a.add(o)
    a.add(o.replace(" ", ""))
    # 괄호 안 딴 이름도 검색어로 쓴다 — '나생문(라쇼몽·곤자쿠 설화)'
    base = re.sub(r"\s*\([^)]*\)", "", o).strip()
    if base:
        a.add(base); a.add(base.replace(" ", ""))
    for inner in re.findall(r"\(([^)]*)\)", o):
        for x in re.split(r"[·,/]| 또는 ", inner):
            x = re.sub(r"(계 소설|소설|설화|민담|고전)$", "", x.strip()).strip()
            if len(x) >= 2:
                a.add(x); a.add(x.replace(" ", ""))
    o = base or o
    for suf in ("전", "설화", "이야기", "기", "록"):
        if o.endswith(suf) and len(o) > len(suf) + 1:
            a.add(o[: -len(suf)])
            a.add(o[: -len(suf)].replace(" ", ""))
    for part in re.split(r"과 |와 |·", o):
        p = part.strip()
        if len(p) >= 2:
            a.add(p)
    if title:
        a.add(title.strip())
    return sorted(x for x in a if x)


def build():
    rows = []
    for f in sorted(glob.glob("scenarios/[0-9]*.json")):
        s = json.load(open(f, encoding="utf-8"))
        m = s.get("meta", {})
        bg = ((s.get("background") or {}).get("setting_raw") or {})
        cfg = s.get("config", {}) or {}
        u = s.get("ui") or {}
        rows.append({
            "id": os.path.basename(f).replace(".json", ""),
            "file": f,
            "origin": m.get("origin", ""),
            "aliases": aliases(m.get("origin", ""), m.get("title", "")),
            "title": m.get("title", ""),
            "era": m.get("era", "") or bg.get("era", ""),
            "culture": bg.get("culture", ""),
            "tone": bg.get("tone", ""),
            "logline": (s.get("intro") or {}).get("twist", "")[:70],
            "suspects": len(s.get("cast", [])),
            "rounds": cfg.get("rounds", 3),
            "places": len(((s.get("map") or {}).get("places") or [])),
            "clues": len(s.get("clue_graph", [])),
            "difficulty": (s.get("difficulty") or {}).get("label", ""),
            "stars": (s.get("stars") or {}).get("stars", ""),
            "stars_n": (s.get("stars") or {}).get("n"),
            "stars_label": (s.get("stars") or {}).get("label", ""),
            "solve_rate": (s.get("difficulty") or {}).get("solve_rate"),
            "narration_pages": (u.get("narration") or {}).get("page_count"),
            "art_total": (u.get("art_specs") or {}).get("total"),
            "cover": {
                "w": 640, "h": 400,
                "prompt_ko": f"{m.get('title','')} — 표지. {bg.get('tone','')}",
                "prompt_en": f"cover art for a murder mystery case titled '{m.get('title','')}', "
                             f"{bg.get('culture','')} setting, moody, no text, 640x400",
            },
        })
    cat = {
        "note": "이미 만들어 둔 사건. 세계관 입력에서 이 목록에 걸리면 새로 각색하지 않고 꺼내 쓴다.",
        "match_rule": "입력을 공백 제거·소문자화한 뒤 aliases와 정확일치 → 부분일치 순으로 찾는다.",
        "count": len(rows),
        "cases": rows,
    }
    json.dump(cat, open("scenarios/catalog.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return cat


def find(cat, q):
    """입력 낱말로 이미 만든 편을 찾는다."""
    k = re.sub(r"\s+", "", str(q or "")).lower()
    if not k:
        return None
    for c in cat["cases"]:
        if any(re.sub(r"\s+", "", a).lower() == k for a in c["aliases"]):
            return c
    for c in cat["cases"]:
        if any(k in re.sub(r"\s+", "", a).lower() or re.sub(r"\s+", "", a).lower() in k
               for a in c["aliases"] if len(a) >= 2):
            return c
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--find", default="")
    a = ap.parse_args()
    cat = build()
    if a.find:
        hit = find(cat, a.find)
        print(f"「{a.find}」 → " + (f"{hit['id']} · {hit['title']}" if hit else "없음 (새로 각색해야 함)"))
        sys.exit(0)
    if not a.quiet:
        print(f"{'원작':16}{'제목':22}{'난이도':8}{'용의자':5}{'라운드':5}{'장소':4}{'단서':4}{'쪽':4}{'그림':4}")
        print("-" * 78)
        for c in cat["cases"]:
            print(f"{c['origin'][:15]:16}{c['title'][:21]:22}{c['difficulty']:8}"
                  f"{c['suspects']:^5}{c['rounds']:^5}{c['places']:^4}{c['clues']:^4}"
                  f"{c['narration_pages'] or '-':^4}{c['art_total'] or '-':^4}")
    print(f"\nout/catalog.json — {cat['count']}편")
