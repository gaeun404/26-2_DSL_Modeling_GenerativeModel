"""
'사건 케이스' 중심 추가 수집 (네 Mac에서 실행).
- 실제 케이스형 데이터셋을 최대한 더 긁는다.
- 원시 파일째로 받고, 없으면 SKIP.
실행: python3 scripts/fetch_cases.py
"""
import os, subprocess

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
ok, skip = [], []

HF = [
    ("20_mysterywriter",    "theprint/MysteryWriter"),
    ("21_mystery_crime_books","AlekseyKorshuk/mystery-crime-books"),
    # 참고: 이미 받은 케이스형(재수집 원하면 주석 해제)
    # ("01_whodunit_full",  "kjgpta/WhoDunIt"),
    # ("06_detectiveqa",    "Phospheneser/DetectiveQA"),
    # ("07_musr_hf",        "TAUR-Lab/MuSR"),
]
GH = [
    ("22_llm_mysteries", "https://github.com/metareflection/llm-mysteries.git"),
]

def hf(folder, repo):
    from huggingface_hub import snapshot_download
    snapshot_download(repo, repo_type="dataset",
                      local_dir=os.path.join(BASE, folder))

for folder, repo in HF:
    print(f"\n=== HF {repo} -> data/{folder} ===")
    try:
        hf(folder, repo); ok.append("HF  " + repo); print("    OK")
    except Exception as e:
        skip.append(f"HF  {repo} ({type(e).__name__})")
        print(f"    SKIP: {type(e).__name__}: {str(e)[:150]}")

for folder, url in GH:
    dest = os.path.join(BASE, folder)
    print(f"\n=== GIT {url} -> data/{folder} ===")
    if os.path.isdir(dest):
        print("    이미 있음, skip"); ok.append("GIT " + folder + " (기존)"); continue
    try:
        subprocess.run(["git", "clone", "--depth", "1", url, dest], check=True)
        subprocess.run(["rm", "-rf", os.path.join(dest, ".git")])
        ok.append("GIT " + url); print("    OK")
    except Exception as e:
        skip.append(f"GIT {url} ({type(e).__name__})"); print(f"    SKIP: {e}")

print("\n" + "="*50)
print("성공:");  [print("  +", x) for x in ok]
print("건너뜀:"); [print("  -", x) for x in skip]
print("="*50)
print("""
수동/신청:
  - WhodunitBench (NeurIPS'24 극본살인 멀티모달): 논문/OpenReview에서 저장소 링크 확인
  - Jubensha 대량 극본: ThinkThrice README의 Google Form
""")
