import { useState } from 'react'

type Evidence = {
  id: string
  title: string
}

type EvidencePickerModalProps = {
  evidences: Evidence[]
  onClose: () => void
  onConfirm: (evidenceId: string) => void
}

export default function EvidencePickerModal({
  evidences,
  onClose,
  onConfirm,
}: EvidencePickerModalProps) {
  const [selectedEvidenceId, setSelectedEvidenceId] =
    useState('')

  const handleConfirm = () => {
    if (selectedEvidenceId === '') {
      return
    }

    onConfirm(selectedEvidenceId)
  }

  return (
    <>
      {/* =========================================
          팝업 뒤 어두운 배경

          바깥을 누르면 닫힘
      ========================================= */}
      <button
        type="button"
        aria-label="증거 선택 닫기"
        onClick={onClose}
        className="absolute inset-0 z-40 cursor-default border-0 bg-black/70"
      />

      {/* =========================================
          증거 선택 팝업
      ========================================= */}
      <div
        className="absolute z-50"
        style={{
          left: 395,
          top: 225,
          width: 650,
          height: 570,

          backgroundColor:
            'rgba(10, 9, 7, 0.97)',

          border:
            '1px solid rgba(225,216,199,0.45)',
        }}
      >
        {/* 제목 */}
        <div
          className="absolute w-full text-center font-game-korean text-game-ivory"
          style={{
            top: 50,
            fontSize: 26,
            letterSpacing: '0.08em',
          }}
        >
          들이댈 단서를 고르세요.
        </div>

        {/* =========================================
            단서 목록

            단서가 많아지면 스크롤
        ========================================= */}
        <div
          className="absolute overflow-y-auto"
          style={{
            left: 75,
            top: 125,
            width: 500,
            height: 260,
          }}
        >
          <div className="flex flex-col gap-[14px]">
            {evidences.map(
              (evidence) => {
                const isSelected =
                  selectedEvidenceId ===
                  evidence.id

                return (
                  <button
                    key={evidence.id}
                    type="button"
                    onClick={() =>
                      setSelectedEvidenceId(
                        evidence.id,
                      )
                    }
                    className="w-full cursor-pointer font-game-korean text-game-ivory"
                    style={{
                      minHeight: 58,

                      border: isSelected
                        ? '1px solid #8b332c'
                        : '1px solid rgba(225,216,199,0.35)',

                      backgroundColor:
                        isSelected
                          ? 'rgba(139,51,44,0.14)'
                          : 'rgba(0,0,0,0.3)',

                      fontSize: 20,
                      letterSpacing:
                        '0.06em',
                    }}
                  >
                    {evidence.title}
                  </button>
                )
              },
            )}
          </div>
        </div>

        {/* =========================================
            들이댄다
        ========================================= */}
        <button
          type="button"
          disabled={
            selectedEvidenceId === ''
          }
          onClick={handleConfirm}
          className="absolute font-game-korean"
          style={{
            left: 175,
            top: 420,
            width: 300,
            height: 65,

            border:
              selectedEvidenceId === ''
                ? '1px solid rgba(225,216,199,0.2)'
                : '1px solid #8b332c',

            backgroundColor:
              selectedEvidenceId === ''
                ? 'rgba(0,0,0,0.3)'
                : 'rgba(139,51,44,0.18)',

            color:
              selectedEvidenceId === ''
                ? 'rgba(225,216,199,0.25)'
                : '#e1d8c7',

            cursor:
              selectedEvidenceId === ''
                ? 'default'
                : 'pointer',

            fontSize: 22,
            letterSpacing: '0.1em',
          }}
        >
          들이댄다
        </button>

        {/* 설명 */}
        <div
          className="absolute w-full text-center font-game-korean text-game-ivory"
          style={{
            bottom: 35,
            fontSize: 15,
            opacity: 0.45,
            letterSpacing: '0.05em',
          }}
        >
          이 단서가 숨겨진 비밀과 관련되어 있다면
          새로운 진술을 들을 수 있습니다.
        </div>
      </div>
    </>
  )
}
