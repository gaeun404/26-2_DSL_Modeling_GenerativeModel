type StoryInputProps = {
  value: string
  onChange: (value: string) => void
}

export default function StoryInput({
  value,
  onChange,
}: StoryInputProps) {
  return (
    <>
      <div
        className="absolute"
        style={{
          left: 255,top: 604,
          width: 928,height: 160,
        }}
      >
        <img
          src="/assets/icons/chat.svg"
          alt=""
          className="absolute inset-0 h-full w-full object-fill"
        />

        <input
          type="text"
          value={value}
          onChange={(event) =>
            onChange(event.target.value)
          }
          placeholder="예) 백설공주"
          className="
            absolute
            inset-0
            h-full
            w-full

            border-0
            bg-transparent

            px-[70px]

            font-game-korean
            text-[30px]
            tracking-[0.1em]
            text-game-ivory

            outline-none

            placeholder:text-game-ivory
            placeholder:opacity-60
          "
        />
      </div>

      {/* 안내 문구 */}
      <div
        className="
          absolute
          left-[255px]
          top-[765px]

          flex
          w-[928px]
          justify-center

          whitespace-nowrap
          font-game-korean
          text-[18px]
          tracking-[0.1em]
          text-game-ivory
        "
      >
        알고 있는 옛이야기·동화·전설이면 무엇이든…
      </div>
    </>
  )
}