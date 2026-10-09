export type VictimData = {
  name: string
  role: string
  bio: string
  status: string
  discoveredPlace: string
  discoveredTime: string
  discoverer: string
  causeOfDeath: string
  image: string
}

/*
  ★칸이 통째로 비어 있던 것을 고친다 (2026-08-29, 시연 제보).
    제보: "피해자 사진이 안 나온다 · 피해자 프로필에 내용이 없다."

    이 카드는 **사인 한 줄만** 그리고 있었다. 사진 자리도 없었다.
    서버가 보내 주는 이름·신분·발견 장소·발견 시각은 받아 놓고 버린 셈이다.
    사인은 지목 전까지 「???」로 둔다 — 흉기와 수법이 곧 정답이다.
*/
export default function VictimCard({
  victim,
}: {
  victim: VictimData
}) {
  const rows: Array<[string, string, boolean]> = [
    ['이름', victim.name, false],
    ['신분', victim.status || victim.role, false],
    ['발견 장소', victim.discoveredPlace, false],
    ['발견 시각', victim.discoveredTime, false],
    ['발견자', victim.discoverer, false],
    ['사인', victim.causeOfDeath, true],
  ]

  return (
    <>
      {/* 큰 낡은 종이 */}
      <img
        src="/assets/icons/old_paper.svg"
        alt=""
        className="absolute left-[270px] top-[-15px] h-[990px] w-[900px]"
      />

      {/*
        ★카드 그림은 **현장**이다 (팀원 제보 —
          "Victim page 사진 규격 안 맞음. 원래 엎드려 죽은 사진이 들어가야 함").

          세로 초상(512×768)을 가로 액자에 넣고 있었으니 규격이 맞을 리가 없다.
          시나리오는 처음부터 카드 그림을 **가로 1045×600 현장**으로 적어 두었다.
          현장 그림이 아직 없으면 초상으로 물러선다 — 빈 액자는 고장처럼 보인다.

          액자 안쪽 자리는 비율로 잡는다(536×300 시절의 142/16/252/268).
      */}
      <div className="absolute left-[437px] top-[155px] z-10 h-[319px] w-[570px]">
        <img
          src="/assets/icons/victim_paper.svg"
          alt=""
          className="absolute inset-0 h-full w-full"
        />

        {/*
          ★피해자 카드에는 **피해자 얼굴**이 온다 (2026-08-30, 제보 —
            "Victim 에서 피해자가 아니라 피해장면이 나온다").

            앞선 제보("사진 규격이 안 맞는다")를 현장 그림으로 읽고 바꿨는데,
            그러니 이번엔 사람이 사라졌다. 이 카드는 **누가 죽었는가**를 보는
            자리다. 현장은 /crime-scene 이 이미 크게 보여 준다.
        */}
        {victim.image !== '' ? (
          <img
            src={victim.image}
            alt={victim.name}
            className="absolute left-[26.5%] top-[5.3%] h-[89.3%] w-[47%] object-cover object-top"
            style={{ filter: 'sepia(0.32) contrast(1.05) brightness(0.94)' }}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center font-game-korean text-[20px] text-[#5e4830]/50">
            사진 없음
          </div>
        )}
      </div>

      {/* =====================================
          피해자 정보

          ★소개글이 종이 밖으로 흘러 나가던 것을 고친다 (2026-08-29, 3차 제보).
            한도윤 소개는 462자다. 그런데 칸은 세 줄(82px)짜리였고, 그 칸이
            종이 아래끝(y=920)에 걸쳐 있어서 글이 종이 밖에서 반쯤 잘렸다.

            줄여서 감출 수는 없다 — 이 글 안에 **총회 안건(계정 이관)** 이
            들어 있고, 그게 동기로 가는 실마리다. 잘라 내면 실마리가 사라진다.
            그래서 종이 안에 자리를 확실히 잡고, 넘치는 만큼은 굴려 읽게 둔다.

            old_paper.svg 는 제 비율(900:830)을 지켜서 800×800 상자 안에서
            800×738 로 그려진다 — 실제로 글을 얹을 수 있는 자리는
            x 486~964 · y 452~814 다. 찢어진 가장자리를 밟지 않게 그 안에 둔다.

          ★소개글이 안 읽히던 것을 고친다 (2026-08-31, 제보 —
            "피해자 상세 설명 하단 텍스트 색 좀 더 잘 보이게").

            색만의 문제가 아니라 **자리도 같이** 문제였다. 종이는 아래로 갈수록
            어두워진다 — 글이 놓이는 자리의 바탕색을 재 보면 y=700 에서 (155,130,93)
            인데 y=840 에서는 (140,107,67) 까지 내려간다. 그런데 상자 바닥이 y=858
            이라, 마지막 두어 줄이 가장 어두운 가장자리 위에 얹혀 있었다.
            #3b2e1e 를 90% 로 깐 글자는 그 자리에서 대비가 2.5:1 밖에 안 됐다.

            그래서 둘을 같이 고친다 —
              · 글자를 검정으로 진하게, 불투명하게, 15px → 16px
                (서현도 같은 제보를 text-black 으로 고쳤다 — 그쪽이 더 진해 그걸 쓴다)
              · 상자 높이 430 → 400 (글 끝이 y≈801 안쪽으로 들어온다)
            이러면 문단 어디에서나 4.5:1 위로 올라온다. 넘치는 만큼은 여전히
            굴려 읽는다 — 총회 안건 대목은 한 글자도 잘리지 않는다.
      ===================================== */}
      <div className="absolute left-[442px] top-[428px] z-20 flex h-[400px] w-[568px] flex-col overflow-hidden p-[0.7cm] font-game-korean text-[18px] tracking-[0.04em] text-[#211810]">
        {rows
          .filter(([, value]) => Boolean(value))
          .map(([label, value, accent]) => (
            <div
              key={label}
              className="flex shrink-0 items-center border-b border-[#5e4830]/25 py-[5px]"
            >
              <span className="w-[110px] shrink-0 font-semibold" style={{ color: '#43341f' }}>
                {label}
              </span>
              <span
                className="flex-1 leading-[1.4]"
                style={accent ? { color: '#7c221d' } : undefined}
              >
                {value}
              </span>
            </div>
          ))}

        {victim.bio !== '' && (
          <p className="victim-bio mt-[12px] min-h-0 flex-1 overflow-y-auto break-keep pr-[12px] text-[16px] leading-[1.7] text-black">
            {victim.bio}
          </p>
        )}
      </div>
    </>
  )
}
