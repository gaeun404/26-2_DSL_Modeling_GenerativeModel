# -*- coding: utf-8 -*-
"""fix_combos.py — **겹쳐 보기가 답을 뱉지 않게.**

■ 왜 (2026-08-31)
  「단서 겹쳐보기」 API를 열다가 발견했다. 91편의 첫 조합이 이렇다 —

      K1(검안) + K2(여섯 잔)  ← **둘 다 1라운드 공짜 단서**
      제목 : 「**니코틴 원액 탄 아이스 아메리카노**는 어떻게 쓰였나」
      결과 : 「니코틴 원액 탄 아이스 아메리카노가 어떻게 쓰였는지가 맞춰진다 —
              **시간차 독살 — 암전 15분**의 얼개가 드러난다.」

  하루 전에 검안에서 물질명을 지우고 세 걸음으로 벌려 놓았는데,
  **조합 한 번이면 흉기도 수법도 그대로 나온다.** 앞문을 잠그고 뒷문을 열어 둔 셈이다.

  조합은 50편을 같은 생성기가 만들었으므로 전부 같은 병이 있다고 봐야 한다.

■ 규칙
  겹쳐 보기는 **가진 것을 다시 보는 일**이지 새 정답을 받는 일이 아니다.
  그러니 조합의 결과는 **한 걸음**이어야 한다 — 후보를 좁히거나, 사람을 지워 주거나.

  · 흉기 이름과 수법 이름은 조합 문면에서 **가린다.**
    (그것을 알려 주는 것은 결정타 단서의 몫이다)
  · 다만 **결정타가 낀 조합**은 그대로 둔다 — 그 단서를 이미 손에 넣었다면
    답을 알아도 된다. 값을 치르고 얻은 것이다.
"""
import json, glob, re, os, argparse


def _head(w):
    w = re.sub(r"\([^)]*\)", " ", str(w or ""))
    tok = [t for t in re.split(r"[\s·,]+", w) if len(t) >= 2]
    return tok[0] if tok else ""


# ★조합 문면은 **틀에서 찍어 낸 것**이라 낱말만 바꾸면 문장이 망가진다
#   ("놋 그것는 어떻게 쓰였나"). 틀을 알아보고 **문장째 갈아 끼운다.**
_TPL = re.compile(r"어떻게\s*쓰였")

_NEW = {
    "title": "어떻게 그럴 수 있었나",
    "yields": ("검안과 현장을 맞대면 얼개가 한 겹 잡힌다 — 그 자리에서 무엇이 어떻게 "
               "오갔는지가 좁혀진다. 다만 쓰인 것이 무엇이었는지까지는 아직 모른다."),
    "unlocks": "수법의 테두리가 보인다. 안을 채우려면 더 찾아야 한다.",
}


def scrub(s):
    """조합에서 흉기·수법 이름을 걷어낸다. 고친 개수를 돌려준다.

    결정타가 낀 조합은 손대지 않는다 — 값을 치르고 얻은 것이라 답을 알아도 된다.
    """
    weapon = str((s.get("death") or {}).get("weapon") or "").strip()
    trick = str((s.get("trick") or {}).get("name") or "").strip()
    trick_head = re.split(r"\s*[—–-]\s*", trick)[0].strip()
    dec = {c.get("id") for c in (s.get("clue_graph") or []) if c.get("decisive")}
    n = 0
    for cb in ((s.get("clue_combos") or {}).get("combos") or []):
        if set(cb.get("needs") or []) & dec:
            continue
        title = str(cb.get("title") or "")
        blob = title + " " + str(cb.get("yields") or "")
        spoils = ((weapon and weapon in blob) or
                  (trick and trick in blob) or
                  (trick_head and len(trick_head) > 1 and trick_head in blob))
        if not spoils:
            continue
        if _TPL.search(title):
            # 「{흉기}는 어떻게 쓰였나」 틀 — 통째로 간다
            cb.update(dict(_NEW))
        else:
            # 틀 밖의 문장은 이름만 조심스레 지운다
            for field in ("title", "yields", "unlocks"):
                tx = str(cb.get(field) or "")
                if not tx:
                    continue
                if weapon:
                    tx = tx.replace(weapon, "쓰인 것")
                if trick:
                    tx = tx.replace(trick, "그 수법")
                elif trick_head and len(trick_head) > 1:
                    tx = tx.replace(trick_head, "그 수법")
                cb[field] = re.sub(r"\s+", " ", tx).strip()
        n += 1
    return n


# ★91편은 손으로 다시 쓴다 — 데모라 문장이 눈에 띈다.
#   K1+K2 는 둘 다 1라운드 공짜다. 그 둘이 낳을 수 있는 것은
#   「누구를 노렸나」까지지 「무엇으로」가 아니다.
_91 = {
    ("K1", "K2"): {
        "title": "노린 잔은 하나뿐이었다",
        "yields": ("검안과 테이블을 맞대면 하나가 분명해진다 — 독이 든 것은 여섯 잔 중 "
                   "회장 것 하나다. 뚜껑 표시가 저마다 달라 잘못 집어 들 여지가 없었으니, "
                   "잘못 마신 사고가 아니라 정해 놓고 넣은 것이다."),
        "unlocks": "우연이 아니다. 한도윤 한 사람을 노렸다.",
        "round_min": 1,
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    total = 0
    for f in sorted(glob.glob("scenarios/*.json")):
        if "catalog" in f:
            continue
        s = json.load(open(f, encoding="utf-8"))
        n = scrub(s)
        if os.path.basename(f).startswith("91"):
            for cb in ((s.get("clue_combos") or {}).get("combos") or []):
                key = tuple(sorted(cb.get("needs") or []))
                if key in _91:
                    cb.update(_91[key])
                    n += 1
        if n:
            total += 1
            if a.check:
                print(f"── {os.path.basename(f)} — 조합 {n}개")
                for cb in ((s.get("clue_combos") or {}).get("combos") or []):
                    print(f"   {cb.get('needs')} · {cb.get('title')}")
                    print(f"      {str(cb.get('yields'))[:110]}")
            else:
                json.dump(s, open(f, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=2)
    print(f"\n조합을 고친 시나리오 {total}편")


if __name__ == "__main__":
    main()
