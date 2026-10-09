# -*- coding: utf-8 -*-
"""
soundtrack.py — **장면마다 다른 음악·효과음**을 만든다.

왜 필요한가
  구조는 이미 있었다 — cues 7개, event_cues 12개, 인물 테마 5개, 장소마다 사건 전/후.
  그런데 실제로 생성모델에 들어가는 **말**이 거의 같았다.
  · 인물 테마: 다섯 중 셋이 persona_flavor "표준", 악기 하나와 난수 BPM만 다름
  · 장소 큐: 서재도 집사 방도 flavor가 똑같이 "서재"
  · 라운드 전환·단서 공개 효과음: 편마다 구별이 없음
  · 진상(엔딩): 사건 음악과 결이 같아서 절정이 절정처럼 안 들림

  같은 프롬프트를 주면 같은 곡이 나온다. 그러니 **장면의 성격을 말로 갈라야** 한다.

무엇을 하나
  ① 인물 테마    신분·성격·말투에서 결을 뽑고, 다섯이 서로 겹치지 않게 한다
  ② 장소 큐      그 방의 주인과 쓰임에서 결을 뽑는다(사건 전/후 따로)
  ③ 효과음       라운드 전환·단서·결정타·오답 등 12종을 길이·질감까지 적는다
  ④ 진상 낭독    추리물의 해명 장면 관습으로 — 초시계 오스티나토, 금관 스탭,
                조여 오는 현. 다른 어떤 큐와도 겹치지 않는 자리다
  ⑤ 장면 목록    music_scenes[] — 음악이 필요한 모든 자리를 한 표로 뽑는다.
                팀에서 받은 장면 목록과 이걸 맞춰 보면 빠진 자리가 드러난다

  ★ 특정 작품의 곡을 흉내 내라고 적지 않는다. 장르 관습만 적는다.

사용:
    python soundtrack.py "scenarios/[0-9]*.json"
    python soundtrack.py --check
    python soundtrack.py --manifest out/13_푸른수염.json    # 장면 목록만 뽑기
"""
import json, glob, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")

# ── 인물 결 — 신분·성격에서 뽑는다 ────────────────────────────────────
FLAVOR = [
    (["인색", "셈", "계산"], "쩨쩨하고 계산적인", "짧게 끊는 저역 피치카토, 인색하게 아끼는 음표",
     "stingy plucked bass motif, notes withheld, comic-sinister"),
    (["과묵", "조용", "말수"], "말 없고 단단한", "긴 지속음 하나. 거의 움직이지 않는다",
     "single sustained drone, almost motionless, withholding"),
    (["수다", "말이 많", "눈치"], "재잘거리고 부산한", "잔음표가 쉴 새 없이 오간다",
     "restless chattering ostinato, quick small notes"),
    (["능글", "넉살", "잇속"], "능청스럽고 미끄러운", "반음 미끄러지는 선율, 살짝 익살",
     "sly chromatic slide, tongue-in-cheek"),
    (["여리", "겁", "순정"], "여리고 떨리는", "높은 음역의 가는 선율, 흔들리는 비브라토",
     "fragile high melody, trembling vibrato"),
    (["다부", "단호", "굳"], "곧고 단호한", "또박또박 걷는 저역, 흔들림 없다",
     "steady marching low line, unwavering"),
    (["지쳐", "냉소", "체념"], "지치고 메마른", "느리게 처지는 하행 선율",
     "slow sagging descending line, worn out"),
    (["거칠", "집요", "험"], "거칠고 집요한", "같은 음형을 물고 늘어진다",
     "gritty repeated figure that refuses to let go"),
]
FLAVOR_POOL = [
    ("서늘하고 속을 알 수 없는", "빈 5도 위의 얇은 선율", "hollow fifths, unreadable"),
    ("따뜻한 척하는", "부드럽게 시작해 어긋나는 화음", "warm opening that sours"),
    ("초조하고 서두르는", "박을 앞질러 나가는 리듬", "rushing ahead of the beat"),
    ("무겁고 눌린", "저역에 눌린 화음, 숨이 짧다", "pressed low chords, short breath"),
    ("맑고 위태로운", "유리처럼 맑은 고음, 금 가기 직전", "glassy high tone about to crack"),
]

PLACE_FLAVOR = [
    (["금단", "지하", "통로", "밀실", "봉인"], "열지 말아야 할 곳", "잔향이 길고 저역이 무겁다"),
    (["서재", "사랑방", "회의", "집무"], "종이와 등불", "책장·먼지·마른 종이의 정적"),
    (["곳간", "창고", "서버", "광"], "쇠와 곡식", "낮은 울림, 문 여닫는 쇳소리"),
    (["부엌", "탕비", "주방"], "물과 불", "달그락거리는 생활음, 온기"),
    (["방", "객방", "침소", "거처"], "사람의 자취", "옷깃·이불·숨의 결"),
    (["별채", "행랑", "옥상", "뜰", "숲"], "바깥 공기", "바람과 먼 소리, 여백"),
]

# ── 효과음 — 길이와 질감까지 적어야 짧은 소리가 산다 ──────────────────
SFX = {
    "round_start":   ("라운드 전환", "1.5~2초", "낮은 종 한 번 + 숨을 들이켜는 여백. 판이 한 칸 깊어진다",
                      "single low bell with long tail, one breath of silence, 2s sting"),
    "clue_found":    ("단서 발견", "0.8초", "맑은 한 점. 짧고 또렷하게",
                      "bright single chime, short and clear, 0.8s"),
    "clue_forensic": ("검안 결과", "1.2초", "차갑고 건조한 두 음. 감정 없이",
                      "cold dry two-note motif, clinical, 1.2s"),
    "clue_decisive": ("결정적 증거", "2.5초", "저역이 쿵 내려앉고 현이 위로 조인다. 판이 뒤집히는 소리",
                      "low impact then rising strings, the board turns, 2.5s"),
    "red_herring":   ("함정 단서", "1초", "맞은 듯 아닌 듯 반음 어긋난 종",
                      "chime a semitone off, almost-right, 1s"),
    "search_hit":    ("탐색 성공", "0.6초", "가벼운 두 음 상행", "light rising two notes, 0.6s"),
    "search_miss":   ("탐색 실패", "0.5초", "짧게 꺼지는 한 음", "short dampened note, 0.5s"),
    "accusation":    ("지목 선언", "3초", "모든 소리가 멎었다가 심장 박동만 남는다",
                      "everything drops out, heartbeat pulse only, 3s"),
    "verdict_correct": ("정답", "4초", "쌓아 올린 화음이 트여 나간다. 시원하되 승리는 아니다",
                        "chord opens out, relief rather than triumph, 4s"),
    "verdict_wrong": ("오답", "4초", "화음이 무너져 저역만 남는다", "chord collapses to bare low, 4s"),
    "life_lost":     ("기회 소진", "1.5초", "금속이 한 번 긁힌다", "single metallic scrape, 1.5s"),
    "time_low":      ("시간 촉박", "루프", "초시계 같은 등박이 점점 빨라진다",
                      "ticking pulse gradually accelerating, loop"),
    "secret_open":   ("비밀 실토", "2초", "긴장이 한 겹 풀리며 낮은 한숨 같은 화음",
                      "one layer of tension releases, sighing low chord, 2s"),
    "event_sting":   ("중반 이벤트", "2.5초", "예고 없이 끼어드는 타격음. 진행을 강제로 끊는다",
                      "abrupt interrupting hit, cuts the scene, 2.5s"),
}

# ── 진상 낭독 — 추리물의 해명 장면 관습 ───────────────────────────────
#   ※ 특정 작품의 곡을 베끼라는 뜻이 아니다. 장르가 공유하는 문법을 적는다.
REVEAL = {
    "name": "진상 낭독",
    "when": "엔딩 — 트릭과 범인을 밝히는 낭독 위에",
    "structure": [
        "① 초시계 같은 등박으로 시작한다(저역 스타카토 또는 피치카토). 느리게.",
        "② 낭독이 진행될수록 박이 조금씩 빨라지고 성부가 하나씩 쌓인다.",
        "③ 트릭의 핵심이 밝혀지는 문장에서 금관/저현이 한 번 크게 찍는다.",
        "④ 범인의 이름이 나오는 순간 모든 소리가 멎는다. 1초 정적.",
        "⑤ 정적 뒤에 주제 선율이 넓게 펼쳐지며 마무리한다.",
    ],
    "mood": "긴장되고 통쾌한. 무섭기보다 **명쾌한** 쪽",
    "avoid": ["공포 연출", "사건 초반 음악의 재탕", "낭독을 덮는 큰 음량"],
    "prompt_en": ("detective-reveal cue: ticking staccato ostinato, gradually accelerating, "
                  "layered strings entering one by one, single brass stab at the twist, "
                  "full stop with 1s silence at the culprit's name, then broad theme; "
                  "tense and clarifying, not horror; instrumental"),
}


# 본 큐 다섯 — 인트로·진상 말고도 각자 결이 달라야 한다
MAIN_CUES = {
    "discovery": ("주검이 나온 순간", "숨이 멎는다. 소리가 한 번 빠졌다가 저역만 남는다",
                  "sudden drop-out then bare low drone, breath held, shock not horror"),
    "investigation": ("장소를 뒤지는 동안", "낮게 깔리는 바닥. 발소리와 옷깃이 들릴 만큼 비운다",
                      "very sparse investigative bed, room for footsteps, minimal pulse, loop"),
    "interrogation": ("마주 앉아 묻는 동안", "느린 등박 하나. 말을 덮지 않는다",
                      "slow single pulse under dialogue, nearly transparent, tension held"),
    "climax": ("결정타를 들이대는 자리", "성부가 겹겹이 쌓이고 박이 조여 온다",
               "layers stacking, tempo tightening, pre-reveal pressure"),
    "ending": ("판이 끝난 뒤", "다 지나간 자리의 여운. 넓고 느리게",
               "aftermath, broad and slow, resolution with a shadow left"),
}


def _flavor(c, used):
    per = (c.get("persona") or {}).get("personality") or ""
    hit = next(((m, d, e) for keys, m, d, e in FLAVOR if any(k in per for k in keys)), None)
    if hit and hit[0] not in used:
        used.add(hit[0]); return hit
    for m, d, e in FLAVOR_POOL:
        if m not in used:
            used.add(m); return (m, d, e)
    return hit or FLAVOR_POOL[0]


def _place_flavor(name):
    for keys, lab, note in PLACE_FLAVOR:
        if any(k in name for k in keys):
            return lab, note
    return "그 방의 공기", "특징 없는 정적"


def apply(s):
    b = s.setdefault("bgm", {})
    pal = b.get("palette") or {}
    inst = pal.get("instruments") or []
    scale = pal.get("scale", "modal")
    cast = {c["id"]: c for c in s["cast"]}
    # ★ 모든 트랙은 시나리오 공통 주제의 변주여야 한다(verify: BGM-theme_unity).
    #   새 큐를 만들 때 이 표를 안 달면 톤 통일이 깨진다.
    theme = (b.get("main_theme") or {}).get("id")

    # ① 인물 테마
    used = set()
    ct = b.setdefault("character_themes", {})
    for i, c in enumerate(s["cast"]):
        mood, desc, en = _flavor(c, used)
        t = ct.setdefault(c["id"], {})
        vo = (c.get("persona") or {}).get("voice") or {}
        t.update({
            "character": c["name"], "mood": mood, "figure": desc,
            "when": f"{c['name']} 심문 · 그의 자리에 들어설 때",
            "leitmotif_instrument": t.get("leitmotif_instrument") or (inst[i % len(inst)] if inst else ""),
            "prompt_en": (f"character leitmotif: {en}; solo "
                          f"{t.get('leitmotif_instrument','instrument')}; {scale}; "
                          f"{t.get('bpm', 80)} BPM; sparse, sits under dialogue; instrumental"),
            "note": f"말투는 {vo.get('form','')}. 음악도 그 결을 따른다.",
        })

    # ② 장소 큐
    pc = b.setdefault("place_cues", {})
    for p in s["map"]["places"]:
        lab, note = _place_flavor(p["name"])
        cell = pc.setdefault(p["id"], {})
        owner = cast.get(p.get("owner") or "", {}).get("name")
        cell.update({"place_name": p["name"], "flavor": lab, "flavor_note": note})
        for state, mood, en in [
            ("pre_murder", "아직 아무 일도 없던", "calm room tone, unremarkable, faint life"),
            ("post_murder", "무언가 지나간 뒤의", "same room gone cold, one element missing, unease"),
        ]:
            cur = cell.setdefault(state, {})
            cur.update({
                "name": f"{p['name']} — {'사건 전' if state=='pre_murder' else '사건 후'}",
                "mood": f"{mood} {lab}",
                "note": note + (f" · {owner}의 자리" if owner else ""),
                "prompt_en": (f"{en}; {lab}; {', '.join(inst[:2])}; very sparse ambient bed; "
                              f"{cur.get('bpm', 70)} BPM; loopable; instrumental"),
            })

    # ③ 효과음
    ev = b.setdefault("event_cues", {})
    for k, (nm, dur, note, en) in SFX.items():
        cell = ev.setdefault(k, {})
        cell.update({"name": nm, "length": dur, "note": note,
                     "prompt_en": f"{en}; {', '.join(inst[:2])}; no melody loop, one-shot"})
        if theme:
            cell.setdefault("theme_variation", theme)

    # ④ 본 큐 다섯
    cues = b.setdefault("cues", {})
    for k, (when, note, en) in MAIN_CUES.items():
        cell = cues.setdefault(k, {})
        cell.setdefault("name", k)
        cell.update({"when": when, "mood": note,
                     "prompt_en": (f"{en}; {', '.join(inst[:3])}; {scale}; "
                                   f"{cell.get('bpm', 72)} BPM; instrumental, loopable")})

    # ④-2 진상 낭독
    rv = cues.setdefault("reveal", {})
    rv.update(REVEAL)
    rv["prompt_en"] = REVEAL["prompt_en"] + f"; {', '.join(inst[:3])}"

    # ⑤ 장면 목록
    # 빠진 곳이 없는지 한 번 더 훑는다
    if theme:
        pools = [b.get("cues") or {}, b.get("event_cues") or {}, b.get("character_themes") or {}]
        for pool in pools:
            for v in pool.values():
                if isinstance(v, dict):
                    v.setdefault("theme_variation", theme)
        for v in (b.get("place_cues") or {}).values():
            for st in ("pre_murder", "post_murder"):
                if isinstance(v.get(st), dict):
                    v[st].setdefault("theme_variation", theme)

    b["music_scenes"] = manifest(s)
    return len(b["music_scenes"])


def manifest(s):
    """음악·효과음이 필요한 자리를 전부 뽑는다. 팀 목록과 맞춰 보는 표."""
    b = s.get("bgm") or {}
    rows = []
    for k, v in (b.get("cues") or {}).items():
        rows.append({"slot": f"cue:{k}", "name": v.get("name", k),
                     "when": v.get("when", ""), "kind": "music",
                     "prompt_en": v.get("prompt_en", "")})
    for cid, v in (b.get("character_themes") or {}).items():
        rows.append({"slot": f"character:{cid}", "name": v.get("character", cid),
                     "when": v.get("when", ""), "kind": "music",
                     "prompt_en": v.get("prompt_en", "")})
    for pid, v in (b.get("place_cues") or {}).items():
        for st in ("pre_murder", "post_murder"):
            c = v.get(st) or {}
            rows.append({"slot": f"place:{pid}:{st}", "name": c.get("name", pid),
                         "when": f"{v.get('place_name','')} 탐색", "kind": "music",
                         "prompt_en": c.get("prompt_en", "")})
    for k, v in (b.get("event_cues") or {}).items():
        rows.append({"slot": f"sfx:{k}", "name": v.get("name", k),
                     "when": v.get("length", ""), "kind": "sfx",
                     "prompt_en": v.get("prompt_en", "")})
    return rows


def check(s):
    b = s.get("bgm") or {}
    bad = []
    moods = [v.get("mood") for v in (b.get("character_themes") or {}).values()]
    if len(set(moods)) < len(moods):
        bad.append(f"인물 테마 결이 겹친다: {len(set(moods))}/{len(moods)}가지")
    for k, v in (b.get("event_cues") or {}).items():
        if not v.get("prompt_en"):
            bad.append(f"효과음 {k}: 프롬프트 없음")
    rv = (b.get("cues") or {}).get("reveal") or {}
    if not rv.get("structure"):
        bad.append("진상 낭독 큐에 구성이 없다")
    if not b.get("music_scenes"):
        bad.append("장면 목록이 없다")
    return (not bad), bad


if __name__ == "__main__":
    if "--check" in sys.argv:
        for p in sorted(glob.glob("scenarios/[0-9]*.json")):
            ok, bad = check(json.load(open(p, encoding="utf-8")))
            if not ok:
                print(f"  ❌ {os.path.basename(p):26} {'; '.join(bad[:3])}")
        print("사운드 검사 끝")
        sys.exit(0)
    if "--manifest" in sys.argv:
        args = [x for x in sys.argv[1:] if not x.startswith("--")]
        s = json.load(open(args[0], encoding="utf-8"))
        rows = s.get("bgm", {}).get("music_scenes") or manifest(s)
        L = [f"# 음악·효과음 장면 목록 — {s['meta'].get('title','')}", "",
             f"총 {len(rows)}자리", "", "| 자리 | 이름 | 언제 | 종류 | 프롬프트 |",
             "|---|---|---|---|---|"]
        for r in rows:
            L.append(f"| `{r['slot']}` | {r['name']} | {r['when']} | {r['kind']} | {r['prompt_en'][:70]} |")
        out = f"음악장면_{os.path.basename(args[0]).replace('.json','')}.md"
        open(out, "w", encoding="utf-8").write("\n".join(L))
        print(f"  {out}  {len(rows)}자리")
        sys.exit(0)
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        n = apply(s)
        json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  {os.path.basename(p):26} 음악 자리 {n}개")
