# -*- coding: utf-8 -*-
"""
cluemedia.py — 단서의 **매체 다변화** + **그림용 구체 묘사(render)** 주입.

피드백(찬열이형, 8/24)
  ② "단서들이 검안서, 신물 등등 새로운 매체를 통해서가 아님"
     → '물건 176 / 증언 151 / 탐색 61'로 뭉뚱그려져 있던 매체를,
       단서 내용에서 실제 매체를 읽어 **검안서·서찰·장부·신물·목격담·소문·흔적…**으로 되배정.
       한 편 안에서 같은 매체가 절반을 넘지 않게 검사한다.
  ③ "각 단서들도 생성모델로 그려야 해서 구체적인 묘사가 필요함"
     → 단서마다 render = {frame(매체 프레임), shot(무엇을 클로즈업), style} 을 붙인다.
       이미지 생성 프롬프트로 바로 쓸 수 있는 한국어 묘사문이다.
       ui.art_specs.rows 에도 '단서 그림 N장' 행을 추가한다.

사용:
    python cluemedia.py            # 전 편 적용(제자리 수정)
    python cluemedia.py --check    # 분포 검사만
    python cluemedia.py out/45_aladdin.json   # 한 편만
"""
import json, glob, re, sys, collections

# 매체 정규명 → (그림 프레임, 클로즈업 지시)
FRAMES = {
    "검안서": ("낡은 종이에 붓글씨로 적힌 검안 문서, 관인이 찍혀 있고 모서리가 해졌다",
              "사인 대목에 먹줄이 그어진 부분을 비스듬히 클로즈업"),
    "서찰":   ("접힌 자국이 깊은 손편지, 급히 쓴 글씨와 번진 먹",
              "결정적인 한 줄이 보일 듯 말 듯한 각도로, 촛불 그림자와 함께"),
    "장부":   ("가죽끈으로 묶인 장부가 펼쳐져 있고 숫자 행렬이 빼곡하다",
              "고쳐 쓴 흔적·이중으로 적힌 칸을 손가락이 짚고 있는 클로즈업"),
    "신물":   ("천에 싸여 있던 개인의 정표 — 손때가 묻어 윤이 난다",
              "탁자 위에 놓인 물건 하나를 정면 클로즈업, 배경은 어둡게"),
    "유품":   ("죽은 이가 남긴 물건, 주인 잃은 티가 나게 놓여 있다",
              "물건의 상한 부분·새겨진 글자를 클로즈업"),
    "목격담": ("증언하는 인물의 상반신 — 말하기를 머뭇거리는 표정",
              "인물 뒤로 그가 봤다는 장면이 흐릿한 회상풍으로 겹쳐진다"),
    "소문":   ("골목 어귀에서 수군거리는 두어 사람의 실루엣",
              "입을 가린 손과 곁눈질, 대상 인물의 뒷모습이 멀리 보인다"),
    "흔적":   ("사건 현장에 남은 자국 — 바닥·문틀·기물에 남은 흔적",
              "흔적 부분을 등불이 비추는 사선 클로즈업, 눈금자나 손가락으로 크기 대비"),
    "현장":   ("사건 현장의 한 지점, 수사하는 시선의 높이",
              "단서가 되는 지점에 빛이 모이고 주변은 어둡게"),
    "물증":   ("증거로 거둬 온 물건이 흰 천 위에 놓여 있다",
              "물건의 특징 부위(날·매듭·얼룩·문양)를 클로즈업"),
    "문서":   ("공적인 기록 문서 — 관청 서식이나 계약 문서",
              "서명·수결·날짜 부분을 클로즈업"),
    "유서":   ("마지막으로 남긴 글 — 글씨가 흔들리다 끊긴다",
              "끊긴 마지막 글자와 떨어진 붓 자국을 클로즈업"),
    "그림":   ("사건과 얽힌 그림·초상 — 화폭 귀퉁이에 단서가 있다",
              "화폭의 세부 한 곳을 클로즈업, 나머지는 그늘"),
}
_ALIAS = {
    "검안": "검안서", "검험": "검안서", "검험서": "검안서", "검안·증언": "검안서",
    "부검": "검안서", "감정서": "검안서", "감식": "검안서", "옛 검험 대조": "검안서",
    "편지": "서찰", "쪽지": "서찰",
    "기록": "문서", "현장기록": "문서", "디지털포렌식": "문서",
    "현장물건": "물증", "물건": "물증", "탐색": "물증", "현장탐색": "현장",
    "증언": "목격담", "정황": "목격담",
}
# 내용으로 매체를 읽는 실마리(위→아래 순서로 먼저 맞은 것)
_HINTS = [
    ("검안서", r"검안|검험|사인은|시신|주검|목졸린|독의|중독|자상|찔린|익사|질식"),
    ("유서",   r"유서|마지막으로 남긴|절명"),
    ("서찰",   r"서찰|편지|쪽지|글월|연서|밀서"),
    ("장부",   r"장부|셈|치부책|출납|금전|빚|차용"),
    ("문서",   r"문서|계약|수결|관인|명부|방명록|목간|호적|송장|순찰패"),
    ("신물",   r"노리개|가락지|반지|비녀|옥패|정표|신물|귀걸이|단추|매듭|부적"),
    ("유품",   r"유품|남긴 물건|주인 잃은"),
    ("소문",   r"소문|수군|말이 돈|도는 말|쑥덕"),
    ("목격담", r"의 말[:：]|증언|같은 말을|목격|마주쳤|^[가-힣A-Za-z·\s]{2,14}[:：]\s*['\"“‘]"),
    ("흔적",   r"자국|흔적|발자국|긁힌|얼룩|핏방울|재[가 ]|그을|눌린"),
    ("현장",   r"【현장】|현장의|시신 곁|머리맡"),
]

def _norm(m):
    return _ALIAS.get(m, m if m in FRAMES else None)

def _read_medium(c):
    cur = _norm(c.get("medium", "") or "")
    surf = c.get("surface", "")
    for name, pat in _HINTS:
        if re.search(pat, surf):
            # 내용이 더 구체적인 매체를 말하면 그걸 따른다(물증/목격담 같은 범용은 내용 우선)
            if cur in (None, "물증", "목격담", "현장") or cur == name:
                return name
            return cur
    return cur or "물증"

_SPEAKER_RE = re.compile(r"^([가-힣A-Za-z]{1,6}(?:\s[가-힣A-Za-z]{1,6}){0,2}?)의 (?:말|증언)[:：]")
_SCRIPT_STRIP = re.compile(r"^.{0,24}?(?:의 말|의 증언|도는 말|말이 하나같다|증언과 그가 주운 것)[:：]?\s*")

def _presentation(c, cast_names):
    """전달 방식 — 피드백(8/24):
    · 사람이 말해 주는 단서는 그 사람이 '직접 나와서' 말한다(spoken + speaker)
    · 글로만 되는 장소 단서는 장소 클릭 → '이 장소의 단서 보기'(place_panel)
    · 나머지는 그림 카드(illustrated)"""
    m, surf = c.get("medium"), c.get("surface", "")
    if m in ("목격담", "소문"):
        sp = _SPEAKER_RE.search(surf)
        name = sp.group(1) if sp else None
        if not name:
            pre = re.match(r"^([가-힣A-Za-z·\s]{2,14}?)[:：]\s*['\"“‘]", surf)
            if pre:
                name = pre.group(1).strip()
        if name in cast_names:
            kind = "cast"
        elif name:
            kind = "npc"
        else:
            name, kind = ("골목 사람들" if m == "소문" else "이름 없는 목격자"), "npc"
        # 대사화: "X의 말: '...'" → X가 직접 말하는 1인칭 대사
        script = _SCRIPT_STRIP.sub("", surf).strip().strip("'\"“”‘’")
        return {"mode": "spoken", "speaker": name, "speaker_kind": kind,
                "script": script,
                "stage": "화자가 화면에 등장해 초상·음성과 함께 직접 말한다. 텍스트 카드로 대체하지 않는다."}
    if c.get("location"):
        return {"mode": "place_panel",
                "stage": "지도에서 그 장소를 누르면 '이 장소의 단서 보기' 버튼이 뜨고, 누르면 이 단서가 나온다."}
    return {"mode": "illustrated", "stage": "단서 그림 카드(render)로 보여 준다."}


def _shot(surface):
    """surface에서 그림에 담을 핵심을 한 줄로 추린다."""
    s = re.sub(r"【[^】]*】", "", surface)
    s = re.sub(r"^[^:：]{2,12}의 (말|증언)[:：]\s*", "", s).strip()
    s = s.strip("'\"“”‘’ ")
    # 첫 두 문장까지만
    parts = re.split(r"(?<=[.?!—])\s+", s)
    return " ".join(parts[:2])[:120]

def enrich(path, check=False):
    s = json.load(open(path, encoding="utf-8"))
    era = s["background"]["setting_raw"].get("era", "")
    pal = (s.get("adapted_story") or {}).get("palette", "") or (s.get("adapted") or {}).get("palette", "")
    cast_names = {c["name"] for c in s["cast"]}
    cnt = collections.Counter()
    for c in s["clue_graph"]:
        m = _read_medium(c)
        cnt[m] += 1
        if check:
            continue
        c["medium"] = m
        c["presentation"] = _presentation(c, cast_names)
        fr, cam = FRAMES[m]
        c["render"] = {
            "frame": fr, "shot": _shot(c.get("surface", "")), "camera": cam,
            "style": f"{era} 배경의 추리 게임 단서 일러스트, 1045×600, 극적인 명암",
            "spoiler_ban": "범인을 특정하는 얼굴·이름·복식은 그리지 않는다" if not c.get("decisive") else "결정타 — 공개 라운드 전 노출 금지",
        }
    n = len(s["clue_graph"])
    top = cnt.most_common(1)[0]
    warn = f"  ⚠ 매체 쏠림: {top[0]} {top[1]}/{n}" if top[1] > n // 2 else ""
    if not check:
        rows = s["ui"]["art_specs"]["rows"]
        rows[:] = [r for r in rows if r.get("kind") != "단서 그림"]
        rows.append({"kind": "단서 그림", "n": n, "w": 1045, "h": 600,
                     "where": "단서 카드마다 한 장 — clue_graph[*].render가 프롬프트",
                     "note": "매체 프레임(검안서/서찰/장부/신물/목격담…)대로 그린다"})
        s["ui"]["art_specs"]["total"] = sum(r["n"] for r in rows)
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    kinds = ", ".join(f"{k}{v}" for k, v in cnt.most_common())
    print(f"  {path.split('/')[-1][:28]:30s} 매체 {len(cnt)}종: {kinds}{warn}")
    return cnt

if __name__ == "__main__":
    check = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    tot = collections.Counter()
    for f in files:
        tot += enrich(f, check)
    print(f"\n전체 매체 분포: {dict(tot.most_common())}")
