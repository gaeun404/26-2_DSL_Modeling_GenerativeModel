import { useGameStore } from '../../store/gameStore'

export default function FreeMemoPanel() {
  const memo = useGameStore((state) => state.freeMemo)
  const setMemo = useGameStore((state) => state.setFreeMemo)

  return (
    <>
      {/* =====================================
          자유메모 전체 영역

          Header 아래 ~ BottomNav 위
      ===================================== */}
      <section
        className="absolute"
        style={{
          left: 30,
          top: 115,

          width: 1380,
          height: 775,
        }}
      >
        {/* =====================================
            왼쪽 안내 패널
            person_card.svg 재사용
        ===================================== */}
        {/*
          ★안내 카드를 흐름 배치로 (2026-08-30).
            세 덩이가 절대좌표(190/320/430)로 박혀 있었는데, 부모의 scaleY(1.5)를
            걷어내자 카드보다 아래로 밀려났다. 늘림에 기대어 자리를 잡고 있었던 것이다.
            액자 비율(206:259)에 맞춘 상자 안에서 세로로 흐르게 둔다.
        */}
        <div
          className="absolute"
          style={{ left: 0, top: 20, width: 350, height: 440 }}
        >
          <img
            src="/assets/icons/person_card.svg"
            alt=""
            className="pointer-events-none absolute inset-0 h-full w-full object-fill"
          />

          <div className="absolute inset-x-[38px] top-[46px] bottom-[42px] flex flex-col justify-center gap-[16px] text-center font-game-korean tracking-[0.04em] text-game-ivory">
            <p className="m-0 text-[19px] leading-[1.75]">
              이 곳에서는 인물이나 단서에 구애받지 않고
              자유롭게 메모를 작성할 수 있습니다.
            </p>

            <img src="/assets/icons/line.svg" alt="" className="h-[16px] w-full object-fill" />

            <p className="m-0 text-[18px] leading-[1.75]">
              떠오른 생각이나 의문점, 추론, 계획 등을 기록해 보세요.
            </p>

            <img src="/assets/icons/line.svg" alt="" className="h-[16px] w-full object-fill" />

            <p className="m-0 text-[18px] leading-[1.75] text-game-ivory/75">
              여러분의 기록이 진실에 가까워질 단서를 남길 수도 있습니다.
            </p>
          </div>
        </div>

        {/*
          ★글자가 늘어나 보이던 까닭 (2026-08-30, 제보 — "자유메모 글씨가 뭔가 이상함,
            늘려놓은 느낌").

            이 상자에 scaleX(1.6) 이 걸려 있었다. 종이 그림만 늘리려던 것인데
            **안에 든 글자까지 1.6배로 늘어났다.** 앞서 글씨 크기를 손봐도
            이상해 보였던 것은 크기가 아니라 이 눌림/늘림 때문이다.

            늘리는 대신 상자를 실제 크기로 잡는다 (1035×1.6 = 1656 은 화면을
            넘으니, 눈에 보이던 자리 그대로 870 폭으로).
        */}
        <div
          className="absolute"
          style={{
            /* old_paper.svg 비율 900:830 ≈ 1.084 — 759 × 700 이면 꽉 찬다 */
            left: 490,
            top: 20,

            width: 759,
            height: 700,
          }}
        >
          {/* =====================================
              낡은 종이

              old_paper.svg 재사용
              오른쪽 영역에 맞게 비율만 변경
          ===================================== */}
          <img
            src="/assets/icons/old_paper.svg"
            alt=""
            className="
              absolute
              inset-0
              h-full
              w-full
              object-fill
            "
          />

      

          {/* =====================================
              실제 자유메모 입력창

              종이 대부분을 textarea로 사용
          ===================================== */}
          <textarea
            value={memo}
            onChange={(event) =>
              setMemo(event.target.value)
            }
            placeholder="자유롭게 메모를 작성해 보세요."
            className="
              absolute
              resize-none
              border-0
              bg-transparent
              outline-none
              font-game-korean
              tracking-[0.05em]
              text-[#211a13]
              placeholder:text-[#493b2d]/40
             
            "
            style={{
              /* 종이 안쪽 — 찢어진 가장자리를 밟지 않게 */
              left: 121,
              top: 140,

              width: 516,
              height: 480,

              fontSize: 20,
              lineHeight: 1.9,
            }}
          />
        </div>
      </section>
    </>
  )
}
