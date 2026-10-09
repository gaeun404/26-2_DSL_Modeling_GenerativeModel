import { useState } from 'react'

import type { ClueCard } from '../../types/scenario'

/*
  라운드가 바뀌면서 손에 들어온 단서를 보여 준다.

  ★왜 (2026-08-29, 시연 제보) — "라운드가 바뀌면서 나오는 새 단서를 확인할 수 없다."
    저절로 들어오는 증언과 이벤트가 준 단서가 수첩에 조용히 쌓이기만 했다.
    무엇이 새로 들어왔는지 모르니, 라운드가 바뀐 것이 사건이 아니라 사고처럼 느껴졌다.

  한 장씩, 몇 장 중 몇 번째인지 적어 가며 보여 준다.
*/
type NewCluesOverlayProps = {
  clues: ClueCard[]
  onClose: () => void
}

export default function NewCluesOverlay({
  clues,
  onClose,
}: NewCluesOverlayProps) {
  const [index, setIndex] = useState(0)

  const clue = clues[index]
  const isLast = index >= clues.length - 1

  if (!clue) {
    return null
  }

  return (
    <div
      className="absolute inset-0 z-[120] flex items-center justify-center font-game-korean"
      style={{ backgroundColor: 'rgba(0,0,0,0.82)' }}
    >
      <div
        className="relative flex flex-col"
        style={{
          width: 820,
          minHeight: 540,
          border: '1px solid rgba(160,132,80,0.75)',
          backgroundColor: 'rgba(14,13,11,0.98)',
          boxShadow: '0 0 44px rgba(210,175,100,0.16)',
          padding: '30px 40px 34px',
        }}
      >
        <div className="flex items-baseline justify-between">
          <span
            className="tracking-[0.14em]"
            style={{ fontSize: 20, color: '#9b1c1c' }}
          >
            밤이 바뀌며 알게 된 것
          </span>
          {clues.length > 1 && (
            <span className="text-[17px] tracking-[0.08em] text-game-gold">
              {index + 1} / {clues.length}
            </span>
          )}
        </div>

        <div className="mt-[18px] flex gap-[26px]">
          {clue.image !== '' && (
            <img
              src={clue.image}
              alt={clue.name}
              className="shrink-0 object-cover"
              style={{
                width: 300,
                height: 190,
                border: '1px solid rgba(128,108,69,0.7)',
              }}
            />
          )}

          <div className="min-w-0 flex-1">
            <div
              className="leading-[1.3] tracking-[0.05em] text-game-ivory"
              style={{ fontSize: 28 }}
            >
              {clue.name || clue.type}
            </div>

            <dl className="mt-[16px] grid grid-cols-[76px_1fr] gap-x-[14px] gap-y-[8px] text-[15px] leading-[1.5]">
              {[
                ['종류', clue.type],
                ['획득 장소', clue.acquired_place],
                ['획득 방법', clue.acquired_method],
              ]
                .filter(([, value]) => Boolean(value))
                .map(([label, value]) => (
                  <div key={label} className="contents">
                    <dt className="text-game-gold/85">{label}</dt>
                    <dd className="m-0 text-game-muted">{value}</dd>
                  </div>
                ))}
            </dl>
          </div>
        </div>

        <p
          className="mt-[24px] flex-1 whitespace-pre-line leading-[1.85] tracking-[0.02em] text-game-ivory"
          style={{ fontSize: 19 }}
        >
          {clue.description}
        </p>

        <button
          type="button"
          onClick={() => (isLast ? onClose() : setIndex(index + 1))}
          className="mt-[22px] cursor-pointer self-end border border-game-parchment/50 bg-[#171512] px-[38px] py-[13px] text-[21px] tracking-[0.1em] text-game-ivory"
        >
          {isLast ? '조사를 이어간다' : '다음 단서 →'}
        </button>
      </div>
    </div>
  )
}
