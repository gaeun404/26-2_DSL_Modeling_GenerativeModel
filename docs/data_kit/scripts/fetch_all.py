"""
후보 데이터셋 전부 일괄 수집 (네 Mac에서 실행).
- HuggingFace: snapshot_download 로 '원시 파일 통째로' -> 스키마 조립 실패 없음
- GitHub: git clone (데이터 gated면 코드/README만)
- 없는 repo는 조용히 SKIP, 마지막에 요약 출력

준비: pip3 install datasets huggingface_hub
실행: python3 scripts/fetch_all.py
"""
import os, subprocess, traceback

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(BASE, exist_ok=True)
ok, skip = [], []

# ---------- HuggingFace (dataset repo 원시 파일) ----------
HF = [
    # (폴더, repo_id)                                   # 용도
    ("01_whodunit_full", "kjgpta/WhoDunIt"),            # 핵심(원시 전체)
    ("06_detectiveqa",   "Phospheneser/DetectiveQA"),  # 장편 추리 QA
    ("07_musr_hf",       "TAUR-Lab/MuSR"),              # 합성 살인미스터리
    ("09_rolebench",     "ZenMoore/RoleBench"),         # 캐릭터 페르소나
    ("10_dailydialog",   "roskoN/dailydialog"),         # 대화 말투(parquet판)
    ("13_fairy_tales_hf","vicclab/fairy_tales"),        # 그림/안데르센류
    ("14_true_detective_hf","TartuNLP/true_detective"), # 5분 미스터리(HF판)
    ("15_musr_murder_only","TAUR-Lab/MuSR"),            # (중복 허용, 무시 가능)
]

def hf_snapshot(folder, repo):
    from huggingface_hub import snapshot_download
    out = os.path.join(BASE, folder)
    snapshot_download(repo, repo_type="dataset", local_dir=out)
    return out

for folder, repo in HF:
    print(f"\n=== HF {repo} -> data/{folder} ===")
    try:
        hf_snapshot(folder, repo)
        ok.append(f"HF  {repo}")
        print("    OK")
    except Exception as e:
        skip.append(f"HF  {repo}  ({type(e).__name__})")
        print(f"    SKIP: {type(e).__name__}: {str(e)[:160]}")

# ---------- GitHub ----------
GH = [
    ("02_fairytaleqa",   "https://github.com/uci-soe/FairytaleQAData.git"),
    ("03_musr",          "https://github.com/Zayne-sprague/MuSR.git"),
    ("04_true_detective","https://github.com/TartuNLP/true-detective.git"),
    ("05_player",        "https://github.com/alickzhu/PLAYER.git"),
    ("11_thinkthrice",   "https://github.com/jackwu502/ThinkThrice.git"),  # 데이터 gated
]

for folder, url in GH:
    dest = os.path.join(BASE, folder)
    print(f"\n=== GIT {url} -> data/{folder} ===")
    if os.path.isdir(dest):
        print("    이미 있음, skip"); ok.append(f"GIT {folder} (기존)"); continue
    try:
        subprocess.run(["git", "clone", "--depth", "1", url, dest], check=True)
        g = os.path.join(dest, ".git")
        if os.path.isdir(g):
            subprocess.run(["rm", "-rf", g])
        ok.append(f"GIT {url}")
        print("    OK")
    except Exception as e:
        skip.append(f"GIT {url}  ({type(e).__name__})")
        print(f"    SKIP: {e}")

# ---------- 요약 ----------
print("\n" + "="*50)
print("성공:")
for x in ok:   print("  +", x)
print("건너뜀:")
for x in skip: print("  -", x)
print("="*50)
print("""
수동으로 받아야 하는 것(스크립트 불가):
  - Murder Accountability Project (실제 살인 통계 CSV): murderdata.org
  - 한국 고전(춘향전/심청전/홍길동전): ko.wikisource.org
  - 한국구비문학대계: gubi.aks.ac.kr
  - Wikipedia 역사사건 덤프: dumps.wikimedia.org
  - ThinkThrice/Jubensha '데이터': repo README의 Google Form 신청
""")
