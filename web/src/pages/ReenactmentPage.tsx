import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useGameStore } from '../store/gameStore'

const CUT_COUNT = 6
const REVEAL_INTERVAL_MS = 1100

const PREVIEW_CUTS = [
  ['결심', '범인은 마지막까지 남아 계획을 실행하기로 결심했다.'],
  ['접근', '사람들의 시선이 끊긴 틈에 사건 장소로 접근했다.'],
  ['범행', '준비해 둔 도구를 사용해 범행을 실행했다.'],
  ['트릭', '시간과 동선을 속이기 위한 장치를 남겼다.'],
  ['위장', '현장을 우연한 사고처럼 보이도록 꾸몄다.'],
  ['아침', '아무 일도 없었던 사람처럼 모두 앞에 다시 나타났다.'],
].map(([title, text], index) => ({
  cut: index + 1,
  title,
  text,
  image: '',
  duration_sec: 1,
}))

export default function ReenactmentPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const scenario = useGameStore((state) => state.scenario)
  const [revealedCount, setRevealedCount] = useState(0)

  const preview = location.pathname === '/reenactment-preview'
  const cuts = useMemo(() => {
    if (preview) return PREVIEW_CUTS
    return scenario?.ui.murder_reenactment?.cuts?.slice(0, CUT_COUNT) ?? []
  }, [preview, scenario])

  /* 재연은 건너뛸 수 없다. 실제 컷을 일정 간격으로 하나씩 연다. */
  useEffect(() => {
    if (cuts.length === 0 || revealedCount >= cuts.length) return

    const timer = window.setTimeout(() => {
      setRevealedCount((count) => Math.min(count + 1, cuts.length))
    }, REVEAL_INTERVAL_MS)

    return () => window.clearTimeout(timer)
  }, [cuts.length, revealedCount])

  const allSixCutsRevealed =
    cuts.length >= CUT_COUNT && revealedCount >= CUT_COUNT

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-black font-game-korean text-game-ivory">
      <img
        src="/assets/icons/title-background.svg"
        alt=""
        className="absolute inset-0 h-full w-full object-fill"
      />

      <header className="absolute left-[70px] top-[34px] flex h-[82px] w-[1300px] items-center justify-center border-b border-white/30">
        <div className="mr-[28px] h-px w-[100px] bg-white/35" />
        <h1 className="m-0 text-[42px] tracking-[0.16em]">범행 재연</h1>
        <div className="ml-[28px] h-px w-[100px] bg-white/35" />
      </header>

      {/*
        ★칸을 그림 비율에 맞춘다 (2026-08-30, 제보 — "재연·결과 이미지 크기 잘 맞춰 주라").

          재연 컷은 1045×600 (가로 1.74:1) 인데 칸이 391×346 (1.13:1) 이었다.
          object-cover 로 채우니 **양옆이 크게 잘려** 나갔다 — 컷마다 무엇을
          보여 주려는지가 가장자리에 있는데 그게 사라진 것이다.

          폭을 늘리고(1320) 높이를 비율로 잡는다 —
            칸 428 × 246 (428 / 1.742 = 246). 두 줄이면 510.
      */}
      {cuts.length > 0 ? (
        <section className="absolute left-[60px] top-[164px] grid h-[510px] w-[1320px] grid-cols-3 grid-rows-2 gap-[18px]">
          {Array.from({ length: CUT_COUNT }, (_, index) => {
            const cut = cuts[index]
            const revealed = index < revealedCount && cut !== undefined

            return (
              <article
                key={cut?.cut ?? index}
                className="relative overflow-hidden border border-[#806c45]/65 bg-black"
              >
                {cut !== undefined && (
                  <>
                    {cut.image !== '' && (
                      <img
                        src={cut.image}
                        alt={cut.title}
                        className="absolute inset-0 h-full w-full object-cover"
                      />
                    )}
                    {cut.image === '' && (
                      <div
                        className="absolute inset-0"
                        style={{
                          background:
                            index % 2 === 0
                              ? 'radial-gradient(circle at 38% 35%, #473523 0%, #17110c 48%, #050403 100%)'
                              : 'radial-gradient(circle at 62% 38%, #3d2925 0%, #15100d 48%, #050403 100%)',
                        }}
                      />
                    )}
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black via-black/80 to-transparent px-[18px] pb-[14px] pt-[52px]">
                      <div className="text-[19px] tracking-[0.1em] text-game-ivory">
                        {index + 1}. {cut.title}
                      </div>
                      <p className="mt-[6px] line-clamp-2 text-[14px] leading-[1.5] tracking-[0.03em] text-game-ivory/75">
                        {cut.text}
                      </p>
                    </div>
                  </>
                )}

                <div
                  className={`absolute inset-0 bg-black transition-opacity duration-700 ${
                    revealed ? 'pointer-events-none opacity-0' : 'opacity-100'
                  }`}
                />
              </article>
            )
          })}
        </section>
      ) : (
        <div className="absolute inset-0 flex items-center justify-center text-[20px] tracking-[0.06em] text-game-ivory/60">
          {/*
            ★못 맞히면 재연도 열리지 않는다 (2026-08-31, 팀 결정 — 가은).
              그때는 지목 화면이 여기를 건너뛰고 엔딩으로 보낸다. 그래도
              주소로 바로 들어올 수 있으니, 고장이 아니라는 것만 말해 둔다.
          */}
          범행 재연은 밝혀낸 밤에만 열립니다.
        </div>
      )}

      <div className="absolute bottom-[64px] left-0 flex w-full justify-center">
        <button
          type="button"
          disabled={!allSixCutsRevealed}
          onClick={() => navigate(preview ? '/' : '/ending')}
          /* yellow_button.svg 비율 1845:482 — 222×58 이어야 테두리가 상자를 채운다 */
          className="relative h-[58px] w-[222px] cursor-pointer border-0 bg-transparent p-0 disabled:cursor-default"
        >
          {allSixCutsRevealed && (
            <img
              src="/assets/icons/yellow_button.svg"
              alt=""
              className="pointer-events-none absolute inset-0 h-full w-full object-fill"
            />
          )}
          <span
            className={`pointer-events-none absolute inset-0 flex items-center justify-center whitespace-nowrap text-[20px] tracking-[0.08em] transition-opacity ${
              allSixCutsRevealed ? 'text-game-ivory opacity-100' : 'text-game-ivory/20 opacity-0'
            }`}
          >
            다음 &gt;
          </span>
        </button>
      </div>
    </main>
  )
}
