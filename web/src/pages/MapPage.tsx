import MapHeader from '../components/map/MapHeader'
import MapBoard from '../components/map/MapBoard'

import { useGameStore } from '../store/gameStore'

export default function MapPage() {
  /*
    TODO(API):

    실제 게임에서는 Loading 단계에서 받은
    scenario.map.places를 사용한다.
  */
  const scenario = useGameStore(
    (state) => state.scenario,
  )

  const currentRound = useGameStore(
    (state) => state.currentRound,
  )

  const visitedPlaceIds = useGameStore(
    (state) => state.visitedPlaceIds,
  )

  const visitPlace = useGameStore(
    (state) => state.visitPlace,
  )


  const locations = scenario?.map.places ?? []


  return (
    <main
      className="
        relative
        h-[1024px]
        w-[1440px]
        overflow-hidden
        bg-black
        text-game-ivory
      "
    >
      {/* =========================================
          메인 페이지와 동일한 배경
      ========================================= */}
      <img
        /* backgrounds/ 폴더가 없어 깨진 그림이 떠 있었다 — 다른 화면과 같은 바탕으로 */
        src="/assets/icons/title-background.svg"
        alt=""
        className="
          absolute
          inset-0
          h-full
          w-full
          object-cover
        "
      />

      {/* 지도 페이지에서는 배경을 더 어둡게 */}
      <div
        className="absolute inset-0"
        style={{
          backgroundColor:
            'rgba(0, 0, 0, 0.65)',
        }}
      />

      <MapHeader />

      {/* =========================================
          지도 종이 + 장소
      ========================================= */}
      <MapBoard
        locations={locations}
        currentRound={currentRound}
        visitedPlaceIds={
          visitedPlaceIds
        }
        onVisitPlace={visitPlace}
      />
    </main>
  )
}
