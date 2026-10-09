type GameHeaderProps = {
  leftText: string
  title: string
  rightText: string

  onLeftClick: () => void
  onRightClick: () => void
}

export default function GameHeader({
  leftText,
  title,
  rightText,
  onLeftClick,
  onRightClick,
}: GameHeaderProps) {
  return (
    <>
      {/* 왼쪽 버튼 */}
      <button
        type="button"
        onClick={onLeftClick}
        className="absolute flex items-center justify-start border-0 bg-transparent p-0 font-game-korean tracking-[0.1em] text-game-ivory cursor-pointer"
        style={{
          left: 70,top: 40,width: 300,height: 100,fontSize: 30,
        }}
      >
        {leftText}
      </button>

      {/* 중앙 제목 */}
      <div
        className="absolute flex items-center justify-center"
        style={{left: 430,top: 42,width: 580,height: 100,
        }}
      >
        <div
          style={{width: 90,height: 1, marginRight: 30,backgroundColor:'rgba(255, 255, 255, 0.45)',
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
            width: 90,height: 1,marginLeft: 30,backgroundColor:'rgba(255, 255, 255, 0.45)',
          }}
        />
      </div>

      {/* 오른쪽 버튼 */}
      <button
        type="button"
        onClick={onRightClick}
        className="absolute flex items-center justify-end border-0 bg-transparent p-0 font-game-korean tracking-[0.1em] text-game-ivory cursor-pointer"
        style={{
          left: 1100,top: 40,width: 270,height: 100,fontSize: 30,
        }}
      >
        {rightText}
      </button>

      {/* 상단 구분선 */}
      <div
        className="absolute"
        style={{
          left: 70,top: 140,width: 1300,height: 1,backgroundColor:'rgba(255, 255, 255, 0.45)',
        }}
      />
    </>
  )
}