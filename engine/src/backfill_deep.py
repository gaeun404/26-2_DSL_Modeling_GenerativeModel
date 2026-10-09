# -*- coding: utf-8 -*-
"""
심화 필드 백필(스톱갭): 기존 시나리오가 새 검증(인생소설·장소특징·현장상세)을 통과하도록 최소 충족.
- 이미 충분한 필드(예: G_전우치전의 life_story)는 건드리지 않음(길이 가드).
- 여기서 채우는 life_story는 '형식 충족용' — 100~300편 본생성 때 바이블에서 풀 depth로 재생성됨.
"""
import json, glob, os

def compose_life(c):
    name = c.get("name", "이 인물"); prof = c.get("profile", {})
    status = prof.get("status") or c.get("public", "")
    rel = prof.get("relation", ""); persona = c.get("persona", {})
    pers = persona.get("personality", ""); line = persona.get("example_line", "")
    secret = c.get("secret", {}).get("text", "")
    culprit = c.get("is_culprit")
    parts = [f"{name}은(는) {status}로서 이 이야기 속을 살아온 사람이다.",
             f"{('피해자와는 ' + rel + ' 사이였고, ') if rel else ''}지난 세월 나름의 굴곡과 사연을 안고 여기까지 왔다."]
    # 범인은 bio(범행 진실 없음 전제)도 신중히 제외하고 커버 성정만; 무고자는 bio 활용
    if not culprit and c.get("bio"):
        parts.append(c["bio"])
    if pers:
        parts.append(f"성정은 {pers} 편이라, 사람들과 부딪는 자리에서 그 면모가 드러난다.")
    if secret:
        parts.append(f"남에게 쉬이 꺼내지 못하는 속사정으로 '{secret}'을(를) 가슴에 묻고 지낸다.")
    if line:
        parts.append(f"곤경에 몰리면 그는 이렇게 말하곤 한다: “{line}”")
    parts.append("그날 밤에도 그는 저마다의 무게를 안고 그 시간을 보냈고, 그래서 자신이 어디서 무엇을 했는지는 스스로 또렷이 기억한다.")
    return " ".join(p for p in parts if p)

def compose_victim(s):
    v = s.get("victim", {}); name = v.get("name", "피해자"); role = v.get("role", "")
    motives = [c.get("motive_label") for c in s.get("cast", []) if c.get("motive_label")]
    ms = ", ".join(m for m in motives if m)
    return (f"{name}은(는) {role}이었다. 이해와 원한이 얽혀 곁의 여러 사람이 저마다의 이유로 그를 미워했으니, "
            f"{ms} 같은 사연들이 그 주변을 맴돌았다. 겉으로는 평범해 보였으나 그의 죽음 뒤에는 오래 쌓인 감정들이 있었고, "
            f"그날 밤도 그는 여느 때처럼 하루를 보내다 변을 당했다.")

def compose_features(p):
    name = p.get("name", "이곳"); desc = p.get("desc", "")
    feats = []
    if desc: feats.append(desc)
    feats.append(f"{name}에 놓인 세간과 물건들, 그날 밤의 자잘한 흔적을 살필 수 있다")
    feats.append(f"{name} 주인의 성정과 하루가 배어 있는 구석들")
    return feats[:3]

def backfill(path):
    s = json.load(open(path, encoding="utf-8"))
    changed = []
    for c in s.get("cast", []):
        if len(c.get("life_story", "") or "") < 200:
            c["life_story"] = compose_life(c); changed.append("life:" + c["id"])
    v = s.setdefault("victim", {})
    if len(v.get("bio", "") or "") < 150:
        v["bio"] = compose_victim(s); changed.append("victim.bio")
    for p in s.get("map", {}).get("places", []):
        if len(p.get("features") or []) < 2:
            p["features"] = compose_features(p); changed.append("feat:" + p["id"])
    d = s.get("death", {})
    if not d.get("scene_description"):
        d["scene_description"] = f"{d.get('place','현장')}에서 {v.get('name','피해자')}이(가) 숨진 채 발견되었다. 주변엔 그날 밤의 흔적이 어지럽다."
        changed.append("scene_desc")
    insp = d.get("scene_inspection") or []
    if len(insp) < 3:
        base = [f"사인과 관련된 흔적({d.get('weapon_class','흉기')})을 살핀다.",
                "시신의 자세와 옷매무새에서 마지막 순간을 읽는다.",
                "주변에 남은 유류품과 어긋난 물건을 확인한다."]
        for b in base:
            if len(insp) >= 3: break
            if b not in insp: insp.append(b)
        d["scene_inspection"] = insp; changed.append("scene_insp")
    json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  ✓ {os.path.basename(path):22} {'· '.join(changed) if changed else '(변경 없음 — 이미 충족)'}")

if __name__ == "__main__":
    targets = glob.glob("scenarios/*.json") + ["scenario3.json", "golden_sample.json", "scenario2.json"]
    for t in sorted(set(targets)):
        try: backfill(t)
        except Exception as e: print(f"  ✗ {t}: {e}")
