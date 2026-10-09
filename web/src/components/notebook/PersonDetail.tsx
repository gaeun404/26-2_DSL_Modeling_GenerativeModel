import { useNavigate } from 'react-router-dom'

import type { NotebookPerson } from '../../pages/NotebookPage'

type PersonDetailProps = {
  person: NotebookPerson
}

export default function PersonDetail({
  person,
}: PersonDetailProps) {
  const navigate = useNavigate()

  /* =====================================
      심문하기

      현재 임시 연결:
      suspect-1 → place-1
      suspect-2 → place-2
      suspect-3 → place-3
      suspect-4 → place-4
      suspect-5 → place-5

      TODO(API):
      나중에는 실제 용의자의 장소 ID 사용
  ===================================== */
  /*
    ★인물 id 로 곧장 간다 (2026-08-29, 시연 제보).
      제보: "수첩에서 용의자를 고르고 「심문하기」를 누르면
             「이 곳에는 만날 사람이 없습니다」가 뜬다."
      여기서 'suspect-3' → 'place-3' 같은 **가짜 장소 id를 지어내고** 있었다.
      실제 id 는 C1…C5 이고, 노하람·임세준은 아예 제 방이 없다.
      심문 화면은 인물 id 를 그대로 받는다.
  */
  const handleInterrogate = () => {
    navigate(`/interrogate/${person.id}`, {
      state: { from: 'notebook' },
    })
  }

  return (
    <section
      className="absolute"
      style={{
        left: 420,
        top: 100,
        width: 525,
        height: 850,
      }}
    >
      {/* =====================================
          PERSON CARD
      ===================================== */}
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
          인물 사진
      ===================================== */}
      <div
        className="
          absolute
          overflow-hidden
        "
        style={{
          left: '50%',
          top: 115,
          width: 300,
          height: 330,
          transform: 'translateX(-50%)',
        }}
      >
        {person.image ? (
          <img
            src={person.image}
            alt={person.name}
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
              text-white/30
            "
            style={{
              fontSize: 22,
            }}
          >
            인물 사진
          </div>
        )}
      </div>

      {/* =====================================
          인물 설명
      ===================================== */}
      <div
        className="
          absolute
          font-game-korean
          tracking-[0.07em]
          text-game-ivory
        "
        style={{
          left: 60,
          top: 495,
          width: 405,
          height: 210,
          fontSize: 21,
          lineHeight: 2,
        }}
      >
        {person.description}
      </div>

      {/* =====================================
          심문하기

          카드 우측 하단
      ===================================== */}
      <button
        type="button"
        onClick={handleInterrogate}
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
          height: 55,
          fontSize: 21,
          textAlign: 'right',
        }}
      >
        심문하기 &gt;
      </button>
    </section>
  )
}
