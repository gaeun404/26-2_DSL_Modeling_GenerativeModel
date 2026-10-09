import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { NotebookClue } from '../../pages/NotebookPage'
import { useGameStore } from '../../store/gameStore'
import { useUiStore } from '../../store/uiStore'

type ClueCombineModalProps = {
  currentClue: NotebookClue
  clues: NotebookClue[]
  onClose: () => void
}

type CombineResult =
  | 'none'
  | 'pending'
  | 'success'
  | 'failure'
  | 'duplicate'

/* 이어졌을 때 서버가 주는 것 — 이름과 그래서 무엇을 알게 되었는가 */
type Composite = {
  name: string
  surface: string
  implies: string | null
  points: number
}

export default function ClueCombineModal({
  currentClue,
  clues,
  onClose,
}: ClueCombineModalProps) {
  const navigate = useNavigate()
  const remainingTurns = useGameStore(
    (state) => state.remainingTurns,
  )
  const roundOver = useGameStore((state) => state.roundOver)

  const closeCombineSession = () => {
    onClose()

    if (roundOver) {
      navigate('/round-end')
    }
  }

  const [
    selectedClueId,
    setSelectedClueId,
  ] = useState('')

  const [
    result,
    setResult,
  ] = useState<CombineResult>('none')

  const [
    composite,
    setComposite,
  ] = useState<Composite | null>(null)

  const [
    failMessage,
    setFailMessage,
  ] = useState('')

  const combine = useGameStore((state) => state.combine)
  const showToast = useUiStore((state) => state.showToast)

  const availableClues =
    clues.filter(
      (clue) =>
        clue.id !== currentClue.id,
    )

  const selectedClue =
    clues.find(
      (clue) =>
        clue.id === selectedClueId,
    )

  const handleSelectClue = (
    clueId: string,
  ) => {
    setSelectedClueId(clueId)
    setResult('none')
  }

  /*
    ★판정은 **서버가 한다** (2026-08-31, 제보 — "단서 겹쳐보기").

      여기에는 'clue-1 + clue-2 면 성공' 같은 임시 규칙이 박혀 있었다.
      실제 단서 id 는 K1·K2… 라서 무엇을 겹쳐도 늘 실패로 떨어졌다 —
      기능이 있는 줄 알았는데 아무것도 안 이어지던 이유다.

      시나리오에는 편당 평균 네 개의 조합이 준비돼 있다. 어느 둘이 붙는지는
      서버도 알려 주지 않는다 — 아무 둘이나 겹쳐 보고, 안 붙으면 안 붙는다고만
      답한다. 알아보는 것이 추리다.

      행동은 쓰지 않는다. 이미 가진 것을 다시 보는 일이다.
  */
  const handleCombine = async () => {
    if (selectedClueId === '' || result === 'pending') {
      return
    }

    setResult('pending')
    setComposite(null)

    try {
      const r = await combine(currentClue.id, selectedClueId)

      if (!r.success) {
        setFailMessage(r.message ?? '')
        setResult('failure')
        return
      }

      setComposite({
        name: r.name ?? '',
        surface: r.surface ?? '',
        implies: r.implies ?? null,
        points: r.points ?? 0,
      })
      setResult(r.already_done ? 'duplicate' : 'success')
    } catch (error) {
      showToast(
        error instanceof Error ? error.message : '겹쳐 보지 못했습니다.',
      )
      setResult('none')
    }
  }

  return (
    <div
      className="absolute"
      style={{
        left: 0,
        top: 0,

        width: 1440,
        height: 1024,

        zIndex: 99999,
      }}
    >
      {/* =========================================
          사건수첩 뒤쪽 어둡게
      ========================================= */}
      <button
        type="button"
        aria-label="겹쳐 보기 닫기"
        onClick={closeCombineSession}
        className="
          absolute
          cursor-default
          border-0
        "
        style={{
          left: 0,
          top: 0,

          width: 1440,
          height: 1024,

          backgroundColor:
            'rgba(0, 0, 0, 0.78)',

          zIndex: 0,
        }}
      />

      {/* =========================================
          팝업
      ========================================= */}
      <div
        className="
          absolute
          font-game-korean
        "
        style={{
          left: 365,
          top: 230,

          width: 710,
          height: 560,

          zIndex: 10,

          backgroundColor: '#0d0c0b',

          border:
            '2px solid #d8cdb9',

          color: '#e1d8c7',

          boxSizing: 'border-box',
        }}
      >
        {/* =====================================
            제목
        ===================================== */}
        <div
          className="absolute"
          style={{
            left: 55,
            top: 45,

            width: 550,

            color: '#e1d8c7',

            fontSize: 22,
            letterSpacing: '0.08em',
          }}
        >
          어느 단서와 겹칠까요?
        </div>

        {/* =====================================
            닫기
        ===================================== */}
        <button
          type="button"
          onClick={closeCombineSession}
          className="
            absolute
            cursor-pointer
            border-0
            bg-transparent
            font-game-korean
          "
          style={{
            right: 30,
            top: 25,

            color: '#e1d8c7',

            fontSize: 17,
            opacity: 0.6,
          }}
        >
          닫기
        </button>

        <div
          className="absolute font-game-korean"
          style={{
            right: 30,
            top: 68,
            color: '#9a8d72',
            fontSize: 16,
            letterSpacing: '0.06em',
          }}
        >
          남은 행동 {remainingTurns}
        </div>

        {/* =====================================
            단서 선택
        ===================================== */}
        <div
          className="
            absolute
            flex
            flex-wrap
            gap-[12px]
            overflow-y-auto
          "
          style={{
            left: 55,
            top: 105,

            width: 600,
            height: 145,
          }}
        >
          {availableClues.map(
            (clue) => {
              const isSelected =
                selectedClueId ===
                clue.id

              return (
                <button
                  key={clue.id}
                  type="button"
                  onClick={() =>
                    handleSelectClue(
                      clue.id,
                    )
                  }
                  className="
                    cursor-pointer
                    font-game-korean
                  "
                  style={{
                    minWidth: 125,
                    minHeight: 52,

                    padding:
                      '8px 18px',

                    border: isSelected
                      ? '1px solid #8b332c'
                      : '1px solid rgba(225, 216, 199, 0.4)',

                    backgroundColor:
                      isSelected
                        ? 'rgba(139, 51, 44, 0.3)'
                        : '#0d0c0b',

                    color: '#e1d8c7',

                    fontSize: 17,
                    letterSpacing:
                      '0.05em',
                  }}
                >
                  {clue.title}
                </button>
              )
            },
          )}
        </div>

        {/* =====================================
            결과
        ===================================== */}
        <div
          className="
            absolute
            flex
            items-center
            justify-center
            text-center
          "
          style={{
            left: 55,
            top: 285,

            width: 600,
            height: 85,

            border:
              '1px solid rgba(225, 216, 199, 0.3)',

            color: '#e1d8c7',

            fontSize: 19,
            letterSpacing: '0.06em',
          }}
        >
          {result === 'pending' && <span>겹쳐 보는 중…</span>}

          {(result === 'success' || result === 'duplicate') && (
            <span>
              {composite?.name || '두 단서가 이어집니다.'}

              {result === 'duplicate' ? (
                <span
                  style={{
                    marginLeft: 12,
                    color: 'rgba(225, 216, 199, 0.5)',
                  }}
                >
                  이미 이어 본 것
                </span>
              ) : (
                composite !== null &&
                composite.points > 0 && (
                  <span
                    style={{
                      marginLeft: 12,
                      color: '#9b3a31',
                    }}
                  >
                    +{composite.points}점
                  </span>
                )
              )}
            </span>
          )}

          {result === 'failure' && (
            <span>
              {failMessage || '이 둘은 이어지지 않습니다.'}
            </span>
          )}
        </div>

        {/* =====================================
            현재 선택한 조합
        ===================================== */}
        {selectedClue !== undefined && (
          <div
            className="
              absolute
              text-center
            "
            style={{
              left: 55,
              top: 400,

              width: 600,

              color: '#e1d8c7',

              fontSize: 15,
              letterSpacing: '0.05em',
              opacity: 0.5,
            }}
          >
            {currentClue.title}

            {'  +  '}

            {selectedClue.title}
          </div>
        )}

        {/* =====================================
            겹쳐 본다 버튼
        ===================================== */}
        <button
          type="button"
          onClick={handleCombine}
          disabled={
            selectedClueId === ''
          }
          className="
            absolute
            font-game-korean
          "
          style={{
            left: 230,
            bottom: 45,

            width: 250,
            height: 60,

            border:
              selectedClueId === ''
                ? '1px solid rgba(225, 216, 199, 0.2)'
                : '1px solid #8b332c',

            backgroundColor:
              selectedClueId === ''
                ? '#0d0c0b'
                : 'rgba(139, 51, 44, 0.2)',

            color:
              selectedClueId === ''
                ? 'rgba(225, 216, 199, 0.3)'
                : '#e1d8c7',

            cursor:
              selectedClueId === ''
                ? 'default'
                : 'pointer',

            fontSize: 20,
            letterSpacing: '0.1em',
          }}
        >
          겹쳐 본다
        </button>
      </div>
    </div>
  )
}
