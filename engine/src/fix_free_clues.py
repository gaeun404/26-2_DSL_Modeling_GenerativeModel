# -*- coding: utf-8 -*-
"""fix_free_clues.py — **공짜로 주는 단서가 답까지 데려다주지 않게.**

■ 제보 (2026-08-30)
  "여섯 잔이라고 이미 해놔서 아메리카노의 니코틴이 범인 수법인 걸 다 알고 있잖아"

  제목이 「여섯 잔의 회의」다. 그리고 1라운드에 **공짜로** 주는 단서가 넷인데,
  그 넷이 이어지면 흉기 문제가 끝난다 —

      K1 검안   급성 중독 · **'S' 컵 잔량에서 검출**   ← 어느 잔인지까지 알려 줌
      K2 여섯 잔 **노린 잔이 처음부터 특정돼 있었다**   ← 결론까지 대신 내려 줌
      K3 자국   뚜껑을 열지 않고 **부어 넣은 자국**     ← 넣은 방법까지
      K4 명패   (트릭 조건 — 흉기와는 무관)

  제목이 잔을 가리키는데 첫 화면이 잔을 확정해 준다. 남는 일이 없다.

■ 고치는 방향 — **갈래 → 경로 → 물질**, 세 걸음으로 벌린다

      1라운드 공짜   K1 「마시는 것에 섞였다」        ← 갈래까지만. 컵인지 물병인지 모른다
      탐색해야 나옴  K3 「이 컵 뚜껑으로 들어갔다」    ← 경로 확정 + 가려야 했다는 사실
      더 파야 나옴   KD 「니코틴 원액 병」            ← 물질 확정 (결정타, 그대로)

  이렇게 벌리면 보기 다섯이 **차례로** 떨어진다 —
      · K1 뒤: 감전·교살 탈락 (셋 남음)
      · K3 뒤: 물병 탈락, 그리고 **무미무취한 수면제도 탈락**
               (가릴 까닭이 없는 독에 시럽을 부을 이유가 없다)
      · KD 뒤: 니코틴 확정

  K3이 이 사건의 **돌쩌귀**가 된다. 공짜로 줄 것이 아니었다.
"""
import json, argparse

TARGET = "scenarios/91_dsl_demo.json"

K1 = {
    "surface": ("【검안】 급성 중독 소견 — 심정지. 위 내용물에서 독물 성분이 검출됐다. "
                "다만 그날 그 방에는 아이스 아메리카노 여섯 잔과 개인 물병, 자판기 음료가 "
                "함께 오갔다 — 무엇에 섞여 들어갔는지는 이것만으로 알 수 없다."),
    "implies": ("weapon_class=급성 중독. 마시는 것에 섞였다. "
                "어느 잔이었는지는 아직 모른다 — 현장을 뒤져야 한다."),
}

K2 = {
    "surface": ("【현장】 테이블에 아이스 아메리카노 여섯 잔. 뚜껑의 주문 표시가 저마다 달라 "
                "누구 것인지 헷갈릴 일이 없다 — 샷추가 'S'는 회장 것 하나뿐이다."),
    "implies": "잔은 사람마다 정해져 있었다. 잘못 집어 들 여지가 없다.",
}

# ★이 사건의 돌쩌귀 — 이제 탐색해야 나온다
K3 = {
    "surface": ("【물증】 회장 컵 뚜껑에 빨대 구멍 말고 눌러 딴 자국이 하나 더 있다 — "
                "뚜껑을 열지 않고 무언가를 부어 넣은 자국이다. 잔 바닥에는 레몬시럽이 "
                "가라앉아 있다. 여섯 잔 중 시럽이 든 잔은 이것뿐인데, 주문 내역에 "
                "시럽 추가는 한 잔도 없다."),
    "implies": ("독이 들어간 길은 이 컵의 뚜껑이다 — 물병도 자판기도 아니다. "
                "그리고 **가려야 했던 독**이다: 맛도 냄새도 없는 것이었다면 "
                "시럽을 부어 넣을 까닭이 없다."),
}

ACTION = {
    "label": "회장 컵의 뚜껑을 살펴본다",
    "result_lines": [
        "회장 컵의 뚜껑을 살펴봤다.",
        "빨대 구멍 하나. 여기까지는 여느 잔과 다르지 않다.",
        "그런데 빛을 비스듬히 넣자 구멍이 하나 더 보인다 — 눌러 딴 자국이다.",
        "새로운 단서를 발견했다.",
    ],
    "highlight_last": True,
    "finds": "K3",
    "button": "단서 보기",
    "sfx": ["event_cues.search_hit", "event_cues.clue_found", "ui.audio.sfx.counter_up"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    s = json.load(open(TARGET, encoding="utf-8"))
    cards = {c["id"]: c for c in s["ui"]["clue_cards"]}

    for cid, new in (("K1", K1), ("K2", K2), ("K3", K3)):
        cl = next(c for c in s["clue_graph"] if c["id"] == cid)
        cl["surface"], cl["implies"] = new["surface"], new["implies"]
        card = cards.get(cid)
        if card:
            card["description"] = new["surface"].split("】", 1)[-1].strip()

    # K3 — 공짜에서 빼고 탐색으로 옮긴다
    k3 = next(c for c in s["clue_graph"] if c["id"] == "K3")
    k3["channel"] = "spine"        # crime_scene 이면 시작하자마자 수첩에 적힌다
    k3["reveal_round"] = 2         # 2라운드에 세미나실을 뒤져야 나온다
    k3["weight"] = "weapon"        # 흉기를 좁히는 단서다 (전에는 trick)
    k3["names_weapon"] = False     # 물질 이름은 대지 않는다 — 그건 KD의 몫
    card = cards.get("K3")
    if card:
        for f in (card.get("fields") or []):
            if f.get("label") == "획득 방법":
                f["value"] = "세미나실(중도 6층) 탐색으로 획득"
            if f.get("label") == "종류":
                f["value"] = "물증"

    # 세미나실 2라운드 조사 목록에 넣는다 (이미 있으면 갈아 끼운다)
    ps = next(p for p in s["ui"]["place_screens"] if "세미나실" in p["title"])
    acts = ps["rounds"].setdefault("2", {}).setdefault("actions", [])
    acts[:] = [x for x in acts if x.get("finds") != "K3"]
    # 소득 없는 행동 하나를 이것으로 바꾼다 — 조사 항목 수를 늘리지 않는다
    miss = next((i for i, x in enumerate(acts) if not x.get("finds")), None)
    if miss is None:
        acts.append(dict(ACTION))
    else:
        acts[miss] = dict(ACTION)

    if a.check:
        print("[K1 공짜]", K1["surface"][:80], "…")
        print("[K2 공짜]", K2["surface"][:80], "…")
        print("[K3 탐색]", K3["surface"][:80], "…")
        print("\n세미나실 2라운드 조사:")
        for x in acts:
            print("   ·", x["label"], "→", x.get("finds") or "—")
    else:
        json.dump(s, open(TARGET, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("91편 — 공짜 단서를 셋으로 줄이고 K3을 탐색으로 옮겼다.")


if __name__ == "__main__":
    main()
