import { useEffect, useState } from 'react'

type RoundEvent = {
  name: string
  text: string

  /*
    효과 문구는 내려오지 않는다 —
    거기에 어느 인물인지가 적혀 있다.
    실제 적용은 서버가 이미 해 두었다.
  */
  effect?: string
}

type RoundEventOverlayProps = {
  event: RoundEvent

  /* 이벤트로 실제 열린 비밀. 없으면 상자를 그리지 않는다 */
  openedSecrets?: string[]

  onClose: () => void
}

export default function RoundEventOverlay({
  event,
  openedSecrets = [],
  onClose,
}: RoundEventOverlayProps) {
  const detail = openedSecrets.length > 0
    ? openedSecrets.join('\n')
    : (event.effect ?? '')
  const [phase, setPhase] = useState(0)

  useEffect(() => {
    const timers = [
      window.setTimeout(() => setPhase(1), 1200),
      window.setTimeout(() => setPhase(2), 2600),
      window.setTimeout(() => setPhase(3), 3900),
    ]

    return () => timers.forEach(window.clearTimeout)
  }, [])

  return (
    <div className={`absolute inset-0 z-[110] overflow-hidden bg-black text-game-ivory ${
      phase === 0 ? 'event-screen-shake' : ''
    }`}>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(110,41,36,0.25),transparent_65%)]" />

      <div className="absolute left-1/2 top-1/2 flex w-[1050px] -translate-x-1/2 -translate-y-1/2 flex-col items-center text-center font-game-korean">
        <div className="text-[23px] tracking-[0.2em] text-game-red-light">
          EVENT
        </div>
        <h2 className="mb-0 mt-[18px] text-[60px] tracking-[0.14em]">
          판이 뒤집힙니다
        </h2>
        <img
          src="/assets/icons/line.svg"
          alt=""
          className="mt-[18px] h-[53px] w-[573px] object-fill"
        />

        <div className={`mt-[26px] transition-all duration-700 ${
          phase >= 1 ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        }`}>
          <div className="text-[21px] tracking-[0.15em] text-game-parchment">
            비밀 공개
          </div>
          <div className="mt-[12px] text-[33px] tracking-[0.1em]">
            {event.name}
          </div>
          <p className="mt-[14px] text-[23px] leading-[1.7] text-game-ivory/70">
            {event.text}
          </p>
        </div>

        {detail !== '' && (
          <div className={`mt-[24px] max-w-[900px] whitespace-pre-line border-l-2 border-[#8a3830] py-[8px] pl-[26px] pr-[8px] text-left text-[25px] leading-[1.65] tracking-[0.08em] text-[#c2b394] transition-all duration-700 ${
            phase >= 2 ? 'opacity-100' : 'opacity-0'
          }`}>
            {detail}
          </div>
        )}

        <button
          type="button"
          disabled={phase < 3}
          onClick={onClose}
          className={`mt-[32px] h-[117px] w-[450px] border-0 bg-transparent p-0 text-[20px] tracking-[0.1em] text-game-ivory transition-opacity ${
            phase >= 3
              ? 'cursor-pointer opacity-100'
              : 'pointer-events-none opacity-0'
          }`}
        >
          이곳을 눌러 계속 진행합니다
        </button>

      </div>
    </div>
  )
}
