import type { ReactNode } from 'react'

interface StoryTextFrameProps {
  story: ReactNode
  align?: 'left' | 'center'
  width?: number
}

/*
  ★글이 상자를 넘던 것을 고친다 (2026-08-29, 시연 제보).
    제보: "인트로 설명 텍스트가 잘린다 · 글이랑 버튼이랑 칸이 꼬인다."

    줄간격이 100px 이었다. 글자는 30px인데. 한 줄짜리 짧은 쪽에서는 가운데
    맞춤처럼 보여 괜찮았지만, 서버가 오프닝을 130자로 묶으면서 세 줄이 되자
    300px — 280px 상자를 그냥 넘어갔다. 게다가 버튼이 상자 위에 겹쳐 있었다.

    줄간격을 글자에 맞추고(1.85), 상자를 줄여 버튼 자리를 아래로 비웠다.

  ★그런데 **테두리가 글보다 작았다** (2026-08-29, 4차 제보).
    제보: "처음 스토리 나올 때 박스가 글보다 작아."

    글을 줄인 것만으로는 안 됐다. StoryFrame.svg 는 제 비율(1124:337)을
    지킨다 — object-fill 로도 안 늘어난다. 그걸 1124×248(4.53:1) 상자에
    넣으니 세로에 맞춰 줄어들어 **827px 폭으로만 그려졌다.** 글은 984px 로
    흐르고 있었으니, 글이 테두리 양옆으로 삐져나간 것이다.

    상자를 그림 비율(1124×337)로 되돌린다. 그러면 테두리가 상자를 꽉 채운다.
    자리를 내려고 위 삽화를 조금 줄였다. 버튼은 테두리 아래로 내렸다.

    ※ 서현이 같은 자리를 글자 크기로 막아 두었었다(26px → 20px, aeede91).
      좁은 테두리에 글을 욱여넣던 임시 처방이다. 테두리가 제 폭을 찾았으니
      20px 은 이제 너무 작다 — 1032px 폭에 세 줄이 뜨고 상자가 텅 빈다.
      25px 로 둔다. 더 작게 하고 싶으면 이 한 줄만 고치면 된다.
*/
export default function StoryTextFrame({
  story,
  align = 'left',
}: StoryTextFrameProps) {
  return (
    <div className="absolute left-[158px] top-[598px] h-[337px] w-[1124px]">

      {/* 글 프레임 */}
      <img
        src="/assets/icons/StoryFrame.svg"
        alt=""
        className="absolute inset-0 h-full w-full object-fill"
      />

      {/* 이야기 글 */}
      <div
        className={`
          absolute
          left-[46px]
          top-[42px]

          flex
          h-[196px]
          w-[1032px]

          items-center

          font-game-korean
          text-[25px]
          leading-[1.85]
          tracking-[0.05em]

          text-game-ivory

          ${
            align === 'center'
              ? 'justify-center text-center'
              : 'justify-start text-left'
          }
        `}
      >
        {story}
      </div>

    </div>
  )
}
