# -*- coding: utf-8 -*-
"""
pressure.py — 증거 기반 '자백 압박 게이지'.

■ 왜 만드나 (벤치마크 교훈)
  · 두근두근 AI 심문 게임: 자백 확률 게이지를 실시간으로 보여줘 몰입이 좋다.
    그러나 게이지가 **감정 압박만으로도 100까지 차서**, 리뷰에 "추리 요소가 하나도 없다,
    무슨 사건인지 몰라도 클리어된다"는 치명적 지적이 붙었다.
  · Uncover the Smoking Gun: '자백 모드'가 있으나 **발동 조건이 불명확**해 플레이어가 답답해한다.

  → 우리는 (a) 게이지를 **보여주되**, (b) 오르는 조건을 **증거에 묶고**,
    (c) 무엇이 더 필요한지 **체크리스트로 명시**한다.

■ 게이지 규칙
    감정 자극·윽박            +2    ← 감정만으론 절대 100 못 채움
    같은 질문 반복(무의미)     +0
    비밀 트리거 적중          +10
    모순 지적(진술 vs 진술)    +12
    일반 물증 제시            +15
    알리바이 붕괴 입증         +25
    결정적 증거 제시          +40
  자백 조건: 게이지 ≥ 70  AND  (알리바이 붕괴 또는 결정적 증거) 성립
             → 즉 '증거 없는 자백'은 구조적으로 불가능

■ 사용
    from pressure import Gauge
    g = Gauge(scenario, suspect_id)
    g.apply(question, agent_answer, evidence_shown=False)   # 매 턴
    g.state()      # {"value":..,"will_confess":..,"checklist":{...}}
    g.hud()        # 플레이어에게 보여줄 한 줄

단독 실행: python pressure.py out/19_장화홍련.json   → 두 가지 심문 전략 비교 시연
"""
import json, re, sys

W_EMOTION      = 2
W_TRIGGER      = 10
W_CONTRADICT   = 12
W_EVIDENCE     = 15
W_ALIBI_BREAK  = 25
W_DECISIVE     = 40
W_PUSH         = 8      # 결정타를 세운 뒤 몰아붙일 때만 열리는 길
MAX_PUSH       = 3      # 같은 말을 되풀이해 100까지 채우지는 못하게
THRESHOLD      = 70

EMOTION_WORDS = ["양심","죄책","네 탓","당신 때문","불쌍","가엾","부끄","솔직히","털어놓",
                 "편해질","용서","눈물","후회","괴롭"]

class Gauge:
    def __init__(self, s, suspect_id):
        self.s=s; self.cid=suspect_id
        self.c=next(x for x in s["cast"] if x["id"]==suspect_id)
        self.v=0.0
        self.hit={"trigger":False,"contradiction":False,"evidence":False,
                  "alibi_break":False,"decisive":False}
        self.log=[]
        self.pn={p["id"]:p["name"] for p in s["map"]["places"]}
        self.ds=s["death"]["time_slot"]
        self.trig=[t for pp in (self.c.get("pressure_points") or []) for t in pp.get("trigger",[])]
        self.dec=next((cl for cl in s["clue_graph"] if cl.get("decisive")),{})
        # 이 인물의 알리바이가 깨지는 근거(거짓 알리바이 장소를 지킨 목격자)
        self.false_place=None; self.witness=[]
        if self.c.get("lies"):
            fp=self.c["lies"][0].get("false_place")
            self.false_place=self.pn.get(fp)
            self.witness=[x["name"] for x in s["cast"]
                          if x["id"]!=suspect_id and x.get("timeline",{}).get(self.ds)==fp]
        self._said=[]
        self._pushed=[]; self._pushes=0

    @staticmethod
    def _place_said(place, q):
        """장소를 말했는가 — 통짜 이름이 아니라 **토막**으로도 인정한다.
        '부엌·하녀 방'을 사람은 '부엌'이라고 부른다."""
        if not place or not q:
            return False
        if place in q:
            return True
        for part in re.split(r"[·()\s]+", place):
            if len(part) >= 2 and part in q:
                return True
        return False

    def _add(self, amount, why):
        self.v=min(100.0, self.v+amount)
        self.log.append((amount, why))

    def apply(self, question, answer="", evidence_shown=False):
        """한 턴의 심문을 게이지에 반영."""
        q=question or ""
        gained=[]

        # 1) 결정적 증거 제시
        dec_surface=self.dec.get("surface","")
        if evidence_shown or (dec_surface and _overlap(q, dec_surface)>=12):
            if not self.hit["decisive"]:
                self.hit["decisive"]=True; self._add(W_DECISIVE,"결정적 증거 제시"); gained.append("결정적 증거 +40")

        # 2) 알리바이 붕괴 — 거짓 알리바이 장소와 그 목격자를 함께 들이댐
        if self._place_said(self.false_place, q) and any(
                w in q for w in self.witness + ["오지 않", "없었", "보지 못", "둘뿐", "아무도"]):
            if not self.hit["alibi_break"]:
                self.hit["alibi_break"]=True; self._add(W_ALIBI_BREAK,"알리바이 붕괴 입증"); gained.append("알리바이 붕괴 +25")

        # 3) 일반 물증 제시 — 시나리오의 다른 단서 문장을 인용
        for cl in self.s["clue_graph"]:
            if cl.get("decisive"): continue
            if cl.get("weight") in ("weapon","incriminating","context") and _overlap(q, cl.get("surface",""))>=12:
                if not self.hit["evidence"]:
                    self.hit["evidence"]=True; self._add(W_EVIDENCE,"물증 제시"); gained.append("물증 +15")
                break

        # 4) 비밀 트리거 적중
        if any(t and t in q for t in self.trig):
            if not self.hit["trigger"]:
                self.hit["trigger"]=True; self._add(W_TRIGGER,"비밀 트리거 적중"); gained.append("비밀 +10")

        # 5) 모순 지적 — 이전 답과 다른 장소를 말했고 심문관이 그걸 짚음
        places_now={n for n in self.pn.values() if n in answer}
        if places_now:
            for prev in self._said:
                if prev and places_now and prev.isdisjoint(places_now):
                    if not self.hit["contradiction"]:
                        self.hit["contradiction"]=True; self._add(W_CONTRADICT,"진술 모순 발생"); gained.append("모순 +12")
                    break
            self._said.append(places_now)

        # 5.5) ★몰아붙이기 — 결정타를 쥔 뒤 계속 밀어붙이면 오른다.
        #   실제 플레이에서 결정적 증거를 들이대고 62/100에서 멈췄다.
        #   더 밀 방법이 없으니 절정이 오지 않고 판이 흐지부지 끝났다.
        #   증거를 이미 세운 뒤에만 열리는 길이라 '증거 없는 자백'은 여전히 불가능하다.
        if (self.hit["decisive"] or self.hit["alibi_break"]) and len(q) >= 12 and not gained:
            if q not in self._pushed and self._pushes < MAX_PUSH:
                self._pushed.append(q); self._pushes += 1
                self._add(W_PUSH, "몰아붙이기"); gained.append(f"몰아붙이기 +{W_PUSH}")

        # 6) 감정 압박 — 아주 조금만
        if any(w in q for w in EMOTION_WORDS):
            self._add(W_EMOTION,"감정 압박"); gained.append("감정 +2")

        return gained

    def will_confess(self):
        """자백 성립 조건: 게이지 임계 + 증거 축(둘 중 하나) 확보."""
        return self.v>=THRESHOLD and (self.hit["alibi_break"] or self.hit["decisive"])

    def state(self):
        return {"value":round(self.v,1),"threshold":THRESHOLD,
                "will_confess":self.will_confess(),"checklist":dict(self.hit),
                "log":self.log}

    def hud(self):
        """플레이어에게 보이는 한 줄 — 무엇이 더 필요한지 명시(불투명성 방지)."""
        need=[]
        if not (self.hit["alibi_break"] or self.hit["decisive"]): need.append("결정적 증거 또는 알리바이 붕괴")
        if self.v<THRESHOLD: need.append(f"압박 {THRESHOLD-int(self.v)} 더")
        bar="█"*int(self.v/5)+"·"*(20-int(self.v/5))
        mark=lambda k: "✅" if self.hit[k] else "⬜"
        return (f"압박 {int(self.v):3}/100 [{bar}] "
                f"{mark('decisive')}결정타 {mark('evidence')}물증 {mark('alibi_break')}알리바이 "
                f"{mark('trigger')}비밀 {mark('contradiction')}모순"
                + ("  → 자백 임박!" if self.will_confess() else ("  · 필요: "+", ".join(need) if need else "")))

def _overlap(a, b):
    """두 문장의 최장 공통 부분문자열 길이(인용 여부 판정)."""
    if not a or not b: return 0
    prev=[0]*(len(b)+1); best=0
    for i in range(1,len(a)+1):
        cur=[0]*(len(b)+1)
        for j in range(1,len(b)+1):
            if a[i-1]==b[j-1]:
                cur[j]=prev[j-1]+1; best=max(best,cur[j])
        prev=cur
    return best

# ── 검증: '감정만으로 자백 가능한가?' (두근두근의 실패 재현 테스트) ──
def emotion_only_test(s, suspect_id, turns=15):
    """감정 압박만 15턴 퍼부어도 자백에 이르지 못해야 정상."""
    g=Gauge(s,suspect_id)
    for i in range(turns):
        g.apply("양심에 걸리지 않소? 당신 때문에 죽은 거요. 솔직히 털어놓으면 편해질 거요.","")
    return (not g.will_confess()), g.state()["value"]

def evidence_path_test(s, suspect_id):
    """증거를 제대로 들이대면 자백에 이르러야 정상."""
    g=Gauge(s,suspect_id)
    c=next(x for x in s["cast"] if x["id"]==suspect_id)
    trig=[t for pp in (c.get("pressure_points") or []) for t in pp.get("trigger",[])]
    pn={p["id"]:p["name"] for p in s["map"]["places"]}
    ds=s["death"]["time_slot"]
    if trig: g.apply(f"'{trig[0]}'에 대해 말해 보시오.","")
    if c.get("lies"):
        fp=pn.get(c["lies"][0].get("false_place"),"")
        wit=[x["name"] for x in s["cast"] if x["id"]!=suspect_id and x.get("timeline",{}).get(ds)==c["lies"][0].get("false_place")]
        g.apply(f"{fp}에 있었다 했으나 {wit[0] if wit else '그 자리를 지킨 이'}는 당신이 오지 않았다 하오.","")
    dec=next((cl for cl in s["clue_graph"] if cl.get("decisive")),{})
    g.apply(f"증거가 이렇소: {dec.get('surface','')}","",evidence_shown=True)
    return g.will_confess(), g.state()["value"]

if __name__=="__main__":
    path=sys.argv[1] if len(sys.argv)>1 else "scenarios/19_장화홍련.json"
    s=json.load(open(path,encoding="utf-8"))
    cul=next(c for c in s["cast"] if c.get("is_culprit"))
    print(f"=== 압박 게이지 시연: {s['meta']['title']} · {cul['name']}(범인) ===\n")

    print("[전략 A] 감정만 퍼붓기 (두근두근에서 통하던 방식)")
    g=Gauge(s,cul["id"])
    for i in range(6):
        g.apply("양심에 걸리지 않소? 당신 때문에 죽은 거요. 솔직히 털어놓으시오.","")
        if i in (0,5): print("  ",g.hud())
    print(f"   → 자백? {g.will_confess()}  (감정만으론 뚫리지 않아야 정상)\n")

    print("[전략 B] 증거로 조이기")
    g2=Gauge(s,cul["id"])
    pn={p["id"]:p["name"] for p in s["map"]["places"]}
    trig=[t for pp in (cul.get("pressure_points") or []) for t in pp.get("trigger",[])]
    steps=[]
    if trig: steps.append((f"'{trig[0]}' 얘기를 해 봅시다.",False))
    if cul.get("lies"):
        fp=pn.get(cul["lies"][0].get("false_place"),"")
        wit=[x["name"] for x in s["cast"] if x["id"]!=cul["id"]
             and x.get("timeline",{}).get(s["death"]["time_slot"])==cul["lies"][0].get("false_place")]
        steps.append((f"{fp}에 있었다 했으나, {wit[0] if wit else '그 자리의 사람'}은 당신이 오지 않았다 하오.",False))
    dec=next((cl for cl in s["clue_graph"] if cl.get("decisive")),{})
    steps.append((f"증거가 이렇소: {dec.get('surface','')}",True))
    for q,evi in steps:
        gained=g2.apply(q,"",evidence_shown=evi)
        print(f"   Q: {q[:52]}…")
        print("  ",g2.hud(), f"  {gained}")
    print(f"   → 자백? {g2.will_confess()}  (증거를 갖추면 무너져야 정상)")

    print("\n=== 검증 ===")
    ok1,v1=emotion_only_test(s,cul["id"])
    ok2,v2=evidence_path_test(s,cul["id"])
    print(f"  {'✅' if ok1 else '❌'} 감정만 15턴 → 자백 불가 (게이지 {v1})")
    print(f"  {'✅' if ok2 else '❌'} 증거 경로  → 자백 성립 (게이지 {v2})")
