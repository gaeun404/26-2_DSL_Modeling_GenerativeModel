import { useGameStore } from '../../store/gameStore'

function findFieldValue(
  fields: {
    label: string
    value: string
  }[],
  labels: string[],
) {
  const field = fields.find(
    (item) =>
      labels.includes(item.label),
  )

  if (field === undefined) {
    return ''
  }

  return field.value
}

export default function CaseSummary() {
  const scenario = useGameStore(
    (state) => state.scenario,
  )

  const caseSummary = useGameStore(
    (state) => state.caseSummary,
  )

  /*
    사건 정보는 프론트에서 작성하지 않는다.

    scenario가 존재하면
    victim_card.fields에서 값을 찾는다.

    현재 백엔드 스키마가 label/value 구조이므로
    label을 기준으로 화면에 필요한 값을 가져온다.
  */
  const victimFields =
    scenario !== null
      ? scenario.ui.victim_card.fields
      : []

  const victim =
    findFieldValue(
      victimFields,
      [
        '피해자',
        '이름',
        '성명',
      ],
    )

  const place =
    findFieldValue(
      victimFields,
      [
        '발견장소',
        '발견 장소',
        '장소',
      ],
    )

  const discoveredTime =
    findFieldValue(
      victimFields,
      [
        '발견시각',
        '발견 시각',
        '시각',
      ],
    )

  const discoverer =
    findFieldValue(
      victimFields,
      [
        '발견자',
      ],
    )

  /*
    로그라인:

    현재 store에 저장되어 있는
    caseSummary를 사용한다.

    프론트에서 임의의 사건 설명을
    fallback으로 작성하지 않는다.
  */
  const logline = caseSummary

  return (
    <div
      className="absolute"
      style={{
        left: 40,
        top: 150,

        width: 600,
        height: 541,

        transform: 'scale(1.2)',
      }}
    >
      {/* 낡은 종이 */}
      <img
        src="/assets/icons/old_paper.svg"
        alt=""
        className="absolute inset-0 h-full w-full object-fill"
      />

      {/* 사건 개요 */}
      <div
        className="absolute font-game-korean text-[#211A13]"
        style={{
          left: 130,
          top: 100,

          width: 340,

          fontSize: 20,
          lineHeight: 1.7,
          letterSpacing: '0.1em',
        }}
      >
        {/* 로그라인 */}
        {logline !== '' && (
          <div
            style={{
              marginBottom: 28,
            }}
          >
            {logline}
          </div>
        )}

        {/* 피해자 */}
        {victim !== '' && (
          <div>
            피해자 · {victim}
          </div>
        )}

        {/* 장소 */}
        {place !== '' && (
          <div>
            장소 · {place}
          </div>
        )}

        {/* 발견시각 */}
        {discoveredTime !== '' && (
          <div>
            발견시각 · {discoveredTime}
          </div>
        )}

        {/* 발견자 */}
        {discoverer !== '' && (
          <div>
            발견자 · {discoverer}
          </div>
        )}
      </div>
    </div>
  )
}