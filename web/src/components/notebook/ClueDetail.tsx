import { useState } from 'react'

import type { NotebookClue } from '../../pages/NotebookPage'

import ClueCombineModal from './ClueCombineModal.tsx'

type ClueDetailProps = {
  clue: NotebookClue
  clues: NotebookClue[]
}

export default function ClueDetail({
  clue,
  clues,
}: ClueDetailProps) {
  const [
    isCombineOpen,
    setIsCombineOpen,
  ] = useState(false)

  return (
    <>
      <section
        className="absolute"
        style={{
          left: 420,
          top: 100,

          width: 525,
          height: 850,
        }}
      >
        {/* 카드 배경 */}
        <img
          src="/assets/icons/person_card.svg"
          alt=""
          className="
            absolute
            inset-0
            h-full
            w-full
            object-fill
          "
        />

        {/* =====================================
            단서 이미지
        ===================================== */}
        <div
          className="absolute overflow-hidden"
          style={{
            left: '50%',
            top: 115,

            width: 300,
            height: 300,

            transform:
              'translateX(-50%)',
          }}
        >
          {clue.image !== '' ? (
            <img
              src={clue.image}
              alt={clue.title}
              className="
                h-full
                w-full
                object-cover
              "
            />
          ) : (
            <div
              className="
                flex
                h-full
                w-full
                items-center
                justify-center
                bg-black/30
                font-game-korean
                text-game-ivory
              "
              style={{
                fontSize: 22,
                opacity: 0.3,
              }}
            >
              단서 이미지
            </div>
          )}
        </div>

        {/* 종류 */}
        <div
          className="
            absolute
            flex
            font-game-korean
            text-game-ivory
          "
          style={{
            left: 65,
            top: 435,
            width: 395,
            fontSize: 17,
            letterSpacing: '0.07em',
          }}
        >
          <span
            style={{
              width: 125,
              opacity: 0.55,
            }}
          >
            종류
          </span>

          <span>{clue.type}</span>
        </div>

        {/* 장소 */}
        <div
          className="
            absolute
            flex
            font-game-korean
            text-game-ivory
          "
          style={{
            left: 65,
            top: 475,
            width: 395,
            fontSize: 17,
            letterSpacing: '0.07em',
          }}
        >
          <span
            style={{
              width: 125,
              opacity: 0.55,
            }}
          >
            장소
          </span>

          <span>{clue.location}</span>
        </div>

        {/* 획득 방법 */}
        <div
          className="
            absolute
            flex
            font-game-korean
            text-game-ivory
          "
          style={{
            left: 65,
            top: 515,
            width: 395,
            fontSize: 17,
            letterSpacing: '0.07em',
          }}
        >
          <span
            style={{
              width: 125,
              opacity: 0.55,
            }}
          >
            획득 방법
          </span>

          <span
            style={{
              flex: 1,
              minWidth: 0,
              lineHeight: 1.45,
              overflowWrap: 'anywhere',
            }}
          >
            {clue.acquisitionMethod}
          </span>
        </div>

        {/* 구분선 */}
        <div
          className="absolute bg-game-ivory"
          style={{
            left: 65,
            top: 575,

            width: 395,
            height: 1,

            opacity: 0.25,
          }}
        />

        {/* =====================================
            개요
        ===================================== */}
        <div
          className="
            absolute
            font-game-korean
            text-game-ivory
          "
          style={{
            left: 65,
            top: 595,

            width: 395,
          }}
        >
          <div
            style={{
              marginBottom: 18,
              fontSize: 17,
              letterSpacing: '0.1em',
              opacity: 0.55,
            }}
          >
            개요
          </div>

          <div
            style={{
              fontSize: 17,
              lineHeight: 1.9,
              letterSpacing: '0.05em',
              maxHeight: 78,
              overflowY: 'auto',
              paddingRight: 8,
            }}
          >
            {clue.description}
          </div>
        </div>

        {/* =====================================
            겹쳐 본다

            카드 우측 하단
        ===================================== */}
        <button
          type="button"
          onClick={() =>
            setIsCombineOpen(true)
          }
          className="
            absolute
            z-10
            cursor-pointer
            border-0
            bg-transparent
            font-game-korean
            tracking-[0.1em]
            text-game-ivory
          "
          style={{
            right: 55,
            bottom: 110,

            width: 180,
            height: 50,

            fontSize: 18,
            textAlign: 'right',
          }}
        >
          겹쳐 본다 &gt;
        </button>
      </section>

      {/* =====================================
          단서 조합 팝업
      ===================================== */}
      {isCombineOpen && (
        <ClueCombineModal
          currentClue={clue}
          clues={clues}
          onClose={() =>
            setIsCombineOpen(false)
          }
        />
      )}
    </>
  )
}
