type RoundEvent = {
  name: string
  kind: string
  text: string
  effect: string
}

type RoundStartOverlayProps = {
  round: number
  event: RoundEvent | null
  onClose: () => void
}

export default function RoundStartOverlay({
  round,
  event,
  onClose,
}: RoundStartOverlayProps) {
  return (
    <button
      type="button"
      onClick={onClose}
      className="absolute inset-0 z-[100] h-[1024px] w-[1440px] cursor-pointer border-0 bg-black/90 p-0 text-game-ivory"
    >
      <div
        className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center"
        style={{
          width: 1100,
        }}
      >
        {/* ROUND */}
        <div
          className="font-serif tracking-[0.15em]"
          style={{
            fontSize: 30,
            color: '#9b1c1c',
          }}
        >
          ROUND {round}
        </div>

        {/* 라운드 시작 */}
        <div
          className="mt-[20px] font-game-korean tracking-[0.12em]"
          style={{
            fontSize: 55,
          }}
        >
          라운드가 시작됩니다.
        </div>

        {/* 장식 */}
        <img
          src="/assets/icons/line.svg"
          alt=""
          className="mt-[20px] object-fill"
          style={{
            width: 573,
            height: 53,
          }}
        />

        {/* =====================================
            현재 라운드 이벤트

            이벤트가 있는 라운드에서만 등장
        ===================================== */}
        {event !== null && (
          <div
            className="mt-[35px] flex flex-col items-center text-center font-game-korean tracking-[0.1em]"
            style={{
              width: 900,
            }}
          >
            {/* 이벤트 종류 */}
            <div
              style={{
                fontSize: 23,
                color: '#9b1c1c',
              }}
            >
              {event.kind}
            </div>

            {/* 이벤트 제목 */}
            <div
              className="mt-[15px]"
              style={{
                fontSize: 34,
              }}
            >
              {event.name}
            </div>

            {/* 이벤트 문구 */}
            <div
              className="mt-[20px]"
              style={{
                fontSize: 28,
                lineHeight: 1.8,
              }}
            >
              {event.text}
            </div>

            {/* 이벤트 효과 */}
            <div
              className="mt-[25px]"
              style={{
                fontSize: 21,
                lineHeight: 1.8,
                color:
                  'rgba(235, 225, 207, 0.65)',
              }}
            >
              {event.effect}
            </div>
          </div>
        )}

        {/* 클릭 안내 */}
        <div
          className="mt-[55px] animate-pulse font-game-korean tracking-[0.1em]"
          style={{
            fontSize: 19,
            color:
              'rgba(235, 225, 207, 0.5)',
          }}
        >
          화면을 클릭하여 계속하기
        </div>
      </div>
    </button>
  )
}
