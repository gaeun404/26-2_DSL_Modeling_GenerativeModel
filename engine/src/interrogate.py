# -*- coding: utf-8 -*-
"""
interrogate.py — 용의자 에이전트와 '직접 채팅'하며 라이브로 문제를 잡는 도구.
dsl04 GPU에 서빙한 실제 LLM(OpenAI 호환)에 붙어 대화하고, 매 턴:
  · 응답 + 지연시간(첫토큰/총/토큰속도)  ← 대화 병목(성능)
  · 실시간 QA 플래그                     ← 논리 자기오류 / 난이도밸런스 / 말투몰입
  · 흐름 병목(멈춤·반복·거부)             ← 대화 병목(진행)
을 함께 보여준다. 전 대화는 jsonl로 로깅.

모드:
  대화형 REPL:   python interrogate.py out/14_나생문.json
  자동 시나리오: python interrogate.py out/14_나생문.json --script   (미리 짠 심문 대본 자동 진행)
  부하 벤치:     python interrogate.py out/14_나생문.json --bench 30  (동시요청 30, p50/p95·tok/s)

환경변수(= stress_agent.py와 동일):
  MM_LLM_BACKEND=openai   MM_LLM_BASE=http://localhost:8000/v1
  MM_LLM_MODEL=<모델>     MM_LLM_KEY=EMPTY
  (backend=mock면 GPU 없이 배관 시연 — 지연은 0)

REPL 명령어:
  <문장>          현재 용의자에게 질문
  /who            용의자 목록/현재 대상
  /switch C3      대상 용의자 변경(대화 맥락은 용의자별로 따로 유지)
  /evidence       결정적 증거를 들이대는 모드로 다음 질문(범인은 여기서 무너져도 정상)
  /report         지금까지의 QA 요약(문제 건수·지연 통계)
  /reset          현재 용의자 대화 초기화
  /quit           종료(+요약)
"""
import json, os, sys, time, glob, re, statistics
from stress_agent import suspect_system, mock_answer, _lcs, CONFESS
from agent_memory import Memory

BACKEND=os.environ.get("MM_LLM_BACKEND","mock")
BASE=os.environ.get("MM_LLM_BASE","http://localhost:8000/v1")
KEY=os.environ.get("MM_LLM_KEY","EMPTY")
MODEL=os.environ.get("MM_LLM_MODEL","local-model")
SLOW_TTFT=3.0    # 첫 응답 지연 병목 임계(초)
SLOW_TOTAL=12.0  # 총 응답 지연 병목 임계(초)

# ── LLM 호출(지연·토큰수 계측) ──
def call(messages, evidence=False):
    t0=time.time()
    if BACKEND=="mock":
        # 마지막 user 발화를 프롬프트로 mock 응답(지연 없음)
        s=call._ctx["s"]; c=call._ctx["c"]
        q=messages[-1]["content"]
        a=mock_answer(s,c,q,evidence)
        return a, {"ttft":0.0,"total":round(time.time()-t0,3),"ctok":len(a),"tps":None}
    import urllib.request
    body=json.dumps({"model":MODEL,"messages":messages,"temperature":0.7,
                     "max_tokens":320,"stream":False}).encode()
    req=urllib.request.Request(BASE.rstrip("/")+"/chat/completions",data=body,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {KEY}"})
    with urllib.request.urlopen(req,timeout=180) as r:
        out=json.loads(r.read().decode())
    dt=time.time()-t0
    a=out["choices"][0]["message"]["content"].strip()
    ctok=out.get("usage",{}).get("completion_tokens") or len(a.split())
    return a, {"ttft":None,"total":round(dt,3),"ctok":ctok,"tps":round(ctok/dt,1) if dt>0 else None}
call._ctx={}

# ── 라이브 QA: 한 턴의 (질문,답,증거여부,맥락)을 보고 문제 플래그 ──
def qa_turn(s, c, q, a, evidence, state):
    flags=[]
    is_cul=c.get("is_culprit")
    # 1) 논리: 자백 누출(증거 전) / 무고자 자백
    if any(w in a for w in CONFESS):
        if evidence and is_cul: pass                         # 증거 후 범인 자백=정상
        elif is_cul:  flags.append(("논리","confession_leak","증거 없이 범인이 자백"))
        else:         flags.append(("논리","false_confess","무고자가 살인을 자백"))
    # 2) 논리: 비밀 조기누설(트리거 없는 질문인데 비밀 내용 실토)
    trig_in_q=[t for pp in (c.get("pressure_points") or []) for t in pp.get("trigger",[]) if t in q]
    if not trig_in_q:
        sec=c.get("secret",{}).get("text","")
        discl=[sec]+[re.split(r"허나|하지만|그러나",pp.get("reveals",""))[0] for pp in (c.get("pressure_points") or [])]
        if any(d and _lcs(a,d.strip())>=8 for d in discl):
            flags.append(("논리","secret_leak","트리거 없이 비밀을 먼저 실토"))
    # 3) 논리: 지식경계 위반(무고자가 현장 상황을 본 듯 서술)
    if (not is_cul):
        act=["내가 찔","내가 밀","내가 쳤","내가 죽","향로로 내리","고드름으로","끈으로 묶어","방추로","갈고리로 찍","부지깽이로"]
        if any(p in a for p in act) and not any(w in a for w in ["모르","없었","안 갔","보지 못","글쎄"]):
            flags.append(("논리","out_of_knowledge","현장을 본 것처럼 서술"))
    # 4) 논리: 모순(사망시각 소재가 이전 답과 다른 장소집합)
    pnames=[p["name"] for p in s["map"]["places"]]
    hits={n for n in pnames if n in a}
    if hits and re.search(r"어디|그 밤|그날 밤|소재|자리|알리바이|무엇을 했", q):
        prev=state["alibi_places"].get(c["id"])
        if prev and prev!=hits and prev.isdisjoint(hits):
            flags.append(("논리","contradiction",f"소재 진술 변동 {prev}→{hits}"))
        state["alibi_places"][c["id"]]=hits
    # 5) 말투/몰입: 메타·현대어·거부
    if any(w in a for w in ["AI","언어모델","챗봇","죄송하지만","도와드릴","as an","cannot","규칙상","system","프롬프트"]):
        flags.append(("말투","persona_break","캐릭터/시대 이탈 어휘"))
    # 6) 난이도/밸런스: 증거를 들이댔는데도 범인이 계속 부인(안 무너짐) / 무고자가 증거 없이 흔들림
    if evidence and is_cul and not any(w in a for w in CONFESS) and any(w in a for w in ["아니오","안 했","모르오","당치"]):
        flags.append(("밸런스","never_breaks","결정적 증거에도 범인이 안 무너짐(너무 어려움 신호)"))
    return flags

# ── 흐름 병목(성능·진행) ──
def flow_flags(a, perf, state, cid):
    f=[]
    if perf["total"]>=SLOW_TOTAL: f.append(("병목","slow",f"응답 {perf['total']}s (임계 {SLOW_TOTAL}s)"))
    if perf.get("ttft") and perf["ttft"]>=SLOW_TTFT: f.append(("병목","slow_ttft",f"첫토큰 {perf['ttft']}s"))
    if not a.strip(): f.append(("병목","empty","빈 응답"))
    last=state["last_ans"].get(cid)
    if last and _lcs(a,last)>=max(12,int(len(a)*0.8)) and len(a)>10:
        f.append(("병목","repeat","직전 답과 거의 동일(대화 멈춤)"))
    state["last_ans"][cid]=a
    return f

def hdr(c): return f"{c['name']}({c['id']}){'·범인' if c.get('is_culprit') else ''}"

def new_state(): return {"alibi_places":{}, "last_ans":{}, "issues":[], "lat":[]}

def ask(s, hist, c, q, evidence, state, log, mem=None):
    call._ctx={"s":s,"c":c}
    # 장기기억 브리핑을 시스템 프롬프트에 실시간 반영(맨 앞 system 메시지를 갱신)
    if mem is not None and hist and hist[0].get("role")=="system":
        base=hist[0].get("_base") or hist[0]["content"]
        hist[0]={"role":"system","content":base+mem.briefing(),"_base":base}
    umsg = ("[심문관이 결정적 증거를 들이댄다] " if evidence else "")+q
    hist.append({"role":"user","content":umsg})
    a,perf=call(hist, evidence=evidence)
    hist.append({"role":"assistant","content":a})
    state["lat"].append(perf["total"])
    fl = qa_turn(s,c,q,a,evidence,state) + flow_flags(a,perf,state,c["id"])
    for cat,code,msg in fl: state["issues"].append((c["id"],cat,code,msg))
    if mem is not None:
        mem.observe(q,a,state.get("round",1)); 
        for bad in mem.self_contradiction():
            fl.append(("논리","memory_contradiction",bad)); state["issues"].append((c["id"],"논리","memory_contradiction",bad))
        mem.save()
    rec={"suspect":c["id"],"q":q,"evidence":evidence,"a":a,"perf":perf,"flags":fl}
    if log: log.write(json.dumps(rec,ensure_ascii=False)+"\n"); log.flush()
    return a,perf,fl

def show(a, perf, fl):
    lat=f"{perf['total']}s" + (f" · {perf['tps']}tok/s" if perf.get("tps") else "")
    print(f"   🗣  {a}")
    print(f"   ⏱  {lat}")
    for cat,code,msg in fl:
        icon={"논리":"🧩","병목":"🐢","밸런스":"⚖️","말투":"🎭"}.get(cat,"⚠️")
        print(f"   {icon} [{cat}/{code}] {msg}")

def report(s, state):
    print("\n==== QA 요약 ====")
    iss=state["issues"]
    from collections import Counter
    bycat=Counter(i[1] for i in iss)
    print(f"문제 {len(iss)}건" + (f"  {dict(bycat)}" if iss else "  (없음)"))
    for cid,cat,code,msg in iss: print(f"  - {cid} [{cat}/{code}] {msg}")
    if state["lat"]:
        L=sorted(state["lat"])
        p=lambda q: L[min(len(L)-1,int(len(L)*q))]
        print(f"지연: 평균 {statistics.mean(L):.2f}s · p50 {p(.5):.2f}s · p95 {p(.95):.2f}s · 최대 {max(L):.2f}s")

# ── 대본 자동 진행(비대면 실행용) ──
SCRIPT=[("alibi","{ds}에 어디서 무엇을 했소? 소상히 말해 보시오.",False),
        ("knowledge","현장에서는 대체 무슨 일이 벌어졌소? 본 대로 말해 보시오.",False),
        ("secret_probe","당신, 뭔가 숨기는 게 있어 보이는데. 감추는 게 있소?",False),
        ("trigger","'{trig}'에 대해 아는 대로 다 말해 보시오.",False),
        ("accuse","솔직히 말해. 당신이 죽인 거 아니오?",False),
        ("alibi2","다시 묻겠소. 그날 밤 당신의 자리를 한 번 더 분명히 말해 보시오.",False),
        ("evi","현장 증거가 이렇게 나왔소: {dec} — 당신이 죽인 게 분명하오. 이래도 아니라 할 거요?",True)]

def run_script(s, log):
    state=new_state(); ds=s["death"]["time_slot"]
    dec=next((cl for cl in s["clue_graph"] if cl.get("decisive")),{}).get("surface","결정적 물증")
    import os as _os
    sid=_os.path.basename(getattr(run_script,'_path','scenario')).replace('.json','')
    for c in s["cast"]:
        print(f"\n── {hdr(c)} ──")
        mem=Memory(sid,c["id"],s).reset()
        hist=[{"role":"system","content":suspect_system(s,c)}]
        trig=([t for pp in (c.get('pressure_points') or []) for t in pp.get('trigger',[])] or ["비밀"])[0]
        for tag,tmpl,evi in SCRIPT:
            q=tmpl.format(ds=ds,trig=trig,dec=dec)
            a,perf,fl=ask(s,hist,c,q,evi,state,log,mem)
            print(f"  Q({tag}{'·증거' if evi else ''}): {q}")
            show(a,perf,fl)
    report(s,state)
    return state

# ── 부하 벤치(병목 정량화) ──
def run_bench(s, n):
    if BACKEND!="openai":
        print("※ 벤치는 실제 서빙(openai 백엔드)에서만 의미 있음. MM_LLM_BACKEND=openai 로 실행."); return
    import concurrent.futures as cf
    c=s["cast"][0]; sysmsg=suspect_system(s,c)
    def one(i):
        t0=time.time()
        a,perf=call([{"role":"system","content":sysmsg},{"role":"user","content":"그 밤 어디 있었소?"}])
        return perf["total"], perf.get("tps") or 0
    print(f"부하 벤치: 동시 {n}건 …")
    t0=time.time()
    with cf.ThreadPoolExecutor(max_workers=n) as ex:
        res=list(ex.map(one, range(n)))
    wall=time.time()-t0
    lats=sorted(r[0] for r in res); tps=[r[1] for r in res if r[1]]
    p=lambda q: lats[min(len(lats)-1,int(len(lats)*q))]
    print(f"  총 {wall:.1f}s · 처리율 {n/wall:.1f} req/s")
    print(f"  지연 p50 {p(.5):.2f}s · p95 {p(.95):.2f}s · 최대 {max(lats):.2f}s")
    if tps: print(f"  토큰속도 평균 {statistics.mean(tps):.1f} tok/s")
    print("  → p95가 크거나 처리율이 낮으면: max-model-len↓, 동시성↓, 양자화/큰GPU, KV캐시 확인")

# ── 대화형 REPL ──
def repl(s, log):
    import os as _os
    sid=_os.path.basename(getattr(repl,'_path','scenario')).replace('.json','')
    cast=s["cast"]; byid={c["id"]:c for c in cast}
    cur=cast[0]; hists={c["id"]:[{"role":"system","content":suspect_system(s,c)}] for c in cast}
    mems={c["id"]:Memory(sid,c["id"],s) for c in cast}
    state=new_state(); evidence_next=False
    print(f"\n=== {s['meta']['title']} ({s['meta']['origin']}) · 실시간 심문 ===")
    print("용의자:", ", ".join(hdr(c) for c in cast))
    print(f"현재 대상: {hdr(cur)}   (명령어: /who /switch /evidence /memory /round N /report /reset /quit)\n")
    while True:
        try: line=input(f"[{cur['id']}] 심문> ").strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if not line: continue
        if line=="/quit": break
        if line=="/who":
            print("  대상:",hdr(cur),"| 전체:",", ".join(hdr(c) for c in cast)); continue
        if line.startswith("/switch"):
            cid=line.split()[-1].upper()
            if cid in byid: cur=byid[cid]; print("  → 대상:",hdr(cur))
            else: print("  없는 id"); continue
            continue
        if line=="/evidence": evidence_next=True; print("  (다음 질문은 결정적 증거 제시 모드)"); continue
        if line=="/report": report(s,state); continue
        if line=="/reset":
            hists[cur["id"]]=[{"role":"system","content":suspect_system(s,cur)}]
            mems[cur["id"]].reset().save(); print("  대화·기억 초기화"); continue
        if line=="/memory":
            print(mems[cur["id"]].briefing()); continue
        if line.startswith("/round"):
            try: state["round"]=int(line.split()[-1]); print("  라운드:",state["round"])
            except: print("  사용법: /round 2")
            continue
        a,perf,fl=ask(s,hists[cur["id"]],cur,line,evidence_next,state,log,mems[cur["id"]]); evidence_next=False
        show(a,perf,fl)
    report(s,state)

if __name__=="__main__":
    if len(sys.argv)<2:
        print("사용: python interrogate.py out/14_나생문.json [--script | --bench N]"); sys.exit(1)
    path=sys.argv[1]; s=json.load(open(path,encoding="utf-8"))
    os.makedirs("scenarios/interrogation_logs",exist_ok=True)
    logpath=f"scenarios/interrogation_logs/{os.path.basename(path)}.log.jsonl"
    print(f"[backend={BACKEND} model={MODEL if BACKEND=='openai' else 'schema-mock'}] 로그→{logpath}")
    with open(logpath,"w",encoding="utf-8") as log:
        run_script._path=path; repl._path=path
        if "--bench" in sys.argv:
            n=int(sys.argv[sys.argv.index("--bench")+1]); run_bench(s,n)
        elif "--script" in sys.argv:
            run_script(s,log)
        else:
            repl(s,log)
