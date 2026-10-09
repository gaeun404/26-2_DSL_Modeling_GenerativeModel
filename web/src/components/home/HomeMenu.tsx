import MenuButton from '../common/MenuButton'

type HomeMenuProps = {
  onStartCase: () => void
  onContinue: () => void
  onSettings: () => void
}

export default function HomeMenu({
  onStartCase,
  onContinue,
  onSettings,
}: HomeMenuProps) {
  return (
    <div className="absolute left-1/2 top-[577px] z-10 flex w-[550px] -translate-x-1/2 flex-col gap-[12px] bg-black/25 px-[15px] py-[17px]">
      <MenuButton
        src="/assets/icons/title-playbutton.svg"
        onClick={onStartCase}
        width={520}
        height={100}
      >
        사건 시작
      </MenuButton>

      <MenuButton
        src="/assets/icons/title-archivebutton.svg"
        onClick={onContinue}
        width={520}
        height={79}
      >
        이어서 조사하기
      </MenuButton>

      <MenuButton
        src="/assets/icons/title-settingbutton.svg"
        onClick={onSettings}
        width={520}
        height={79}
      >
        멀티플레이
      </MenuButton>
    </div>
  )
}