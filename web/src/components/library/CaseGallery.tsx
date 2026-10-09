export type LibraryCase = {
  id: string
  title: string
  origin: string

  /* CaseOpen에서 보여줄 사건 소개 문구 임시 */
  backgroundLine: string
  incidentLine: string
  endingLine1: string
  endingLine2: string

  suspects: number
  rounds: number
  difficulty: number
  coverImage: string

  category:
    | 'medieval'
    | 'folktale'
    | 'modern'

  createdAt: number
}


type CaseGalleryProps = {
  cases: LibraryCase[]
  selectedCaseId: string
  onSelect: (caseId: string) => void
}


export default function CaseGallery({
  cases,
  selectedCaseId,
  onSelect,
}: CaseGalleryProps) {
  return (
    <div className="absolute left-[70px] top-[190px] h-[610px] w-[1300px] overflow-x-auto overflow-y-hidden">

      <div className="flex w-max gap-[30px] pb-[20px]">

        {cases.map((item) => {
          const selected =
            item.id ===
            selectedCaseId


          return (
            <button
              key={item.id}
              type="button"
              onClick={() =>
                onSelect(
                  item.id,
                )
              }
              className={`
                relative
                h-[400px]
                w-[640px]
                shrink-0
                cursor-pointer
                overflow-hidden
                bg-transparent
                p-0

                ${
                  selected
                    ? 'border-2 border-game-ivory'
                    : 'border border-white/30'
                }
              `}
            >

              {/* 사건표지 */}
              {item.coverImage ? (
                <img
                  src={
                    item.coverImage
                  }
                  alt={
                    item.title
                  }
                  className="
                    h-full
                    w-full
                    object-cover
                  "
                />
              ) : (
                <div
                  className="
                    flex
                    h-full
                    w-full
                    items-center
                    justify-center

                    font-game-korean
                    text-[25px]
                    tracking-[0.1em]
                    text-game-ivory/40
                  "
                >
                  사건 표지 이미지
                </div>
              )}

            </button>
          )
        })}

      </div>

    </div>
  )
}