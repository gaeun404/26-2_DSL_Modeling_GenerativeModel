/*
  누구를 심문할까.

  ★왜 필요한가 (2026-08-30, 제보 — "라운드에서 용의자 심문 칸이 없다").
    라운드 화면 메뉴는 [지도 · 사건수첩 · 대질 · 범인지목] 넷뿐이었다.
    심문은 지도 → 장소 → 그 방에 서 있는 사람을 눌러야만 닿는데, 그러면
    **그 방에 있는 사람만** 물을 수 있는 것처럼 보인다. 실제로는 다섯 명
    누구에게나 물을 수 있다. 여기서 바로 고르게 한다.

  이 선택창에서는 기본 초상만 보여 준다. 심문 중의 표정 변화는 심문 화면에만
  머물러야 이후 인물 선택에서도 당황한 얼굴이 남지 않는다.
*/

type Person = {
  id: string
  listName: string
  image: string
}

export default function InterrogatePickerModal({
  suspects,
  turnsLeft,
  onClose,
  onPick,
}: {
  suspects: Person[]
  turnsLeft: number
  onClose: () => void
  onPick: (castId: string) => void
}) {
  const outOfTurns = turnsLeft <= 0

  return (
    <div className="absolute inset-0 z-[250] bg-black/75 font-game-korean text-game-ivory">
      <button
        type="button"
        aria-label="심문 팝업 닫기"
        onClick={onClose}
        className="absolute inset-0 cursor-default border-0 bg-transparent"
      />

      <section className="absolute left-1/2 top-1/2 w-[1060px] -translate-x-1/2 -translate-y-1/2 border border-game-parchment/45 bg-[#0d0c0b] px-[54px] py-[42px] shadow-[0_20px_80px_rgba(0,0,0,0.8)]">
        <h2 className="m-0 flex items-baseline justify-between border-b border-game-parchment/25 pb-[20px] text-[30px] tracking-[0.12em]">
          누구에게 묻겠습니까
          <span className="text-[18px] tracking-[0.08em] text-game-ivory/50">
            {outOfTurns
              ? '이번 밤의 행동을 다 썼습니다'
              : `행동 1을 씁니다 · 남은 행동 ${turnsLeft}`}
          </span>
        </h2>

        <div className="mt-[30px] flex justify-between gap-[14px]">
          {suspects.map((person) => (
            <button
              key={person.id}
              type="button"
              disabled={outOfTurns}
              onClick={() => onPick(person.id)}
              className="group flex w-[186px] cursor-pointer flex-col items-center border border-white/12 bg-black/40 p-0 pb-[16px] transition-colors hover:border-game-parchment disabled:cursor-default disabled:opacity-35"
            >
              <div className="h-[218px] w-full overflow-hidden bg-black/40">
                {person.image !== '' && (
                  <img
                    src={person.image}
                    alt={person.listName}
                    className="h-full w-full object-cover object-top"
                  />
                )}
              </div>

              <span className="mt-[14px] text-[23px] tracking-[0.08em]">
                {person.listName}
              </span>
            </button>
          ))}
        </div>

        <div className="mt-[34px] flex justify-center">
          <button
            type="button"
            onClick={onClose}
            className="h-[64px] w-[200px] cursor-pointer border border-white/20 bg-black/45 text-[21px] tracking-[0.1em] text-game-ivory/75 transition-colors hover:border-game-parchment hover:text-game-ivory"
          >
            닫기
          </button>
        </div>
      </section>
    </div>
  )
}
