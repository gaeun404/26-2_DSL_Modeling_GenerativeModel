# -*- coding: utf-8 -*-
"""make_documents.py — **단서를 물건으로 만든다.** 문면을 지어 넣는다.

■ 왜
  단서가 「장부가 있다」로 끝나면 읽을 것이 없다. **장부를 펴 보여야** 추리다.
  91편은 손으로 지어 넣었고(`docs_91.py`), 나머지 편은 이 스크립트가 채운다.

■ 무엇을 채우나
  clue_graph[].document = {kind, title, meta[], body[]}
  cast[].secrets[].document = 같은 모양

  **문서로 보여 줄 만한 것만** 채운다 — medium 이 문서·장부·서찰·검안서·기록인 것.
  목격담·소문·흔적은 물건이 아니므로 건드리지 않는다.

■ 지키는 것 (프롬프트에 박아 둔다)
  · surface 에 이미 적힌 사실과 **어긋나지 않게**. 없는 사실을 보태지 않는다.
  · 범인·수법·동기를 **새로 흘리지 않는다**. 미끼는 미끼로 남긴다.
  · 요약하지 말고 **그 문서가 실제로 그렇게 생겼을 모양**으로 적는다.

사용:
    python3 src/make_documents.py --check                 # 몇 장이 비어 있나
    python3 src/make_documents.py --scenario 07_hansel_gretel.json
    python3 src/make_documents.py                         # 전 편 (키 필요)
    python3 src/make_documents.py --limit 20              # 한 번에 20장만
"""
import json, glob, os, sys, argparse, re

sys.path.insert(0, os.path.dirname(__file__))

PAPER = {"문서", "장부", "서찰", "검안서", "기록", "일지", "편지", "명부", "영수증"}

SYS = """너는 추리 게임의 소품을 만든다. 단서 하나를 **실물 문서**로 적는다.

지켜라
· 주어진 '한 줄 설명'에 적힌 사실과 어긋나지 않게 쓴다. 없는 사실을 새로 지어내지 마라.
· 누가 범인인지, 어떤 수법이었는지 **절대 새로 밝히지 마라.** 너는 모른다.
· 요약하지 마라. 그 문서가 실제로 그렇게 생겼을 모양 그대로 적는다.
· 시대와 배경에 맞는 말투와 서식을 쓴다.

형식 — JSON 하나만 답한다. 다른 말은 붙이지 마라.
{"kind":"장부","title":"…","meta":["…"],"body":["…","…"]}
  kind  문서의 종류 (장부·서찰·검안서·메모·일지·영수증 …)
  title 화면에 뜰 이름
  meta  작성 시각·쪽수 같은 곁정보 0~2줄 (없으면 빈 배열)
  body  문면 그 자체. 6~14줄. 표라면 줄 맞춰 적는다."""


def prompt(s, cl):
    m = s.get("meta", {})
    return (f"[배경] {m.get('era','')} · {m.get('origin','')} · {m.get('title','')}\n"
            f"[이 단서의 매체] {cl.get('medium')}\n"
            f"[한 줄 설명 — 이것과 어긋나면 안 된다]\n{cl.get('surface')}\n"
            f"[찾은 곳] {cl.get('location') or '—'}\n\n"
            "이 문서의 문면을 적어라.")


def parse(txt):
    t = str(txt or "").strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        return None
    try:
        d = json.loads(t[i:j + 1])
    except Exception:
        return None
    if not isinstance(d, dict) or not d.get("body"):
        return None
    body = [str(x) for x in (d.get("body") or []) if str(x).strip()]
    if len(body) < 3:
        return None
    return {"kind": str(d.get("kind") or "문서")[:12],
            "title": str(d.get("title") or "")[:40],
            "meta": [str(x)[:40] for x in (d.get("meta") or [])][:2],
            "body": body[:16]}


def targets(s):
    """문면을 채울 자리 — (붙일 dict, 프롬프트용 단서) 쌍."""
    out = []
    for cl in (s.get("clue_graph") or []):
        if cl.get("document"):
            continue
        if (cl.get("medium") or "") in PAPER:
            out.append((cl, cl))
    for c in (s.get("cast") or []):
        for sec in (c.get("secrets") or []):
            if sec.get("document"):
                continue
            tx = str(sec.get("text") or "")
            # 물건이 등장하는 비밀만 (파일·문서·장부·편지·표…)
            if re.search(r"(pptx|docx|파일|문서|장부|편지|서찰|명부|일지|영수증|기록|안건|계약|메모)", tx):
                out.append((sec, {"medium": "문서", "surface": tx,
                                  "location": c.get("name")}))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default=None)
    ap.add_argument("--check", action="store_true", help="세어만 본다")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    files = ([f"scenarios/{a.scenario}"] if a.scenario
             else [f for f in sorted(glob.glob("scenarios/*.json")) if "catalog" not in f])

    if a.check:
        tot = have = 0
        for f in files:
            s = json.load(open(f, encoding="utf-8"))
            t = targets(s)
            n_have = sum(1 for cl in (s.get("clue_graph") or []) if cl.get("document"))
            tot += len(t); have += n_have
            if t:
                print(f"  {os.path.basename(f):28s} 채울 자리 {len(t):3d} · 이미 있음 {n_have}")
        print(f"\n총 채울 자리 {tot}장 · 이미 있는 문면 {have}장")
        return

    import play_agents as PA
    llm = PA.open_llm(tokens=900)
    if not llm:
        print("키가 없습니다 — .apikey 파일이나 MM_API_KEY 환경변수를 주세요.")
        return

    done = 0
    for f in files:
        s = json.load(open(f, encoding="utf-8"))
        t = targets(s)
        if not t:
            continue
        ch = 0
        for node, src in t:
            if a.limit and done >= a.limit:
                break
            try:
                txt = llm.chat([{"role": "system", "content": SYS},
                                {"role": "user", "content": prompt(s, src)}])
            except Exception as e:
                print("   ! 실패:", str(e)[:60]); continue
            d = parse(txt)
            if d:
                node["document"] = d; ch += 1; done += 1
        if ch:
            json.dump(s, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"  {os.path.basename(f):28s} 문면 {ch}장")
        if a.limit and done >= a.limit:
            break
    print(f"\n모두 {done}장 지어 넣었다.")


if __name__ == "__main__":
    main()
