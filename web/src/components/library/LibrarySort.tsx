type SortType =
  | 'recent'
  | 'difficulty'
  | 'category'

type StoryCategory =
  | 'medieval'
  | 'folktale'
  | 'modern'

type LibrarySortProps = {
  sortType: SortType
  categoryOpen: boolean

  onSortChange: (
    sortType: SortType,
  ) => void

  onCategoryOpen: () => void

  onCategoryChange: (
    category: StoryCategory,
  ) => void
}

export default function LibrarySort({
  sortType,
  categoryOpen,
  onSortChange,
  onCategoryOpen,
  onCategoryChange,
}: LibrarySortProps) {
  return (
    <div className="absolute left-[930px] top-[125px] z-30 flex items-center gap-[18px] font-game-korean text-[20px] tracking-[0.1em] text-game-ivory">

      <button
        type="button"
        onClick={() =>
          onSortChange('recent')
        }
        className={`cursor-pointer border-0 bg-transparent p-0 ${
          sortType === 'recent'
            ? 'text-game-ivory'
            : 'text-game-ivory/50'
        }`}
      >
        최근순
      </button>

      <span>·</span>

      <button
        type="button"
        onClick={() =>
          onSortChange('difficulty')
        }
        className={`cursor-pointer border-0 bg-transparent p-0 ${
          sortType === 'difficulty'
            ? 'text-game-ivory'
            : 'text-game-ivory/50'
        }`}
      >
        난이도순
      </button>

      <span>·</span>

      <div className="relative">
        <button
          type="button"
          onClick={onCategoryOpen}
          className={`cursor-pointer border-0 bg-transparent p-0 ${
            sortType === 'category'
              ? 'text-game-ivory'
              : 'text-game-ivory/50'
          }`}
        >
          계열
        </button>

        {categoryOpen && (
          <div className="absolute right-0 top-[35px] z-50 w-[150px] border border-white/30 bg-game-bg">

            <button
              type="button"
              onClick={() =>
                onCategoryChange(
                  'medieval',
                )
              }
              className="block h-[45px] w-full cursor-pointer border-0 bg-transparent font-game-korean text-[17px] text-game-ivory"
            >
              중세
            </button>

            <button
              type="button"
              onClick={() =>
                onCategoryChange(
                  'folktale',
                )
              }
              className="block h-[45px] w-full cursor-pointer border-0 bg-transparent font-game-korean text-[17px] text-game-ivory"
            >
              전래동화
            </button>

            <button
              type="button"
              onClick={() =>
                onCategoryChange(
                  'modern',
                )
              }
              className="block h-[45px] w-full cursor-pointer border-0 bg-transparent font-game-korean text-[17px] text-game-ivory"
            >
              현대
            </button>

          </div>
        )}
      </div>

    </div>
  )
}

export type {
  SortType,
  StoryCategory,
}