interface MenuButtonProps {
  src: string
  children: string
  onClick: () => void

  width?: number
  height?: number

  className?: string
}

export default function MenuButton({
  src,
  children,
  onClick,
  width = 520,
  height = 64,
  className = '',
}: MenuButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        relative
        block
        cursor-pointer
        border-0
        bg-transparent
        p-0
        ${className}
      `}
      style={{
        width,
        height,
      }}
    >
      {/* SVG 버튼 배경 */}
      <img
        src={src}
        alt=""
        className="
          absolute
          inset-0
          h-full
          w-full
          object-fill
        "
      />

      {/* 버튼 글자 */}
      <span
        className="
          absolute
          left-1/2
          top-1/2
          -translate-x-1/2
          -translate-y-1/2

          whitespace-nowrap

          font-game-korean
          text-[20px]
          tracking-[0.2em]
          text-[#e7dfd0]
        "
      >
        {children}
      </span>
    </button>
  )
}