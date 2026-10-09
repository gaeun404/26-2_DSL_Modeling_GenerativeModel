"""
HuggingFace 데이터셋 일괄 다운로드 (네 Mac에서 실행 — 클라우드 샌드박스는 HF 차단됨).
준비: pip install datasets
실행: python scripts/fetch_huggingface.py
결과: data/ 아래 각 폴더에 jsonl 저장

일부는 gated(신청 승인 필요)일 수 있음. 실패해도 나머지는 계속 진행.
"""
import os, json, traceback
from datasets import load_dataset

BASE = os.path.join(os.path.dirname(__file__), "..", "data")

# (폴더명, HF repo, config 또는 None)
JOBS = [
    ("01_whodunit",   "kjgpta/WhoDunIt",            None),
    ("06_detectiveqa","Phospheneser/DetectiveQA",   None),
    ("07_musr_hf",    "TAUR-Lab/MuSR",              None),   # object_placements/team_allocation 포함
    ("08_fairytaleqa_hf","WorkInTheDark/FairytaleQA", None),
    ("09_rolebench",  "ZenMoore/RoleBench",         None),   # 캐릭터 페르소나
    ("10_dailydialog","daily_dialog",               None),   # 대화 말투
]

def dump(ds, folder):
    outdir = os.path.join(BASE, folder)
    os.makedirs(outdir, exist_ok=True)
    for split in ds:
        path = os.path.join(outdir, f"{split}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for row in ds[split]:
                f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        print(f"    {split}: {ds[split].num_rows} rows -> {folder}/{split}.jsonl")

for folder, repo, cfg in JOBS:
    print(f"\n=== {repo} -> data/{folder} ===")
    try:
        ds = load_dataset(repo, cfg) if cfg else load_dataset(repo)
        dump(ds, folder)
    except Exception as e:
        print(f"    SKIP ({type(e).__name__}): {e}")
        print("    (gated면 HF 페이지에서 access 요청 후 `huggingface-cli login` 하고 재실행)")

print("\n완료.")
