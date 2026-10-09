import { useEffect } from 'react'

import { useGameStore } from '../../store/gameStore'

/*
  그날 밤 시간표 (S-19).

  ★왜 (2026-08-29, 시연 제보) — "타임스탬프는 어떻게 보나유?"
    시나리오는 그날 밤을 분 단위로 갖고 있지만, 서버는 **아는 것만** 내려 준다 —
    모두가 아는 공지와, 만난 사람이 제 입으로 한 말. CCTV·영수증처럼 한 사람을
    겨누는 기록은 올라오지 않는다. 그건 찾아내야 할 몫이다.

    그래서 비어 있는 시각이 곧 "아직 못 밝힌 자리"가 된다.
*/
export default function TimelinePanel() {
  const rows = useGameStore((state) => state.timeline)
  const note = useGameStore((state) => state.timelineNote)
  const loadTimeline = useGameStore((state) => state.loadTimeline)

  useEffect(() => {
    void loadTimeline()
  }, [loadTimeline])

  return (
    <section
      className="absolute font-game-korean text-game-ivory"
      style={{ left: 70, top: 130, width: 1300, height: 770 }}
    >
      <div className="mb-[18px] flex items-baseline justify-between border-b border-game-parchment/25 pb-[12px]">
        <h2 className="m-0 text-[26px] tracking-[0.1em]">그날 밤</h2>
        <span className="text-[15px] tracking-[0.06em] text-game-ivory/45">
          밝혀낸 {rows.length}건
        </span>
      </div>

      {rows.length === 0 ? (
        <p className="mt-[120px] text-center text-[20px] leading-[1.8] text-game-ivory/40">
          아직 시간 위에 세울 것이 없습니다.
          <br />
          사람을 만나고 방을 뒤지면 하나씩 채워집니다.
        </p>
      ) : (
        <ol className="m-0 max-h-[660px] list-none overflow-y-auto p-0 pr-[10px]">
          {rows.map((row, index) => (
            <li
              key={`${row.time}-${index}`}
              className="flex gap-[26px] border-b border-white/8 py-[16px]"
            >
              <span className="w-[92px] shrink-0 font-serif text-[22px] tracking-[0.06em] text-game-gold">
                {row.time}
              </span>

              <span className="w-[120px] shrink-0 text-[18px] text-game-ivory/85">
                {row.who}
              </span>

              <span className="min-w-0 flex-1 break-keep text-[18px] leading-[1.7] text-game-ivory/90">
                {row.text}
              </span>

              <span
                className={`w-[92px] shrink-0 text-right text-[14px] tracking-[0.04em] ${
                  row.source === '본인 주장'
                    ? 'text-game-red-light/80'
                    : 'text-game-ivory/35'
                }`}
              >
                {row.source}
              </span>
            </li>
          ))}
        </ol>
      )}

      {note !== '' && (
        <p className="mt-[16px] text-[15px] tracking-[0.05em] text-game-ivory/40">
          {note}
        </p>
      )}
    </section>
  )
}
