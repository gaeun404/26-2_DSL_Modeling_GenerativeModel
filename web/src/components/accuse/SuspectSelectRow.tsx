import type { AccuseSuspect } from '../../pages/AccusePage'

type SuspectSelectRowProps = {
  suspects: AccuseSuspect[]
  selectedSuspectId: string
  onSelect: (id: string) => void
}

export default function SuspectSelectRow({
  suspects,
  selectedSuspectId,
  onSelect,
}: SuspectSelectRowProps) {
  return (
    <section
      className="
        absolute
        flex
        justify-between
      "
      style={{
        left: 55,
        top: 155,

        width: 1330,
        height: 360,
      }}
    >
      {suspects.map((suspect) => {
        const selected =
          selectedSuspectId ===
          suspect.id

        return (
          <button
            key={suspect.id}
            type="button"
            onClick={() =>
              onSelect(suspect.id)
            }
            className="
              relative
              border-0
              bg-transparent
              p-0
              cursor-pointer
            "
            style={{
              width: 245,
              height: 350,
            }}
          >
            {/* 용의자 사진 */}
<div
  className="absolute overflow-hidden"
  style={{
    left: 0,
    top: 0,

    width: 245,
    height: 275,
  }}
>

  {/*
    액자 창의 자리 — 그림의 알파에서 잰 값이다(SuspectCard 주석 참고).
    8px 씩 물려 두었더니 사진이 액자 테두리 밑으로 파고들었다.
  */}
  <div
    className="absolute overflow-hidden bg-black/40"
    style={{
      left: '9%',
      top: '7%',

      width: '82%',
      height: '84%',
    }}
  >
    {suspect.image ? (
      <img
        src={suspect.image}
        alt={suspect.name}
        className="
          h-full
          w-full
          object-cover
          object-top
        "
      />
    ) : (
      <div
        className="
          flex
          h-full
          w-full
          items-center
          justify-center
          bg-black/30
          font-game-korean
          text-white/25
        "
        style={{
          fontSize: 20,
        }}
      >
        인물 사진
      </div>
    )}
  </div>

  {/* 용의자 사진 테두리 */}
  <img
    src="/assets/icons/suspect_frame.svg"
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
</div>
            {/* 이름 */}
            <div
              className="
                absolute
                flex
                items-center
                justify-center
                whitespace-nowrap
                font-game-korean
                tracking-[0.08em]
              "
              style={{
                left: 0,
                top: 285,

                width: 245,
                height: 55,

                fontSize: 27,

                color: selected
                  ? '#9b2f2f'
                  : '#e1d8c7',
              }}
            >
              {suspect.name}
            </div>
          </button>
        )
      })}
    </section>
  )
}
