import {
  useNavigate,
  useParams,
} from 'react-router-dom'

import GameHeader2 from '../components/common/GameHeader2'
import { useGameStore } from '../store/gameStore'
import { getSuspects } from '../data/scenarioAdapter'

export default function SuspectDetailPage() {
  const navigate = useNavigate()
  const { suspectId } = useParams()
  const scenario = useGameStore((state) => state.scenario)
  const suspects = getSuspects(scenario)

  /*
    마지막 용의자에서 메인으로 이동할 때
    ROUND 시작 화면을 띄우기 위한 store 함수
  */
  const showRoundStart = useGameStore(
    (state) => state.showRoundStart,
  )

  const foundIndex = suspects.findIndex(
    (suspect) => suspect.id === suspectId,
  )

  const currentIndex =
    foundIndex === -1 ? 0 : foundIndex

  const suspect = suspects[currentIndex]

  if (!suspect) {
    return (
      <main className="flex h-[1024px] w-[1440px] items-center justify-center bg-black font-game-korean text-[28px] text-game-ivory/60">
        용의자 정보를 불러오지 못했습니다.
      </main>
    )
  }

  const isFirst = currentIndex === 0
  const isLast =
    currentIndex === suspects.length - 1

  const currentNumber = String(
    currentIndex + 1,
  ).padStart(2, '0')

  const totalNumber = String(
    suspects.length,
  ).padStart(2, '0')

  /*
    이전 용의자
  */
  const handlePrevious = () => {
    if (isFirst) {
      return
    }

    navigate(
      `/suspect/${suspects[currentIndex - 1].id}`,
    )
  }

  /*
    다음 용의자

    마지막 용의자라면:
    1. ROUND 시작 화면 활성화
    2. MainPage 이동
  */
  const handleNext = () => {
    if (isLast) {
      showRoundStart()
      navigate('/main')
      return
    }

    navigate(
      `/suspect/${suspects[currentIndex + 1].id}`,
    )
  }

  /*
    알리바이 듣기
  */
  const handleAlibi = () => {
    navigate(
      `/suspect/${suspect.id}/alibi`,
    )
  }

  /*
    바로 심문하기.

    노하람·임세준처럼 제 방이 없는 인물도 여기서는 만난다 —
    인물 id 로 곧장 들어간다.
  */
  const handleInterrogate = () => {
    navigate(`/interrogate/${suspect.id}`, {
      state: { from: 'suspects', castId: suspect.id },
    })
  }

  /*
    TODO(BGM):

    suspect.bgm에 백엔드에서 받은
    해당 용의자의 BGM URL이 들어오면
    이 페이지에서 재생한다.

    현재는 실제 음원이 연결되지 않았기 때문에
    재생하지 않는다.
  */

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-black text-game-ivory">

      {/* 배경 — 이 인물이 서 있는 방. 제 방이 없는 사람도 있다 */}
      {suspect.backgroundImage !== '' && (
        <img
          src={suspect.backgroundImage}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}

      {/* 배경 어둡게 */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundColor:
            'rgba(0, 0, 0, 0.55)',
        }}
      />

      {/* 공통 Header: GameHeader2 사용 */}
      <GameHeader2
        leftText="< 용의자 목록"
        title={`SUSPECTS ${currentNumber}/${totalNumber}`}
        rightText=""
        onLeftClick={() =>
          navigate('/suspects')
        }
        onRightClick={() => {}}
      />

      {/* 왼쪽 인물 사진 영역  */}
      <div
        className="absolute overflow-hidden"
        style={{
          left: 70,
          top: 189,

          width: 573,
          height: 668,

          border:
            '1px solid rgba(225, 216, 199, 0.6)',
        }}
      >
        

        {suspect.image !== '' ? (
          <img
            src={suspect.image}
            alt={suspect.name}
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center font-game-korean text-[25px] tracking-[0.1em] text-white/30">
            인물 사진 영역
          </div>
        )}
      </div>

      {/* 오른쪽 용의자 정보창 */}
      <div
        className="absolute"
        style={{
          left: 797,
          top: 189,

          width: 573,
          height: 668,

          border:
            '1px solid rgba(225, 216, 199, 0.6)',

          backgroundColor:
            'rgba(0, 0, 0, 0.35)',
        }}
      />

      {/* 용의자 이름 */}
      <div
        className="absolute flex items-center justify-center whitespace-nowrap font-game-korean text-[40px] tracking-[0.1em]"
        style={{
          left: 930,
          top: 185,

          width: 310,
          height: 130,
        }}
      >
        {suspect.name}
      </div>

      {/* 영문 이름 */}
      <div
        className="absolute flex items-center justify-center whitespace-nowrap font-serif text-[25px] tracking-[0.1em]"
        style={{
          left: 1002,
          top: 255,

          width: 163,
          height: 140,
        }}
      >
        {suspect.englishName}
      </div>

      {/* 이름 아래 장식 */}
      <img
        src="/assets/icons/line.svg"
        alt=""
        className="absolute object-fill"
        style={{
          left: 797,
          top: 331,

          width: 573,
          height: 53,
        }}
      />

      {/*
        ★값이 상자 밖으로 넘치던 것을 고친다 (2026-08-29, 시연 제보).
          제보: "캐릭터 상세 페이지에서 설명 텍스트가 잘려 있다."
          세 칸 모두 whitespace-nowrap 이라 「운영진(세미나 진행 담당)」이
          상자 오른쪽으로 그대로 흘러 나갔다. 줄바꿈을 허용하고 폭을 맞췄다.
          그리고 소개글은 **아예 안 그리고 있었다** — 이제 아래에 둔다.
      */}
      <div
        className="absolute font-game-korean text-[21px] leading-[1.5] tracking-[0.05em]"
        style={{ left: 830, top: 380, width: 510 }}
      >
        {[
          ['신분', suspect.status],
          ['나이', suspect.age],
          ['피해자 관계', suspect.relation],
        ]
          .filter(([, value]) => Boolean(value))
          .map(([label, value]) => (
            <div key={label} className="mb-[14px] flex items-start">
              <span className="w-[130px] shrink-0 font-semibold text-game-gold/90">
                {label}
              </span>
              <span className="flex-1 break-keep text-game-ivory">{value}</span>
            </div>
          ))}

        {suspect.intro !== '' && (
          <p className="mt-[6px] max-h-[150px] overflow-y-auto break-keep pr-[6px] text-[17px] leading-[1.8] text-game-ivory/70">
            {suspect.intro}
          </p>
        )}
      </div>

      {/* 피해자 관계 아래 장식 */}
      <img
        src="/assets/icons/line.svg"
        alt=""
        className="absolute object-fill"
        style={{
          left: 797,
          top: 654,

          width: 573,
          height: 53,
        }}
      />

      {/* 알리바이 듣기  */}
      <button
        type="button"
        onClick={handleAlibi}
        className="absolute border-0 bg-transparent p-0"
        style={{
          left: 1099,
          top: 731,

          width: 214,
          height: 140,
        }}
      >
        <span className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean text-[25px] tracking-[0.06em] text-game-ivory">
          알리바이 듣기
        </span>
      </button>

      {/* 바로 심문하기 */}
      <button
        type="button"
        onClick={handleInterrogate}
        className="absolute border-0 bg-transparent p-0 disabled:cursor-default disabled:opacity-35"
        style={{
          left: 855,
          top: 731,

          width: 214,
          height: 140,
        }}
      >
        <span className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean text-[25px] tracking-[0.06em] text-game-ivory">
          바로 심문하기
        </span>
      </button>

      {/* 이전 용의자  */}
      {!isFirst && (
        <button
          type="button"
          onClick={handlePrevious}
          className="absolute border-0 bg-transparent p-0"
          style={{
            left: 126,
            top: 880,

            width: 214,
            height: 140,
          }}
        >
          <img
            src="/assets/icons/button.svg"
            alt=""
            className="absolute inset-0 h-full w-full -scale-x-100 object-fill"
          />

          <span className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean text-[25px] tracking-[0.06em] text-game-ivory">
            &lt; 이전 용의자
          </span>
        </button>
      )}

      {/* 하단 장식  */}
      <img
        src="/assets/icons/line.svg"
        alt=""
        className="absolute object-fill"
        style={{
          left: 434,
          top: 927,

          width: 573,
          height: 53,
        }}
      />

      <button
        type="button"
        onClick={handleNext}
        className="absolute border-0 bg-transparent p-0"
        style={{
          left: 1100,
          top: 880,

          width: 214,
          height: 140,
        }}
      >
        <img
          src="/assets/icons/button.svg"
          alt=""
          className="absolute inset-0 h-full w-full object-fill"
        />

        <span className="absolute inset-0 flex -translate-y-[5px] items-center justify-center whitespace-nowrap font-game-korean text-[25px] tracking-[0.06em] text-game-ivory">
          {isLast
            ? '메인으로 >'
            : '다음 용의자 >'}
        </span>
      </button>
    </main>
  )
}
