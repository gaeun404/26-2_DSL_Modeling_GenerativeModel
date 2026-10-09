# murdermystery — 데이터 형태·예시·학습 활용

받은 전체 데이터를 ① JSON/데이터 형태 ② 예시 ③ 생성모델 학습 활용으로 정리.
※ HF 전용 코퍼스(DetectiveQA·RoleBench·MysteryWriter 등)는 필드가 버전따라 다를 수 있어
  실제 스키마는 `head`/`json.load`로 한번 확인 권장. 아래는 대표형.

## 1. 케이스 구조 — 생성 논리 · 시드 · 평가

| 데이터 | 형태 | 예시 | 학습 활용 |
|---|---|---|---|
| 07_musr_hf / 03_musr (250) | `{context, questions:[{question, answer(idx), choices:[용의자], intermediate_trees(수단·동기·기회 사실트리), intermediate_data}]}` | choices:["Mackenzie","Ana"], answer:0; 트리: "Mack은 눈차쿠 숙련(수단)→…" | 정답 추론체인 본보기. "수단/동기/기회로 범인 좁히기" 논리 SFT. clue_graph 설계 원본. (용의자 2명 한계) |
| 01_whodunit_full (320/원본64) | `{title, culprit_ids:[...], text}` | {"title":"The Red-Headed League","culprit_ids":["John Clay"],"text":"..."} | few-shot 시드 + 생성물 평가 벤치. LLM으로 용의자·단서 추출해 케이스화 |
| 06_detectiveqa | `{novel, questions:[{question, answer, options, reasoning}]}` (편별 json) | "범인은? → 근거와 함께" | 장편 추론 SFT + eval |
| 04_true_detective (191) | `{mystery, solution, options}` (data.zip) | 5분 미스터리 퍼즐 + 정답 | 짧고 solvable한 골격 템플릿 |
| 05_player Jubensha (26게임) | 캐릭터별 `{script, victims, secrets, is_murderer, kill_by_me, acts_goal, questions, final_goal}` | "Boss Zhang": is_murderer:false, secrets:[...] | 유일한 다인 용의자 실물. "각자 비밀·범인만 아는 정보·자기소개" 구조 본보기 |

## 2. 트릭·동기 패턴 사전 — 생성 재료

| 데이터 | 형태 | 예시 | 학습 활용 |
|---|---|---|---|
| 23_conan_cases (751) | `{title, infobox:{victim, culprit, "cause of death", motive, trick}, suspects_candidates:[], scenario_text, source_url, license}` | motive:"상속", cause:"독살", trick:"알리바이 조작" | 트릭·동기 유형 사전. 생성 시 트릭 조건부 샘플링. ⚠️원문 재배포·복제학습 금지(재작성만) |

## 3. 현실 분포 — 동기 리얼리티

| 데이터 | 형태 | 예시 | 학습 활용 |
|---|---|---|---|
| 17_murder_accountability SHR (~80만 행) | CSV 32컬럼. 핵심 Circumstance(동기)·Weapon·Relationship·VicSex·VicAge·Solved | Weapon:"Knife", Relationship:"Acquaintance", Circumstance:"Argument" | 생성 동기·무기·관계를 현실 분포로 샘플링하는 prior. 비현실 동기 방지 |

## 4. 배경·원작 — 세계관/캐릭터

| 데이터 | 형태 | 예시 | 학습 활용 |
|---|---|---|---|
| 02_fairytaleqa (278) | 스토리(섹션) + `{question, attribute, answer, ex-or-im}` | "누가 가장 아름답다 했나 → 왕비의 딸" | 백설공주류 원작 캐릭터/사건 + 인과추론 QA |
| 12_gutenberg (7종, PD) | 원문 .txt | 셜록·포·브라운신부·그림·안데르센 | PD 배경 + 셜록 추리 스타일 |
| 16_korean_classics | 위키텍스트 .txt(하위편 합본) | 심청전·박씨전 | 조선시대 배경 |
| 13_fairy_tales_hf | `{title, text}` | 그림/안데르센 | 설화 배경 보강 |

## 5. 말투·페르소나 — 인물 에이전트

| 데이터 | 형태 | 예시 | 학습 활용 |
|---|---|---|---|
| 09_rolebench | `{role, instruction, question, answer}` | 특정 캐릭터 말투 응답 | 인물별 말투 고정(페르소나 일관성) fine-tune |
| 10_dailydialog | `{dialog:[...], act, emotion}` | 일상 대화 시퀀스 | 자연스러운 심문·대화 톤 |

## 6. 보조 코퍼스 — 시드 다양화

| 데이터 | 형태 | 학습 활용 |
|---|---|---|
| 20_mysterywriter | `{instruction/prompt, output}` | 미스터리 서사 생성 SFT 보조 |
| 21_mystery_crime_books | `{text}` 도서 코퍼스 | 도메인 스타일 사전학습 |
| 22_llm_mysteries | `{mystery, solution}` (GitHub) | 추론 시드/eval |

---

## 학습 파이프라인에서의 역할 요약

- **SFT 콜드스타트 입력** ← 1번(MuSR·WhoDunIt·Jubensha)을 공통 케이스 스키마로 변환한 시드
- **생성 조건(재료)** ← 2번 코난 트릭·동기 사전 + 3번 SHR 현실분포 + 4번 배경
- **검증 후 축적된 합성분** ← 본 SFT→DPO 학습의 "다량" 본체
- **평가 벤치** ← 1번의 WhoDunIt·DetectiveQA·TrueDetective
- **인물 에이전트(대화) 학습** ← 5번 RoleBench·dailydialog

핵심: 받은 데이터는 대부분 **생성기 재료·시드·평가**다. 최종 학습 타깃(다용의자 시나리오)은
생성→검증을 통과한 합성 데이터가 채운다.
