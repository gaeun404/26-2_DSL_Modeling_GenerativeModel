import { useGameStore } from '../../store/gameStore'
import { useUiStore } from '../../store/uiStore'
import { getMaxRounds } from '../../config/gameRules'

export default function MainHeader() {
  const openSettings = useUiStore((state) => state.openSettings)

  const scenario = useGameStore(
    (state) => state.scenario,
  )

  const gameTitle = useGameStore(
    (state) => state.gameTitle,
  )

  const sourceTitle = useGameStore(
    (state) => state.sourceTitle,
  )

  const selectedLibraryCase = useGameStore(
    (state) => state.selectedLibraryCase,
  )

  const currentRound = useGameStore(
    (state) => state.currentRound,
  )

  const remainingTurns = useGameStore(
    (state) => state.remainingTurns,
  )

  const totalRounds =
    getMaxRounds(scenario)

  const displayTitle =
    gameTitle ||
    selectedLibraryCase?.title ||
    sourceTitle ||
    '생성된 이야기'

  return (
    <>
      {/* 게임 제목 */}
      <div
        title={displayTitle}
        className="absolute flex items-center overflow-hidden text-ellipsis whitespace-nowrap font-game-korean tracking-[0.1em] text-game-ivory"
        style={{
          left: 58,
          top: 15,

          width: 300,
          height: 85,

          fontSize: 30,
        }}
      >
        <span className="overflow-hidden text-ellipsis whitespace-nowrap">
          {displayTitle}
        </span>
      </div>

      {/* ROUND */}
      <div
        className="absolute flex items-center justify-center whitespace-nowrap font-serif tracking-[0.1em] text-game-ivory"
        style={{
          left: 405,
          top: 15,

          width: 300,
          height: 85,

          fontSize: 30,
        }}
      >
        <span>
          ROUND&nbsp;
        </span>

        <span
          style={{
            color: '#9b1c1c',
          }}
        >
          {currentRound}
        </span>

        <span>
          &nbsp;/ {totalRounds}
        </span>
      </div>

      {/* 남은 행동 */}
      <div
        className="absolute flex items-center justify-center whitespace-nowrap font-game-korean tracking-[0.1em] text-game-ivory"
        style={{
          left: 850,
          top: 15,

          width: 300,
          height: 85,

          fontSize: 30,
        }}
      >
        <span>
          남은 행동&nbsp;
        </span>

        <span
          style={{
            color: '#9b1c1c',
          }}
        >
          {remainingTurns}
        </span>
      </div>

      {/* 설정 */}
      <button
        type="button"
        onClick={openSettings}
        className="absolute flex cursor-pointer items-center justify-end border-0 bg-transparent p-0 font-game-korean tracking-[0.1em] text-game-ivory"
        style={{
          left: 1180,
          top: 15,

          width: 145,
          height: 85,

          fontSize: 30,
        }}
      >
        설정
      </button>

      {/* 상단 구분선 */}
      <div
        className="absolute"
        style={{
          left: 58,
          top: 98,

          width: 1268,
          height: 1,

          backgroundColor:
            'rgba(225, 216, 199, 0.45)',
        }}
      />
    </>
  )
}
