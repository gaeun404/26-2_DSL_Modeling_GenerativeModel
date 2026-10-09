import { useGameStore } from '../../store/gameStore'

type ClueMemoPanelProps = {
  clueId: string
  clueTitle: string
}

export default function ClueMemoPanel({
  clueId,
  clueTitle,
}: ClueMemoPanelProps) {
  const currentMemo = useGameStore(
    (state) => state.clueMemos[clueId] ?? '',
  )
  const setClueMemo = useGameStore(
    (state) => state.setClueMemo,
  )

  return (
    <section
      className="absolute"
      style={{
        // ⭐ MemoPanel과 동일
        left: 965,
        top: 125,

        width: 440,
        height: 850,
      }}
    >
      {/* =====================================
          old_paper.svg

          네가 현재 맞춘 값 그대로
      ===================================== */}
      <div
        className="absolute"
        style={{
          left: 30,
          top: 10,

          width: 420,
          height: 720,

          transform:
            'scaleX(1.7) scaleY(1.9)',
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
            단서별 메모
        ================================= */}
        <textarea
          value={currentMemo}
          onChange={(event) =>
            setClueMemo(clueId, event.target.value)
          }
          placeholder={`${clueTitle}에 대한 메모를 작성해 보세요.`}
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
            // ⭐ 기존 MemoPanel 그대로
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
