# -*- coding: utf-8 -*-
"""
agent_memory.py — 용의자 에이전트의 장기기억.

문제
  · 지금은 대화 history 리스트뿐 → 길어지면 잘리고, 20턴 전 자기 진술을 잊어 말이 바뀐다(contradiction).
  · 라운드가 바뀌거나 세션이 끊기면 기억이 통째로 사라진다.
  · 이미 실토한 비밀을 또 실토하거나, 안 한 척한다.

설계 (4층 기억)
  1) commitments  : 에이전트가 '사실'로 뱉은 진술 원장(장소·시각·인물·행위). ← 모순 방지의 핵심
  2) disclosures  : 이미 공개한 비밀/트리거. 재공개·번복 방지
  3) episodes     : 턴 요약(누가 뭘 물었고 나는 어떻게 반응했나) — 오래된 건 압축
  4) pressure     : 심문 강도·추궁 횟수·현재 라운드 상태
  → 매 턴 시스템 프롬프트에 '기억 브리핑'으로 주입 → 모델이 과거와 어긋나지 않게 답한다.

디스크에 저장되어 세션이 끊겨도 이어진다: out/memory/<시나리오>__<용의자>.json

사용:
  from agent_memory import Memory
  mem = Memory(scenario_id, suspect_id)          # 자동 로드
  sys_prompt = base_prompt + mem.briefing()      # 매 턴 주입
  mem.observe(question, answer, round_no)        # 답변 후 기록(자동 사실추출)
  mem.save()
단독 실행: python agent_memory.py out/14_나생문.json   → 메모리 스키마 미리보기
"""
import json, os, re, time, glob, sys

MEM_DIR = ".runtime/memory"

# 질문 낱말에서 조사를 뗀다 — '안건을'과 '안건은'이 같은 것을 묻는 말이 되도록
_JOSA_Q = ("에서는", "에게서", "으로는", "이라는", "에서", "에게", "으로", "까지",
           "부터", "에는", "에도", "이나", "만은", "이란", "라는",
           "을", "를", "이", "가", "은", "는", "에", "의", "와", "과", "도", "로", "만")


def _strip_josa_q(w):
    for j in _JOSA_Q:
        if w.endswith(j) and len(w) - len(j) >= 2:
            return w[: -len(j)]
    return w

# ── 진술에서 '사실 주장' 뽑기(장소·시각·행위·인물) ─────────────────────
def _place_aliases(name):
    """'무덤가 움막(칠성 자리)' → ['무덤가 움막(칠성 자리)','무덤가 움막','움막'] 처럼 부분 표기도 매칭."""
    al=[name]
    base=re.sub(r"\s*[（(].*?[)）]\s*","",name).strip()      # 괄호 주석 제거
    if base and base!=name: al.append(base)
    toks=[t for t in re.split(r"[ ·]", base) if len(t)>=2]
    if toks: al.append(toks[-1])                            # 마지막 명사(움막/계단/처마…)
    return list(dict.fromkeys(al))

def extract_claims(text, places, slots, names):
    """모델 답변에서 검증 가능한 사실 주장을 추출한다(규칙 기반, LLM 불필요)."""
    claims=[]
    for pl in places:
        if not pl: continue
        hit=next((a for a in _place_aliases(pl) if a and a in text), None)
        if hit:
            # 부정문이면 '없었다' 주장으로 (별칭 기준으로 탐지)
            neg = re.search(r"%s[^.!?]{0,14}(안 갔|가지 않|없었|들르지 않|발도|근처에도)" % re.escape(hit), text)
            claims.append({"type":"place","value":pl,"polarity":"absent" if neg else "present"})
    for sl in slots:
        if sl and sl in text: claims.append({"type":"time","value":sl,"polarity":"present"})
    for nm in names:
        if nm and nm in text: claims.append({"type":"person","value":nm,"polarity":"mentioned"})
    for m in re.finditer(r"(밤새|내내|줄곧|한 번도|처음부터 끝까지)", text):
        claims.append({"type":"absolute","value":m.group(1),"polarity":"asserted"})
    return claims

class Memory:
    def __init__(self, scenario_id, suspect_id, scenario=None, mem_dir=MEM_DIR,
                 resume=False):
        """resume=False가 기본이다 (2026-08-25).

        ★기억은 **한 판 안에서만** 이어져야 한다. 예전엔 무조건 디스크의 옛
          기록을 읽어 들였다. 그래서 새 판 1라운드 **첫 질문**부터 다섯 명이
          모두 "아까 말씀드렸잖아요"로 답했다 — 지난 판의 기억이었다.
          판을 새로 시작하면 백지에서 출발한다. 이어서 볼 때만 resume=True.
        """
        self.sid=scenario_id; self.cid=suspect_id; self.dir=mem_dir
        self.path=os.path.join(mem_dir, f"{scenario_id}__{suspect_id}.json")
        self.s=scenario
        self.data={"scenario":scenario_id,"suspect":suspect_id,
                   "commitments":[], "disclosures":[], "episodes":[],
                   "pressure":{"turns":0,"accusations":0,"round":1,"max_pressure":0},
                   "updated":None}
        if resume and os.path.exists(self.path):
            try: self.data=json.load(open(self.path,encoding="utf-8"))
            except Exception: pass
        # 시나리오에서 어휘 목록 준비
        self.places=[p["name"] for p in (scenario or {}).get("map",{}).get("places",[])] if scenario else []
        self.slots=(scenario or {}).get("time_slots",[]) if scenario else []
        self.names=[c["name"] for c in (scenario or {}).get("cast",[])] if scenario else []
        if scenario: self.names.append(scenario.get("victim",{}).get("name",""))
        self.triggers=[]
        if scenario:
            me=next((c for c in scenario["cast"] if c["id"]==suspect_id), None)
            if me: self.triggers=[t for pp in (me.get("pressure_points") or []) for t in pp.get("trigger",[])]

    # ── 기록 ────────────────────────────────────────────────
    def observe(self, question, answer, round_no=None):
        p=self.data["pressure"]; p["turns"]+=1
        if round_no: p["round"]=round_no
        if any(w in question for w in ["죽인","범인","자백","당신이 했"]): p["accusations"]+=1
        # 1) 사실 주장 원장에 적립(중복은 카운트만 증가)
        for cl in extract_claims(answer, self.places, self.slots, self.names):
            key=(cl["type"],cl["value"],cl["polarity"])
            hit=next((c for c in self.data["commitments"]
                      if (c["type"],c["value"],c["polarity"])==key), None)
            if hit: hit["times"]+=1; hit["last_round"]=p["round"]
            else:
                self.data["commitments"].append({**cl,"times":1,
                    "first_round":p["round"],"last_round":p["round"],
                    "quote":answer[:80]})
        # 2) 비밀 공개 여부
        fired=[t for t in self.triggers if t in question]
        if fired and answer:
            for t in fired:
                if t not in [d["trigger"] for d in self.data["disclosures"]]:
                    self.data["disclosures"].append({"trigger":t,"round":p["round"],
                                                     "said":answer[:120]})
        # 3) 에피소드(최근 12턴 유지, 그 이전은 압축)
        self.data["episodes"].append({"r":p["round"],"q":question[:70],"a":answer[:110]})
        if len(self.data["episodes"])>12:
            old=self.data["episodes"][:-12]; self.data["episodes"]=self.data["episodes"][-12:]
            summ=f"(이전 {len(old)}턴 요약) 주로 " + ", ".join(
                sorted({c['value'] for c in self.data['commitments'] if c['type']=='place'})[:3]) + " 관련 진술 반복"
            self.data["episodes"].insert(0,{"r":0,"q":"[압축된 과거]","a":summ})
        p["max_pressure"]=max(p["max_pressure"], p["accusations"])
        return self

    # ── 주입용 브리핑 ───────────────────────────────────────
    # ── 이미 물었던 것인가 ────────────────────────────────────────────
    #  ★찬열이형 요청(2026-08-25)
    #    "그 용의자가 채팅에서 했던 말을 또 반복해서 대답해야 할 때, 오류 말고
    #     '아 아까 대답했잖아요', '전에 말했듯이~' 이렇게 할 수 있게"
    #    → 같은 것을 다시 물으면 **같은 답을 복사하지 말고, 이미 말했음을 짚고** 넘어간다.
    #      한 겹 더 얹거나 짜증을 내거나 — 어느 쪽이든 '기억하는 사람'으로 보여야 한다.
    _STOP_Q = {"대해", "말해", "보시오", "말씀", "주시오", "합니까", "인가요", "무엇",
               "어떻게", "그날", "그때", "당신", "그거", "그것"}

    def _qkey(self, q):
        """질문에서 뜻 있는 낱말만 추린다 — 표현이 달라도 같은 것을 묻는지 보려고.

        ★한글만 뽑으면 'DSL 2.0' 같은 핵심어를 통째로 버린다.
          영문·숫자도 함께 잡는다. 조사가 붙은 꼴('안건을','탄핵은')도 같은 것으로 본다.
        """
        raw = re.findall(r"[가-힣]{2,}|[A-Za-z][A-Za-z0-9.]{1,}|[0-9]+\.?[0-9]*", q or "")
        out = set()
        for w in raw:
            w = w.strip(".")
            if not w:
                continue
            if re.fullmatch(r"[가-힣]+", w):
                w = _strip_josa_q(w)             # 조사 떼기
                if len(w) < 2 or w in self._STOP_Q:
                    continue
            out.add(w.lower())
        return out

    def recall(self, question):
        """이 질문을 전에도 받았는가. 받았으면 그때 뭐라 답했는지 함께 돌려준다."""
        now = self._qkey(question)
        if not now:
            return None
        best, score = None, 0.0
        for e in self.data["episodes"]:
            if e.get("q", "").startswith("["):
                continue                       # 압축된 과거는 건너뛴다
            prev = self._qkey(e["q"])
            if not prev:
                continue
            j = len(now & prev) / len(now | prev)
            if j > score:
                best, score = e, j
        if best and score >= 0.5:              # 절반 이상 겹치면 '같은 것을 또 묻는다'
            times = sum(1 for e in self.data["episodes"]
                        if not e.get("q", "").startswith("[")
                        and len(self._qkey(e["q"]) & now) / max(1, len(self._qkey(e["q"]) | now)) >= 0.5)
            return {"asked_before": True, "similarity": round(score, 2),
                    "times": times, "prev_q": best["q"], "prev_a": best["a"],
                    "round": best["r"]}
        return None

    def briefing(self):
        """매 턴 시스템 프롬프트 뒤에 붙일 '내 기억'. 모델이 과거 진술과 어긋나지 않게 한다."""
        if not self.data["commitments"] and not self.data["episodes"]:
            return "\n[내 기억] 아직 심문에서 한 말이 없다."
        L=["\n[내 기억 — 반드시 이와 어긋나지 않게 답하라]"]
        # 1) 내가 이미 못 박은 사실
        pl=[c for c in self.data["commitments"] if c["type"]=="place"]
        if pl:
            txt=", ".join(f"{c['value']}에 {'있었다' if c['polarity']=='present' else '가지 않았다'}"
                          f"({c['times']}회 진술)" for c in pl[:6])
            L.append(f"· 내가 이미 말한 내 소재: {txt}")
        ab=[c["value"] for c in self.data["commitments"] if c["type"]=="absolute"]
        if ab: L.append(f"· 내가 쓴 단정 표현: {', '.join(sorted(set(ab))[:4])} — 이 단정을 뒤집지 말 것")
        pr=[c["value"] for c in self.data["commitments"] if c["type"]=="person"]
        if pr: L.append(f"· 내가 언급한 인물: {', '.join(sorted(set(pr))[:6])}")
        # 2) 이미 실토한 비밀
        if self.data["disclosures"]:
            ds=", ".join(d["trigger"] for d in self.data["disclosures"])
            L.append(f"· 이미 실토한 것: [{ds}] — 이미 인정했으므로 '그런 적 없다'고 번복하지 말 것. "
                     f"다시 물으면 인정한 상태에서 이어 말하라.")
        else:
            L.append("· 아직 아무 비밀도 실토하지 않았다 — 먼저 꺼내지 말 것")
        # 3) 최근 대화
        if self.data["episodes"]:
            L.append("· 최근 오간 말:")
            for e in self.data["episodes"][-4:]:
                L.append(f"    (R{e['r']}) 묻기: {e['q']} / 내 답: {e['a']}")
        # 4) 압박 상태 → 태도 조정
        p=self.data["pressure"]
        L.append(f"· 현재 라운드 R{p['round']}, 나는 지금까지 {p['turns']}번 답했고 "
                 f"{p['accusations']}번 범인으로 몰렸다. "
                 + ("압박이 크다 — 태도가 조금씩 흔들려도 좋다." if p["accusations"]>=2
                    else "아직 여유가 있다."))
        L.append("· 같은 문장을 그대로 반복하지 말 것. 같은 사실이라도 표현을 바꿔 말하라.")
        return "\n".join(L)

    # 말체별 '아까 말했잖아요' 문형 — 인물 말투로 되받아야 사람처럼 보인다
    _AGAIN = {
        "해요체": ("아까 말씀드렸잖아요", "그건 아까 다 얘기했어요"),
        "다정체": ("아까 말씀드렸잖아요", "그건 아까 다 얘기했어요"),
        "설명체": ("아까 말씀드렸던 거잖아요", "그건 아까 얘기했더라고요"),
        "반존대": ("아까 말했잖아요", "그건 아까 다 얘기했는데요"),
        "합쇼체": ("아까 말씀드렸습니다", "그건 앞서 말씀드린 그대로입니다"),
        "합니다체": ("아까 말씀드렸습니다", "그건 앞서 말씀드린 그대로입니다"),
        "격식체": ("아까 말씀드렸습니다", "앞서 말씀드린 그대로입니다"),
        "건조체": ("아까 말했습니다", "앞서 말한 그대로입니다"),
        "공손체": ("아까 말씀드렸지요", "앞서 말씀드린 그대로랍니다"),
        "완곡체": ("아까 말씀드렸네요", "앞서 말씀드린 그대로군요"),
        "하오체": ("아까 말하지 않았소", "앞서 말한 그대로요"),
        "정중체": ("아까 말하지 않았소", "앞서 말한 그대로요"),
        "탄식체": ("아까 말하지 않았소이다", "앞서 말한 그대로외다"),
        "하게체": ("아까 말하지 않았나", "앞서 말한 그대로일세"),
        "노숙체": ("아까 말하지 않았나", "앞서 말한 그대로네"),
        "노년체": ("아까 말했지", "앞서 말한 그대로네"),
        "소인체": ("아까 아뢰지 않았사옵니까", "앞서 아뢴 그대로이옵니다"),
        "올시다체": ("아까 말씀드렸소", "앞서 말한 그대로올시다"),
        "노라체": ("아까 이르지 않았느냐", "앞서 이른 그대로니라"),
    }

    def again_directive(self, question, form="", name=""):
        """같은 것을 또 물었을 때 프롬프트에 얹을 지시. 없으면 None."""
        r = self.recall(question)
        if not r:
            return None
        a, b = self._AGAIN.get(form, ("아까 말씀드렸습니다", "앞서 말씀드린 그대로입니다"))
        n = r["times"]
        tone = ("처음 되풀이라 담담하게" if n <= 1 else
                "두 번째라 슬쩍 성가신 기색" if n == 2 else
                "세 번째다 — 대놓고 지친 티를 내라")
        return (
            "\n[★이건 이미 물었던 것이다]\n"
            f"· 같은 것을 {n}번째 묻고 있다. (그때 내 답: \"{r['prev_a']}\")\n"
            f"· **같은 답을 복사하지 마라.** 먼저 이미 말했다는 것을 짚어라 — "
            f"\"{a}\" 나 \"{b}\" 같은 식으로, 네 말투로.\n"
            f"· 그러고 나서 **한 겹만 더 얹어라** — 그때 빠뜨린 자리·시각·사람 한 가지.\n"
            f"  더 얹을 것이 정말 없으면 그렇게 말하고 짧게 끝내라.\n"
            f"· 기색: {tone}.\n"
            f"· ★물음표는 여전히 금지다. 되묻지 말고 그냥 말하라."
        )

    # ── 자기모순 자체 점검(저장 전) ─────────────────────────
    def self_contradiction(self):
        """원장 안에서 서로 충돌하는 주장을 찾아낸다(같은 장소를 있었다/없었다)."""
        bad=[]
        seen={}
        for c in self.data["commitments"]:
            if c["type"]!="place": continue
            k=c["value"]
            if k in seen and seen[k]!=c["polarity"]:
                bad.append(f"{k}: '{seen[k]}' ↔ '{c['polarity']}'")
            else: seen[k]=c["polarity"]
        # 사망 시각에 두 곳 이상 '있었다'
        present=[c["value"] for c in self.data["commitments"]
                 if c["type"]=="place" and c["polarity"]=="present"]
        if len(set(present))>2:
            bad.append(f"소재 주장이 {len(set(present))}곳으로 흩어짐: {sorted(set(present))[:4]}")
        return bad

    def save(self):
        os.makedirs(self.dir, exist_ok=True)
        self.data["updated"]=time.strftime("%Y-%m-%d %H:%M:%S")
        json.dump(self.data, open(self.path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        return self.path

    def reset(self):
        self.data["commitments"]=[]; self.data["disclosures"]=[]; self.data["episodes"]=[]
        self.data["pressure"]={"turns":0,"accusations":0,"round":1,"max_pressure":0}
        return self

if __name__=="__main__":
    path=sys.argv[1] if len(sys.argv)>1 else "scenarios/14_나생문.json"
    s=json.load(open(path,encoding="utf-8"))
    sid=os.path.basename(path).replace(".json","")
    c=next(x for x in s["cast"] if x.get("is_culprit"))
    m=Memory(sid,c["id"],s,mem_dir=".runtime/memory_demo")
    # 데모: 두 턴을 관찰시키고 브리핑을 보여준다
    m.observe("밤에 어디 있었소?", c.get("alibi_narration",""), 1)
    trg=(c.get("pressure_points") or [{}])[0].get("trigger",["비밀"])[0]
    m.observe(f"'{trg}'에 대해 말해 보시오.", (c.get("pressure_points") or [{}])[0].get("reveals",""), 2)
    print(f"=== {c['name']} 기억 브리핑(시스템 프롬프트에 주입되는 부분) ===")
    print(m.briefing())
    print("\n자기모순 점검:", m.self_contradiction() or "없음")
    print("저장:", m.save())
