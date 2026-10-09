import {
  useEffect,
  useRef,
  useState,
} from 'react'
import type { FormEvent } from 'react'
import {
  Navigate,
  useNavigate,
} from 'react-router-dom'

import GameHeader2 from '../components/common/GameHeader2'
import { getSuspects } from '../data/scenarioAdapter'
import { useGameStore } from '../store/gameStore'
import { useUiStore } from '../store/uiStore'

type ConfrontationBeat = {
  name: string
  /* narration — 판정자의 말. 두 사람 어느 쪽도 아니다 */
  speaker: 'left' | 'right' | 'narration'
  line: string | null
}

export default function ConfrontationPage() {
  const navigate = useNavigate()
  const openSettings = useUiStore((state) => state.openSettings)
  const pair = useGameStore((state) => state.confrontationPair)
  const scenario = useGameStore((state) => state.scenario)
  const confront = useGameStore((state) => state.confront)
  const suspects = getSuspects(scenario)
  const leftSuspect = suspects.find(
    (suspect) => suspect.id === pair?.[0],
  )
  const rightSuspect = suspects.find(
    (suspect) => suspect.id === pair?.[1],
  )
  const confrontationLog = useGameStore(
    (state) => state.confrontationLog,
  )
  const confrontationUsed = useGameStore(
    (state) => state.confrontationUsed,
  )
  const roundOver = useGameStore((state) => state.roundOver)
  const setConfrontationLog = useGameStore(
    (state) => state.setConfrontationLog,
  )
  const showToast = useUiStore((state) => state.showToast)
  const savedQuestion =
    confrontationLog.find((message) => message.side === 'user')
      ?.text ?? ''
  const savedBeatCount = confrontationLog.filter(
    (message) => message.side !== 'user',
  ).length
  const [question, setQuestion] = useState('')
  const [submittedQuestion, setSubmittedQuestion] =
    useState(savedQuestion)
  const [beatIndex, setBeatIndex] = useState(savedBeatCount - 1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [activeBeats, setActiveBeats] = useState<ConfrontationBeat[]>(
    [],
  )
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isPlaying) {
      return
    }

    if (beatIndex >= activeBeats.length - 1) {
      const finishTimer = window.setTimeout(() => {
        setIsPlaying(false)
      }, 1300)

      return () => window.clearTimeout(finishTimer)
    }

    const beatTimer = window.setTimeout(() => {
      const nextIndex = beatIndex + 1
      const beat = activeBeats[nextIndex]
      const speakerName =
        beat.speaker === 'narration'
          ? ''
          : beat.speaker === 'left'
            ? leftSuspect?.listName ?? ''
            : rightSuspect?.listName ?? ''

      setConfrontationLog([
        ...useGameStore.getState().confrontationLog,
        {
          name: speakerName,
          text: beat.line ?? '',
          side: beat.speaker,
          beat: beat.name,
        },
      ])
      setBeatIndex(nextIndex)
    }, beatIndex < 0 ? 250 : 1300)

    return () => window.clearTimeout(beatTimer)
  }, [
    beatIndex,
    isPlaying,
    activeBeats,
    leftSuspect?.listName,
    rightSuspect?.listName,
    setConfrontationLog,
  ])

  useEffect(() => {
    const log = logRef.current

    if (log) {
      log.scrollTo({
        top: log.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [beatIndex, submittedQuestion])

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault()

    const trimmedQuestion = question.trim()

    /* 같은 이유로 여기도 처음부터 막혀 있었다 (위 hasFinished 주석 참고) */
    if (
      trimmedQuestion === '' ||
      isPlaying ||
      (activeBeats.length > 0 && beatIndex === activeBeats.length - 1)
    ) {
      return
    }

    if (pair === null) return

    let beats: ConfrontationBeat[]

    try {
      const response = await confront(
        pair[0],
        pair[1],
        trimmedQuestion,
      )

      /*
        ★두 사람이 한 사람으로 뭉쳐 보이던 것을 고친다 (2026-08-30, 제보 —
          "대질할 때 대화가 다 같은 인물로 나온다").

          서버는 말한 사람을 **두 가지로** 알려 준다 —
            who     "A" / "B"   (맞세운 두 자리)
            cast_id "C5" / "C1" (인물 id)
          그런데 화면은 그 값을 pair[0]("C5")이나 response.a("차연우")와 견주고
          있었다. "A" 는 둘 중 어느 것과도 같지 않으니 **모든 줄이 오른쪽으로**
          떨어졌다. 그래서 한 사람이 혼잣말하는 것처럼 보였다.

          id 로 먼저 맞추고, 없으면 A/B 자리로 맞춘다. 이름으로도 한 번 더 본다.
      */
      const beatSide = (
        castId?: string | null,
        who?: string | null,
        name?: string | null,
      ): 'left' | 'right' => {
        if (castId === pair[0]) return 'left'
        if (castId === pair[1]) return 'right'

        const slot = (who ?? '').trim().toUpperCase()
        if (slot === 'A') return 'left'
        if (slot === 'B') return 'right'

        if (name && name === response.a) return 'left'
        if (name && name === response.b) return 'right'

        return 'right'
      }

      /*
        여는 말은 사람 대사가 아니라 **판정자의 나레이션**일 때가 있다
        (문자열 하나로 온다). 그때는 가운데 한 줄로 둔다.
      */
      const opening = response.opening as
        | string
        | { speaker?: string; cast_id?: string; who?: string; name?: string; line?: string }
        | null

      const openingLine =
        typeof opening === 'string' ? opening : opening?.line ?? ''

      beats = [
        ...(openingLine
          ? [{
              name: '여는 말',
              speaker:
                typeof opening === 'string'
                  ? ('narration' as const)
                  : beatSide(opening?.cast_id, opening?.who ?? opening?.speaker, opening?.name),
              line: openingLine,
            }]
          : []),
        ...(response.exchange ?? [])
          .filter((beat) => Boolean(beat.line ?? beat.text))
          .map((beat, index) => ({
            name: beat.beat || `${index + 1}`,
            speaker: beatSide(
              beat.cast_id,
              beat.who ?? beat.speaker,
              beat.name,
            ),
            line: beat.line ?? beat.text ?? '',
          })),
      ]
    } catch (error) {
      showToast(
        error instanceof Error
          ? error.message
          : '요청에 실패했습니다.',
      )
      return
    }

    if (beats.length === 0) {
      showToast('두 사람 사이에서 나온 말이 없습니다.')
      return
    }

    setActiveBeats(beats)
    setSubmittedQuestion(trimmedQuestion)
    setConfrontationLog([
      {
        name: '나',
        text: trimmedQuestion,
        side: 'user',
      },
    ])
    setBeatIndex(-1)
    setIsPlaying(true)
  }

  const currentBeat =
    activeBeats[beatIndex] ?? null
  /*
    ★아무것도 안 했는데 「대질 완료」로 잠겨 있던 것을 고친다
      (2026-08-29, 시연 제보).

      제보 둘이 같은 자리에서 났다 —
        "대질 페이지에 들어가면 「말이 어긋납니다…」가 처음부터 떠 있다"
        "질문을 쓰고 보낼 버튼이 없다"

      beatIndex 는 -1 로 시작하고 activeBeats 는 빈 배열이라
      `beatIndex === activeBeats.length - 1` 이 **처음부터 참**이었다.
      그래서 결과 문구가 뜨고, 전송 버튼은 hasFinished 로 잠겼다.
      오간 말이 실제로 있을 때만 끝난 것으로 본다.
  */
  const hasFinished =
    confrontationUsed &&
    !isPlaying &&
    confrontationLog.length > 0

  if (pair === null) {
    return <Navigate to="/main" replace />
  }

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-black font-game-korean text-game-ivory">
      <img
        src="/assets/icons/title-background.svg"
        alt=""
        className="absolute inset-0 h-full w-full object-fill opacity-70"
      />

      <GameHeader2
        leftText="< 돌아가기"
        title="대질"
        rightText="설정"
        onLeftClick={() => navigate(roundOver ? '/round-end' : '/main')}
        onRightClick={openSettings}
      />

      <section
        className={`absolute left-[55px] top-[125px] h-[520px] w-[470px] overflow-hidden border bg-black/55 transition-all duration-500 ${
          currentBeat?.speaker === 'left'
            ? 'border-game-parchment shadow-[0_0_32px_rgba(210,197,170,0.2)]'
            : 'border-white/15 opacity-55'
        }`}
      >
        {leftSuspect?.image ? (
          <img
            src={leftSuspect.image}
            alt={leftSuspect.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-[38px] tracking-[0.12em] text-white/45">
            {leftSuspect?.listName ?? ''}
          </div>
        )}
      </section>

      <section
        className={`absolute left-[915px] top-[125px] h-[520px] w-[470px] overflow-hidden border bg-black/55 transition-all duration-500 ${
          currentBeat?.speaker === 'right'
            ? 'border-game-parchment shadow-[0_0_32px_rgba(210,197,170,0.2)]'
            : 'border-white/15 opacity-55'
        }`}
      >
        {rightSuspect?.image ? (
          <img
            src={rightSuspect.image}
            alt={rightSuspect.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-[38px] tracking-[0.12em] text-white/45">
            {rightSuspect?.listName ?? ''}
          </div>
        )}
      </section>

      <div className="absolute left-[545px] top-[125px] h-[520px] w-[350px] border border-white/10 bg-black/55">
        <div className="flex h-[62px] items-center justify-center border-b border-white/10 text-[19px] tracking-[0.16em] text-game-parchment">
          {currentBeat
            ? `${beatIndex + 1} / ${activeBeats.length} · ${currentBeat.name}`
            : '대질 기록'}
        </div>

        <div
          ref={logRef}
          className="h-[457px] overflow-y-auto px-[24px] py-[22px] text-left"
        >
          {submittedQuestion === '' ? (
            <p className="mt-[135px] text-center text-[21px] leading-[1.7] text-white/40">
              두 사람에게 묻고 싶은 것을 적어<br />맞대 놓으세요.
            </p>
          ) : (
            <>
              {confrontationLog.map((message, index) => (
                <ChatLogMessage
                  key={`${message.side}-${message.beat ?? 'question'}-${index}`}
                  {...message}
                />
              ))}
            </>
          )}
        </div>
      </div>

      <div className="absolute left-[55px] top-[665px] flex h-[92px] w-[640px] items-center border border-white/15 bg-black/55 px-[30px] text-[22px] leading-[1.5]">
        <span className="mr-[18px] text-game-parchment">
          {`{A}`}
        </span>
        {leftSuspect?.alibi ?? ''}
      </div>

      <div className="absolute left-[745px] top-[665px] flex h-[92px] w-[640px] items-center border border-white/15 bg-black/55 px-[30px] text-[22px] leading-[1.5]">
        <span className="mr-[18px] text-game-parchment">
          {`{B}`}
        </span>
        {rightSuspect?.alibi ?? ''}
      </div>

      <form
        onSubmit={handleSubmit}
        className="absolute left-[55px] top-[785px] flex h-[120px] w-[1330px] items-stretch"
      >
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          disabled={confrontationUsed || isPlaying}
          placeholder={
            confrontationUsed
              ? '이미 완료한 대질입니다.'
              : '무엇을 묻겠습니까?'
          }
          className="min-w-0 flex-1 border border-white/20 bg-black/55 px-[35px] text-[26px] tracking-[0.06em] text-game-ivory outline-none placeholder:text-white/35 focus:border-game-parchment"
        />
        <button
          type="submit"
          disabled={
            confrontationUsed ||
            question.trim() === '' ||
            isPlaying ||
            hasFinished
          }
          className="ml-[18px] w-[300px] cursor-pointer border border-game-parchment/50 bg-[#171512] text-[27px] tracking-[0.12em] text-game-ivory disabled:cursor-default disabled:opacity-35"
        >
          {isPlaying
            ? '대질 중…'
            : hasFinished
              ? '대질 완료'
              : '맞대 놓는다'}
        </button>
      </form>

      {hasFinished && (
        <div className="absolute left-[360px] top-[920px] flex h-[70px] w-[720px] items-center justify-center border-l-[3px] border-game-red-light bg-game-red/25 text-[24px] tracking-[0.08em]">
          말이 어긋납니다 · 드러난 것이 기록되었습니다.
        </div>
      )}
    </main>
  )
}

function ChatLogMessage({
  name,
  text,
  side,
  beat,
}: {
  name: string
  text: string
  side: 'user' | 'left' | 'right' | 'narration'
  beat?: string
}) {
  return (
    <div className={`mb-[24px] ${
      side === 'narration'
        ? 'text-center'
        : side === 'right'
          ? 'text-right'
          : 'text-left'
    }`}>
      <div className="mb-[8px] text-[18px] text-game-parchment">
        {name}
        {beat && (
          <span className="ml-[8px] text-[14px] text-white/35">
            {beat}
          </span>
        )}
      </div>
      <div className={`inline-block max-w-full border px-[14px] py-[11px] text-[17px] leading-[1.65] ${
        side === 'narration'
          ? 'border-transparent bg-transparent text-white/40 italic'
          : side === 'user'
            ? 'border-white/15 bg-white/5 text-white/65'
            : side === 'left'
            ? 'border-game-parchment/25 bg-game-gold/15'
            : 'border-game-red-light/30 bg-game-red/15'
      }`}>
        {text}
      </div>
    </div>
  )
}
