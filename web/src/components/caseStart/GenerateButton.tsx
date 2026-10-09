interface GenerateButtonProps {
  text: string
  onClick: () => void
  disabled: boolean
  textOffsetX?: number
  textOffsetY?: number
}

export default function GenerateButton({
  text,
  onClick,
  disabled,
  textOffsetX = 0,
  textOffsetY = 0,
}: GenerateButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="relative block h-[186px] w-[350px] border-0 bg-transparent p-0 disabled:cursor-not-allowed disabled:opacity-40"
    >
      <img
        src="/assets/icons/button.svg"
        alt=""
        className="absolute inset-0 h-full w-full object-fill"
      />

      {/*
        글이 그림 안쪽에서만 놀게 한다.
        button.svg 는 오른쪽 끝에 화살표 장식을 달고 있어서, 가운데 정렬만
        해 두면 긴 글이 그 화살표를 밟는다 — 「다른 밤으로 다시 빚는다」가
        그랬다. 양쪽에 자리를 떼어 두고 그 안에서 가운데를 잡는다.
      */}
      <span
        className={`
          absolute
          inset-y-0
          left-[30px]
          right-[54px]
          flex
          items-center
          justify-center
          whitespace-nowrap
          font-game-korean
          tracking-[0.08em]
          text-game-ivory
          ${
            text.length > 9
              ? 'text-[21px]'
              : 'text-[35px]'}`}
        style={{
          transform: `translate(${textOffsetX}px, ${textOffsetY}px)`,
        }}
      >
        {text}
      </span>
    </button>
  )
}
