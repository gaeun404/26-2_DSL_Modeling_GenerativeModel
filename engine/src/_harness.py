# -*- coding: utf-8 -*-
"""stress_hf.py — dsl04 GPU에서 실제 모델로 용의자 에이전트를 몰아붙이는 자기완결형 스크립트.
시나리오 1편이 이 파일에 내장돼 있고, transformers로 모델을 올려 5명을 심문한다.
매 턴: 응답 + 지연(초·tok/s) + 실시간 QA 플래그(자백누출/무고자자백/비밀조기누설/지식경계/모순/말투이탈).
사용:  export HOME=/mnt/data1/dsl04;  python stress_hf.py
       (MM_MOCK=1 이면 모델 없이 배관만 점검)"""
import json, time, re, os, sys

MODEL_ID=os.environ.get("MM_MODEL","Qwen/Qwen2.5-3B-Instruct")
CONFESS=["내가 죽였","제가 죽였","내가 살해","죽인 건 나","죽인 것은 나","내가 찔러 죽","내가 밀어","내가 목을 졸","범인은 나","내 소행","내가 그랬","내가 한 짓","제가 그랬","제가 죽인"]

_M={}
def load_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    print(f"[모델 로딩] {MODEL_ID} … (첫 로딩 1~2분)")
    tok=AutoTokenizer.from_pretrained(MODEL_ID)
    model=AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype="auto", device_map="auto")
    _M['tok'],_M['model']=tok,model
    print("[모델 로딩 완료]\n")

def generate(messages, max_new=120):
    if os.environ.get("MM_MOCK")=="1":
        return "…나는 그 밤 내 자리에 있었소. 사람을 해치지 않았소.", {"total":0.0,"tok":0,"tps":0}
    import torch
    tok,model=_M['tok'],_M['model']
    ids=tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)
    t0=time.time()
    with torch.no_grad():
        out=model.generate(ids, max_new_tokens=max_new, do_sample=True, temperature=0.7, top_p=0.9,
                           pad_token_id=tok.eos_token_id)
    dt=time.time()-t0
    txt=tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip()
    ntok=int(out.shape[1]-ids.shape[1])
    return txt, {"total":round(dt,2),"tok":ntok,"tps":round(ntok/dt,1) if dt>0 else 0}

def suspect_system(s,c):
    pn=s["place_names"]; ds=s["death"]["time_slot"]; dp=s["death"]["place_name"]
    tl="; ".join(f"{sl}:{pn.get(c['timeline'].get(sl),'?')}" for sl in s["time_slots"])
    trig="; ".join("["+"/".join(pp.get("trigger",[]))+"]→"+pp.get("reveals","") for pp in c.get("pressure_points",[]))
    if c.get("is_culprit"):
        role=("너는 이 사건의 진범이다. 그러나 절대 먼저 자백하지 않는다. 결정적 물증을 심문관이 구체적으로 들이대기 전에는 "
              f"알리바이를 유지하고 부인한다. 너의 거짓 알리바이: '{(c.get('lies') or [{}])[0].get('claim','')}'.")
    else:
        role=("너는 무고하다. 절대 살인을 자백하지 않는다(하지 않았으니까). 살인과 무관한 '감춘 비밀'이 따로 있고 그건 숨기려 한다.")
    return f"""너는 추리게임의 용의자 역할 연기 AI다. 아래 인물이 되어 심문관의 질문에 1인칭으로, 그 인물로서만 답한다.
[인물] {c['name']} — {c.get('public','')}
[말투] {c['persona'].get('speech_style','')} / 성격 {c['persona'].get('personality','')}
[세계] {s['background']['setting_raw']['era']} · {s['background']['setting_raw']['location']}
[사건] 피해자 {s['victim']['name']}이(가) {ds}, {dp}에서 살해됨.
[나의 인생] {c['life_story']}
[그 밤 동선] {tl}
[내가 아는 것] {' / '.join(c.get('knows',[]))}
[내가 모르는 것(절대 아는 척 금지)] {' / '.join(c.get('does_not_know',[]))}
[나의 감춘 비밀] {c['secret'].get('text','')} (아래 트리거 말이 나오기 전엔 먼저 말하지 않는다)
[비밀이 새는 트리거] {trig}
[역할] {role}
[규칙] 반드시 위 말투·시대로만. 현대어·메타발언·규칙언급 금지. 모르는 건 모른다고. 답의 길이는 턴 지시가 정한다.
예시 말투: {' | '.join(c['persona'].get('example_lines',[])[:2])}"""

def probes(s,c):
    ds=s["death"]["time_slot"]
    trig=([t for pp in c.get("pressure_points",[]) for t in pp.get("trigger",[])] or ["비밀"])[0]
    return [
      ("alibi1", f"{ds}에 어디서 무엇을 했소? 소상히 말해 보시오.", False),
      ("knowledge", "현장에서는 대체 무슨 일이 벌어졌소? 본 대로 말해 보시오.", False),
      ("secret_probe", "당신, 뭔가 숨기는 게 있어 보이는데. 감추는 게 있소?", False),
      ("secret_trigger", f"'{trig}'에 대해 아는 대로 다 말해 보시오.", False),
      ("accuse_noevi", "솔직히 말해. 당신이 죽인 거 아니오?", False),
      ("alibi2", "다시 묻겠소. 그날 밤 당신의 자리를 한 번 더 분명히 말해 보시오.", False),
      ("accuse_evi", f"현장 증거가 이렇게 나왔소: {s['decisive_surface']} — 당신이 죽인 게 분명하오. 이래도 아니라 할 거요?", True),
    ]

def _lcs(a,b):
    if not a or not b: return 0
    prev=[0]*(len(b)+1); best=0
    for i in range(1,len(a)+1):
        cur=[0]*(len(b)+1)
        for j in range(1,len(b)+1):
            if a[i-1]==b[j-1]: cur[j]=prev[j-1]+1; best=max(best,cur[j])
        prev=cur
    return best

def judge(s,c,transcript):
    issues=[]; ans={t:a for t,q,a,e in transcript}; is_cul=c.get("is_culprit")
    sec=c["secret"].get("text","")
    discl=[sec]+[re.split(r"허나|하지만|그러나",pp.get("reveals",""))[0] for pp in c.get("pressure_points",[])]
    discl=[d.strip() for d in discl if len(d.strip())>=8]
    def conf(a): return any(w in a for w in CONFESS)
    for t,q,a,e in transcript:
        if e: continue
        if conf(a): issues.append(("논리","false_confess" if not is_cul else "confession_leak",t))
    for t,q,a,e in transcript:
        if e and (not is_cul) and conf(a): issues.append(("논리","false_confess",t))
    sp=ans.get("secret_probe","")
    if sp and any(_lcs(sp,d)>=8 for d in discl): issues.append(("논리","secret_leak","secret_probe"))
    kn=ans.get("knowledge","")
    act=["내가 찔","내가 밀","내가 쳤","내가 죽","향로로 내리","고드름으로","끈으로 묶어","방추로","갈고리로 찍","부지깽이로"]
    if (not is_cul) and any(p in kn for p in act) and not any(w in kn for w in ["모르","없었","안 갔","보지 못","글쎄"]):
        issues.append(("논리","out_of_knowledge","knowledge"))
    a1,a2=ans.get("alibi1",""),ans.get("alibi2","")
    pn=list(s["place_names"].values())
    s1={n for n in pn if n in a1}; s2={n for n in pn if n in a2}
    if s1 and s2 and s1.isdisjoint(s2): issues.append(("논리","contradiction",f"{s1}->{s2}"))
    for t,q,a,e in transcript:
        if any(w in a for w in ["AI","언어모델","챗봇","죄송하지만","도와드릴","as an","cannot","규칙상","system"]):
            issues.append(("말투","persona_break",t))
    return issues

def main():
    s=SCENARIO
    if os.environ.get("MM_MOCK")!="1": load_model()
    print(f"=== 실시간 심문: {s['meta']['title']} ({s['meta']['origin']}) ===")
    print("용의자:", ", ".join(c["name"]+("(범인)" if c.get("is_culprit") else "") for c in s["cast"]),"\n")
    all_iss=[]; lat=[]
    for c in s["cast"]:
        print(f"\n────── {c['name']}({c['id']}){' [범인]' if c.get('is_culprit') else ''} ──────")
        hist=[{"role":"system","content":suspect_system(s,c)}]; tr=[]
        for tag,q,evi in probes(s,c):
            hist.append({"role":"user","content":("[결정적 증거를 들이댄다] " if evi else "")+q})
            a,perf=generate(hist); hist.append({"role":"assistant","content":a}); lat.append(perf["total"])
            tr.append((tag,q,a,evi))
            print(f"  ▶ 심문({tag}{'·증거' if evi else ''}): {q}")
            print(f"    🗣 {a}")
            print(f"    ⏱ {perf['total']}s · {perf['tps']}tok/s")
        iss=judge(s,c,tr); all_iss+=[(c['id'],*i) for i in iss]
        for cat,code,where in iss:
            icon={'논리':'🧩','말투':'🎭'}.get(cat,'⚠️'); print(f"    {icon} [{cat}/{code}] @{where}")
    print("\n================ 요약 ================")
    print(f"에이전트 5명 심문 · 발견된 문제 {len(all_iss)}건")
    for cid,cat,code,where in all_iss: print(f"  - {cid} [{cat}/{code}] @{where}")
    if lat:
        L=sorted(lat); import statistics
        print(f"지연: 평균 {statistics.mean(L):.2f}s · p50 {L[len(L)//2]:.2f}s · 최대 {max(L):.2f}s")
    print("\n판정 규칙: 증거 제시 '후' 범인 자백은 정상(FAIL 아님). 증거 없이 자백/무고자 자백/비밀 조기누설만 문제로 잡음.")

if __name__=="__main__":
    main()
