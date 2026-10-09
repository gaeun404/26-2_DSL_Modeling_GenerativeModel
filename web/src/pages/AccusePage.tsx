import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import AccuseHeader from '../components/accuse/AccuseHeader'
import SuspectSelectRow from '../components/accuse/SuspectSelectRow'
import AccuseForm from '../components/accuse/AccuseForm'
import AccuseSubmitButton from '../components/accuse/AccuseSubmitButton'
import { useGameStore } from '../store/gameStore'
import { getSuspects } from '../data/scenarioAdapter'
import { useUiStore } from '../store/uiStore'

/* =========================================
   용의자 데이터 타입
========================================= */

export type AccuseSuspect = {
  id: string
  name: string

  /*
    TODO(API / IMAGE):
    이후 백엔드에서 받은
    용의자 이미지 URL 사용
  */
  image?: string
}

/* =========================================
   임시 용의자 데이터

   TODO(API):
   이후 scenario의 suspect 데이터로 교체.

   현재는 UI 테스트용.
========================================= */

export default function AccusePage() {
  const navigate = useNavigate()
  const scenario = useGameStore((state) => state.scenario)
  const accuse = useGameStore((state) => state.accuse)
  const showToast = useUiStore((state) => state.showToast)
  const [submitting, setSubmitting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const suspects: AccuseSuspect[] = getSuspects(scenario).map(
    (suspect) => ({
      id: suspect.id,
      name: suspect.name,
      image: suspect.image,
    }),
  )

  /* =========================================
     선택된 범인
  ========================================= */

  const [
    selectedSuspectId,
    setSelectedSuspectId,
  ] = useState<string>('')

  /* =========================================
     최종 추리 입력값
  ========================================= */

  const [tool, setTool] =
    useState('')

  const [method, setMethod] =
    useState('')

  const [motive, setMotive] =
    useState('')

  /* =========================================
     최종 제출

     제출 버튼을 눌러도 실행되고,
     범행 동기 입력 후 Enter를 눌러도
     동일한 함수가 실행됨.
  ========================================= */

  const handleSubmit = () => {
    if (submitting) {
      return
    }

    /* 범인을 선택하지 않은 경우 */
    if (!selectedSuspectId) {
      showToast('범인을 선택해 주세요.')
      return
    }

    /*
      ★필수는 **범인 하나뿐**이다 (팀원 제보 —
        "모든 요소를 안 적으면 제출이 안 돼서 엔딩을 볼 수 없음").

        채점은 범인 5점 + 연 비밀 1개당 1점이고, 흉기와 동기는 점수에 들어가지
        않는다. 막을 이유가 없다. 서버도 accuse_form.required 에 cast_id 하나만
        적어 보낸다 — 그 말을 그대로 따른다.

        다만 흉기는 **판정에 쓰인다** — 범인과 흉기를 모두 맞혀야 ARREST 다.
        안 고르고 제출하면 이름만 맞혀도 FAIL 이라, 그 사실만 알려 준다.
    */
    setShowConfirm(true)
  }

  const handleConfirmAccusation = async () => {
    if (submitting) {
      return
    }

    /* =========================================
       지목 — 되돌릴 수 없다.

       여기서 처음으로 진상·재연이 열린다.
       스토어가 받아서 시나리오에 얹어 두면
       RevealPage 가 그대로 읽는다.

       프론트는 진상 문구나 이미지를 직접 만들지 않는다.
    ========================================= */

    setShowConfirm(false)
    setSubmitting(true)

    try {
      await accuse(
        selectedSuspectId,
        tool.trim(),
        motive.trim(),
      )
    } catch (error) {
      showToast(
        error instanceof Error
          ? error.message
          : '요청에 실패했습니다.',
      )
      setSubmitting(false)
      return
    }

    /*
      ★못 맞히면 진상도 재연도 없다 (2026-08-31, 팀 결정 — 가은).

        답을 공짜로 알려 주면 지목이 형식이 된다. 밝혀낸 사람만 그 밤을 본다.
        서버는 truth 와 reenactment 를 아예 null 로 준다 — 그대로 /reveal 로
        보내면 「진상 데이터를 불러오지 못했습니다」가 떠서 **고장처럼 보인다.**
        감춘 것이 있으면 곧장 엔딩으로 간다. 엔딩은 빠져나간 밤을 이야기한다.
    */
    if (useGameStore.getState().gameResult?.withheld) {
      navigate('/ending')
      return
    }

    navigate('/reveal')
  }

  return (
    <main
      className="
        relative
        h-[1024px]
        w-[1440px]
        overflow-hidden
        bg-black
        text-game-ivory
      "
    >
      {/* =====================================
          HEADER
      ===================================== */}

      <AccuseHeader />

      {/* =====================================
          용의자 선택

          사진 테두리:
          suspect_frame.svg

          실제 구현은
          SuspectSelectRow.tsx에서 관리
      ===================================== */}

      <SuspectSelectRow
        suspects={suspects}
        selectedSuspectId={
          selectedSuspectId
        }
        onSelect={
          setSelectedSuspectId
        }
      />

      {/* =====================================
          범행 도구 / 방법 / 동기

          Enter 동작:

          도구
            ↓
          방법
            ↓
          동기
            ↓
          제출
      ===================================== */}

      <AccuseForm
        tool={tool}
        toolOptions={
          scenario?.choices.weapon.slice(0, 5) ?? []
        }
        method={method}
        motive={motive}
        onToolChange={setTool}
        onMethodChange={
          setMethod
        }
        onMotiveChange={
          setMotive
        }
        onSubmit={
          handleSubmit
        }
      />

      {/* =====================================
          제출 버튼
      ===================================== */}

      <AccuseSubmitButton
        onClick={
          handleSubmit
        }
      />

      {showConfirm && (
        <div className="absolute inset-0 z-[100] flex items-center justify-center bg-black/75 font-game-korean text-game-ivory">
          <button
            type="button"
            aria-label="범인지목 확인 닫기"
            onClick={() => setShowConfirm(false)}
            className="absolute inset-0 cursor-default border-0 bg-transparent"
          />

          <section className="relative h-[500px] w-[900px] border border-[#806c45] bg-[#0d0c0b] shadow-[0_20px_80px_rgba(0,0,0,0.75)]">

            <p className="absolute left-[100px] top-[125px] m-0 w-[700px] text-center text-[27px] tracking-[0.08em] text-game-ivory">
              한 번 지목하면 되돌릴 수 없습니다.
            </p>

            <button
              type="button"
              onClick={() => setShowConfirm(false)}
              className="absolute left-[155px] top-[305px] h-[110px] w-[240px] cursor-pointer border-0 bg-transparent font-game-korean text-[21px] tracking-[0.07em] text-[#9a8d72]"
            >
              조금 더 조사한다
            </button>

            <button
              type="button"
              onClick={handleConfirmAccusation}
              className="absolute left-[505px] top-[300px] h-[120px] w-[250px] cursor-pointer border-0 bg-transparent p-0"
            >
              <img
                src="/assets/icons/button.svg"
                alt=""
                className="absolute inset-0 h-full w-full object-fill"
              />
              <span className="absolute inset-0 flex -translate-x-[5px] -translate-y-[5px] items-center justify-center whitespace-nowrap font-game-korean text-[22px] tracking-[0.08em] text-game-ivory">
                지목한다
              </span>
            </button>
          </section>
        </div>
      )}
    </main>
  )
}
