"""
코난 사건 '전문(시나리오)' 수집 — conan_cases.jsonl 에 매칭해서 확장.
각 사건 페이지에서:
  - 인포박스 사실(피해자/범인/사인/동기 등)  [이미 있던 것]
  - 등장인물(용의자 후보) 목록
  - Plot / Resolution / Deduction 등 섹션 전문
을 뽑아 conan_cases_full.jsonl 로 저장.

*** 연구/패턴학습 전용 ***
- 각 레코드에 source_url / license 표기.
- 이 원문 프로즈를 그대로 재배포하거나, 모델이 그대로 복제하도록 학습시키지 말 것.
  실제 학습은 이걸 우리 스키마로 재작성/합성한 결과물로 한다.

실행: python3 scripts/fetch_conan_full.py
"""
import os, json, re, time, urllib.parse, urllib.request

BASE = os.path.join(os.path.dirname(__file__), "..", "data", "23_conan_cases")
IN   = os.path.join(BASE, "conan_cases.jsonl")
OUT  = os.path.join(BASE, "conan_cases_full.jsonl")
API  = "https://www.detectiveconanworld.com/wiki/api.php"
PAGE = "https://www.detectiveconanworld.com/wiki/"
UA   = {"User-Agent": "mm-research/1.0"}
DELAY = 0.6
LICENSE = "CC-BY-SA (Detective Conan World wiki) / research-use only"

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

def get_wikitext(title):
    d = api({"action": "parse", "page": title, "prop": "wikitext"})
    time.sleep(DELAY)
    if not d or "error" in d: return None
    return (d.get("parse", {}) or {}).get("wikitext")

# ---- 위키 마크업 정리 ----
def strip_markup(t):
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)          # 단순 템플릿
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)          # 중첩 1회 더
    t = re.sub(r"\{\|.*?\|\}", "", t, flags=re.S)  # 표
    t = re.sub(r"\[\[File:[^\]]*\]\]", "", t, flags=re.I)
    t = re.sub(r"\[\[Image:[^\]]*\]\]", "", t, flags=re.I)
    t = re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", r"\2", t)  # [[a|b]]->b
    t = re.sub(r"'''?", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

# ---- 섹션 분해: == Title == 기준 ----
def sections(wt):
    parts = re.split(r"\n==+\s*(.+?)\s*==+\s*\n", "\n" + wt)
    out = {"_intro": parts[0]}
    for i in range(1, len(parts) - 1, 2):
        out[parts[i].strip().lower()] = parts[i + 1]
    return out

# ---- 인포박스 key/val (전편과 동일) ----
KEYVAL = re.compile(r"\|\s*([A-Za-z0-9 _]+?)\s*=\s*(.+)")
WANT = ["victim", "culprit", "cause of death", "motive", "case", "location",
        "weapon", "murderer", "victims", "culprits", "trick"]

def infobox(wt):
    f = {}
    for m in KEYVAL.finditer(wt):
        k = m.group(1).strip().lower()
        if k in WANT:
            f[k] = strip_markup(m.group(2))
    return f

# ---- 등장인물(용의자 후보) 추출: Characters 섹션의 링크들 ----
def characters(secs):
    for key in ("characters", "characters in order of appearance",
                "people", "characters introduced"):
        if key in secs:
            names = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", secs[key])
            names = [n.strip() for n in names if ":" not in n]
            # 중복 제거·상한
            uniq = list(dict.fromkeys(names))
            return uniq[:30]
    return []

# ---- 시나리오 섹션 모으기 ----
SCENE_KEYS = ["plot", "resolution", "deduction", "summary", "explanation",
              "case", "synopsis", "the case", "the resolution"]

def scenario(secs):
    chunks = []
    for k, v in secs.items():
        if any(sk == k or sk in k for sk in SCENE_KEYS):
            txt = strip_markup(v)
            if len(txt) > 80:
                chunks.append(f"## {k.title()}\n{txt}")
    return "\n\n".join(chunks)

# ---- 실행: 기존 케이스 타이틀 기준 ----
titles = []
if os.path.exists(IN):
    for line in open(IN, encoding="utf-8"):
        titles.append(json.loads(line)["title"])
else:
    print("conan_cases.jsonl 이 없음. 먼저 fetch_conan.py 실행."); raise SystemExit

print(f"{len(titles)}건 확장 시작...")
n_ok = 0
with open(OUT, "w", encoding="utf-8") as fout:
    for i, t in enumerate(titles):
        wt = get_wikitext(t)
        if not wt: continue
        secs = sections(wt)
        rec = {
            "title": t,
            "source_url": PAGE + urllib.parse.quote(t.replace(" ", "_")),
            "license": LICENSE,
            "infobox": infobox(wt),
            "suspects_candidates": characters(secs),
            "scenario_text": scenario(secs),
        }
        if rec["scenario_text"] or rec["infobox"]:
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_ok += 1
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(titles)} 처리, 저장 {n_ok}건")

print(f"\n완료: {n_ok}건 -> {OUT}")
print("※ 연구/패턴학습 전용. 원문 재배포·모델의 원문 복제 학습 금지.")
