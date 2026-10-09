import MainMenuItem from './MainMenuItem'

type MenuItem = {
  label: string
  icon: string
  path: string
  enabled: boolean
  lockedReason?: string
  onClick?: () => void
}

type MainMenuProps = {
  items: MenuItem[]
}

export default function MainMenu({
  items,
}: MainMenuProps) {
  return (
    <>
      {/* 하단 가로 구분선 */}
      <div className="absolute left-[86px] top-[774px] h-px w-[1268px] bg-[#8D8D86] opacity-70" />

      {/* 메뉴 전체 영역 */}
      <div className="absolute left-0 top-[774px] flex h-[250px] w-[1440px]">
        {items.map(
          (item, index) => (
            <div
              key={item.label}
              className="relative flex h-full flex-1"
            >
              {/* 메뉴 사이 세로 구분선 */}
              {index !== 0 && (
                <div className="absolute left-0 top-0 z-10 h-full w-px bg-[#8D8D86] opacity-70" />
              )}

              <MainMenuItem
                label={item.label}
                icon={item.icon}
                path={item.path}
                enabled={item.enabled}
                lockedReason={item.lockedReason}
                onClick={item.onClick}
              />
            </div>
          ),
        )}
      </div>
    </>
  )
}
