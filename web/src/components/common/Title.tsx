type TitleProps = {
  text: string
  className: string
  decorationClassName: string
}

export default function Title({
  text,
  className,
  decorationClassName,
}: TitleProps) {
  return (
    <>
      {/* ========================================
          공통 돋보기 장식
      ======================================== */}
      <img
        src="/assets/icons/title-emblem.svg"
        alt=""
        className={`
          pointer-events-none
          absolute
          object-contain
          ${decorationClassName}
        `}
      />

      {/* ========================================
          공통 제목
      ======================================== */}
      <div
        className={`
          whitespace-pre-line
          text-center
          font-game-korean
          text-[60px]
          leading-[1.5]
          tracking-[0.1em]
          text-game-ivory
          ${className}
        `}
      >
        {text}
      </div>
    </>
  )
}