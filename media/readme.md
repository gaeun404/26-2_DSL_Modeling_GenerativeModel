# Mystery Assets 생성 파이프라인 — 실행 가이드

학과 서버(Slurm + `/mnt/data1` 공용 스토리지) 기준 사용법.

## 구성

| 타깃 | conda 환경 | 노트북 | 모델 |
|------|-----------|--------|------|
| `sa3` | `sa3` | `bgm_stable_audio.ipynb` | Stable Audio (BGM) |
| `ace` | `ace` | `bgm_ace_step.ipynb` | ACE-Step (BGM) |
| `img` | `img` | `image_hidream.ipynb` | HiDream (이미지) |

입력: `scenarios_en/*.json` (20개 시나리오 — `scenarios/*.json` 원본을
`python3 build_scenario_en.py`로 영어 변환·보강해서 생성. 4개 노트북 모두
`scenarios_en/` 안의 json을 전부 자동으로 읽는다. 상세는 `build_scenario_en.py`
docstring 참고)
출력: `/mnt/data1/$USER/mystery/outputs`

---

## 0. 사전 확인 (최초 1회)

내 계정이 어떤 partition / account / QoS 를 쓸 수 있는지 먼저 확인한다.
`run_assets.sh` 의 `--account=ug`, `--partition=jobs` 가 실제와 다르면 job 이 제출조차 안 된다.

```bash
sacctmgr show assoc tree format=cluster,acct,user,qos,part user=$USER
sinfo -o "%20P %10N %12G %8t %C"
```

`--partition` 은 `sinfo` 의 PARTITION 칼럼, `--account` 는 `sacctmgr` 의 Account 칼럼 값으로 맞춘다.
GPU 종류는 아래로 확인:

```bash
scontrol show node <노드이름> | grep -i gres
```

---

## 1. 환경 설치 (최초 1회)

```bash
cd ~/26-2_Modeling_GenerativeModel/Jaemin
bash setup_envs.sh          # sa3 / ace / img 3개 모두
# 또는 하나만: bash setup_envs.sh img
```

miniforge 는 `/mnt/data1/$USER/miniforge3` 에 설치된다.
설치 후 아래 두 줄을 `~/.bashrc` 에 추가해두면 편하다.

```bash
source /mnt/data1/$USER/miniforge3/etc/profile.d/conda.sh
export HF_HOME=/mnt/data1/$USER/mystery/hf_cache
```

> **`HF_HOME` 은 꼭 설정할 것.** HiDream / Stable Audio / ACE-Step 가중치는 수십 GB라
> 기본값(`~/.cache/huggingface`)으로 받으면 홈 디렉토리 용량이 터진다.

---

## 2. 배치 실행 (기본 방법)

```bash
cd ~/26-2_Modeling_GenerativeModel/Jaemin
bash submit.sh img       # 또는 ace / sa3
```

확인:

```bash
squeue -u $USER
tail -f /mnt/data1/$USER/mystery/logs/mystery_assets_*.out
scancel <JobID>          # 취소
```

`squeue` 의 `NODELIST(REASON)` 칼럼:

| 표시 | 의미 |
|------|------|
| `(Resources)` | 정상. GPU 빌 때까지 대기 중 |
| `(Priority)` | 정상. 우선순위 높은 job 대기 중 |
| `(QOSMax...)` / `(AssocMax...)` | 요청량이 한도 초과 → GPU 수·메모리·시간 줄이기 |
| `(PartitionConfig)` | partition 이름 또는 요청 스펙이 잘못됨 |
| `(InvalidAccount)` | `--account` 값이 잘못됨 |

---

## 3. 노트북을 직접 돌리고 싶을 때 (디버깅용)

**VS Code로 서버에 붙어서 노트북을 그냥 실행하면 로그인 노드에서 돌아 GPU를 못 쓴다.**
반드시 GPU 노드를 잡은 뒤 실행할 것.

```bash
# GPU 노드 인터랙티브 세션
srun -p jobs -A ug --gres=gpu:1 --cpus-per-task=8 --mem=64G -t 2:00:00 --pty bash

# 들어간 뒤 확인
hostname                 # 로그인 노드와 달라야 정상
nvidia-smi

# Jupyter 띄우기
source /mnt/data1/$USER/miniforge3/etc/profile.d/conda.sh
conda activate img
export HF_HOME=/mnt/data1/$USER/mystery/hf_cache
jupyter notebook --no-browser --port=8888 --ip=0.0.0.0
```

내 노트북(맥)에서 새 터미널을 열고 터널을 뚫는다:

```bash
ssh -L 8888:<GPU노드이름>:8888 <내계정>@<서버주소>
```

브라우저에서 `localhost:8888` 접속, 또는 VS Code에서
`Select Kernel → Existing Jupyter Server → http://localhost:8888/?token=...`

---

## 4. 원본 스크립트에서 고친 것들

문제가 있었던 부분과 수정 내용:

| 파일 | 문제 | 수정 |
|------|------|------|
| `setup_envs.sh` | miniforge 를 `/root/miniforge3` 에 설치 시도 → root 권한 없어 실패 | `/mnt/data1/$USER/miniforge3` |
| `setup_envs.sh` | `papermill` 미설치 → `run_assets.sh` 가 실행 불가 | 각 환경에 설치 |
| `setup_envs.sh` | `set -u` 와 conda 스크립트 충돌 가능 | activate 구간에서 `set +u` |
| `run_assets.sh` | `conda activate mystery` — 존재하지 않는 환경 | 타깃별 `sa3`/`ace`/`img` |
| `run_assets.sh` | conda 경로 `/data1/$USER` — setup 결과와 불일치 | `/mnt/data1/$USER` 로 통일 |
| `run_assets.sh` | `${TARGET}_generate.ipynb` — 존재하지 않는 파일명 | 실제 노트북명으로 매핑 |
| `run_assets.sh` | `--output` 디렉토리를 job 시작 후에 생성 → job 이 조용히 죽음 | `submit.sh` 가 제출 전에 생성 |
| `run_assets.sh` | 마지막 `ls` 실패가 `pipefail` 로 job 을 FAILED 처리 | 실패 무시 처리 |
| `readme.md` | 빈 파일 | 이 문서 |

---

## 5. 자주 나는 에러

**`CondaError: Run 'conda init'`**
→ `source /mnt/data1/$USER/miniforge3/etc/profile.d/conda.sh` 를 먼저 실행.

**`torch.cuda.is_available()` 가 `False`**
→ 로그인 노드에서 실행 중이다. `srun --gres=gpu:1 --pty bash` 로 GPU 노드를 잡을 것.

**`No space left on device`**
→ `HF_HOME` 이 홈으로 잡혀 있다. `echo $HF_HOME` 확인 후 `/mnt/data1/$USER/...` 로 변경.
   기존 캐시 정리: `rm -rf ~/.cache/huggingface`

**`CUDA out of memory` (특히 HiDream)**
→ GPU 1장으로 부족하면 `run_assets.sh` 에서 `--gres=gpu:2` 로 늘리거나,
   노트북에서 fp16/bf16 또는 `enable_model_cpu_offload()` 사용.

**job 이 제출되자마자 사라짐 (로그 파일도 없음)**
→ `--output` 경로의 디렉토리가 없는 경우. `submit.sh` 로 제출하면 해결된다.
