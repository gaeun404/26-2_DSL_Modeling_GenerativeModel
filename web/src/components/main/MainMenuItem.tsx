import { useNavigate } from 'react-router-dom'

type MainMenuItemProps = {
  label: string
  icon: string
  path: string
  enabled: boolean
  /* 잠겨 있으면 왜 잠겼는지 한 줄 — 아무 반응 없이 잠겨 있으면 고장처럼 보인다 */
  lockedReason?: string
  onClick?: () => void
}

export default function MainMenuItem({
  label,
  icon,
  path,
  enabled,
  lockedReason,
  onClick,
}: MainMenuItemProps) {
  const navigate = useNavigate()

  const handleClick = () => {
    if (onClick) {
      onClick()
      return
    }

    /*
      잠겨 있는 메뉴는
      눌러도 아무 반응 없음.
    */
    if (!enabled) {
      return
    }

    navigate(path)
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="relative h-[250px] flex-1 border-0 bg-transparent p-0 text-game-ivory"
      style={{
        cursor:
          enabled || onClick
            ? 'pointer'
            : 'default',

        /*
          이벤트 발생 전:
          회색처럼 보이도록 낮은 opacity

          이벤트 발생 후:
          원래 색상
        */
        opacity:
          enabled
            ? 1
            : 0.35,
      }}
    >
      {/*
        ★칸 수가 달라져도 안 넘치게 (2026-08-30).
          아이콘과 이름을 절대좌표(left 52 / left 178)로 박아 두어 **네 칸일 때만**
          맞았다. 「심문」을 넣어 다섯 칸이 되자 마지막 칸이 화면 밖으로 20px
          삐져나갔다. 가운데로 흐르게 두면 칸 수와 무관하다.
      */}
      <div className="flex h-full w-full flex-col items-center justify-center gap-[10px] px-[10px]">
        <img
          src={icon}
          alt=""
          className="h-[104px] w-[104px] shrink-0 object-contain"
        />

        <div className="whitespace-nowrap text-[27px] tracking-[0.08em]">
          {label}
        </div>

        {/* 왜 잠겼는가 — 아무 반응 없이 잠겨 있으면 고장처럼 보인다 */}
        {!enabled && lockedReason && (
          <div className="w-full text-center font-game-korean text-[14px] leading-[1.4] tracking-[0.04em] text-game-ivory/60">
            {lockedReason}
          </div>
        )}
      </div>
    </button>
  )
}
