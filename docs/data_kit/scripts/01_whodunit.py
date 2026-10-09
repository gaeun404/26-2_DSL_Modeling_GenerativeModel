"""
WhoDunIt 다운로드 + 가공.
- whodunit_raw.jsonl      : 전체 원본 덤프
- whodunit_originals.jsonl: 이름 미치환 '원본' 사건만, 짧은 순
- multisuspect_cases.json : (extract 이후 단계용 placeholder는 별도)
실행: python scripts/01_whodunit.py
"""
import json, ast, os
from datasets import load_dataset

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "01_whodunit")
os.makedirs(OUT, exist_ok=True)

data = load_dataset("kjgpta/WhoDunIt")["train"].to_list()

# 전체 raw
with open(os.path.join(OUT, "whodunit_raw.jsonl"), "w", encoding="utf-8") as f:
    for r in data:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

def is_original(r):
    m = r.get("metadata")
    if m is None:
        return True
    if isinstance(m, str):
        try:
            m = ast.literal_eval(m)
        except Exception:
            return True
    return not isinstance(m, dict)

orig = sorted([r for r in data if is_original(r)], key=lambda r: len(r["text"]))
with open(os.path.join(OUT, "whodunit_originals.jsonl"), "w", encoding="utf-8") as f:
    for r in orig:
        f.write(json.dumps({
            "title": r["title"],
            "culprit_ids": r["culprit_ids"],
            "char_len": len(r["text"]),
            "text": r["text"],
        }, ensure_ascii=False) + "\n")

print(f"전체 {len(data)}건 / 원본 {len(orig)}건 저장 -> data/01_whodunit/")
for r in orig[:5]:
    print(f'{len(r["text"]):>7}자 | {r["title"][:40]} | {r["culprit_ids"]}')
