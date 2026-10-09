import type { MapPlace } from '../../types/scenario'

import MapLocation from './MapLocation'


type MapBoardProps = {
  locations: MapPlace[]

  currentRound: number

  visitedPlaceIds: string[]

  onVisitPlace: (
    placeId: string,
  ) => void
}


export default function MapBoard({
  locations,
  currentRound,
  visitedPlaceIds,
  onVisitPlace,
}: MapBoardProps) {
  return (
    <div
      className="absolute"
      style={{
        left: 162,
        top: 200,

        width: 1117,
        height: 835,
      }}
    >
      {/* =========================================
          기존 지도 종이 배경

          디자인 / 크기 그대로 유지
      ========================================= */}
      <img
        src="/assets/icons/map.svg"
        alt=""
        className="absolute"
        style={{
          left: 0,
          top: 0,

          width: 1117,
          height: 835,

          transform:
            'scale(0.9)',

          transformOrigin:
            'top left',

          objectFit:
            'fill',
        }}
      />

      {/* =========================================
          기존 3 × 3 지도 Matrix
      ========================================= */}
      <div
        className="
          absolute
          grid
          grid-cols-3
          grid-rows-3
        "
        style={{
          left: 50,
          top: 60,

          width: 900,
          height: 670,
        }}
      >
        {locations.map(
          (location) => {
            /*
              현재 라운드가
              장소의 unlock_round 이상이면
              접근 가능.
            */
            const unlocked =
              currentRound >=
              location.unlock_round

            /*
              한 번이라도 들어간 적 있는 장소
            */
            const visited =
              visitedPlaceIds.includes(
                location.id,
              )

            /*
              현재 라운드에 처음 열린 장소이며
              아직 방문하지 않았다면 NEW.
            */
            const isNew =
              unlocked &&
              !visited &&
              currentRound ===
                location.unlock_round

            return (
              <MapLocation
                key={location.id}
                id={location.id}
                name={location.name}
                thumb={location.thumb}
                row={location.pos.row}
                col={location.pos.col}
                unlocked={unlocked}
                visited={visited}
                isNew={isNew}
                onVisit={
                  onVisitPlace
                }
              />
            )
          },
        )}
      </div>
    </div>
  )
}