# -*- coding: utf-8 -*-
"""
game_engine_v2.py — 확장 머더미스터리 게임 엔진 (v2.2)
1. 상호작용형 소지품 (Belongings) 심문 획득 & forced_by 연쇄 해금 (매칭 사유 반환, 한국어 조사 처리)
2. 복합 단서 조합 (/combine) — weight, decisive, points_to 반환 일관성 보장
3. 2차 정밀 감식 (/inspect)
4. 대질 심문 (/confront) — 1회 한정 안전 차감 (turns 사전 검사), undisclosed hidden_from 한정 FLINCH

── 시나리오 데이터 v2 연동 (2026-08-25) ─────────────────────────────
원본 엔진은 50편 전부 그대로 통과했다. 아래는 **로직은 그대로 두고 읽는 데이터만 늘린** 것이다.
  P1 /combine  이 시나리오의 clue_combos(본 단서끼리의 조합)도 읽는다   편당 1.0 → 4.1개
  P2 /inspect  이 place_rewards(장소별 고유 발견)도 받는다              편당 1.0 → 2.8곳
  P3 /confront 가 cross_examination(큐레이션된 대질 대사)을 함께 돌려준다  편당 3.7쌍
  P4 weight 어휘를 시나리오와 통일 (incriminating → physical)
  P5 turns_per_round 기본값 8 → 12 (전 편 실제값)
  P6 points_to 폴백 제거 — 진범이 안 낀 조합은 None (UI 오해 방지)
  P7 round_min 존중 — 아직 이른 조합/대질은 막는다
"""
import json, re
from stance import decide as stance_decide, directive as stance_directive
from pressure import Gauge
try:
    from agent_memory import Memory          # 장기기억(디스크에 남는다)
except Exception:
    Memory = None

CONFRONT_PRESSURE_BONUS = 10.0  # 대질 심문 시 동석으로 인한 기본 압박 증가치 (전 시나리오 공통 룰)
STOPWORDS = {"그것", "이것", "저것", "했다", "있는", "하는", "이후", "그때", "사실", "경우", "대해", "위해", "몰래", "자신"}
JOSA_LIST = ("으로써", "으로서", "에서는", "에게서", "이라는", "에서", "에게", "으로", "까지", "부터", "이나", "이며", "하며", "이고", "을", "를", "이", "가", "은", "는", "에", "의", "와", "과", "도", "로", "만", "랑")

def _josa(w, pair="을/를"):
    """받침을 보고 조사를 고른다. '서민재와 차연우를'처럼 어긋나던 자리를 막는다."""
    a, b = pair.split("/")
    ch = (w or " ")[-1]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


def _strip_josa(w):
    for j in JOSA_LIST:
        if w.endswith(j) and len(w) > len(j) + 1:
            return w[:-len(j)]
    return w

class GameSession:
    def __init__(self, scenario_dict):
        self.s = scenario_dict
        self.cast = {c["id"]: c for c in self.s.get("cast", [])}
        self.places = {p["id"]: p for p in self.s.get("map", {}).get("places", [])}
        self.clue_graph = {cl["id"]: cl for cl in self.s.get("clue_graph", [])}
        self.culprit_id = self.s.get("solution", {}).get("culprit")
        
        # 플레이어 인벤토리 및 상태
        self.held_clues = set()
        self.disclosed_secrets = {cid: set() for cid in self.cast}
        self.gauges = {cid: Gauge(self.s, cid) for cid in self.cast}
        self.denied_before = {cid: False for cid in self.cast}
        
        # 리소스 및 제한
        self.current_round = 1
        self.max_rounds = self.s.get("config", {}).get("rounds", 3)
        self.turns_left = self.s.get("config", {}).get("turns_per_round", 12)  # P5
        self.confront_tokens = 1  # 대질 심문 1회 한정
        self.met = set()          # 알리바이를 이미 들은 인물 (첫 대면은 한 번뿐)
        self.searched = set()     # (장소, 라운드) — 이미 값을 치른 방
        self.notebook = []        # ★수첩에 적힌 것 — 얻는 즉시 여기 쌓인다
        self.flinches = {}        # {용의자: {비밀: 흔들린 횟수}} — 집요한 추궁의 길
        self._heard = []          # 지금까지 들은 답 — '아는 것'에 들어간다
        self._answers_seen = 0
        self._known_cache, self._known_cache_at = "", None
        
        # 복합 단서 및 2차 감식 데이터베이스
        self.composite_clues = self._init_composite_clues()
        self.inspections = self._init_inspections()
        
        # 1라운드 스파인 단서 기본 지급 — 수첩에도 곧장 적는다
        for cl in self.s.get("clue_graph", []):
            if cl.get("reveal_round") == 1 and cl.get("channel") in ("spine", "crime_scene"):
                self.held_clues.add(cl["id"])
                self._record(cl["id"],
                             "사건 시작 시 공개" if cl.get("channel") == "crime_scene"
                             else "1라운드 자동 공개")

        # P8) 대질 해금 라운드 — 중반 이벤트가 터진 뒤부터 열린다.
        _cx = self.s.get("cross_examination") or {}
        _ev = [e.get("round") for e in self.s.get("events", []) if e.get("round")]
        self.confront_unlock_round = _cx.get("unlock_round") or (min(_ev) if _ev else 2)

        # P9) 인물별 장기기억 — 이미 한 말·이미 받은 질문을 기억한다.
        #     대화 이력만으로는 길어지면 잘리고 라운드가 넘어가면 사라진다.
        #     같은 것을 또 물으면 "아까 말씀드렸잖아요"로 받게 하는 것이 목적이다.
        self.memory = {}
        if Memory:
            sid = (self.s.get("meta") or {}).get("origin", "scenario")
            for cid in self.cast:
                try:
                    # 새 판은 **백지에서** 시작한다 — 지난 판 기억을 물려받으면
                    # 첫 질문부터 "아까 말씀드렸잖아요"가 나온다.
                    self.memory[cid] = Memory(sid, cid, scenario=self.s, resume=False)
                except Exception:
                    pass

        # P3) 큐레이션된 대질 쌍 — (a,b) 순서 무관하게 찾도록 색인
        self.cx_pairs = {}
        for x in (self.s.get("cross_examination") or {}).get("pairs", []):
            self.cx_pairs[tuple(sorted([x["a"], x["b"]]))] = x

    def _init_composite_clues(self):
        """시나리오에 정의된 복합 단서 or 소지품 조합 규칙 로드"""
        combos = {}
        # 1) 시나리오 자체 composite_clues 필드 확인
        for cc in self.s.get("composite_clues", []):
            req = tuple(sorted(cc.get("requires", [])))
            combos[req] = cc

        # 2) belongings의 combines_with에서 자동 도출
        belonging_map = {}
        for cid, c in self.cast.items():
            for b in c.get("belongings", []):
                belonging_map[b["id"]] = (cid, b)

        for bid, (cid, b) in belonging_map.items():
            partner = b.get("combines_with")
            if partner and partner in belonging_map:
                pair = tuple(sorted([bid, partner]))
                if pair not in combos:
                    p_cid, p_b = belonging_map[partner]
                    
                    # points_to 논리 보정: 진범이 연루된 조합일 때만 진범 지목, 아닐 경우 신분/비밀 주체 지목
                    target_culprit = p_cid if self.cast[p_cid].get("is_culprit") else (cid if self.cast[cid].get("is_culprit") else None)
                    is_decisive = target_culprit is not None
                    
                    combos[pair] = {
                        "id": f"CK_{pair[0]}_{pair[1]}",
                        "name": f"{b['name']} + {p_b['name']} 대조 감정서",
                        "requires": list(pair),
                        "surface": f"{b['name']}과 {p_b['name']}을 결합하여 확인한 결과: {b.get('reveals','')}와 {p_b.get('reveals','')}가 정확히 일치하여 진실이 입증됨.",
                        "implies": f"{b.get('reveals','')} 관련 서브 사건 및 인물 관계의 실체 규명.",
                        # P4) 시나리오 어휘와 통일: incriminating → physical
                        "weight": "physical" if is_decisive else "context",
                        # P6) 진범이 안 낀 조합은 가리키는 사람을 두지 않는다.
                        #     decisive=False인데 points_to가 차 있으면 UI가
                        #     "이 사람을 가리키는 단서"로 오해한다.
                        "points_to": target_culprit,
                        "decisive": is_decisive
                    }

        # P1) 시나리오의 clue_combos — 본 단서(clue_graph)끼리의 조합.
        #     belongings 조합(편당 1개)과 달리 편당 3.1개가 더 있다.
        for cb in (self.s.get("clue_combos") or {}).get("combos", []):
            req = tuple(sorted(cb.get("needs", [])))
            if len(req) != 2 or req in combos:
                continue
            combos[req] = {
                "id": cb["id"],
                "name": cb.get("title", cb["id"]),
                "requires": list(req),
                "surface": cb.get("yields", ""),
                "implies": cb.get("unlocks", ""),
                "weight": "context",
                "points_to": None,
                "decisive": False,
                "points": cb.get("points", 1),        # 채점에 더할 점수
                "round_min": cb.get("round_min", 1),  # 이 라운드부터 가능
                "source": "clue_combos",
            }
        return combos

    def _init_inspections(self):
        """현장 및 단서 2차 감식 항목 초기화"""
        insp = {}
        d = self.s.get("death", {})
        dp = d.get("place", "PC")
        insps = d.get("scene_inspection", [])
        if insps:
            insp[dp] = {
                "id": f"INSP_{dp}",
                "target": dp,
                "target_name": self.places.get(dp, {}).get("name", "사건 현장"),
                "result": "\n".join([f"  · [정밀 검시] {line}" for line in insps]),
                "clue_id": f"K_INSP_{dp}",
                "clue_name": f"{self.places.get(dp, {}).get('name', '현장')} 정밀 감식 소견서",
                "surface": f"정밀 감식 결과: {insps[0] if insps else ''}",
                "weight": "context",
                "decisive": False
            }

        # P2) 장소별 고유 발견 — 정식 단서가 없는 방에도 볼 것을 준다.
        #     "들어가 봐야 아무것도 없는 방"을 없애려고 시나리오에 넣은 값이다.
        for pid, r in (self.s.get("place_rewards") or {}).get("rewards", {}).items():
            if pid in insp:
                continue
            insp[pid] = {
                "id": f"INSP_{pid}",
                "target": pid,
                "target_name": r.get("name", pid),
                "result": f"  · {r.get('text','')}",
                "clue_id": f"K_INSP_{pid}",
                "clue_name": f"{r.get('name', pid)}에서 본 것",
                "surface": r.get("text", ""),
                "weight": "context",
                "decisive": False,
                "teaches": r.get("teaches", ""),   # 무엇을 알게 되는가
                "about": r.get("about"),           # 관련 인물 id (있으면)
                "source": "place_rewards",
            }
        return insp

    def _find_matching_belonging(self, suspect_data, admitted_secret):
        """실토(ADMIT)한 비밀과 일치하는 소지품(짐 카드)을 정밀 매칭하여 (소지품 dict, 매칭사유) 반환"""
        if not suspect_data.get("belongings"):
            return None, None
            
        sec_text = admitted_secret.get("text", "")
        sec_forced = set(admitted_secret.get("forced_by", []))
        
        # 1) 비밀의 forced_by에 명시된 소지품 ID 매칭
        for b in suspect_data.get("belongings", []):
            bid = b.get("id")
            if bid in sec_forced and bid not in self.held_clues:
                return b, "forced_by"
                
        # 2) 유의미한 명사/키워드(조사 제거 및 불용어 제외) 유사도 매칭
        raw_tokens = re.findall(r'[가-힣]{2,}', sec_text)
        meaningful_words = [_strip_josa(w) for w in raw_tokens if len(_strip_josa(w)) >= 2 and _strip_josa(w) not in STOPWORDS]
        if meaningful_words:
            for b in suspect_data.get("belongings", []):
                bid = b.get("id")
                if bid not in self.held_clues:
                    target_text = b.get("name", "") + " " + b.get("reveals", "")
                    if any(w in target_text for w in meaningful_words):
                        return b, "keyword"
                    
        # 3) 미획득 소지품 중 첫 번째 fallback
        for b in suspect_data.get("belongings", []):
            bid = b.get("id")
            if bid not in self.held_clues:
                return b, "fallback"
        return None, None

    def interrogate(self, suspect_id, question, evidence_shown=False, confronting_with=None,
                    free=False, evidence_id=None):
        """용의자 심문 실행"""
        if suspect_id not in self.cast:
            return {"error": f"존재하지 않는 용의자 ID: {suspect_id}"}
        
        c = self.cast[suspect_id]
        
        # 행동 예산 (2026-08-25) — 심문 1. 대질은 **예산 밖 별도 토큰**이라 free=True로 온다.
        #   예산 안에 두었더니 예산 10 이하에서 한 번도 안 쓰였다(실측 0회).
        #   한 판에 한 번뿐인 특별 행동이 일상 행동과 예산을 다투면 영영 안 쓰인다.
        cost = 0 if free else 1
        if self.turns_left < cost:
            return {"error": f"이 라운드에 남은 행동이 없습니다 (현재: {self.turns_left})",
                    "out_of_budget": True}
        self.turns_left -= cost

        # 1. 대질 심문 상태 및 '아직 공개되지 않은' hidden_from 감지
        is_flinch_confront = False
        confront_reason = ""
        if confronting_with:
            w_name = self.cast.get(confronting_with, {}).get("name", confronting_with)
            for sec in c.get("secrets", []):
                sec_text = sec.get("text", "")
                # 이미 실토하여 공개된 비밀은 FLINCH 대상에서 제외
                if sec_text not in self.disclosed_secrets[suspect_id]:
                    if confronting_with in sec.get("hidden_from", []):
                        is_flinch_confront = True
                        confront_reason = f"비밀을 감춰야 하는 {w_name}({confronting_with})이 동석해 있어 극도로 동요함"
                        break

        # 2. Stance 결정
        gauge_state = self.gauges[suspect_id].state()
        st = stance_decide(
            self.s, c, question,
            gauge_state=gauge_state,
            evidence_shown=evidence_shown,
            disclosed=self.disclosed_secrets[suspect_id],
            denied_before=self.denied_before[suspect_id],
            held_clues=self.held_clues,
            flinches=self.flinches.get(suspect_id, {}),  # 같은 자리를 몇 번 찔렀나
            known=self.known_text(),                     # 플레이어가 화면에서 본 것
            evidence_id=(evidence_id if evidence_id in self.held_clues else None),
        )

        # 대질로 인한 FLINCH 오버라이드 (ADMIT/BREAK가 아닌 경우)
        if is_flinch_confront and st["stance"] in ("DEFLECT", "ANSWER"):
            st["stance"] = "FLINCH"
            st["why"] = confront_reason

        # 3. Pressure 및 게이지 반영
        applied = self.gauges[suspect_id].apply(
            question=question,
            answer="",
            evidence_shown=evidence_shown
        )
        if confronting_with:
            w_name = self.cast.get(confronting_with, {}).get("name", confronting_with)
            self.gauges[suspect_id]._add(CONFRONT_PRESSURE_BONUS, f"대질 심문 동석 긴장 ({w_name})")

        # 4. ADMIT 도달 시 비밀 실토 및 '정합한 소지품(Belongings)' 획득
        yielded_belonging = None
        match_reason = None
        if st["stance"] == "ADMIT":
            admitted_sec = st.get("secret") or {}
            sec_text = admitted_sec.get("text", "")
            if sec_text:
                self.disclosed_secrets[suspect_id].add(sec_text)
            
            matched_b, match_reason = self._find_matching_belonging(c, admitted_sec)
            if matched_b:
                bid = matched_b.get("id")
                self.held_clues.add(bid)
                # ★심문으로 얻은 물건도 추리에 값을 보탠다 (2026-08-27).
                #   제 입으로 내놓은 제 물건이니 임자가 분명하다.
                #   전에는 clue_graph 밖에 있어 지목 셈에 한 톨도 들어가지 않았다.
                self.clue_graph.setdefault(bid, {
                    "id": bid, "channel": "belongings", "medium": "소지품",
                    "surface": str(matched_b.get("surface") or matched_b.get("name") or bid),
                    "weight": "testimony", "decisive": False,
                    "points_to": suspect_id,
                    "reveal_round": self.current_round,
                })
                yielded_belonging = matched_b
                self._record(bid, "심문 실토", who=c["name"])         # 수첩에 자동 기록

        elif st["stance"] == "DEFLECT":
            self.denied_before[suspect_id] = True

        elif st["stance"] == "FLINCH" and (st.get("secret") or {}).get("text"):
            # 흔들린 자리를 적어 둔다 — 같은 자리를 거듭 찌르면 결국 열린다.
            # 게이지도 조금씩 올린다. 그래야 화면의 압박 막대가 움직이고,
            # 플레이어가 '이 자리를 더 파면 되겠다'는 것을 눈으로 안다.
            tx = st["secret"]["text"]
            self.flinches.setdefault(suspect_id, {})
            self.flinches[suspect_id][tx] = self.flinches[suspect_id].get(tx, 0) + 1
            self.gauges[suspect_id]._add(6.0, "같은 자리를 다시 찔렸다")

        # P9) 이미 물었던 것인가 — 프롬프트에 얹을 지시를 만든다
        again = None
        mem = self.memory.get(suspect_id)
        if mem:
            form = ((c.get("persona") or {}).get("voice") or {}).get("form", "")
            try:
                again = mem.again_directive(question, form, c.get("name", ""))
            except Exception:
                again = None
        # ★실토(ADMIT)·붕괴(BREAK) 턴에는 끈다 (2026-08-28).
        #   실측 — 엔진은 실토를 판정했는데 대사는 「아까 말씀드렸던 거잖아요」로
        #   지난 답을 되풀이하고 끝났다. '또 물었다' 지시가 실토 지시를 덮은 것.
        #   털어놓는 자리에서는 되풀이 짜증이 설 자리가 없다.
        if st.get("stance") in ("ADMIT", "BREAK"):
            again = None

        # 5. 지시문 생성 (c["timeline"] 방어적 조회)
        c_timeline = c.get("timeline", {})
        mine_places = [self.places.get(c_timeline.get(sl), {}).get("name", "") for sl in self.s.get("time_slots", [])]
        # ★범인의 자리는 **거짓말한 자리**로 준다 (2026-08-28).
        #   timeline은 진짜 동선이다. 그대로 주면 범인이 지시문을 따르다
        #   범행 자리를 제 입으로 대게 된다. 그가 '댄' 자리는 lies의 자리다.
        for li in (c.get("lies") or []):
            fp = self.places.get(li.get("false_place"), {}).get("name")
            if fp:
                dslot = (self.s.get("death") or {}).get("time_slot")
                slots = self.s.get("time_slots", [])
                if dslot in slots:
                    mine_places[slots.index(dslot)] = fp
        mine_places = [p for p in dict.fromkeys(mine_places) if p]
        dir_text = stance_directive(st, c, mine_places)

        return {
            "suspect_id": suspect_id,
            "suspect_name": c["name"],
            "stance": st["stance"],
            "why": st["why"],
            # ★지시문 **전문**을 내보낸다 (2026-08-25).
            #   예전엔 미리보기 세 줄만 나갔고, 프롬프트를 만드는 쪽은 그걸 쓰지
            #   않았다. 그래서 엔진이 ADMIT을 내려도 모델은 그 사실을 모른 채
            #   회피만 했다 — 태도 기계와 대사가 통째로 끊겨 있었다.
            #   프롬프트를 만드는 쪽은 이 문자열을 **반드시** 이어 붙여야 한다.
            "directive": dir_text,
            # ★이번 턴에 **감췄어야 할 것** — 대사를 만든 뒤 코드가 검사할 재료다.
            #   2026-08-25: 이걸 안 내보내서 stance.leaked()가 늘 빈 목록을 보고
            #   None만 돌려줬다. 가드를 붙여 놓고도 **한 번도 걸리지 않았다.**
            #   프롬프트를 만드는 쪽은 답을 받은 뒤 반드시:
            #       reply, _ = stance.strip_leak(reply, st)
            "still_hidden": st.get("still_hidden") or [],
            "directive_preview": dir_text.split("\n")[1:4],
            "gauge_before": gauge_state["value"],
            "gauge_after": round(self.gauges[suspect_id].v, 1),
            "hud": self.gauges[suspect_id].hud(),
            "yielded_belonging": yielded_belonging,
            "belonging_match_reason": match_reason,
            "confronting_with": confronting_with,
            "turns_left": self.turns_left,
            "held_clues": list(self.held_clues),
            "applied_pressure": applied,
            # P9) 장기기억 — 프롬프트에 얹을 것들
            "memory_briefing": (mem.briefing() if mem else None),
            "asked_before": (mem.recall(question) if mem else None),
            "again_directive": again,
        }

    def known_text(self):
        """**플레이어가 지금까지 화면에서 본 것 전부**를 한 덩이 글로.

        ★2026-08-27. 이것이 없어서 구멍이 하나 있었다.
          아무것도 못 찾은 사람이 「항공권 얘기를 해 봅시다」라고 치면
          엔진은 그것을 정곡으로 쳤다. 세 번 물으면 비밀이 열렸다.
          그 낱말은 단서를 찾아야 알 수 있는 말인데, 찍어서 연 셈이다.
          **아는 말로만 찌를 수 있어야 한다.**

        여기 들어가는 것 — 손에 쥔 단서, 만난 사람의 알리바이와 공개 신분,
        지금까지 들은 답, 그리고 화면에 낭독된 나레이션.
        (수첩에 안 적힌 것, 안 만난 사람의 것은 들어가지 않는다)
        """
        if getattr(self, "_known_cache_at", None) == (len(self.held_clues), len(self.met),
                                                      self._answers_seen):
            return self._known_cache
        parts = []
        for cl in (self.s.get("clue_graph") or []):
            if cl.get("id") in self.held_clues:
                parts.append(str(cl.get("surface") or ""))
        for cid, c in self.cast.items():
            parts.append(str(c.get("public") or ""))
            if cid in self.met:
                parts.append(str(c.get("alibi_narration") or ""))
        parts.extend(self._heard)                       # 지금까지 들은 답
        ui = self.s.get("ui") or {}
        for pg in (ui.get("narration") or {}).get("pages", []):
            parts.append(str(pg.get("text") or ""))
        sn = (ui.get("story_narration") or {})
        for key in ("case_open", "crime_scene", "victim_card"):
            parts.append(str((sn.get(key) or {}).get("text") or ""))
        for node in (sn.get("suspect_intro") or {}).values():
            parts.append(str((node or {}).get("text") or ""))
        for node in (sn.get("event") or {}).values():
            parts.append(str((node or {}).get("text") or ""))
        for ev in (self.s.get("events") or []):
            if ev.get("_applied"):
                parts.append(str(ev.get("text") or "") + " " + str(ev.get("effect") or ""))
        self._known_cache = " ".join(parts)
        self._known_cache_at = (len(self.held_clues), len(self.met), self._answers_seen)
        return self._known_cache

    def remember(self, suspect_id, question, answer):
        """LLM이 실제로 뱉은 답을 기억에 적는다.
        엔진은 판단만 하고 문장은 밖에서 만들므로, 답이 나온 뒤 이걸 불러 줘야
        다음 턴에 '아까 말했잖아요'가 성립한다."""
        # 들은 답도 '아는 것'에 들어간다 — 남의 입에서 나온 말은 물어도 된다
        if answer:
            self._heard.append(str(answer))
            self._answers_seen += 1
        mem = self.memory.get(suspect_id)
        if not mem:
            return None
        try:
            mem.observe(question, answer, self.current_round)
            mem.save()
        except Exception:
            return None
        return mem.briefing()


    # ── 화면이 필요한 것 ──────────────────────────────────────────────
    #  ★UI에서 거꾸로 짠 부분이다 (2026-08-25).
    #    지금까지는 프론트가 search·interrogate의 반환값을 조각조각 모아
    #    HUD와 수첩을 스스로 짜맞춰야 했다. 화면 하나 그리는 데 호출이 여러 번
    #    필요하면 반드시 어긋난다. 한 번에 다 준다.

    _KIND = {"crime_scene": "사건 시작 시 공개", "spine": "{r}라운드에 공개",
             "location": "{place}에서 발견", "record": "{place}에서 발견",
             "physical": "{place}에서 발견", "belongings": "{who}이(가) 내놓음"}

    def _roles(self):
        """직책 → 그 직책인 사람. **공개 신분에서만** 뽑는다.

        ★2026-08-27, 자동 플레이 여섯 판에서 여섯 명 모두 엉뚱한 사람을 짚었다.
          까닭이 뚜렷했다 — 결정타는 임자를 **직책**으로만 가리키는데
          ('사물함 열쇠는 홍보부장 것 하나뿐이다') 미끼는 **이름**으로 가리킨다
          ('좋아하는 향: 니코틴(유가람)'). 이름이 적힌 쪽이 이길 수밖에 없다.
          직책과 이름의 짝은 [용의자] 화면에 공개되어 있는 것이므로,
          수첩에 곁들여도 **아무것도 흘리지 않는다.** 사람이 화면을 오가며
          하는 일을 수첩이 대신해 줄 뿐이다.
        """
        if getattr(self, "_roles_cache", None) is not None:
            return self._roles_cache
        out = {}
        for c in self.cast.values():
            pub = str(c.get("public") or "") or str((c.get("profile") or {}).get("status") or "")
            head = re.split(r"[—,·(]", pub)[0].strip()
            for w in re.findall(r"[가-힣]{2,}", head):
                if len(w) >= 2:
                    out.setdefault(w, []).append(c["name"])
        self._roles_cache = out
        return out

    def _record(self, clue_id, how, where=None, who=None):
        """단서를 **수첩에 적는다.** 얻는 모든 길에서 이걸 부른다.

        ★적는 것은 **본문뿐**이다. 이 단서가 누구를 가리키는지(points_to),
          무엇을 뜻하는지(implies)는 절대 넣지 않는다 — 그건 플레이어가 할 몫이다.
          그래서 플레이어는 단서를 다시 보려고 그 장소에 또 들어갈 필요가 없다.
        """
        cl = self.clue_graph.get(clue_id) or {}
        if not cl or any(e.get("id") == clue_id for e in self.notebook):
            return None
        # ★수첩에 **이름**을 함께 적는다 (2026-08-31, 팀원 제보 —
        #   "대질 단서 사건수첩에 들어갈 때 이름 이상해").
        #   여태 항목에는 id와 본문뿐이라, 화면이 제목 자리에 id("B5")나
        #   본문 첫 줄을 잘라 넣고 있었다. 심문·대질로 얻은 것은 clue_cards 에
        #   카드가 없어서 더 그랬다 — 그럴 때는 **누구에게서 나왔는지**로 짓는다.
        card = next((c for c in (self.s.get("ui", {}).get("clue_cards") or [])
                     if c.get("id") == clue_id), None)
        name = (card or {}).get("name")
        if not name:
            if who and "실토" in str(how):
                name = f"{who}의 실토"
            elif who:
                name = f"{who}의 말"
            elif where:
                name = f"{where}에서 나온 것"
            else:
                name = cl.get("medium") or clue_id
        entry = {
            "id": clue_id,
            "name": name,                          # 화면 제목은 이것을 쓴다
            "round": self.current_round,
            "surface": cl.get("surface", ""),      # 본문 그대로
            "medium": cl.get("medium", ""),
            "how": how,                            # 어떻게 얻었나
            "where": where, "who": who,
            "decisive": bool(cl.get("decisive")),
            "memo": "",                            # 플레이어가 직접 쓴다 — 추리는 여기만
        }
        # 본문에 직책이 나오면 **그 직책이 누구인지**만 곁들인다(공개 정보다).
        surf = entry["surface"]
        gloss = {}
        for role, names in self._roles().items():
            if role and role in surf:
                gloss[role] = names if len(names) > 1 else names[0]
        if gloss:
            entry["roles"] = gloss
        self.notebook.append(entry)
        return entry

    def meet(self, suspect_id):
        """인물을 **처음 만났을 때** 알리바이를 듣는다. 예산 0, 한 번뿐.

        두 번째부터는 already=True로 돌려주고 아무것도 쓰지 않는다.
        프론트는 심문 화면에 들어설 때마다 이걸 부르면 된다.
        """
        c = self.cast.get(suspect_id)
        if not c:
            return {"error": f"존재하지 않는 용의자 ID: {suspect_id}"}
        first = suspect_id not in self.met
        self.met.add(suspect_id)
        return {"suspect_id": suspect_id, "suspect_name": c["name"],
                "first_meet": first, "already": not first, "cost": 0,
                "alibi": (c.get("alibi_narration") or "").strip(),
                "note": "첫 대면에만 말풍선으로 띄운다. [용의자] 화면에는 늘 남아 있다."}

    def state(self):
        """지금 화면에 그려야 할 것 **전부**. 호출은 이것 하나로 끝난다."""
        ev_rounds = [e.get("round") for e in (self.s.get("events") or []) if e.get("round")]
        focus = ((self.s.get("ui") or {}).get("hud") or {}).get("copy", {}).get("round_focus") or []
        return {
            "round": self.current_round, "max_rounds": self.max_rounds,
            "turns_left": self.turns_left,
            "budget": self.s.get("config", {}).get("turns_per_round", 8),
            "round_focus": (focus[self.current_round - 1]
                            if self.current_round - 1 < len(focus) else ""),
            "can_next_round": self.current_round < self.max_rounds,
            "is_last_round": self.current_round >= self.max_rounds,
            # 대질 — 잠겼는지, 왜 잠겼는지, 몇 번 남았는지
            "confront": {
                "unlocked": self.current_round >= self.confront_unlock_round,
                "tokens_left": self.confront_tokens,
                "unlock_round": self.confront_unlock_round,
                "locked_reason": ("사람을 맞대 놓으려면 판이 한 번 뒤집혀야 한다."
                                  if self.current_round < self.confront_unlock_round else None),
                # ★대질도 행동 하나를 쓴다(2026-08-29). 안내 문구가 옛말로 남아 있었다.
                #   화면이 「행동 1」을 그릴 수 있게 숫자로도 준다.
                "cost_note": "행동 하나를 쓴다. 한 판에 한 번뿐이다.",
                "cost": 1,
            },
            "event_rounds": ev_rounds,
            # ★이번 라운드에 **아직 못 찾은 장소 단서가 몇 장 남았는가** (2026-08-27).
            #   실측 — 판정자가 스물두 번을 뒤지고 심문은 두 번 했다. 방이 비었는지
            #   알 길이 없으니 계속 뒤진 것이다. 라운드 배너는 이미 "새로 드러나는 것이
            #   N가지"라고 알려 주고 있으니, 그중 몇이 남았는지도 알려 주는 것이 맞다.
            "findable_left": sum(
                1 for cl in (self.s.get("clue_graph") or [])
                if (cl.get("reveal_round") or 1) <= self.current_round
                and cl.get("channel") in ("location", "record", "physical")
                and cl.get("id") not in self.held_clues),
            # 인물 — 만났나, 알리바이, 공개된 비밀
            "cast": [{
                "id": cid, "name": c["name"], "public": c.get("public", ""),
                "met": cid in self.met,
                "alibi": (c.get("alibi_narration") or "").strip() if cid in self.met else None,
                "secrets_open": sorted(self.disclosed_secrets.get(cid, set())),
                "pressure": round(self.gauges[cid].v, 1),
            } for cid, c in self.cast.items()],
            # 수첩 — 적힌 것 그대로
            "notebook": list(self.notebook),
            "held_clues": sorted(self.held_clues),
            "combos_done": sorted(getattr(self, "done_combos", set())),
        }

    def apply_event(self, rnd=None):
        """이번 라운드의 이벤트를 **실제로 적용한다.**

        ★2026-08-26. events[].effect 에 "C3의 비밀 단서가 즉시 공개되고, 그 인물의
          압박이 한 단계 오른다"라고 적어 놓고, 정작 코드는 그 문장을 화면에
          띄우기만 했다. 실제 플레이에서 이벤트가 터진 뒤에도 임세준의 비밀은
          그대로 닫혀 있었고, 엔딩에서 "끝까지 안 물으시더군요" 소리를 들었다.
          **써 놓은 효과는 일어나야 한다.**
        """
        import re as _re
        rnd = rnd or self.current_round
        out = []
        for ev in (self.s.get("events") or []):
            if ev.get("round") != rnd or ev.get("_applied"):
                continue
            ev["_applied"] = True
            eff = str(ev.get("effect") or "") + " " + str(ev.get("text") or "")
            ids = [x for x in _re.findall(r"C\d+", eff) if x in self.cast]
            if not ids:                      # 이름으로 적혀 있을 수도 있다
                ids = [cid for cid, c in self.cast.items() if c["name"] in eff]
            done = {"event": ev.get("name"), "cast": [], "clues": [], "secrets": []}
            for cid in ids:
                c = self.cast[cid]
                done["cast"].append(cid)
                # ① 감추던 것이 남의 입에서 먼저 나온다 — 비밀 하나가 열린다
                if "비밀" in eff or "공개" in eff:
                    sec = next((x for x in (c.get("secrets") or [])
                                if x.get("text")
                                and x["text"] not in self.disclosed_secrets[cid]), None)
                    if sec:
                        self.disclosed_secrets[cid].add(sec["text"])
                        done["secrets"].append(sec["text"])
                        # 그 비밀을 여는 단서도 함께 손에 들어온다 — '단서가 공개된다'
                        for k in (sec.get("forced_by") or []):
                            if k not in self.held_clues and any(
                                    cl.get("id") == k for cl in self.s.get("clue_graph") or []):
                                self.held_clues.add(k)
                                self._record(k, "이벤트 — 남의 입에서", who=c["name"])
                                done["clues"].append(k)
                # ② 압박이 한 단계 오른다
                if "압박" in eff or "동요" in eff:
                    self.gauges[cid]._add(15.0, f"이벤트 — {ev.get('name','판이 뒤집혔다')}")
            out.append(done)
        return out

    def next_round(self):
        """라운드를 넘긴다. 원본 엔진엔 없어서 실험용으로 넣었다 —
        round_min이 걸린 조합·대질을 시험하려면 라운드를 올릴 수단이 필요하다."""
        if self.current_round >= self.max_rounds:
            return {"error": f"마지막 라운드입니다 ({self.max_rounds})."}
        self.current_round += 1
        self.turns_left = self.s.get("config", {}).get("turns_per_round", 12)
        # ★라운드를 넘긴다고 단서를 다 주면 안 된다.
        #   처음엔 그 라운드 단서를 전부 지급했더니, 아무것도 안 하고 라운드만 넘겨도
        #   결정타까지 손에 들어와 "탐색만/소거파"가 확신을 갖고 적중했다(policy_play 적발).
        #   저절로 오는 것은 **증언(spine)**뿐이다.
        #   장소 단서(location/record/physical)는 search()로 직접 찾아야 한다.
        given, findable = [], []
        for cl in self.s.get("clue_graph", []):
            if cl.get("reveal_round") != self.current_round:
                continue
            if cl.get("channel") in ("spine", "crime_scene"):
                self.held_clues.add(cl["id"]); given.append(cl["id"])
                self._record(cl["id"], f"{self.current_round}라운드 자동 공개")
            else:
                findable.append(cl["id"])
        return {"round": self.current_round, "turns_left": self.turns_left,
                "given": given,            # 저절로 들어온 증언
                "findable": findable,      # 이제 찾을 수 있게 된 것(직접 뒤져야 한다)
                "newly_opened": given + findable}

    def confront(self, target_id, witness_id, question, evidence_shown=False):
        """대질 심문 커맨드 (/confront) — 1회 한정 및 트랜잭션 안전성 보장"""
        # P8) 이벤트가 터지기 전에는 대질 화면 자체가 잠겨 있다
        if self.current_round < self.confront_unlock_round:
            return {"error": "아직 맞대 놓을 수 없습니다 — 판이 한 번 뒤집혀야 합니다.",
                    "locked": True,
                    "unlock_round": self.confront_unlock_round}
        if self.confront_tokens <= 0:
            return {"error": "대질 심문은 게임 중 1회만 사용할 수 있습니다 (기회 소진)."}
        if target_id not in self.cast or witness_id not in self.cast:
            return {"error": "유효하지 않은 용의자 ID입니다."}
        if target_id == witness_id:
            return {"error": "동일 인물과는 대질 심문을 할 수 없습니다."}
        
        # ★대질도 행동 하나를 쓴다 (2026-08-29, 제보 — "대질도 턴에 넣자").
        #   전에는 예산 밖에 두었다. 한 판 1회 토큰이 곧 값이라 여겼기 때문이다.
        #   그러나 공짜인 행동은 **언제 쓸지 고민할 거리가 없다** — 끝나기 전에 아무 때나
        #   한 번 누르면 그만이다. 값을 매기면 「지금 맞세울까, 한 번 더 물을까」가 생긴다.
        #   1회 한정은 그대로다. 예산이 없으면 아예 못 연다.
        if self.turns_left < 1:
            return {"error": "이 라운드에 남은 행동이 없습니다.", "out_of_budget": True}
        self.confront_tokens -= 1
        res = self.interrogate(target_id, question, evidence_shown=evidence_shown,
                               confronting_with=witness_id, free=False)
        
        # 혹시 모를 내부 에러 발생 시 토큰 롤백
        if "error" in res:
            self.confront_tokens += 1
            return res
            
        # P3) 이 두 사람에게 준비된 대질 대사가 있으면 함께 돌려준다.
        #     없으면 즉흥 대질 — hidden_from 기반 FLINCH만 난다.
        cx = self.cx_pairs.get(tuple(sorted([target_id, witness_id])))
        if cx:
            res["cross_exam"] = {
                # ★한 질문에 둘이 주고받는 대본 — 대질의 본체(2026-08-25)
                "exchange": cx.get("exchange"),
                "beats": cx.get("beats"),
                "reveals": cx.get("reveals"),      # 이 대질로 무엇이 드러나는가
                "topic": cx.get("topic"),
                "conflict": cx.get("conflict"),        # 무엇이 어긋나는가
                "a_claim": cx.get("a_claim"),
                "b_claim": cx.get("b_claim"),
                "on_confront": cx.get("on_confront"),  # 양쪽 실토 대사
                "reward": cx.get("reward"),
                "kind": cx.get("kind"),
                "surfaced_by": cx.get("surfaced_by"),
            }
            # ★플레이어가 **무엇을 물었는지**가 반영된다 (2026-08-25).
            #   전에는 무엇을 묻든 같은 대본이 나왔다. 질문이 대질의 결을 정해야 한다.
            #   묻는 결에 따라 두 사람이 여는 말과 마무리가 달라진다.
            q = str(question or "")
            if any(w in q for w in ("어디", "그 시각", "있었", "자리")):
                angle = "알리바이"
            elif any(w in q for w in ("사이", "관계", "아는", "어떤 사람")):
                angle = "관계"
            elif any(w in q for w in ("봤", "보았", "목격", "들었")):
                angle = "목격"
            else:
                angle = "그날 밤"
            res["cross_exam"]["asked"] = q
            res["cross_exam"]["angle"] = angle
            res["cross_exam"]["opening"] = {
                "알리바이": f"판정자가 그 시각의 자리를 묻는다. 두 사람이 서로를 본다.",
                "관계": f"판정자가 두 사람 사이를 묻는다. 한쪽이 먼저 눈을 피한다.",
                "목격": f"판정자가 본 것을 묻는다. 한쪽이 먼저 입을 뗀다.",
                "그날 밤": f"판정자가 그 밤을 묻는다. 둘 다 잠시 말이 없다.",
            }[angle]

            # 드러난 것을 세션 상태에 반영한다
            rv = cx.get("reveals") or {}
            if rv.get("kind") == "relation":
                for r in (self.s.get("relation_web") or []):
                    if {r.get("a"), r.get("b")} == set(rv.get("between") or []):
                        r["public"] = True          # 수첩에 관계가 적힌다
            for l in (cx.get("exchange") or []):
                if l.get("beat") == "실토":
                    self.disclosed_secrets.setdefault(l["cast_id"], set()).add(l["line"])

            # ★대질에서 **새 단서가 나온다** (2026-08-25).
            #   전에는 대본만 재생되고 손에 남는 것이 없었다. 한 판에 한 번뿐인
            #   행동인데 얻는 것이 없으면 쓸 까닭이 없다.
            #   적히는 것은 **어긋남이라는 사실**이지 그 해석이 아니다.
            an, bn = self.cast[target_id]["name"], self.cast[witness_id]["name"]
            cxid = f"CX_{min(target_id, witness_id)}_{max(target_id, witness_id)}"
            if cxid not in self.held_clues:
                self.held_clues.add(cxid)
                # ★대질도 **추리에 값을 보태야 한다** (2026-08-27).
                #   전에는 이 단서가 누구를 가리키는지 비어 있어, 한 판에 한 번뿐인
                #   행동을 써도 지목에는 한 톨도 반영되지 않았다.
                #   알리바이가 어긋난 자리에서는 **거짓을 말한 쪽**을 가리킨다.
                aims = None
                _txt = f"{cx.get('conflict') or ''} {rv.get('note') or ''} {cx.get('topic') or ''}"
                if any(w in _txt for w in ("자리", "시각", "알리바이", "어긋", "그 시간", "있었")):
                    # 자리가 어긋난 자리에서는 **거짓을 말한 쪽**을 가리킨다.
                    #   관계나 비밀이 드러난 대질은 사람을 가리키지 않는다 — 그건 이야기다.
                    for who_ in (target_id, witness_id):
                        if (self.cast[who_].get("lies") or []):
                            aims = who_
                            break
                self.clue_graph[cxid] = {
                    "id": cxid, "channel": "cross_exam", "medium": "대질",
                    "surface": (f"{an}{_josa(an,'과/와')} {bn}{_josa(bn,'을/를')} 맞대 놓은 자리에서 나온 것 — "
                                f"{cx.get('conflict') or (rv.get('note') or '')}"),
                    "weight": "testimony", "decisive": False,
                    "points_to": aims,
                    "reveal_round": self.current_round,
                }
                self.notebook.append({
                    "id": cxid, "round": self.current_round,
                    "surface": self.clue_graph[cxid]["surface"],
                    "medium": "대질", "how": f"{an} ↔ {bn} 대질",
                    "where": None, "who": None, "decisive": False, "memo": "",
                })
                res["cross_exam"]["gained_clue"] = self.clue_graph[cxid]
            res["is_curated_pair"] = True
        else:
            # ★준비된 쌍이 아니어도 **빈손으로 돌려보내지 않는다** (2026-08-25).
            #   91편은 열 쌍 가운데 다섯만 대본이 있었다. 한 판에 한 번뿐인 행동인데
            #   짝을 잘못 고르면 아무것도 못 얻고 끝났다.
            #   대본이 없으면 **두 사람의 알리바이를 맞대 놓는다** — 둘 다 이미
            #   말한 사실이므로 지어내는 것이 없고, 고른 짝마다 내용이 달라진다.
            A, B = self.cast[target_id], self.cast[witness_id]
            an, bn = A["name"], B["name"]
            dslot = (self.s.get("death") or {}).get("time_slot", "그 시각")
            pa = (A.get("timeline") or {}).get(dslot)
            pb = (B.get("timeline") or {}).get(dslot)
            pan = self.places.get(pa, {}).get("name", "?")
            pbn = self.places.get(pb, {}).get("name", "?")
            same = pa and pb and pa == pb

            if same:
                conflict = (f"{an}{_josa(an,'과/와')} {bn}{_josa(bn,'이/가')} "
                            f"{dslot}에 같은 자리({pan})를 댔다. "
                            f"그렇다면 서로를 보았어야 한다.")
                ex = [
                    {"beat": "진술", "name": an, "cast_id": target_id,
                     "line": (A.get("alibi_narration") or "").strip(),
                     "tone": "또박또박"},
                    {"beat": "겹침", "name": bn, "cast_id": witness_id,
                     "line": (B.get("alibi_narration") or "").strip(),
                     "tone": "같은 자리를 댄다. 둘 다 표정이 굳는다"},
                    {"beat": "깨달음", "name": an, "cast_id": target_id,
                     "line": f"…{pan}에 있었다면, 우리는 서로를 봤어야 합니다.",
                     "tone": "천천히. 스스로 말하면서 알아차린다"},
                    {"beat": "함구", "name": bn, "cast_id": witness_id,
                     "line": "더 드릴 말씀이 없습니다.",
                     "tone": "입을 닫는다"},
                ]
                note = (f"두 사람이 {dslot}에 같은 자리를 댔다. "
                        f"서로를 보았다는 말은 어느 쪽도 하지 않는다.")
            else:
                conflict = (f"{an}{_josa(an,'은/는')} {pan}, {bn}{_josa(bn,'은/는')} {pbn}. "
                            f"{dslot}에 서로 다른 자리에 있었다. "
                            f"둘 중 누구도 상대를 보증하지 못한다.")
                ex = [
                    {"beat": "진술", "name": an, "cast_id": target_id,
                     "line": (A.get("alibi_narration") or "").strip(),
                     "tone": "또박또박"},
                    {"beat": "대조", "name": bn, "cast_id": witness_id,
                     "line": (B.get("alibi_narration") or "").strip(),
                     "tone": "다른 자리를 댄다"},
                    {"beat": "여지", "name": an, "cast_id": target_id,
                     "line": f"{bn}{_josa(bn,'이/가')} {pbn}에 있었는지는 제가 알 수 없습니다.",
                     "tone": "선을 긋는다"},
                    {"beat": "여지", "name": bn, "cast_id": witness_id,
                     "line": f"저도 {an}{_josa(an,'을/를')} 보지 못했습니다.",
                     "tone": "같은 말을 되돌려준다"},
                ]
                note = (f"두 사람은 {dslot}에 다른 자리에 있었다. "
                        f"서로의 알리바이를 받쳐 주지 못한다.")

            res["cross_exam"] = {
                "exchange": ex,
                "beats": [x["beat"] for x in ex],
                "kind": "alibi_compare",
                "topic": f"{dslot}의 자리",
                "conflict": conflict,
                "a_claim": (A.get("alibi_narration") or "").strip(),
                "b_claim": (B.get("alibi_narration") or "").strip(),
                "reveals": {"kind": "alibi_compare",
                            "between": [target_id, witness_id], "note": note},
                "asked": str(question or ""),
                "improvised": True,
                "note": "대본이 없는 짝 — 두 사람이 이미 말한 알리바이를 맞대 놓는다.",
            }
            cxid = f"CX_{min(target_id, witness_id)}_{max(target_id, witness_id)}"
            if cxid not in self.held_clues:
                self.held_clues.add(cxid)
                # 대본 없는 짝도 마찬가지 — 알리바이가 어긋나면 거짓말한 쪽을 가리킨다
                aims2 = next((w for w in (target_id, witness_id)
                              if (self.cast[w].get("lies") or [])), None)
                self.clue_graph[cxid] = {
                    "id": cxid, "channel": "cross_exam", "medium": "대질",
                    "surface": (f"{an}{_josa(an,'과/와')} {bn}{_josa(bn,'을/를')} 맞대 놓은 자리에서 나온 것 — {conflict}"),
                    "weight": "testimony", "decisive": False,
                    "points_to": aims2,
                    "reveal_round": self.current_round,
                }
                self.notebook.append({
                    "id": cxid, "round": self.current_round,
                    "surface": self.clue_graph[cxid]["surface"],
                    "medium": "대질", "how": f"{an} ↔ {bn} 대질",
                    "where": None, "who": None, "decisive": False, "memo": "",
                })
                res["cross_exam"]["gained_clue"] = self.clue_graph[cxid]
            res["is_curated_pair"] = False
        res["confront_tokens_left"] = self.confront_tokens
        return res

    def combine(self, clue1, clue2):
        """복합 단서 조합 커맨드 (/combine)"""
        pair = tuple(sorted([clue1, clue2]))
        if clue1 not in self.held_clues or clue2 not in self.held_clues:
            missing = [c for c in (clue1, clue2) if c not in self.held_clues]
            return {"error": f"보유하지 않은 단서는 조합할 수 없습니다: {missing}"}

        if pair in self.composite_clues:
            comp = self.composite_clues[pair]
            # P7) 아직 이른 조합은 막는다 — 시나리오가 라운드를 정해 뒀다
            if comp.get("round_min", 1) > self.current_round:
                return {"success": False,
                        "message": "아직 이 둘을 잇기엔 아는 것이 부족하다.",
                        "round_min": comp["round_min"]}
            already = comp["id"] in self.held_clues
            self.held_clues.add(comp["id"])
            if not already:
                # 조합으로 나온 것도 수첩에 남는다 — clue_graph에 없으므로 직접 넣는다
                if not any(e.get("id") == comp["id"] for e in self.notebook):
                    def _nm(cid):
                        c = next((x for x in (self.s.get("ui", {}).get("clue_cards") or [])
                                  if x.get("id") == cid), None)
                        return (c or {}).get("name") or cid
                    self.notebook.append({
                        "id": comp["id"],
                        "name": comp.get("name") or "겹쳐 본 것",   # 화면 제목
                        "round": self.current_round,
                        "surface": comp.get("surface", ""), "medium": "조합",
                        # ★id 가 아니라 이름으로 적는다 — 「K1 + K3」은 사람 말이 아니다
                        "how": f"「{_nm(clue1)}」와 「{_nm(clue2)}」를 겹쳐 얻음",
                        "where": None, "who": None,
                        "decisive": bool(comp.get("decisive")), "memo": "",
                    })
            return {
                "success": True,
                "composite_id": comp["id"],
                "name": comp["name"],
                "surface": comp["surface"],
                "implies": comp["implies"],
                "weight": comp.get("weight", "context"),
                "decisive": comp.get("decisive", False),
                "points_to": comp.get("points_to"),
                # 이미 이어 본 조합은 점수를 다시 주지 않는다(실험 중 같은 조합이
                # 라운드마다 되풀이 성공하며 점수가 중복 적립됐다)
                "points": 0 if already else comp.get("points", 0),
                "already_done": already,
                "source": comp.get("source", "belongings")
            }
        else:
            return {"success": False, "message": f"{clue1}와 {clue2} 사이에는 유의미한 조합 관계가 없습니다."}

    def search(self, place_id, action_index=None):
        """장소 조사 (/search) — **1차 탐색**.

        원본 엔진에는 이게 없었다. `/inspect`는 2차 정밀 감식이고,
        정작 단서를 처음 손에 넣는 경로(장소를 뒤져 선택지를 고르는 것)가 빠져 있었다.
        시나리오는 `ui.place_screens[].rounds[R].actions[]`에 그 선택지를 갖고 있다 —
        선택지마다 `finds`(찾게 되는 단서 id)와 `result_lines`(보여 줄 글)가 붙어 있다.

        action_index를 안 주면 그 라운드에 **아직 안 찾은 것**을 하나 찾는다.
        """
        ps = next((x for x in (self.s.get("ui", {}).get("place_screens") or [])
                   if x.get("place_id") == place_id), None)
        if not ps:
            return {"error": f"그런 장소가 없습니다: {place_id}"}
        # ★장소 조사도 **행동 예산**을 쓴다 (2026-08-25 확정).
        #   config.action_budget: 탐색과 심문이 같은 주머니(라운드당 8)를 쓴다.
        #   "방을 더 뒤질까, 사람을 더 팔까"가 이 예산 위에서 결정된다.
        #   대질(1회 토큰)·감식(파생 행동)·조합(생각)은 예산 밖이다.
        if self.turns_left < 1:
            return {"error": "이 라운드에 남은 행동이 없습니다.", "out_of_budget": True}
        rd = (ps.get("rounds") or {}).get(str(self.current_round)) or {}
        acts = rd.get("actions") or []
        if not acts:
            return {"success": False, "message": "이 라운드에 여기서 볼 것은 없습니다."}

        # ★값은 **선택지가 아니라 장소**에 매긴다 (2026-08-25 개정).
        #   전에는 "책상 밑을 본다" 한 번이 사람에게 한 번 묻는 것과 같은 값이었다.
        #   같은 방에서 서랍을 열고 바닥을 보는 일이 각각 한 턴씩 드는 것은
        #   플레이어가 이해할 수 없는 셈이다. 그리고 헛수고 선택지가 예산을 먹으니
        #   방을 고르는 판단이 아니라 **어느 칸을 찍느냐**가 게임이 돼 버렸다.
        #       바뀐 것 — 한 장소를 그 라운드에 **처음 조사할 때만 1턴.**
        #                 그 라운드 동안 그 방은 다시 봐도 값이 들지 않고,
        #                 그 방에 그 라운드에 있는 단서는 **한꺼번에 다 나온다.**
        key = (place_id, self.current_round)
        first = key not in self.searched

        # 이 방·이 라운드에 있는 것을 전부 준다
        got, already = [], []
        for a in acts:
            cid = a.get("finds")
            if not cid:
                continue
            if cid in self.held_clues:
                already.append(cid)
                continue
            got.append(cid)

        # ★값은 **보는 데**가 아니라 **찾는 데** 든다 (2026-08-27).
        #   방은 여섯인데 그 라운드에 뭔가 있는 방은 셋뿐이다. 어느 셋인지 모르니
        #   여섯을 다 뒤지면 여덟 턴 가운데 여섯이 날아갔다 — 사람을 팔 겨를이 없다.
        #   그래서 실제 플레이가 '탐색 22 · 심문 2'로 굴러갔다.
        #   빈 방은 값을 매기지 않는다. 대신 그 라운드에는 다시 보아도 같다.
        #   이렇게 두면 여섯 방을 다 돌아도 **세 턴**이고, 나머지 다섯은 사람 몫이다.
        # ★빈 방도 값을 쓴다 (2026-08-29, 시연 제보 — "턴 10은 너무 많다, 지루하다").
        #   전에는 아무것도 안 나오는 방을 공짜로 두었다(방 여섯을 다 뒤져도 세 턴).
        #   그랬더니 **아무 대가 없이 전부 열어 보는 것이 최적해**가 되어, 고르는 재미가
        #   사라지고 클릭만 늘었다. 이제 그 라운드에 **처음 들어간 방**은 소득과 무관하게
        #   한 턴이다 — 어디를 뒤질지가 다시 판단이 된다.
        #   (같은 라운드에 그 방을 다시 보는 것은 여전히 공짜다.)
        if first:
            if self.turns_left < 1:
                return {"error": "이 라운드에 남은 행동이 없습니다.", "out_of_budget": True}
            self.turns_left -= 1
            self.searched.add(key)

        for cid in got:
            self.held_clues.add(cid)
            self._record(cid, "장소 탐색", where=ps.get("title"))

        # 화면에 띄울 연출은 선택지 단위로 남는다 — 값을 안 매길 뿐이다.
        #
        # ★누른 칸과 뜨는 글이 어긋나던 것을 고친다 (2026-08-29, 시연 제보).
        #   「낙서를 본다」를 눌렀더니 "딱히 특별한 건 없었다"가 떴는데 수첩에는
        #   단서가 들어와 있었다. 방 단위로 한꺼번에 찾는 구조라서, **찾은 것의 연출**과
        #   **누른 칸의 연출**이 서로 다른 데서 났기 때문이다. 이제 이렇게 준다 —
        #       pressed : 누른 칸
        #       shown   : 이번에 실제로 무언가 나온 칸들 (없으면 누른 칸)
        #   그래야 "눌렀다 → 이것이 나왔다"가 화면에서 한 줄로 이어진다.
        pressed = (acts[action_index]
                   if action_index is not None and 0 <= action_index < len(acts)
                   else None)
        yielded = [a for a in acts if a.get("finds") in got]
        shown = yielded or ([pressed] if pressed else acts)

        def _card(cid):
            cl = self.clue_graph.get(cid) or {}
            return {"id": cid, "surface": cl.get("surface"),
                    "weight": cl.get("weight"), "decisive": cl.get("decisive", False)}

        return {
            "success": True,
            "place": place_id, "place_name": ps.get("title"),
            "first_visit": first,
            "cost": 1 if first else 0,
            "actions": [{"label": a.get("label"),
                         "result_lines": a.get("result_lines", []),
                         "finds": a.get("finds")} for a in shown],
            "found_clues": got,                 # 이번에 새로 얻은 것
            "clues": [_card(c) for c in got],
            "already_had": already,
            "empty": not got and not already,
            # 옛 이름 — 호출부가 하나만 보던 시절과 맞춰 둔다
            "found_clue": got[0] if got else None,
            "clue": _card(got[0]) if got else None,
            "label": (shown[0].get("label") if shown else ""),
            "result_lines": (shown[0].get("result_lines", []) if shown else []),
            # 누른 칸이 무엇이었는지도 그대로 돌려준다 — 화면이 짚어 보일 수 있게
            "pressed_index": action_index,
            "pressed_label": (pressed or {}).get("label"),
            "turns_left": self.turns_left,
            "layer_note": rd.get("layer_note"),
        }

    def inspect(self, target_id):
        """2차 정밀 감식 커맨드 (/inspect) — **행동 예산 밖.**
        이미 찾은 것을 더 자세히 보는 파생 행동이라, 예산 안에 두면
        탐색·심문과 다투다 영영 안 쓰인다(예산 10 이하에서 실측 0회)."""
        if target_id in self.inspections:
            data = self.inspections[target_id]
            self.held_clues.add(data["clue_id"])
            return {
                "success": True,
                "target_name": data["target_name"],
                "report": data["result"],
                "new_clue": {
                    "id": data["clue_id"],
                    "name": data["clue_name"],
                    "surface": data["surface"]
                }
            }
        else:
            return {"success": False, "message": f"'{target_id}'에 대해서는 추가적인 정밀 감식 대상이 없습니다."}
