import { useNavigate } from 'react-router-dom'

import { useGameStore } from '../store/gameStore'
import { useUiStore } from '../store/uiStore'
import { getMaxRounds } from '../config/gameRules'

export default function RoundEndPage() {
  const navigate = useNavigate()

  const currentRound =
    useGameStore(
      (state) =>
        state.currentRound,
    )

  const scenario =
    useGameStore(
      (state) => state.scenario,
    )

  const advanceRound =
    useGameStore(
      (state) => state.advanceRound,
    )

  const showToast = useUiStore((state) => state.showToast)

  const maxRounds = getMaxRounds(scenario)

  const isLastRound =
    maxRounds > 0 && currentRound >= maxRounds

  /*
    =========================================
    다음 단계
    =========================================
  */

  const handleContinue = async () => {
    if (maxRounds === 0) {
      navigate('/')
      return
    }

    /*
      마지막 라운드 종료

      → 최종 범인 지목
    */
    if (isLastRound) {
      navigate('/accuse')
      return
    }

    /*
      다음 라운드 시작.

      라운드를 올리는 것도 서버의 몫이다 —
      새 행동 예산, 저절로 들어오는 증언, 이벤트까지
      한 번에 돌아온다.
    */
    try {
      await advanceRound()
    } catch (error) {
      showToast(
        error instanceof Error
          ? error.message
          : '라운드를 넘기지 못했습니다.',
      )
      return
    }

    navigate('/main')
  }

  return (
    <main
      className="
        relative
        h-[1024px]
        w-[1440px]
        overflow-hidden
        bg-black
        font-game-korean
        text-game-ivory
      "
    >
      {/* =====================================
          위쪽 장식선
      ===================================== */}

      <div
        className="absolute"
        style={{
          left: 70,
          top: 132,

          width: 1300,
          height: 1,

          backgroundColor:
            'rgba(238, 233, 223, 0.35)',
        }}
      />

      {/* =====================================
          ROUND
      ===================================== */}

      <div
        className="absolute"
        style={{
          left: 170,
          top: 225,

          width: 1100,

          textAlign: 'center',

          fontSize: 22,
          letterSpacing: '0.15em',
          color: '#9b1c1c',
        }}
      >
        ROUND {currentRound}
      </div>

      {/* =====================================
          종료 나레이션

          TODO(API):
          추후 라운드별 종료 문구로 교체.

          무엇이 잘못되었는지는
          플레이어에게 알려주지 않는다.
      ===================================== */}

      <div
        className="absolute"
        style={{
          left: 320,
          top: 350,

          width: 800,

          textAlign: 'center',

          fontSize: 30,
          lineHeight: 2,
          letterSpacing: '0.1em',
        }}
      >
        {currentRound}라운드가 끝났다.

        <br />

        밤이 더 깊어졌다.

        <br />

        복도의 불이 하나씩 꺼진다.
      </div>

      {/* =====================================
          종료 안내
      ===================================== */}

      <div
        className="absolute"
        style={{
          left: 420,
          top: 755,

          width: 600,
          height: 55,

          display: 'flex',
          alignItems: 'center',
          justifyContent:
            'center',

          fontSize: 20,
          letterSpacing: '0.12em',
          color: '#9a8d72',
        }}
      >
        {isLastRound
          ? '모든 라운드가 끝났습니다.'
          : '이 라운드가 끝났습니다.'}
      </div>

      {/* =====================================
          다음 단계 버튼
      ===================================== */}

      <button
        type="button"
        onClick={handleContinue}
        className="
          absolute
          cursor-pointer
          font-game-korean
          text-game-ivory
        "
        style={{
          left: 495,
          top: 819,

          width: 450,
          height: 117,

          border: 0,
          backgroundColor:
            'transparent',

          fontSize: 20,
          letterSpacing: '0.15em',
        }}
      >
        {isLastRound
          ? '최종 추리 >'
          : '이곳을 눌러 계속 진행합니다'}
      </button>

    </main>
  )
}
