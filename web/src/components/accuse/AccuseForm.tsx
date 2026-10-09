import { useRef } from 'react'

type AccuseFormProps = {
  tool: string
  toolOptions: string[]
  method: string
  motive: string

  onToolChange: (value: string) => void
  onMethodChange: (value: string) => void
  onMotiveChange: (value: string) => void

  onSubmit: () => void
}

export default function AccuseForm({
  tool,
  toolOptions,
  method,
  motive,
  onToolChange,
  onMethodChange,
  onMotiveChange,
  onSubmit,
}: AccuseFormProps) {
  const methodRef =
    useRef<HTMLInputElement>(null)

  const motiveRef =
    useRef<HTMLInputElement>(null)

  const fields = [
    {
      id: 'method',
      label: '범행 방법',
      value: method,
      placeholder: '방법을 입력하세요',
      onChange: onMethodChange,
      inputRef: methodRef,
    },
    {
      id: 'motive',
      label: '범행 동기',
      value: motive,
      placeholder: '동기를 입력하세요',
      onChange: onMotiveChange,
      inputRef: motiveRef,
    },
  ]

  const handleEnter = (
    fieldId: string,
  ) => {
    if (fieldId === 'method') {
      motiveRef.current?.focus()
      return
    }

    if (fieldId === 'motive') {
      onSubmit()
    }
  }

  return (
    <section
      className="absolute"
      style={{
        left: 100,
        top: 590,

        width: 900,
        height: 270,
      }}
    >
      <div
        className="absolute"
        style={{ left: 0, top: 0, width: 900, height: 72 }}
      >
        <div
          className="absolute flex items-center font-game-korean tracking-[0.08em] text-game-ivory"
          style={{ left: 0, top: 0, width: 190, height: 72, fontSize: 27 }}
        >
          범행 도구
        </div>

        <div
          className="absolute flex items-center gap-[8px]"
          style={{ left: 238, top: 0, width: 780, height: 72 }}
        >
          {toolOptions.map((option) => {
            const selected = tool === option

            return (
              <button
                key={option}
                type="button"
                onClick={() => onToolChange(option)}
                className="h-[68px] min-w-0 flex-1 cursor-pointer px-[10px] font-game-korean leading-[1.2] tracking-[0.02em]"
                style={{
                  border: selected
                    ? '1px solid #8a3830'
                    : '1px solid rgba(154, 141, 114, 0.55)',
                  backgroundColor: selected
                    ? 'rgba(138, 56, 48, 0.28)'
                    : 'rgba(10, 9, 7, 0.75)',
                  color: selected ? '#e1d8c7' : '#9a8d72',
                  fontSize: 16,
                }}
              >
                {option}
              </button>
            )
          })}
        </div>
      </div>

      {fields.map(
        (field, index) => (
          <div
            key={field.id}
            className="absolute"
            style={{
              left: 0,
              top: (index + 1) * 85,

              width: 900,
              height: 72,
            }}
          >
            {/*입력창 이름= */}
            <div
              className="
                absolute
                flex
                items-center
                font-game-korean
                tracking-[0.08em]
                text-game-ivory
              "
              style={{
                left: 0,
                top: 0,

                width: 190,
                height: 72,

                fontSize: 27,
              }}
            >
              {field.label}
            </div>

            {/* 입력창 */}
            <div
              className="absolute"
              style={{
                left: 200,
                top: 0,

                // ⭐ 입력창 전체 크기
                width: 690,
                height: 72,
                transform : 'scaleX(1.5)'
              }}
            >
              <img
                src="/assets/icons/chat.svg"
                alt=""
                className="
                  absolute
                  inset-0
                  h-full
                  w-full
                  object-fill
                "
              />

              {/* 실제 입력 */}
              <input
                ref={field.inputRef}
                type="text"
                value={field.value}
                onChange={(event) =>
                  field.onChange(
                    event.target.value,
                  )
                }
                onKeyDown={(event) => {
                  if (
                    event.key ===
                    'Enter'
                  ) {
                    event.preventDefault()

                    handleEnter(
                      field.id,
                    )
                  }
                }}
                placeholder={
                  field.placeholder
                }
                className="
                  absolute
                  border-0
                  bg-transparent
                  outline-none
                  font-game-korean
                  tracking-[0.06em]
                  text-game-ivory
                  placeholder:text-white/25
                "
                style={{
                  left: 70,
                  top: 10,

                  width: 610,
                  height: 52,

                  fontSize: 21,

                  transform: 'scaleX(0.7)'
                }}
              />
            </div>
          </div>
        ),
      )}
    </section>
  )
}
