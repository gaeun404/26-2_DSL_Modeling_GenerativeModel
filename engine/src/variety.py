# -*- coding: utf-8 -*-
"""
variety.py — **모음 전체가 얼마나 다양한가**를 본다. 한 편씩 보는 검사가 아니다.

왜 필요한가
  지금 검사기들은 전부 "이 한 편이 성립하는가"를 묻는다. 그래서 23편이 전부 통과한다.
  그런데 재미 점수를 재 보니 89.5~97.2에 몰려 있었다(표준편차 1.8).
  지표가 고장 난 줄 알았는데, 실제로 재 보니 **작품들이 서로 닮은 것**이었다.

      채널 종류   23편 모두 3       교차 단서  23편 모두 정확히 5개
      라운드      23편 모두 3        인물 수    23편 모두 5명
      장소        6~7               좁힘 곡선  전부 5→3→1 언저리

  이야기(트릭 21종, 흉기 12종)는 다양한데 **판의 뼈대가 판박이**다.
  이 상태로 100편을 만들어 학습시키면, 모델은 "5인·3라운드·장소 6"을 규칙으로 배운다.
  한 편씩은 다 통과하는데 다 비슷한 게임이 나온다.

  그래서 **모음 단위로** 다양성을 재고, 어느 축이 주저앉았는지 알려 준다.

보는 축
  cast_n rounds places clue_n channels cross_n trap_ratio
  narrow(좁힘 곡선) trick weapon culture register 말체조합

판정
  ○ 벌어짐   값이 여러 갈래로 퍼져 있다
  △ 좁음     두세 갈래뿐
  × 주저앉음 전부 같은 값 — 생성기가 규칙으로 굳혔다는 뜻

사용:
    python variety.py                 # out/ 전체
    python variety.py --target 100    # 100편 목표일 때 필요한 폭까지 함께
"""
import json, glob, sys, os, collections, statistics as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")

# 100편으로 갈 때 **최소한 이만큼은 갈라져야** 한다는 눈금
TARGET = {
    "cast_n":    (3, "인물 수 — 4·5·6명이 섞여야 판의 밀도가 달라진다"),
    "rounds":    (2, "라운드 — 3라운드 일변도면 호흡이 하나뿐이다"),
    "places":    (4, "장소 수 — 좁은 집과 넓은 마을은 다른 게임이다"),
    "clue_n":    (6, "단서 수 — 촘촘한 판과 성근 판"),
    "channels":  (3, "단서 채널 종류 — 현장·증언·장소 말고도 있어야"),
    "cross_n":   (4, "교차 단서 수 — 관계가 물리는 정도"),
    "narrow":    (4, "좁힘 곡선 — 천천히 좁혀지는 판과 급히 좁혀지는 판"),
    "trick":     (25, "트릭 — 같은 트릭이 반복되면 학습이 편향된다"),
    "weapon":    (10, "흉기 유형"),
    "culture":   (4, "배경 문화권"),
    "voiceset":  (10, "말체 조합 — 다섯 명에게 어떤 말체를 물렸나"),
    "event_kind": (5, "중반 이벤트 — 새증언 말고도 두번째사건·증거소실·인물이탈·시간압박·외부개입"),
    "dying_kind": (3, "다잉메시지 방식 — 글자일부·물건배치·몸짓·암호·훼손"),
    "twist_kind": (4, "반전 종류 — 피해자오인·자작극·공범·시간착오·은폐자별개"),
}


def measure(paths):
    M = collections.defaultdict(list)
    for p in sorted(paths):
        s = json.load(open(p, encoding="utf-8"))
        cg = s.get("clue_graph") or []
        cast = s.get("cast") or []
        M["cast_n"].append(len(cast))
        M["rounds"].append(s.get("config", {}).get("rounds", 3))
        M["places"].append(len(s.get("map", {}).get("places") or []))
        M["clue_n"].append(len(cg))
        M["channels"].append(len({c.get("channel") for c in cg}))
        M["cross_n"].append(sum(1 for c in cg if len(c.get("affects") or []) >= 2))
        try:
            import flow
            M["narrow"].append(tuple(flow.narrowing(s)))
        except Exception:
            pass
        M["trick"].append((s.get("trick") or {}).get("name", "?"))
        M["weapon"].append(s.get("death", {}).get("weapon_class", "?"))
        M["culture"].append(((s.get("background") or {}).get("setting_raw") or {}).get("culture", "?"))
        # 중반 이벤트·다잉메시지·단서 유형도 다양성 축이다.
        # 실제로 재 보니 23편의 이벤트가 전부 '새증언' 하나였다 — 중반이 늘 같다.
        try:
            import extract_structure as ES
            r = ES.from_scenario(s)
            M["event_kind"].append(tuple(r["event_kinds"]) or ("없음",))
            M["dying_kind"].append(r["dying_kind"] or "없음")
            M["clue_kindset"].append(tuple(r["clue_kinds"]))
            M["twist_kind"].append(r["twist_kind"])
        except Exception:
            pass
        M["voiceset"].append(tuple(sorted(
            ((c.get("persona") or {}).get("voice") or {}).get("form", "?") for c in cast)))
    return M


def report(M, n_files, target=None):
    print(f"{'축':10}{'갈래':>5}{'분포':>44}   판정")
    print("-" * 78)
    weak = []
    for k, vals in M.items():
        kinds = collections.Counter(vals)
        nk = len(kinds)
        top = ", ".join(f"{v}×{c}" for v, c in kinds.most_common(3)
                        if not isinstance(v, tuple)) or \
              ", ".join(f"{'/'.join(map(str, v))}×{c}" for v, c in kinds.most_common(3))
        if nk == 1:
            mark = "× 주저앉음"
        elif nk <= max(2, n_files // 8):
            mark = "△ 좁음"
        else:
            mark = "○ 벌어짐"
        if mark != "○ 벌어짐":
            weak.append((k, nk))
        print(f"{k:10}{nk:5}{top[:44]:>44}   {mark}")
    if target:
        print("\n" + "-" * 78)
        print(f"{'축':10}{'지금':>5}{'100편 목표':>10}   무엇이 부족한가")
        for k, (need, why) in TARGET.items():
            now = len(collections.Counter(M.get(k, [])))
            if now < need:
                print(f"{k:10}{now:5}{need:>10}   {why}")
    return weak


if __name__ == "__main__":
    paths = glob.glob("scenarios/[0-9]*.json")
    M = measure(paths)
    print(f"작품 {len(paths)}편\n")
    weak = report(M, len(paths), target=("--target" in sys.argv))
    print("\n" + "=" * 78)
    if weak:
        print("주저앉은 축:", ", ".join(f"{k}({n}갈래)" for k, n in weak))
        print("→ 이 축들이 생성기에 **상수로 박혀 있다.** 100편으로 가기 전에 폭을 열어야 한다.")
    else:
        print("모든 축이 벌어져 있다.")
