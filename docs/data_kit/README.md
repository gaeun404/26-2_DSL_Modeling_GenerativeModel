# murdermystery — 데이터셋 스타터 키트

생성형 추리게임(NOIR) 학습·참고용 데이터셋 모음. 처음부터 다시 세팅하는 버전.

라이선스 표기: **⭐ = 퍼블릭 도메인/오픈(서비스까지 안전)**, **⚠️ = 학습·참고만(원문을 그대로 출력하지 말 것 — 구조·패턴만 사용)**.

---

## 0. 빠른 시작

```bash
cd murdermystery                      # 이 키트를 여기에 풀었다고 가정
python -m venv .venv && source .venv/bin/activate
pip install datasets

# 1) HuggingFace 계열 (WhoDunIt 등) — 이 zip엔 없음, 아래로 받기
python scripts/fetch_huggingface.py

# 2) GitHub 계열 — 이 zip에 이미 들어있음. 다시 받고 싶으면:
bash scripts/fetch_github.sh

# 3) Gutenberg 원작 텍스트(퍼블릭 도메인)
python scripts/fetch_gutenberg.py

# 4) WhoDunIt 가공본(원본 64편 등) 만들기
python scripts/01_whodunit.py
```

> 참고: 클라우드에서 이 키트를 만들 때 HuggingFace·Gutenberg는 네트워크 차단이라 **GitHub 소스만 미리 담았고**, HF/Gutenberg는 위 스크립트로 네 컴퓨터에서 받으면 된다(로컬은 제한 없음).

---

## 1. 이 zip에 이미 포함된 것 (GitHub 소스)

| 폴더 | 데이터셋 | 라이선스 | 내용 |
|---|---|---|---|
| `data/02_fairytaleqa` | FairytaleQA (uci-soe) | ⭐ | 동화 278편 + QA 주석. 백설공주·신데렐라류 원작 캐릭터/사건 소스 |
| `data/03_musr` | MuSR (murder_mystery.json) | ⭐ | 합성 살인미스터리 다단계 추론. 골격/추론체인 레퍼런스 |
| `data/04_true_detective` | TrueDetective (TartuNLP) | ⚠️ | 5분 미스터리 퍼즐 191개. 짧고 solvable → 시나리오 골격 최적 |
| `data/05_player` | PLAYER* / Jubensha | (코드 라이선스 확인) | 다인 용의자·심문 구조. english/ 26게임 |

## 2. 스크립트로 받는 것 (네 컴퓨터에서 실행)

### HuggingFace — `python scripts/fetch_huggingface.py`
| 폴더 | repo | 라이선스 | 용도 |
|---|---|---|---|
| `01_whodunit` | `kjgpta/WhoDunIt` | ⭐ | **핵심.** PD 추리소설 + 범인/용의자 주석 |
| `06_detectiveqa` | `Phospheneser/DetectiveQA` | ⚠️ | 장편 추리 QA. 단서→범인 추론 |
| `07_musr_hf` | `TAUR-Lab/MuSR` | ⭐ | MuSR 공식본(3개 도메인 전체) |
| `08_fairytaleqa_hf` | `WorkInTheDark/FairytaleQA` | ⭐ | FairytaleQA HF판 |
| `09_rolebench` | `ZenMoore/RoleBench` | ⚠️ | 캐릭터 페르소나·말투 일관성 |
| `10_dailydialog` | `daily_dialog` | ⭐ | 일상 대화 말투 |

### Gutenberg(퍼블릭 도메인) — `python scripts/fetch_gutenberg.py`
| 폴더 | 내용 | 라이선스 |
|---|---|---|
| `12_gutenberg` | 셜록 홈즈 3권·포 단편집·브라운 신부·그림/안데르센 동화 | ⭐ |

### 게이트드(별도 신청) — `bash scripts/fetch_github.sh` 로 코드만
| 폴더 | 데이터셋 | 비고 |
|---|---|---|
| `11_thinkthrice` | ThinkThrice / Jubensha | 데이터는 README의 Google Form 신청 승인 필요 |

## 3. 스크립트로도 못 받는 것 (수동/대용량)

| 데이터셋 | 라이선스 | 경로 |
|---|---|---|
| Murder Accountability Project | ⭐ | murderdata.org (실제 살인사건 통계 CSV — 동기·수법·관계 현실 분포) |
| Wikipedia 역사사건 덤프 | ⭐ CC BY-SA | dumps.wikimedia.org (중세·조선 배경) |
| 한국 고전(춘향전·심청전·홍길동전) | ⭐ | ko.wikisource.org (위키문헌) |
| 한국구비문학대계 | ⭐ | gubi.aks.ac.kr |

---

## 4. 폴더 구조

```
murdermystery/
├── README.md              ← 이 파일
├── data/
│   ├── 01_whodunit/       (스크립트 실행 후 채워짐)
│   ├── 02_fairytaleqa/    ✅ 포함
│   ├── 03_musr/           ✅ 포함 (murder_mystery.json)
│   ├── 04_true_detective/ ✅ 포함
│   └── 05_player/         ✅ 포함
└── scripts/
    ├── 01_whodunit.py         WhoDunIt 가공본 생성
    ├── fetch_huggingface.py   HF 일괄 다운로드
    ├── fetch_github.sh        GitHub 일괄 클론
    └── fetch_gutenberg.py     Gutenberg 원작 텍스트
```

## 5. 라이선스 주의 (한 줄 요약)

"연구용"이어도 **학습**과 **결과물 재배포/서비스**는 다른 문제다. ⚠️ 표시 데이터는
원문 문장을 생성물에 그대로 넣지 말고 **구조(clue graph·타임라인·의심 분배 패턴)만** 참고할 것.
⭐ 표시(PD/오픈)만 서비스 산출물에 안전하게 쓸 수 있다.
