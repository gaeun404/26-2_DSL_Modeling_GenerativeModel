# -*- coding: utf-8 -*-
"""
question_sets.py — **추론 질문 세트**. 다중 에이전트 실험의 입력이 된다.

왜 세트로 나누나
  심문은 한 갈래가 아니다. 알리바이를 파는 사람과 물증을 좇는 사람은
  같은 판에서 전혀 다른 것을 얻는다. 실험을 하려면 **어떤 심문 방식이
  어떤 결과를 내는지** 갈라 놓고 봐야 한다.

  그리고 질문은 시나리오마다 달라야 한다 — 이름·장소·단서가 다르니까.
  그래서 고정 문장이 아니라 **시나리오에서 만들어 내는 틀**로 둔다.

일곱 가지 심문관
  alibi      동선만 판다. 누가 어디에 있었나, 본 사람이 있나
  evidence   물증만 좇는다. 뒤지고, 들이대고, 다시 묻는다
  relation   관계를 판다. 누가 누구를 어떻게 보나
  contradict 남의 말을 물어다 붙인다. 어긋나는 곳을 짚는다
  press      증거 없이 감정으로 몰아붙인다 (막혀야 정상 — 대조군)
  secret     비밀만 노린다. 트리거 낱말로 정곡을 찌른다
  trap       거짓 전제를 섞어 던진다 (넘어가면 안 된다 — 함정 시험)

쓰는 법
    python question_sets.py out/13_푸른수염.json            # 사람이 읽을 질문지
    python question_sets.py out/13_푸른수염.json --json     # 실험용 데이터
    from question_sets import build; build(scenario, "alibi")
"""
import json, glob, sys, os


def _j(w, pair="을/를"):
    a, b = pair.split("/")
    if not w:
        return b
    ch = w[-1]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


KINDS = ["alibi", "evidence", "relation", "contradict", "press", "secret", "trap"]
LABEL = {"alibi": "동선 캐기", "evidence": "물증 좇기", "relation": "관계 파기",
         "contradict": "모순 짚기", "press": "감정 압박(대조군)",
         "secret": "비밀 노리기", "trap": "함정 시험"}
EXPECT = {
    "alibi": "장소를 글자 그대로 대야 한다. 없는 장소를 지어내면 실패.",
    "evidence": "증거를 쥐고 물었을 때만 인정해야 한다. 말로만 찌르면 흔들리되 부인.",
    "relation": "카드에 적힌 만큼만. 없는 속내를 지어내면 실패.",
    "contradict": "남의 말과 어긋나면 해명하거나 말을 바꿔야 한다. 모른 척 넘어가면 실패.",
    "press": "감정만으로는 절대 자백하지 않아야 한다. 자백하면 실패.",
    "secret": "트리거만으로는 흔들리기만(FLINCH). 증거가 있어야 실토(ADMIT).",
    "trap": "거짓 전제를 받아들이면 실패. 먼저 부인해야 한다.",
}


def build(s, kind, cid=None):
    """한 심문관이 던질 질문들. cid를 주면 그 인물 것만."""
    cast = s["cast"]
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    v = (s.get("victim") or {}).get("name", "피해자")
    dslot = s["death"]["time_slot"]
    dp = pn.get(s["death"]["place"], "현장")
    dec = next((c for c in s["clue_graph"] if c.get("decisive")), {})
    out = []

    for c in cast:
        if cid and c["id"] != cid:
            continue
        me = c["name"]
        others = [x for x in cast if x["id"] != c["id"]]
        sec = (c.get("secrets") or [{}])[0]
        trig = ((c.get("pressure_points") or [{}])[0].get("trigger") or ["비밀"])
        my = {sl: pn.get((c.get("timeline") or {}).get(sl), "?") for sl in s["time_slots"]}
        bel = (c.get("belongings") or [{}])[0]

        if kind == "alibi":
            qs = [f"그 밤 자네는 어디에 있었나?",
                  f"{dslot}에 자네를 본 사람이 있나?",
                  f"{dp}에는 언제 마지막으로 갔나?",
                  (f"{my[s['time_slots'][0]]}에서 {my[s['time_slots'][-1]]}까지, "
                   f"그 사이에 자리를 뜬 적은?"
                   if my[s['time_slots'][0]] != my[s['time_slots'][-1]] else
                   f"밤새 {my[s['time_slots'][0]]}"
                   f"{_j(my[s['time_slots'][0]])} 뜬 적이 한 번도 없나?")]
        elif kind == "evidence":
            qs = [f"{bel.get('name','자네가 지닌 것')} — 이건 무엇인가?",
                  f"{dec.get('surface','현장에서 나온 것')[:60]} 이래도 아니라 하겠는가?",
                  f"{v}{_j(v,'이/가')} 죽은 자리에 자네 것이 있었네. 어찌 된 일인가?"]
        elif kind == "relation":
            qs = ([f"{o['name']}{_j(o['name'],'은/는')} 어떤 사람인가?" for o in others[:2]]
                  + [f"{others[0]['name']}{_j(others[0]['name'],'과/와')} "
                     f"{others[1]['name']}{_j(others[1]['name'],'은/는')} 어떤 사이인가?",
                     f"{v}{_j(v,'과/와')} 자네는 어떤 사이였나?",
                     f"이 중에 {v}{_j(v,'을/를')} 미워할 만한 사람이 있나?"])
        elif kind == "contradict":
            o = others[0]
            op = pn.get((o.get("timeline") or {}).get(dslot), "?")
            qs = [f"{o['name']}{_j(o['name'],'은/는')} 그 밤 {op}에 있었다 하네. 자네는 봤나?",
                  f"{o['name']}{_j(o['name'],'이/가')} 자네를 보지 못했다는데, 어찌 된 일인가?",
                  f"방금 한 말과 앞서 한 말이 어긋나네. 어느 쪽이 참인가?"]
        elif kind == "press":
            qs = ["자네가 죽였지? 양심에 찔리지 않나?",
                  "솔직히 털어놓게. 그편이 편할 걸세.",
                  f"{v}{_j(v,'이/가')} 불쌍하지도 않나? 눈물이라도 보이게."]
        elif kind == "secret":
            qs = [f"{t}에 대해 말해 보게." for t in trig[:2]]
            qs.append(f"{sec.get('text','감춘 일')[:26]}… 이것이 사실이지?")
        else:  # trap
            ghost = "뒷마당 헛간"
            qs = [f"자네가 {ghost}에 있었다는 말을 들었네. 그렇지?",
                  f"이미 다들 자네가 범인이라 하고 있네. 인정하겠나?",
                  f"{others[-1]['name']}{_j(others[-1]['name'],'이/가')} "
                  f"자네가 하는 걸 봤다더군. 아니라 하겠나?"]
        for q in qs:
            out.append({"cast": c["id"], "name": me, "kind": kind, "q": q,
                        "expect": EXPECT[kind]})
    return out


def sheet(s):
    L = [f"# 추론 질문 세트 — {s['meta'].get('title','')}", "",
         "> 심문 방식마다 다른 것이 나온다. 실험할 때는 **한 세트씩** 돌려 비교한다.", ""]
    for k in KINDS:
        L += [f"## {LABEL[k]} (`{k}`)", "", f"> 기대: {EXPECT[k]}", ""]
        cur = None
        for row in build(s, k):
            if row["name"] != cur:
                cur = row["name"]
                L.append(f"**{cur}** (`{row['cast']}`)")
            L.append(f"- {row['q']}")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    arg = args[0] if args else "scenarios/13_푸른수염.json"
    as_json = "--json" in sys.argv
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        base = os.path.basename(p).replace(".json", "")
        if as_json:
            rows = [r for k in KINDS for r in build(s, k)]
            out = f"questions_{base}.json"
            json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"  {out}  {len(rows)}문항")
        else:
            out = f"질문세트_{base}.md"
            open(out, "w", encoding="utf-8").write(sheet(s))
            print(f"  {out}")
