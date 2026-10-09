# -*- coding: utf-8 -*-
"""에이전트 그라운딩 보강 — 각 용의자에 relationships/knows/does_not_know/persona.example_lines를
시나리오 자체 데이터(역할·비밀·동기·타임라인·피해자)에서 파생해 채운다.
이 필드들은 (1) 35항목 체크리스트를 충족하고 (2) GPU 실시간 대화 검증 때 에이전트가
정보 공백·자기모순을 내지 않도록 하는 '연기 재료'다. 이미 있으면 건드리지 않는다(멱등)."""
import json, glob, sys

def _j_(w, pair="을/를"):
    a,b=pair.split("/")
    if not w: return b
    ch=w[-1]
    if not ("\uac00"<=ch<="\ud7a3"): return b
    return a if (ord(ch)-0xAC00)%28 else b

def enrich_cast(s):
    cast=s["cast"]; victim=s.get("victim",{}); vname=victim.get("name","피해자")
    slots=s["time_slots"]; dslot=s["death"]["time_slot"]
    pd={p["id"]:p for p in s["map"]["places"]}
    byid={c["id"]:c for c in cast}
    for c in cast:
        # ── relationships ──
        if not c.get("relationships"):
            rel={}
            rel["victim"]=f"{vname}. {c.get('kill_motive','사연이 얽힌 사이')}"
            for o in cast:
                if o["id"]==c["id"]: continue
                rel[o["id"]]=f"{o['name']}({o.get('public','')}). {vname}{_j_(vname)} 둘러싸고 각자의 사정으로 얽힌 사이."
            c["relationships"]=rel
        # ── knows / does_not_know ──
        if not c.get("knows"):
            myplace=pd.get(c["timeline"].get(dslot),{}).get("name","제 자리")
            knows=[]
            # 사망 시각 자기 소재(범인은 '주장'하는 알리바이를 유지)
            if c.get("is_culprit") and c.get("lies"):
                fp=pd.get(c["lies"][0].get("false_place"),{}).get("name","다른 곳")
                knows.append(f"나는 그 밤 {fp}에 있었다고 말한다(공개 진술).")
            else:
                knows.append(f"나는 그 밤({dslot}) {myplace}에 있었다.")
            sec=c.get("secret",{}).get("text")
            if sec: knows.append(f"내 감춘 사정: {sec}.")
            knows.append(f"{vname}에 대한 내 감정: {c.get('motive_label','복잡한 마음')}.")
            c["knows"]=knows
        if not c.get("does_not_know"):
            dnk=[]
            if c.get("timeline",{}).get(dslot)!=s["death"]["place"] and not c.get("is_culprit"):
                dnk.append(f"그 밤 사건 현장({pd.get(s['death']['place'],{}).get('name','현장')})에서 실제로 무슨 일이 있었는지.")
            dnk.append("진범이 누구인지, 결정적 증거가 무엇인지는 알지 못한다.")
            dnk.append("다른 용의자들이 각자 감추고 있는 비밀의 구체적 내용.")
            c["does_not_know"]=dnk
        # ── persona.example_lines(≥2) ──
        per=c.setdefault("persona",{})
        if len(per.get("example_lines") or [])<2:
            lines=[]
            if per.get("example_line"): lines.append(per["example_line"])
            if c.get("alibi_narration"): lines.append(c["alibi_narration"])
            for pp in (c.get("pressure_points") or []):
                r=pp.get("reveals")
                if r and r not in lines: lines.append(r); break
            # 중복 제거 후 최소 2개 보장
            seen=[];
            for l in lines:
                if l and l not in seen: seen.append(l)
            while len(seen)<2:
                seen.append(f"({c['name']}) …그 일과 나는 무관하오.")
            per["example_lines"]=seen[:3]
    return s

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/[0-9]*.json"
    n=0
    for p in sorted(glob.glob(arg)):
        s=json.load(open(p,encoding="utf-8"))
        before=json.dumps(s,ensure_ascii=False)
        enrich_cast(s)
        if json.dumps(s,ensure_ascii=False)!=before:
            json.dump(s,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
            n+=1; print("보강:",p.split("/")[-1])
    print(f"\n{n}편 에이전트 그라운딩 보강 완료")
