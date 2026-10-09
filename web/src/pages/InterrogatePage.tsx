import { useEffect } from 'react'
import { useParams } from 'react-router-dom'

import InterrogateHeader from '../components/interrogate/InterrogateHeader'
import InterrogateChat from '../components/interrogate/InterrogateChat'
import {
  getPlaces,
  getSuspects,
} from '../data/scenarioAdapter'
import { useGameStore } from '../store/gameStore'

/*
  심문 화면.

  주소의 :targetId 는 인물 id(C1…C5)다.
  장소 id(P2 등)로 들어와도 그 장소에 서 있는 인물로 옮겨 준다 —
  지도에서 바로 들어오는 길이 있기 때문이다.

  노하람·임세준처럼 제 방이 없는 인물은
  [용의자] 화면에서만 만난다.
*/
export default function InterrogatePage() {
  const { placeId: targetId } = useParams()

  const scenario = useGameStore((state) => state.scenario)
  const selectedPlaceId = useGameStore(
    (state) => state.selectedPlaceId,
  )
  const meet = useGameStore((state) => state.meet)

  const suspects = getSuspects(scenario)
  const places = getPlaces(scenario)

  /* 인물 id 로 왔으면 그대로, 장소 id 로 왔으면 그 방 주인으로 */
  const castId =
    suspects.find((suspect) => suspect.id === targetId)?.id ??
    places.find((place) => place.id === targetId)?.castId ??
    null

  const suspect = suspects.find(
    (item) => item.id === castId,
  )

  /* 배경은 그 인물이 서 있는 방, 없으면 마지막으로 본 방 */
  const place =
    places.find((item) => item.castId === castId) ??
    places.find((item) => item.id === selectedPlaceId) ??
    places[0]

  /*
    첫 대면 알리바이는 행동을 쓰지 않는다.
    화면에 들어설 때마다 불러도 두 번째부터는 아무 일도 없다.
  */
  useEffect(() => {
    if (castId === null) {
      return
    }

    meet(castId).catch(() => {
      /* 알리바이를 못 받아도 심문은 할 수 있다 */
    })
  }, [castId, meet])

  if (suspect === undefined) {
    return (
      <main className="flex h-[1024px] w-[1440px] items-center justify-center bg-black font-game-korean text-[28px] text-game-ivory">
        이 곳에는 만날 사람이 없습니다.
      </main>
    )
  }

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-black text-game-ivory">
      {/* =========================================
          장소 상세 페이지와 동일한 배경
      ========================================= */}
      {place?.backgroundImage ? (
        <img
          src={place.backgroundImage}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : null}

      {/* 배경 어둡게 */}
      <div
        className="absolute inset-0"
        style={{
          backgroundColor: 'rgba(0, 0, 0, 0.68)',
        }}
      />

      <InterrogateHeader
        title={suspect.name}
        placeId={place?.id ?? ''}
      />

      <InterrogateChat
        castId={suspect.id}
        characterName={suspect.name}
        faces={suspect.faces}
        fallbackImage={suspect.image}
        initialAlibi={suspect.alibi}
      />
    </main>
  )
}
