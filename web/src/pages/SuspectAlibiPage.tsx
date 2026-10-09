import {
  useNavigate,
  useParams,
} from 'react-router-dom'

import GameHeader2 from '../components/common/GameHeader2'
import AlibiContent from '../components/alibi/AlibiContent'
import { getSuspects } from '../data/scenarioAdapter'
import { useGameStore } from '../store/gameStore'

export default function SuspectAlibiPage() {
  const navigate = useNavigate()
  const { suspectId } = useParams()
  const scenario = useGameStore((state) => state.scenario)
  const suspects = getSuspects(scenario)

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

  const currentNumber = String(
    currentIndex + 1,
  ).padStart(2, '0')

  const totalNumber = String(
    suspects.length,
  ).padStart(2, '0')

  const handleBack = () => {
    navigate(`/suspect/${suspect.id}`)
  }

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-black text-game-ivory">
      {/* =========================================
          용의자별 장소 배경

          TODO(API / IMAGE):
          나중에 생성된 장소 이미지 URL로 교체
      ========================================= */}
      <img
        src={suspect.backgroundImage}
        alt=""
        className="absolute inset-0 h-full w-full object-cover"
      />

      {/* 배경 어둡게 */}
      <div
        className="absolute inset-0"
        style={{
          backgroundColor:
            'rgba(0, 0, 0, 0.65)',
        }}
      />

      {/* =========================================
          공통 헤더

          이전으로
          SUSPECTS 01/05

          이전으로 클릭 시
          현재 용의자의 상세 페이지로 이동
      ========================================= */}
      <GameHeader2
        leftText="< 이전으로"
        title={`SUSPECTS ${currentNumber}/${totalNumber}`}
        rightText=""
        onLeftClick={handleBack}
        onRightClick={() => {}}
      />

      {/* 용의자 사진 + 알리바이 */}
      <AlibiContent
        image={suspect.image}
        alibi={suspect.alibi}
      />
    </main>
  )
}
