import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import StoryTextFrame from '../components/story/StoryTextFrame'
import { getRevealPages } from '../data/scenarioAdapter'
import { useGameStore } from '../store/gameStore'

const escapeRegExp = (value: string) =>
  value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

export default function RevealPage() {
  const navigate = useNavigate()
  const scenario = useGameStore((state) => state.scenario)
  const [currentPage, setCurrentPage] = useState(0)
  const [highlightDecisiveClues, setHighlightDecisiveClues] =
    useState(false)

  const pages = getRevealPages(scenario) ?? []

  /* 못 맞혀서 감춘 것이라면 그 사정을 말해 준다 */
  const withheldReason = useGameStore(
    (state) => state.gameResult?.withheld?.reason,
  )

  const decisiveClueTerms = useMemo(() => {
    if (scenario === null) return []

    const decisiveIds = new Set(
      scenario.clue_graph
        .filter((clue) => clue.decisive)
        .map((clue) => clue.clue_id),
    )

    return scenario.ui.clue_cards
      .filter((clue) => decisiveIds.has(clue.clue_id))
      .flatMap((clue) => [clue.name, clue.type])
      .map((term) => term.trim())
      .filter(
        (term, index, terms) =>
          term.length > 1 && terms.indexOf(term) === index,
      )
      .sort((a, b) => b.length - a.length)
  }, [scenario])

  if (pages.length === 0) {
    return (
      <main className="relative flex h-[1024px] w-[1440px] items-center justify-center overflow-hidden bg-black font-game-korean">
        <img
          src="/assets/icons/title-background.svg"
          alt=""
          className="absolute inset-0 h-full w-full object-fill"
        />
        {/*
          ★빈 화면과 **감춘 화면**은 다르다 (2026-08-31, 팀 결정 — 가은).
            못 맞히면 진상이 아예 안 열린다. 그때 「불러오지 못했습니다」가
            뜨면 고장으로 읽힌다. 감춘 것이라면 그렇다고 말하고 엔딩으로 보낸다.
        */}
        <div className="relative z-10 max-w-[900px] px-[60px] text-center">
          <h1 className="m-0 text-[38px] tracking-[0.14em] text-game-ivory">
            사건의 진상
          </h1>

          <p className="mt-[36px] text-[20px] leading-[1.8] tracking-[0.06em] text-game-ivory/60">
            {withheldReason || '진상 데이터를 불러오지 못했습니다.'}
          </p>

          <button
            type="button"
            onClick={() => navigate('/ending')}
            className="mt-[44px] h-[64px] w-[240px] cursor-pointer border border-white/25 bg-black/45 font-game-korean text-[20px] tracking-[0.08em] text-game-ivory/80 transition-colors hover:border-game-parchment hover:text-game-ivory"
          >
            그 밤의 끝으로
          </button>
        </div>
      </main>
    )
  }

  const current = pages[currentPage]
  const isLastPage = currentPage === pages.length - 1

  const highlightedStory = (() => {
    if (!highlightDecisiveClues || decisiveClueTerms.length === 0) {
      return current.text
    }

    const pattern = new RegExp(
      `(${decisiveClueTerms.map(escapeRegExp).join('|')})`,
      'g',
    )

    return current.text.split(pattern).map((part, index) =>
      decisiveClueTerms.includes(part) ? (
        <span key={`${part}-${index}`} className="text-[#9b1c1c]">
          {part}
        </span>
      ) : (
        part
      ),
    )
  })()

  const handleNext = () => {
    if (isLastPage) {
      navigate('/reenactment')
      return
    }

    setCurrentPage((previous) => previous + 1)
  }

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-black">
      <img
        src="/assets/icons/title-background.svg"
        alt=""
        className="absolute left-0 top-0 h-[1024px] w-[1440px] object-fill"
      />

      {/*
        ★그림이 없는 박에는 액자도 그리지 않는다 (2026-08-30).

          진상은 **말로 밝히는 자리**다. 여섯 컷은 바로 뒤 재연이 통째로
          가져가므로, 여기에 같은 그림을 또 얹으면 「that night은 왜 또 나오지?」가
          된다. 그래서 얼굴은 범인이 드러나는 박 한 곳에만 있다.

          그런데 액자는 늘 그려지고 있었다 — 여섯 쪽 중 다섯 쪽이 **빈 액자**다.
          빈 액자는 "안 불러와졌나" 싶게 만든다. 그림이 있을 때만 액자를 두고,
          없으면 박 이름만 큼직하게 둔다.
      */}
      <div className="absolute left-[231px] top-[22px] h-[560px] w-[977px]">
        {current.image !== '' ? (
          <>
            <img
              src={current.image}
              alt=""
              className="absolute left-[19px] top-[19px] h-[522px] w-[939px] object-cover"
            />
            <img
              src="/assets/icons/ImageFrame.svg"
              alt=""
              className="pointer-events-none absolute inset-0 h-full w-full object-fill"
            />
            <div className="absolute left-[40px] top-[34px] z-10 font-game-korean text-[18px] tracking-[0.12em] text-game-ivory/70">
              사건의 진상 · {current.beatTitle}
            </div>
          </>
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center font-game-korean">
            <p className="m-0 font-serif text-[16px] tracking-[0.34em] text-game-ivory/35">
              사건의 진상
            </p>
            <p className="m-0 mt-[22px] text-[46px] tracking-[0.2em] text-game-parchment">
              {current.beatTitle}
            </p>
            <div className="mt-[30px] h-px w-[220px] bg-game-parchment/25" />
          </div>
        )}
      </div>

      <StoryTextFrame
        story={highlightedStory}
        width={1000}
      />

      <div className="absolute left-[126px] top-[943px] flex w-[1124px] items-center justify-end gap-[6px]">
        <button
          type="button"
          onClick={() =>
            setHighlightDecisiveClues((currentValue) => !currentValue)
          }
          className={`h-[64px] w-[220px] cursor-pointer border-0 bg-transparent font-game-korean text-[18px] tracking-[0.06em] ${
            highlightDecisiveClues
              ? 'text-[#9b1c1c]'
              : 'text-game-ivory/70'
          }`}
        >
          결정타 단서 강조
        </button>

        <button
          type="button"
          onClick={handleNext}
          /* yellow_button.svg 비율 1845:482 — 222×58 이어야 테두리가 상자를 채운다 */
          className="relative left-[32px] h-[58px] w-[222px] cursor-pointer border-0 bg-transparent p-0"
        >
          <img
            src="/assets/icons/yellow_button.svg"
            alt=""
            className="absolute inset-0 h-full w-full object-fill"
          />
          <span className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean text-[20px] tracking-[0.08em] text-game-ivory">
            다음 &gt;
          </span>
        </button>
      </div>
    </main>
  )
}
