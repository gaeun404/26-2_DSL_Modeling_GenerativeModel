# -*- coding: utf-8 -*-
"""
art_handoff.py — **그림 그리는 사람에게 넘길 한 장짜리 명세를 뽑는다.**

시나리오 JSON 안에 흩어져 있는 그림 지시를 한 곳에 모아 HTML로 낸다.
JSON을 열어 보지 않아도 무엇을 몇 장 그려야 하는지, 각 장에 무엇이
반드시 보여야 하는지, 영어 프롬프트가 무엇인지 그 자리에서 알 수 있게 한다.

같이 나가는 것:
    docs/91_이미지명세.html   보는 문서
    docs/91_이미지목록.csv     파일명·크기 목록(작업 관리용)

사용:
    python3 art_handoff.py                       # 91편
    python3 art_handoff.py ../scenarios/xx.json
"""
import json, sys, csv, html, os

OUT_HTML = "../docs/91_이미지명세.html"
OUT_CSV = "../docs/91_이미지목록.csv"


def rows(s):
    """그려야 할 것 전부를 한 줄씩."""
    ui = s["ui"]
    out = []

    for ps in ui.get("place_screens", []):
        a = ps.get("art") or {}
        out.append(dict(
            group="장소 배경", key=ps["place_id"], title=ps["title"],
            file=f"91_place_{ps['place_id']}.png", w=a.get("w"), h=a.get("h"),
            must=a.get("must_show") or [], ko=a.get("prompt_ko", ""),
            en=a.get("prompt_en", ""), neg=a.get("negative_en", ""),
            note=a.get("reserve", ""), variants=a.get("variants") or {}))
        m = ps.get("map_thumb") or {}
        out.append(dict(
            group="지도 썸네일", key=ps["place_id"], title=f"{ps['title']} — 지도 아이콘",
            file=f"91_map_{ps['place_id']}.png", w=m.get("w"), h=m.get("h"),
            must=[], ko=m.get("prompt_ko", ""), en=m.get("prompt_en", ""),
            neg=m.get("negative_en", ""), note="", variants={}))

    for card in ui.get("clue_cards", []):
        t = card.get("thumb") or {}
        if not t:
            continue
        out.append(dict(
            group="단서 카드", key=card["id"], title=f"{card['id']} · {card.get('name','')}",
            file=f"91_clue_{card['id']}.png", w=t.get("w"), h=t.get("h"),
            must=[f"촬영 — {t.get('shot','')}", f"초점 — {t.get('focus','')}"],
            ko=t.get("prompt_ko", ""), en=t.get("prompt_en", ""),
            neg=t.get("negative_en", ""), note=card.get("list_sub", ""), variants={}))

    for pg in (ui.get("narration") or {}).get("pages", []):
        img = pg.get("image") or {}
        out.append(dict(
            group="오프닝 삽화", key=f"{pg.get('page')}쪽",
            title=f"{pg.get('page')}쪽 — {pg.get('text','')[:34]}…",
            file=img.get("file") or f"91_open_{int(pg.get('page') or 0):02d}.png",
            w=img.get("w"), h=img.get("h"), must=[],
            ko=img.get("prompt_ko", ""), en=img.get("prompt_en", ""),
            neg=img.get("negative_en", ""), note=pg.get("text", ""), variants={}))

    for cut in (ui.get("murder_reenactment") or {}).get("cuts", []):
        img = cut.get("image") or {}
        out.append(dict(
            group="범행 재연", key=f"{cut.get('no')}컷", title=f"{cut.get('no')}. {cut.get('label','')}",
            file=img.get("file") or f"91_reenact_{cut.get('no')}.png",
            w=img.get("w"), h=img.get("h"), must=[],
            ko=img.get("prompt_ko", ""), en=img.get("prompt_en", ""),
            neg=img.get("negative_en", ""), note=cut.get("text", ""), variants={}))

    ba = (ui.get("victim_card") or {}).get("body_art") or {}
    if ba:
        out.append(dict(
            group="현장", key="현장", title="사건 뒤의 세미나실 (주검 없음)",
            file=ba.get("file", "91_scene_after.png"), w=ba.get("w"), h=ba.get("h"),
            must=[], ko=ba.get("prompt_ko", ""), en=ba.get("prompt_en", ""),
            neg=ba.get("negative_en", ""), note=ba.get("rule", ""), variants={}))
    return out


def build(path):
    s = json.load(open(path, encoding="utf-8"))
    rs = rows(s)
    photos = (s.get("assets") or {}).get("photos") or {}
    e = html.escape

    groups = []
    for g in ["장소 배경", "지도 썸네일", "단서 카드", "오프닝 삽화", "범행 재연", "현장"]:
        items = [r for r in rs if r["group"] == g]
        if items:
            groups.append((g, items))

    def card(r):
        must = "".join(f"<li>{e(x)}</li>" for x in r["must"])
        var = ""
        for k, v in (r["variants"] or {}).items():
            if not isinstance(v, dict):
                continue
            var += (f"<div class='var'><b>{e(k)}</b> — {e(v.get('when',''))}"
                    f"<p>{e(v.get('diff',''))}</p>"
                    f"<code>+ {e(v.get('prompt_en_add',''))}</code></div>")
        return f"""
        <article class="spec" id="{e(r['file'])}">
          <header>
            <div class="slot"><span class="chip">{e(str(r['key']))}</span>
              <span class="size">{r['w']}×{r['h']}</span></div>
            <h3>{e(r['title'])}</h3>
            <div class="file"><code>{e(r['file'])}</code></div>
          </header>
          {f'<p class="src">{e(r["note"])}</p>' if r["note"] else ''}
          {f'<ul class="must">{must}</ul>' if must else ''}
          <div class="block"><span class="lab">지시</span><p>{e(r['ko'])}</p></div>
          <div class="block"><span class="lab">prompt</span>
            <pre data-copy>{e(r['en'])}</pre></div>
          <details><summary>넣지 말 것 (negative)</summary><pre data-copy>{e(r['neg'])}</pre></details>
          {var}
        </article>"""

    body = ""
    for g, items in groups:
        body += (f"<section id='g{e(g)}'><div class='ghead'><h2>{e(g)}</h2>"
                 f"<span class='count'>{len(items)}장</span></div>"
                 + "".join(card(r) for r in items) + "</section>")

    total = len(rs)
    nav = "".join(f"<a href='#g{e(g)}'>{e(g)} <b>{len(i)}</b></a>" for g, i in groups)
    photo_rows = "".join(
        f"<tr><td>{e(k)}</td><td><code>{e(v)}</code></td></tr>" for k, v in photos.items())

    doc = f"""<title>여섯 잔의 회의 · 이미지 명세</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@300;400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --bg:#F1F3F5; --card:#FFFFFF; --ink:#15181D; --muted:#61686F; --line:#DCE0E5;
  --accent:#166B80; --accent-soft:#E3F0F3; --warn:#9C4A18; --warn-soft:#F7EBE2;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg:#0E1114; --card:#161A1F; --ink:#E6E9EC; --muted:#98A1AA; --line:#242B32;
    --accent:#6FCADE; --accent-soft:#13303A; --warn:#E0A277; --warn-soft:#33231A;
  }}
}}
:root[data-theme="dark"] {{
  --bg:#0E1114; --card:#161A1F; --ink:#E6E9EC; --muted:#98A1AA; --line:#242B32;
  --accent:#6FCADE; --accent-soft:#13303A; --warn:#E0A277; --warn-soft:#33231A;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font-family:"IBM Plex Sans KR",system-ui,-apple-system,sans-serif; font-weight:300;
  line-height:1.7; -webkit-font-smoothing:antialiased; }}
code,pre {{ font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; }}
.wrap {{ max-width:1080px; margin:0 auto; padding:0 24px 96px; }}
header.top {{ padding:64px 0 28px; border-bottom:1px solid var(--line); }}
header.top .eyebrow {{ font-size:12px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); font-weight:600; }}
h1 {{ font-size:clamp(28px,4vw,40px); font-weight:600; letter-spacing:-.02em;
  margin:10px 0 6px; text-wrap:balance; }}
header.top p {{ margin:0; color:var(--muted); max-width:62ch; }}
.tally {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:22px; }}
.tally a {{ display:flex; align-items:center; gap:8px; text-decoration:none; color:var(--ink);
  background:var(--card); border:1px solid var(--line); border-radius:999px;
  padding:7px 15px; font-size:13px; }}
.tally a b {{ color:var(--accent); font-weight:600; font-variant-numeric:tabular-nums; }}
.tally a:hover {{ border-color:var(--accent); }}
.rules {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:24px 26px; margin:34px 0 10px; }}
.rules h2 {{ font-size:15px; font-weight:600; margin:0 0 14px; letter-spacing:-.01em; }}
.rules ul {{ margin:0; padding-left:18px; }}
.rules li {{ margin-bottom:9px; }}
.flag {{ background:var(--warn-soft); border-left:3px solid var(--warn); border-radius:0 8px 8px 0;
  padding:16px 20px; margin:18px 0 0; }}
.flag b {{ color:var(--warn); font-weight:600; }}
table {{ width:100%; border-collapse:collapse; margin-top:14px; font-size:14px; }}
td,th {{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); }}
section {{ margin-top:56px; scroll-margin-top:20px; }}
.ghead {{ display:flex; align-items:baseline; gap:12px; padding-bottom:10px;
  border-bottom:2px solid var(--ink); margin-bottom:22px; }}
.ghead h2 {{ font-size:20px; font-weight:600; margin:0; letter-spacing:-.01em; }}
.count {{ color:var(--muted); font-size:13px; font-variant-numeric:tabular-nums; }}
.spec {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:22px 24px; margin-bottom:16px; scroll-margin-top:20px; }}
.spec header {{ display:grid; grid-template-columns:auto 1fr; gap:4px 16px; align-items:start;
  margin-bottom:14px; }}
.slot {{ display:flex; flex-direction:column; gap:6px; align-items:flex-start; }}
.chip {{ background:var(--accent-soft); color:var(--accent); font-weight:600; font-size:12px;
  padding:3px 10px; border-radius:5px; font-family:"IBM Plex Mono",monospace; }}
.size {{ font-size:11px; color:var(--muted); font-variant-numeric:tabular-nums; }}
.spec h3 {{ font-size:16px; font-weight:600; margin:0; letter-spacing:-.01em; }}
.file {{ grid-column:2; font-size:12px; color:var(--muted); }}
.src {{ color:var(--muted); font-size:14px; margin:0 0 12px; padding-left:12px;
  border-left:2px solid var(--line); }}
ul.must {{ margin:0 0 14px; padding-left:18px; font-size:14px; }}
ul.must li {{ margin-bottom:4px; }}
.block {{ display:grid; grid-template-columns:64px 1fr; gap:14px; margin-bottom:10px;
  align-items:start; }}
.lab {{ font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted);
  padding-top:5px; }}
.block p {{ margin:0; font-size:14.5px; }}
pre {{ margin:0; background:var(--bg); border:1px solid var(--line); border-radius:7px;
  padding:12px 14px; font-size:12.5px; line-height:1.65; white-space:pre-wrap;
  word-break:break-word; cursor:copy; position:relative; }}
pre:hover {{ border-color:var(--accent); }}
pre.copied::after {{ content:"복사됨"; position:absolute; top:6px; right:8px; font-size:11px;
  color:var(--accent); }}
details {{ margin-top:10px; }}
summary {{ cursor:pointer; font-size:12.5px; color:var(--muted); }}
.var {{ margin-top:12px; padding:12px 14px; background:var(--accent-soft); border-radius:7px;
  font-size:13.5px; }}
.var p {{ margin:6px 0; }}
.var code {{ font-size:12px; }}
footer {{ margin-top:64px; padding-top:20px; border-top:1px solid var(--line);
  color:var(--muted); font-size:13px; }}
</style>
<div class="wrap">
<header class="top">
  <div class="eyebrow">DSL 시연편 · 이미지 발주</div>
  <h1>「여섯 잔의 회의」 그릴 것 {total}장</h1>
  <p>연세대 중앙도서관 6층, 2020년대. 이 편은 중간발표 시연에 나가므로 장소·단서·삽화를 틀에서
     뽑지 않고 한 장씩 손으로 썼습니다. 아래 지시와 프롬프트를 그대로 쓰시면 됩니다.
     회색 상자를 누르면 복사됩니다.</p>
  <nav class="tally">{nav}</nav>
</header>

<div class="rules">
  <h2>이 편의 결 — 다섯 장 그리기 전에</h2>
  <ul>
    <li><b>촛불·등불·한복·사극은 없습니다.</b> 시험기간 밤 열 시의 대학 도서관입니다.
        천장 형광등(4000K 언저리)과 노트북·빔 스크린의 푸른 화면빛이 섞이고,
        그림자가 옅고, 창유리에 실내가 되비칩니다.</li>
    <li><b>사람을 그리지 않습니다.</b> 인물은 실사 사진 여섯 장이 따로 있습니다.
        장면은 빈 자리와 놓인 물건으로 말합니다.</li>
    <li><b>주검도 그리지 않습니다.</b> 뒤로 밀려난 의자 하나와 기울어진 잔으로만 씁니다.
        피는 어떤 형태로도 그리지 않습니다.</li>
    <li><b>한글을 그리지 않습니다.</b> 생성 모델이 쓴 한글은 깨집니다.
        글자가 필요한 자리는 <b>줄과 칸의 구조만</b> 남기고, 실제 문구는 UI가 위에 얹습니다.</li>
    <li><b>장소 배경은 왼쪽 아래 3분의 1을 비웁니다.</b> 인물 서 있는 컷이 그 위에 겹칩니다.</li>
  </ul>
  <div class="flag">
    <b>실존 인물 관련</b> — 이 편의 여섯 인물은 DSL 실제 구성원이고, 초상은 본인 사진입니다.
    얼굴을 생성하거나 표정을 합성하지 않습니다. 배경 지우기와 크기 맞추기만 합니다.
    사건·비밀·동기는 전부 허구이며, 시연·녹화·배포 전에 여섯 분 전원의 동의가 필요합니다.
    <table><tr><th>인물</th><th>파일</th></tr>{photo_rows}</table>
  </div>
</div>

{body}

<footer>
  프롬프트는 시나리오 JSON에서 그대로 뽑았습니다 — 문서와 게임 데이터가 어긋날 일이 없습니다.
  고칠 곳이 있으면 JSON 쪽을 고치고 이 문서를 다시 뽑습니다.
  파일명은 그대로 두시면 프론트가 바로 물립니다.
</footer>
</div>
<script>
document.querySelectorAll('pre[data-copy]').forEach(function (el) {{
  el.addEventListener('click', function () {{
    navigator.clipboard && navigator.clipboard.writeText(el.textContent).then(function () {{
      el.classList.add('copied');
      setTimeout(function () {{ el.classList.remove('copied'); }}, 1200);
    }});
  }});
}});
</script>"""

    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    open(OUT_HTML, "w", encoding="utf-8").write(doc)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["종류", "번호", "이름", "파일명", "가로", "세로", "상태"])
        for r in rs:
            w.writerow([r["group"], r["key"], r["title"], r["file"], r["w"], r["h"], ""])
    print(f"  {OUT_HTML} · {total}장")
    for g, items in groups:
        print(f"     {g:8s} {len(items):3d}장")
    return total


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    build(args[0] if args else "../scenarios/91_dsl_demo.json")
