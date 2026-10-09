import type { NotebookPerson } from '../../pages/NotebookPage'

type PersonChoiceProps = {
  person: NotebookPerson
  selected: boolean
  onClick: () => void
}

export default function PersonChoice({
  person,
  selected,
  onClick,
}: PersonChoiceProps) {
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
        width: 350,
        height: 155,
      }}
    >
      {/* 선택 여부에 따라 SVG 변경 */}
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
          인물 사진
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
        {person.image ? (
          <img
            src={person.image}
            alt={person.name}
            className="h-full w-full object-cover"
            style={{
              WebkitMaskImage:
                'radial-gradient(ellipse at center, black 78%, transparent 100%)',
              maskImage:
                'radial-gradient(ellipse at center, black 78%, transparent 100%)',
            }}
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
              text-white/30
            "
            style={{
              fontSize: 16,
            }}
          >
            사진
          </div>
        )}
      </div>

      {/* 이름 */}
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
        {person.name}
      </div>

      {/* 신분 */}
      <div
        className="
          absolute
          whitespace-normal
          font-game-korean
          tracking-[0.07em]
          text-game-ivory
        "
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
        {person.status}
      </div>
    </button>
  )
}
