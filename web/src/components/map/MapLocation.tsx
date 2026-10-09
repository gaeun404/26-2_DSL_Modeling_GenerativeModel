import { useNavigate } from 'react-router-dom'


type MapLocationProps = {
  id: string
  name: string

  /* 서버가 준 장소 그림 */
  thumb?: string

  row: number
  col: number

  unlocked: boolean
  visited: boolean
  isNew: boolean

  onVisit: (
    placeId: string,
  ) => void
}


export default function MapLocation({
  id,
  name,
  thumb,
  row,
  col,
  unlocked,
  visited,
  isNew,
  onVisit,
}: MapLocationProps) {
  const navigate = useNavigate()


  const handleClick = () => {
    /*
      아직 열리지 않은 장소는
      눌러도 아무 일도 일어나지 않는다.
    */
    if (!unlocked) {
      return
    }


    /*
      장소 방문 기록.

      IMPORTANT:
      지도에서 장소를 선택하는 것 자체는
      행동을 소모하지 않는다.
    */
    onVisit(id)


    /*
      =========================================
      기존

      지도
        ↓
      PlacePage
        ↓
      PlaceInvestigationPage


      변경

      지도
        ↓
      PlaceInvestigationPage


      따라서 중간 PlacePage를 건너뛴다.
      =========================================
    */
    navigate(
      `/place/${id}/investigation`,
    )
  }


  return (
    <button
      type="button"
      onClick={handleClick}
      className="
        relative
        flex
        flex-col
        items-center
        justify-center
        border-0
        bg-transparent
        p-0
      "
      style={{
        gridRow: row,
        gridColumn: col,

        cursor:
          unlocked
            ? 'pointer'
            : 'default',

        /*
          상태별 표시

          잠김
          → 가장 흐림

          방문함
          → 조금 흐림

          NEW / 아직 방문 안 함
          → 선명
        */
        opacity:
          !unlocked
            ? 0.25
            : visited
              ? 0.55
              : 1,
      }}
    >
      {/* =========================================
          장소 그림
      ========================================= */}
      <div
        className="
          relative
          overflow-hidden
          border
          border-[#6f5636]/60
        "
        style={{
          width: 260,
          height: 160,
        }}
      >
        {thumb ? (
          <img
            src={thumb}
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
            style={{
              filter: unlocked ? 'none' : 'grayscale(1) brightness(0.45)',
            }}
          />
        ) : null}


        {/* 이번 ROUND에 새로 열린 장소 */}
        {isNew && (
          <div
            className="
              absolute
              right-[10px]
              top-[8px]
              font-serif
              tracking-[0.08em]
            "
            style={{
              fontSize: 18,
              color: '#8f2f22',
            }}
          >
            ● NEW
          </div>
        )}


        {/* 아직 잠긴 장소 */}
        {!unlocked && (
          <div
            className="
              absolute
              inset-0
              flex
              items-center
              justify-center
              font-game-korean
              text-[#251a10]
            "
            style={{
              fontSize: 30,
            }}
          >
            🔒
          </div>
        )}
      </div>


      {/* 장소 이름 */}
      <div
        className="
          flex
          items-center
          justify-center
          whitespace-nowrap
          font-game-korean
          tracking-[0.08em]
          text-[#251a10]
        "
        style={{
          marginTop: 12,

          height: 45,

          fontSize: 28,
        }}
      >
        {name}
      </div>


      {/* 이미 방문한 장소 */}
      {visited && (
        <div
          className="
            font-game-korean
            tracking-[0.06em]
            text-[#251a10]
          "
          style={{
            marginTop: -3,
            fontSize: 15,
          }}
        >
          이미 살펴봄
        </div>
      )}
    </button>
  )
}