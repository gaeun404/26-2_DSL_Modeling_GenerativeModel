import { useState } from 'react'


type InvestigationOption = {
  id: string

  /* 서버 /search 에 그대로 넘기는 번호 */
  index: number

  label: string
}


export type FoundClue = {
  id: string
  title: string
  description: string
  type: string
  place: string
  method: string
  image: string
}


/*
  서버가 돌려준 조사 결과.

  무엇이 나오는지는 프론트가 미리 알지 못한다 —
  조사한 뒤에야 채워진다. 문구도 서버가 짓는다.
*/
export type InvestigationResult = {
  /* 누른 칸 이름 */
  label: string

  /* 한 줄 요약 — 「단서 2장을 얻었다」 / 「이곳은 오늘 밤 달라진 것이 없다」 */
  message: string

  /* 이번 조사에 든 행동. 0이면 안 깎였다 */
  cost: number

  resultLines: string[]
  clues: FoundClue[]
}


type InvestigationPanelProps = {
  options: InvestigationOption[]
  characterName: string
  canTalk: boolean
  currentRound: number
  placeId: string
  investigatedActionIds: string[]
  remainingTurns: number
  pending: boolean
  result: InvestigationResult | null

  /* 예산을 다 썼는가. 참이면 추가 조사를 막는다 */
  roundOver: boolean

  onInvestigate: (optionId: string, actionIndex: number) => void
  onResultComplete: () => void
  onTalk: () => void
}


export default function InvestigationPanel({
  options,
  characterName,
  canTalk,
  currentRound,
  placeId,
  investigatedActionIds,
  remainingTurns,
  pending,
  result,
  roundOver,
  onInvestigate,
  onResultComplete,
  onTalk,
}: InvestigationPanelProps) {
  /*
    한 방에서 여러 장이 한꺼번에 나올 수 있다.
    한 장씩 보여 주고, 몇 장 중 몇 번째인지 늘 적어 둔다 —
    제보: "단서가 2개 발견된 경우 두 번째로 넘어갈 방법이 없다."
  */
  const [clueIndex, setClueIndex] = useState(0)
  const [showCluePopup, setShowCluePopup] = useState(false)

  const foundClues = result?.clues ?? []
  const hasClue = foundClues.length > 0
  const currentClue = foundClues[clueIndex] ?? null
  const isLastClue = clueIndex >= foundClues.length - 1


  const handleOptionClick = (option: InvestigationOption) => {
    const actionKey = `${currentRound}:${placeId}:${option.id}`

    if (pending || investigatedActionIds.includes(actionKey)) {
      return
    }

    setClueIndex(0)
    onInvestigate(option.id, option.index)
  }


  const closeResult = () => {
    setShowCluePopup(false)
    setClueIndex(0)
    onResultComplete()
  }


  /* 단서 팝업 — 여러 장이면 다음 장으로, 마지막이면 닫는다 */
  const handleClueNext = () => {
    if (!isLastClue) {
      setClueIndex(clueIndex + 1)
      return
    }

    closeResult()
  }


  return (
    <>
      <div
        className="absolute"
        style={{ left: 70, top: 132, width: 1300, height: 830 }}
      >
        {/* ── 결과 상자 ── */}
        <div
          className="absolute flex flex-col"
          style={{
            left: 790,
            top: 0,
            width: 510,
            height: 430,
            backgroundColor: 'rgba(0, 0, 0, 0.38)',
            padding: '26px 30px',
          }}
        >
          <div
            className="font-game-korean tracking-[0.14em] text-game-gold"
            style={{ fontSize: 15 }}
          >
            {result ? (hasClue ? '단서 발견' : '조사 결과') : '장소 조사'}
          </div>

          <div
            className="mt-3 font-game-korean leading-[1.35] tracking-[0.05em] text-game-ivory"
            style={{ fontSize: 24 }}
          >
            {result ? result.label || '조사' : '조사할 대상을 선택하세요'}
          </div>

          {/* 서버가 지어 준 한 줄 요약 */}
          {result && (
            <div
              className={`mt-3 font-game-korean tracking-[0.04em] ${
                hasClue ? 'text-game-red-light' : 'text-game-gold/80'
              }`}
              style={{ fontSize: 18 }}
            >
              {result.message}
            </div>
          )}

          <p
            className="mt-3 flex-1 overflow-y-auto font-game-korean leading-[1.85] tracking-[0.02em] text-game-muted"
            style={{ fontSize: 16 }}
          >
            {result
              ? result.resultLines.join(' ')
              : '장소를 살펴보면 사건과 연결된 단서를 발견할 수 있습니다.'}
          </p>

          <div className="mt-3 border-t border-game-gold-dark pt-3 font-game-korean text-[14px] leading-[1.6] tracking-[0.06em] text-game-muted">
            {result ? (
              <>
                {/*
                  값이 안 들었으면 그렇다고 말해 준다 —
                  제보: "단서가 안 나오면 행동이 안 깎이는데 의도된 건가?"
                  의도된 것이 맞다. 다만 화면이 말을 안 해서 버그처럼 보였다.
                */}
                {result.cost === 0
                  ? '행동을 쓰지 않았다.'
                  : `행동 ${result.cost}회를 썼다.`}
                {'  ·  '}
                남은 행동 {remainingTurns}
              </>
            ) : (
              `남은 행동 ${remainingTurns}`
            )}
          </div>
        </div>


        {/* ── 조사 선택 ── */}
        {result === null && (
          <>
            <div
              className="absolute"
              style={{
                left: 0,
                top: 620,
                width: 1300,
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 400px)',
                gridAutoRows: '86px',
                columnGap: 50,
                rowGap: 18,
              }}
            >
              {options.map((option) => {
                const actionKey = `${currentRound}:${placeId}:${option.id}`
                const investigated =
                  investigatedActionIds.includes(actionKey)
                const disabled = investigated || pending || roundOver

                return (
                  <button
                    key={option.id}
                    type="button"
                    disabled={disabled}
                    onClick={() => handleOptionClick(option)}
                    className="relative border-0 bg-transparent p-0"
                    style={{
                      width: 400,
                      height: 86,
                      cursor: disabled ? 'default' : 'pointer',
                      opacity: investigated ? 0.35 : pending ? 0.6 : 1,
                    }}
                  >
                    <img
                      src="/assets/icons/yellow_button.svg"
                      alt=""
                      className="absolute inset-0 h-full w-full object-fill"
                    />
                    <span
                      className="absolute inset-0 flex items-center justify-center px-[20px] text-center font-game-korean leading-[1.3] tracking-[0.03em] text-game-ivory"
                      style={{ fontSize: 19 }}
                    >
                      {investigated ? '조사 완료' : option.label}
                    </span>
                  </button>
                )
              })}
            </div>

            {/* 대화 — 주인 없는 방에서는 뜨지 않는다 */}
            {canTalk && (
              <button
                type="button"
                onClick={onTalk}
                className="absolute cursor-pointer border-0 bg-transparent p-0"
                style={{ left: 450, top: 724, width: 400, height: 86 }}
              >
                <img
                  src="/assets/icons/yellow_button.svg"
                  alt=""
                  className="absolute inset-0 h-full w-full object-fill"
                  style={{
                    filter:
                      'sepia(1) saturate(5) hue-rotate(315deg) brightness(0.55)',
                  }}
                />
                <span
                  className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean tracking-[0.06em] text-game-ivory"
                  style={{ fontSize: 21 }}
                >
                  {characterName}와 대화하기
                </span>
              </button>
            )}
          </>
        )}


        {/* ── 결과를 본 뒤 ── */}
        {result !== null && (
          <button
            type="button"
            onClick={hasClue ? () => setShowCluePopup(true) : closeResult}
            className="absolute cursor-pointer border-0 bg-transparent p-0"
            style={{ left: 880, top: 600, width: 300, height: 86 }}
          >
            <img
              src="/assets/icons/yellow_button.svg"
              alt=""
              className="absolute inset-0 h-full w-full object-fill"
            />
            <span
              className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean tracking-[0.06em] text-game-ivory"
              style={{ fontSize: 24 }}
            >
              {hasClue
                ? foundClues.length > 1
                  ? `단서 ${foundClues.length}장 보기`
                  : '단서 보기'
                : '계속 조사'}
            </span>
          </button>
        )}

      </div>


      {/* =========================================
          단서 팝업

          전문이 스크롤 없이 다 보이게 상자를 키웠다.
          여러 장이면 몇 장 중 몇 번째인지 늘 적는다.
      ========================================= */}
      {showCluePopup && currentClue !== null && (
        <div
          className="absolute inset-0 z-40 flex items-center justify-center"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.78)' }}
        >
          <div
            className="relative flex flex-col"
            style={{
              width: 820,
              minHeight: 560,
              border: '1px solid rgba(160,132,80,0.75)',
              backgroundColor: 'rgba(14,13,11,0.98)',
              boxShadow: '0 0 40px rgba(210,175,100,0.14)',
              padding: '30px 40px 34px',
            }}
          >
            <div className="flex items-baseline justify-between">
              <span
                className="font-game-korean tracking-[0.12em]"
                style={{ fontSize: 20, color: '#9b1c1c' }}
              >
                새로운 단서
              </span>
              {foundClues.length > 1 && (
                <span className="font-game-korean text-[17px] tracking-[0.08em] text-game-gold">
                  {clueIndex + 1} / {foundClues.length}
                </span>
              )}
            </div>

            <div className="mt-[18px] flex gap-[26px]">
              {currentClue.image !== '' && (
                <img
                  src={currentClue.image}
                  alt={currentClue.title}
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
                  className="font-game-korean leading-[1.3] tracking-[0.05em] text-game-ivory"
                  style={{ fontSize: 28 }}
                >
                  {currentClue.title}
                </div>

                {/* 종류 · 획득 장소 · 획득 방법 */}
                <dl className="mt-[16px] grid grid-cols-[76px_1fr] gap-x-[14px] gap-y-[8px] font-game-korean text-[15px] leading-[1.5]">
                  {[
                    ['종류', currentClue.type],
                    ['획득 장소', currentClue.place],
                    ['획득 방법', currentClue.method],
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

            {/* 본문 — 스크롤 없이 다 보이게 */}
            <p
              className="mt-[24px] flex-1 whitespace-pre-line font-game-korean leading-[1.85] tracking-[0.02em] text-game-ivory"
              style={{ fontSize: 19 }}
            >
              {currentClue.description}
            </p>

            <button
              type="button"
              onClick={handleClueNext}
              className="mt-[22px] cursor-pointer self-end border border-game-parchment/50 bg-[#171512] px-[38px] py-[13px] font-game-korean text-[21px] tracking-[0.1em] text-game-ivory"
            >
              {isLastClue ? '수첩에 담는다' : '다음 단서 →'}
            </button>
          </div>
        </div>
      )}
    </>
  )
}
