import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import MainHeader from '../components/main/MainHeader'
import CaseSummary from '../components/main/CaseSummary'
import MainMenu from '../components/main/MainMenu'
import RoundStartOverlay from '../components/main/RoundStartOverlay'
import RoundEventOverlay from '../components/main/RoundEventOverlay'
import NewCluesOverlay from '../components/main/NewCluesOverlay'
import ConfrontationEntryModal from '../components/confrontation/ConfrontationEntryModal'
import InterrogatePickerModal from '../components/main/InterrogatePickerModal'

import { useGameStore } from '../store/gameStore'
import { useUiStore } from '../store/uiStore'
import { useConfrontationUnlocked } from '../config/gameRules'
import { getMainBackground, getSuspects } from '../data/scenarioAdapter'


export default function MainPage() {
  const navigate = useNavigate()
  const [showConfrontationEntry, setShowConfrontationEntry] =
    useState(false)
  const [showRoundEvent, setShowRoundEvent] = useState(false)
  const scenario = useGameStore(
    (state) => state.scenario,
  )
  const mainBackground = getMainBackground(scenario)
  const suspects = getSuspects(scenario)

  const currentRound = useGameStore(
    (state) => state.currentRound,
  )

  const roundStartVisible =
    useGameStore(
      (state) =>
        state.roundStartVisible,
    )

  const hideRoundStart =
    useGameStore(
      (state) =>
        state.hideRoundStart,
    )

  const confrontationUsed = useGameStore(
    (state) => state.confrontationUsed,
  )
  const confrontationPair = useGameStore(
    (state) => state.confrontationPair,
  )
  const startConfrontation = useGameStore(
    (state) => state.startConfrontation,
  )


  /*
    =========================================
    이번 라운드에 터진 이벤트
    =========================================

    라운드를 넘길 때 서버가 알려 준 것만 띄운다.
    시나리오를 미리 훑어 찾지 않는다 —
    이벤트가 실제로 적용됐는지는 엔진만 안다.
  */
  const roundEvent = useGameStore((state) => state.roundEvent)
  const clearRoundEvent = useGameStore(
    (state) => state.clearRoundEvent,
  )
  const openedSecrets = useGameStore((state) => state.openedSecrets)
  const newClues = useGameStore((state) => state.newClues)
  const clearNewClues = useGameStore((state) => state.clearNewClues)
  const [showNewClues, setShowNewClues] = useState(false)


  /*
    =========================================
    대질 해금 여부
    =========================================

    서버가 state.confront 로 알려 준다.
    판이 한 번 뒤집혀야 열린다.
  */
  const confrontationUnlocked = useConfrontationUnlocked()

  /*
    ★지목은 **마지막 밤에만** 띄운다 (팀원 제보 —
      "1, 2라운드에선 범인 맞추기 그냥 없애는 게 나을 듯").

      서버는 막지 않는다 — 일찍 짚고 끝내는 것도 선택이므로. 다만 이른 지목은
      대개 근거 없는 찍기라, 화면에서 감춰 주는 편이 낫다.
      마지막 밤이면 state.accuse_advised 가 참으로 온다.
  */
  const accuseAdvised = useGameStore((state) => state.accuseAdvised)

  /*
    ★심문 칸 (2026-08-30, 제보 — "라운드에서 용의자 심문 칸이 없다").
      지도 → 장소 → 서 있는 사람으로만 닿을 수 있어, 그 방 사람만 물을 수
      있는 것처럼 보였다. 다섯 명 누구에게나 물을 수 있다.
  */
  const [showInterrogatePicker, setShowInterrogatePicker] = useState(false)
  const remainingTurns = useGameStore((state) => state.remainingTurns)
  const confrontationPairs = useGameStore(
    (state) => state.confrontationPairs,
  )
  const maxRounds = useGameStore(
    (state) => state.serverState?.max_rounds ?? 3,
  )

  /*
    라운드 시작 → 이벤트 → 새 단서 순으로 보여 준다.
    한 번에 다 띄우면 무엇이 새로 온 것인지 알 수 없다.
  */
  const handleRoundStartClose = () => {
    hideRoundStart()

    if (roundEvent !== null) {
      setShowRoundEvent(true)
      return
    }

    if (newClues.length > 0) {
      setShowNewClues(true)
    }
  }


  /*
    =========================================
    밤을 마치는 자리

    ★라운드를 넘기는 곳을 여기 하나로 모은다 (2026-08-31, 제보 —
      "남은 행동이 0이 되면 바로 다음 라운드로 전환되는 오류").

      전에는 심문 화면이 마지막 답을 받은 1.4초 뒤에 저 혼자 라운드를 넘겼다.
      그 자동 전환을 지웠는데, 그러면 이번엔 나갈 길이 없어진다 —
      「이번 밤을 마친다」 버튼이 **장소 조사 화면에만** 있었기 때문이다.

      그래서 라운드 화면에도 같은 버튼을 둔다. 심문·조사·대질·수첩 어디서
      행동을 다 썼든, 보던 것을 끝까지 읽고 나오면 여기서 밤을 마친다.
      대질로 마지막 행동을 썼을 때도 똑같이 여기서 넘어간다 — 예외는 없다.
    =========================================
  */
  const roundOver = useGameStore((state) => state.roundOver)
  const isLastRound = useGameStore((state) => state.isLastRound)
  const advanceRound = useGameStore((state) => state.advanceRound)
  const showToast = useUiStore((state) => state.showToast)
  const [finishing, setFinishing] = useState(false)

  const handleFinishRound = async () => {
    if (finishing) return

    if (isLastRound) {
      navigate('/accuse')
      return
    }

    setFinishing(true)

    try {
      await advanceRound()
    } catch (error) {
      showToast(
        error instanceof Error
          ? error.message
          : '라운드를 넘기지 못했습니다.',
      )
      return
    } finally {
      setFinishing(false)
    }

    /* 이미 이 화면이다. ROUND 시작 오버레이는 서버 state 가 띄운다 */
  }

  const menuItems = [
    {
      label: '지도',
      icon:
        '/assets/icons/map_icon.svg',
      path: '/map',
      enabled: true,
    },

    {
      label: '사건수첩',
      icon:
        '/assets/icons/note_icon.svg',
      path: '/notebook',
      enabled: true,
    },

    {
      label: '심문',
      icon:
        '/assets/icons/magnifier_icon.svg',
      path: '/interrogate',
      enabled: remainingTurns > 0,
      lockedReason: '이번 밤의 행동을 다 썼다.',
      onClick: () => {
        if (remainingTurns <= 0) return
        setShowInterrogatePicker(true)
      },
    },

    {
      label: '대질',

      icon:
        '/assets/icons/confront_icon.svg',

      path: '/confrontation',

      /*
        ★대질도 행동 하나를 쓴다(game_engine_v2.confront) — 그러니 심문과
          똑같이 예산이 남았을 때만 연다. 이미 치른 대질을 다시 읽는 것은
          행동을 쓰지 않으므로 그때는 열어 준다.
      */
      enabled:
        confrontationUnlocked &&
        (remainingTurns > 0 || (confrontationUsed && confrontationPair !== null)),
      lockedReason: confrontationUnlocked
        ? '이번 밤의 행동을 다 썼다.'
        : undefined,
      onClick: () => {
        if (confrontationUsed && confrontationPair !== null) {
          navigate('/confrontation')
          return
        }

        if (remainingTurns <= 0) return

        setShowConfrontationEntry(true)
      },
    },

    {
      label: '범인지목',
      icon:
        '/assets/icons/criminal_icon.svg',
      path: '/accuse',
      enabled: accuseAdvised,
      lockedReason: `${maxRounds}번째 밤에 짚는다.`,
    },
  ]


  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-black font-game-korean text-game-ivory">
      {/* =========================================
          TODO(API / IMAGE):

          이후 생성된 메인 배경 이미지로 교체
      ========================================= */}
      <img
        /* backgrounds/ 폴더가 없어 깨진 그림이 떠 있었다 — 다른 화면과 같은 바탕으로 */
        src={mainBackground || '/assets/icons/title-background.svg'}
        alt=""
        className="absolute inset-0 h-full w-full object-cover"
      />

      {/* 상단 게임 정보 */}
      <MainHeader />

      {/* 사건 개요 */}
      <CaseSummary />

      {/*
        이번 밤의 행동을 다 썼다 — 사건 개요(x 40~640) 오른쪽,
        메뉴 구분선(y 774) 위의 빈 자리에 놓는다.
      */}
      {roundOver && (
        <button
          type="button"
          onClick={handleFinishRound}
          disabled={finishing}
          className="absolute left-[700px] top-[664px] flex h-[88px] w-[660px] cursor-pointer flex-col items-center justify-center gap-[4px] border border-game-red-light/60 bg-game-red/25 p-0 font-game-korean text-game-ivory transition-colors hover:bg-game-red/40 disabled:cursor-default disabled:opacity-50"
        >
          <span className="text-[15px] tracking-[0.08em] text-game-ivory/60">
            이번 밤의 행동을 다 썼다
          </span>
          <span className="text-[24px] tracking-[0.08em]">
            {finishing
              ? '넘기는 중…'
              : isLastRound
                ? '범인을 지목한다 →'
                : '이번 밤을 마친다 →'}
          </span>
        </button>
      )}

      {/* 지도 / 사건수첩 / 대질 / 범인지목 */}
      <MainMenu
        items={menuItems}
      />

      {/* =========================================
          라운드 시작 화면

          ROUND 1:
          첫 Main 진입 시 등장

          ROUND 2, 3:
          nextRound() 실행 시 다시 등장

          화면 아무 곳이나 클릭하면 닫힘.
      ========================================= */}
      {roundStartVisible && (
        <RoundStartOverlay
          round={currentRound}
          event={null}
          onClose={handleRoundStartClose}
        />
      )}

      {showRoundEvent && roundEvent !== null && (
        <RoundEventOverlay
          event={roundEvent}
          openedSecrets={openedSecrets}
          onClose={() => {
            setShowRoundEvent(false)
            clearRoundEvent()

            if (newClues.length > 0) {
              setShowNewClues(true)
            }
          }}
        />
      )}

      {showNewClues && newClues.length > 0 && (
        <NewCluesOverlay
          clues={newClues}
          onClose={() => {
            setShowNewClues(false)
            clearNewClues()
          }}
        />
      )}

      {showInterrogatePicker && (
        <InterrogatePickerModal
          suspects={suspects}
          turnsLeft={remainingTurns}
          onClose={() => setShowInterrogatePicker(false)}
          onPick={(castId) => {
            setShowInterrogatePicker(false)
            navigate(`/interrogate/${castId}`)
          }}
        />
      )}

      {showConfrontationEntry && (
        <ConfrontationEntryModal
          suspects={suspects}
          pairs={confrontationPairs}
          unlocked={confrontationUnlocked}
          alreadyUsed={confrontationUsed}
          onClose={() => setShowConfrontationEntry(false)}
          onConfirm={(pair) => {
            startConfrontation(pair)
            navigate('/confrontation')
          }}
        />
      )}
    </main>
  )
}
