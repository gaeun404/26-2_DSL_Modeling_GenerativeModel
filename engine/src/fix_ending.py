# -*- coding: utf-8 -*-
"""fix_ending.py — **엔딩을 그 사건의 사실로 다시 짓는다.**

■ 왜 (2026-08-29, 제보 — "엔딩이 너무 클로드 티 남. 재미없고, 납득할 만큼 자세해야지")
  50편의 엔딩이 **같은 다섯 줄**이었다. 이름과 장소만 바뀐다 —

      「이름이 불렸을 때, {범인}은 웃지도 부인하지도 않았다.」
      「{범인}은 그 밤의 일을 처음부터 되짚어 말했다. 길지 않았다.」
      「긴 밤이 밝았다.」

  '되짚어 말했다'고만 하고 **무슨 말을 했는지 적지 않았다.** 여운만 있고 사실이 없다.
  플레이어는 한 시간을 파고든 끝에 왔는데, 끝에서 듣는 것이 분위기뿐이면 허탈하다.

■ 무엇으로 짓나 (없는 사실을 지어내지 않는다)
  시나리오는 이미 `solution.reason` 에 **그 사건의 전모**를 갖고 있다(중앙값 349자).
  거기에 결정타 단서의 문면을 얹어, 엔딩이 세 가지를 말하게 한다 —

      ① 무엇을 했나   ② 왜 그랬나   ③ **어떻게 들켰나**

  ③이 핵심이다. 그것이 있어야 플레이어가 제 추리를 돌아보며 납득한다.
  빗나간 밤에는 **어디서 놓쳤는지**(끝내 펴 보지 않은 결정타)를 짚어 준다.
"""
import json, glob, re, argparse, os

SENT = re.compile(r"(?<=다\.)\s+|(?<=다\!)\s+")


def _jo(w, pair="이었다/였다"):
    """받침을 보고 고른다 — 「파우치」이었다 → 「파우치」였다."""
    a, b = pair.split("/")
    ch = str(w or " ")[-1]
    if not ("가" <= ch <= "힣"):
        return b
    return a if (ord(ch) - 0xAC00) % 28 else b


def _sents(t):
    return [x.strip() for x in SENT.split(str(t or "").strip()) if x.strip()]


def _place(s):
    pid = (s.get("death") or {}).get("place")
    for ps in (s.get("ui") or {}).get("place_screens") or []:
        if ps.get("place_id") == pid:
            return ps.get("title") or ""
    for p in (s.get("map") or {}).get("places") or []:
        if p.get("id") == pid:
            return p.get("name") or p.get("title") or ""
    return ""


def _decisive(s):
    """결정타 단서의 (이름, 문면)."""
    d = next((c for c in (s.get("clue_graph") or []) if c.get("decisive")), None)
    if not d:
        return None, None
    card = next((c for c in (s["ui"].get("clue_cards") or [])
                 if c.get("id") == d.get("id")), None)
    surf = re.sub(r"\s+", " ", str(d.get("surface") or "")).strip()
    if len(surf) > 110:
        surf = surf[:109].rstrip() + "…"
    return ((card or {}).get("name") or d.get("id")), surf


def build(s):
    cast = s.get("cast") or []
    cul = next((c for c in cast if c.get("is_culprit")), None)
    if not cul:
        return None
    who = cul.get("name") or "그"
    victim = (s.get("victim") or {}).get("name") or "피해자"
    place = _place(s)
    reason = str((s.get("solution") or {}).get("reason") or "")
    reason = re.sub(r"\(허구[^)]*\)", "", reason).strip()
    ss = _sents(reason)
    if not ss:
        return None
    dname, dsurf = _decisive(s)

    # reason 은 대개 [무엇을 왜 했나] … [무엇이 그를 가리킨다] 로 끝난다.
    # 가리키는 문장을 뒤에서 찾아 갈라 둔다 — 그것이 '어떻게 들켰나'다.
    point_i = None
    for i in range(len(ss) - 1, -1, -1):
        if re.search(r"(가리킨다|가리켰다|드러난다|건져 낸다|남는다)\.?$", ss[i]):
            point_i = i
            break
    did = ss[:point_i] if point_i is not None else ss[:-1] or ss
    caught_by = ss[point_i:] if point_i is not None else ss[-1:]

    lamp_on = f"{place}의 불이 모두 켜졌다." if place else "방의 불이 모두 켜졌다."
    lamp_off = f"{place}의 불이 하나씩 꺼졌다." if place else "방의 불이 하나씩 꺼졌다."

    caught = [f"이름이 불렸을 때, {who}는 웃지도 부인하지도 않았다.",
              f"「…언제부터 알고 계셨습니까.」 그것이 {who}의 첫 마디였다.",
              "그리고 그 밤의 일을 처음부터 되짚었다."]
    caught += did
    if dname and dsurf:
        caught.append(f"{who}를 끝내 앉힌 것은 「{dname}」{_jo(dname)} — {dsurf}")
    caught += caught_by
    caught.append(lamp_on)

    escaped = [f"이름이 불린 사람은 그 자리에서 아니라고 했다.",
               f"그리고 그 말은 사실이었다. — 그날 밤 {victim}에게 손을 댄 사람은 {who}다."]
    escaped += did
    if dname and dsurf:
        escaped.append(f"끝내 펴 보지 않은 것이 하나 있었다. 「{dname}」 — {dsurf}")
    escaped += caught_by
    # ★빠져나간 밤에는 **범인이 자리를 뜨는 장면**을 넣는다 (2026-08-30, 제보 —
    #   "추리 실패하면 FAIL 뜨고 범인 튀는 장면 있으면 좋겠다").
    #   붙잡히는 그림만 있고 놓치는 그림이 없으면, 실패가 그냥 '아무 일 없음'이 된다.
    escaped += [f"{who}는 남은 이들 사이에 섞여 서 있었다. 아무도 그를 보지 않았다.",
                f"{who}가 먼저 자리를 떴다. 문을 나서는 걸음이 조금 빨랐다.",
                "복도 끝에서 발소리가 멀어지고, 비상구 문이 한 번 여닫혔다.",
                lamp_off, "아침이 왔고, 아무 일도 없었다는 듯 하루가 시작됐다."]
    return caught, escaped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--scenario", default=None)
    a = ap.parse_args()
    files = ([f"scenarios/{a.scenario}"] if a.scenario else
             [f for f in sorted(glob.glob("scenarios/*.json")) if "catalog" not in f])
    n = 0
    for f in files:
        s = json.load(open(f, encoding="utf-8"))
        r = build(s)
        if not r:
            continue
        caught, escaped = r
        br = (s.setdefault("ending", {}).setdefault("branches", {}))
        br.setdefault("caught", {}).setdefault("label", "붙잡힌 밤")
        br.setdefault("escaped", {}).setdefault("label", "빠져나간 밤")
        if a.check:
            print(f"── {os.path.basename(f)}  [붙잡힌 밤]")
            for x in caught:
                print("   ", x)
            print()
        else:
            br["caught"]["beats"] = caught
            br["escaped"]["beats"] = escaped
            json.dump(s, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        n += 1
    print(f"\n{'고칠' if a.check else '고친'} 엔딩 {n}편")


if __name__ == "__main__":
    main()
