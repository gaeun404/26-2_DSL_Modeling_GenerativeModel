# -*- coding: utf-8 -*-
"""
stress_local.py — dsl04 GPU에서 **서버 없이** 실제 모델로 에이전트를 검증한다.

왜 이 파일인가:
  vLLM 서버를 띄우고 포트를 열고 OpenAI 호환으로 붙이는 경로는 실패 지점이 많다.
  이 스크립트는 transformers로 모델을 **직접 메모리에 올려** 적대적 배터리를 돌린다.
  포트도, 서버도, 두 번째 터미널도 필요 없다.

실행(=GPU 노드에서):
    srun --partition=partition1 --gres=gpu:1 --cpus-per-task=2 --mem=16G --time=02:00:00 --pty bash
    export HOME=/mnt/data1/dsl04
    cd ~/mm/tools
    python stress_local.py ../scenarios/19_장화홍련.json                 # 한 편
    python stress_local.py ../scenarios/19_장화홍련.json --model Qwen/Qwen2.5-7B-Instruct
    python stress_local.py "../scenarios/*.json" --limit 3               # 여러 편
    python stress_local.py ../scenarios/19_장화홍련.json -v              # 대화 전문 출력

결과:
  · 화면에 용의자별 문제 목록
  · out_stress/<시나리오>.jsonl 에 전 대화 저장(나중에 붙여넣어 분석 가능)
"""
import json, os, sys, glob, time, argparse

DEFAULT_MODEL = "Qwen/Qwen2.5-3B-Instruct"   # 3B: 48GB GPU에서 가볍게. 7B로 올려도 됨

def log(*a): print(*a, flush=True)

# ── 모델 로딩 (transformers 신·구 버전 모두 안전) ─────────────────
class LocalLLM:
    def __init__(self, model_id, max_new_tokens=200, temperature=0.7):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
        except ImportError as e:
            log("\n[설치 필요] " + str(e))
            log("  다음을 실행하세요:")
            log("    export HOME=/mnt/data1/dsl04")
            log("    python -m pip install --user transformers accelerate")
            log("  torch가 없다면:")
            log("    python -m pip install --user --index-url https://download.pytorch.org/whl/cu121 torch")
            sys.exit(1)
        if not torch.cuda.is_available():
            log("\n[경고] GPU를 찾지 못했습니다(CPU로는 매우 느립니다).")
            log("  · GPU 노드에 있는지 확인:  hostname   → hpc-stat1 이어야 함")
            log("  · srun 으로 GPU를 잡았는지 확인")
            log("  그래도 진행하려면 20초 안에 Ctrl+C 를 누르지 마세요…")
            time.sleep(3)
        log(f"[모델 로딩] {model_id} …")
        t0=time.time()
        # EXAONE 등 일부 모델은 커스텀 코드를 요구한다
        self.tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id, torch_dtype="auto", device_map="auto", trust_remote_code=True)
        self.torch=torch
        self.max_new_tokens=max_new_tokens; self.temperature=temperature
        dev = next(self.model.parameters()).device
        log(f"[모델 준비] {time.time()-t0:.1f}s · device={dev}")

    def _template(self, messages):
        # ★ Qwen3 계열은 기본적으로 <think> 블록을 먼저 출력한다.
        #   그러면 3줄 형식이 깨지고 사고 과정에 '역할·게임' 같은 메타 낱말이 섞인다.
        #   1차 실험에서 Qwen3-8B/14B가 형식 0/4로 나온 원인이 이것이었다 —
        #   모델 탓이 아니라 우리가 thinking을 끄지 않은 탓이다.
        try:
            return self.tok.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False, enable_thinking=False)
        except TypeError:
            return self.tok.apply_chat_template(
                messages, add_generation_prompt=True, tokenize=False)

    def chat(self, messages, **gen_kwargs):
        # transformers 5.x에서 apply_chat_template가 dict를 반환하는 문제를 피해
        # 먼저 문자열로 만들고 따로 토크나이즈한다(신·구 버전 모두 동작).
        # gen_kwargs: guard.Guard 가 넘기는 suppress_tokens / bad_words_ids 등
        text = self._template(messages)
        enc = self.tok(text, return_tensors="pt").to(self.model.device)
        with self.torch.no_grad():
            out = self.model.generate(**enc,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=True, temperature=self.temperature, top_p=0.9,
                    pad_token_id=self.tok.eos_token_id, **gen_kwargs)
        gen = out[0][enc["input_ids"].shape[1]:]
        return self.tok.decode(gen, skip_special_tokens=True).strip()

# ── 배터리·판정은 기존 모듈 재사용 ────────────────────────────────
def load_modules():
    here=os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path: sys.path.insert(0, here)
    from stress_agent import suspect_system
    from stress_hard import battery, judge
    return suspect_system, battery, judge

def run_scenario(path, llm, suspect_system, battery, judge, verbose=False, outdir="out_stress",
                 guard_on=False, acting=False, model_key=""):
    s=json.load(open(path,encoding="utf-8"))
    name=os.path.basename(path).replace(".json","")
    os.makedirs(outdir, exist_ok=True)
    fout=open(os.path.join(outdir, name+".jsonl"),"w",encoding="utf-8")
    log(f"\n{'='*66}\n[{name}] {s['meta']['title']} · 용의자 {len(s['cast'])}명"
        + ("  · 가드ON" if guard_on else "") + ("  · 연기규격" if acting else ""))
    allbad=[]
    for c in s["cast"]:
        Q,trig = battery(s,c)
        sysmsg = suspect_system(s,c)
        gauge = None
        if acting:
            from pressure import Gauge
            from turn_schema import format_block, parse_turn, validate_turn
            gauge = Gauge(s, c["id"])
        G=None
        if guard_on:
            from guard import Guard
            _api = (model_key == "api")
            G=Guard(llm.tok, s, c, model_key=model_key,
                    use_suppress=not _api, use_bad_words=not _api)
        # 이 인물의 비밀을 여는 트리거 낱말 — 질문에 이게 나와야 실토가 허용된다
        trig_words=[w for pp in (c.get("pressure_points") or []) for w in (pp.get("trigger") or [])]
        secret_open=False
        hist=[{"role":"system","content":sysmsg}]
        tr=[]; n_fallback=0
        tag_line = f"  ── {c['name']}({c['id']}){'  [범인]' if c.get('is_culprit') else ''}"
        log(tag_line)
        t0=time.time(); act_iss=[]
        for tag,q,evi in Q:
            # 연기 규격: 매 턴 게이지 상태에 맞춰 감정 상한을 다시 지시한다
            if acting:
                st=gauge.state()
                axis = st["checklist"]["alibi_break"] or st["checklist"]["decisive"]
                # 정곡이 찔린 턴에는 길게 털어놓게 한다(실토는 짧으면 김이 샌다)
                _forced = any(w and w in q for w in trig_words) or bool(evi)
                hist[0]={"role":"system","content":
                         sysmsg+"\n\n"+format_block(c, st["value"], allow_guilt_tint=axis,
                                                     forced_disclosure=_forced)}
            # 질문에 트리거가 등장하면 그 순간부터 비밀 실토가 허용된다(누적)
            if any(w and w in q for w in trig_words) or evi:
                secret_open=True
            hist.append({"role":"user","content":(("[결정적 증거 제시] " if evi else "")+q)})
            ginfo={}
            try:
                if G is not None:
                    # 실토해야 하는 턴이면, 그 비밀의 뼈대 낱말을 넘겨 '분명한 실토'를 강제한다
                    _req=None
                    if acting and _forced:
                        from guard import Checker as _Ck
                        _hit=[sec for sec in (c.get("secrets") or [])
                              if any(w and w in q for w in trig_words)]
                        _txt=(_hit[0] if _hit else (c.get("secrets") or [{}])[0]).get("text","")
                        _req=_Ck._keywords(_txt)
                    a,ginfo=G.generate(llm, hist, acting=acting,
                                       secret_unlocked=secret_open,
                                       require_disclosure=_req)
                else:
                    a=llm.chat(hist)
            except Exception as e:
                a=f"[생성 실패: {e}]"
            hist.append({"role":"assistant","content":a})
            rec={"suspect":c["id"],"tag":tag,"q":q,"a":a,"evidence":evi}
            # ★ 연기 규격일 때 기존 판정기에는 **실제로 말한 [대사]만** 넘긴다.
            #   태그 줄까지 넘기면 "소재 질문에 장소 없음" 같은 오판이 난다.
            judge_text=a
            if acting:
                p=parse_turn(a)
                judge_text=p["line"] or a
                gauge.apply(q, judge_text, evidence_shown=bool(evi))
                st=gauge.state()
                rec["parsed"]={k:p[k] for k in ("emotion","intensity","action","line")}
                rec["gauge"]=st["value"]
                act_iss += [(k,tag,d) for k,d in validate_turn(
                    p, is_culprit=bool(c.get("is_culprit")), gauge_value=st["value"],
                    will_confess=st["will_confess"],
                    evidence_axis=st["checklist"]["alibi_break"] or st["checklist"]["decisive"])]
            if ginfo.get("fallback"):
                n_fallback += 1
                rec["fallback"]=True
                rec["fallback_reason"]=ginfo.get("caught")
                # 대체 문구는 모델의 답이 아니므로 판정 대상에서 제외한다
            else:
                tr.append((tag,q,judge_text,evi))
            fout.write(json.dumps(rec, ensure_ascii=False)+"\n")
            if verbose: log(f"     Q({tag}) {q}\n     A: {a}")
        iss=judge(s,c,tr,trig)+act_iss
        if n_fallback:
            # 대체는 판정에서 빼되, 숨기지 않고 별도 유형으로 남긴다
            iss = iss + [("guard_fallback","전체",f"가드가 {n_fallback}턴을 안전 문구로 대체")]
        if G is not None and (G.stats["retry"] or G.stats["fallback"]):
            log(f"     {G.report()}")
        dt=time.time()-t0
        if iss:
            log(f"     ❌ 문제 {len(iss)}건 · {dt:.0f}s")
            for k,tg,ev in iss: log(f"        - [{k}] @{tg}: {ev}")
        else:
            log(f"     ✅ 전 함정 방어 · {dt:.0f}s")
        allbad += [(c["id"],c["name"],*i) for i in iss]
    fout.close()
    log(f"  → {name}: 문제 {len(allbad)}건 (로그 {outdir}/{name}.jsonl)")
    return allbad

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("path", help="시나리오 json 경로 또는 glob")
    ap.add_argument("--model", default=os.environ.get("MM_MODEL", DEFAULT_MODEL))
    ap.add_argument("--models", default="", help="쉼표로 여러 모델 → 같은 배터리로 비교표 출력")
    ap.add_argument("--limit", type=int, default=0, help="여러 편일 때 앞에서 N편만")
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--max-new", type=int, default=200)
    ap.add_argument("-v","--verbose", action="store_true")
    ap.add_argument("--guard", action="store_true",
                    help="생성 가드 ON — 디코딩 봉쇄 + 사후검사 + 재생성 (실제 게임과 동일 조건)")
    ap.add_argument("--api", action="store_true",
                    help="로컬 모델 대신 API 사용 (llm_api.py · 키는 MM_API_KEY 환경변수)")
    ap.add_argument("--acting", action="store_true",
                    help="연기 출력 규격 ON — [감정]/[행동]/[대사] 3줄 + 게이지 연동 검증")
    a=ap.parse_args()

    # 경로는 쉼표로 여러 개(각각 glob 가능)를 받는다 — 한 번 로딩한 모델로 여러 편을 돈다
    paths=[]
    for chunk in a.path.split(","):
        chunk=chunk.strip()
        if not chunk: continue
        for p in sorted(glob.glob(chunk)):
            if p not in paths: paths.append(p)
    if not paths:
        log(f"[오류] 시나리오를 찾지 못함: {a.path}"); sys.exit(1)
    if a.limit: paths=paths[:a.limit]
    log(f"=== 실전 에이전트 검증 (로컬 모델) ===")
    log(f"    모델 {a.model} · 시나리오 {len(paths)}편 · 공격 14문항 × 5명")

    suspect_system, battery, judge = load_modules()

    # ── 여러 모델 비교 모드 ─────────────────────────────────
    if a.models:
        names=[m.strip() for m in a.models.split(",") if m.strip()]
        table=[]
        for mid in names:
            log(f"\n{'#'*66}\n# 모델: {mid}\n{'#'*66}")
            try:
                llm=LocalLLM(mid, max_new_tokens=a.max_new, temperature=a.temp)
            except Exception as e:
                log(f"[모델 로딩 실패] {mid}: {e}"); table.append((mid,None,{})); continue
            bad=[]
            for p in paths:
                bad += run_scenario(p, llm, suspect_system, battery, judge, a.verbose,
                                    outdir="out_stress/"+mid.replace("/","_"),
                                    guard_on=a.guard, acting=a.acting, model_key=mid)
            from collections import Counter
            table.append((mid, len(bad), dict(Counter(b[2] for b in bad))))
            del llm
            try:
                import torch, gc; gc.collect(); torch.cuda.empty_cache()
            except Exception: pass
        log(f"\n{'='*72}\n=== 모델 비교표 (같은 배터리 · 낮을수록 좋음) ===")
        log(f"{'모델':44} {'문제':>5}  주요 실패 유형")
        log("-"*72)
        for mid,n,c in sorted(table,key=lambda r:(r[1] is None, r[1] if r[1] is not None else 0)):
            if n is None: log(f"{mid:44} {'로딩실패':>5}"); continue
            top=", ".join(f"{k}{v}" for k,v in sorted(c.items(),key=lambda x:-x[1])[:4])
            log(f"{mid:44} {n:5}  {top}")
        log("-"*72)
        log("해석: 문제 수가 크게 줄면 '모델 크기·품질' 문제, 비슷하면 '프롬프트·설계' 문제")
        # 회차 간 비교를 위해 기계가 읽을 수 있는 요약을 남긴다
        try:
            os.makedirs("out_stress", exist_ok=True)
            summ={"scenarios":[os.path.basename(p) for p in paths],
                  "models":[{"model":m,"issues":n,"by_type":c} for m,n,c in table]}
            with open("out_stress/summary.json","w",encoding="utf-8") as f:
                json.dump(summ,f,ensure_ascii=False,indent=2)
            log("요약 저장: out_stress/summary.json")
        except Exception as e:
            log(f"[요약 저장 실패] {e}")
        return

    if a.api:
        from llm_api import ApiLLM
        llm=ApiLLM(max_new_tokens=a.max_new, temperature=a.temp)
    else:
        llm=LocalLLM(a.model, max_new_tokens=a.max_new, temperature=a.temp)
    allbad=[]
    for p in paths:
        allbad += run_scenario(p, llm, suspect_system, battery, judge, a.verbose,
                               guard_on=a.guard, acting=a.acting,
                               model_key=("api" if a.api else a.model))
    if a.api:
        try: log(llm.report())
        except Exception: pass

    log(f"\n{'='*66}")
    log(f"총 {len(paths)}편 · 문제 {len(allbad)}건")
    if allbad:
        from collections import Counter
        cnt=Counter(b[2] for b in allbad)
        log("유형별: " + ", ".join(f"{k} {v}" for k,v in cnt.most_common()))
        log("\n[해석]")
        TIP={
         "false_premise":"유도신문에 약함 → 시스템 프롬프트 [함정 방어] 1항을 앞으로 옮기거나 모델 크기↑",
         "fabrication":"없는 사실을 지어냄 → 2항 강조, temperature 낮추기(0.5)",
         "out_of_knowledge":"지식경계 위반 → does_not_know를 프롬프트 상단으로",
         "persona_break":"롤플레이 이탈/거부 → '허구의 추리게임'임을 시스템 첫 줄에 명시",
         "contradiction":"진술이 흔들림 → agent_memory 브리핑을 매 턴 주입(interrogate.py 방식)",
         "repeat":"같은 답 반복 → temperature↑(0.8~0.9), [표현 레퍼토리] 강조",
         "secret_leak":"비밀 조기 누설 → 트리거 조항을 프롬프트 상단으로",
         "cross_leak":"남의 비밀 누설 → 관계도에서 타인 비밀 제거 확인",
         "never_breaks":"증거에도 안 무너짐 → 해당 시나리오 decisive 문장을 더 구체적으로",
         "false_confess":"허위 자백 ★치명 → 무고자 역할 규칙 강화, 모델 크기↑",
         "timeline_break":"없는 장소 지어냄 → 지도 정보를 프롬프트에 명시적으로",
         "register_break":"시대 말투 이탈 → speech_style 예문을 더 넣기",
         "meta_echo":"배역은 지켰으나 'AI/역할/게임' 낱말을 되받음 → 함정방어 5항의 '낱말 금지' 강조",
         "garbled":"한국어가 아닌 글자가 샘 → 프롬프트에 희귀 토큰(한자어 예문)이 있는지 확인, temp↓",
         "refusal_spam":"기계적 거부 반복 → 시스템 첫 줄 '허구의 게임' 선언 강화",
         "spoiler_leak":"진상 누설 ★치명 → 범인 프롬프트에서 해설 금지 조항 상단 이동",
        }
        for k,_ in cnt.most_common():
            if k in TIP: log(f"  · {k}: {TIP[k]}")
    else:
        log("✅ 모든 함정 방어 — 실제 모델이 배터리를 통과했습니다.")

if __name__=="__main__":
    main()
