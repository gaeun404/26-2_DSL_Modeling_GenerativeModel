# -*- coding: utf-8 -*-
"""
extract_structure.py — 모아 둔 사건 자료에서 **뼈대만** 뽑아 학습용 표로 만든다.

왜 이렇게 하나
  ① 목표에 더 맞다.
     variety.py로 재 보니 지금 23편은 트릭 21종·흉기 12종으로 이야기는 다양한데
     **판의 뼈대가 판박이**다 — 23편 모두 5인·3라운드·장소 6·교차단서 5.
     대본 문장을 더 넣는다고 라운드 수가 달라지지 않는다. 필요한 건 **구조의 폭**이다.

  ② 위험이 낮다.
     저작권은 '표현'을 보호하지 '구조·아이디어'를 보호하지 않는다.
     "밀실 + 소실되는 흉기 + 상속 동기 + 용의자 6인 + 4라운드"는 사실의 기술이다.
     대본 문장은 그 자체가 보호 대상이다. 그래서 **문장은 버리고 뼈대만 남긴다.**

무엇을 뽑나 (원문은 한 글자도 저장하지 않는다)
  trick_class      밀실 / 알리바이위조 / 오인 / 흉기소실 / 다잉메시지 / 이중사건 …
  motive_class     원한 / 치정 / 재물 / 은폐 / 복수 / 우발 …
  weapon_class     자상 / 둔기 / 독 / 교살 / 익사 / 추락 …
  relation_class   가족 / 고용 / 연인 / 이웃 / 낯선 이 …
  cast_n rounds places clue_n channel_mix cross_n narrow_shape
  twist_kind       반전의 종류(피해자 오인 / 공범 / 시간 착오 / 자작극 …)

내놓는 것
  structure_bank.jsonl   한 줄에 사건 하나의 뼈대. **문장 없음.**
  structure_report.md    어느 축이 어떻게 퍼져 있는지

쓰는 법
  export MM_DATA=/경로/mm_kit/data
  python extract_structure.py                 # 자료에서 뽑기
  python extract_structure.py --from-out      # 우리 23편에서도 같은 형식으로 뽑기
  python extract_structure.py --check         # 뽑은 표에 원문이 섞였는지 검사
"""
import json, glob, sys, os, re, csv, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")
DATA = os.environ.get("MM_DATA", os.path.join("..", "mm_kit", "data"))
BANK = "structure_bank.jsonl"

# ── 분류표 — 자유 문장을 **몇 갈래로** 접는다 ─────────────────────────
TRICK = [
    ("밀실", ["밀실", "잠긴", "안에서 잠", "locked", "닫힌 방"]),
    ("알리바이위조", ["알리바이", "시계", "녹음", "전화", "휴대폰", "대역", "시간 조작"]),
    ("오인", ["오인", "착각", "바꿔치기", "1인 2역", "변장", "쌍둥이", "misident"]),
    ("흉기소실", ["녹는", "얼음", "사라진 흉기", "소실", "먹어", "태워"]),
    ("다잉메시지", ["다잉", "메시지", "유서", "남긴 글", "dying"]),
    ("사고위장", ["사고", "자살", "추락", "익사", "위장", "staged"]),
    ("숨은공간", ["통로", "비밀", "지하", "숨은", "이중벽", "hidden"]),
    ("독", ["독", "약", "poison", "중독"]),
    ("공범", ["공범", "협력", "둘이", "짜고"]),
    ("원격", ["원격", "장치", "덫", "타이머", "자동"]),
]
MOTIVE = [
    ("재물", ["재물", "돈", "유산", "상속", "빚", "횡령", "보험", "지분"]),
    ("복수", ["복수", "원수", "앙갚음", "한", "보복"]),
    ("치정", ["치정", "연인", "불륜", "질투", "사랑", "삼각"]),
    ("은폐", ["은폐", "입막음", "발각", "폭로", "약점", "협박"]),
    ("명예", ["명예", "체면", "지위", "자리", "승진", "평판"]),
    ("우발", ["우발", "홧김", "다툼", "말다툼", "몸싸움"]),
]
WEAPON = [("자상", ["자상", "칼", "단검", "찔"]), ("둔기", ["둔기", "때려", "가격", "내리"]),
          ("독", ["독", "약물", "중독"]), ("교살", ["교살", "목", "끈", "졸"]),
          ("익사", ["익사", "물", "연못", "빠"]), ("추락", ["추락", "떨어", "밀"]),
          ("화재", ["불", "화재", "태"])]
RELATION = [("가족", ["가족", "아버지", "어머니", "형", "동생", "아들", "딸", "부부", "숙부", "조카"]),
            ("고용", ["고용", "주인", "하인", "집사", "마름", "직원", "상사", "부하"]),
            ("연인", ["연인", "애인", "약혼", "부인", "남편"]),
            ("이웃", ["이웃", "동네", "마을", "동무", "친구"]),
            ("낯선이", ["낯선", "손님", "떠돌", "나그네", "외부"])]
# 다잉메시지 — '무엇으로 남겼나'가 갈래다. 문장이 아니라 방식을 뽑는다.
DYING = [
    ("글자일부", ["글자", "쓰다 만", "적다 만", "획", "이름 일부", "피로 쓴"]),
    ("물건배치", ["놓아", "가리키", "쥐고", "손에", "배치", "돌려놓"]),
    ("몸짓방향", ["손가락", "가리킨", "고개", "몸이 향", "발끝"]),
    ("암호상징", ["암호", "기호", "상징", "숫자", "꽃말", "카드"]),
    ("훼손된것", ["지워", "찢", "태워", "덮여", "누군가 손"]),
]
# 단서 유형 — 어떤 통로로 알게 되는가
CLUE_KIND = [
    ("검안", ["검안", "검험", "상처", "사인", "시반", "부검"]),
    ("목격증언", ["봤", "보았", "목격", "증언", "들었"]),
    ("물증", ["발견", "떨어진", "남은", "묻은", "조각", "자국"]),
    ("기록문서", ["장부", "문서", "편지", "명부", "계약", "일지", "기록"]),
    ("알리바이반증", ["오지 않", "없었", "그 시각", "자리를 비", "보지 못"]),
    ("현장구조", ["잠긴", "통로", "창", "문", "구조", "배치"]),
]
# 중반 이벤트 — 판을 어떻게 흔드는가
EVENT_KIND = [
    ("새증언", ["증언", "입을 열", "입을 연", "입에서", "말한다", "털어놓", "한마디"]),
    ("두번째사건", ["또 죽", "두 번째", "추가 피해", "쓰러진", "습격"]),
    ("증거소실", ["사라진", "불탄", "없어진", "훼손", "지워진", "타 버린"]),
    ("인물이탈", ["달아", "도망", "사라졌", "떠났"]),
    ("시간압박", ["시간", "새벽", "떠나야", "곧", "촉박"]),
    ("외부개입", ["관에서", "포졸", "손님", "찾아온", "밖에서"]),
    ("자백번복", ["번복", "말을 바꾸", "아까는", "거짓이었"]),
]
TWIST = [("피해자오인", ["피해자가 다른", "죽은 자가", "오인", "바꿔"]),
         ("자작극", ["자작", "스스로", "꾸민"]),
         ("공범존재", ["공범", "둘", "짜고"]),
         ("시간착오", ["시간", "시각", "알리바이가 무너"]),
         ("은폐자별개", ["옮긴", "치운", "숨긴 사람", "은폐"])]


def _classify(text, table, default="기타"):
    t = (text or "")
    for label, keys in table:
        if any(k in t for k in keys):
            return label
    return default


def from_scenario(s, src="ours"):
    """우리 시나리오에서 뼈대를 뽑는다. 같은 형식이라야 함께 학습할 수 있다."""
    cg = s.get("clue_graph") or []
    cast = s.get("cast") or []
    cul = next((c for c in cast if c.get("is_culprit")), {})
    trick_blob = json.dumps(s.get("trick") or {}, ensure_ascii=False)
    try:
        import flow
        narrow = flow.narrowing(s)
    except Exception:
        narrow = []
    return {
        "source": src,
        "trick_class": _classify(trick_blob, TRICK),
        "motive_class": _classify(cul.get("kill_motive", "") + cul.get("motive_label", ""), MOTIVE),
        "weapon_class": _classify(s.get("death", {}).get("weapon_class", ""), WEAPON),
        "relation_class": _classify((cul.get("profile") or {}).get("relation", "")
                                    + cul.get("public", ""), RELATION),
        "twist_kind": _classify(json.dumps(s.get("solution") or {}, ensure_ascii=False), TWIST),
        "cast_n": len(cast),
        "rounds": s.get("config", {}).get("rounds", 3),
        "places": len(s.get("map", {}).get("places") or []),
        "clue_n": len(cg),
        "channel_mix": sorted({c.get("channel") for c in cg if c.get("channel")}),
        "cross_n": sum(1 for c in cg if len(c.get("affects") or []) >= 2),
        "narrow_shape": narrow,
        "incidents": len(s.get("incidents") or []) or 1,
        "dying_kind": (_classify(json.dumps(s.get("death") or {}, ensure_ascii=False), DYING, "")
                       or None),
        "clue_kinds": sorted({_classify(c.get("surface", "") + c.get("implies", ""),
                                        CLUE_KIND) for c in cg}),
        # 이벤트에 kind가 적혀 있으면 그걸 쓴다. 낱말로 추측하는 건 없을 때뿐이다.
        "event_kinds": sorted({(e.get("kind")
                                or _classify(e.get("text", "") + e.get("effect", ""), EVENT_KIND))
                               for e in (s.get("events") or [])}) or [],
    }


def from_record(r, src):
    """모아 둔 자료 한 건 → 뼈대. **문장은 저장하지 않는다.**
    자료마다 필드 이름이 달라, 값 전체를 문자열로 합쳐 분류만 한다."""
    blob = json.dumps(r, ensure_ascii=False)
    return {
        "source": src,
        "trick_class": _classify(blob, TRICK),
        "motive_class": _classify(blob, MOTIVE),
        "weapon_class": _classify(blob, WEAPON),
        "relation_class": _classify(blob, RELATION),
        "twist_kind": _classify(blob, TWIST),
        # 자료에 숫자가 있으면 쓰고, 없으면 비운다 — 지어내지 않는다
        "cast_n": r.get("suspects") or r.get("cast_n"),
        "rounds": r.get("rounds"),
        "places": r.get("places"),
        "clue_n": r.get("clues") or r.get("clue_n"),
        "channel_mix": None,
        "cross_n": None,
        "narrow_shape": None,
        "incidents": 1,
        "dying_kind": _classify(blob, DYING, "") or None,
        "clue_kinds": sorted({_classify(blob, CLUE_KIND)}),
        "event_kinds": sorted({_classify(blob, EVENT_KIND)}),
    }


def _read_any(path):
    if path.endswith(".jsonl"):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except Exception:
                    pass
    elif path.endswith(".json"):
        try:
            d = json.load(open(path, encoding="utf-8"))
            for r in (d if isinstance(d, list) else [d]):
                yield r
        except Exception:
            pass
    elif path.endswith(".csv"):
        for r in csv.DictReader(open(path, encoding="utf-8")):
            yield r


def harvest():
    rows = []
    if not os.path.isdir(DATA):
        print(f"  자료 폴더가 없습니다: {DATA}  (MM_DATA로 지정하세요)")
        return rows
    for path in glob.glob(os.path.join(DATA, "**", "*.*"), recursive=True):
        if not path.endswith((".jsonl", ".json", ".csv")):
            continue
        src = os.path.basename(os.path.dirname(path))
        n = 0
        for r in _read_any(path):
            if isinstance(r, dict):
                rows.append(from_record(r, src))
                n += 1
        if n:
            print(f"  {os.path.basename(path):40} {n}건")
    return rows


# ── 원문이 섞이지 않았는지 검사 ───────────────────────────────────────
def check(path=BANK):
    """뼈대 표에 **문장이 들어가 있으면** 뽑기가 잘못된 것이다."""
    bad = 0
    ALLOWED = {"source", "trick_class", "motive_class", "weapon_class", "relation_class",
               "twist_kind", "cast_n", "rounds", "places", "clue_n", "channel_mix",
               "cross_n", "narrow_shape", "incidents",
               "dying_kind", "clue_kinds", "event_kinds"}
    for i, line in enumerate(open(path, encoding="utf-8")):
        r = json.loads(line)
        extra = set(r) - ALLOWED
        if extra:
            print(f"  ❌ {i}행: 허용되지 않은 항목 {sorted(extra)}"); bad += 1
        for k, v in r.items():
            if isinstance(v, str) and (len(v) > 24 or re.search(r"[.!?…]", v)):
                print(f"  ❌ {i}행 {k}: 문장이 들어 있다 — {v[:40]}"); bad += 1
    print(f"\n{'✅ 원문 없음 — 뼈대만 담겼습니다' if not bad else f'❌ {bad}건'}")
    return bad == 0


def report(rows):
    L = ["# 뼈대 표", "", f"총 {len(rows)}건", ""]
    for axis in ("trick_class", "motive_class", "weapon_class", "relation_class",
                 "twist_kind", "dying_kind", "cast_n", "rounds", "places"):
        c = collections.Counter(str(r.get(axis)) for r in rows if r.get(axis) is not None)
        if not c:
            continue
        L.append(f"## {axis} — {len(c)}갈래")
        L += [f"- {k} × {v}" for k, v in c.most_common(12)]
        L.append("")
    # 여러 값을 갖는 축은 따로 센다
    for axis in ("clue_kinds", "event_kinds", "channel_mix"):
        c = collections.Counter(v for r in rows for v in (r.get(axis) or []))
        if not c:
            continue
        L.append(f"## {axis} — {len(c)}갈래 (한 편에 여럿)")
        L += [f"- {k} × {v}" for k, v in c.most_common(12)]
        L.append("")
    open("structure_report.md", "w", encoding="utf-8").write("\n".join(L))
    print("\n저장: structure_report.md")


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    rows = []
    if "--from-out" in sys.argv or not os.path.isdir(DATA):
        for p in sorted(glob.glob("scenarios/[0-9]*.json")):
            rows.append(from_scenario(json.load(open(p, encoding="utf-8"))))
        print(f"  우리 시나리오 {len(rows)}편")
    if os.path.isdir(DATA):
        rows += harvest()
    with open(BANK, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n{BANK}  {len(rows)}건")
    report(rows)
    check()
