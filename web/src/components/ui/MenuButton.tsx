import type { ReactNode } from 'react'

interface MenuButtonProps {
  children: ReactNode

  onClick?: () => void

  /**
   * 메인 버튼인지 여부.
   * 사건 시작만 true.
   */
  primary?: boolean

  /**
   * 나중에 SVG 아이콘 들어갈 자리.
   */
  icon?: ReactNode

  /**
   * 우측 화살표 등.
   */
  rightElement?: ReactNode
}

export default function MenuButton({
  children,
  onClick,
  primary = false,
  icon,
  rightElement,
}: MenuButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        group
        relative
        flex
        h-[64px]
        w-[520px]
        items-center
        justify-center
        overflow-hidden

        border
        font-game
        text-[21px]
        tracking-[0.22em]

        transition-all
        duration-200

        ${
          primary
            ? `
              border-game-red-light
              bg-[linear-gradient(90deg,#170d0b_0%,#35120f_50%,#170d0b_100%)]
              text-game-ivory

              hover:border-[#a24a40]
              hover:bg-[linear-gradient(90deg,#1e0e0c_0%,#481813_50%,#1e0e0c_100%)]
            `
            : `
              border-game-gold-dark
              bg-[rgba(4,4,3,0.72)]
              text-game-ivory

              hover:border-game-gold
              hover:bg-[rgba(24,20,15,0.85)]
            `
        }
      `}
    >
      {/* 안쪽 장식 테두리 */}
      <span
        aria-hidden="true"
        className="
          pointer-events-none
          absolute
          inset-[5px]
          border
          border-[rgba(128,108,69,0.28)]
        "
      />

      {/* 왼쪽 아이콘 */}
      <span
        className="
          absolute
          left-[42px]
          flex
          h-[36px]
          w-[36px]
          items-center
          justify-center
        "
      >
        {icon}
      </span>

      {/* 버튼 텍스트 */}
      <span className="relative z-10">
        {children}
      </span>

      {/* 우측 영역 */}
      {rightElement && (
        <span
          className="
            absolute
            right-[34px]
            flex
            items-center
            justify-center
          "
        >
          {rightElement}
        </span>
      )}
    </button>
  )
}