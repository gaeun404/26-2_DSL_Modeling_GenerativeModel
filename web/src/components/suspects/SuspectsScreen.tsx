import SuspectCard from './SuspectCard'

type SuspectItem = {
  id: string
  name: string
  image: string
}

type SuspectsScreenProps = {
  suspects: SuspectItem[]
  onSuspectClick: (suspectId: string) => void
  onStartInvestigation: () => void
  onBack: () => void
}

export default function SuspectsScreen({
  suspects,
  onSuspectClick,
  onStartInvestigation,
  onBack,
}: SuspectsScreenProps) {
  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-game-bg">
      {/* 배경 */}
      <img
        src="/assets/icons/title-background.svg"
        alt=""
        className="absolute inset-0 h-full w-full object-fill"
      />

      {/* SUSPECTS 제목 */}
      <div className="absolute left-[430px] top-[64px] flex h-[100px] w-[580px] items-center justify-center">
        <div className="mr-[24px] h-[1px] w-[100px] bg-[#b9aa8c]/45" />

        <h1 className="m-0 font-serif text-[70px] tracking-[0.12em] text-game-ivory">
          SUSPECTS
        </h1>

        <div className="ml-[24px] h-[1px] w-[100px] bg-[#b9aa8c]/45" />
      </div>

      {/* 용의자 5명 */}
      <div className="absolute left-[50px] top-[300px] flex w-[1324px] items-start justify-between">
        {suspects.map((suspect) => (
          <SuspectCard
            key={suspect.id}
            name={suspect.name}
            image={suspect.image}
            selected={false}
            onClick={() => onSuspectClick(suspect.id)}
          />
        ))}
      </div>

      {/* 안내 문구 */}
      <div className="absolute left-[370px] top-[665px] flex h-[80px] w-[700px] items-center justify-center whitespace-nowrap font-game-korean text-[34px] tracking-[0.06em] text-game-ivory">
        인물을 선택해 확인하세요.
      </div>

      {/* 하단 장식 */}
      <img
        src="/assets/icons/line.svg"
        alt=""
        className="absolute left-[379px] top-[745px] h-[63px] w-[682px] object-fill"
      />

      {/*
        ★「조사를 시작한다」가 뒤로가기처럼 느껴지던 것을 고친다
          (2026-08-29, 시연 제보).
          여기서 /main 으로 보내니, 방금 온 곳으로 돌아갈 뿐이라
          "이전 버튼과 같은 효과"로 보였다. 조사는 지도에서 시작한다 —
          지도로 보내고, 돌아가는 길은 따로 둔다.
      */}
      <button
        type="button"
        onClick={onBack}
        className="absolute left-[56px] top-[40px] cursor-pointer border-0 bg-transparent p-0 font-game-korean text-[24px] tracking-[0.08em] text-game-ivory/70"
      >
        &lt; 돌아가기
      </button>

      <button
        type="button"
        onClick={onStartInvestigation}
        className="absolute left-[950px] top-[900px] h-[117px] w-[450px] cursor-pointer border-0 bg-transparent p-0"
      >
        <img
          src="/assets/icons/button.svg"
          alt=""
          className="absolute inset-0 h-full w-full object-fill"
        />
        <span className="absolute inset-0 z-10 flex -translate-x-[10px] -translate-y-[5px] items-center justify-center whitespace-nowrap font-game-korean text-[20px] leading-none tracking-[0.08em] text-game-ivory">
          조사를 시작한다
        </span>
      </button>
    </main>
  )
}
