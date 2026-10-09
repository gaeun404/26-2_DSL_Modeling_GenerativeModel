import GenerateButton from './GenerateButton'

type CaseStartActionsProps = {
  onOpenLibrary: () => void
  onGenerate: () => void
  generateDisabled: boolean
}

export default function CaseStartActions({
  onOpenLibrary,
  onGenerate,
  generateDisabled,
}: CaseStartActionsProps) {
  return (
    <>
      {/* 미리 준비된 사건 보기 */}
      <div className="absolute left-[172px] top-[782px] ">
        <GenerateButton
          text="미리 준비된 사건 보기"
          onClick={onOpenLibrary}
          disabled={false}
          textOffsetX={-19}
          textOffsetY={-5}
        />
      </div>

      {/* 생성하기 */}
      <div className="absolute left-[918px] top-[782px]">
        <GenerateButton
          text="생성하기"
          onClick={onGenerate}
          disabled={generateDisabled}
          textOffsetY={-5}
        />
      </div>
    </>
  )
}
