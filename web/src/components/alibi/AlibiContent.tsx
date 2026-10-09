type AlibiContentProps = {
  image: string
  alibi: string
}

export default function AlibiContent({
  image,
  alibi,
}: AlibiContentProps) {
  return (
    <>
      {/* 용의자 사진 */}
      <div
        className="absolute overflow-hidden"
        style={{
          left: 70,
          top: 189,
          width: 573,
          height: 668,
          border:
            '1px solid rgba(225, 216, 199, 0.6)',
        }}
      >
        {/*
          TODO(API / IMAGE):
          나중에 생성된 용의자 이미지 URL 사용
        */}

        {image !== '' ? (
          <img
            src={image}
            alt="용의자"
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center font-game-korean text-[25px] tracking-[0.1em] text-white/30">
            인물 사진 영역
          </div>
        )}
      </div>

      {/* 대화창 */}
      <div
        className="absolute flex items-center justify-center"
        style={{
          left: 797,
          top: 189,
          width: 573,
          height: 668,
          border:
            '1px solid rgba(225, 216, 199, 0.65)',
          backgroundColor:
            'rgba(0, 0, 0, 0.35)',
        }}
      >
        {/* 알리바이 내용 */}
        <div
          className="whitespace-pre-line text-center font-game-korean tracking-[0.1em] text-game-ivory"
          style={{
            width: 448,
            fontSize: 30,
            lineHeight: 4.6,
          }}
        >
          {alibi}
        </div>
      </div>

      {/* 하단 줄 장식 */}
      <img
        src="/assets/icons/line.svg"
        alt=""
        className="absolute object-fill"
        style={{
          left: 434,
          top: 927,
          width: 573,
          height: 53,
        }}
      />
    </>
  )
}