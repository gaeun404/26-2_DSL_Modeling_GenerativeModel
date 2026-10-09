import type { NotebookPerson } from '../../pages/NotebookPage'

import PersonChoice from './PersonChoice'

type PersonListProps = {
  persons: NotebookPerson[]
  selectedPersonId: string
  onSelect: (id: string) => void
}

export default function PersonList({
  persons,
  selectedPersonId,
  onSelect,
}: PersonListProps) {
  return (
    <section
      className="absolute"
      style={{
        // 왼쪽 선택 영역
        left: 35,
        top: 170,

        width: 380,
        height: 850,
      }}
    >
      

      {/* =====================================
          인물 리스트

          ★다섯이 다 보이게 (2026-08-30).
            620px 에 155px 짜리를 넣어 네 사람만 보였다. 다섯째가 스크롤
            아래 숨는데, 이 편에서는 그게 하필 **범인**이다.
            상자를 780 으로 늘려 다섯이 한눈에 들어오게 한다.
      ===================================== */}
      <div
        className="
          flex
          flex-col
          overflow-y-auto
        "
        style={{
          width: 365,
          height: 790,

          gap: 0,

          paddingRight: 10,
        }}
      >
        {persons.map((person) => (
          <PersonChoice
            key={person.id}
            person={person}
            selected={
              person.id ===
              selectedPersonId
            }
            onClick={() =>
              onSelect(person.id)
            }
          />
        ))}
      </div>
    </section>
  )
}