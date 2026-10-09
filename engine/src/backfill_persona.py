# -*- coding: utf-8 -*-
"""깊은 페르소나(관계도/지식경계/말투표본) + 비밀 탐색 단서 백필 — 기존 골드를 35/35로.
기존 rich 필드(life_story·alibi·secret·kill_motive·persona)에서 근거 있게 구성."""
import json, glob, re, sys

def first_sent(t):
    t=(t or "").strip()
    m=re.split(r"(?<=[.!?。])\s", t)
    return m[0] if m else t

def backfill(path):
    s=json.load(open(path,encoding="utf-8"))
    cast=s["cast"]; ids=[c["id"] for c in cast]
    places={p["id"]:p for p in s.get("map",{}).get("places",[])}
    owner_place={p.get("owner"):pid for pid,p in places.items()}
    dslot=s.get("death",{}).get("time_slot"); vic=s.get("victim",{}).get("name","피해자")
    name={c["id"]:c["name"] for c in cast}
    for c in cast:
        # example_lines
        per=c.setdefault("persona",{})
        if len(per.get("example_lines") or [])<2:
            lines=[per.get("example_line"), first_sent(c.get("alibi_narration",""))]
            pp=(c.get("pressure_points") or [{}])[0].get("reveals","")
            if pp: lines.append(first_sent(pp))
            per["example_lines"]=[l for l in dict.fromkeys(lines) if l][:3]
        # relationships
        if not c.get("relationships"):
            rel={"victim": c.get("kill_motive","피해자와 얽힌 사이")}
            others=[i for i in ids if i!=c["id"]][:2]
            for o in others:
                oc=next(x for x in cast if x["id"]==o)
                rel[o]=f"{oc.get('public','')} — 같은 사건에 얽힌 사이"
            c["relationships"]=rel
        # knows / does_not_know
        if not c.get("knows"):
            here=places.get((c.get("timeline") or {}).get(dslot),{}).get("name","")
            c["knows"]=[f"그 밤 자신은 {here}에 있었다",
                        f"자신의 감춘 사정({c.get('secret',{}).get('type','비밀')})",
                        f"{vic}와의 관계와 그날의 정황"]
        if not c.get("does_not_know"):
            c["does_not_know"]=(["곳간·현장에서 자신의 거짓이 어떻게 드러날지"] if c.get("is_culprit")
                                else ["범인이 누구인지","다른 이들이 감춘 비밀","사건 현장의 자세한 정황"])
    # 비밀 탐색 단서: 소유 장소에 location 단서 없는 용의자 보강
    loc_places={cl.get("location") for cl in s["clue_graph"] if cl.get("channel")=="location"}
    n=1
    for c in cast:
        pl=owner_place.get(c["id"])
        if pl and pl not in loc_places:
            sec=c.get("secret",{})
            s["clue_graph"].append({
                "id":f"SB{n}","channel":"location","medium":"물건","location":pl,
                "surface":f"{places[pl]['name']}에서 나온, {sec.get('text','감춘 사정')}을(를) 보여주는 흔적.",
                "implies":f"{c['name']}의 비밀={sec.get('type','비밀')}. 살인과 무관(레드헤링).",
                "weight":"red_herring","points_to":None,"exculpates":[],"reveal_round":2,"decisive":False})
            loc_places.add(pl); n+=1
    json.dump(s,open(path,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(f"  ✓ {path}")

if __name__=="__main__":
    targets=sys.argv[1:] or ["scenarios/G_전우치전.json","scenarios/H_홍길동전.json","scenarios/I_운영전.json","scenarios/J_아랑설화.json"]
    for t in targets: backfill(t)
