# -*- coding: utf-8 -*-
"""fix_weapon.py — **흉기 문제를 문제답게 만든다.**

■ 제보 (2026-08-30)
  "수법은 너무 누구나 알지 않나? 단서가 검안이라 이미 나와 있잖아.
   아니면 적어도 '레몬 향으로 쓴 냄새를 감췄다' 이런 거라도 단서에 안 적혀 있던가.
   그리고 수법 후보가 너무 그럴싸한 것도 없잖아."

  세 군데가 다 무너져 있었다. 하나씩.

  ① **검안이 답을 대 버린다.**
     「급성 중독 소견. 'S' 컵 잔량에서 고농도 **니코틴** 검출」
     그리고 보기 1번이 「**니코틴** 원액 탄 아이스 아메리카노」다.
     검안은 1라운드에 현장 화면에서 그냥 주는 단서다. 즉 **공짜로 답이 나온다.**
     추리가 아니라 낱말 맞추기가 된다.

     → 검안은 **갈래까지만** 말한다(급성 중독). 무엇이었는지는 결정타 단서
       (소품 파우치 — 니코틴 원액 병)를 찾아야 안다. 두 걸음이 생긴다.

  ② **감춘 흔적이 어디에도 안 적혀 있다.**
     니코틴은 쓰고 냄새가 난다. 그냥 타면 한 모금에 안다. 그래서 범인은
     레몬시럽으로 가렸다 — 이것이 트릭의 알맹이인데 단서에 없었다.
     검안에 **가려져 있었다는 사실**을 적는다. 그러면 플레이어는
     「가릴 필요가 있는 독」을 찾게 된다 — 무미무취한 수면제가 아니라.

  ③ **보기가 그 방에 없던 물건이다.**
     2026년 학회 회의실인데 보기에 「괄사 문어(둔기)」가 있었다.
     게다가 **정답이 50편 전부 1번**이었다(확인함).

     → 보기는 그 사건의 물건으로 짓고, 자리를 섞는다.
       좋은 보기 다섯이란: 검안으로 **둘셋이 남고**, 결정타로 **하나가 되는** 것.
"""
import json, glob, re, os, argparse, hashlib

# ── ① 검안이 물질명을 대지 않게 ───────────────────────────────────────
_EXAM = re.compile(r"【(검안|검험|부검)】|검안 소견|부검 소견")
_CLASS = [(re.compile(r"중독|독|짐주|비상|부자|약물|수면제|니코틴|메탄올"), "독물 성분"),
          (re.compile(r"자상|찔린|칼|비녀|침"), "예기(銳器)에 의한 손상"),
          (re.compile(r"교살|목맴|끈|졸린"), "경부 압박")]


def _head(w):
    """흉기 이름에서 **물질/도구를 가리키는 낱말**만 뽑는다.
    '니코틴 원액 탄 아이스 아메리카노' → '니코틴',  '짐주(鴆酒) 독배' → '짐주'"""
    w = re.sub(r"\([^)]*\)", " ", str(w or ""))
    tok = [t for t in re.split(r"[\s·,]+", w) if len(t) >= 2]
    return tok[0] if tok else ""


def redact_exam(s):
    """검안 단서에서 물질 이름을 지우고, **가려져 있었다는 사실**을 남긴다."""
    w = (s.get("death") or {}).get("weapon") or ""
    head = _head(w)
    if not head:
        return 0
    klass = next((lab for rx, lab in _CLASS if rx.search(w)), "독물 성분")
    n = 0
    for c in (s.get("clue_graph") or []):
        surf = str(c.get("surface") or "")
        if not _EXAM.search(surf) or head not in surf:
            continue
        # 물질 이름을 갈래말로 바꾼다 — '고농도 니코틴 검출' → '고농도 독물 성분 검출'
        c["surface"] = surf.replace(head, klass)
        c["implies"] = re.sub(re.escape(head), klass, str(c.get("implies") or ""))
        # 갈래만 알려 주는 단서라는 것을 못 박아 둔다
        c["names_weapon"] = False
        n += 1
    return n


# ── ③ 보기 다섯 — 자리를 섞는다 ───────────────────────────────────────
def shuffle_choices(s, fname):
    """정답이 늘 1번이던 것을 고친다. 편마다 자리는 **고정**이다(무작위 아님)."""
    ch = (s.get("choices") or {}).get("weapon") or []
    ans = (s.get("death") or {}).get("weapon")
    if len(ch) < 2 or ans not in ch:
        return False
    rest = [x for x in ch if x != ans]
    seed = int(hashlib.md5(fname.encode()).hexdigest(), 16)
    at = seed % len(ch)                      # 정답이 앉을 자리
    order = rest[:at] + [ans] + rest[at:]
    s["choices"]["weapon"] = order
    return True


# ── 91편 — 보기를 그 방의 물건으로 다시 짓는다 ────────────────────────
#   검안(급성 중독)으로 셋이 남고, 소품 파우치로 하나가 된다.
#   그리고 '가려야 했다'는 사실이 무미무취한 수면제를 걷어낸다 — 한 겹 더.
_91 = {
    "weapon": [
        "니코틴 원액 탄 아이스 아메리카노",       # 정답 — 쓰고 냄새난다. 그래서 가렸다
        "수면제 녹인 아이스 아메리카노",           # 중독계 — 그러나 무미무취라 가릴 이유가 없다
        "실험실 메탄올을 섞은 물병",               # 중독계 — 그러나 컵이 아니라 물병이다
        "개조한 노트북 어댑터 감전",               # 검안(중독)에서 걸러진다
        "HDMI 케이블 교살",                        # 검안(중독)에서 걸러진다
    ],
    "exam": ("【검안】 급성 중독 소견 — 심정지. 'S' 표시 컵 잔량에서 독물 성분이 검출됐다. "
             "다만 잔에서 나는 것은 시트러스 향뿐이다 — 쓴맛과 냄새를 가릴 만큼 "
             "레몬시럽이 진하게 들어가 있었다. 여섯 잔 중 시럽이 들어간 잔은 이것 하나다."),
    "exam_implies": ("weapon_class=급성 중독. 독은 컵 안에 있었다. "
                     "그리고 **가려야 했던 독**이다 — 맛도 냄새도 없는 것이었다면 "
                     "시럽을 넣을 까닭이 없다."),
}


def fix_91(s):
    s.setdefault("choices", {})["weapon"] = list(_91["weapon"])
    for c in (s.get("clue_graph") or []):
        if _EXAM.search(str(c.get("surface") or "")):
            c["surface"] = _91["exam"]
            c["implies"] = _91["exam_implies"]
            c["names_weapon"] = False
            break
    # 단서 카드 문면도 같이 맞춘다
    for card in (s.get("ui", {}).get("clue_cards") or []):
        if "검안" in str(card.get("name") or "") or "검험" in str(card.get("name") or ""):
            card["description"] = _91["exam"].split("】", 1)[-1].strip()
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = [f for f in sorted(glob.glob("scenarios/*.json")) if "catalog" not in f]
    red = shuf = 0
    for f in files:
        s = json.load(open(f, encoding="utf-8"))
        base = os.path.basename(f)
        if base.startswith("91"):
            fix_91(s)
        else:
            red += 1 if redact_exam(s) else 0
        shuf += 1 if shuffle_choices(s, base) else 0
        if a.check:
            ch = s["choices"]["weapon"]; ans = s["death"]["weapon"]
            print(f"{base:26} 정답 {ch.index(ans)+1}번 / {len(ch)}")
        else:
            json.dump(s, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n검안에서 물질명 가림 {red}편 · 보기 자리 섞음 {shuf}편")


if __name__ == "__main__":
    main()
