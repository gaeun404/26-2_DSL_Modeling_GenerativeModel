# -*- coding: utf-8 -*-
"""K_구운몽 → 35/35: 원작(구운몽) 서사 나레이션 + 다섯 용의자 소개 + 비밀 탐색 단서 보강."""
import json
from checklist import check

s=json.load(open("scenarios/K_구운몽.json",encoding="utf-8"))

# ── 원작을 실제로 들려주는 나레이션(성진의 꿈→양소유 부귀영화). 살인 시점=꿈에서 깨기 전(부귀 절정) ──
s["intro"]["original_summary"]=("육관대사의 제자 성진이 하룻밤 꿈에 인간 세상 양소유로 태어나, 무예와 글로 승상에 올라 "
    "두 부인과 여섯 낭자를 아내로 맞고 부귀영화를 누린 옛이야기. 그 화려한 꿈이 절정에 이른 취미궁에서 사건이 일어난다.")
s["intro"]["narration"]=[
  {"beat":1,"mood":"신비","focus":"world","scene":"연화도량에서 잠든 젊은 중","text":"옛날 옛적, 육관대사의 제자 성진이 하룻밤 꿈에 인간 세상 양소유로 태어났단다."},
  {"beat":2,"mood":"평온","focus":"world","scene":"과거에 급제해 승상에 오르는 양소유","text":"그는 무예와 글로 입신하여 마침내 대승상에 올랐고, 부귀가 그의 저택 취미궁에 가득 찼단다."},
  {"beat":3,"mood":"화사","focus":"world","scene":"두 부인과 여섯 낭자가 어우러진 규방","text":"양소유는 두 부인과 여섯 낭자를 아내로 맞아, 비단과 가무 속에 더없는 영화를 누렸지."},
  {"beat":4,"mood":"의미심장","focus":"C1","scene":"가면을 든 예인 낭자","text":"그중 가무와 연희를 맡은 낭자 능파는 누구로든 변하는 재주가 있었으나, 옛 시절 하나를 깊이 감추고 있었단다."},
  {"beat":5,"mood":"의미심장","focus":"C2","scene":"규방 살림을 쥔 시비 우두머리","text":"규방 살림을 도맡은 시비 우두머리 춘섬은 절뚝이는 걸음과 쥐색 배자가 표였고, 병든 노모를 봉양하느라 늘 쪼들렸지."},
  {"beat":6,"mood":"고요","focus":"C3","scene":"규방의 질서를 다스리는 정부인","text":"정부인은 규방의 위계를 엄히 다스렸고, 방자한 새 사람을 못마땅해했단다."},
  {"beat":7,"mood":"의미심장","focus":"C4","scene":"곳간 열쇠를 쥔 청지기","text":"청지기 곽집사는 곳간과 드나듦을 지켰으나, 어긋난 물목 셈이 그의 뒷목을 눌렀지."},
  {"beat":8,"mood":"불안","focus":"C5","scene":"약을 다루는 의녀","text":"의녀 난영은 규방의 병을 살폈단다. 독과 약을 아는 손이라, 사람들은 그녀를 조금 두려워했지."},
  {"beat":9,"mood":"애잔","focus":"victim","scene":"총애를 독차지한 젊은 첩","text":"그 무렵 새로 든 젊은 첩 소랑이 승상의 총애를 독차지하니, 규방의 웃음 아래 시샘이 조용히 고였단다."},
  {"beat":10,"mood":"충격","focus":"victim","scene":"백옥 문진 곁에 쓰러진 소랑","text":"부귀의 꿈이 절정에 이른 어느 밤, 소랑이 제 처소에서 백옥 문진 곁에 쓰러져 발견된다. 꿈에서 깨기도 전에, 화려한 이야기는 여기서 끝난다."}
]

# ── 비밀 탐색 단서 보강: 각 용의자 소유 장소에 그의 비밀을 드러내는 location 단서 ──
have={cl["id"] for cl in s["clue_graph"]}
add=[
 {"id":"S1","channel":"location","medium":"물건","location":"P2",
  "surface":"능파 별당 분장함 밑에서 나온 옛 기적(妓籍) 문서와 천기 시절의 낡은 노리개.",
  "implies":"C1(능파)의 비밀=천기였던 과거. 살인과 무관(레드헤링).",
  "weight":"red_herring","points_to":None,"exculpates":[],"reveal_round":2,"decisive":False},
 {"id":"S2","channel":"location","medium":"서찰","location":"P1",
  "surface":"소랑 처소 정리 장부 갈피에서 나온, 춘섬이 삯을 떼어 병든 노모께 부친 서찰.",
  "implies":"C2(춘섬)의 비밀=노모께 보낸 규방 재물. 살인과 무관(레드헤링).",
  "weight":"red_herring","points_to":None,"exculpates":[],"reveal_round":2,"decisive":False},
 {"id":"S3","channel":"location","medium":"문서","location":"P3",
  "surface":"정부인 처소 문갑에서 나온, 기운 친정을 규방 재물로 도운 셈 문서.",
  "implies":"C3(정부인)의 비밀=친정 재물유용. 살인과 무관(레드헤링).",
  "weight":"red_herring","points_to":None,"exculpates":[],"reveal_round":2,"decisive":False},
 {"id":"S5","channel":"location","medium":"문서","location":"P5",
  "surface":"의약방 약장 뒤에서 나온, 위험한 약재를 규방 밖으로 몰래 판 거래 문서.",
  "implies":"C5(난영)의 비밀=약재밀매. 살인과 무관(레드헤링).",
  "weight":"red_herring","points_to":None,"exculpates":[],"reveal_round":2,"decisive":False},
]
for cl in add:
    if cl["id"] not in have: s["clue_graph"].append(cl)

json.dump(s,open("scenarios/K_구운몽.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)

R,rate=check(s); npass=sum(1 for _,c,_ in R if c)
print(f"K_구운몽 재점검: {npass}/{len(R)}  정답률 {rate:.2f}")
for n,c,_ in R:
    if not c: print("  ❌", n)
