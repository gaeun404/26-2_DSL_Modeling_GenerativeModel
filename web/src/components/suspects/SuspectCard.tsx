interface SuspectCardProps {
  name: string
  image: string
  selected: boolean
  onClick: () => void
}

/*
  ★사진을 액자 창에 맞춘다 (2026-08-29, 2차 제보 — "suspect 이미지도 칸에 맞춰줄 수 있나").

    액자(suspect_frame.svg)는 세로로 긴 창을 가진 그림인데, 사진을 그 창이
    아니라 **왼쪽 위 구석에 150 × 150 정사각형**으로 얹고 있었다. 초상은
    512 × 768 세로 그림이라, 오른쪽과 아래가 액자 안에서 텅 비고 얼굴은
    잘렸다. 액자 바깥 크기(200 × 270)와 버튼 크기(170 × 230)도 어긋나 있어
    아래 이름과 겹쳤다.

    창의 자리는 그림의 알파에서 재 왔다 — 왼쪽 6.47% · 위 5.30% ·
    가로 86.98% · 세로 87.37%. 비율로 두면 액자를 키우고 줄여도 따라온다.
*/
const WINDOW = {
  left: '6.47%',
  top: '5.30%',
  width: '86.98%',
  height: '87.37%',
}

const FRAME_W = 200
const FRAME_H = 270

export default function SuspectCard({
  name,
  image,
  selected,
  onClick,
}: SuspectCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{ width: FRAME_W }}
      className="relative cursor-pointer border-0 bg-transparent p-0"
    >
      {/* 액자 */}
      <div
        style={{ width: FRAME_W, height: FRAME_H }}
        className={`relative transition-all duration-300 ${
          selected ? 'scale-[1.04] brightness-125' : ''
        }`}
      >
        {/* 사진 — 액자 창 안에 꽉 채운다 */}
        <div
          className="absolute z-10 overflow-hidden bg-black/40"
          style={WINDOW}
        >
          {image !== '' ? (
            <img
              src={image}
              alt={name}
              className="h-full w-full object-cover object-top"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center font-game-korean text-[17px] tracking-[0.08em] text-white/25">
              인물 사진
            </div>
          )}
        </div>

        <img
          src="/assets/icons/suspect_frame.svg"
          alt=""
          className="pointer-events-none absolute inset-0 z-20 h-full w-full object-fill"
        />
      </div>

      {/* 인물 이름 */}
      <div className="mt-[14px] w-full whitespace-nowrap text-center font-game-korean text-[34px] tracking-[0.1em] text-game-ivory">
        {name}
      </div>
    </button>
  )
}
