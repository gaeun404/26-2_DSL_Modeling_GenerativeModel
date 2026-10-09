import Title from '../common/Title'
import GenerateButton from '../caseStart/GenerateButton'

type CaseOpenContentProps = {
  isBlackout: boolean
  caseLabel: string
  caseTitle: string

  backgroundLine: string
  incidentLine: string
  endingLine1: string
  endingLine2: string

  showTitle: boolean
  showBackground: boolean
  showIncident: boolean
  showEnding1: boolean
  showEnding2: boolean
  showButtons: boolean

  onRestart: () => void
  onOpen: () => void
}

export default function CaseOpenContent({
  isBlackout,
  caseLabel,
  caseTitle,

  backgroundLine,
  incidentLine,
  endingLine1,
  endingLine2,

  showTitle,
  showBackground,
  showIncident,
  showEnding1,
  showEnding2,
  showButtons,

  onRestart,
  onOpen,
}: CaseOpenContentProps) {
  return (
    <>
      {/* 머리글 + 사건 제목 */}
      <div
        className={`
          origin-center
          scale-100
          transition-all
          duration-700
          ${
            showTitle
              ? 'translate-y-0 scale-100 opacity-100'
              : 'translate-y-[8px] scale-[0.96] opacity-0'
          }
        `}
      >
        {/* CASE - 원작 / 사용자 커스텀 */}
        <div
          className={`
            absolute
            left-[70px]
            top-[55px]

            font-game-korean
            text-[22px]
            tracking-[0.15em]
            text-game-ivory
            transition-opacity
            duration-700
            ${isBlackout ? 'opacity-0' : 'opacity-100'}
          `}
        >
          CASE - {caseLabel}
        </div>


        {/* 공통 Title */}
        {/* 넉 줄이 접히면서 자리를 더 먹으니 제목을 조금 올린다 */}
        <Title
          text={caseTitle}
          className="
            absolute
            left-[270px]
            top-[120px]

            flex
            h-[260px]
            w-[900px]
            items-center
            justify-center

            leading-[120px]
          "
          decorationClassName="
            left-[460px]
            top-[46px]
            h-[350px]
            w-[520px]
          "
        />
      </div>


      {/* =====================================
          사건 넉 줄

          ★글이 화면 밖으로 흘러 나가던 것을 고친다 (2026-08-29, 3차 제보).
            네 줄이 전부 `whitespace-nowrap` 인 900px 상자였다. 그런데 실제
            글은 배경 89자 · 사건 140자다. 27px 한글로 140자면 2,300px —
            상자의 두 배 반이고, 1440px 화면도 넘는다. 그래서 첫 장면에서
            글이 양쪽으로 잘려 나갔다.

            줄을 접게 두고, 접힌 만큼 자리를 준다. 네 덩이를 절대좌표로
            따로 박아 두면 접히는 순간 서로 겹치므로 **흐르는 세로단**으로
            바꾼다. 끝 두 줄(감상 한 마디 + 난이도)은 짧아서 한 줄에 같이 둔다.

            드러나는 순서(배경 → 사건 → 마무리)는 그대로다.
      ===================================== */}
      <div
        className="
          absolute
          left-[220px]
          top-[470px]

          flex
          w-[1000px]
          flex-col
          items-center
          gap-[20px]

          text-center
          font-game-korean
          tracking-[0.06em]
          text-game-ivory
        "
      >
        {/* 배경 */}
        <p
          className={`
            m-0
            max-w-full
            text-[23px]
            leading-[1.7]
            transition-opacity
            duration-700
            ${showBackground ? 'opacity-100' : 'opacity-0'}
          `}
        >
          {backgroundLine}
        </p>

        {/* 사건 */}
        <p
          className={`
            m-0
            max-w-full
            text-[23px]
            leading-[1.7]
            text-game-ivory/85
            transition-opacity
            duration-700
            ${showIncident ? 'opacity-100' : 'opacity-0'}
          `}
        >
          {incidentLine}
        </p>

        {/* 마무리 — 감상 한 마디 · 난이도 */}
        <p className="m-0 flex max-w-full flex-wrap items-center justify-center gap-x-[16px] text-[21px] leading-[1.7]">
          {/*
            ★한 마디가 비면 「·」도 함께 지운다 (2026-08-31).
              난이도 소개문(「트릭이 꼬여 있다」)을 없애자 앞이 빈 채로
              「· 쉬움」만 남아, 앞말이 잘린 것처럼 보였다.
          */}
          {endingLine1 !== '' && (
            <span
              className={`
                text-game-parchment
                transition-opacity
                duration-700
                ${showEnding1 ? 'opacity-100' : 'opacity-0'}
              `}
            >
              {endingLine1}
            </span>
          )}

          {endingLine2 !== '' && (
            <span
              className={`
                text-game-ivory/45
                transition-opacity
                duration-700
                ${showEnding2 ? 'opacity-100' : 'opacity-0'}
              `}
            >
              {endingLine1 !== '' ? `· ${endingLine2}` : endingLine2}
            </span>
          )}
        </p>
      </div>


      {/* 버튼  */}
      <div
        className={`
          transition-opacity
          duration-700

          ${
            showButtons
              ? 'opacity-100'
              : 'pointer-events-none opacity-0'
          }
        `}
      >
        {/* 다른 밤으로 다시 빚는다 */}
        <div className="absolute left-[172px] top-[782px]">
          <GenerateButton
            text="다른 밤으로 다시 빚는다"
            onClick={onRestart}
            disabled={false}
            textOffsetX={-15}
            textOffsetY={-5}
          />
        </div>


        {/* 사건을 연다 */}
        <div className="absolute left-[918px] top-[782px]">
          <GenerateButton
            text="사건을 연다"
            onClick={onOpen}
            disabled={false}
            textOffsetX={-5}
            textOffsetY={-5}
          />
        </div>
      </div>
    </>
  )
}
