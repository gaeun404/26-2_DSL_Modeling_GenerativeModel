import type {
  LibraryCase,
} from './CaseGallery'

type CaseInfoProps = {
  selectedCase: LibraryCase
  onStart: () => void
}

export default function CaseInfo({
  selectedCase,
  onStart,
}: CaseInfoProps) {
  return (
    <>
      {/* 선택한 사건 정보 */}
      <div className="absolute left-[70px] top-[825px] flex h-[90px] w-[980px] items-center border border-white/30 px-[30px] font-game-korean text-[22px] tracking-[0.1em] text-game-ivory">

        {/* 사건 제목 */}
        {selectedCase.title}

        <span className="mx-[15px]">
          ·
        </span>

        용의자 {selectedCase.suspects}명

        <span className="mx-[15px]">
          ·
        </span>

        {selectedCase.rounds}라운드

        <span className="mx-[15px]">
          ·
        </span>

        난이도{' '}
        {'★'.repeat(
          selectedCase.difficulty,
        )}
        {'☆'.repeat(
          5 - selectedCase.difficulty,
        )}
      </div>

      {/* 이 사건으로 시작 */}
      <button
        type="button"
        onClick={onStart}
        className="absolute left-[1080px] top-[797px] h-[150px] w-[290px] cursor-pointer border-0 bg-transparent p-0"
      >
        <img
          src="/assets/icons/button.svg"
          alt=""
          className="pointer-events-none absolute inset-0 h-full w-full object-fill"
        />

        <span className="pointer-events-none absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean text-[21px] tracking-[0.1em] text-game-ivory">
          이 사건으로 시작
        </span>
      </button>
    </>
  )
}