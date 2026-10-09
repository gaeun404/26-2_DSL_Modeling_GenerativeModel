"""
Project Gutenberg 퍼블릭 도메인 추리/원작 텍스트 몇 편 받기 (네 Mac에서 실행).
클라우드 샌드박스는 gutenberg.org 차단됨 -> 로컬에서 실행.
실행: python scripts/fetch_gutenberg.py
결과: data/12_gutenberg/*.txt
"""
import os, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "12_gutenberg")
os.makedirs(OUT, exist_ok=True)

# (파일명, Gutenberg ebook id)  — 모두 퍼블릭 도메인
BOOKS = {
    "sherlock_adventures.txt": 1661,   # The Adventures of Sherlock Holmes
    "sherlock_memoirs.txt":    834,    # The Memoirs of Sherlock Holmes
    "study_in_scarlet.txt":    244,    # A Study in Scarlet
    "poe_tales.txt":           2148,   # The Works of E.A. Poe (Murders in the Rue Morgue 등)
    "father_brown.txt":        204,    # The Innocence of Father Brown (Chesterton)
    "grimm_fairy_tales.txt":   2591,   # Grimms' Fairy Tales
    "andersen_tales.txt":      1597,   # Andersen's Fairy Tales
}

for name, eid in BOOKS.items():
    url = f"https://www.gutenberg.org/files/{eid}/{eid}-0.txt"
    alt = f"https://www.gutenberg.org/cache/epub/{eid}/pg{eid}.txt"
    for u in (url, alt):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=30).read()
            open(os.path.join(OUT, name), "wb").write(data)
            print(f"OK  {name}  ({len(data)//1024} KB)")
            break
        except Exception as e:
            last = e
    else:
        print(f"FAIL {name}: {last}")

print("완료.")
