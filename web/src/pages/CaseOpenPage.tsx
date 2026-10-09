import {
  useEffect,
  useState,
} from 'react'

import {
  useNavigate,
  useSearchParams,
} from 'react-router-dom'

import CaseOpenContent from '../components/caseopen/CaseOpenContent'
import ConfirmDialog from '../components/common/ConfirmDialog'

import { useGameStore } from '../store/gameStore'


export default function CaseOpenPage() {
  const navigate = useNavigate()

  const [searchParams] =
    useSearchParams()

  const scenario =
    useGameStore(
      (state) =>
        state.scenario,
    )

  const gameTitle =
    useGameStore(
      (state) =>
        state.gameTitle,
    )

  const sourceTitle =
    useGameStore(
      (state) =>
        state.sourceTitle,
    )

  const caseNarration = useGameStore((state) => state.caseNarration)

  const selectedLibraryCase =
    useGameStore(
      (state) =>
        state.selectedLibraryCase,
    )


  const mode =
    searchParams.get('mode') ===
    'archive'
      ? 'archive'
      : 'generate'


  /* 순차 등장 */
  const [
    isBlackout,
    setIsBlackout,
  ] = useState(true)

  const [
    showTitle,
    setShowTitle,
  ] = useState(false)

  const [
    showBackground,
    setShowBackground,
  ] = useState(false)

  const [
    showIncident,
    setShowIncident,
  ] = useState(false)

  const [
    showEnding1,
    setShowEnding1,
  ] = useState(false)

  const [
    showEnding2,
    setShowEnding2,
  ] = useState(false)

  const [
    showButtons,
    setShowButtons,
  ] = useState(false)

  const [
    showRestartPopup,
    setShowRestartPopup,
  ] = useState(false)


  /* 등장 연출 */
  useEffect(() => {
    const blackoutTimer =
      window.setTimeout(() => {
        setIsBlackout(false)
      }, 700)

    const titleTimer =
      window.setTimeout(() => {
        setShowTitle(true)
      }, 700)

    const backgroundTimer =
      window.setTimeout(() => {
        setShowBackground(true)
      }, 1500)

    const incidentTimer =
      window.setTimeout(() => {
        setShowIncident(true)
      }, 2500)

    const ending1Timer =
      window.setTimeout(() => {
        setShowEnding1(true)
      }, 3400)

    const ending2Timer =
      window.setTimeout(() => {
        setShowEnding2(true)
      }, 4100)

    const buttonsTimer =
      window.setTimeout(() => {
        setShowButtons(true)
      }, 4600)

    return () => {
      window.clearTimeout(
        blackoutTimer,
      )

      window.clearTimeout(
        titleTimer,
      )

      window.clearTimeout(
        backgroundTimer,
      )

      window.clearTimeout(
        incidentTimer,
      )

      window.clearTimeout(
        ending1Timer,
      )

      window.clearTimeout(
        ending2Timer,
      )

      window.clearTimeout(
        buttonsTimer,
      )
    }
  }, [])


  

  const caseTitle =
    mode === 'archive'
      ? selectedLibraryCase?.title ??
        scenario?.title ??
        gameTitle
      : (scenario?.title ??
        gameTitle) ||
        '생성된 이야기'



  const caseLabel =
    mode === 'archive'
      ? selectedLibraryCase?.origin ??
        scenario?.origin ??
        ''
      : scenario?.origin ||
        sourceTitle ||
        '사용자 커스텀'


  const backgroundLine =
    mode === 'archive'
      ? selectedLibraryCase?.backgroundLine ??
        scenario?.ui.victim_card.bio_short ??
        ''
      : scenario?.ui.victim_card.bio_short ??
        ''


  /*
    ★여기서 피해자를 알려 주면 안 된다 (2026-08-31, 제보 —
      "회장이 피해자인 걸 보여주지 않는 걸로 바꿨는데?").

      death.scene_description 은 「한도윤이 의자에서 미끄러진 채 쓰러져 있다」로
      시작한다. 이 화면은 빨간 화면보다 **앞**이라, 그것을 여기 쓰면 누가
      죽었는지가 판을 열기도 전에 적혀 버린다. 현장 묘사는 빨간 화면 뒤,
      사건 현장(S-08)에서 처음 나온다.

      사건 공개 나레이션은 이미 이름 없이 쓰여 있다 — 그것을 쓴다.
  */
  const incidentLine =
    selectedLibraryCase?.incidentLine ||
    caseNarration ||
    ''

  const endingLines =
    scenario?.ending.truth_reveal
      ?.split(/\n+/)
      .map((line) => line.trim())
      .filter(Boolean) ?? []


  const endingLine1 =
    mode === 'archive'
      ? selectedLibraryCase?.endingLine1 ??
        endingLines[0] ??
        ''
      : endingLines[0] ??
        ''


  const endingLine2 =
    mode === 'archive'
      ? selectedLibraryCase?.endingLine2 ??
        endingLines[1] ??
        ''
      : endingLines[1] ??
        ''


  return (
    <main
      className="
        relative
        h-[1024px]
        w-[1440px]
        overflow-hidden
        bg-black
      "
    >

      {/* 배경 */}
      <img
        src="/assets/icons/title-background.svg"
        alt=""
        className={`
          absolute
          inset-0
          h-full
          w-full
          object-fill
          transition-opacity
          duration-700

          ${
            showTitle
              ? 'opacity-100'
              : 'opacity-0'
          }
        `}
      />


      {/* 암전 */}
      <div
        className={`
          pointer-events-none
          absolute
          inset-0
          z-40
          bg-black
          transition-opacity
          duration-700

          ${isBlackout ? 'opacity-100' : 'opacity-0'}
        `}
      />

      {/* 내용 */}
      <CaseOpenContent
        isBlackout={isBlackout}
        caseLabel={
          caseLabel
        }

        caseTitle={
          caseTitle
        }

        backgroundLine={
          backgroundLine
        }

        incidentLine={
          incidentLine
        }

        endingLine1={
          endingLine1
        }

        endingLine2={
          endingLine2
        }

        showTitle={
          showTitle
        }

        showBackground={
          showBackground
        }

        showIncident={
          showIncident
        }

        showEnding1={
          showEnding1
        }

        showEnding2={
          showEnding2
        }

        showButtons={
          showButtons
        }

        onRestart={() =>
          setShowRestartPopup(true)
        }

        onOpen={() =>
          navigate(
            '/story',
          )
        }
      />

      {showRestartPopup && (
        <ConfirmDialog
          title="지금의 사건은 사라집니다."
          description="같은 이야기로 새로운 밤을 빚을까요?"
          cancelLabel="이 밤을 남긴다"
          confirmLabel="다시 빚는다"
          onCancel={() => setShowRestartPopup(false)}
          onConfirm={() => navigate('/case-start')}
        />
      )}

    </main>
  )
}
