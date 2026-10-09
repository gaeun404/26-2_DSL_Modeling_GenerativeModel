# 생성형 머더미스터리

다섯 명의 AI 용의자를 상대로 세 라운드 안에 범인을 짚는 추리 게임.
시나리오 50편, 게임 엔진, 생성·검증 도구가 모두 들어 있다.

> **내부 공유용.** 저장소를 공개로 돌리기 전에 아래 [공개 전 확인](#공개-전-확인)을 읽을 것.

---

## 바로 돌려 보기

파이썬 3.9 이상만 있으면 된다. 설치할 것은 없다.

```bash
python3 walk.py --auto               # 화면 순서대로 끝까지 (인트로→…→재연→엔딩)
python3 walk.py                      # 직접 골라 가며 (지도에서 장소를 고른다)
python3 compare.py                   # 다섯 방식을 인트로부터 엔딩까지 견준다
python3 compare.py --full 증거파      # 한 방식만 처음부터 끝까지 자세히
python3 agents.py                    # 성격이 다른 판정자 여섯을 같은 밤에 풀어놓는다
python3 agents.py --full 심리        # 한 성격의 판을 처음부터 끝까지
python3 walk.py --agent              # 용의자·판정자 둘 다 LLM이 맡아 혼자 논다

# 프론트엔드와 붙이기
pip install -r requirements.txt
python3 server.py                    # http://127.0.0.1:8000
#   /docs  자동 생성된 API 문서 (직접 눌러 볼 수 있다)
#   /demo  배선만 확인하는 한 장짜리 화면
#   명세   docs/API명세.md  ← 프론트 팀원에게 넘길 것
python3 play.py                      # 91편 「여섯 잔의 회의」 한 판
python3 play.py --list               # 시나리오 50편 목록
python3 play.py 38_cinderella.json --style 탐색파
python3 check.py                     # 검증 여덟 가지 전부 (몇 분)
python3 check.py --fast              # 무거운 것 빼고 (30초)
```

`play.py`는 **키가 없어도 돈다.** 용의자가 언제 흔들리고 언제 실토하는지는
코드(`stance` + `pressure`)가 정하기 때문이다. 대사 자리만 자리표시자로 나온다.

실제 문장까지 보려면 OpenAI 키가 필요하다.

```bash
echo "sk-..." > .apikey               # .gitignore에 들어 있다
python3 playtest.py --rounds 2        # 약 100원
python3 playtest.py --style 증거파
```

---

## 폴더

| | |
|---|---|
| `scenarios/` | **완성된 시나리오 50편** + `catalog.json`. 이것이 게임 데이터의 전부다 |
| `novels/` | 편마다의 바이블(설정 소설). 시나리오를 사람이 읽는 형태 |
| `src/` | 게임 엔진과 생성·검증 도구 150여 개. 서로 import하므로 평평하게 둔다 |
| `docs/` | 설계서 · 스토리보드 · 플레이어 규칙 · 단서 명세 · 스키마 |
| `assets/dsl/` | 91편 시연용 실사 초상 6장 — [공개 전 확인](#공개-전-확인) |
| `.runtime/` | 실행 중 생기는 것(장기기억 등). 깃에 올라가지 않는다 |

진입점은 뿌리에 넷뿐이다.

| | |
|---|---|
| `walk.py` | **화면 순서대로 걸어 보기** — 모의 프론트엔드 (키 불필요) |
| `compare.py` | **다섯 방식으로 각각 한 판씩** 돌려 견주기 (키 불필요) |
| `server.py` | **엔진을 HTTP로 연다** — 프론트가 붙는 자리 (FastAPI) |
| `agents.py` | **성격이 다른 판정자 여섯**이 각자 질문을 지어 가며 판다 (`.apikey` 있으면 LLM, 없으면 규칙) |
| `play.py` | 한 판 돌려 보기 (키 불필요) |
| `playtest.py` | 실제 LLM으로 한 판 (키 필요) |
| `check.py` | 검증 여덟 가지 |
| `build.py` | 시나리오 다시 빌드 |

---

## 게임이 어떻게 굴러가는가

세 라운드(편에 따라 넷), 라운드마다 **행동 예산 8**.
**장소 하나를 그 라운드에 처음 조사할 때 1**, 사람에게 한 번 묻는 데 1이 든다.
같은 방을 다시 봐도 값이 더 들지 않고, 그 방에 그 라운드에 있는 단서는 한꺼번에 나온다.
여덟 번으로는 다섯 사람을 다 만나면서 모든 방을 뒤질 수 없다 — 그 선택이 이 게임이다.

**단서가 들어오는 길은 넷뿐이고, 한 단서는 한 길로만 들어온다.**

| 길 | `channel` | 예산 |
|---|---|---|
| 자동 지급 | `crime_scene` · `spine` | 0 |
| 장소 탐색 | `location` · `record` · `physical` | 1 |
| 심문 실토 | `belongings` | 1 |
| 수첩 조합 | `clue_combos` | 0 |

얻는 즉시 사건수첩에 **자동으로** 적힌다. 본문만 적고 추리는 적지 않는다.
그래서 단서를 다시 보려고 그 장소에 또 들어갈 필요가 없다.

인물을 **처음 만나면** 알리바이를 두 문장으로 먼저 말한다(예산 0).
채팅은 그 진술을 **알고 나서** 파고드는 자리다.

비밀은 **그 비밀을 여는 단서를 손에 쥐고 내밀었을 때만** 열린다.
어느 단서가 누구 것인지는 단서 본문에 드러나 있다 — 이름·신분·낱말로.
말로만 찌르면 흔들릴 뿐(FLINCH), 인정하지 않는다.

자세한 것은 `docs/설계서.html`, 화면별 명세는 `docs/스토리보드.html`.

---

## 엔진 쓰는 법

```python
import sys; sys.path.insert(0, "src")
import json, stance
from game_engine_v2 import GameSession

s = json.load(open("scenarios/91_dsl_demo.json", encoding="utf-8"))
g = GameSession(s)

g.state()                     # 화면에 그릴 것 전부 — 라운드·예산·대질 잠금·인물·수첩
g.meet("C1")                  # 첫 대면 알리바이. 예산 0, 두 번째부터 already=True
g.search("PC", 0)             # 장소 조사. 예산 1
g.combine("K1", "K2")         # 수첩에서 겹치기. 예산 0
g.confront("C1", "C5", "…")   # 대질. 한 판 1회, 예산 밖
g.next_round()
```

### 심문 한 번의 전체 왕복

**판단은 코드가 내리고, 문장만 LLM이 만든다.** 이 순서를 지켜야 한다.

```python
st = g.interrogate("C1", question,
                   evidence_shown=bool(내가_인용한_단서))

system  = stress_agent.suspect_system(s, cast)   # 인물 설정서
system += st["directive"]                        # ★이번 턴의 태도 — 빠뜨리면 판단과 대사가 따로 논다
system += st["memory_briefing"] or ""            # 이 인물이 지금까지 한 말
system += st["again_directive"] or ""            # 같은 것을 또 물었을 때만

reply = llm(system, history[-6:], question)

# ★받은 뒤 코드로 검사한다 — 프롬프트만으로는 샌다
if (stance.leaked(reply, st) or stance.confessed(reply, cast)
        or stance.bad_address(reply)):
    reply = llm(system + 경고문, history[-4:], question)   # 한 번 다시
reply, _ = stance.strip_leak(reply, st)          # 비밀·동기가 샜으면 도려낸다
reply, _ = stance.strip_confession(reply, cast)  # 범인이 자백했으면 도려낸다
reply = stance.fix_address(reply)                # 엉뚱한 호칭을 바로잡는다

g.remember("C1", question, reply)                # 이걸 빠뜨리면 다음 턴에 같은 말을 되풀이한다
```

가장 자주 나는 사고 두 가지 —

1. **`st["directive"]`를 안 붙인다.** 엔진이 ADMIT을 정해도 모델은 그 사실을 모른 채
   계속 회피한다. 화면엔 「실토」가 뜨는데 대사는 「말씀드리기 어려워요」가 된다.
2. **답을 받은 뒤 검사하지 않는다.** 실측에서 범인이 살해 동기를 통째로 읊었고,
   무고한 인물이 자기 비밀을 먼저 불었다. 그 한 마디로 게임이 끝난다.

---

## 시나리오를 고치려면

`scenarios/*.json`을 손으로 고친 뒤 다시 빌드하고 검증한다.

```bash
python3 build.py 91_dsl_demo.json     # 한 편
python3 build.py                      # 50편 전부 (몇 분)
python3 check.py
```

빌드 순서는 `src/hand_pipeline.sh`에 적혀 있다.
새 편을 만들려면 `src/build_91_dsl.py` 같은 씨앗 파일을 본떠 쓴다 —
`SEED` 딕셔너리 하나를 손으로 쓰면 `seedc.py`가 규칙을 강제하며 JSON을 뽑는다.

**검증은 통과해야 한다.** 여덟 가지가 각각 다른 것을 본다.

| | |
|---|---|
| `run_all` | 논리·난이도·플레이가능·비밀 이중도달·UX·관계 + 54항목 |
| `fe_lint` | 프론트가 필요한 것이 스키마에 다 있는가 |
| `ux_lint` | 게임 요소가 실제로 작동하는가 |
| `eval_play` | 한 판이 끝까지 굴러가는가 |
| `eval_policies` | 성급하게 찍어도 맞아떨어지지는 않는가 |
| `relation_lint` | 관계 서술이 상투구가 아닌가 |
| `agent_lint` | 인물 카드에 자백 어휘가 새지 않았는가 |

---

## 공개 전 확인

- **`.apikey`를 절대 커밋하지 않는다.** `.gitignore`에 들어 있지만 한 번 더 본다.
  이미 올린 적이 있다면 그 키는 폐기한다.
- **`assets/dsl/`의 초상 6장과 `scenarios/91_dsl_demo.json`은 실존 인물이 소재다.**
  작중 비밀·동기·범행은 전부 허구지만, 외부 공개·녹화·배포 전에
  **여섯 사람 모두의 동의**가 필요하다. 저장소를 공개로 돌릴 계획이라면 이 둘을 먼저 뺀다.
- 원작 각색분은 공개 설화·동화·고전이 바탕이다. 참고 자료로 쓴 상용 대본·문제집은
  이 저장소에 들어 있지 않으며, 그 문장을 그대로 옮긴 곳도 없다.

---

## 현재 상태

```
시나리오        50편 · 검증 여덟 가지 전부 통과
난이도          별 다섯 등급에 각 10편씩
평균            장소 7.1곳 · 단서 17개 · 대질 3.7쌍 · 조합 4.1개
라운드          3라운드 34편 · 4라운드 16편
행동 예산       전 편 8
```
