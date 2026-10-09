# slurm — hpccluster 에서 노트북 4개 돌리기

계정 `dsl04` / `partition1` / `account=ug` / `qos=normal` 실측 기준으로 맞춰져 있다.
GPU 는 RTX 6000 Ada (49GB, **compute capability 8.9**) 라 FP8 이 되고, FLUX.2 klein 도 돌아간다.

## 순서

```bash
# 0. 저장소를 $HOME(=/data1/$USER) 아래에 두고, 로그인 노드에서
cd ~/26-2_DSL_Modeling_GenerativeModel/media/slurm

# 1. 사전 점검 (아무것도 안 바꾼다). 디스크 170GB 확보가 관건
./probe.sh

# 2. HF 토큰
echo hf_xxxxx > ~/.hf_token && chmod 600 ~/.hf_token

# 3. 제출
./submit_all.sh --dry-run     # 명령 먼저 확인
./submit_all.sh
```

## 작업 구성

| 스크립트 | 커널 | GPU | mem | time |
|---|---|---|---|---|
| `00_setup.sbatch` | — | 불필요 | 32G | 4h |
| `01_verify.sbatch` | — | 필요 | 16G | 15m |
| `10_bgm_stable_audio.sbatch` | `sa3` | 필요 | 48G | 3h |
| `11_bgm_ace_step.sbatch` | `ace` | 필요 | 48G | 3h |
| `20_image_hidream.sbatch` | `img` | 필요 | **96G** | 5h |
| `21_image_flux2_klein.sbatch` | `flux` | 필요 | 48G | 5h |

`img` 만 96G 인 이유: `enable_model_cpu_offload()` 라 HiDream 47GB + Llama 16GB 가
전부 호스트 RAM 에 올라간다.

의존성은 `afterany` 로 건다. `afterok` 이면 setup 이 부분 실패했을 때 멀쩡한 환경까지
전부 취소된다. 각 job 이 시작할 때 자기 환경을 다시 확인한다.

## 이 클러스터 함정 대응

스크립트가 이미 처리하고 있는 것들 — 직접 sbatch 를 짤 때 참고.

| 함정 | 대응 위치 |
|---|---|
| ③ 로그 디렉토리가 없으면 job 이 로그도 없이 즉사 | `submit_all.sh` 가 **제출 전에** `mkdir -p` |
| ④ `--output` 을 로그인 노드 경로로 주면 실패 | `--output=/mnt/data1/...` (계산 노드 경로) |
| ⑤ 제출 시 cwd 가 계산 노드에 없어 `0:53` | `--chdir=/tmp` |
| ⑥ `BASH_SOURCE`/`SLURM_SUBMIT_DIR` 이 spool·로그인 경로 | `--export=ALL,PROJ_REL=<상대경로>` 로 전달, job 이 루트를 직접 탐색 |
| 계산 노드에 `$HOME` 이 없음 | `common.sh` 가 `HOME=$ROOT` 로 재설정 |
| ⑦ conda/venv 콘솔 스크립트 shebang 깨짐 | `activate` 안 씀. `"$PY" -m papermill` 처럼 직접 호출 |
| 디스크 부족 (`os error 28`) | `UV_CACHE_DIR`/`TMPDIR`/`HF_HOME` 전부 `PROJ_BASE` 아래 + `need_space` 가드 |

## 결과 확인

```bash
squeue -u $USER
sacct -u $USER --starttime today --format=JobID%12,JobName%16,State%14,ExitCode,Elapsed

# papermill 은 로그를 stderr 로 보낸다. .err 를 볼 것
tail -n 40 ~/mystery/logs/*.err

ls ~/mystery/outputs/      # 생성물
ls ~/mystery/executed/     # 셀 출력이 담긴 노트북
```

로그 끝에는 `trap ... EXIT` 로 항상 요약이 남는다 — 성공/실패, 생성물 개수,
실패했다면 **몇 번째 셀에서 어떤 예외가 났는지**까지 뽑아준다.

## ExitCode 읽기

| 값 | 의미 |
|---|---|
| `0:0` | 정상 |
| `1:0` | 스크립트 실패 (셀 예외 등) |
| `0:9` | SIGKILL — `scancel` 또는 시간 초과 |
| `0:53` | **job 이 시작조차 못 함** → 작업 디렉토리 / 로그 경로 문제 |

## 자주 걸리는 것

**`No space left on device (os error 28)`**
`/data1/$USER` 여유가 170GB 미만이다. `probe.sh` 1번을 볼 것.
정리: `bash ../setup_kernels.sh --clean`

**`meta-llama/Llama-3.1-8B-Instruct` 401**
gated(수동 승인). 승인 전에는 미러로:
```bash
export LLAMA_ID=NousResearch/Meta-Llama-3.1-8B-Instruct
```
`submit_all.sh` 가 `--export=ALL` 이라 제출 셸의 환경변수가 job 으로 전달된다.

**환경 하나만 다시 만들기**
```bash
bash ../setup_kernels.sh --only ace
./submit_all.sh --no-setup --only ace
```

**대기가 길 때**
`--time` 을 줄이면 backfill 빈틈에 들어간다. `submit_all.sh` 상단의
`T_BGM` / `T_IMG` 를 실제 소요의 120% 정도로 조정할 것.
