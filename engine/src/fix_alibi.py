# -*- coding: utf-8 -*-
"""fix_alibi.py — **알리바이를 대조할 수 있게 만든다.**

■ 왜 (2026-08-29, 시연 제보 — "알리바이가 너무 애매함")
  여태 알리바이는 다섯이 같은 틀이었다 —
      「저는 초저녁엔 「A」, 밤엔 「B」에 있었어요. C가 곁에 있었어요.」
  세 가지가 잘못이다.
    ① 시간이 「초저녁·밤」 두 덩어리뿐이다. 사건은 분 단위로 벌어지는데
       알리바이가 뭉뚱그려져 있으니 **대조할 것이 없다.** 이게 '애매하다'의 정체다.
    ② **하던 일이 없다.** 「복도에 있었다」로는 더 캐물을 거리가 생기지 않는다.
    ③ 다섯이 같은 문형이라 누구 말인지 구별되지 않고,
       「하필 곁엔 아무도 없었어요」가 여럿에게 반복되어 되레 광고가 된다.

■ 어떻게 고치나
  시나리오는 이미 `timeline_events` 에 **분 단위 그날 밤**을 갖고 있다.
  거기서 그 사람 몫을 뽑아 **시각 + 하던 일**로 다시 쓴다. 없는 사실은 안 보탠다.

■ 스포일러 규칙 (중요)
  · 범인은 **제 입으로 진실을 말하지 않는다.** 범인의 알리바이는 `lies[].claim`
    (그가 준비해 둔 커버스토리)으로 짓는다. CCTV 같은 객관 기록에만 남은 움직임은
    알리바이에 넣지 않는다 — 그건 플레이어가 찾아내서 들이대야 할 몫이다.
  · 무고한 사람도 **제 진술로 남은 것**만 말한다.
"""
import json, glob, re, argparse, os

# 말끝을 그대로 이어 쓰기 위해 기존 알리바이에서 어미를 뽑는다
# 말끝 — 기존 알리바이에서 알아내어 그대로 이어 쓴다
TAIL = [("있었습니다", "습니다"), ("있었답니다", "답니다"), ("있었어요", "어요"),
        ("있었소", "소"), ("있었네", "네"), ("있었다", "다")]


def voice(old):
    for mark, suf in TAIL:
        if mark in str(old or ""):
            return suf
    return "어요"


def conj(t, suf, last=True):
    """서술을 그 말끝으로 활용한다. 「픽업했다」+어요 → 「픽업했어요」"""
    t = re.sub(r"[\s.。]+$", "", str(t or ""))
    if t.endswith("한다"):
        stem = t[:-2] + "했"
    elif re.search(r"(했다|았다|었다|였다)$", t):
        stem = t[:-1]
    elif t.endswith("다"):
        stem = t[:-1]
        # 이미 과거(ㅆ 받침)면 '었'을 덧붙이지 않는다 — 「기다렸」+었 = 「기다렸었」
        if not (stem and "가" <= stem[-1] <= "힣" and (ord(stem[-1]) - 0xAC00) % 28 == 20):
            stem += "었"
    else:
        stem = t + "했" if not t.endswith(("었", "았", "했")) else t
    if not last:
        return stem + "고"                     # 가운데 마디는 이어 붙인다
    return stem + ("다" if suf == "다" else suf)


def companion(old):
    """곁에 누가 있었다고 했는지 — 그 구절을 그대로 살린다."""
    m = re.search(r"([^.]*곁[^.]*\.)", str(old or ""))
    return m.group(1).strip() if m else ""


def _clip(t, n=34):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    t = re.sub(r"\s*—.*$", "", t)               # 작가 주석 꼬리 제거
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def build(s, c):
    """이 인물의 알리바이를 시간표에서 다시 짓는다."""
    old = str(c.get("alibi_narration") or "")
    suf = voice(old)
    ev = [e for e in (s.get("timeline_events") or []) if e.get("who") == c["id"]]
    # 본인이 제 입으로 말할 수 없는 것은 뺀다 — 녹음·CCTV에만 남은 관찰
    ev = [e for e in ev if not re.search(r"(녹음|CCTV|촬영본|타임스탬프)", str(e.get("text")))]

    # 범인은 제 커버스토리로 말한다 — 객관 기록에 남은 움직임은 말하지 않는다
    if c.get("is_culprit"):
        claim = ""
        for li in (c.get("lies") or []):
            if li.get("claim"):
                claim = str(li["claim"]); break
        ev = [e for e in ev if "진술" in str(e.get("known_from") or "")]
        raw = [(e.get("time"), _clip(e.get("text"))) for e in ev[:1]]
        if claim:
            raw.append((None, _clip(claim, 44)))
    else:
        mine = [e for e in ev if "진술" in str(e.get("known_from") or "")] or ev
        raw = [(e.get("time"), _clip(e.get("text"))) for e in mine[:2]]

    if not raw:
        return None
    chunks = []
    for i, (tm, tx) in enumerate(raw):
        last = (i == len(raw) - 1)
        head = f"{tm}쯤엔 " if tm else ""
        chunks.append(head + conj(tx, suf, last))
    sent = ", ".join(chunks) + "."
    sent = re.sub(r"\s+", " ", sent).replace("..", ".")
    comp = companion(old)
    return (sent + (" " + comp if comp else "")).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--scenario", default=None)
    a = ap.parse_args()
    files = ([f"scenarios/{a.scenario}"] if a.scenario else
             [f for f in sorted(glob.glob("scenarios/*.json")) if "catalog" not in f])
    n = 0
    for f in files:
        s = json.load(open(f, encoding="utf-8")); ch = 0
        for c in (s.get("cast") or []):
            nw = build(s, c)
            if nw and nw != c.get("alibi_narration"):
                if a.check and ch < 5:
                    print(f"   {c['name']}")
                    print(f"     전: {c.get('alibi_narration')}")
                    print(f"     후: {nw}")
                else:
                    c["alibi_narration"] = nw
                ch += 1; n += 1
        if ch and not a.check:
            json.dump(s, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        if ch and a.check:
            print(f"── {os.path.basename(f)}\n")
    print(f"\n{'고칠' if a.check else '고친'} 알리바이 {n}개")


if __name__ == "__main__":
    main()
