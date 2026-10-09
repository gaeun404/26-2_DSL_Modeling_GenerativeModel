import { useNavigate } from 'react-router-dom'

type PlaceHeaderProps = {
  placeName: string
}

export default function PlaceHeader({
  placeName,
}: PlaceHeaderProps) {
  const navigate = useNavigate()

  return (
    <>
      {/* ========================================
          지도

          이전 지도 페이지의 돌아가기와
          동일한 위치 / 크기
      ======================================== */}
      <button
        type="button"
        onClick={() => navigate('/map')}
        className="
          absolute
          flex
          items-center
          justify-start
          border-0
          bg-transparent
          p-0
          font-game-korean
          tracking-[0.1em]
          text-game-ivory
          cursor-pointer
        "
        style={{
          left: 70,
          top: 40,

          width: 300,
          height: 100,

          fontSize: 30,
        }}
      >
        &lt; 지도
      </button>

      {/* ========================================
          중앙 장소 이름

          백엔드 장소 이름을 그대로 표시
      ======================================== */}
      <div
        className="
          absolute
          flex
          items-center
          justify-center
        "
        style={{
          left: 430,
          top: 42,

          width: 580,
          height: 100,
        }}
      >
        {/* 왼쪽 흰 줄 */}
        <div
          style={{
            width: 90,
            height: 1,
            marginRight: 30,

            backgroundColor:
              'rgba(255, 255, 255, 0.45)',
          }}
        />

        {/* 장소 이름 */}
        <h1
          className="
            m-0
            whitespace-nowrap
            font-game-korean
            tracking-[0.1em]
            text-game-ivory
          "
          style={{
            fontSize: 40,
          }}
        >
          {placeName}
        </h1>

        {/* 오른쪽 흰 줄 */}
        <div
          style={{
            width: 90,
            height: 1,
            marginLeft: 30,

            backgroundColor:
              'rgba(255, 255, 255, 0.45)',
          }}
        />
      </div>

      {/* ========================================
          사건수첩

          이전 지도 페이지와 동일
      ======================================== */}
      <button
        type="button"
        onClick={() => navigate('/notebook')}
        className="
          absolute
          flex
          items-center
          justify-end
          border-0
          bg-transparent
          p-0
          font-game-korean
          tracking-[0.1em]
          text-game-ivory
          cursor-pointer
        "
        style={{
          left: 1100,
          top: 40,

          width: 270,
          height: 100,

          fontSize: 30,
        }}
      >
        사건수첩
      </button>

      {/* ========================================
          상단 흰 줄
      ======================================== */}
      <div
        className="absolute"
        style={{
          left: 70,
          top: 140,

          width: 1300,
          height: 1,

          backgroundColor:
            'rgba(255, 255, 255, 0.45)',
        }}
      />
    </>
  )
}