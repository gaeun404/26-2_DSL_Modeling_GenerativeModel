import type { NotebookClue } from '../../pages/NotebookPage'

import ClueChoice from './ClueChoice'

type ClueListProps = {
  clues: NotebookClue[]
  selectedClueId: string
  onSelect: (id: string) => void
}

export default function ClueList({
  clues,
  selectedClueId,
  onSelect,
}: ClueListProps) {
  /*
    단서가 4개 이상 모이면
    스크롤 가능한 목록으로 변경.

    실제 내용이 영역을 넘을 때
    스크롤바가 나타남.
  */
  const shouldScroll =
    clues.length >= 4

  return (
    <section
      className="absolute"
      style={{
        // ⭐ PersonList와 완전히 동일
        left: 35,
        top: 170,

        width: 380,
        height: 850,
      }}
    >
      <div
        className="flex flex-col"
        style={{
          // ⭐ PersonList와 동일
          width: 365,
          height: 620,

          gap: 0,

          paddingRight: 10,

          overflowY: shouldScroll
            ? 'auto'
            : 'hidden',
        }}
      >
        {clues.map((clue) => (
          <ClueChoice
            key={clue.id}
            clue={clue}
            selected={
              clue.id ===
              selectedClueId
            }
            onClick={() =>
              onSelect(clue.id)
            }
          />
        ))}
      </div>
    </section>
  )
}