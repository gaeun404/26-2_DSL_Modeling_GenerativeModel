export type LoadingMode =
  | 'generate'
  | 'archive'

type LoadingStatusListProps = {
  filledGauges: number
  mode: LoadingMode
}

type LoadingStep = {
  gauge: number
  icon: string
  text: string
  left: number
  top: number
  width: number
  height: number
  textLeft: number
  textTop: number
}


/*
  =========================================
  이야기 각색 모드
  =========================================
*/
const generateSteps: LoadingStep[] = [
  {
    gauge: 2,
    icon: '/assets/icons/person_icon.svg',
    text: '등장인물을 불러오고 있습니다',
    left: 415,
    top: 512,
    width: 121,
    height: 69,
    textLeft: 536,
    textTop: 485,
  },

  {
    gauge: 7,
    icon: '/assets/icons/hiding_icon.svg',
    text: '사건의 진실을 숨기고 있습니다',
    left: 415,
    top: 625,
    width: 121,
    height: 62,
    textLeft: 536,
    textTop: 590,
  },

  {
    gauge: 12,
    icon: '/assets/icons/magnifier_icon.svg',
    text: '단서를 배치하고 있습니다',
    left: 415,
    top: 748,
    width: 121,
    height: 62,
    textLeft: 536,
    textTop: 709,
  },
]


/*
  =========================================
  이미 준비된 사건 모드

  3번째 칸 → 첫 문구
  9번째 칸 → 두 번째 문구

  따라서 확실하게 순차적으로 등장한다.
  =========================================
*/
const archiveSteps: LoadingStep[] = [
  {
    gauge: 3,
    icon: '/assets/icons/magnifier_icon.svg',
    text: '사건 기록을 열고 있습니다',
    left: 415,
    top: 570,
    width: 121,
    height: 62,
    textLeft: 536,
    textTop: 535,
  },

  {
    gauge: 9,
    icon: '/assets/icons/person_icon.svg',
    text: '그날 밤의 사람들을 부르고 있습니다',
    left: 415,
    top: 690,
    width: 121,
    height: 69,
    textLeft: 536,
    textTop: 655,
  },
]


export default function LoadingStatusList({
  filledGauges,
  mode,
}: LoadingStatusListProps) {
  const steps =
    mode === 'archive'
      ? archiveSteps
      : generateSteps

  return (
    <>
      {steps.map((step) => {
        const isVisible =
          filledGauges >= step.gauge

        return (
          <div
            key={step.text}
            className={`transition-opacity duration-700 ${
              isVisible
                ? 'opacity-100'
                : 'opacity-0'
            }`}
          >
            <img
              src={step.icon}
              alt=""
              className="absolute object-contain"
              style={{
                left: step.left,
                top: step.top,
                width: step.width,
                height: step.height,
              }}
            />

            <p
              className="absolute m-0 whitespace-nowrap font-game-korean text-[30px] leading-[140px] tracking-[0.1em] text-game-ivory"
              style={{
                left: step.textLeft,
                top: step.textTop,
              }}
            >
              {step.text}
            </p>
          </div>
        )
      })}
    </>
  )
}