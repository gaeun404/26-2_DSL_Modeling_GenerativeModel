type GameHeader2Props = {
  leftText: string
  title: string
  rightText: string
  onLeftClick: () => void
  onRightClick: () => void
}

export default function GameHeader2({
  leftText,
  title,
  rightText,
  onLeftClick,
  onRightClick,
}: GameHeader2Props) {
  return (
    <>
      {/* 왼쪽 */}
      <button
        type="button"
        onClick={onLeftClick}
        className="absolute z-20 flex cursor-pointer items-center justify-start border-0 bg-transparent p-0 font-game-korean tracking-[0.1em] text-game-ivory"
        style={{
          left: 45,
          top: 15,
          width: 300,
          height: 85,
          fontSize: 30,
        }}
      >
        {leftText}
      </button>

      {/* 중앙 */}
      <div
        className="pointer-events-none absolute z-20 flex items-center justify-center"
        style={{
          left: 430,
          top: 10,
          width: 580,
          height: 90,
        }}
      >
        <div
          style={{
            width: 90,
            height: 1,
            marginRight: 30,
            backgroundColor:
              'rgba(255,255,255,0.45)',
          }}
        />

        <h1
          className="m-0 whitespace-nowrap font-game-korean tracking-[0.1em] text-game-ivory"
          style={{
            fontSize: 40,
          }}
        >
          {title}
        </h1>

        <div
          style={{
            width: 90,
            height: 1,
            marginLeft: 30,
            backgroundColor:
              'rgba(255,255,255,0.45)',
          }}
        />
      </div>

      {/* 오른쪽 */}
      {rightText !== '' && (
        <button
          type="button"
          onClick={onRightClick}
          className="absolute z-20 flex cursor-pointer items-center justify-end border-0 bg-transparent p-0 font-game-korean tracking-[0.1em] text-game-ivory"
          style={{
            left: 1100,
            top: 15,
            width: 270,
            height: 85,
            fontSize: 30,
          }}
        >
          {rightText}
        </button>
      )}

      {/* 하단 선 */}
      <div
        className="pointer-events-none absolute z-20"
        style={{
          left: 45,
          top: 98,
          width: 1320,
          height: 1,
          backgroundColor:
            'rgba(255,255,255,0.45)',
        }}
      />
    </>
  )
}
