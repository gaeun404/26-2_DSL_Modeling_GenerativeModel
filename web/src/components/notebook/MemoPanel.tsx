import { useGameStore } from '../../store/gameStore'

type MemoPanelProps = {
  personId: string
  personName: string
}

export default function MemoPanel({
  personId,
  personName,
}: MemoPanelProps) {
  const currentMemo = useGameStore(
    (state) => state.personMemos[personId] ?? '',
  )
  const setPersonMemo = useGameStore(
    (state) => state.setPersonMemo,
  )

  return (
    <section
      className="absolute"
      style={{
        left: 965,
        top: 125,

        width: 440,
        height: 850,
      }}
    >
    

      {/* =====================================
          old_paper.svg
      ===================================== */}
      <div
        className="absolute"
        style={{
          left: 30,
          top: 10,

          width: 420,
          height: 720,

          transform: 'scaleX(1.7) scaleY(1.9)'
        }}
      >
        <img
          src="/assets/icons/old_paper.svg"
          alt=""
          className="
            absolute
            inset-0
            h-full
            w-full
            object-fill
          "
        />

        {/* =================================
            실제 메모 입력
        ================================= */}
        <textarea
          value={currentMemo}
          onChange={(event) =>
            setPersonMemo(personId, event.target.value)
          }
          placeholder={`${personName}에 대한 메모를 작성해 보세요.`}
          className="
            absolute
            resize-none
            border-0
            bg-transparent
            outline-none
            font-game-korean
            tracking-[0.06em]
            text-[#211a13]
            placeholder:text-[#493b2d]/55
          "
          style={{
            left: 100,
            top: 250,

            width: 330,
            height: 530,

            fontSize: 8.5,
            lineHeight: 1.8,

          }}
        />
      </div>
    </section>
  )
}
