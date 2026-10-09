import { useState } from 'react'

type ConfrontationEntryModalProps = {
  suspects: Array<{ id: string; listName: string }>
  unlocked: boolean
  alreadyUsed: boolean
  /*
    ★시나리오가 고른 「말이 어긋나는 짝」 (팀원 제보 —
      "대질심문에 사람이 한 명으로 뜬다").
      아무나 맞세울 수도 있지만, 이 짝들이 실제로 어긋난다.
  */
  pairs?: Array<{ a: string; b: string; aName: string; bName: string }>
  onClose: () => void
  onConfirm: (pair: [string, string]) => void
}

export default function ConfrontationEntryModal({
  suspects,
  unlocked,
  alreadyUsed,
  pairs = [],
  onClose,
  onConfirm,
}: ConfrontationEntryModalProps) {
  const [firstId, setFirstId] = useState<string | null>(null)
  const [secondId, setSecondId] = useState<string | null>(null)
  const [confirming, setConfirming] = useState(false)

  const locked = !unlocked || alreadyUsed
  const lockedTitle = alreadyUsed
    ? '이미 대질을 사용했습니다'
    : '아직 맞대 놓을 수 없다'
  const lockedDescription = alreadyUsed
    ? '대질은 한 판에 한 번뿐입니다.'
    : '사람을 맞대 놓으려면 판이 한 번 뒤집혀야 한다.'

  return (
    <div className="absolute inset-0 z-[250] bg-black/75 font-game-korean text-game-ivory">
      <button
        type="button"
        aria-label="대질 팝업 닫기"
        onClick={onClose}
        className="absolute inset-0 cursor-default border-0 bg-transparent"
      />

      <section className="absolute left-1/2 top-1/2 w-[820px] -translate-x-1/2 -translate-y-1/2 border border-game-parchment/45 bg-[#0d0c0b] px-[58px] py-[45px] shadow-[0_20px_80px_rgba(0,0,0,0.8)]">
        {locked ? (
          <>
            <div className="border border-game-parchment/25 px-[38px] py-[32px]">
              <h2 className="m-0 text-[30px] tracking-[0.1em]">
                🔒 {lockedTitle}
              </h2>
              <p className="mb-0 mt-[18px] text-[21px] leading-[1.7] text-game-ivory/65">
                {lockedDescription}
              </p>
            </div>
            <div className="mt-[24px] border border-game-parchment/25 py-[22px] text-center text-[20px] text-game-ivory/60">
              토큰·행동 예산은 그대로 유지됩니다.
            </div>
            <ActionButton label="닫기" onClick={onClose} centered />
          </>
        ) : confirming && firstId && secondId ? (
          <>
            <h2 className="m-0 border-b border-game-parchment/25 pb-[24px] text-[34px] tracking-[0.12em]">
              대질 확인
            </h2>
            {/* 값을 정확히 말해 준다 — 「지금 맞세울까, 한 번 더 물을까」가 여기서 갈린다 */}
            <div className="my-[42px] border-l-[3px] border-game-red-light bg-game-red/20 px-[32px] py-[30px] text-[25px] leading-[1.7]">
              대질은 한 판에 한 번뿐이고 <b className="text-game-parchment">행동 1</b>을 씁니다.<br />
              되돌릴 수 없습니다.
            </div>
            <p className="text-center text-[22px] text-game-parchment">
              {nameOf(suspects, firstId)} · {nameOf(suspects, secondId)}
            </p>
            <div className="mt-[38px] flex justify-center gap-[24px]">
              <ActionButton
                label="조금 더 생각한다"
                onClick={() => setConfirming(false)}
              />
              <ActionButton
                label="맞대 놓는다"
                onClick={() => onConfirm([firstId, secondId])}
                primary
              />
            </div>
          </>
        ) : (
          <>
            <h2 className="m-0 border-b border-game-parchment/25 pb-[24px] text-[34px] tracking-[0.12em]">
              대질 상대 고르기
            </h2>
            <PersonSelector
              label="누구를 앉힐까요?"
              selectedId={firstId}
              excludedId={secondId}
              onSelect={setFirstId}
              suspects={suspects}
            />
            <PersonSelector
              label="누구와 맞대 놓을까요?"
              selectedId={secondId}
              excludedId={firstId}
              onSelect={setSecondId}
              suspects={suspects}
            />

            {/* =================================
                말이 어긋나는 짝

                아무나 맞세울 수 있지만, 이 짝들은 시나리오가 실제로
                어긋나게 짜 둔 것이다. 한 번뿐인 기회라 길잡이를 준다.
            ================================= */}
            {pairs.length > 0 && (
              <div className="mt-[26px] border-t border-game-parchment/20 pt-[20px]">
                <p className="m-0 mb-[12px] text-[17px] tracking-[0.06em] text-game-ivory/50">
                  말이 어긋나는 짝
                </p>
                <div className="flex flex-wrap gap-[10px]">
                  {pairs.map((pair) => {
                    const picked =
                      (firstId === pair.a && secondId === pair.b) ||
                      (firstId === pair.b && secondId === pair.a)

                    return (
                      <button
                        key={`${pair.a}-${pair.b}`}
                        type="button"
                        onClick={() => {
                          setFirstId(pair.a)
                          setSecondId(pair.b)
                        }}
                        className={`cursor-pointer border px-[16px] py-[9px] text-[17px] tracking-[0.04em] transition-colors ${
                          picked
                            ? 'border-game-parchment bg-game-gold/15 text-game-ivory'
                            : 'border-game-parchment/30 bg-black/40 text-game-ivory/65 hover:border-game-parchment/70'
                        }`}
                      >
                        {pair.aName} · {pair.bName}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            <div className="mt-[32px] flex justify-center gap-[24px]">
              <ActionButton label="닫기" onClick={onClose} />
              <ActionButton
                label="다음"
                onClick={() => setConfirming(true)}
                disabled={!firstId || !secondId}
                primary
              />
            </div>
          </>
        )}
      </section>
    </div>
  )
}

function PersonSelector({
  label,
  selectedId,
  excludedId,
  onSelect,
  suspects,
}: {
  label: string
  selectedId: string | null
  excludedId: string | null
  onSelect: (id: string) => void
  suspects: Array<{ id: string; listName: string }>
}) {
  return (
    <div className="mt-[30px]">
      <p className="mb-[16px] text-[22px] text-game-ivory/75">
        {label}
      </p>
      <div className="flex gap-[12px]">
        {suspects.map((suspect) => {
          const disabled = suspect.id === excludedId
          const selected = suspect.id === selectedId
          return (
            <button
              key={suspect.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(suspect.id)}
              className={`h-[58px] flex-1 border text-[19px] transition-colors ${
                selected
                  ? 'border-game-red-light bg-game-red/30 text-game-ivory'
                  : 'border-game-parchment/30 bg-black/30 text-game-ivory/65'
              } disabled:cursor-default disabled:opacity-20`}
            >
              {suspect.listName}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function ActionButton({
  label,
  onClick,
  disabled = false,
  primary = false,
  centered = false,
}: {
  label: string
  onClick: () => void
  disabled?: boolean
  primary?: boolean
  centered?: boolean
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`${centered ? 'mx-auto mt-[28px] block' : ''} h-[68px] min-w-[220px] cursor-pointer border border-game-parchment/35 px-[24px] text-[20px] tracking-[0.06em] text-game-ivory disabled:cursor-default disabled:opacity-25 ${
        primary ? 'bg-game-red/40' : 'bg-black/35'
      }`}
    >
      {label}
    </button>
  )
}

function nameOf(
  suspects: Array<{ id: string; listName: string }>,
  id: string,
) {
  return suspects.find((suspect) => suspect.id === id)?.listName ?? id
}
