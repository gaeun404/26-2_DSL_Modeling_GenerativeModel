# -*- coding: utf-8 -*-
"""측정된 난이도(100회+ 플레이 정답률)를 각 시나리오에 부여. game이 표시/밸런싱에 사용."""
import json, glob
from simulate import simulate, tier, legs

def label(path, N=600):
    s=json.load(open(path,encoding="utf-8"))
    rate=simulate(s,N)
    t,_=tier(rate)
    s["difficulty"]={
        "solve_rate":round(rate,2),
        "tier":t.split()[-1] if " " in t else t,   # 적정(중)→'적정(중)'
        "label":t,
        "measured_by":f"montecarlo_{N}plays_full_answer",
        "band_ok":0.30<=rate<=0.70,
        "config":{"rounds":s["config"].get("rounds"),"attempts":s["config"].get("attempts"),
                  "turns_per_round":s["config"].get("turns_per_round")},
        "false_leads":[c["id"] for c in s["cast"] if not c.get("is_culprit") and legs(c)>=2],
    }
    json.dump(s,open(path,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    flag="✅" if s["difficulty"]["band_ok"] else "⚠️"
    print(f"  {flag} {rate:.2f} {t:14} {path}")

if __name__=="__main__":
    import sys
    paths=glob.glob(sys.argv[1]) if len(sys.argv)>1 else glob.glob("scenarios/[0-9]*.json")
    for p in sorted(paths): label(p)
