# My Murder Mystery

**생성모델로 매 판 새로 쓰이는 AI 인터랙티브 추리게임**
DSL 26-2 Modeling — Generative Model Team

15기 백가은 · 안재민 　|　 16기 김용진 · 이준희 · 한서현

> 이 저장소는 **중간발표 시점(2026-09-02)** 의 코드입니다. 발표자료는 [`My_Murder_Mystery_중간발표.pdf`](./My_Murder_Mystery_중간발표.pdf).

---

## Project Overview

머더미스터리는 사람이 시나리오 하나를 쓰는 데 수십 시간이 든다. 그렇게 써도 **한 번 풀면 끝난다** — 범인을 아는 순간 재플레이 가치가 사라진다. 그래서 이 장르는 콘텐츠 공급이 수요를 못 따라간다.

우리는 **사건·용의자·단서·트릭을 생성모델이 매 판 새로 구성하게** 했다. 문제는 "그럴듯한 이야기"를 만드는 게 아니라 **풀 수 있는 사건**을 만드는 것이다. 추리가 성립하려면 단서들이 논리적으로 한 사람만 가리켜야 하고, 나머지 넷은 의심스럽되 결국 혐의를 벗어야 한다. 소설은 틀려도 읽히지만 추리는 틀리면 게임이 깨진다.

그래서 이 프로젝트의 중심은 **생성과 검증을 분리한 파이프라인**이다.

| | |
|---|---|
| **생성** | 원작 한 줄 → 사건 1개. 인물·단서·트릭·엔딩을 LM이 쓴다 |
| **구조** | MMO(수단·동기·기회)를 **단서 그래프**로 옮겨, 각 단서가 누구를 가리키고 누구를 혐의에서 벗기는지 명시 |
| **검증** | 타임라인 모순 · 해의 유일성 · 의심도 균등 · 난이도를 **코드가** 판정 |
| **플레이** | 용의자 5인을 다중 에이전트로 세우고, 말투는 LM이 쓰되 **무엇을 말할지는 코드가 정한다** |

---

## Pipeline

```
INPUT                SCENARIO             ENGINE                CLIENT
전래동화·원작 배경  →  각색한 살인사건  →  FastAPI           →  React · Vercel
범죄 통계 데이터       cast · clue_graph    세션 = 한 판          화면 24개
                       trick · secrets      REST 19갈래
       ↓                     ↓                   ↓
   사건의 기본 구조      MMO 단서 그래프      라운드·턴수·공개
   (피해자, 용의자 5,    + 검증 통과본        대질·조합·판정
    트릭, 동기)
                             ↓
                   IMAGE (FLUX 2) · BGM (Stable Audio 3)
```

### 1. Dataset

| 내용 | 데이터셋 | 출처 |
|---|---|---|
| 추론 구조 | **MuSR** — 사실 트리를 단서 그래프 설계에 그대로 옮김 | [Zayne-sprague/MuSR](https://github.com/Zayne-sprague/MuSR) · [TAUR-Lab/MuSR](https://huggingface.co/datasets/TAUR-Lab/MuSR) |
| 사건 코퍼스 | **WhoDunIt · DetectiveQA · True Detective** — 생성 시드 겸 평가 벤치마크 | [kjgpta/WhoDunIt](https://huggingface.co/datasets/kjgpta/WhoDunIt) · [Phospheneser/DetectiveQA](https://huggingface.co/datasets/Phospheneser/DetectiveQA) · [TartuNLP/true-detective](https://github.com/TartuNLP/true-detective) |
| 다인 용의자 | **PLAYER — 剧本杀 극본**. 다인 용의자가 각자 비밀을 갖는 실물 구조 | [alickzhu/PLAYER](https://github.com/alickzhu/PLAYER) |
| 트릭 · 동기 | 사건 아카이브 · 강력범죄 통계 — 트릭 분류와 동기의 현실 분포 | 위키 아카이브 · [murderdata.org](https://murderdata.org) |
| 배경 · 심문 | **FairytaleQA · Gutenberg · 한국 고전 · RoleBench** — 원작 세계관과 인물 말투 | [uci-soe/FairytaleQAData](https://github.com/uci-soe/FairytaleQAData) · [ZenMoore/RoleBench](https://huggingface.co/datasets/ZenMoore/RoleBench) |
| 현장 조사 | 보드게임 카페 머더미스터리 플레이 — 라운드 구성·행동 제한·대질 규칙 | 현장 답사 · 수작업 |

### 2. MMO Structure — 단서 그래프

추리가 성립하는 최소 조건을 자료 구조로 고정했다. 단서마다 네 가지를 명시한다.

```
MEANS      수단    흉기 · 접근권
MOTIVE     동기    이해관계 · 비밀          →   세 축을 모두 만족하는 인물 = 범인
OPPORTUNITY 기회   동선 · 알리바이
```

| 필드 | 뜻 |
|---|---|
| `points_to` | 이 단서가 가리키는 인물 |
| `exculpates` | 이 단서로 혐의를 벗는 인물 |
| `decisive` | 승부를 가르는 단서인가 |
| `forced_by` | 어떤 단서가 이 비밀을 열게 하는가 |
| `channel` | 얻는 경로 (현장·조사·심문·대질·조합) |
| `reveal_round` | 몇 라운드부터 닿을 수 있는가 |

전체 스키마는 [`docs/스키마.md`](./docs/스키마.md).

### 3. 심문 — 코드가 판정하고 LM이 쓴다

용의자 5인은 각자 페르소나와 장기기억을 갖는 에이전트다. 다만 **"무엇을 말할지"를 LM에 맡기지 않는다.** 플레이어가 들이댄 증거와 압박 게이지로 코드가 태도를 먼저 정하고, LM은 그 태도대로 **문장만** 쓴다.

```
ANSWER → DEFLECT → FLINCH → ADMIT → BREAK
답한다   피한다    흔들렸다  실토했다  무너졌다
```

실토하지 않아야 할 것을 흘렸는지, 질문에 엉뚱한 답을 했는지, 알맹이 없이 둘러댔는지를 코드가 사후 검사해서 걸리면 다시 쓰게 한다. (`src/stance.py`, `src/play_agents.py`, `src/guard.py`)

### 4. Agent-based Validation

사람이 50편을 다 풀어 볼 수 없으므로 **에이전트가 대신 푼다.**

| | |
|---|---|
| **몬테카를로** | 50편 × 각 600회 시뮬레이션으로 난이도 측정 |
| **전략 에이전트 5종** | 체계적 탐색 · 조기 지목 · 미끼 추종 · 소거법 · 무작위 |
| **LLM 판정자 6종** | 형사 · 기자 · 과학수사 · 심리 · 변호사 · 초심자 페르소나가 실제 플레이 로그를 읽고 교정 |

`src/simulate.py` · `src/eval_policies.py` · `src/measure_difficulty.py` · `src/stress_agent.py`

### 5. Image / BGM

| | 모델 | 흐름 |
|---|---|---|
| **IMAGE** | FLUX 2 (Text-to-Image) | Text/Reference → Mistral Text Encoder + VAE Encoder → Noise → Diffusion Transformer → VAE Decoder |
| **BGM** | Stable Audio 3 (Text-to-Music) | Text Prompt → Gemma Text Encoder → Noise → Diffusion Transformer → Audio Decoder |

시나리오 JSON의 `ui.place_screens[].art.prompt_*`, `bgm.cues.*.prompt_en` 이 그대로 프롬프트로 들어간다. 노트북은 [`media/`](./media).

### 6. Custom Scenario Generator

플레이어가 컨셉을 적어 넣으면 그 자리에서 한 편을 만든다. LLM API는 CLOVA Studio.

```
사용자 컨셉 입력 → 재료 생성 → 조립 assemble() → UI 텍스트·BGM 배정·novel → 검증 → 최종 출력
```

| 재료 생성 4단계 | 모델 | 하는 일 |
|---|---|---|
| 1 뼈대 | HCX-007 (추론) | 범인 · MMO · 거짓말 등 논리 뼈대 |
| 2 인물 서사 | HCX-005 | 인물 성격, 배경과 서사 |
| 3 도입 나레이션 | HCX-005 | 사건 개요 및 요약 |
| 4 단서 · 정답 | `generate.py` | `synthesize_mystery()` 가 사실관계를 단서 데이터로 변환 |

`src/generate.py` · `src/llm_custom.py` · `src/build_custom.py`

---

## Output / Evaluation

### 행동 예산별 범인 적중률

라운드당 행동 횟수를 바꿔 가며 250판(5전략 × 50편)을 돌렸다. **목표는 절반** — 너무 쉬우면 추리가 아니고 너무 어려우면 게임이 아니다.

| 라운드당 행동 | 범인 적중률 | 판정 |
|---|---|---|
| 10회 | 66% | 여유롭다 |
| 9회 | 59% | |
| **8회 (채택)** | **44%** | 목표에 가장 가깝다 |

### 시나리오 검증

전 편이 `src/verify.py` 를 통과해야 플레이 가능으로 친다.

| 항목 | 기준 |
|---|---|
| 구조 | 용의자 5인 · 범인 1인 · 라운드/턴 설정 |
| 타임라인 | 인물 동선에 모순이 없는가 |
| 해 | 소거 후 남는 용의자가 2~3인이고, 결정타가 그 사이를 가르는가 |
| 의심도 | 특정 인물에게 혐의가 쏠려 있지 않은가 |
| 스포일러 | 공개 전 응답에 정답이 새지 않는가 |

### 산출물

| | |
|---|---|
| 시나리오 | 원작 기반 50편 + 커스텀 생성 (**이 저장소에는 시연용 1편만 포함** — 아래 참고) |
| 엔진 | FastAPI · 세션 = 한 판 · REST 19갈래 |
| 화면 | React + Vite + Tailwind + Zustand, 24개 페이지 |
| 에셋 | 편당 이미지 72장 규격 · BGM 큐 세트 |

---

## Repository Structure

```
26-2_DSL_Modeling_GenerativeModel/
├── README.md
├── My_Murder_Mystery_중간발표.pdf
│
├── engine/                     # 백엔드 — 생성 · 검증 · 플레이
│   ├── server.py               #   FastAPI, REST 19갈래
│   ├── ui_wire.py              #   화면이 읽는 모양으로 (정답은 뗀다)
│   ├── ui_view.py  ui_assets.py
│   ├── requirements.txt  render.yaml  Procfile
│   ├── scenarios/
│   │   └── 91_dsl_demo.json    #   시연용 1편
│   └── src/
│       ├── game_engine_v2.py   #   한 판의 모든 규칙 — 라운드·턴·조사·심문·대질·조합·판정
│       ├── stance.py           #   태도 판정 (ANSWER/DEFLECT/FLINCH/ADMIT/BREAK)
│       ├── pressure.py         #   압박 게이지
│       ├── play_agents.py      #   용의자 에이전트 — 페르소나·기억·발화
│       ├── guard.py            #   실토 금지·스포일러 차단 사후 검사
│       ├── verify.py           #   시나리오 검증
│       ├── generate.py         #   커스텀 시나리오 생성 (CLOVA Studio)
│       ├── llm_custom.py  build_custom.py
│       ├── build_91_dsl.py     #   시연 편 빌더
│       ├── simulate.py  eval_policies.py  measure_difficulty.py  stress_agent.py
│       ├── llm_api.py  llm.py  #   LLM 호출 (키는 환경변수)
│       └── … (전처리·보정·린트 스크립트)
│
├── web/                        # 프론트엔드 — React + Vite
│   ├── src/pages/              #   화면 24개
│   ├── src/components/         #   19개 묶음
│   ├── public/assets/
│   └── .env.example
│
├── media/                      # 이미지 · BGM 생성 노트북
│   ├── image_fluxdev*.ipynb  image_qwen*.ipynb  image_hidream*.ipynb
│   ├── bgm_stable_audio*.ipynb  bgm_ace_step*.ipynb
│   ├── build_scenario_en.py  validate_scenarios_en.py
│   └── slurm/
│
└── docs/
    ├── 스키마.md                #   시나리오 JSON 전체 스키마
    ├── API명세.md               #   REST 명세
    ├── 단서전달_명세.md
    ├── 게임규칙_플레이어용.md
    ├── 파이프라인.md
    ├── GAME_FLOW_SPEC.md
    └── data_kit/               #   데이터 카탈로그 · 포맷
```

---

## Usage

### 백엔드

```bash
cd engine
pip install -r requirements.txt
python3 server.py                      # http://127.0.0.1:8000
```

심문은 LLM을 부른다. 키는 **코드에 넣지 말고 환경변수로** 준다.

```bash
export MM_API_KEY=...                  # OpenAI 호환 엔드포인트면 어디든
export MM_API_BASE=https://...         # 생략 시 OpenAI 기본
export MM_API_MODEL=gpt-4o-mini
```

키가 없어도 서버는 뜬다 — 심문 답변만 못 받는다. 조사·대질·지목·엔딩은 그대로 돌아간다.

### 프론트엔드

```bash
cd web
npm install
cp .env.example .env                   # VITE_API_BASE_URL=http://127.0.0.1:8000
npm run dev                            # http://127.0.0.1:5173
```

### 시나리오 검증

```bash
cd engine
python3 src/verify.py scenarios/91_dsl_demo.json
```

### 커스텀 시나리오 생성

```bash
cd engine
export CLOVA_API_KEY=...
python3 src/generate.py --concept "눈 내린 산장, 다섯 사람, 끊긴 전화선"
```

### 난이도 측정

```bash
cd engine
python3 src/measure_difficulty.py      # 몬테카를로
python3 src/eval_policies.py           # 전략 에이전트 5종
```

---

## Requirements

**백엔드**

```
Python 3.11+
fastapi>=0.110
uvicorn[standard]>=0.29
```

**프론트엔드**

```
Node 20+
react 19 · react-router-dom 7 · zustand 5 · tailwindcss 4 · vite
```

**이미지 · BGM 노트북** — GPU 환경(slurm 스크립트 동봉). `diffusers`, `transformers`, `torch`, `stable-audio-tools`

---

## 공개 범위에 관하여

이 저장소는 **중간발표 시점의 코드**이며, 아래 둘은 의도적으로 뺐습니다.

- **원작 기반 시나리오 50편** — 팀이 이어서 서비스로 만들고 있는 작업물이라 시연용 1편(`91_dsl_demo.json`)만 넣었습니다. 파이프라인·엔진·검증 코드는 전부 들어 있어 **생성부터 플레이까지 그대로 재현됩니다.**
- **시연 편의 등장인물 이름** — 발표 때는 학회원 실명으로 시연했지만, 공개 저장소에는 **가명으로 바꿔** 올렸습니다.

중간발표 이후의 작업은 이 저장소에 없습니다.

---

## References

**Datasets**

- Sprague et al., *MuSR: Testing the Limits of Chain-of-thought with Multistep Soft Reasoning*, ICLR 2024 — [github](https://github.com/Zayne-sprague/MuSR)
- *WhoDunIt* — [huggingface](https://huggingface.co/datasets/kjgpta/WhoDunIt)
- Xiao et al., *DetectiveQA: Evaluating Long-Context Reasoning on Detective Novels* — [huggingface](https://huggingface.co/datasets/Phospheneser/DetectiveQA)
- Del & Fishel, *True Detective: A Deep Abductive Reasoning Benchmark* — [github](https://github.com/TartuNLP/true-detective)
- Zhu et al., *PLAYER: Multi-Agent Script Murder Mystery* — [github](https://github.com/alickzhu/PLAYER)
- Xu et al., *FairytaleQA* — [github](https://github.com/uci-soe/FairytaleQAData)
- Wang et al., *RoleLLM / RoleBench* — [huggingface](https://huggingface.co/datasets/ZenMoore/RoleBench)

**Models**

- Claude (Anthropic) — 시나리오 생성
- GPT-4o mini (OpenAI) — 용의자 심문 에이전트
- FLUX 2 — 장면·인물·단서 이미지
- Stable Audio 3 — 장면별 BGM
- CLOVA Studio HCX-007 / HCX-005 (NAVER) — 커스텀 시나리오 생성기
