import { useState } from 'react'

import {
  useNavigate,
  useParams,
} from 'react-router-dom'

import InvestigationHeader from '../components/investigation/InvestigationHeader'
import InvestigationPanel from '../components/investigation/InvestigationPanel'
import type { InvestigationResult } from '../components/investigation/InvestigationPanel'

import { useGameStore } from '../store/gameStore'
import { useUiStore } from '../store/uiStore'
import {
  getInvestigationOptions,
  getPlaces,
} from '../data/scenarioAdapter'


export default function PlaceInvestigationPage() {
  const navigate = useNavigate()

  const { placeId } = useParams()

  const currentRound = useGameStore(
    (state) => state.currentRound,
  )

  const remainingTurns = useGameStore(
    (state) => state.remainingTurns,
  )

  const scenario = useGameStore(
    (state) => state.scenario,
  )

  const investigatedActionIds = useGameStore(
    (state) => state.investigatedActionIds,
  )

  const markActionInvestigated = useGameStore(
    (state) => state.markActionInvestigated,
  )

  const investigate = useGameStore(
    (state) => state.investigate,
  )

  const roundOver = useGameStore((state) => state.roundOver)

  const setSelectedPlaceId = useGameStore(
    (state) => state.setSelectedPlaceId,
  )

  const showToast = useUiStore((state) => state.showToast)

  /* 서버가 돌려준 조사 결과 — 화면에 그대로 그린다 */
  const [result, setResult] =
    useState<InvestigationResult | null>(null)

  const [pending, setPending] = useState(false)

  const places = getPlaces(scenario)

  const place = places.find(
    (item) => item.id === placeId,
  )

  if (place === undefined) {
    return (
      <main className="flex h-[1024px] w-[1440px] items-center justify-center bg-black font-game-korean text-[28px] text-game-ivory">
        장소 정보를 불러오지 못했습니다.
      </main>
    )
  }

  const options = getInvestigationOptions(
    scenario,
    place.id,
    currentRound,
  )


  /*
    =========================================
    대화하기
    =========================================

    이 장소에 서 있는 인물에게 간다.
    들어가는 것 자체는 값이 들지 않는다 —
    질문을 보낼 때 서버가 1턴을 뺀다.
  */
  const handleTalk = () => {
    if (!place.castId) {
      showToast(place.talkNote || '이 곳에는 만날 사람이 없습니다.')
      return
    }

    setSelectedPlaceId(place.id)
    navigate(`/interrogate/${place.castId}`)
  }


  /*
    =========================================
    조사 선택
    =========================================

    무엇이 나오는지는 프론트가 모른다.
    서버에 물어 보고, 돌아온 것을 그린다.

    값은 장소에 매겨진다 —
    그 라운드에 처음 뒤지는 방만 1턴이고,
    그 방의 단서는 한꺼번에 다 나온다.
    빈 방은 값이 들지 않는다.
  */
  const handleInvestigate = async (
    optionId: string,
    actionIndex: number,
  ) => {
    const actionKey = `${currentRound}:${place.id}:${optionId}`

    if (
      pending ||
      investigatedActionIds.includes(actionKey)
    ) {
      return
    }

    setPending(true)

    try {
      const found = await investigate(place.id, actionIndex)

      markActionInvestigated(actionKey)

      /*
        문구는 서버가 짓는다.

        전에는 누른 칸의 연출과 실제로 나온 것이 서로 다른 데서 났다 —
        "딱히 특별한 건 없었다"가 뜨면서 수첩에는 단서가 들어와 있었다.
        이제 lines 는 **실제로 무언가 나온 칸 기준**이고,
        message 는 한 줄 요약이다.
      */
      setResult({
        label: found.pressed_label ?? '',
        message: found.message,
        cost: found.cost,
        resultLines: found.lines,
        clues: found.found.map((clue) => ({
          id: clue.clue_id,
          title: clue.name ?? clue.clue_id,
          description: clue.description ?? '',
          type: clue.type ?? '',
          place: clue.acquired_place,
          method: clue.acquired_method,
          image: clue.full_image || clue.image || '',
        })),
      })
    } catch (error) {
      showToast(
        error instanceof Error
          ? error.message
          : '조사에 실패했습니다.',
      )
    } finally {
      setPending(false)
    }
  }


  /*
    =========================================
    조사 결과 확인 완료
    =========================================

    ★여기서 라운드를 넘기지 않는다 (2026-08-29, 시연 제보).
      제보: "마지막 행동을 하면 결과를 보기도 전에 라운드가 넘어간다."
      예산이 0이 되어도 결과 상자는 그대로 둔다. 넘기는 것은
      플레이어가 「이번 밤을 마친다」를 누를 때뿐이다.
  */
  const handleResultComplete = () => {
    setResult(null)
  }


  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-black text-game-ivory">

      {/* 장소 배경 */}
      {place.backgroundImage !== '' && (
        <img
          src={place.backgroundImage}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}


      {/* 배경 어둡게 */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.62)',
        }}
      />


      {/* =========================================
          Header

          돌아가기 / 장소명 / 사건수첩
      ========================================= */}
      <InvestigationHeader
        placeName={place.name}
        placeId={place.id}
      />


      {/* =========================================
          조사 Panel
      ========================================= */}
      <InvestigationPanel
        options={options}
        characterName={place.characterName}
        canTalk={place.castId !== null}
        currentRound={currentRound}
        placeId={place.id}
        investigatedActionIds={investigatedActionIds}
        remainingTurns={remainingTurns}
        pending={pending}
        result={result}
        roundOver={roundOver}
        onInvestigate={handleInvestigate}
        onResultComplete={handleResultComplete}
        onTalk={handleTalk}
      />

    </main>
  )
}
