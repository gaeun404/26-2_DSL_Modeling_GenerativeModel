type LoadingProgressBarProps = {
  filledGauges: number
}

const GAUGE_COUNT = 17

export default function LoadingProgressBar({
  filledGauges,
}: LoadingProgressBarProps) {
  return (
    <div className="absolute left-[223px] top-[845px] h-[110px] w-[992px]">

      {/* 로딩바 외곽 */}
      <img
        src="/assets/icons/loading_bar.svg"
        alt=""
        className="absolute inset-0 h-full w-full object-fill"
      />

      {/* 17칸 게이지 */}
      <div className="absolute left-[18px] top-[15px] flex h-[80px] w-[956px] items-center gap-[4px] overflow-hidden px-[4px]">
        {Array.from({
          length: GAUGE_COUNT,
        }).map((_, index) => {
          const isFilled =
            index < filledGauges

          /*
            왼쪽 → 오른쪽으로 갈수록
            기존처럼 조금씩 밝아짐
          */
          const ratio =
            index /
            (GAUGE_COUNT - 1)

          const brightness =
            0.42 +
            ratio * 0.85

          return (
            <img
              key={index}
              src="/assets/icons/gauge.svg"
              alt=""
              className={`h-[68px] flex-1 object-fill transition-opacity duration-500 ${
                isFilled
                  ? 'opacity-100'
                  : 'opacity-0'
              }`}
              style={{
                filter: `brightness(${brightness})`,
              }}
            />
          )
        })}
      </div>

    </div>
  )
}