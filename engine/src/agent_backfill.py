# -*- coding: utf-8 -*-
"""에이전트 정보 공백 백필: 린터가 잡은 bio/pressure_points/example_line 결손을 기존 필드에서 채움."""
import json, glob, re

def sentences(t, n=2):
    parts = re.split(r"(?<=[.!?。])\s+", (t or "").strip())
    return " ".join(parts[:n]) if parts else ""

def kw_from_secret(sec):
    txt = (sec.get("text","") or ""); typ = sec.get("type","") or ""
    words = [w for w in re.split(r"[\s,·]", txt) if len(w) >= 2][:3]
    trig = list(dict.fromkeys([typ] + words))
    return [t for t in trig if t][:4] or [typ or "비밀"]

def fix(path):
    s = json.load(open(path, encoding="utf-8")); ch = []
    for c in s["cast"]:
        if not c.get("bio"):
            c["bio"] = sentences(c.get("life_story",""), 3) or f"{c.get('name')}의 배경."
            ch.append("bio:"+c["id"])
        per = c.setdefault("persona", {})
        if not per.get("example_line"):
            per["example_line"] = "내가 그럴 사람으로 보이오?"
            ch.append("line:"+c["id"])
        if not (c.get("pressure_points") or []):
            sec = c.get("secret", {}) or {}
            reveal = (f"…{sec.get('text','그 일')}은(는) 사실이오. 허나 그건 이 죽음과는 상관없소."
                      if not c.get("is_culprit")
                      else f"…{sec.get('text','그 일')}은(는) 인정하오. 허나 사람을 해친 일은 결코 아니오.")
            c["pressure_points"] = [{"trigger": kw_from_secret(sec), "reveals": reveal,
                                     "unlocks": sec.get("type","비밀")}]
            ch.append("pp:"+c["id"])
    if ch:
        json.dump(s, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  {'✓' if ch else '·'} {path}  {' '.join(ch) if ch else '(이미 충분)'}")

if __name__ == "__main__":
    for p in sorted(glob.glob("scenarios/*.json")):
        fix(p)
