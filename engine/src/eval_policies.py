# -*- coding: utf-8 -*-
"""
eval_policies.py — **다섯 부류의 플레이어**로 한 편씩 돌려 본다. 맞히는 길만이 아니라
틀리는 길에서도 게임이 성립하는지를 본다.

다섯 부류
  정공법   장소를 다 뒤지고 끝까지 듣고 마지막에 지목 (eval_play와 같음)
  성급이   라운드가 끝날 때마다 그 시점 1위를 바로 지목. 틀리면 생명이 깎이고 계속
  헛다리   결정타가 나오는 장소를 끝까지 안 뒤진다 — 결정타 없이 지목
  소거파   배제 단서만 셈한다. 마지막에 남은 후보 중 의심 1위를 지목
  막찍이   증거를 안 본다. 매 라운드 무작위 지목 (생명 3개 소진 실험)

무엇을 잡아내나
  · 성급이가 1라운드에 맞히면 → 판이 너무 뻔하다
  · 헛다리도 맞히면 → 결정타가 무의미하다 (소거만으로 답이 나온다)
  · 생명(3회)을 다 써도 엔딩 등급이 안 나오면 → 실패 엔딩 구멍
  · 오답 지목 뒤 게임이 이어질 수 없으면 → 재도전 설계 구멍

사용:
    python eval_policies.py                 # 전 편
    python eval_policies.py out/34*.json
    python eval_policies.py --out 정책평가.md
"""
import json, glob, sys, os, argparse, collections, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")
FREE = ("crime_scene",)


class Sim:
    """autoplay의 의심도 기계를 정책만 바꿔 돌린다."""

    def __init__(self, s, skip_decisive=False, exculpate_only=False):
        self.s = s
        self.rounds = (s.get("config") or {}).get("rounds", 3)
        self.lives = (s.get("config") or {}).get("attempts", 3)
        self.susp = {c["id"]: 0.0 for c in s["cast"]}
        self.cleared = set()
        self.held = set()
        self.cul = next(c["id"] for c in s["cast"] if c.get("is_culprit"))
        self.skip_decisive = skip_decisive
        self.exculpate_only = exculpate_only
        self.dec_locs = {c.get("location") or s["death"]["place"]
                         for c in s["clue_graph"] if c.get("decisive")}
        self.accusations = []
        self.secrets = set()                 # 캐낸 비밀(소지품 단서로 열린 것)
        self.blind = False                   # 막찍이 — 단서를 아예 안 본다

    def see(self, cl):
        if self.blind:
            return
        if self.exculpate_only:
            for e in (cl.get("exculpates") or []):
                self.cleared.add(e); self.susp[e] = -99
            return
        for e in (cl.get("exculpates") or []):
            self.cleared.add(e); self.susp[e] = -99
        pt = cl.get("points_to")
        if pt and pt not in self.cleared:
            self.susp[pt] += 3.0 if cl.get("decisive") else 1.0
        for a in (cl.get("affects") or []):
            if a not in self.cleared:
                self.susp[a] += 0.3

    def round_(self, r):
        if self.blind:
            return                            # 막찍이는 단서를 줍지도 않는다
        for cl in self.s["clue_graph"]:
            if cl["id"] in self.held:
                continue
            rr = cl.get("reveal_round") or 1
            free = cl.get("channel") in FREE
            if free and r == 1:
                self.held.add(cl["id"]); self.see(cl); continue
            if not free and rr <= r:
                loc = cl.get("location") or self.s["death"]["place"]
                if self.skip_decisive and loc in self.dec_locs:
                    continue                      # 그 장소는 발도 안 들인다
                self.held.add(cl["id"]); self.see(cl)

    def top(self, strict=False):
        live = [(v, k) for k, v in self.susp.items() if k not in self.cleared]
        if not live:
            live = [(v, k) for k, v in self.susp.items()]
        live.sort(reverse=True)
        if strict and len(live) >= 2 and abs(live[0][0] - live[1][0]) < 1e-9:
            return None                      # 확실한 1위가 없다 — 성급이도 이번엔 참는다
        return live[0][1]

    def remaining(self):
        return [c["id"] for c in self.s["cast"] if c["id"] not in self.cleared]

    def accuse(self, cid):
        self.accusations.append(cid)
        ok = cid == self.cul
        if not ok:
            self.lives -= 1
        return ok

    def _count_secrets(self):
        """쥔 단서(forced_by)로 열 수 있는 비밀 수 — 심문에서 들이대면 실토하는 것들."""
        n = 0
        for c in self.s["cast"]:
            for sec in (c.get("secrets") or []):
                fb = set(sec.get("forced_by") or [])
                if fb and fb & self.held:
                    n += 1
                    break                      # 인물당 하나만 셈 (채점 규칙과 맞춤)
        return n

    def score(self, correct):
        sc = self.s.get("scoring") or {}
        pts = (sc.get("culprit_correct", 5) if correct else 0)
        pts += sc.get("secret_revealed_each", 1) * self._count_secrets()
        pts -= sc.get("wrong_accusation_penalty", 0) * max(0, len(self.accusations) - (1 if correct else 0))
        return max(0, pts), sc.get("max", 10)

    def grade(self, pts):
        gr = sorted((self.s.get("ending") or {}).get("grades") or [],
                    key=lambda g: g.get("min", 0))
        name = None
        for g in gr:
            if pts >= g.get("min", 0):
                name = g.get("name") or g.get("title")
        return name


def run_policy(s, policy, seed=0):
    random.seed(seed)
    sim = Sim(s, skip_decisive=(policy == "헛다리"),
              exculpate_only=(policy == "소거파"))
    sim.blind = (policy == "막찍이")
    correct = False; when = None
    for r in range(1, sim.rounds + 1):
        sim.round_(r)
        if policy in ("성급이", "막찍이") and sim.lives > 0 and not correct:
            if policy == "막찍이":
                cand = [x for x in sim.remaining() if x not in sim.accusations]
                pick = random.choice(cand) if cand else None
            else:
                pick = sim.top(strict=True)
            if pick is not None and sim.accuse(pick):
                correct = True; when = r
        if sim.lives <= 0:
            break
    if not correct and sim.lives > 0 and policy not in ("막찍이",):
        pick = sim.top()
        if sim.accuse(pick):
            correct = True; when = sim.rounds
    pts, mx = sim.score(correct)
    return {
        "policy": policy, "correct": correct, "when": when,
        "lives_left": max(0, sim.lives), "tries": len(sim.accusations),
        "pts": pts, "max": mx, "grade": sim.grade(pts),
        "remaining": len(sim.remaining()),
    }


POLICIES = ["정공법", "성급이", "헛다리", "소거파", "막찍이"]


def one(path):
    s = json.load(open(path, encoding="utf-8"))
    rows = {p: run_policy(s, p) for p in POLICIES}
    # 막찍이는 운이라 5시드 평균
    wins = sum(run_policy(s, "막찍이", seed=k)["correct"] for k in range(5))
    rows["막찍이"]["win5"] = wins
    issues = []
    if rows["성급이"]["correct"] and (rows["성급이"]["when"] or 9) <= 1:
        issues.append("1라운드에 성급 지목이 적중 — 너무 뻔함")
    if rows["헛다리"]["correct"] and rows["헛다리"]["remaining"] <= 1:
        issues.append("결정타 없이 소거만으로 유일해짐 — 결정타 무의미")
    for p in POLICIES:
        if rows[p]["grade"] is None:
            issues.append(f"{p} 점수({rows[p]['pts']})에 해당하는 엔딩 등급 없음")
    lucky = [run_policy(s, "막찍이", seed=k) for k in range(5)]
    best_lucky = max((r["pts"] for r in lucky), default=0)
    if best_lucky >= rows["정공법"]["pts"]:
        issues.append(f"막찍이 최고점({best_lucky})이 정공법({rows['정공법']['pts']})과 같거나 큼 — 감점 설계 점검")
    return s["meta"]["title"], os.path.basename(path).replace(".json", ""), rows, issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    paths = []
    for x in (a.paths or ["scenarios/[0-9]*.json"]):
        paths += sorted(glob.glob(x))
    L = [f"{'편':22}{'정공':5}{'성급(R)':8}{'헛다리':6}{'소거':5}{'막찍5':6} 문제",
         "-" * 84]
    md = ["# 정책별 플레이 시뮬레이션", "",
          "| 편 | 정공법 | 성급이(적중R) | 헛다리 | 소거파 | 막찍이(5판) | 문제 |",
          "|---|---|---|---|---|---|---|"]
    n_issue = 0
    for p in paths:
        try:
            title, fid, rows, issues = one(p)
        except Exception as e:
            L.append(f"{os.path.basename(p)[:20]:22} 실행 실패: {type(e).__name__} {e}")
            n_issue += 1
            continue
        def m(x): return "○" if x["correct"] else "✗"
        hasty = rows["성급이"]
        L.append(f"{fid[:20]:22}"
                 f"{m(rows['정공법']):5}"
                 f"{(m(hasty)+'(R'+str(hasty['when'])+')') if hasty['correct'] else '✗':8}"
                 f"{m(rows['헛다리']):6}"
                 f"{m(rows['소거파']):5}"
                 f"{rows['막찍이']['win5']}/5   "
                 f"{'; '.join(issues) or '—'}")
        md.append(f"| {title} | {m(rows['정공법'])} {rows['정공법']['pts']}/{rows['정공법']['max']} "
                  f"({rows['정공법']['grade']}) | "
                  f"{m(hasty)}{' R'+str(hasty['when']) if hasty['correct'] else ''} "
                  f"생명{hasty['lives_left']} | "
                  f"{m(rows['헛다리'])} 후보{rows['헛다리']['remaining']} | "
                  f"{m(rows['소거파'])} 후보{rows['소거파']['remaining']} | "
                  f"{rows['막찍이']['win5']}/5 | {'; '.join(issues) or '—'} |")
        if issues:
            n_issue += 1
    L.append("-" * 84)
    L.append(f"문제 있는 편: {n_issue}/{len(paths)}")
    print("\n".join(L))
    if a.out:
        md += ["", f"문제 있는 편: **{n_issue}/{len(paths)}**", "",
               "읽는 법: 정공법은 ○이어야 정상. 성급이 R1 적중·헛다리 ○(후보 1)은 판이 쉽다는 신호. "
               "막찍이는 5판 중 1~2번이 정상(다섯 명 중 하나 × 생명 3회)."]
        open(a.out, "w", encoding="utf-8").write("\n".join(md))
        print("저장:", a.out)


if __name__ == "__main__":
    main()
