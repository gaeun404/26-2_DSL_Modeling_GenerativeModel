import VictimCard from './VictimCard'
import type { VictimData } from './VictimCard'

type VictimScreenProps = {
  victim: VictimData
  onContinue: () => void
}

export default function VictimScreen({
  victim,
  onContinue,
}: VictimScreenProps) {
  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-game-bg bg-[url('/assets/icons/title-background.svg')] bg-[length:100%_100%] bg-no-repeat">

      {/* VICTIM 제목 */}
      <div className="absolute left-[430px] top-[28px] flex h-[86px] w-[580px] items-center justify-center">
        <div className="mr-[24px] h-[1px] w-[100px] bg-[#b9aa8c]/45" />

        <h1 className="m-0 font-serif text-[58px] tracking-[0.12em] text-game-ivory">
          VICTIM
        </h1>

        <div className="ml-[24px] h-[1px] w-[100px] bg-[#b9aa8c]/45" />
      </div>

      {/* 피해자 카드 */}
      <VictimCard victim={victim} />

      {/* 계속하기 버튼 */}
      <button
        type="button"
        onClick={onContinue}
        className="absolute left-[950px] top-[900px] z-50 h-[117px] w-[450px] cursor-pointer border-0 bg-transparent p-0"
      >
        <img
          src="/assets/icons/button.svg"
          alt=""
          className="absolute inset-0 h-full w-full object-fill"
        />

        <span className="absolute inset-0 flex -translate-x-[10px] -translate-y-[5px] items-center justify-center whitespace-nowrap font-game-korean text-[20px] tracking-[0.08em] text-game-ivory">
          계속하기
        </span>
      </button>
    </main>
  )
}
