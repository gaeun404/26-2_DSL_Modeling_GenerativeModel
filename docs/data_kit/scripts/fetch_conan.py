"""
명탐정 코난 '사건 구조'만 수집 (Detective Conan World 위키, MediaWiki API).
- 저작권 원문 대신 인포박스의 사실(fact)만 추출: 피해자/범인/사인/동기/트릭 등
- 결과: data/23_conan_cases/conan_cases.jsonl  (구조 레코드)
실행: python3 scripts/fetch_conan.py

주의: 이건 학습/분석용 '사건 구조' 데이터. 원문 대사/서술은 담지 않는다.
"""
import os, json, re, time, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "23_conan_cases")
os.makedirs(OUT, exist_ok=True)
API = "https://www.detectiveconanworld.com/wiki/api.php"
UA = {"User-Agent": "mm-research/1.0"}
DELAY = 0.6

# 사건 정보가 담긴 페이지 카테고리 후보 (없으면 자동 skip)
CATS = [
    "Category:Cases", "Category:Manga Cases", "Category:Anime Cases",
    "Category:Episodes", "Category:Movies",
]

def api(params):
    params = {**params, "format": "json", "formatversion": "2"}
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(DELAY * (2 ** i)); continue
            return None
        except Exception:
            time.sleep(DELAY); continue
    return None

def list_category(cat):
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "categorymembers",
             "cmtitle": cat, "cmlimit": "500", "cmtype": "page"}
        if cont: p["cmcontinue"] = cont
        d = api(p); time.sleep(DELAY)
        if not d: break
        titles += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        cont = d.get("continue", {}).get("cmcontinue")
        if not cont: break
    return titles

def get_wikitext(title):
    d = api({"action": "parse", "page": title, "prop": "wikitext"})
    time.sleep(DELAY)
    if not d or "error" in d: return None
    return (d.get("parse", {}) or {}).get("wikitext")

# 인포박스 첫 템플릿의 |key = value 쌍을 통째로 추출 (필드명이 뭐든 캡처)
KEYVAL = re.compile(r"\|\s*([A-Za-z0-9 _]+?)\s*=\s*(.+)")
# 우리가 특히 원하는 사건 필드
WANT = ["victim", "culprit", "cause of death", "motive", "case", "location",
        "weapon", "murderer", "victims", "culprits", "trick"]

def clean(v):
    v = re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", r"\2", v)  # [[a|b]]->b
    v = re.sub(r"<[^>]+>", "", v)                           # html
    v = re.sub(r"\{\{[^}]*\}\}", "", v)                     # 남은 템플릿
    v = v.replace("'''", "").replace("''", "").strip(" |")
    return v.strip()

def extract_case(title, wt):
    fields = {}
    for m in KEYVAL.finditer(wt):
        k = m.group(1).strip().lower()
        fields[k] = clean(m.group(2))
    picked = {k: fields[k] for k in fields if k in WANT}
    # 사건성 필드가 하나도 없으면 케이스 아님
    if not any(k in fields for k in ("victim", "culprit", "cause of death",
                                     "motive", "murderer")):
        return None
    return {"title": title, **picked}

# --- 실행 ---
seen, cases = set(), []
all_titles = []
for c in CATS:
    ts = list_category(c)
    print(f"{c}: {len(ts)}개")
    all_titles += ts
all_titles = [t for t in all_titles if t not in seen and not seen.add(t)]
print(f"총 후보 페이지: {len(all_titles)}")

for i, t in enumerate(all_titles):
    wt = get_wikitext(t)
    if not wt: continue
    rec = extract_case(t, wt)
    if rec:
        cases.append(rec)
    if (i + 1) % 25 == 0:
        print(f"  {i+1}/{len(all_titles)} 처리, 케이스 {len(cases)}건")

with open(os.path.join(OUT, "conan_cases.jsonl"), "w", encoding="utf-8") as f:
    for r in cases:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"\n완료: {len(cases)}건 -> data/23_conan_cases/conan_cases.jsonl")
