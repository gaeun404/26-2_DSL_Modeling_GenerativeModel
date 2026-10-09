"""
현실분포(Murder Accountability Project) + 추가 미스터리 코퍼스(F) 일괄 수집.
- MAP: bctyner/MurderAccountabilityProject GitHub 저장소(데이터 파일 포함)
- F  : theprint/MysteryWriter, AlekseyKorshuk/mystery-crime-books, metareflection/llm-mysteries
실행: python3 scripts/fetch_realism.py
"""
import os, subprocess

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
ok, skip = [], []

# ---- HuggingFace 코퍼스 ----
HF = [
    ("20_mysterywriter",     "theprint/MysteryWriter"),
    ("21_mystery_crime_books","AlekseyKorshuk/mystery-crime-books"),
]
def hf(folder, repo):
    from huggingface_hub import snapshot_download
    snapshot_download(repo, repo_type="dataset",
                      local_dir=os.path.join(BASE, folder))
for folder, repo in HF:
    print(f"\n=== HF {repo} -> data/{folder} ===")
    if os.path.isdir(os.path.join(BASE, folder)):
        print("    이미 있음, skip"); ok.append("HF " + repo + " (기존)"); continue
    try:
        hf(folder, repo); ok.append("HF " + repo); print("    OK")
    except Exception as e:
        skip.append(f"HF {repo} ({type(e).__name__})")
        print(f"    SKIP: {type(e).__name__}: {str(e)[:150]}")

# ---- GitHub (MAP 현실분포 + llm-mysteries) ----
GH = [
    ("17_murder_accountability","https://github.com/bctyner/MurderAccountabilityProject.git"),
    ("22_llm_mysteries",        "https://github.com/metareflection/llm-mysteries.git"),
]
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
MAP 데이터 위치 확인:
  ls -la data/17_murder_accountability
  (CSV/데이터 파일이 있음. SHR = Supplementary Homicide Reports, 1976~ 미국 살인기록.
   동기·흉기·피해자-가해자 관계 컬럼이 생성 동기 리얼리티 참고용)
원본 사이트: murderdata.org (수동 최신본 필요시)
""")
