# -*- coding: utf-8 -*-
"""
server.py — **엔진을 HTTP로 연다.** 프론트엔드가 붙을 자리.

  pip install fastapi uvicorn
  python3 server.py                  # http://127.0.0.1:8000
  python3 server.py --port 9000
  open http://127.0.0.1:8000/docs    # 자동 생성된 API 문서(직접 눌러 볼 수 있다)
  open http://127.0.0.1:8000/demo    # 붙는지 눈으로 보는 한 장짜리 화면

■ 규칙 하나 — **화면에 뜨는 것만 내려보낸다.**
  is_culprit·points_to·아직 안 열린 비밀·정답은 어떤 응답에도 실리지 않는다.
  지목(POST /accuse)을 한 뒤에야 진상·재연·엔딩이 열린다.
  프론트가 실수로 다 받아 놓고 숨기는 구조면, 브라우저 개발자도구로 답이 보인다.

■ 세션
  한 판이 한 세션이다. 메모리에 들고 있고 기본 2시간 뒤 사라진다.
  시연용이라 이걸로 충분하다 — 여러 대에서 이어 하려면 그때 DB를 붙인다.

■ 대사
  MM_API_KEY 가 서버에 있으면 용의자 대사를 서버가 만들어 내려보낸다.
  **키는 브라우저로 나가지 않는다.** 없으면 판단(stance)만 내려보내고
  대사 자리는 비워 둔다 — 프론트는 그대로 그리면 된다.
"""
import _boot  # noqa: F401
import os, sys, re, json, glob, time, uuid, argparse, threading

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel
except ImportError:
    print("먼저 설치하세요:  pip install fastapi uvicorn")
    sys.exit(1)

from game_engine_v2 import GameSession
import play_agents as PA
# ★그림과 소리 — 재민이 만든 91_dsl 번들(이미지 108 · BGM 43).
#   이 층은 server.py 를 다시 쓸 때마다 함께 지워졌다 — 네 번이다.
#   그래서 ui_wire.py 한 파일로 모았다. 지워졌으면 이 import 와 mount 두 줄만
#   되살리면 된다. 무엇을 붙이는지는 ui_wire.py 머리말에 적어 두었다.
import ui_wire as W
import ui_assets as A          # ID → 그림·소리 주소 (ui_wire 가 쓰는 것과 같다)

# ★발표용 — **답을 아예 안 알려 준다** (2026-08-31, 제보 —
#   "발표 배포용은 정답 제출하면 그냥 끝나게, 범인이 누군지 모르게").
#
#   시연은 사람들 앞에서 한 판을 보여 주는 자리다. 그 자리에서 진상까지
#   흘러가면 보고 있던 사람들은 이 사건을 다시 풀 수 없다. 그래서 발표용은
#   3라운드 뒤 지목을 제출하는 것으로 끝난다 — 맞았는지 틀렸는지도 말하지
#   않는다. 맞았다고 알려 주는 순간 범인이 누구인지도 함께 알려 주는 셈이다.
#
#   ★스위치는 **판 단위**다 (2026-09-02).
#     처음에는 서버 전체 스위치로 뒀는데, 그러면 발표용 백엔드를 하나 더
#     띄워야 하고 — 화면에 백엔드 주소가 빌드 때 새겨지므로 — 발표용 화면도
#     그 주소로 다시 빌드해야 한다. 두 화면이 겉으로 똑같이 생겨서, 주소를
#     잘못 붙여도 지목 제출 직전까지 아무도 모른다. 시연 날 그걸 겪을 수는 없다.
#
#     그래서 판을 열 때 정한다 — POST /session 에 {"hide_answer": true}.
#     감추는 일은 **여전히 서버가 한다.** 그 판에서는 진상이 아예 안 나가므로
#     개발자도구로도 안 보인다. 백엔드도 화면 빌드도 한 벌이면 된다.
#
#     HIDE_ANSWER=1 은 서버 전체를 발표용으로 잠그는 열쇠로 남겨 둔다.
HIDE_ANSWER = os.environ.get("HIDE_ANSWER", "").strip().lower() not in ("", "0", "false", "no")


def _hidden(v):
    """이 판이 답을 감추는 판인가."""
    return bool(HIDE_ANSWER or v.get("hide_answer"))

SCEN_DIR = "scenarios"
TTL = 60 * 60 * 2          # 세션 수명 두 시간
_lock = threading.Lock()
SESSIONS = {}              # sid -> {"g":GameSession, "s":dict, "t":float, "hist":{}}
LLM = None                 # 있으면 용의자 대사를 서버가 만든다

app = FastAPI(title="여섯 잔의 회의 — 머더미스터리 엔진",
              description="생성형 머더미스터리 백엔드. 화면 순서는 docs/스토리보드.html 참고.",
              version="1.0")
# ★어느 주소에서 부를 수 있게 할 것인가.
#   ALLOW_ORIGINS 를 주면 그 목록만 — 안 주면 전부 연다(개발·시연 편의).
#   밖에 세울 때는 반드시 프론트 도메인으로 좁힌다.
_ORIGINS = [x.strip() for x in os.environ.get("ALLOW_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_ORIGINS, allow_methods=["*"],
                   allow_headers=["*"])
W.mount(app)                      # /assets — 그림·소리
W.check(app)                      # 안 걸렸으면 뜨자마자 말한다


@app.get("/health", include_in_schema=False)
def health():
    return {"ok": True, "sessions": len(SESSIONS), "llm": bool(LLM)}


# ── 세션 ──────────────────────────────────────────────────────────────
def _gc():
    now = time.time()
    for k in [k for k, v in SESSIONS.items() if now - v["t"] > TTL]:
        SESSIONS.pop(k, None)


def _sess(sid):
    with _lock:
        _gc()
        v = SESSIONS.get(sid)
        if not v:
            raise HTTPException(404, "그런 판이 없습니다. 다시 시작해 주세요.")
        v["t"] = time.time()
        return v


def _sn(s, *keys):
    node = (s.get("ui") or {}).get("story_narration") or {}
    for k in keys:
        node = (node or {}).get(k) if isinstance(node, dict) else None
    return (node or {}).get("text") if isinstance(node, dict) else None


# ── 내려보내는 모양 ───────────────────────────────────────────────────
def _view_state(v):
    """S-11 라운드 화면이 필요로 하는 것 전부. 한 번에 준다."""
    g, s = v["g"], v["s"]
    st = g.state()
    return W.state({
        "round": st["round"], "max_rounds": st["max_rounds"],
        "turns_left": st["turns_left"], "budget": st["budget"],
        "round_focus": st["round_focus"],
        # ★라운드는 **저절로 넘어가지 않는다** (2026-08-29, 시연 제보).
        #   제보: "마지막 행동 결과를 보기도 전에 라운드가 넘어간다."
        #   서버는 예산이 0이 되어도 아무것도 하지 않는다 — 넘기는 것은 프론트가
        #   /next_round 를 부를 때뿐이다. 화면이 판단할 수 있게 상태를 붙여 준다.
        #   round_over 가 참이면 「이번 밤을 마친다」 버튼을 띄우면 된다.
        "round_over": st["turns_left"] <= 0,
        "can_next_round": st.get("can_next_round"),
        "is_last_round": st.get("is_last_round"),
        # ★지목 버튼은 **마지막 밤에만** 띄우길 권한다 (2026-08-29, 팀원 제보 —
        #   "1, 2라운드에선 범인 맞추기 그냥 없애는 게 나을 듯").
        #   서버가 막지는 않는다(일찍 짚고 끝내는 것도 플레이어의 선택이다).
        #   다만 이른 지목은 대개 근거 없는 찍기라, 화면에서는 감추는 편이 낫다.
        "accuse_advised": bool(st.get("is_last_round")),
        "findable_left": st.get("findable_left"),
        # ★맞세울 **후보**를 준다 — 정답 짝이 아니라. (2026-08-30, 제보 —
        #   "「말이 어긋나는 짝」을 알려주면 어캄")
        #   맞는 지적이다. 전날 "대질에 사람이 한 명만 뜬다"는 제보를 받고
        #   cross_examination.pairs 를 그대로 내보냈는데, 그건 시나리오가 들고 있는
        #   **어긋나는 짝의 정답표**다. 누구와 누구의 말이 안 맞는지 찾아내는 것이
        #   대질의 전부인데, 화면이 그걸 먼저 읽어 주면 남는 건 클릭뿐이다.
        #   이제는 **만난 사람 전부**를 후보로 준다. 둘을 고르는 건 플레이어 몫이다.
        #   짝이 맞으면 준비된 대질 대본이 나오고, 어긋나면 즉흥 대질이 된다
        #   (엔진은 어느 쪽이든 처리한다 — game_engine_v2.confront 참고).
        "confront": {**st["confront"],
                     "pick": 2,
                     "candidates": [{"id": c["id"], "name": c["name"], "met": c["met"]}
                                    for c in st["cast"]]},
        "cast": [{
            "id": c["id"], "name": c["name"], "public": c["public"],
            "met": c["met"], "alibi": c["alibi"],
            "secrets_open": c["secrets_open"], "secrets_left": max(
                0, len([x for x in (g.cast[c["id"]].get("secrets") or []) if x.get("text")])
                - len(c["secrets_open"])),
            "pressure": c["pressure"],
        } for c in st["cast"]],
        "notebook": st["notebook"],
        # ★화면이 쓰는데 서버가 안 주던 둘 (2026-08-30).
        #   held_clues 가 없으면 수첩이 통째로 튀고, verdict 가 없으면 엔딩이
        #   ARREST/FAIL 을 못 가린다.
        "held_clues": sorted(g.held_clues),
        # ★화면은 이 자리를 **객체**로 읽는다 (named·correct·score·max·grade·verdict).
        #   여태 문자열을 넣고 있었는데, 그동안은 이 값이 늘 비어 있어서
        #   아무도 몰랐다. 채우기 시작하자 화면이 gameResult 를 이걸로 덮어써
        #   지목 결과가 통째로 날아갔다. 규격을 맞춘다.
        #   발표용에서는 맞았는지를 **넣지 않는다** — 그것이 곧 답이다.
        "verdict": v.get("verdict_summary"),
    }, s)


def _view_places(v):
    """S-13 지도."""
    g, s = v["g"], v["s"]
    out = []
    for ps in (s["ui"].get("place_screens") or []):
        pid = ps["place_id"]
        out.append({
            "id": pid, "title": ps["title"],
            "searched": (pid, g.current_round) in g.searched,
            "owner": ps.get("standing_character"),
            "owner_id": ps.get("standing_cast_id"),
            "talk": ps.get("talk"),
        })
    return W.places(out, s)


def _place_name(s, pid):
    """장소 id를 사람이 읽는 이름으로. 'PC' 가 그대로 화면에 뜨던 것을 막는다."""
    if not pid:
        return None
    for ps in (s.get("ui") or {}).get("place_screens") or []:
        if ps.get("place_id") == pid:
            return ps.get("title") or pid
    for p in (s.get("map") or {}).get("places") or []:
        if p.get("id") == pid:
            return p.get("name") or p.get("title") or pid
    return pid


def _no_finds(actions):
    """조사 선택지에서 **정답 표시를 떼어 낸다.**

    엔진의 선택지에는 그 칸이 품은 단서 id(`finds`)가 붙어 있다. 화면이 쓰라고
    있는 값이 아니라 엔진 내부 값이다 — 그대로 나가면 누르기 전에 답이 보인다.
    """
    out = []
    for a in (actions or []):
        if isinstance(a, dict):
            a = {k: val for k, val in a.items() if k != "finds"}
        out.append(a)
    return out


def _clue_card(s, cid, live=None):
    """단서 하나를 **화면이 읽는 카드**로.

    ★대질에서 나온 단서는 시나리오에 없다 (2026-08-31, 제보 —
      "대질단서 사건수첩에 들어갈 때 이름 이상해").
      엔진이 판이 도는 중에 만들어 낸다(game_engine_v2.confront). 그러니
      ui.clue_cards 를 아무리 뒤져도 없고, 이름 자리가 비어 수첩에 이상한 줄이
      생겼다. 그런 단서는 엔진이 들고 있는 노드(live)의 surface 를 본문으로,
      「대질」이라는 출처를 이름으로 삼는다.
    """
    card = next((c for c in (s["ui"].get("clue_cards") or []) if c.get("id") == cid), None)
    # ★단서는 **물건**이지 물건에 대한 설명이 아니다 (2026-08-29, 시연 제보).
    #   제보: "「탄핵소추안.pptx를 만들어 뒀다」 이렇게 설명하지 말고 실제 글을 만들어야지."
    #   맞는 말이다. 「장부가 있다」가 아니라 **장부를 펴 보여야** 읽고 판단할 수 있다.
    #   document 가 있으면 화면은 카드 아래에 그 문면을 그대로 펼쳐 보여 준다.
    graph = (live or {}).get(cid) if isinstance(live, dict) else None
    if graph is None:
        graph = next((c for c in (s.get("clue_graph") or []) if c.get("id") == cid), None)
    # 시나리오에 카드가 없는 것(대질에서 즉석으로 난 단서)은 노드에서 지어 낸다
    name = (card or {}).get("name")
    desc = (card or {}).get("description")
    if not name:
        name = {"cross_exam": "맞댄 자리에서 나온 말"}.get(
            (graph or {}).get("channel"), (graph or {}).get("medium") or "단서")
    if not desc:
        desc = (graph or {}).get("surface")
    return W.clue_card({"id": cid, "name": name,
                        "description": desc,
                        "list_sub": (card or {}).get("list_sub") or (graph or {}).get("medium"),
                        "fields": (card or {}).get("fields"),
                        "document": (graph or {}).get("document"),
                        }, cid)


# ── 요청 몸통 ─────────────────────────────────────────────────────────
class NewGame(BaseModel):
    scenario: str = "91_dsl_demo.json"
    # 발표용 판 — 지목을 제출하면 거기서 끝난다. 맞았는지도 말하지 않는다.
    hide_answer: bool = False


class SearchIn(BaseModel):
    place_id: str
    action_index: int | None = None   # 화면에서 누른 조사 선택지 (없으면 방 전체)


class AskIn(BaseModel):
    cast_id: str
    question: str
    clue_id: str | None = None


class ConfrontIn(BaseModel):
    a: str
    b: str
    question: str = ""


class CombineIn(BaseModel):
    clue_a: str
    clue_b: str


class AccuseIn(BaseModel):
    cast_id: str
    weapon: str | None = None
    motive: str | None = None


# ── 화면 ──────────────────────────────────────────────────────────────
@app.get("/scenarios", summary="고를 수 있는 사건 목록")
def scenarios():
    out = []
    for f in sorted(glob.glob(f"{SCEN_DIR}/*.json")):
        if "catalog" in f:
            continue
        try:
            s = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        # ★라이브러리 카드가 필요로 하는 것을 다 준다 (2026-08-29).
        #   여태 제목·시대·별점뿐이라 화면이 카드를 채울 수 없었다.
        st = s.get("stars") or {}
        out.append({"file": os.path.basename(f), "title": s["meta"]["title"],
                    "origin": s["meta"].get("origin"),        # 원작 (별주부전 · 헨젤과 그레텔 …)
                    "era": s["meta"].get("era"),
                    "stars": st.get("stars"),                 # ★★★☆☆
                    "stars_n": st.get("n"),                   # 1~5 (정렬용)
                    "tier": (s.get("difficulty") or {}).get("label"),   # 쉬움/보통/어려움
                    "blurb": st.get("blurb"),                 # 한 줄 소개
                    # ★logline 은 50편 전부 비어 있다. 전에는 별점 소개문(blurb)으로
                    #   채웠는데, 그것이 사건 공개 화면에 「트릭이 꼬여 있다 · 쉬움」처럼
                    #   **서로 어긋나는 한 줄**로 떴다(2026-08-30 제보). 비면 비운 채 보낸다 —
                    #   화면은 사건 나레이션과 현장 묘사를 이미 갖고 있다.
                    "logline": (s.get("background") or {}).get("logline"),
                    "rounds": s["config"].get("rounds"),
                    "turns_per_round": s["config"].get("turns_per_round"),
                    "cast": len(s.get("cast") or [])})
    return out


# ★기록실에 무엇을 놓을 것인가.
#   그림과 소리는 **91편 것만** 있다(ui_assets 가 91_dsl 번들 하나를 본다).
#   50편을 다 열어 두면 다른 편을 골랐을 때 91편 그림이 엉뚱하게 붙는다 —
#   실제로 전우치를 열었더니 중앙도서관 사진이 나왔다.
#   시연에 쓸 편만 기본으로 둔다. LIBRARY=* 로 전부 열 수 있다.
LIBRARY = [x.strip() for x in
           os.environ.get("LIBRARY", "91_dsl_demo.json").split(",") if x.strip()]


@app.get("/scenarios/library", summary="사건 기록실 (S-04) — 화면이 읽는 카드")
def library():
    """프론트 [사건 기록실]이 읽는 모양. **미리 만들어 둔 사건만** — 실시간 생성은 없다.

    `/scenarios` 와 다른 길이다. 그쪽은 파일 목록이고, 이쪽은 **카드 한 장**이다 —
    배경 한 줄·사건 한 줄·표지 그림까지 붙는다. 엔딩 문구는 미끼만 싣고 진상은 넣지 않는다.
    """
    out = []
    for f in sorted(glob.glob(f"{SCEN_DIR}/*.json")):
        name = os.path.basename(f)
        if "catalog" in f or (LIBRARY != ["*"] and name not in LIBRARY):
            continue
        try:
            sc = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        out.append(W.library_card(sc, name, has_assets=(name == "91_dsl_demo.json")))
    return out


@app.get("/audio", summary="소리 목록 — 판을 열기 전에도 준다")
def audio():
    """첫 화면과 기록실에도 음악이 있어야 한다.

    소리는 판이 아니라 번들에 딸린 것이다. /session 응답에만 실으면 판을 열기 전에는
    화면이 틀 곡을 모른다 — 타이틀 곡이 있는데도 첫 화면이 조용해진다.
    어느 화면에 어느 곡인지는 시나리오 `ui.screens[].bgm` 이 정해 두었다.
    """
    return W.audio_book()


@app.post("/session", summary="새 판을 연다 (S-05~S-10)")
def new_session(body: NewGame):
    path = f"{SCEN_DIR}/{os.path.basename(body.scenario)}"
    if not os.path.exists(path):
        raise HTTPException(404, f"그런 사건이 없습니다: {body.scenario}")
    s = json.load(open(path, encoding="utf-8"))
    g = GameSession(s)
    sid = uuid.uuid4().hex[:12]
    with _lock:
        # file 은 되찾기(/session/{sid}/scenario)가 쓴다
        SESSIONS[sid] = {"g": g, "s": s, "t": time.time(), "hist": {},
                         "file": os.path.basename(path),
                         # 판을 열 때 정해지고, 그 뒤로는 바뀌지 않는다
                         "hide_answer": bool(body.hide_answer)}
    ui = s["ui"]
    return {
        "session_id": sid,
        "meta": s["meta"],
        "case": {                                   # S-05 사건 공개
            "logline": (s.get("background") or {}).get("logline"),
            "setting": (s.get("background") or {}).get("setting"),
            "narration": _sn(s, "case_open"),
        },
        # S-06 오프닝 — 묶어서 대여섯 쪽으로. 쪽마다 auto_ms(권장 자동 넘김)가 붙는다
        "opening": _opening((ui.get("narration") or {}).get("pages", [])),
        # ★쪽번호(1/6 … 5/6)는 **띄우지 않는다** (2026-08-30, 제보 — 두 번째).
        #   남은 분량을 세어 보이면 이야기가 아니라 과제가 된다. 서버는 page 번호를
        #   더 이상 내려보내지 않고, 화면도 i+1 / length 를 그리지 말라는 뜻으로
        #   이 값을 함께 준다. 인트로·엔딩 양쪽에 똑같이 적용한다.
        "opening_ui": {"show_page_number": False, "text_style": "pre-line"},
        "blood_transition": (_scr(s, "blood_transition") or {}).get("copy", {}).get("line"),
        "crime_scene": {                            # S-08 현장
            "narration": _sn(s, "crime_scene"),
            "description": (s.get("death") or {}).get("scene_description"),
            "image": W.scene_after(),                # 사건 뒤의 세미나실
            "clues": [_clue_card(s, c["id"]) for c in g.notebook],
        },
        # S-09 피해자 카드
        # ★칸이 비어 있던 것을 채운다 (2026-08-29, 시연 제보 — "피해자 프로필에 내용이 없다").
        #   화면은 [신분 / 발견 장소 / 발견 시각 / 사인] 네 칸으로 그려 두었는데,
        #   서버는 이름·신분·나레이션만 주고 있었다. 뒤 세 칸이 영영 빈 채였다.
        #   장소와 시각은 death 에 있으니 그대로 준다. **사인은 주지 않는다** —
        #   흉기와 수법은 정답이라, 지목(/accuse) 전에는 물음표로 둔다.
        # ★원본 ui.victim_card 를 그대로 쓴다 (2026-08-29, 팀원 제보 — "사진 규격이 안 맞는다").
        #   여태 death 에서 필드를 다시 만들어 내려보냈는데, 시나리오에는 이미 **완성된 카드**가
        #   있었다 — 신분·발견 장소·발견 시각·사인(???)·발견자 다섯 칸과 요약까지.
        #   그리고 카드에 들어갈 그림은 초상이 아니라 **현장 그림(1045×600 가로)** 이다.
        #   ※ 주검은 그린다 — 다만 조건이 붙는다 (2026-08-31 갱신).
        #     91편은 실존 인물이 모델이라 한동안 **사람 없이** 밀려난 의자와 기울어진 잔만
        #     그렸다. 여섯 명 전원 동의를 확인한 뒤로(가은 H-2) 되살렸고, 지금 세 그림
        #     (scene_after · open_14 · reenact_6) 모두 같은 규칙을 지킨다 —
        #     엎드린 자세, 얼굴 안 보임, 피·상처 없음, 멀리서 작게. 연출하지 않는다.
        "victim": (lambda vc, v: {
            "name": vc.get("name") or v.get("name"),
            "role": v.get("role"),
            # ★hidden_value 를 떼고 보낸다 (2026-08-31).
            #   「사인」 칸은 화면에 「???」로 뜨지만, 원본에는 그 옆에
            #   hidden_value 로 **흉기 정답**이 적혀 있다. 그대로 내보내면
            #   화면만 가려질 뿐 개발자도구에는 그대로 보인다.
            "fields": W.fields(vc.get("fields")),
            "summary": vc.get("summary"),
            "bio": vc.get("bio_short") or v.get("bio"),
            "self_intro": v.get("self_intro") or [],
            "found_place": _place_name(s, (s.get("death") or {}).get("place")),
            "found_time": (s.get("death") or {}).get("time_slot"),
            "cause": "???",                          # 지목 전까지 밝히지 않는다
            "narration": _sn(s, "victim_card"),
            "portrait": A.portrait("victim", W.photos(s)),
            # 카드 그림은 초상이 아니라 **현장(가로 1045×600)** 이다.
            "scene_art": W.scene_after(),
        })(s["ui"].get("victim_card") or {}, s.get("victim") or {}),
        "suspects": [                               # S-10 용의자 소개
            {"id": c["id"], "name": c["name"], "public": c.get("public"),
             "intro": _sn(s, "suspect_intro", c["id"]),
             "photo": A.portrait(c["id"], W.photos(s)),
             "theme": A.character_theme(c["id"])}
            for c in s["cast"]],
        # ★흉기 선택지 (2026-08-29, 팀원 제보 — "범행도구 제출 5지선다 아니었나").
        #   맞다. 시나리오 choices.weapon 에 다섯 개가 들어 있는데 API가 안 주고 있었다.
        #   화면은 이걸로 5지선다를 그리고, 고른 문자열을 그대로 /accuse 의 weapon 에 넣는다.
        "weapon_choices": (s.get("choices") or {}).get("weapon") or [],
        # ★무엇이 **필수**인지 못 박아 준다 (2026-08-29, 팀원 제보 —
        #   "모든 요소를 안 적으면 제출이 안 돼서 엔딩을 볼 수 없음").
        #   채점은 **범인 5점 + 비밀 1개당 1점**이다 — 흉기와 동기는 점수에 들어가지
        #   않는다. 그러니 필수로 막을 이유가 없다. 범인만 고르면 제출된다.
        "accuse_form": {
            "required": ["cast_id"],
            "optional": ["weapon", "motive"],
            "weapon": "choice", "motive": "free_text",
            "note": "범인만 고르면 제출된다. 흉기·동기는 적어도 되고 안 적어도 된다.",
        },
        "scoring": {**(s.get("scoring") or {}),
                    "explain": "범인을 맞히면 5점, 연 비밀 하나에 1점. 최대 10점."},
        "config": {"rounds": s["config"].get("rounds"),
                   "turns_per_round": s["config"].get("turns_per_round"),
                   "llm": bool(LLM),
                   # 발표용이면 지목 제출로 판이 끝난다 — 화면이 이걸 보고 문구를 바꾼다
                   "hide_answer": _hidden(SESSIONS[sid])},
        # ★그림 규격을 한곳에 모아 보낸다 (2026-08-31, 팀원 제보 —
        #   "사진 크기 스키마에 넣기, 피해자 사진 svg 크기 570×319").
        #   여태 규격이 시나리오 곳곳에 흩어져 있어 화면이 매번 어림해 넣었다.
        #   portrait 항목에는 **당황 컷을 기본 초상으로 쓰지 말라**는 것도 적어 두었다.
        "art_sizes": (ui.get("art_sizes") or {}),
        # ★화면 전체가 읽는 시나리오 — **정답은 떼어 낸 것**(ui_view.scenario_view).
        #   오프닝 삽화·장소 그림·단서 카드·인물 카드가 다 여기 들어 있다.
        #   단서 카드는 지금 손에 든 것만. 나머지는 찾을 때마다 응답에 딸려 온다.
        "scenario": W.scenario_view(s, os.path.basename(path), held=g.held_clues),
        "audio": W.audio_book(),
        "state": _view_state(SESSIONS[sid]),
    }


@app.get("/session/{sid}/scenario", summary="화면이 읽는 시나리오 — 정답은 빠져 있다")
def session_scenario(sid: str):
    """새로고침한 뒤 판을 되찾을 때 쓴다. /session 응답의 scenario 와 같은 것이다."""
    v = _sess(sid)
    return W.scenario_view(v["s"], v.get("file") or "", held=v["g"].held_clues,
                           # ★맞혔을 때만 연다 (2026-08-31, 팀 결정 — 가은).
                           #   틀리면 /accuse 가 진상·재연을 감추는데, 여기서
                           #   열어 주면 새로고침 한 번으로 다 보인다. 규칙은
                           #   두 길에서 같아야 한다.
                           accused=(not _hidden(v)
                                    and v.get("verdict") == "ARREST"))


_SENT = re.compile(r"(?<=[.!?…\u2026])\s+|(?<=다\.)\s+")


def _lines(txt, wide=34):
    """나레이션을 **문장 단위 줄**로 끊는다.

    긴 문장은 쉼표·연결어미 자리에서 한 번 더 접는다 — 34자를 넘으면
    화면 어디선가 저절로 접히는데, 그 자리는 대개 뜻과 상관없는 곳이다.
    """
    out = []
    for s in [x.strip() for x in _SENT.split(str(txt or "")) if x.strip()]:
        while len(s) > wide * 1.6:
            cut = -1
            for m in re.finditer(r"(?<=[,;])\s+|(?<=고)\s+|(?<=며)\s+|(?<=만)\s+", s):
                if m.end() <= wide * 1.3:
                    cut = m.end()
            if cut < 8:
                break
            out.append(s[:cut].strip())
            s = s[cut:].strip()
        out.append(s)
    return out


def _opening(pages, target=130):
    """오프닝을 **읽을 만한 덩이로 묶고**, 쪽마다 자동 넘김 시간을 붙인다.

    ★왜 (2026-08-29, 시연 제보) — "인트로가 너무 늘어진다."
      91편 오프닝은 611자를 열네 쪽에 나눠 담고 있었다. 쪽당 마흔네 자.
      한 문장 읽고 누르고, 한 문장 읽고 누르기를 열네 번 하면 사건이 시작되기도
      전에 지친다. 글은 그대로 두고 **담는 그릇만** 바꾼다 — 130자 안팎으로 묶으면
      대여섯 쪽이 된다.

    auto_ms 는 프론트가 쓰라고 주는 권장 시간이다. 한글 읽는 속도를 글자당 90ms로
    보고 여유 1.2초를 더한다. 화면이 이 값을 쓰면 누르지 않아도 이야기가 흐르고,
    그래도 누르면 바로 넘어간다(둘 다 되게 두는 것이 좋다).
    """
    out, buf, img, first_no = [], "", None, None
    def flush():
        nonlocal buf, img, first_no
        if not buf.strip():
            return
        txt = buf.strip()
        # ★줄은 **서버가 끊는다** (2026-08-30, 제보 — "줄바꿈 신경 써서").
        #   한 덩이로 내려보내면 화면 너비에 따라 문장 한가운데가 잘린다
        #   ("영상 / 이 끝나고 십 분 휴식"). 나레이션은 문장이 곧 호흡이라
        #   **문장마다 한 줄**로 끊어 준다. text 에는 \n 을 넣어 두었으니
        #   화면은 white-space: pre-line 한 줄만 주면 그대로 그려진다.
        lines = _lines(txt)
        out.append({"text": "\n".join(lines), "lines": lines, "image": img,
                    "auto_ms": min(9000, int(len(txt) * 90) + 1200)})
        buf, img, first_no = "", None, None
    for p in pages:
        t = (p.get("text") or "").strip()
        if not t:
            continue
        if buf and len(buf) + len(t) > target:
            flush()
        if not buf:
            # 원본에는 생성 프롬프트가 들어 있다 — 묶음 첫 쪽의 그림 주소로 바꾼다
            img = W.story(p.get("page"))
            first_no = p.get("page")
        buf = (buf + " " + t).strip()
    flush()
    # ★쪽 번호는 매기지 않는다 (2026-08-30, 제보 — "밑에 1/6, 5/6 이런 거 빼").
    #   전에는 여기서 다시 매겨 내려보냈고, 화면이 그걸 그대로 「5 / 6」으로 찍었다.
    #   남은 쪽수를 세어 보이면 이야기가 아니라 분량이 된다. 필드를 아예 없앤다.
    return out


def _scr(s, sid):
    return next((x for x in (s["ui"].get("screens") or []) if x.get("id") == sid), {}) or {}


@app.get("/session/{sid}/state", summary="지금 화면에 그릴 것 전부 (S-11)")
def get_state(sid: str):
    return _view_state(_sess(sid))


@app.get("/session/{sid}/map", summary="지도 (S-13)")
def get_map(sid: str):
    v = _sess(sid)
    return {"places": _view_places(v), "state": _view_state(v)}


@app.post("/session/{sid}/search", summary="장소 조사 (S-14) — 무언가 나온 방만 1턴")
def search(sid: str, body: SearchIn):
    v = _sess(sid)
    r = v["g"].search(body.place_id, action_index=body.action_index)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    got = [c["id"] for c in (r.get("clues") or [])]
    # ★화면에 그대로 읽어 줄 한 줄 (2026-08-29) — 프론트가 문구를 짓지 않게 한다.
    #   빈 방에 "딱히 특별한 건 없었다"가 뜨면서 수첩에는 단서가 들어와 있던 사고를 막는다.
    if got:
        msg = f"단서 {len(got)}장을 얻었다." if len(got) > 1 else "단서 하나를 얻었다."
    elif r.get("already_had"):
        msg = "여기서 볼 것은 이미 다 보았다."
    else:
        msg = "이곳은 오늘 밤 달라진 것이 없다."
    return {"place": r.get("place_name"), "first_visit": r.get("first_visit"),
            # ★finds 는 떼고 보낸다 (2026-08-30, 되살아난 것 — 세 번째).
            #   엔진이 주는 선택지에는 그 칸이 품은 단서 id 가 붙어 있다.
            #   그대로 내려보내면 누르기도 전에 어느 칸에 무엇이 있는지 다 보인다.
            "actions": _no_finds(r.get("actions") or r.get("shown")),
            "lines": r.get("result_lines") or [],      # 연출 문장 (찾은 칸 기준)
            "pressed_label": r.get("pressed_label"),
            "message": msg,
            "cost": r.get("cost", 0),                  # 이번 조사에 든 행동 (0이면 안 깎였다)
            "found": [_clue_card(v["s"], c) for c in got],
            "already_had": r.get("already_had") or [],
            "empty": not got,
            # 소리 한 번 — 찾았을 때와 헛디뎠을 때가 다르다
            "sfx": W.event_cue("clue_found" if got else "search_miss"),
            "state": _view_state(v)}


@app.post("/session/{sid}/meet/{cast_id}", summary="첫 대면 알리바이 (P-06) — 예산 0")
def meet(sid: str, cast_id: str):
    v = _sess(sid)
    r = v["g"].meet(cast_id)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    return {**r, "state": _view_state(v)}


@app.post("/session/{sid}/ask", summary="심문 (S-15) — 1턴")
def ask(sid: str, body: AskIn):
    v = _sess(sid)
    g, s = v["g"], v["s"]
    if body.cast_id not in g.cast:
        raise HTTPException(400, "그런 인물이 없습니다.")
    c = g.cast[body.cast_id]
    q = body.question.strip()
    cl = None
    if body.clue_id and body.clue_id in g.held_clues:
        cl = g.clue_graph.get(body.clue_id)
        if cl and cl.get("surface"):
            q = f"「{cl['surface']}」 — {q}"          # 단서는 문장째 내민다
    before = set(g.disclosed_secrets.get(body.cast_id, set()))
    st = g.interrogate(body.cast_id, q, evidence_shown=bool(cl),
                       evidence_id=(cl or {}).get("id"))
    # ★들이댄 물건을 **인물도 보게 한다** (2026-08-30, 제보 —
    #   "변명이 너무 성의없잖아, 니코틴을 뭘 특별한 용도로 써").
    #   여태 인물에게는 단서의 **이름 한 줄**만 갔다. 그러니 「특별한 용도」처럼
    #   속 빈 말밖에 못 했다 — 댈 거리가 없으니 지어낸 것이다.
    #   물건에는 대개 문면이 딸려 있다(소품 대장·장부·문자 기록). 그걸 함께 보여 주면
    #   「대장에 적힌 건 조명 젤이랑 배터리다」처럼 **따져 볼 수 있는 말**이 나온다.
    #   플레이어는 이미 이 문면을 수첩에서 읽을 수 있으므로 새는 정보가 아니다.
    if cl and st and not st.get("error"):
        doc = cl.get("document") or {}
        body_lines = [str(x) for x in (doc.get("body") or [])][:8]
        brief = ["[지금 눈앞에 놓인 물건 — 이것을 보고 답한다]",
                 f"· {cl.get('surface') or cl.get('id')}"]
        if doc.get("title"):
            brief.append(f"· 딸린 문서: {doc['title']}")
        brief += [f"    {x}" for x in body_lines]
        brief.append("· 이 문면에 **적혀 있는 것**만 근거로 삼는다. "
                     "적혀 있지 않은 물건은 「내가 넣은 것이 아니다」가 답이다.")
        st["evidence_brief"] = "\n".join(brief)
    if st.get("error"):
        raise HTTPException(400, st["error"])

    line = None
    if LLM:
        hist = v["hist"].setdefault(body.cast_id, [])
        stat = {"regen": 0, "stripped": 0}
        try:
            line = PA.suspect_reply(LLM, s, g, c, q, st, hist, stat)
        except Exception as e:
            line = None
            st["llm_error"] = str(e)[:80]
    opened = sorted(set(g.disclosed_secrets.get(body.cast_id, set())) - before)
    # 비밀이 열릴 때도 **그 물건을 펴 보여** 준다 (문면이 적힌 비밀에 한해)
    opened_docs = []
    for sec in (c.get("secrets") or []):
        if sec.get("text") in opened and sec.get("document"):
            opened_docs.append({"text": sec["text"], "document": sec["document"]})
    return {
        "cast": {"id": c["id"], "name": c["name"]},
        "question": q,
        "line": line,                       # 키가 없으면 null — 프론트는 자리만 비워 둔다
        "stance": st["stance"],             # ANSWER/DEFLECT/FLINCH/ADMIT/BREAK
        # ★정곡을 찔렀는가 (2026-08-31, 팀원 제보 — "비밀 정곡 찔리면 채팅 붉은색 효과").
        #   화면이 stance 문자열을 해석하게 두면 규칙이 두 군데로 갈린다.
        #   서버가 **연출 신호 하나**로 정리해 준다 —
        #     hit  : 아픈 곳을 건드렸다(FLINCH·ADMIT·BREAK). 붉은 효과를 준다.
        #     level: 얼마나 세게. 1=흔들림 2=실토 3=무너짐 (효과 세기에 쓰라고)
        "hit": st["stance"] in ("FLINCH", "ADMIT", "BREAK"),
        "hit_level": {"FLINCH": 1, "ADMIT": 2, "BREAK": 3}.get(st["stance"], 0),
        "pressure": st.get("gauge_after"),
        "turns_left": st.get("turns_left"),
        "secrets_opened": opened,
        "secret_documents": opened_docs,     # 열린 비밀이 물건이면 그 문면
        "belonging": st.get("yielded_belonging"),
        # 압박에 따라 얼굴을 갈아 끼운다 — 화면은 이 주소를 그대로 쓴다
        "face": W.face(c["id"], st["stance"]),
        "sfx": W.event_cue("secret_open") if opened else None,
        "state": _view_state(v),
    }


@app.post("/session/{sid}/confront", summary="대질 (S-16) — 한 판 1회, 행동 1")
def confront(sid: str, body: ConfrontIn):
    v = _sess(sid)
    g = v["g"]
    r = g.confront(body.a, body.b, body.question or "그 시각 어디 계셨는지 다시 말씀해 주세요.")
    if r.get("error"):
        raise HTTPException(400, r["error"])
    cx = r.get("cross_exam") or {}
    return {"a": g.cast[body.a]["name"], "b": g.cast[body.b]["name"],
            "angle": cx.get("angle"), "opening": cx.get("opening"),
            "exchange": cx.get("exchange"),
            "reveals": cx.get("reveals"),
            # ★대질로 얻은 단서도 **카드**로 준다 (2026-08-31, 제보 —
            #   "대질단서 사건수첩에 들어갈 때 이름 이상해").
            #   엔진은 clue_graph 노드를 그대로 얹어 준다. 그 노드에는 name 이
            #   아예 없고(그래서 수첩에 이름 없는 줄이 생겼다) 대신 points_to —
            #   **그 단서가 누구를 가리키는지**가 들어 있다. 지목 전에 나가면 안 되는 값이다.
            #   ui.clue_cards 의 카드로 옮겨 담는다.
            "gained_clue": (_clue_card(v["s"], (cx.get("gained_clue") or {}).get("id"),
                                       live=getattr(v["g"], "clue_graph", None))
                            if isinstance(cx.get("gained_clue"), dict)
                            and (cx.get("gained_clue") or {}).get("id")
                            else None),
            "curated": r.get("is_curated_pair"),
            "portraits": {body.a: A.portrait(body.a, W.photos(v["s"])),
                          body.b: A.portrait(body.b, W.photos(v["s"]))},
            "sfx": W.event_cue("clue_decisive"),
            "state": _view_state(v)}


@app.post("/session/{sid}/next_round", summary="라운드 넘기기 (S-20 → S-12)")
def next_round(sid: str):
    v = _sess(sid)
    g, s = v["g"], v["s"]
    r = g.next_round()
    if r.get("error"):
        raise HTTPException(400, r["error"])
    events = g.apply_event(g.current_round) or []
    # ★이벤트가 준 단서가 화면에 안 뜨던 것을 고친다 (2026-08-29, 시연 제보).
    #   "판이 뒤집힙니다 하고 이벤트 단서가 안 나온다" —
    #   실제로는 나오고 있었다. 다만 event_result 는 단서를 **id로만**(["S2"]) 주고
    #   given 만 카드로 줬다. 화면이 그릴 수 있는 모양이 아니었던 것이다.
    #   이제 이벤트 단서도 카드로 펴고, **이번 라운드에 새로 들어온 것 전부**를
    #   new_clues 한 자리에 모아 준다 — 화면은 여기 하나만 그리면 된다.
    ev_ids = [cid for e in events for cid in (e.get("clues") or [])]
    for e in events:
        e["clue_cards"] = [_clue_card(s, cid) for cid in (e.get("clues") or [])]
    given_ids = list(r.get("given") or [])
    all_ids = given_ids + [c for c in ev_ids if c not in given_ids]
    return {
        "round": r["round"],
        "given": [_clue_card(s, c) for c in given_ids],
        "new_clues": [_clue_card(s, c) for c in all_ids],   # 라운드 단서 + 이벤트 단서
        "opened_secrets": [t for e in events for t in (e.get("secrets") or [])],
        "round_start": _sn(s, "round_start", str(r["round"])),
        "event": next(({"name": e.get("name"), "text": e.get("text"),
                        "effect": e.get("effect")}
                       for e in (s.get("events") or [])
                       if e.get("round") == r["round"]), None),
        "event_result": events,
        "sfx": W.event_cue("round_start"),
        "state": _view_state(v),
    }


_JOSA_T = __import__("re").compile(
    r"(은|는|이|가|을|를|의|에|에서|으로|로|와|과|도|만|께|한테|부터|까지|이나|나)$")


@app.get("/session/{sid}/rules", summary="이 판의 규칙 (P-02) — 그대로 읽어 주면 된다")
def rules(sid: str):
    """★"게임룰 설명이 있으면 좋겠다" (2026-08-29, 팀원 제보).

    규칙 문서는 있었지만 API로 나가지 않아 화면에서 띄울 수 없었다.
    편마다 라운드 수와 예산이 다르므로 **그 판의 값으로 채워** 내려보낸다.
    """
    v = _sess(sid)
    g, s = v["g"], v["s"]
    cfg = s.get("config") or {}
    n_cast = len(s.get("cast") or [])
    # ★문구는 **실제 게임 룰 안내 방식**을 따른다 (2026-08-30, 제보 —
    #   "「증거를 내밀어라 — 그냥 묻는 것과 답이 다르다」처럼 AI 티 나게 쓰지 마라").
    #   추리 보드게임·머더미스터리 룰 시트와 게임 내 튜토리얼은 이렇게 쓴다 —
    #     · 존댓말 평서문. 잠언·비유·명령형 감탄을 쓰지 않는다
    #     · **숫자를 앞에** 둔다 ("라운드마다 행동 8회")
    #     · 조건 → 결과로 붙인다 ("제시하면 답변이 달라집니다")
    #     · 한 항목은 한두 문장. 세계관 문장과 규칙 문장을 섞지 않는다
    return {"title": "게임 방법",
            "items": [
                {"h": "목표",
                 "t": f"용의자 {n_cast}명 가운데 범인은 1명입니다. "
                      f"{cfg.get('rounds')}개 라운드 동안 조사와 심문으로 단서를 모아, "
                      "마지막에 범인을 지목합니다."},
                {"h": "행동",
                 "t": f"라운드마다 행동 {cfg.get('turns_per_round')}회가 주어집니다. "
                      "장소 조사와 심문에 각각 1회가 소모됩니다. "
                      "같은 라운드에 이미 조사한 장소를 다시 열 때는 소모되지 않습니다."},
                {"h": "알리바이",
                 "t": "용의자를 처음 만나 알리바이를 듣는 데에는 행동이 소모되지 않습니다."},
                {"h": "증거 제시",
                 "t": "질문할 때 수첩의 단서를 함께 제시할 수 있습니다. "
                      "제시한 단서가 그 인물이 숨긴 사실과 관련되면 답변이 달라집니다."},
                {"h": "반복 추궁",
                 "t": "같은 사실을 거듭 물으면 압박이 쌓입니다. "
                      "표정이 굳거나 말이 흐려지면 관련된 비밀이 있다는 신호입니다."},
                {"h": "대질",
                 "t": "용의자 두 명을 대질시킬 수 있습니다. "
                      "게임당 1회만 가능하며 행동 1회가 소모됩니다."},
                {"h": "추리 성공",
                 "t": "범인과 흉기를 모두 맞히면 추리에 성공합니다. "
                      "동기는 선택 입력이며 성공 여부에 반영되지 않습니다."},
            ]}


@app.get("/session/{sid}/timeline", summary="그날 밤 시간표 (S-19) — 플레이어가 아는 것만")
def timeline(sid: str):
    """★"타임스탬프는 어떻게 보나요?" 에 답한다 (2026-08-29, 시연 제보).

    시나리오는 그날 밤을 분 단위로 갖고 있다. 그러나 **그대로 내려보내면 안 된다** —
    91편의 21:38 「휴식 시작 40초 만에 세미나실로 되돌아갔다」는 그 자체가 결정타다.
    공적 기록이라고 다 주면 첫 화면에서 범인이 드러난다.

    그래서 규칙은 하나다 — **플레이어가 이미 본 것만 시간 위에 세운다.**
      · 손에 쥔 단서·들은 알리바이·나눈 대화에 그 일이 이미 나와 있으면 → 올린다
      · 만난 사람이 제 입으로 한 말이면 → 「본인 주장」으로 표시해 올린다
    새 사실은 한 줄도 보태지 않는다. 아는 것을 시간순으로 정리해 줄 뿐이다.
    """
    v = _sess(sid)
    g, s = v["g"], v["s"]
    known = g.known_text() or ""
    met = set(getattr(g, "met", set()) or set())

    def _stems(t):
        out = set()
        for w in __import__("re").findall(r"[가-힣]{2,}", str(t or "")):
            x = _JOSA_T.sub("", w)
            if len(x) >= 2:
                out.add(x)
        return out

    # ★낱말 겹침으로는 안 된다 (2026-08-29 재수정).
    #   처음엔 「이미 본 글과 두 낱말만 겹치면 올린다」로 했더니, 오프닝에 이미 나온
    #   '세미나실·복도·회의' 때문에 열세 건 중 열두 건이 첫 화면에서 다 떴다 —
    #   **결정타인 21:38 CCTV까지.** 밑말을 빼도 이번엔 작가 주석이 새어 나왔다.
    #   시각은 timeline_events 에만 있고, 그 글은 원래 **설계 문서**로 쓰인 것이라
    #   「— 먼저 다녀간 것은 이때다」 같은 정답이 섞여 있다. 그러니 겹침이 아니라
    #   **출처로** 가른다. 두 가지만 올린다:
    #       ① 모두가 아는 공지 — 회의 시작·영상 종료·발견 신고 (who = all)
    #       ② 만난 사람이 **제 입으로** 한 말 (본인 진술) → 「본인 주장」으로 표시
    #   CCTV·영수증처럼 한 사람을 겨누는 기록은 올리지 않는다. 그건 찾아내야 할 몫이다.
    def _clean(t, _re=__import__("re")):
        t = str(t or "")
        t = _re.sub(r"\s*[—–]\s*[^—–]*?(?:이때다|이때이다)\s*\.?\s*$", "", t)
        t = _re.sub(r"\s*\([^)]*(?:사실|거짓|실은|진짜)[^)]*\)", "", t)
        return t.strip()

    rows = []
    for e in (s.get("timeline_events") or []):
        who = e.get("who")
        kf = str(e.get("known_from") or "")
        public = (who in (None, "", "all")
                  and any(w in kf for w in ("회의록", "모두")))
        by_word = (who in met and "진술" in kf)
        if not (public or by_word):
            continue
        rows.append({
            "time": e.get("time"), "slot": e.get("slot"),
            "cast_id": (who if who and who != "all" else None),
            "who": (g.cast.get(who, {}).get("name") if who and who != "all" else "모두"),
            "text": _clean(e.get("text")),
            "source": ("본인 주장" if by_word else "공지된 사실"),
        })
    rows.sort(key=lambda r: str(r.get("time") or ""))
    return {"rows": rows,
            "total": len(s.get("timeline_events") or []),
            "note": "아직 밝히지 못한 시각은 비어 있다 — 뒤지고 물을수록 채워진다.",
            "state": _view_state(v)}


@app.get("/session/{sid}/notebook", summary="사건수첩 (S-18) — 단서만")
def notebook(sid: str):
    v = _sess(sid)
    # ★cards 가 없으면 새로고침으로 판을 되찾을 때 화면이 통째로 튄다
    #   (2026-08-30, 되살아난 것). clues 는 id 목록, cards 는 그 카드다.
    rows = v["g"].state()["notebook"]        # 줄 하나가 dict 다 (id·round·medium…)
    live = getattr(v["g"], "clue_graph", None)
    return {"clues": rows,
            "cards": [_clue_card(v["s"], r["id"], live=live)
                      for r in rows if isinstance(r, dict) and r.get("id")]}


@app.post("/session/{sid}/combine", summary="단서 둘을 겹쳐 본다")
def combine(sid: str, body: CombineIn):
    """★단서 겹쳐보기 (2026-08-31, 팀원 제보 — "단서 겹쳐보기").

    엔진에는 처음부터 있던 기능인데(`GameSession.combine`) **API가 안 열려 있었다.**
    편당 조합이 평균 4.1개 준비돼 있으니, 화면만 붙이면 바로 쓸 수 있다.

    ■ 어느 둘이 붙는지는 **알려 주지 않는다.**
      「겹쳐지는 짝 목록」을 내려보내면 대질 때와 똑같은 잘못을 되풀이하는 것이다 —
      무엇과 무엇이 이어지는지 알아보는 것이 추리다. 아무 둘이나 겹쳐 볼 수 있고,
      안 붙으면 안 붙는다고만 답한다.

    ■ 행동 예산은 쓰지 않는다. 겹치는 것은 **이미 가진 것을 다시 보는 일**이라
      새로 얻는 것이 아니다. 여기에 값을 매기면 수첩을 여는 것이 무서워진다.
    """
    v = _sess(sid)
    r = v["g"].combine(body.clue_a, body.clue_b)
    if r.get("error"):
        raise HTTPException(400, r["error"])
    # ★points_to 는 떼고 보낸다 — **그 조합이 누구를 가리키는지**가 답이다.
    #   엔진은 내부에서 쓰려고 붙여 주지만, 화면으로 나가면 겹쳐 보기가
    #   범인 알려 주는 단추가 된다. 지목(/accuse) 전에는 어떤 응답에도 싣지 않는다.
    r = {k: val for k, val in r.items() if k not in ("points_to", "is_culprit")}
    return {**r, "state": _view_state(v)}


@app.post("/session/{sid}/accuse", summary="범인 지목 (S-21) — 되돌릴 수 없다. 여기서 진상이 열린다")
def accuse(sid: str, body: AccuseIn):
    v = _sess(sid)
    g, s = v["g"], v["s"]
    cul = next((c["id"] for c in s["cast"] if c.get("is_culprit")), None)
    correct = body.cast_id == cul
    # ★점수가 아니라 **성공·실패**로 가른다 (2026-08-30, 제보).
    #   "추리 성공은 범인과 흉기를 **모두** 맞췄을 때." 점수는 뒤에 참고로만 남긴다.
    #   흉기는 여전히 **선택 입력**이다 — 안 적어도 제출은 되고, 다만 성공은 아니다.
    true_weapon = str((s.get("death") or {}).get("weapon")
                      or (s.get("solution") or {}).get("weapon") or "").strip()
    said_weapon = str(body.weapon or "").strip()
    weapon_ok = bool(said_weapon) and said_weapon == true_weapon
    success = bool(correct and weapon_ok)
    n_sec = sum(len(x) for x in g.disclosed_secrets.values())
    sc = s.get("scoring") or {}
    pts = min((sc.get("culprit_correct", 5) if correct else 0)
              + n_sec * sc.get("secret_revealed_each", 1), sc.get("max", 10))
    grade = ""
    for gr in sorted(((s.get("ending") or {}).get("grades") or []),
                     key=lambda x: x.get("min", 0)):
        if pts >= gr.get("min", 0):
            grade = gr.get("name", "")
    end = s.get("ending") or {}
    # ★갈래는 **성공했는가**로 고른다 (2026-08-30).
    #   전에는 '범인을 맞혔는가'로 골랐다. 그러면 흉기를 틀렸을 때 화면엔 FAIL 이 뜨는데
    #   이야기는 「붙잡힌 밤」이 흘러 앞뒤가 어긋난다. 둘 다 맞아야 ARREST 이므로,
    #   수법을 못 밝히면 **붙잡아 둘 수 없다** — 이야기도 빠져나간 밤으로 간다.
    # ★판정을 **세션에 적어 둔다** (2026-08-31).
    #   여태 v["verdict"] 를 읽는 곳만 있고 넣는 곳이 없었다. 그래서
    #   state.verdict 가 늘 비었고, 새로고침으로 판을 되찾으면 맞혔는데도
    #   진상이 닫힌 채로 돌아왔다.
    # ★발표용은 여기서 끝난다 — 맞았는지도 말하지 않는다.
    #   맞았다고 알려 주는 순간 범인이 누구인지도 함께 알려 주는 셈이다.
    if _hidden(v):
        v["verdict"] = "SUBMITTED"
        v["verdict_summary"] = {
            "named": g.cast.get(body.cast_id, {}).get("name"),
            "verdict": "SUBMITTED",
            "hide_answer": True,
            # correct·score·grade·max 는 넣지 않는다 — 맞았는지가 곧 답이다
            "withheld_reason": "이 판은 발표용입니다 — 진상은 밝히지 않습니다.",
        }
        return {
            "hide_answer": True,
            "verdict": "SUBMITTED",
            "verdict_line": "제출했습니다. 이 밤의 진상은 여기서 밝히지 않습니다.",
            "named": g.cast.get(body.cast_id, {}).get("name"),
            "said_weapon": said_weapon or None,
            # 몇 사람에게서 무엇을 꺼냈는지는 제 손으로 한 일이라 남긴다 —
            # 다만 **본문은 연 것만** 준다. 못 연 것을 펴 보이면 답으로 가는 길이 보인다.
            "secrets_record": {
                "opened": n_sec,
                "total": sum(1 for c in s["cast"] for x in (c.get("secrets") or [])
                             if x.get("text")),
                "items": [{"cast_id": c["id"], "cast_name": c["name"],
                           "opened": True, "text": tx}
                          for c in s["cast"]
                          for tx in sorted(g.disclosed_secrets.get(c["id"], set()))],
            },
            "ending": {
                "narration": "그리고 그 밤의 일은, 아직 아무에게도 말해지지 않았다.",
                "branch": {"label": "제출한 밤", "beats": [
                    "당신은 이름을 적어 냈다.",
                    "봉투는 그대로 봉해졌다.",
                    "이 사건을 아직 풀지 않은 사람이 남아 있기 때문이다.",
                ], "result_line": ""},
                "ui": {"show_page_number": False, "text_style": "pre-line"},
                "reveal_order": {}, "replay": {},
            },
            "truth": None, "reenactment": None, "culprit_reveal": None,
            "withheld": {"truth": True, "reenactment": True, "culprit_face": True,
                         "reason": "이 판은 발표용입니다 — 진상은 밝히지 않습니다."},
            "sfx": W.event_cue("verdict_wrong"),
            "state": _view_state(v),
        }

    v["verdict"] = "ARREST" if success else "FAIL"
    v["verdict_summary"] = {
        "named": g.cast.get(body.cast_id, {}).get("name"),
        "correct": correct, "score": pts, "max": sc.get("max", 10),
        "grade": grade, "verdict": v["verdict"], "success": success,
    }
    branch = (end.get("branches") or {}).get("caught" if success else "escaped")
    # ★못 맞힌 밤에는 **엔딩 글도 범인을 부르지 않는다** (2026-08-31).
    #   진상·재연을 감춰 놓고 갈래 글이 "그날 밤 손을 댄 사람은 ○○다" 하고
    #   읊으면 감춘 것이 아무 뜻이 없다. 실제로 91편 escaped 갈래가 그랬다.
    #   글은 고쳤지만, 다른 편에도 같은 자리가 있을 수 있으니 여기서 한 번 더
    #   거른다 — 범인 이름이 든 줄은 빼고 내려보낸다.
    if not success and isinstance(branch, dict):
        cul_name = next((c["name"] for c in s["cast"] if c["id"] == cul), None)
        if cul_name:
            branch = {**branch,
                      "beats": [b for b in (branch.get("beats") or [])
                                if cul_name not in b]}
    #   같은 FAIL 이라도 사정이 다르다. 화면이 첫 줄을 갈라 읽을 수 있게 한 줄 준다.
    if success:
        verdict_line = "범인과 수법을 모두 밝혔다."
    elif correct:
        verdict_line = "이름은 맞았다. 그러나 수법을 짚지 못해 그를 붙잡아 둘 수 없었다."
    else:
        verdict_line = "이름을 잘못 짚었다. 진범은 그 밤을 빠져나갔다."
    # ★비밀은 **점수가 아니라 기록**이다 (2026-08-31, 제보 — "비밀 맞춘 거 점수?").
    #   판정은 ARREST/FAIL 하나로 끝난다. 다만 다섯 사람에게서 무엇을 꺼냈는지는
    #   한 판의 성적표라 보여 줄 값어치가 있다.
    #   화면 요구: **연 비밀은 하얀 글씨, 못 연 비밀은 눌러야 보이게.**
    #   그러려면 못 연 것의 본문도 함께 내려가야 한다 — 지목이 끝난 뒤이므로 괜찮다.
    secrets = []
    for c in s["cast"]:
        opened_here = g.disclosed_secrets.get(c["id"], set())
        for sec in (c.get("secrets") or []):
            tx = sec.get("text")
            if not tx:
                continue
            secrets.append({
                "cast_id": c["id"], "cast_name": c["name"],
                "opened": tx in opened_here,
                "text": tx,                       # 못 연 것은 화면이 가려 두었다가 눌러 편다
                "note": sec.get("note"),
                "document": sec.get("document"),
            })

    return {
        "named": g.cast.get(body.cast_id, {}).get("name"),
        "secrets_record": {"opened": n_sec, "total": len(secrets), "items": secrets},
        # 화면이 크게 띄울 것 — ARREST / FAIL
        "verdict": "ARREST" if success else "FAIL",
        "success": success,
        "culprit_correct": correct,      # 범인만 맞힌 경우도 알 수 있게
        "weapon_correct": weapon_ok,
        "verdict_line": verdict_line,     # ARREST/FAIL 아래에 한 줄로
        "true_weapon": true_weapon if (correct or True) else None,   # 지목 뒤이므로 공개
        "correct": correct, "points": pts, "max": sc.get("max", 10), "grade": grade,
        "secrets_opened": n_sec,
        # ★못 맞히면 **진상도 재연도 열리지 않는다** (2026-08-31, 제보 —
        #   "틀리면 엔딩 장면 빼기" → 확인: 진상·재연 둘 다 빼고 도주 장면만).
        #   답을 공짜로 알려 주면 지목이 형식이 된다. 밝혀낸 사람만 그 밤을 본다.
        "sfx": W.event_cue("verdict_correct" if success else "verdict_wrong"),
        "bgm": A.cue("reveal"),
        "truth": W.reveal_view(s, W.photos(s)) if success else None,
        "reenactment": W.reenactment_view(s) if success else None,
        "withheld": None if success else {
            "truth": True, "reenactment": True, "culprit_face": True,
            "reason": "밝혀내지 못했다. 그 밤에 무슨 일이 있었는지는 끝내 알 수 없다.",
        },
        # ★범인의 얼굴은 **ARREST 화면에서** 처음 보인다 (2026-08-31, 제보).
        #   진상 낭독에는 이름도 얼굴도 없다 — 재연에서 이름이 나오고,
        #   붙잡히는 화면에서 얼굴이 나온다. 순서가 곧 연출이다.
        "culprit_reveal": ({
            "cast_id": cul,
            "name": next((c["name"] for c in s["cast"] if c["id"] == cul), None),
            "portrait": A.portrait(cul, W.photos(s)),
            "show_on": "ARREST",
        } if success else None),
        "ending": {                                       # S-24 엔딩
            "narration": _sn(s, "ending", grade),
            "branch": branch,
            # ★엔딩에도 쪽번호를 찍지 않는다 (2026-08-30, 제보).
            #   beats 는 이미 한 줄이 한 호흡이라, 그대로 줄바꿈해 쌓으면 된다.
            "ui": {"show_page_number": False, "text_style": "pre-line"},
            # ★다시보기와 자백 순서도 **밝혀낸 밤에만** 열린다 (2026-08-31).
            #   replay 는 그 밤의 시간표를 줄줄이 펴 보이는데, 거기에
            #   「암전 사이 옆자리에서 컵에 …를 넣었다」까지 적혀 있다.
            #   진상을 감춰 놓고 이것을 열면 감춘 뜻이 없다.
            "reveal_order": ((end.get("reveal_order") or {}) if success else {}),
            "replay": ((end.get("replay") or {}) if success else {}),
        },
    }


# ★화면까지 이 서버가 내준다 — Render 한 대로 끝난다 (2026-09-02).
#   web/ 폴더가 있을 때만 켜진다. 없으면 예전처럼 화면은 Netlify 가 맡는다.
#   ※ 반드시 **API 길을 다 등록한 뒤** 걸어야 한다. 남는 주소를 전부
#     index.html 로 넘기는 규칙이라, 먼저 걸면 /session 까지 삼킨다.
_WEB = None   # 아래 맨 끝에서 켠다


@app.get("/demo", response_class=HTMLResponse, include_in_schema=False)
def demo():
    p = os.path.join("docs", "demo.html")
    if not os.path.exists(p):
        return HTMLResponse("<p>docs/demo.html 이 없습니다.</p>", status_code=404)
    return HTMLResponse(open(p, encoding="utf-8").read())


def main():
    global LLM
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    ap.add_argument("--no-llm", action="store_true", help="대사 생성 없이 판단만")
    a = ap.parse_args()

    if not a.no_llm:
        LLM = PA.open_llm()            # .apikey 또는 MM_API_KEY
        print("  용의자 대사 — " + ("서버가 만든다" if LLM else "키가 없어 자리만 비워 둔다"))
    import uvicorn
    print(f"  문서 http://{a.host}:{a.port}/docs   ·   데모 http://{a.host}:{a.port}/demo")
    uvicorn.run(app, host=a.host, port=a.port)


# ── 화면 내주기 ───────────────────────────────────────────────────────
#   여기가 파일의 맨 끝인 것이 중요하다 — 위의 API 길들이 먼저 잡히고,
#   남는 주소만 화면으로 간다.
_WEB = W.serve_web(app, os.environ.get("WEB_DIR", "web"))
if _WEB:
    print("  화면도 이 서버가 내줍니다 (web/) — Netlify 없이 한 대로 됩니다")


if __name__ == "__main__":
    main()
