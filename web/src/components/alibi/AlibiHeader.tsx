import { useNavigate } from 'react-router-dom'

type AlibiHeaderProps = {
  currentIndex: number
  total: number
}

export default function AlibiHeader({
  currentIndex,
  total,
}: AlibiHeaderProps) {
  const navigate = useNavigate()

  const currentNumber = String(
    currentIndex + 1,
  ).padStart(2, '0')

  const totalNumber = String(
    total,
  ).padStart(2, '0')

  return (
    <>
      {/* 용의자 목록 */}
      <button
        type="button"
        onClick={() => navigate('/suspects')}
        className="
          absolute
          border-0
          bg-transparent
          p-0
          font-game-korean
          tracking-[0.1em]
          text-game-ivory
          cursor-pointer
        "
        style={{
          left: 59,
          top: 0,
          width: 220,
          height: 140,
          fontSize: 30,
        }}
      >
        &lt; 용의자 목록
      </button>

      {/* 05 / 05 */}
      <div
        className="
          absolute
          flex
          items-center
          justify-center
          whitespace-nowrap
          font-serif
          tracking-[0.1em]
          text-game-ivory
        "
        style={{
          left: 1059,
          top: 0,
          width: 308,
          height: 140,
          fontSize: 30,
        }}
      >
        <span>
          SUSPECTS&nbsp;
        </span>

        <span
          style={{
            color: '#9b1c1c',
          }}
        >
          {currentNumber}
        </span>

        <span>
          &nbsp;/&nbsp;{totalNumber}
        </span>
      </div>

      {/* 상단 줄 */}
      <div
        className="absolute"
        style={{
          left: 70,
          top: 132,
          width: 1300,
          height: 2,
          backgroundColor:
            'rgba(225, 216, 199, 0.7)',
        }}
      />
    </>
  )
}