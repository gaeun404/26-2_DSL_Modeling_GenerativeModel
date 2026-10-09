type ConfirmDialogProps = {
  title: string
  description: string
  cancelLabel: string
  confirmLabel: string
  onCancel: () => void
  onConfirm: () => void
}

export default function ConfirmDialog({
  title,
  description,
  cancelLabel,
  confirmLabel,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <>
      <button
        type="button"
        aria-label="팝업 닫기"
        onClick={onCancel}
        className="absolute inset-0 z-40 cursor-default border-0 bg-black/70"
      />
      <div className="absolute left-1/2 top-1/2 z-50 h-[390px] w-[700px] -translate-x-1/2 -translate-y-1/2">
        <img
          src="/assets/icons/StoryFrame.svg"
          alt=""
          className="absolute inset-0 h-full w-full object-fill"
        />
        <div className="absolute left-[70px] top-[62px] flex h-[135px] w-[560px] flex-col items-center justify-center gap-[14px] text-center font-game-korean text-game-ivory">
          <p className="m-0 text-[30px] tracking-[0.1em]">
            {title}
          </p>
          <p className="m-0 text-[20px] tracking-[0.06em] text-game-ivory/70">
            {description}
          </p>
        </div>
        {[
          [cancelLabel, onCancel],
          [confirmLabel, onConfirm],
        ].map(([label, onClick], index) => (
          <button
            key={label as string}
            type="button"
            onClick={onClick as () => void}
            className={`absolute top-[225px] h-[120px] w-[250px] cursor-pointer border-0 bg-transparent p-0 ${
              index === 0 ? 'left-[75px]' : 'left-[375px]'
            }`}
          >
            <img
              src="/assets/icons/button.svg"
              alt=""
              className="absolute inset-0 h-full w-full object-fill"
            />
            <span className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean text-[22px] tracking-[0.08em] text-game-ivory">
              {label as string}
            </span>
          </button>
        ))}
      </div>
    </>
  )
}
