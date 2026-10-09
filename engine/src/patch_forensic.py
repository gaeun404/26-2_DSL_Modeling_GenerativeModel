# -*- coding: utf-8 -*-
"""플래그십 G/H 단서를 '검안서·감식 소견체'(구체 사실)로 재작성 — 소설투 제거, 메커니즘 강화."""
import json
from verify import verify, _print
from difficulty import difficulty_gate
from playtest import trace
from agent_lint import lint

def set_clue(s, cid, **kv):
    for cl in s["clue_graph"]:
        if cl["id"] == cid:
            cl.update(kv); return
def save_check(s, path, name):
    json.dump(s, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    ok=verify(s)[0]; gok=difficulty_gate(s)[0]; pok=trace(s,verbose=False)[0]; lok=lint(s)[0]
    print(f"  {name}: verify {ok} · 난이도 {gok} · 플레이 {pok} · 린트 {lok}")

# ===== G_전우치전 =====
g=json.load(open("scenarios/G_전우치전.json",encoding="utf-8"))
g["death"]["scene_inspection"]=[
  "【검안】 입술·조상(爪床) 청색증, 구강 내 검붉은 잔사. 두부·경부 외상 없음.",
  "【독물】 위 내용물 및 술잔 잔사에서 복어독 계열 양성. 사인: 급성 음독. 사망추정 亥時(밤).",
  "【현장】 술잔 2점 중 1점에만 잔사 검출 → 대작자 존재.",
  "【현장】 방문 빗장 안쪽에서 잠김, 옆방 통하는 미닫이 문틀에 최근 긁힘 — 그쪽 출입 흔적.",
]
set_clue(g,"K1",medium="검안서",
  surface="【검안 소견】 청색증·구강 잔사, 위 내용물 복어독 양성. 경부·두부 외상 전무. 사인: 급성 음독.",
  implies="사인은 음독(독). 흉기=짐주. 외상 없음 → 둔기·자상·교살 배제.")
set_clue(g,"K2",medium="현장기록",
  surface="【현장】 서안 위 유서 1매 '내 죄를 씻고자 이 잔을 든다'. 자획 정연해 언뜻 자필 유서로 보임.",
  implies="자살로 오도하는 정황(함정). 진위는 필적·지문 감정 전까지 미확정.")
set_clue(g,"K6",medium="감정서",
  surface="【필적·지문 감정】 유서 자획 습관(之·心)이 피해자 자필 표본과 불일치, 청지기 곽서방의 대필 서찰과 일치. 유서에서 피해자 지문 불검출. 서안 밑 동일 문구 연습지 3매.",
  implies="유서는 위조. 대필 이력·술상 접근을 겸한 곽서방만 가능. 오의원은 피해자 자필을 다뤄본 적 없어 위조 불가 → 배제.")
save_check(g,"scenarios/G_전우치전.json","G_전우치전")

# ===== H_홍길동전 =====
h=json.load(open("scenarios/H_홍길동전.json",encoding="utf-8"))
h["death"]["scene_inspection"]=[
  "【검안】 후두부 상투선 하방에 심부 자창 1개. 창구경 약 2mm(가는 침상 흉기). 두개 타박·표피박탈 없음.",
  "【사인】 경부 심부 자창에 의한 연수 손상·실혈. 즉시성 사망.",
  "【현장】 놋촛대 표면 혈흔은 도말양(닦아 묻힌 형태), 낙하·충격흔 없음 → 흉기 아님(위장).",
  "【현장】 방 안 실·바늘 냄새, 바닥 실밥 1올. 재물 반출 흔적 없음(도난 목적 아님).",
]
set_clue(h,"K1",medium="검안서",
  surface="【검안 소견】 사인은 둔기 아닌 후두부 2mm 심부 자창. 촛대엔 충격흔 없고 두개 타박 없음.",
  implies="흉기=가는 침상(은비녀). 촛대는 흉기가 아님.")
set_clue(h,"K2",medium="현장기록",
  surface="【현장】 피 묻은 놋촛대가 서안 옆에 넘어져 있어 언뜻 둔기 타살로 보임.",
  implies="둔기 살인으로 오인하게 만든 함정. 검안과 배치됨.")
set_clue(h,"K6",medium="감정서",
  surface="【창상·흉기 감정】 자창 심도·자입각이 침선용 은비녀와 일치, 급소 정타 — 바느질 숙련자의 정밀 수기. 촛대 혈흔은 사후 도말. 침선에 능한 이는 이 집에서 첩 난이뿐.",
  implies="가는 은비녀 정밀 자상은 침선 숙련자(난이)만 가능. 임객주는 둔기류만 다뤄 이 흉기 불가 → 배제.")
save_check(h,"scenarios/H_홍길동전.json","H_홍길동전")
