import type { NotebookClue } from '../../pages/NotebookPage'

type ClueChoiceProps = {
  clue: NotebookClue
  selected: boolean
  onClick: () => void
}

export default function ClueChoice({
  clue,
  selected,
  onClick,
}: ClueChoiceProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="
        relative
        shrink-0
        overflow-hidden
        border-0
        bg-transparent
        p-0
        cursor-pointer
      "
      style={{
        // PersonChoice와 동일
        width: 350,
        height: 155,
      }}
    >
      {/* =====================================
          선택 여부에 따라 붉은색 변경

          TODO:
          나중에 단서 전용 SVG가 생기면
          여기 경로만 바꾸면 됨
      ===================================== */}
      <img
        src={
          selected
            ? '/assets/icons/red_person_choice.svg'
            : '/assets/icons/person_choice.svg'
        }
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
          PersonChoice 사진과 동일한 위치/크기
      ===================================== */}
      <div
        className="absolute overflow-hidden"
        style={{
          left: 18,
          top: 15,

          width: 110,
          height: 125,
        }}
      >
        {clue.image ? (
          <img
            src={clue.image}
            alt={clue.title}
            className="h-full w-full object-cover"
            style={{
              WebkitMaskImage:
                'radial-gradient(ellipse at center, black 78%, transparent 100%)',
              maskImage:
                'radial-gradient(ellipse at center, black 78%, transparent 100%)',
            }}
          />
        ) : (
          <div className="h-full w-full bg-black/30" />
        )}
      </div>

      {/* =====================================
          단서 이름
      ===================================== */}
      <div
        className="
          absolute
          whitespace-normal
          font-game-korean
          tracking-[0.08em]
          text-game-ivory
        "
        style={{
          left: 155,
          top: 27,
          right: '0.4cm',

          fontSize: 27,
          lineHeight: 1.25,
          overflowWrap: 'anywhere',
          textAlign: 'left',
        }}
      >
        {clue.title}
      </div>

      {/* 단서 종류 — 인물 카드의 신분 위치 */}
      <div
        className="absolute whitespace-normal font-game-korean tracking-[0.07em] text-[#8a3830]"
        style={{
          left: 155,
          top: 72,
          right: '0.4cm',
          bottom: '0.4cm',
          fontSize: 18,
          lineHeight: 1.3,
          overflowWrap: 'anywhere',
          overflowY: 'auto',
          textAlign: 'left',
        }}
      >
        {clue.type}
      </div>
    </button>
  )
}
