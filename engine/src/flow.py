# -*- coding: utf-8 -*-
"""
flow.py — **몰입이 끊기는 자리**를 찾는다.

왜 또 만드나
  fun.py는 23편 모두 89.5~97.2점을 준다(표준편차 1.8). 전부 "재미있다"고 하는
  지표는 아무것도 말해 주지 않는다. 기능이 **있느냐 없느냐**만 세기 때문이다.
  정답률(0.39~0.68)은 잘 퍼지니 난이도는 이미 볼 수 있다. 없는 것은 **흐름**이다.

  판이 재미없어지는 자리는 대개 정해져 있다.
    · 물어볼 이유가 없는 인물이 앉아 있다
    · 물어야 할 낱말을 플레이어가 알 길이 없다
    · 한 라운드에 할 일이 없다
    · 의심이 한 사람에게만 쏠려 나머지가 장식이 된다
    · 결정적인 것이 전부 끝에 몰려 앞이 늘어진다

검사 항목
  DEAD-suspect    아무 단서도 안 걸리고 남의 비밀에도 안 엮인 인물
  TRIGGER-unreach 비밀을 여는 낱말이 어떤 단서에도 나오지 않는다 (물어볼 방법이 없다)
  REWARD-gap      라운드별 새 정보량이 심하게 치우쳤다
  SUSPICION-skew  혐의를 가리키는 단서가 한 사람에게만 몰렸다
  LATE-load       결정적인 것이 마지막 라운드에만 있다
  HOOK-weak       1라운드에 '이상한 점'이 드러나지 않는다 — 왜 파고들지?
  MID-sag         2라운드에 새 단서도 이벤트도 없다
  SECRET-flat     비밀들이 무게가 같아 누구를 파도 똑같다

사용:
    python flow.py                       # 전편, 한 표로
    python flow.py out/13_푸른수염.json
"""
import json, glob, sys, os, collections, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")


def _by_round(s):
    d = collections.defaultdict(list)
    for cl in s["clue_graph"]:
        d[cl.get("reveal_round") or 1].append(cl)
    return d


def analyse(s):
    bad, note = [], {}
    cast = s["cast"]
    ids = {c["id"] for c in cast}
    names = {c["id"]: c["name"] for c in cast}
    rounds = s.get("config", {}).get("rounds", 3)
    byr = _by_round(s)
    blob_all = json.dumps(s["clue_graph"], ensure_ascii=False)

    # ① 물어볼 이유가 없는 인물
    touched = collections.Counter()
    for cl in s["clue_graph"]:
        for t in (cl.get("affects") or []):
            touched[t] += 1
        if cl.get("points_to"):
            touched[cl["points_to"]] += 1
        for e in (cl.get("exculpates") or []):
            touched[e] += 1
        for cid, nm in names.items():
            if nm and nm in (cl.get("surface", "") + cl.get("implies", "")):
                touched[cid] += 1
    dead = [names[i] for i in ids if touched[i] == 0]
    if dead:
        bad.append(("DEAD-suspect", f"단서에 한 번도 안 걸리는 인물: {dead} — 심문할 이유가 없다"))
    note["touch"] = {names[i]: touched[i] for i in ids}

    # ② 물어야 할 낱말을 알 길이 있는가
    for c in cast:
        trig = [t for pp in (c.get("pressure_points") or []) for t in (pp.get("trigger") or [])]
        if not trig:
            continue
        seen = [t for t in trig if t and t in blob_all]
        if not seen:
            bad.append(("TRIGGER-unreach",
                        f"{c['name']}의 비밀을 여는 말 {trig[:3]} — 어떤 단서에도 안 나온다"))

    # ③ 라운드별 정보량
    counts = [len(byr.get(r, [])) for r in range(1, rounds + 1)]
    note["per_round"] = counts
    if counts and max(counts) >= 4 * max(1, min(counts)):
        bad.append(("REWARD-gap",
                    f"라운드별 새 단서 {counts} — 한쪽에 쏠려 다른 라운드가 빈다"))

    # ④ 의심 쏠림
    acc = collections.Counter(cl["points_to"] for cl in s["clue_graph"] if cl.get("points_to"))
    if acc:
        top, n = acc.most_common(1)[0]
        if len(acc) == 1 and n >= 2:
            bad.append(("SUSPICION-skew",
                        f"혐의 단서가 {names.get(top,top)} 한 사람에게만 {n}개 — 나머지가 장식이 된다"))
    note["accuse"] = {names.get(k, k): v for k, v in acc.items()}

    # ⑤ 결정적인 것이 끝에만
    dec = [cl for cl in s["clue_graph"] if cl.get("decisive")]
    exc = [cl for cl in s["clue_graph"] if cl.get("exculpates")]
    if dec and all((cl.get("reveal_round") or 1) == rounds for cl in dec):
        early_exc = [cl for cl in exc if (cl.get("reveal_round") or 1) < rounds]
        if len(early_exc) < 2:
            bad.append(("LATE-load",
                        f"결정타도 배제 단서도 마지막 라운드에 몰렸다 — 앞 두 라운드가 늘어진다"))

    # ⑥ 1라운드 흡인력 — '이상한 점'이 드러나는가
    r1 = byr.get(1, [])
    hook_words = ("어긋", "이상", "없어졌", "사라졌", "뒤집", "밀실", "잠겨", "맞지 않",
                  "다르다", "다른", "새로", "겹쳐", "타다 만", "빈 ", "비어")
    if not any(any(w in (cl.get("surface", "") + cl.get("implies", "")) for w in hook_words)
               for cl in r1):
        bad.append(("HOOK-weak", "1라운드 단서에 '이상한 점'이 없다 — 왜 파고들어야 하는지가 안 선다"))

    # ⑦ 2라운드 처짐
    if rounds >= 3:
        mid = byr.get(2, [])
        ev2 = [e for e in (s.get("events") or []) if e.get("round") == 2]
        if not mid and not ev2:
            bad.append(("MID-sag", "2라운드에 새 단서도 이벤트도 없다"))

    # ⑧ 비밀의 무게가 다 같은가
    kinds = [(c.get("secret") or {}).get("type", "") for c in cast]
    pts = [sec.get("points_if_kept", 1) for c in cast for sec in (c.get("secrets") or [])]
    if len(set(k for k in kinds if k)) <= 1 and len(kinds) > 2:
        bad.append(("SECRET-flat", f"비밀 성격이 전부 같다({kinds[0]}) — 누구를 파도 똑같다"))
    note["secret_kinds"] = kinds
    return bad, note


def narrowing(s):
    """라운드가 지날수록 **후보가 몇 명 남는가.**
    2라운드에 이미 한 명만 남으면 3라운드는 확인 절차일 뿐이다 — 그래서 쉽다."""
    rounds = s.get("config", {}).get("rounds", 3)
    ids = [c["id"] for c in s["cast"]]
    out, alive = [], set(ids)
    for r in range(1, rounds + 1):
        for cl in s["clue_graph"]:
            if (cl.get("reveal_round") or 1) > r:
                continue
            for e in (cl.get("exculpates") or []):
                alive.discard(e)
            if cl.get("decisive") and cl.get("points_to"):
                alive = {cl["points_to"]}
        out.append(len(alive))
    return out


def main(paths):
    counts = collections.Counter()
    lines = ["# 흐름·몰입 점검", ""]
    worst = []
    for p in sorted(paths):
        s = json.load(open(p, encoding="utf-8"))
        bad, note = analyse(s)
        nm = os.path.basename(p)
        print(f"\n═══ {nm}  {s['meta'].get('title','')}")
        nar = narrowing(s)
        print(f"  라운드별 단서 {note['per_round']} · 남는 후보 {nar} · 인물별 접점 "
              + ", ".join(f"{k}:{v}" for k, v in note["touch"].items()))
        if len(nar) >= 2 and nar[-2] <= 1:
            bad.append(("EARLY-solved",
                        f"후보가 {nar} — 마지막 라운드 전에 이미 한 명으로 좁혀진다"))
        if nar and nar[0] <= 2:
            bad.append(("EARLY-solved", f"1라운드에 벌써 후보가 {nar[0]}명 — 너무 빨리 좁혀진다"))
        for k, why in bad:
            counts[k] += 1
            print(f"  ❌ {k}  {why}")
        worst.append((len(bad), nm))
        if bad:
            lines.append(f"### {nm}")
            lines += [f"- **{k}** — {why}" for k, why in bad]
            lines.append("")
    print("\n" + "=" * 62)
    for k, v in counts.most_common():
        print(f"  {k:18} {v}")
    print(f"  합계 {sum(counts.values())}건")
    worst.sort(reverse=True)
    print("\n손볼 순서:", ", ".join(f"{n}({c})" for c, n in worst[:5] if c))
    open("flow_report.md", "w", encoding="utf-8").write("\n".join(lines))
    print("저장: flow_report.md")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    main(glob.glob(arg))
