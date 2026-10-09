# -*- coding: utf-8 -*-
"""
deduce.py — **단서 조합(아하!) 메커닉**과 **장소 고유 보상**을 넣는다.

■ 왜 만들었나 (재미 지표 F3·F2가 가장 낮았다)
    F3 '아하연결' 평균 6.05/10 (가중 10) — 단서 하나가 곧 답을 주는 구조라
      "두 개를 이어 붙여야 뜻이 생기는" 순간이 거의 없었다. 추리의 쾌감은 거기서 나온다.
    F2 '장소보상' 평균 7.23/10 — 328곳 중 129곳에 **아무 보상이 없었다.**
      들어가 봐야 아무것도 없는 방은 그 자체로 재미를 깎는다.

■ 무엇을 넣나
    ① clue_combos[]  — 수첩에서 단서 두 장을 겹치면 **새 사실**이 나온다.
       레시피는 이 편의 실제 단서에서 뽑는다(억지로 만들지 않는다).
         흉기 × 트릭      → 그 흉기가 어떻게 쓰였는가
         증언 × 알리바이깨기 → 누구의 말이 거짓인가
         물증 × 동기      → 왜 그랬는가
         소문 × 알리바이   → 왜 그 사람이 아닌가(헛다리 해소)
         정황 × 결정타     → 마지막 한 조각
       조합에 성공하면 점수를 주고, 어떤 조합은 대질/비밀을 연다.

    ② place_rewards{} — location 단서가 없는 장소에도 **고유한 발견**을 준다.
       사건 해결에 직결되진 않지만 그 집을 이해하게 하는 것 —
       인물의 살림, 지난 일의 자취, 다음에 무엇을 물을지의 실마리.

사용:
    python deduce.py                  # 전 편
    python deduce.py out/38_*.json    # 한 편
"""
import json, glob, re, sys

from ui import _j                      # 조사 도우미
from story_narration import _spoiler_words   # 비밀 누출 차단


def _short(x, cap=90):
    x = re.sub(r"【[^】]*】", "", str(x or ""))
    x = re.sub(r"\s+", " ", x).strip()
    return (x[:cap].rstrip(" ,—") + "…") if len(x) > cap else x


def _by(clues, *weights):
    return [c for c in clues if c.get("weight") in weights]


def combos(s):
    """이 편의 단서에서 실제로 성립하는 조합만 뽑는다."""
    cl = s["clue_graph"]
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    cast = {c["id"]: c["name"] for c in s["cast"]}
    rounds = int(s["config"].get("rounds", 3))
    dec = next((c for c in cl if c.get("decisive")), None)
    out = []

    def add(a, b, title, yields, unlocks, pts, rmin):
        if not a or not b or a["id"] == b["id"]:
            return
        out.append({
            "id": f"CB{len(out)+1}",
            "needs": [a["id"], b["id"]],
            "title": title,
            "a_hint": _short(a.get("surface")),
            "b_hint": _short(b.get("surface")),
            "yields": yields,
            "unlocks": unlocks,
            "points": pts,
            "round_min": rmin,
        })

    wpn = _by(cl, "weapon")
    trk = _by(cl, "trick")
    tst = _by(cl, "testimony")
    abk = _by(cl, "alibi_break")
    phy = _by(cl, "physical")
    mot = _by(cl, "motive")
    alb = _by(cl, "alibi")
    rh = _by(cl, "red_herring")
    ctx = _by(cl, "context")

    d = s["death"]
    wp = re.sub(r"\s*\([^)]*\)", "", str(d.get("weapon", ""))).strip()
    tr = (s.get("trick") or {}).get("name", "")

    # ① 흉기 × 트릭 — 그 흉기가 '어떻게' 쓰였는지가 비로소 서는 조합
    if wpn and trk:
        add(wpn[0], trk[0], f"{wp}{_j(wp,'은/는')} 어떻게 쓰였나",
            f"{wp}{_j(wp,'이/가')} 어떻게 쓰였는지가 맞춰진다 — {tr}의 얼개가 드러난다.",
            "트릭 항목이 수첩에 정리된다", 1, 1)

    # ② 증언 × 알리바이 깨기 — 누구 말이 거짓인가
    if tst and abk:
        who = cast.get(abk[0].get("points_to"), "")
        add(tst[0], abk[0], "어긋난 말",
            f"두 말을 겹치면 {who or '한 사람'}의 진술에서 시각이 어긋난다.",
            "그 인물과의 대질이 열린다", 2, max(2, rounds - 1))

    # ③ 물증 × 동기 — 왜 그랬는가
    if phy and mot:
        add(phy[0], mot[0], "값을 부른 까닭",
            "물건과 셈이 이어져, 이 죽음이 무엇 때문이었는지가 선다.",
            "동기 후보가 좁혀진다", 2, 2)

    # ④ 소문 × 알리바이 — 왜 그 사람이 아닌가(헛다리 해소)
    if rh and alb:
        pt = cast.get(rh[0].get("points_to"), "")
        add(rh[0], alb[0], f"{pt or '소문 속 그 사람'}{_j(pt or '소문 속 그 사람','은/는')} 왜 아닌가",
            f"쏠린 소문과 증언을 맞대면 {pt or '그 사람'}"
            f"{_j(pt or '그 사람','이/가')} 그 자리에 없었음이 드러난다.",
            "헛다리 하나가 정리된다", 1, 2)

    # ⑤ 정황 × 결정타 — 마지막 한 조각
    if ctx and dec:
        add(ctx[0], dec, "마지막 한 조각",
            "정황이 결정타와 맞물려, 남은 한 사람만 설명이 된다.",
            "지목 화면에서 확신 표시가 뜬다", 3, rounds)
    elif trk and dec and len(trk) > 1:
        add(trk[1], dec, "마지막 한 조각",
            "트릭의 조건과 결정타가 맞물려, 남은 한 사람만 설명이 된다.",
            "지목 화면에서 확신 표시가 뜬다", 3, rounds)

    return out


def place_rewards(s):
    """location 단서가 없는 장소에 고유한 발견을 준다."""
    cl = s["clue_graph"]
    have = {c.get("location") for c in cl if c.get("channel") == "location"}
    cast = {c["id"]: c for c in s["cast"]}
    out = {}
    for p in s["map"]["places"]:
        pid = p["id"]
        if pid in have:
            continue
        owner = cast.get(p.get("owner") or "")
        feats = p.get("features") or []
        f0 = feats[0] if feats else p.get("desc", "")
        if owner:
            nm = owner["name"]
            # ★bio에는 '진짜 절박함은 …였다'처럼 정답이 적혀 있다. 그대로 쓰면 게임이 끝난다.
            #   비밀·동기 낱말이 겹치면 공개 신분(public)으로 물러선다.
            words, _blob = _spoiler_words(owner)
            cand = _short(owner.get("bio") or "", 70)
            if sum(1 for w in words if w in cand) >= 1:
                cand = _short(owner.get("public") or (owner.get("profile") or {}).get("status"), 70)
            text = (f"{f0}{_j(f0,'이/가')} 눈에 든다. {nm}의 살림이 그대로 놓여 있다 — {cand}")
            teaches = f"{nm}{_j(nm,'이/가')} 어떤 사람인지, 무엇을 아끼는지 알게 된다"
            about = owner["id"]
        else:
            text = (f"{f0}{_j(f0,'이/가')} 눈에 든다. 이 집이 어떻게 돌아가는지가 보인다 — "
                    f"{p.get('desc','')}")
            teaches = "이 집의 살림과 동선을 이해하게 된다"
            about = None
        out[pid] = {
            "place": pid, "name": p["name"],
            "text": _short(text, 170),
            "teaches": teaches,
            "about": about,
            "kind": "flavor",
            "note": "사건 해결에 직결되지는 않지만, 빈손으로 나오는 방이 없게 한다. "
                    "심문에서 물어볼 거리를 준다.",
        }
    return out


def enrich(path, check=False):
    s = json.load(open(path, encoding="utf-8"))
    cb = combos(s)
    pr = place_rewards(s)
    if not check:
        s["clue_combos"] = {
            "note": "수첩에서 단서 두 장을 겹치면 새 사실이 나온다. "
                    "단서 하나가 곧 답을 주지 않게 하고, 이어 붙이는 재미를 만든다.",
            "ui_copy": {"button": "겹쳐 본다", "picker": "어느 단서와 겹칠까요?",
                        "hit": "두 단서가 이어집니다.", "miss": "이 둘은 이어지지 않는다.",
                        "done": "이미 이어 본 조합입니다."},
            "rule": "두 단서를 **모두 획득한 뒤**에만 겹칠 수 있다. 성공하면 점수를 얻고 "
                    "yields가 수첩에 새 항목으로 남는다.",
            "combos": cb, "count": len(cb),
        }
        s["place_rewards"] = {
            "note": "location 단서가 없는 장소에도 고유한 발견을 둔다 — 빈손으로 나오는 방이 없게.",
            "rewards": pr, "count": len(pr),
        }
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  {path.split('/')[-1][:28]:30s} 조합 {len(cb)}개 · 장소보상 {len(pr)}곳")
    return len(cb), len(pr)


if __name__ == "__main__":
    check = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    a = b = 0
    for f in files:
        x, y = enrich(f, check)
        a += x; b += y
    print(f"\n{len(files)}편 · 조합 총 {a}개 · 장소보상 총 {b}곳")
