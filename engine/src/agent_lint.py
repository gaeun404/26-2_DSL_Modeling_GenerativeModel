# -*- coding: utf-8 -*-
"""
자기오류 방지 린터(정적, API 불필요) — 용의자 AI 에이전트가 '정보 공백/자기모순'을
일으킬 소지를 스키마 단계에서 잡는다. (실시간 대화 자기오류는 stress_agent.py로 별도 검증)

검사:
  [정보충분성] life_story/bio/persona/timeline/pressure_points 존재·길이
  [범인은폐]   범인 life_story/bio에 범행 자백 어휘가 없는가
  [정합성]     alibi_narration이 timeline상 사망시각 장소와 어긋나지 않는가(범인 제외)
  [참조무결]   owner/points_to/exculpates/location/false_place가 실존 id/장소인가
  [연기재료]   pressure_points trigger/reveals, persona.example_line 등 채워졌는가
사용: python agent_lint.py "scenarios/*.json"
"""
import json, sys, glob

SEARCHABLE = ("location", "record", "physical")   # 뒤져야 나오는 채널(채널 분화 후)
CONFESS = ["살해", "죽였", "죽이려", "독을 탔", "독을 타", "목을 졸", "찔러 죽", "범행", "내가 죽", "죽인 것은 나"]

def lint(s):
    issues = []
    ids = {c["id"] for c in s["cast"]}
    places = {p["id"] for p in s.get("map",{}).get("places",[])}
    dslot = s.get("death",{}).get("time_slot"); dplace = s.get("death",{}).get("place")

    for p in s.get("map",{}).get("places",[]):
        # 주인 없는(숨은/공용) 장소는 허용. 다만 주인을 '지정했는데' 용의자가 아니면 오류.
        if p.get("owner") and p.get("owner") not in ids:
            issues.append(f"장소 {p['id']} owner '{p.get('owner')}' 불명")

    for c in s["cast"]:
        cid = c["id"]
        # 정보 충분성
        if len(c.get("life_story","") or "") < 200: issues.append(f"{cid} life_story 짧음")
        if not c.get("bio"): issues.append(f"{cid} bio 없음")
        if set((c.get("timeline") or {}).keys()) != set(s.get("time_slots",[])):
            issues.append(f"{cid} timeline 슬롯 누락")
        for slot, pid in (c.get("timeline") or {}).items():
            if pid not in places: issues.append(f"{cid} timeline 장소 '{pid}' 불명")
        # 연기 재료
        per = c.get("persona") or {}
        if not per.get("example_line"): issues.append(f"{cid} persona.example_line 없음")
        pps = c.get("pressure_points") or []
        if not pps: issues.append(f"{cid} pressure_points 없음")
        for pp in pps:
            if not pp.get("trigger") or not pp.get("reveals"):
                issues.append(f"{cid} pressure_point trigger/reveals 비어있음")
        # 범인 은폐
        if c.get("is_culprit"):
            blob = (c.get("life_story","") or "") + (c.get("bio","") or "")
            hit = [w for w in CONFESS if w in blob]
            if hit: issues.append(f"{cid}(범인) life_story/bio에 자백 어휘 {hit}")
            for l in (c.get("lies") or []):
                fp = l.get("false_place")
                if fp and fp not in places: issues.append(f"{cid} lies.false_place '{fp}' 불명")
        else:
            if c.get("lies"): issues.append(f"{cid}(무고) lies 보유(범인만 가능)")
            # 무고자 알리바이 진술 vs 동선 정합: 사망시각 현장 부재여야 결백 주장 성립
            if (c.get("timeline") or {}).get(dslot) == dplace and c.get("mmo",{}).get("opportunity") is False:
                issues.append(f"{cid} opportunity=false인데 사망시각 현장에 위치(모순)")

    # 참조 무결
    for cl in s.get("clue_graph",[]):
        pt = cl.get("points_to")
        if pt and pt not in ids: issues.append(f"단서 {cl.get('id')} points_to '{pt}' 불명")
        for e in (cl.get("exculpates") or []):
            if e not in ids: issues.append(f"단서 {cl.get('id')} exculpates '{e}' 불명")
        loc = cl.get("location")
        if loc and loc not in places: issues.append(f"단서 {cl.get('id')} location '{loc}' 불명")

    # 정답 정합
    sol = s.get("solution",{})
    if sol.get("weapon") not in (s.get("choices",{}).get("weapon") or []):
        issues.append("solution.weapon이 보기에 없음")
    return (len(issues) == 0), issues

def secret_lint(s):
    """각 용의자의 비밀이 (①장소 탐색 + ②심문 pressure_points) 양쪽으로 확인 가능한지."""
    issues=[]
    owner_place={p.get("owner"):p["id"] for p in s.get("map",{}).get("places",[])}
    loc_by_place={}
    for cl in s.get("clue_graph",[]):
        if cl.get("channel") in SEARCHABLE and cl.get("location"):
            loc_by_place.setdefault(cl["location"],[]).append(cl)
    for c in s["cast"]:
        cid=c["id"]
        pps=c.get("pressure_points") or []
        if not any(pp.get("trigger") and pp.get("reveals") for pp in pps):
            issues.append(f"{cid} 비밀 심문 경로(pressure_points) 없음")
        pl=owner_place.get(cid)
        if pl and not loc_by_place.get(pl):
            issues.append(f"{cid} 비밀 탐색 경로 없음(소유 장소 {pl}에 location 단서 부재)")
    return (len(issues)==0), issues

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"  # catalog.json 등 비시나리오 제외
    paths = glob.glob(arg)
    clean = 0
    for p in sorted(paths):
        try: ok, iss = lint(json.load(open(p, encoding="utf-8")))
        except Exception as e: ok, iss = False, [f"예외 {e}"]
        clean += ok
        if ok: print(f"  ✅ 정상  {p}")
        else:
            print(f"  ⚠️  {p}")
            for i in iss: print(f"       - {i}")
    print(f"\n총 {len(paths)}편 | 린트통과 {clean}편 ({round(100*clean/len(paths)) if paths else 0}%)")
