# -*- coding: utf-8 -*-
"""살인 현장을 '독립된 장소(피해자·무소유)'로 분리 — 지도를 [현장 + 용의자 방 5] = 6곳으로.
기존: death.place가 용의자 소유 방(P1)을 겸함 → 변경: 현장 PC(무소유) 신설, 용의자 방 P1은 그 소유자 방으로 정리."""
import json, glob, math, re
from verify import verify

def dist(a,b):
    if not a or not b: return 0
    return math.hypot(a[0]-b[0], a[1]-b[1])

def migrate(path):
    s=json.load(open(path,encoding="utf-8"))
    slots=s["time_slots"]; ds=s["death"]["time_slot"]; dp=s["death"]["place"]
    places=s["map"]["places"]
    pd={p["id"]:p for p in places}
    if "PC" in pd:  # 이미 분리됨
        return None
    old=pd[dp]; owner=old.get("owner")
    owner_name=next((c["name"] for c in s["cast"] if c["id"]==owner), None)

    # 1) 현장 PC 신설(무소유) — 기존 현장의 이름/묘사/특징을 그대로 가져감
    PC={"id":"PC","name":old["name"],"owner":None,"pos":[0.0,0.0],
        "desc":old.get("desc",""),
        "features":old.get("features") or ["현장에 남은 흔적"]}
    # 2) 기존 P1은 그 소유자(용의자)의 '방'으로 재정의(이름/좌표/특징 교체, 소유·id 유지)
    old["name"]=f"{owner_name}의 방" if owner_name else old["name"]
    old["pos"]=[3.0,-1.0]
    old["features"]=[f"{owner_name}의 방에 놓인 세간과 자취",
                     f"{owner_name}의 일상이 밴 물건들"] if owner_name else old["features"]
    # PC를 목록 맨 앞에 삽입
    s["map"]["places"]=[PC]+places
    # 3) 사망 장소 = 현장
    s["death"]["place"]="PC"
    # 4) 사망 시각에 현장(구 dp)에 있던 인물(=범인)만 PC로 이동
    for c in s["cast"]:
        if c["timeline"].get(ds)==dp:
            c["timeline"][ds]="PC"
    # 5) 현장 기반 결정적/지목 단서(location==dp)는 PC로, 비밀(레드헤링)은 방(P1)에 남김
    for cl in s["clue_graph"]:
        if cl.get("channel")=="location" and cl.get("location")==dp:
            if cl.get("decisive") or cl.get("weight")=="incriminating":
                cl["location"]="PC"
    # 5b) 범인 방(구 dp)에 location 단서가 하나도 안 남으면, 범인 '개인 비밀' 탐색 단서를 보강
    #     (현장 증거는 PC로 갔으므로 범인 방이 비면 secret_lint가 깨진다)
    loc_at_room=[cl for cl in s["clue_graph"]
                 if cl.get("channel")=="location" and cl.get("location")==dp]
    if owner and not loc_at_room:
        culprit=next((c for c in s["cast"] if c["id"]==owner), None)
        sec=(culprit or {}).get("secret",{}) or {}
        sec_txt=sec.get("text","")
        ids=[cl["id"] for cl in s["clue_graph"]]
        nid="L%d"%(1+max([int(cl["id"][1:]) for cl in s["clue_graph"]
                          if cl["id"].startswith("L") and cl["id"][1:].isdigit()]+[0]))
        while nid in ids: nid="L%d"%(int(nid[1:])+1)
        s["clue_graph"].append({
            "id":nid,"channel":"location","location":dp,"round":2,"reveal_round":2,
            "weight":"red_herring","decisive":False,"points_to":None,"exculpates":[],
            "text":f"{owner_name}의 방에서 나온 개인적 흔적 — {sec_txt}".strip(" —"),
            "reveals_secret":owner})
    # 6) 지도 이동한도 재조임(현장 이동 포함)
    pd2={p["id"]:p for p in s["map"]["places"]}
    maxmv=0
    for c in s["cast"]:
        tl=[pd2.get(c["timeline"].get(sl),{}).get("pos") for sl in slots]
        for a,b in zip(tl,tl[1:]): maxmv=max(maxmv,dist(a,b))
    s["map"]["max_move_per_slot"]=round(maxmv+0.6,2)

    ok,rep=verify(s)
    json.dump(s,open(path,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    fails=[r for r in rep if not r[1]]
    return ok, [f"{r[0]}:{r[2]}" for r in fails]

if __name__=="__main__":
    for p in sorted(glob.glob("scenarios/[0-9]*.json")):
        r=migrate(p)
        if r is None:
            print(f"  · {p.split('/')[-1]} 이미 분리됨"); continue
        ok,fails=r
        print(f"  {'✅' if ok else '❌'} {p.split('/')[-1]}  현장 분리 · verify {ok}")
        for f in fails: print("      -",f)
