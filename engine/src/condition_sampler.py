"""
조건 샘플러 — 우리가 모은 데이터를 생성 프롬프트의 '조건'으로 주입.
  - 코난: 트릭·동기 패턴 1개
  - SHR(MAP): 현실 동기·흉기·관계 1개
  - 원작: 원문 발췌(한국고전/동화/Gutenberg)
데이터 폴더 이름이 번호("23_conan_cases")든 한글("[트릭사전]코난...")이든 찾도록 glob 매칭.
데이터가 없으면 그 조건만 건너뜀(생성은 계속).

DATA_DIR 지정: 환경변수 MM_DATA 또는 기본 ../mm_kit/data
"""
import os, glob, json, csv, random, re

DATA_DIR = os.environ.get("MM_DATA", os.path.join(os.path.dirname(__file__), "..", "mm_kit", "data"))

def _find_dir(keyword):
    for d in glob.glob(os.path.join(DATA_DIR, "*")):
        if os.path.isdir(d) and keyword.lower() in os.path.basename(d).lower():
            return d
    return None

def sample_conan():
    d = _find_dir("conan")
    if not d: return None
    for name in ("conan_cases_full.jsonl", "conan_cases.jsonl"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            rows = [json.loads(l) for l in open(p, encoding="utf-8")]
            random.shuffle(rows)
            for r in rows:
                info = r.get("infobox", r)  # full판은 infobox, 기본판은 flat
                trick = info.get("trick") or ""
                motive = info.get("motive") or ""
                if trick or motive:
                    return {"trick": trick[:120], "motive": motive[:120]}
    return None

def sample_shr(max_scan=200000):
    d = _find_dir("murder_account") or _find_dir("현실분포") or _find_dir("MAP")
    if not d: return None
    csvs = glob.glob(os.path.join(d, "*.csv"))
    if not csvs: return None
    # 리저버 샘플링으로 무작위 1행 (대용량 대비)
    pick, n = None, 0
    with open(csvs[0], encoding="latin-1", errors="ignore") as f:
        r = csv.DictReader(f)
        for row in r:
            n += 1
            if random.randint(1, n) == 1:
                pick = row
            if n >= max_scan: break
    if not pick: return None
    return {"circumstance": pick.get("Circumstance",""),
            "weapon": pick.get("Weapon",""),
            "relationship": pick.get("Relationship","")}

def sample_origin(origin):
    """원작명이 든 파일에서 앞부분 발췌."""
    for key in ("korean", "고전", "fairytale", "gutenberg", "동화", "배경"):
        d = _find_dir(key)
        if not d: continue
        for p in glob.glob(os.path.join(d, "**", "*.txt"), recursive=True):
            base = os.path.basename(p)
            if origin[:2] in base or origin in base:
                txt = open(p, encoding="utf-8", errors="ignore").read()
                txt = re.sub(r"\s+", " ", txt)
                return txt[:800]
    return None

def sample_trick():
    """트릭 뱅크에서 중심 트릭 하나. MM_FORCE_TRICK(id)로 강제 지정 가능(배치 커버리지용)."""
    p = os.path.join(os.path.dirname(__file__), "trick_bank.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    tricks = d if isinstance(d, list) else d.get("tricks", [])
    if not tricks:
        return None
    force = os.environ.get("MM_FORCE_TRICK")
    if force:
        for t in tricks:
            if t.get("id") == force or t.get("name") == force:
                return t
    return random.choice(tricks)

def build_conditions(origin):
    """생성 프롬프트에 붙일 조건 텍스트."""
    parts = []
    tk = sample_trick()
    if tk:
        parts.append(f"- ★중심 트릭: '{tk.get('name','')}' ({tk.get('cat','')}) — {tk.get('desc','')}\n  구현: {tk.get('how','')}\n  → 이 사건은 반드시 이 트릭을 축으로 설계할 것.")
    c = sample_conan()
    if c and (c["trick"] or c["motive"]):
        parts.append(f"- 참고 트릭/동기 패턴(코난): 트릭='{c['trick']}', 동기='{c['motive']}' → 이 결을 참고해 새 사건을 구성(그대로 베끼지 말 것)")
    s = sample_shr()
    if s and (s["circumstance"] or s["weapon"]):
        parts.append(f"- 현실 분포(실제 살인통계): 정황='{s['circumstance']}', 흉기='{s['weapon']}', 관계='{s['relationship']}' → 동기·흉기·관계의 현실감 참고")
    o = sample_origin(origin)
    if o:
        parts.append(f"- 원작 원문 발췌: \"{o}\" → 인물·배경을 이 원문에 충실하게")
    hint = os.environ.get("MM_CULPRIT_HINT")  # 예: "C3" — 범인 위치 편중 방지(배치 커버리지용)
    if hint:
        parts.append(f"- ★이번 사건의 범인은 용의자 {hint} 자리(다섯 중 {hint[-1]}번째로 소개되는 인물)로 설정하라. 겉으론 가장 의심 덜 가는 인물이 범인이면 좋다.")
    if not parts:
        return ""
    return "[생성 조건 — 아래 재료를 반영하되 표절 금지]\n" + "\n".join(parts)

if __name__ == "__main__":
    import sys
    origin = sys.argv[1] if len(sys.argv) > 1 else "심청전"
    print(f"DATA_DIR = {DATA_DIR}")
    print("conan :", sample_conan())
    print("shr   :", sample_shr())
    print("origin:", (sample_origin(origin) or "")[:120])
    print("\n--- 조건 블록 ---\n" + (build_conditions(origin) or "(조건 없음: 데이터 폴더 확인)"))
