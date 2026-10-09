# -*- coding: utf-8 -*-
"""
alibi.py — **알리바이는 채팅이 아니라 첫 대면의 진술로 준다.**

■ 왜 (2026-08-25)
  지금까지 플레이어는 "그 밤에 어디 있었소"를 다섯 번 물어야 했다. 예산 8 가운데
  다섯이 동선 확인에만 날아갔고, 정작 **아는 것을 바탕으로 파고드는 질문**을 할
  여유가 없었다. 게다가 다섯 사람의 동선을 채팅 로그에서 되짚어야 해서 헷갈렸다.

      바뀐 것 — 인물을 **처음 만나면** 그 자리에서 알리바이를 짧게 말한다.
                예산 0. 수첩에도 그대로 박힌다.
                채팅은 **그 진술을 알고 나서** 파고드는 자리가 된다.

■ 왜 다시 만드나 (고쳐 쓰지 않고)
  기존 alibi_narration은 말투 변환기를 거치며 250개 중 101개가 제 말체와 어긋났다.
  91편은 아예 깨져 있었다 — "찍혔을걸습니다?", "암전 때니다?", "잤어니다".
  문장을 손보는 것보다 **동선에서 다시 짓는 편**이 맞다. 동선은 스키마의 사실이고,
  말체는 persona.voice가 이미 갖고 있으니 둘을 합치면 된다.

■ 만드는 규칙
  · 두 문장을 넘지 않는다. 첫 문장은 동선, 둘째 문장은 **본 사람이 있는가**.
  · 범인은 거짓 동선(lies[0].false_place)을 댄다 — 진짜를 대면 자백이 된다.
  · 사망 시각을 **반드시** 포함한다. 그 칸이 비면 알리바이가 아니다.
  · 비밀·동기는 한 글자도 넣지 않는다.

사용:
    python3 alibi.py                     # 전 편
    python3 alibi.py out/91_dsl_demo.json
    python3 alibi.py --check             # 고치지 않고 점검만
"""
import json, glob, re, sys

# 말체 → (과거 종결어미, 자칭). '있었'·'없었'·'봤' 뒤에 그대로 붙는다.
FORM = {
    "해요체": ("어요", "저"),   "다정체": ("어요", "저"),   "설명체": ("어요", "저"),
    "반존대": ("어요", "나"),   "완곡체": ("네요", "저"),
    "합쇼체": ("습니다", "저"), "격식체": ("습니다", "저"), "합니다체": ("습니다", "저"),
    "건조체": ("습니다", "저"),
    "하오체": ("소", "나"),     "정중체": ("소", "나"),
    "올시다체": ("소이다", "저"), "탄식체": ("더이다", "나"),
    "공손체": ("답니다", "저"), "소인체": ("사옵니다", "소인"),
    "하게체": ("네", "나"),     "노숙체": ("네", "나"),
    "노라체": ("노라", "나"),
}
_DEFAULT = ("습니다", "저")

_J_EUN = lambda w: ("은" if _bat(w) else "는")
_J_I = lambda w: ("이" if _bat(w) else "가")


def _bat(w):
    ch = (w or " ")[-1]
    return "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28


def _witness_of(s, c):
    """이 인물을 봤다고 적혀 있는 사람. 같은 시각 같은 곳에 있던 이를 고른다.
    ★없으면 없는 대로 둔다 — '아무도 못 봤다'가 오히려 판을 만든다."""
    dslot = s["death"]["time_slot"]
    mine = (c.get("timeline") or {}).get(dslot)
    if not mine:
        return None
    for x in s["cast"]:
        if x["id"] == c["id"] or x.get("is_culprit"):
            continue
        if (x.get("timeline") or {}).get(dslot) == mine:
            return x["name"]
    return None


def build_line(s, c):
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    slots = s.get("time_slots") or []
    dslot = s["death"]["time_slot"]
    end, me = FORM.get(((c.get("persona") or {}).get("voice") or {}).get("form", ""), _DEFAULT)

    # 범인은 커버스토리를 댄다
    tl = dict(c.get("timeline") or {})
    if c.get("is_culprit") and (c.get("lies") or []):
        fp = (c["lies"][0] or {}).get("false_place")
        if fp:
            tl[dslot] = fp

    # 사망 시각은 반드시, 그리고 그 앞뒤로 한 칸만 더
    order = [dslot] + [x for x in slots if x != dslot]
    picked = []
    for sl in order:
        if sl in tl and pn.get(tl[sl]):
            picked.append((sl, pn[tl[sl]]))
        if len(picked) == 2:
            break
    if not picked:
        return ""
    picked.sort(key=lambda x: slots.index(x[0]) if x[0] in slots else 9)

    # 두 칸이 **같은 곳**이면 한 번만 말한다 — "밤엔 A, 새벽엔 A"는 사람 말이 아니다
    if len(picked) == 2 and picked[0][1] == picked[1][1]:
        where = f"{picked[0][0]}부터 {picked[1][0]}까지 「{picked[0][1]}」"
    else:
        where = ", ".join(f"{sl}엔 「{pl}」" for sl, pl in picked)
    s1 = f"{me}{_J_EUN(me)} {where}에 있었{end}."

    w = _witness_of(s, c)
    s2 = (f"{w}{_J_I(w)} 곁에 있었{end}." if w else f"하필 곁엔 아무도 없었{end}.")
    return f"{s1} {s2}"


def enrich(path, check=False):
    s = json.load(open(path, encoding="utf-8"))
    n_fix = 0
    lines = {}
    for c in s["cast"]:
        line = build_line(s, c)
        if not line:
            continue
        lines[c["id"]] = line
        if c.get("alibi_narration") != line:
            n_fix += 1
        if not check:
            c["alibi_narration"] = line

    if not check:
        # 인물 카드에 그대로 박고, **처음 만나면 자동으로 말한다**고 표시한다
        for card in (s.get("ui") or {}).get("suspect_cards", []):
            ln = lines.get(card.get("id"))
            if not ln:
                continue
            card["alibi_quote"] = "“" + ln + "”"
            card["alibi_label"] = "알리바이"
            card["alibi_on_first_meet"] = {
                "auto": True, "cost": 0,
                "when": "이 인물을 처음 만나는 순간(장소에서든 수첩에서든) 자동으로 한 번",
                "how": "초상 옆 말풍선으로 이 문장을 띄운다. 건너뛸 수 있다.",
                "then": "하단 내비 [용의자] 화면에 그대로 박히고, 다시 묻지 않아도 언제든 볼 수 있다.",
                "note": "채팅으로 동선을 되묻게 하지 마라 — 예산만 먹고 헷갈린다. "
                        "채팅은 이 진술을 **알고 나서** 파고드는 자리다.",
            }
            # '관계' 칸이 신분을 두 번 적던 것을 바로잡는다
            for f in (card.get("fields") or []):
                if f.get("label") == "관계":
                    v = str(f.get("value") or "")
                    head = v.split(" — ")[0].strip()
                    if head and v.count(head) > 1:
                        f["value"] = v.split(" — ", 1)[1].strip() if " — " in v else v
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"  {path.split('/')[-1][:28]:30s} 알리바이 {len(lines)}명 · 새로 지은 것 {n_fix}")
    return n_fix


if __name__ == "__main__":
    check = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    tot = sum(enrich(f, check) for f in files)
    print(f"\n{len(files)}편 · 다시 지은 알리바이 {tot}개")
