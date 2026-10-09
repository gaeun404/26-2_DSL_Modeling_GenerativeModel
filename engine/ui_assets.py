# -*- coding: utf-8 -*-
"""ui_assets.py — **파일 이름이 곧 지도다.**

재민이 만든 91_dsl GAME 번들(이미지 108 · BGM 43)은 파일 이름 안에 ID를 담고
있다 — `91_portrait_C1.png`, `91_clue_K7.png`, `91_place_P2.png`,
`bgm/character_themes/C3.wav`. 그래서 표를 따로 들 필요가 없다.
**ID를 넣으면 URL이 나온다.** 없는 파일이면 None을 돌려준다 — 화면은 빈 자리를
그대로 그리면 된다.

번들 위치는 MM_ASSETS_DIR 로 바꿀 수 있다(기본 `assets`).
서버는 그 폴더를 `/assets` 로 열어 둔다.

■ 파일을 안 들고도 주소는 낼 수 있다 (배포용)

  밖에 세울 때는 그림·음원을 프론트(CDN)에 두는 편이 낫다 — 백엔드는 가벼워지고
  이미지는 CDN이 훨씬 잘 뿌린다. 그러면 백엔드에는 파일이 없다.

  그래서 `assets_manifest.json`(있는 파일 목록 한 장)을 읽는다. 목록에 있으면
  주소를 낸다. 목록도 파일도 없으면 여전히 None — **없는 그림의 주소를 내지
  않는다**는 성질은 그대로다.
"""
import json
import os
from urllib.parse import quote

# 정적 파일 뿌리 — server.py 가 이 폴더를 /assets 로 마운트한다
ASSETS_DIR = os.environ.get("MM_ASSETS_DIR", "assets")
ASSETS_URL = "/assets"

# 파일을 안 들고 있을 때 참고할 목록. build_deploy.sh 가 만들어 둔다.
_MANIFEST_PATH = os.environ.get("MM_ASSETS_MANIFEST", "assets_manifest.json")
try:
    _MANIFEST = set(json.load(open(_MANIFEST_PATH, encoding="utf-8")))
except Exception:
    _MANIFEST = set()

BUNDLE = "91_dsl"                      # 이 편의 이미지·음원 묶음 폴더 이름
PREFIX = "91"                          # 파일 이름 맨 앞에 붙은 편 번호

# ★얼굴은 **생성 초상**으로 통일한다 (2026-08-29, 시연 제보).
#   시나리오에는 "카드는 실제 사진을 쓴다"고 적혀 있었고 그대로 따랐는데,
#   제보가 이렇게 왔다 — "사진이 규격에 안 맞고 심지어 crop한 실제 사진이다."
#   증명사진은 1:1 인데 카드 자리는 세로로 길어 얼굴이 잘렸고, 생성 초상
#   (512×768)과 섞여 톤도 어긋났다. 실존 인물 사진을 화면에 계속 띄우는 일도
#   내보낼 것을 생각하면 피하는 편이 낫다.
#   MM_REAL_PHOTOS=1 을 주면 예전처럼 실제 사진으로 돌아간다.
USE_REAL_PHOTOS = os.environ.get("MM_REAL_PHOTOS", "0") == "1"

# 압박 판정(stance) → 표정 슬롯. mmapi.js 의 faceOf 와 같은 셈이다.
#   ANSWER/DEFLECT → 평정 · FLINCH → 흔들림 · ADMIT/BREAK → 무너짐
_STANCE_FACE = {"ANSWER": "calm", "DEFLECT": "calm", "FLINCH": "nervous",
                "ADMIT": "tense", "BREAK": "tense"}


def _exists(rel):
    """번들 안에 진짜 있는 파일만 URL로 만든다.

    손에 파일이 있으면 그것을 보고, 없으면 목록을 본다.
    """
    if _MANIFEST:
        return f"{BUNDLE}/{rel}" in _MANIFEST
    return os.path.exists(os.path.join(ASSETS_DIR, BUNDLE, rel))


def url(rel):
    """번들 상대경로 → 브라우저가 부를 주소. 파일이 없으면 None."""
    if not rel or not _exists(rel):
        return None
    return f"{ASSETS_URL}/{BUNDLE}/{rel}"


def raw_url(path):
    """시나리오가 들고 있는 `assets/dsl/한도윤.png` 같은 경로를 주소로."""
    if not path:
        return None
    p = str(path).lstrip("/")
    inner = p[len("assets/"):] if p.startswith("assets/") else p
    if not (inner in _MANIFEST if _MANIFEST
            else os.path.exists(os.path.join(ASSETS_DIR, inner))):
        return None
    # 이 폴더의 파일 이름은 한글이다(한도윤.png). 주소로 나갈 때는 인코딩해 둔다.
    return f"{ASSETS_URL}/{quote(inner)}"


# ── 사람 ──────────────────────────────────────────────────────────────
def portrait(cast_id, photos=None):
    """인물 카드에 붙는 얼굴.

    기본은 생성 초상. 다만 **생성 초상을 못 찾으면 실제 사진으로 물러선다** —
    번들이 없는 환경(저장소만 받아 띄운 서버)에서 얼굴 자리가 통째로 비는 것보다
    낫다. assets/dsl 여섯 장은 저장소에 함께 있다.
    """
    if USE_REAL_PHOTOS and photos:
        u = raw_url((photos or {}).get(cast_id))
        if u:
            return u
    return (url(f"portraits/{PREFIX}_portrait_{cast_id}.png")
            or raw_url((photos or {}).get(cast_id)))


def face(cast_id, stance=None, slot=None):
    """심문 화면의 표정. stance 를 주면 판정에 맞는 얼굴로 바꾼다."""
    s = slot or _STANCE_FACE.get(str(stance or "").upper(), "calm")
    return url(f"emotions/{PREFIX}_emotion_{cast_id}_{s}.png")


def faces(cast_id):
    """표정 세 벌을 한꺼번에 — 프론트가 미리 받아 두고 갈아 끼운다."""
    return {"calm": face(cast_id, slot="calm"),
            "shaken": face(cast_id, slot="nervous"),
            "broken": face(cast_id, slot="tense")}


def fullbody(cast_id):
    """장소에 서 있는 전신."""
    return url(f"fullbody/{PREFIX}_fullbody_{cast_id}.png")


# ── 장소 ──────────────────────────────────────────────────────────────
def place(place_id):
    return url(f"places/{PREFIX}_place_{place_id}.png")


def place_thumb(place_id):
    return url(f"maps/{PREFIX}_map_{place_id}.png")


# ── 단서 ──────────────────────────────────────────────────────────────
def clue(clue_id):
    return url(f"clues/{PREFIX}_clue_{clue_id}.png")


def clue_full(clue_id):
    return url(f"clues_full/{PREFIX}_clue_full_{clue_id}.png")


# ── 삽화 ──────────────────────────────────────────────────────────────
def story(page):
    """오프닝 나레이션 1~14쪽."""
    return url(f"story/{PREFIX}_open_{int(page):02d}.png")


def reenact(no):
    """범행 재연 컷 1~6."""
    return url(f"reenact/{PREFIX}_reenact_{int(no)}.png")


def scene_after():
    """사건 뒤의 현장."""
    return url(f"scene/{PREFIX}_scene_after.png")


# ── 소리 ──────────────────────────────────────────────────────────────
def bgm(group, name):
    """음악 한 곡.

    배포할 때는 WAV(한 곡 19MB)를 MP3로 줄여 올린다 — 43곡이 471MB에서
    30MB 아래로 내려간다. 줄인 것이 있으면 그것을 먼저 쓰고, 없으면 원본 WAV.
    """
    return (url(f"bgm/{group}/{name}.mp3")
            or url(f"bgm/{group}/{name}.wav"))


def cue(name):
    return bgm("cues", name)


def event_cue(name):
    return bgm("event_cues", name)


def ui_music(name):
    return bgm("ui_music", name)


def character_theme(cast_id):
    return bgm("character_themes", cast_id)


def place_cue(place_id, after_murder=True):
    """장소 음악은 살인 전/후 두 벌이다. 게임 안에서는 늘 '뒤'다."""
    return bgm("place_cues", f"{place_id}_{'post' if after_murder else 'pre'}_murder")


def _bgm_ids(group):
    """번들에 실제로 있는 곡 이름. 파일이 없는 배포(목록 모드)에서도 똑같이 센다."""
    prefix = f"{BUNDLE}/bgm/{group}/"
    if _MANIFEST:
        names = [p[len(prefix):] for p in _MANIFEST if p.startswith(prefix)]
    else:
        d = os.path.join(ASSETS_DIR, BUNDLE, "bgm", group)
        names = os.listdir(d) if os.path.isdir(d) else []
    return sorted({os.path.splitext(n)[0] for n in names
                   if n.endswith((".wav", ".mp3"))})


def audio_book():
    """화면이 쓰는 소리를 한 장에 모아 내려보낸다.

    ★장소 곡과 인물 테마도 같이 싣는다 (2026-08-29, 4차 제보 — "게임팩에 넣는
      위치가 다 있을 텐데").

      맞다. 시나리오 `ui.screens[].bgm` 에 화면마다 어느 곡인지 적혀 있다 —
      장소 조사는 `place_cues.{place_id}`, 심문은 `character_themes.{cast_id}`.
      그런데 이 목록에는 cues·events·ui 셋뿐이라, 화면이 그 둘을 부를 방법이
      없었다. 마흔세 곡 중 열여덟 곡만 울던 까닭이다.

      이름은 번들에 있는 것을 그대로 센다 — 시나리오마다 장소 수가 달라도
      고칠 것이 없다.
    """
    return {
        "cues": {n: cue(n) for n in
                 ("intro", "investigation", "interrogation", "discovery",
                  "climax", "reveal", "ending")},
        "events": {n: event_cue(n) for n in
                   ("round_start", "search_hit", "search_miss", "clue_found",
                    "clue_decisive", "clue_forensic", "secret_open",
                    "event_sting", "red_herring", "time_low", "life_lost",
                    "accusation", "verdict_correct", "verdict_wrong")},
        "ui": {n: ui_music(n) for n in
               ("title", "loading", "world_input", "notebook", "accuse")},
        # 장소 곡은 살인 전/후 두 벌이다. 열쇠는 "PC_post_murder" 처럼 통째로 준다.
        "places": {n: bgm("place_cues", n) for n in _bgm_ids("place_cues")},
        "characters": {n: character_theme(n) for n in _bgm_ids("character_themes")},
    }
