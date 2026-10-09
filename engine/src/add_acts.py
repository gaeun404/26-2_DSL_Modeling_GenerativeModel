# -*- coding: utf-8 -*-
"""
add_acts.py — 라운드별 행동 지침(act_directions) 주입.

배경: 받아둔 Jubensha 극본(05_player)의 구조를 보니, 각 인물에게 '막(act)마다'
      목표와 팁이 주어진다 — "너는 범인이니 이건 먼저 밝히지 마라",
      "네 동선은 누구와도 겹치지 않는다" 같은 식. (구조만 차용, 원문 미사용)

우리 문제: 에이전트가 라운드가 바뀌어도 같은 말을 반복함(대화 병목) + 감정 곡선이 없음.
해결: 인물별 × 라운드별로
      goal(이번 라운드 목표) / conceal(감출 것) / concede(내줘도 되는 것)
      / tone(연기·음성 지시) / if_pressed(몰릴 때 반응) 을 스키마에서 자동 생성.

s["cast"][i]["act_directions"] = [{round, goal, conceal[], concede[], tone, if_pressed}, ...]
사용: python add_acts.py
"""
import json, glob, sys

def dirs_for(s, c):
    rounds=s.get("config",{}).get("rounds",3)
    pn={p["id"]:p["name"] for p in s["map"]["places"]}
    ds=s["death"]["time_slot"]
    my=pn.get(c.get("timeline",{}).get(ds),"내 자리")
    sec=c.get("secret",{}).get("text","")
    trig=[t for pp in (c.get("pressure_points") or []) for t in pp.get("trigger",[])]
    cul=c.get("is_culprit")
    lie=(c.get("lies") or [{}])[0]
    fake=pn.get(lie.get("false_place"),"") if cul else ""
    out=[]
    for r in range(1, rounds+1):
        if cul:
            if r==1:
                out.append(dict(round=1,
                  goal=f"의심을 사지 않는 게 최우선. '{lie.get('claim', f'{fake}에 있었다')}'를 자연스럽게 깔아 둔다.",
                  conceal=[sec, "그 밤 실제 동선", "피해자와의 마지막 접촉"],
                  concede=["피해자를 미워한 사실은 인정해도 됨(다들 그러니까)"],
                  tone="평상시 말투 그대로. 여유 있게, 오히려 남 이야기를 먼저 꺼내 시선을 돌린다.",
                  if_pressed="화제를 다른 용의자의 수상한 점으로 돌린다."))
            elif r<rounds:
                out.append(dict(round=r,
                  goal="알리바이의 균열을 메운다. 먼저 말을 늘리지 말고 묻는 것만 답한다.",
                  conceal=[sec, "거짓 알리바이가 흔들린다는 자각"],
                  concede=[f"'{trig[0] if trig else '사소한 비밀'}'을 찔리면 비밀 일부는 내준다 — 단, 살인과 분리해서"],
                  tone="말이 조금 느려지고 사이가 길어진다. 목소리 톤은 낮게 눌린다.",
                  if_pressed="'그건 이 일과 상관없소'로 선을 긋고, 비밀은 인정하되 살인은 강하게 부인."))
            else:
                out.append(dict(round=rounds,
                  goal="끝까지 부인. 단, 결정적 물증을 구체적으로 들이대면 무너져도 된다(설계된 결말).",
                  conceal=["자백 — 물증 제시 전까지는 절대"],
                  concede=["물증이 정확히 제시되면 동기를 토로하며 자백"],
                  tone="호흡이 짧아지고 말끝이 흔들린다. 자백 순간엔 급격히 낮고 느리게.",
                  if_pressed="물증이 두루뭉술하면 반박, 정확하면 침묵 후 자백."))
        else:
            if r==1:
                out.append(dict(round=1,
                  goal=f"내 결백을 담담히 말한다. 그 밤 나는 {my}에 있었다.",
                  conceal=[sec],
                  concede=["피해자에 대한 원망은 솔직히 말해도 됨"],
                  tone="담담하게. 억울함을 과장하지 않는다.",
                  if_pressed="같은 사실을 되풀이하되 표현은 바꾼다(똑같은 문장 반복 금지)."))
            elif r<rounds:
                out.append(dict(round=r,
                  goal="내 비밀이 들킬까 조마조마하다. 살인과 무관함을 분리해 강조.",
                  conceal=[sec],
                  concede=[f"'{trig[0] if trig else '그 일'}'을 정확히 찔리면 비밀을 실토한다(정상 동작)"],
                  tone="말이 빨라지고 톤이 올라간다(억울함). 비밀을 찔리면 목소리가 순간 잦아든다.",
                  if_pressed="비밀은 인정하되 '그건 부끄러운 일이지 살인이 아니다'로 선을 긋는다."))
            else:
                out.append(dict(round=rounds,
                  goal="끝까지 결백을 주장. 증거를 들이대도 절대 자백하지 않는다(하지 않았으므로).",
                  conceal=[],
                  concede=["아는 사실은 다 내놓아 수사에 협조"],
                  tone="절박하고 또렷하게. 억울함이 목소리를 높인다.",
                  if_pressed="논리로 반박한다 — 내가 그럴 수단·기회가 없었음을 짚는다."))
    return out

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/[0-9]*.json"
    for p in sorted(glob.glob(arg)):
        s=json.load(open(p,encoding="utf-8"))
        for c in s["cast"]:
            c["act_directions"]=dirs_for(s,c)
        json.dump(s,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        n=len(s["cast"][0]["act_directions"])
        print(f"  🎬 {p.split('/')[-1]:26} 인물 {len(s['cast'])}명 × 라운드 {n} 행동지침 주입")
    print("\n라운드별 목표·감출것·내줄것·연기톤 주입 완료 (Jubensha 구조 차용, 원문 미사용)")
