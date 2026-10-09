type AccuseSubmitButtonProps = {
  onClick: () => void
}

export default function AccuseSubmitButton({
  onClick,
}: AccuseSubmitButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="
        absolute
        z-20
        border-0
        bg-transparent
        p-0
        cursor-pointer
      "
      style={{
        left: 1060,
        top: 665,

        width: 270,
        height: 150,
      }}
    >
      <img
        src="/assets/icons/button.svg"
        alt=""
        className="
          pointer-events-none
          absolute
          inset-0
          h-full
          w-full
          object-fill
        "
      />

      <span
        className="
          pointer-events-none
          absolute
          inset-0
          flex
          items-center
          justify-center
          font-game-korean
          tracking-[0.1em]
          text-game-ivory
        "
        style={{
          fontSize: 38,
        }}
      >
        제출
      </span>
    </button>
  )
}
