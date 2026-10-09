type NotebookTab = 'person' | 'clue' | 'timeline' | 'memo'

type NotebookBottomNavProps = {
  selectedTab: NotebookTab
  onSelect: (tab: NotebookTab) => void
}

const tabs: {
  id: NotebookTab
  label: string
}[] = [
  {
    id: 'person',
    label: '인물',
  },
  {
    id: 'clue',
    label: '단서',
  },
  {
    /*
      그날 밤 시간표 — 제보: "타임스탬프는 어떻게 보나요?"
      아는 것만 시간순으로 쌓인다. 비어 있는 시각이 곧 아직 못 밝힌 자리다.
    */
    id: 'timeline',
    label: '시간표',
  },
  {
    id: 'memo',
    label: '자유메모',
  },
]

export default function NotebookBottomNav({
  selectedTab,
  onSelect,
}: NotebookBottomNavProps) {
  return (
    <nav
      className="absolute"
      style={{
        left: 70,
        top: 930,

        width: 1300,
        height: 75,
      }}
    >
      {/* =========================================
          상단 가로 구분선
      ========================================= */}
      <div
        className="absolute"
        style={{
          left: 0,
          top: 0,

          width: '100%',
          height: 1,

          backgroundColor:
            'rgba(225, 216, 199, 0.55)',
        }}
      />

      {/* =========================================
          인물 | 단서 | 자유메모
      ========================================= */}
      <div
        className="absolute flex"
        style={{
          left: 0,
          top: 1,

          width: '100%',
          height: 74,
        }}
      >
        {tabs.map((tab, index) => {
          const selected =
            selectedTab === tab.id

          return (
            <div
              key={tab.id}
              className="relative flex-1"
            >
              {/* 두 번째 / 세 번째 칸 왼쪽 세로선 */}
              {index !== 0 && (
                <div
                  className="absolute"
                  style={{
                    left: 0,
                    top: 10,

                    width: 1,
                    height: 54,

                    backgroundColor:
                      'rgba(225, 216, 199, 0.45)',
                  }}
                />
              )}

              <button
                type="button"
                onClick={() =>
                  onSelect(tab.id)
                }
                className="
                  absolute
                  inset-0
                  flex
                  items-center
                  justify-center
                  border-0
                  bg-transparent
                  p-0
                  font-game-korean
                  tracking-[0.1em]
                  cursor-pointer
                "
                style={{
                  fontSize: 28,

                  color: selected
                    ? '#9b2f2f'
                    : '#e1d8c7',
                }}
              >
                {tab.label}
              </button>
            </div>
          )
        })}
      </div>
    </nav>
  )
}