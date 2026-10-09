import Title from '../common/Title'

export default function CaseStartTitle() {
  return (
    <>
      {/* CASE ARCHIVE  */}
      <div
        className="
          absolute
          left-[70px]
          top-[55px]

          font-game-korean
          text-[22px]
          tracking-[0.15em]
          text-game-ivory
        "
      >
        CASE ARCHIVE · 01
      </div>


      {/*  공통 제목 + 돋보기  */}
      <Title
        text={'어떤 이야기에서\n사건을 시작할까요?'}
        className="
          absolute
          left-[270px]
          top-[187px]


          flex
          h-[210px]
          w-[900px]
          items-center
          justify-center

          leading-[120px]
        "
        decorationClassName="
          left-[460px]
          top-[60px]
          h-[390px]
          w-[520px]
        "
      />


      {/* 설명 */}
      <div
        className="
          absolute
          left-[501px]
          top-[500px]

          flex
          h-[60px]
          w-[436px]
          items-center
          justify-center

          whitespace-nowrap
          font-game-korean
          text-[30px]
          leading-[60px]
          tracking-[0.1em]
          text-game-ivory
        "
      >
        원하는 세계관을 입력해 주세요.
      </div>
    </>
  )
}