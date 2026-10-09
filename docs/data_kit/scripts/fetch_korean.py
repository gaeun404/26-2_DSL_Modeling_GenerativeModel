"""
한국 고전 설화/소설 수집 (위키문헌 API) — v2
개선점:
  - 429 방지: 요청 간 딜레이 + 지수 백오프 재시도
  - '장 목록 페이지'는 하위 페이지(제목/1, 제목/2 ...)를 긁어 이어붙임
  - 제목 목록 확장
실행: python3 scripts/fetch_korean.py
결과: data/16_korean_classics/*.txt  (+ index.json)
"""
import os, json, time, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "16_korean_classics")
os.makedirs(OUT, exist_ok=True)
API = "https://ko.wikisource.org/w/api.php"
UA = {"User-Agent": "mm-research/1.0 (contact: research)"}
DELAY = 1.2          # 요청 간 기본 텀(초)
MAXRETRY = 5

TITLES = [
    "춘향전", "심청전", "흥부전", "홍길동전", "별주부전",
    "콩쥐팥쥐", "장화홍련전", "전우치전", "박씨전", "사씨남정기",
    "구운몽", "금방울전", "숙향전", "운영전", "허생전",
    "양반전", "호질", "옹고집전", "배비장전", "토끼전",
    "심청전(경판본)", "춘향전(완판본)", "홍길동전(경판본)",
    "임경업전", "유충렬전", "조웅전", "심생전", "이춘풍전",
]

def api_get(params):
    """429/일시오류 시 백오프 재시도."""
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(MAXRETRY):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = DELAY * (2 ** i)
                print(f"    429 -> {wait:.1f}s 대기 후 재시도")
                time.sleep(wait); continue
            raise
        except Exception:
            time.sleep(DELAY); continue
    return None

def wikitext(title):
    d = api_get({"action": "parse", "page": title, "prop": "wikitext",
                 "format": "json", "formatversion": "2"})
    time.sleep(DELAY)
    if not d or "error" in d:
        return None
    return (d.get("parse", {}) or {}).get("wikitext")

def subpages(title):
    """제목/ 로 시작하는 하위 페이지 목록."""
    d = api_get({"action": "query", "list": "allpages",
                 "apprefix": title + "/", "apnamespace": "0",
                 "aplimit": "max", "format": "json", "formatversion": "2"})
    time.sleep(DELAY)
    if not d:
        return []
    pages = (d.get("query", {}) or {}).get("allpages", []) or []
    def keyf(p):  # 숫자 순 정렬
        s = p["title"].split("/")[-1]
        return (0, int(s)) if s.isdigit() else (1, s)
    return [p["title"] for p in sorted(pages, key=keyf)]

def collect(title):
    main = wikitext(title) or ""
    subs = subpages(title)
    parts = [main] if len(main) > 50 else []
    for sp in subs:
        wt = wikitext(sp)
        if wt and len(wt) > 50:
            parts.append(f"\n\n=== {sp} ===\n{wt}")
    return "\n".join(parts), len(subs)

index = []
for t in TITLES:
    try:
        text, nsub = collect(t)
        if len(text) < 800:
            print(f"SKIP {t} (본문 부족: {len(text)}자, 하위 {nsub}개)")
            continue
        fn = t.replace("/", "_") + ".txt"
        open(os.path.join(OUT, fn), "w", encoding="utf-8").write(text)
        index.append({"title": t, "file": fn, "char_len": len(text), "subpages": nsub})
        print(f"OK   {t}  ({len(text)//1000}K자, 하위 {nsub}개)")
    except Exception as e:
        print(f"SKIP {t}: {type(e).__name__}: {str(e)[:80]}")

json.dump(index, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"\n완료: {len(index)}편 -> data/16_korean_classics/")
