# -*- coding: utf-8 -*-
"""
ui_wire.py — **그림과 소리를 응답에 붙이는 자리.**

★왜 따로 떼어 놓았나.
  시나리오 원본에는 그림 자리에 URL 이 아니라 **생성 프롬프트**가 들어 있다.
  그래서 서버는 내려보내기 직전에 ID → 주소로 갈아 끼워야 한다.
  그 코드가 server.py 안에 흩어져 있었는데, 엔진을 고칠 때마다 함께 지워졌다 —
  c81680b · 82629f6 · bbbe80d · 18ae6fe, **네 번**이다. 매번 그림도 소리도
  전부 끊기고 앱이 아예 안 열렸다.

  그래서 이 파일로 모은다. server.py 는 자리마다 한 줄씩만 부르면 된다:

      import ui_wire as W
      ...
      return W.state(payload, s)

  다시 덮이더라도 되살릴 것이 스무 군데가 아니라 **부르는 한 줄씩**이다.
  그리고 server.py 가 이 층을 안 걸었으면 뜨자마자 알 수 있게
  check(app) 이 경고를 낸다 — 시연장에서 알게 되는 일이 없도록.

무엇을 하나 (전부 **덧붙이기만** 한다 — 엔진이 만든 값은 건드리지 않는다):
  · 사람   초상 · 표정 세 벌 · 전신 · 테마곡
  · 장소   삽화 · 지도 썸네일 · 서 있는 사람 · 장소 음악
  · 단서   썸네일 · 카드 일러스트
  · 사건   현장 사진 · 오프닝 쪽그림 · 재연 컷
  · 소리   행동마다 붙는 효과음
"""
import os

import ui_assets as A
import ui_view as V

BUNDLE = A.BUNDLE
ASSETS_DIR = A.ASSETS_DIR


# ── 붙이는 자리 ───────────────────────────────────────────────────────
def mount(app):
    """/assets 를 연다. 번들은 보통 저장소 밖(재민의 outputs)을 가리키는 링크라
    StaticFiles 가 기본으로는 따라가지 않는다 — 실제 경로를 **먼저** 건다.
    밖에 세울 때는 파일 없이 목록(assets_manifest.json)만 보고 주소를 낸다."""
    try:
        from fastapi.staticfiles import StaticFiles
    except ImportError:
        return
    real = os.path.realpath(os.path.join(A.ASSETS_DIR, A.BUNDLE))
    if os.path.isdir(real):
        app.mount(f"/assets/{A.BUNDLE}", StaticFiles(directory=real), name="bundle")
    if os.path.isdir(A.ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=A.ASSETS_DIR), name="assets")


def serve_web(app, root="web"):
    """화면(빌드된 프론트)까지 이 서버가 내준다 — **Render 한 대로 끝난다.**

    ★왜 (2026-09-02, 제보 — "그냥 render로 하면 안 되냐").
      원래는 화면을 Netlify, 엔진을 Render 로 나눠 두었다. 그런데 —
        · 화면이 123MB 라 Netlify 업로드가 안 됐다(그림을 줄여 지금은 가볍다).
        · 화면에 백엔드 주소를 **빌드할 때 새겨야** 해서 순서가 꼬였다.
        · CORS(ALLOW_ORIGINS)를 따로 맞춰야 했다.

      한 대에서 같이 내주면 셋 다 사라진다. 주소가 같으니 화면은 백엔드
      주소를 몰라도 되고(상대경로), CORS 도 필요 없고, 올릴 곳도 하나다.

    web/ 폴더가 없으면 아무 일도 하지 않는다 — 나눠 세우던 방식도 그대로 된다.
    """
    import os as _os
    if not _os.path.isdir(root):
        return False
    try:
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse
    except ImportError:
        return False

    index = _os.path.join(root, "index.html")

    # 화면이 들고 있는 정적 파일들
    for sub in ("assets",):
        d = _os.path.join(root, sub)
        if _os.path.isdir(d):
            app.mount(f"/{sub}", StaticFiles(directory=d), name=f"web-{sub}")

    # 주소는 브라우저가 들고 있다(React Router). /library 로 바로 들어와도
    # 그런 파일은 없으므로, 남는 주소는 전부 index.html 로 넘겨 앱이 그리게 한다.
    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa(full_path: str):
        cand = _os.path.join(root, full_path)
        if full_path and _os.path.isfile(cand):
            return FileResponse(cand)
        return FileResponse(index)

    return True


def check(app):
    """이 층이 안 걸렸으면 **뜨자마자** 말한다.

    밖에 세울 때(Render)는 백엔드에 파일이 없다 — 그림·소리는 프론트가 들고
    있고 서버는 주소만 낸다. 그때는 /assets 가 없는 것이 정상이므로 잠자코 있는다.
    번들이 옆에 있는데 안 걸렸을 때만 말한다 — 그건 부르는 줄이 빠진 것이다.
    """
    if not os.path.isdir(A.ASSETS_DIR):
        return True                       # 밖에 세운 판 — 파일 없이 주소만 낸다
    paths = {getattr(r, "path", "") for r in app.routes}
    if not any(p.startswith("/assets") for p in paths):
        print("⚠ 그림·소리가 안 걸렸습니다 — server.py 에서 ui_wire.mount(app) 를 부르세요.")
        return False
    return True


def photos(s):
    return (s.get("assets") or {}).get("photos") or {}


# ── 사람 ──────────────────────────────────────────────────────────────
def cast_row(row, s):
    cid = row.get("id")
    row["portrait"] = A.portrait(cid, photos(s))
    row["faces"] = A.faces(cid)
    row["theme"] = A.character_theme(cid)
    return row


def state(payload, s):
    """라운드 화면(S-11)이 읽는 것 전부."""
    for c in payload.get("cast") or []:
        cast_row(c, s)
    return payload


# ── 장소 ──────────────────────────────────────────────────────────────
def places(rows, s):
    for p in rows:
        pid = p.get("id")
        p["art"] = A.place(pid)
        p["thumb"] = A.place_thumb(pid)
        p["bgm"] = A.place_cue(pid)
        owner = p.get("owner_id")
        p["standing"] = A.fullbody(owner) if owner else None
    return rows


# ── 단서 ──────────────────────────────────────────────────────────────
def clue_card(card, cid):
    """★화면은 clue_id 로 읽는다 — id 만 주면 수첩에 합쳐지지 않는다. 둘 다 준다."""
    card["clue_id"] = cid
    card["image"] = A.clue(cid)
    card["full_image"] = A.clue_full(cid)
    card["thumb"] = A.clue(cid)
    return card


# ── 사건 ──────────────────────────────────────────────────────────────
def scene_after():
    return A.scene_after()


def story(page):
    return A.story(page)


def reenact(no):
    return A.reenact(no)


def audio_book():
    return A.audio_book()


def event_cue(name):
    return A.event_cue(name)


def face(cid, stance):
    return A.face(cid, stance)


# ── 시나리오를 화면이 읽는 모양으로 (정답은 뗀다) ──────────────────────
def scenario_view(s, filename, held=None, accused=False):
    return V.scenario_view(s, filename, held=held, accused=accused)


def fields(rows):
    """카드의 라벨-값 목록 — **hidden_value 는 떼고 보낸다.**

    피해자 카드의 「사인」 칸은 화면에 「???」로 뜨지만, 원본에는 그 옆에
    hidden_value 로 **흉기 정답**이 함께 적혀 있다. 그대로 내보내면 화면만
    가려질 뿐 개발자도구에는 그대로 보인다.
    """
    return V._fields(rows)


def library_card(sc, name, has_assets=False):
    return V.library_card(sc, name, has_assets=has_assets)


def reveal_view(*a, **k):
    return V.reveal_view(*a, **k)


def reenactment_view(*a, **k):
    return V.reenactment_view(*a, **k)
