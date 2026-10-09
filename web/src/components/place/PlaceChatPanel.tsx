import { useNavigate } from 'react-router-dom'

type PlaceChatPanelProps = {
  characterName: string
  dialogue: string
  placeId: string
}

export default function PlaceChatPanel({
  characterName,
  dialogue,
  placeId,
}: PlaceChatPanelProps) {
  const navigate = useNavigate()

  return (
    <div
      className="absolute"
      style={{
        // =========================================
        // 대화창 전체 위치
        // =========================================
        left: 121,
        top: 637,

        // 대화창 전체 크기
        width: 1198,
        height: 337,
      }}
    >
      {/* =========================================
          대화창 배경
          StoryFrame.svg
      ========================================= */}
      <img
        src="/assets/icons/StoryFrame.svg"
        alt=""
        className="
          absolute
          inset-0
          h-full
          w-full
          object-fill
        "
      />

      {/* =========================================
          대화 영역

          이름 : 대사
                 대사
                 대사

          형태로 줄맞춤
      ========================================= */}
      <div
        className="
          absolute
          flex
          items-start
          font-game-korean
          tracking-[0.08em]
          text-game-ivory
        "
        style={{
          // ⭐ 대화 전체 위치
          left: 40,
          top: 70,

          // ⭐ 대화 전체 영역 크기
          width: 760,
          height: 180,

          // ⭐ 글씨 크기
          fontSize: 25,

          // ⭐ 행간
          lineHeight: 1.8,
        }}
      >
        {/* =====================================
            인물 이름 + :

            이름 길이가 달라도
            ":" 위치는 동일하게 유지

            TODO(API):
            백엔드에서 characterName 받아올 예정
        ===================================== */}
        <div
          className="
            shrink-0
            whitespace-nowrap
            text-right
          "
          style={{
            // ⭐ ":" 위치 조절
            // 크게 → 오른쪽
            // 작게 → 왼쪽
            width: 180,
          }}
        >
          {characterName} :
        </div>

        {/* =====================================
            대사

            줄바꿈이 되어도 모든 줄이
            ":" 뒤에서 동일하게 시작

            TODO(API):
            SuspectDetail에서 사용한
            동일한 진술 데이터 연결 예정
        ===================================== */}
        <div
          style={{
            // ⭐ ":"와 대사 사이 간격
            marginLeft: 18,

            // ⭐ 대사가 들어가는 가로 영역
            width: 560,
          }}
        >
          {dialogue}
        </div>
      </div>

      {/* =========================================
          심문하기 버튼
      ========================================= */}
      <button
        type="button"
        onClick={() =>
          navigate(`/interrogate/${placeId}`)
        }
        className="
          absolute
          border-0
          bg-transparent
          p-0
          cursor-pointer
        "
        style={{
          // ⭐ 심문하기 위치
          left: 835,
          top: 62,

          // ⭐ 버튼 크기
          width: 235,
          height: 90,

          transform: 'scale(1.1)',
        }}
      >
        <img
          src="/assets/icons/button.svg"
          alt=""
          className="
            absolute
            inset-0
            h-full
            w-full
            object-fill
          "
        />

        <span
          className="
            absolute
            inset-0
            flex
            items-center
            justify-center
            whitespace-nowrap
            font-game-korean
            tracking-[0.08em]
            text-game-ivory
          "
          style={{
            fontSize: 27,
          }}
        >
          심문하기
        </span>
      </button>

      {/* =========================================
          주변조사 버튼
      ========================================= */}
      <button
        type="button"
        onClick={() =>
          navigate(
            `/place/${placeId}/investigate`,
          )
        }
        className="
          absolute
          border-0
          bg-transparent
          p-0
          cursor-pointer
        "
        style={{
          // ⭐ 주변조사 위치
          left: 835,
          top: 165,

          // ⭐ 버튼 크기
          width: 235,
          height: 90,

          transform: 'scale(1.1)',
        }}
      >
        <img
          src="/assets/icons/button.svg"
          alt=""
          className="
            absolute
            inset-0
            h-full
            w-full
            object-fill
          "
        />

        <span
          className="
            absolute
            inset-0
            flex
            items-center
            justify-center
            whitespace-nowrap
            font-game-korean
            tracking-[0.08em]
            text-game-ivory
          "
          style={{
            fontSize: 27,
          }}
        >
          주변조사
        </span>
      </button>
    </div>
  )
}