import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useGameStore } from '../store/gameStore'

/* =========================================
   엔딩

   ★결과는 두 갈래이고, **진상은 밝혀낸 사람만 본다** (2026-08-31, 팀 결정 — 가은).

     붙잡힌 밤   진상 다섯 박과 재연 여섯 컷을 다 본 뒤 여기로 온다.
     빠져나간 밤 지목이 빗나간 판. 진상도 재연도 열리지 않고 **곧장 여기로** 온다.
                 답을 공짜로 알려 주면 지목이 형식이 되기 때문이다. 대신 이
                 화면이 그 밤이 어떻게 끝났는지를 말하고, 비밀 성적표로
                 무엇을 놓쳤는지 짚어 준다.

     그래서 이 화면은 등급만 읊는 자리가 아니라, 그 밤이 어떻게 끝났는지를
     말하는 자리다. 갈래 글(branch.beats)을 여기서 읽는다.

   ★버튼도 고친다.
     「다시 조사하기」가 /main 으로 가고 있었다. 판은 이미 끝났고 예산도 0이라,
     돌아가 봐야 아무것도 못 한다. 다시 하려면 새 판을 열어야 한다.
========================================= */

export default function EndingPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const scenario = useGameStore((state) => state.scenario)
  const gameResult = useGameStore((state) => state.gameResult)
  const endingBranch = useGameStore((state) => state.endingBranch)
  const openedSecrets = useGameStore((state) => state.openedSecrets)
  const preview = location.pathname === '/ending-preview'
  const result = preview
    ? {
        score: 9,
        correct: true,
        grade: '명탐정',
        max: 10,
        verdict: 'ARREST' as const,
        verdictLine: '범인과 수법을 모두 밝혀냈다.',
        weaponCorrect: true,
        trueWeapon: null,
        secretsOpened: 4,
      }
    : gameResult

  /*
    ★점수가 아니라 **추리 성공/실패**로 가른다 (팀원 제보).
      범인과 흉기를 모두 맞혀야 ARREST. 이름만 맞히면 수법을 못 밝힌 것이라
      붙잡아 둘 수 없다 — FAIL 이다. 그래서 「맞혔는가」와 「성공했는가」가 다르다.
  */
  const verdict = result?.verdict ?? (result?.correct ? 'ARREST' : 'FAIL')
  const arrested = verdict === 'ARREST'

  /*
    ★발표용은 **판정을 내지 않는다** (2026-08-31, 제보 —
      "발표 배포용은 정답 제출하면 그냥 끝나게, 범인이 누군지 모르게").

      사람들 앞에서 한 판을 보여 주는 자리라, 그 자리에서 진상까지 흘러가면
      보고 있던 사람들은 이 사건을 다시 풀 수 없다. 맞았다고 알려 주는 것도
      안 된다 — 맞았다는 말이 곧 범인이 누구인지 알려 주는 말이다.

      그래서 이 화면은 「제출했다」까지만 말한다. 적중/빗나감 줄도, 등급도,
      점수도 띄우지 않는다. 남기는 것은 **제 손으로 연 비밀**뿐이다.
  */
  const submittedOnly = verdict === 'SUBMITTED'
  const verdictLine =
    result?.verdictLine ??
    (arrested
      ? '범인과 수법을 모두 밝혔다.'
      : result?.correct
        ? '이름은 맞았다. 그러나 수법을 짚지 못해 그를 붙잡아 둘 수 없었다.'
        : '이름을 잘못 짚었다. 진범은 그 밤을 빠져나갔다.')

  const correct = arrested
  const score = result?.score ?? 0
  const maxScore = result?.max ?? scenario?.scoring.max ?? 10
  const revealedSecrets = result?.secretsOpened ?? openedSecrets.length

  /* 판이 끝난 뒤에만 오는 성적표 — 못 연 비밀의 본문도 들어 있다 */
  const secretItems = result?.secretsRecord?.items ?? []

  /* 눌러서 펴 본 것 (이 화면에서만 기억한다) */
  const [peeked, setPeeked] = useState<string[]>([])

  /*
    등급 — 서버가 이미 골라서 준다. 없을 때만 점수로 되짚는다.
  */
  const gradeName =
    result?.grade ||
    [...(scenario?.ending.grades ?? [])]
      .sort((a, b) => b.min - a.min)
      .find((item) => score >= item.min)?.name ||
    ''

  const gradeText =
    [...(scenario?.ending.grades ?? [])]
      .sort((a, b) => b.min - a.min)
      .find((item) => score >= item.min)?.text ?? ''

  const beats = preview
    ? [
        '흩어져 있던 단서가 하나의 진실을 가리켰다.',
        '범인은 더 이상 자신의 범행을 부정하지 못했다.',
      ]
    : endingBranch?.beats ?? []
  const label = preview
    ? '붙잡힌 밤'
    : endingBranch?.label ?? (correct ? '붙잡힌 밤' : '빠져나간 밤')
  const resultLine = preview
    ? '긴 밤이 끝나고, 사건은 마침내 종결되었다.'
    : endingBranch?.result_line ?? ''

  const handleRetry = () => {
    /* 끝난 판으로는 돌아갈 수 없다 — 기록실에서 새로 연다 */
    navigate('/library')
  }

  const handleHome = () => {
    navigate('/')
  }

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-game-bg font-game-korean">
      <img
        src="/assets/icons/title-background.svg"
        alt=""
        className="absolute left-0 top-0 h-full w-full object-fill"
      />

      <div className="absolute left-[250px] top-[74px] flex h-[880px] w-[940px] flex-col">
        {/* 머리글 */}
        <div className="flex h-[64px] w-full shrink-0 items-center justify-center border-b border-[#806f50]/40">
          <p className="text-[25px] tracking-[0.15em] text-game-ivory">엔딩</p>
        </div>

        {/* =================================
            판정 — ARREST / FAIL

            크게 하나. 그 아래 한 줄로 사정을 말한다.
        ================================= */}
        <div
          className={`mt-[18px] flex w-full shrink-0 flex-col items-center justify-center border py-[18px] ${
            arrested || submittedOnly
              ? 'border-[#806f50]/60 bg-black/25'
              : 'border-game-red-light/45 bg-game-red/12'
          }`}
        >
          <p
            className={`font-serif text-[40px] tracking-[0.22em] ${
              arrested || submittedOnly
                ? 'text-game-parchment'
                : 'text-game-red-light'
            }`}
          >
            {submittedOnly ? '제출' : verdict}
          </p>

          <p className="mt-[6px] text-[20px] tracking-[0.1em] text-game-ivory/80">
            {label}
          </p>

          <p className="mt-[10px] px-[40px] text-center text-[16px] leading-[1.6] tracking-[0.03em] text-game-ivory/55">
            {verdictLine}
          </p>
        </div>

        {/* =================================
            그 밤이 어떻게 끝났는가

            갈래 글이 있으면 그것을, 없으면 등급 글을 읊는다.
        ================================= */}
        <div className="mt-[16px] w-full flex-1 overflow-y-auto border border-[#806f50]/35 px-[64px] py-[36px]">
          {beats.length > 0 ? (
            <div className="flex flex-col gap-[20px]">
              {beats.map((beat, index) => {
                const text = typeof beat === 'string' ? beat : beat.text
                const secretId =
                  typeof beat === 'string' ? null : beat.secret_id ?? null
                const secretWasOpened =
                  secretId === null || openedSecrets.includes(secretId)

                return (
                  <p
                    key={`${index}-${text.slice(0, 12)}`}
                    className={`text-[22px] leading-[1.85] tracking-[0.04em] ${
                      secretWasOpened
                        ? 'text-game-ivory/90'
                        : 'text-game-red-light'
                    }`}
                  >
                    {text}
                  </p>
                )
              })}

              {resultLine !== '' && (
                <p
                  className={`mt-[10px] text-[21px] tracking-[0.1em] ${
                    correct ? 'text-game-parchment' : 'text-game-red-light/85'
                  }`}
                >
                  {resultLine}
                </p>
              )}
            </div>
          ) : (
            <p className="whitespace-pre-line text-center text-[24px] leading-[2.1] tracking-[0.08em] text-game-ivory">
              {gradeText}
            </p>
          )}

        </div>

        {/* 짚은 것 · 밝혀낸 비밀 */}
        <div className="mt-[16px] flex w-full shrink-0 flex-col items-center justify-center gap-[6px] border border-[#806f50]/40 py-[13px]">
          {!submittedOnly && (
          <p className="text-[19px] tracking-[0.08em] text-game-ivory/85">
            범인 {result?.correct ? '적중' : '빗나감'}
            <span className="mx-[16px] opacity-40">·</span>
            수법 {result?.weaponCorrect ? '적중' : '빗나감'}
            <span className="mx-[16px] opacity-40">·</span>
            밝혀낸 비밀 {revealedSecrets}개
            {secretItems.length > 0 && (
              <span className="opacity-45"> / {secretItems.length}</span>
            )}
          </p>
          )}

          {/* 발표용 — 제 손으로 연 비밀만 세어 준다 */}
          {submittedOnly && (
            <p className="text-[19px] tracking-[0.08em] text-game-ivory/85">
              밝혀낸 비밀 {revealedSecrets}개
              {result?.secretsRecord?.total ? (
                <span className="opacity-45">
                  {' '}/ {result.secretsRecord.total}
                </span>
              ) : null}
            </p>
          )}

          {/* =================================
              비밀 성적표

              ★못 연 비밀도 **여기서는** 보여 준다 (2026-08-31, 제보 —
                "엔딩화면에 밝혀낸 비밀: 밝힌 비밀은 하얀 글씨로,
                 못 밝혀낸 건 누르면 알 수 있게").

                판은 이미 끝났으니 감출 이유가 없다. 다만 연 것과 못 연 것을
                한 색으로 두면 성적표가 아니게 된다 — 연 것은 흰 글씨로 그냥
                두고, 못 연 것은 가려 두었다가 누를 때만 편다. 무엇을 놓쳤는지
                **자기 손으로 열어 보는 것**이 이 화면의 마지막 일이다.
          ================================= */}
          {secretItems.length > 0 && (
            <ul className="mt-[10px] flex w-full list-none flex-col gap-[6px] px-[40px]">
              {secretItems.map((item, index) => {
                const key = `${item.castId}-${index}`
                const shown = item.opened || peeked.includes(key)

                return (
                  <li key={key} className="flex items-baseline gap-[12px]">
                    <span className="w-[86px] shrink-0 text-right text-[15px] tracking-[0.06em] text-game-ivory/45">
                      {item.castName}
                    </span>

                    {shown ? (
                      <span
                        className={`text-[16px] leading-[1.6] tracking-[0.02em] ${
                          item.opened
                            ? 'text-game-ivory'
                            : 'italic text-game-ivory/55'
                        }`}
                      >
                        {item.text}
                        {!item.opened && (
                          <span className="ml-[10px] text-[13px] not-italic text-game-red-light/70">
                            못 밝힌 것
                          </span>
                        )}
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setPeeked((prev) => [...prev, key])}
                        className="cursor-pointer border-0 bg-transparent p-0 text-left text-[16px] leading-[1.6] tracking-[0.02em] text-game-ivory/30 underline decoration-dotted underline-offset-4 transition-colors hover:text-game-ivory/60"
                      >
                        밝히지 못한 비밀 — 눌러서 본다
                      </button>
                    )}
                  </li>
                )
              })}
            </ul>
          )}

          {/* 흉기는 지목 뒤에 공개된다 — 틀렸다면 무엇이었는지 알려 준다 */}
          {!submittedOnly && result?.trueWeapon && !result.weaponCorrect && (
            <p className="text-[16px] tracking-[0.04em] text-game-ivory/45">
              수법은 「{result.trueWeapon}」였다.
            </p>
          )}

          {!submittedOnly && gradeName !== '' && (
            <p className="text-[15px] tracking-[0.1em] text-game-ivory/35">
              {gradeName} · {score} / {maxScore}
            </p>
          )}
        </div>

        {/* 버튼 */}
        {/*
          액자 버튼(button.svg)은 제 비율(350:186)을 지켜서, 납작한 상자에
          넣으면 테두리가 글자보다 작게 그려진다. 긴 글은 그냥 테두리 상자로 둔다 —
          용의자 화면의 「지도에서 조사를 시작한다」와 같은 모양이다.
        */}
        <div className="mt-[22px] flex w-full shrink-0 items-center justify-center gap-[22px]">
          <button
            type="button"
            onClick={handleRetry}
            className="h-[72px] w-[320px] cursor-pointer border border-[#8c1f1f] bg-[#161009] text-[22px] tracking-[0.08em] text-game-ivory outline outline-1 outline-offset-4 outline-[#5d1616] transition-colors hover:bg-[#241609]"
          >
            이 사건을 다시 조사한다
          </button>

          <button
            type="button"
            onClick={handleHome}
            className="h-[72px] w-[240px] cursor-pointer border border-white/20 bg-black/45 text-[22px] tracking-[0.08em] text-game-ivory/75 transition-colors hover:border-game-parchment hover:text-game-ivory"
          >
            첫 화면으로
          </button>
        </div>
      </div>
    </main>
  )
}
