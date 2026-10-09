import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import {
  useGameStore,
  type ChatMessage,
} from '../../store/gameStore'
import { getNotebookClues } from '../../data/scenarioAdapter'
import { useUiStore } from '../../store/uiStore'
import type { Stance } from '../../api/scenarioApi'

type InterrogateChatProps = {
  castId: string
  characterName: string
  faces: {
    calm: string
    shaken: string
    broken: string
  }
  fallbackImage: string
  initialAlibi: string
}

/*
  판정 → 얼굴.

  ANSWER·DEFLECT는 평정, FLINCH는 흔들림,
  ADMIT·BREAK는 무너짐.
  서버도 같은 셈으로 얼굴 주소를 함께 보내 준다.
*/
const faceFor = (
  stance: Stance | undefined,
  faces: InterrogateChatProps['faces'],
) => {
  if (stance === 'ADMIT' || stance === 'BREAK') return faces.broken
  if (stance === 'FLINCH') return faces.shaken
  return faces.calm
}

/*
  셀렉터가 매번 새 배열을 만들면 zustand 는 상태가 바뀐 줄 알고
  다시 그린다 — 그러면 또 새 배열이 나오고, 끝이 없다.
  빈 배열은 하나를 만들어 돌려쓴다.
*/
const NO_MESSAGES: ChatMessage[] = []

const subjectParticle = (name: string) => {
  const lastCode = name.trim().charCodeAt(name.trim().length - 1)
  const hasFinalConsonant =
    lastCode >= 0xac00 &&
    lastCode <= 0xd7a3 &&
    (lastCode - 0xac00) % 28 !== 0

  return hasFinalConsonant ? '이' : '가'
}

export default function InterrogateChat({
  castId,
  characterName,
  faces,
  fallbackImage,
  initialAlibi,
}: InterrogateChatProps) {
  const remainingTurns = useGameStore(
    (state) => state.remainingTurns,
  )

  const scenario = useGameStore((state) => state.scenario)

  const serverFace = useGameStore(
    (state) => state.suspectFaces[castId],
  )

  const discoveredClueIds = useGameStore(
    (state) => state.discoveredClueIds,
  )

  const interrogate = useGameStore(
    (state) => state.interrogate,
  )

  const showToast = useUiStore((state) => state.showToast)

  const messages = useGameStore(
    (state) => state.interrogationLogs[castId] ?? NO_MESSAGES,
  )

  const setInterrogationLog = useGameStore(
    (state) => state.setInterrogationLog,
  )

  useEffect(() => {
    if (messages.length > 0 || initialAlibi.trim() === '') {
      return
    }

    setInterrogationLog(castId, [
      {
        id: Date.now(),
        sender: 'suspect',
        text: initialAlibi,
      },
    ])
  }, [castId, initialAlibi, messages.length, setInterrogationLog])

  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)

  /* 함께 들이밀 단서 */
  const [clueId, setClueId] = useState('')
  const [cluePickerOpen, setCluePickerOpen] = useState(false)

  const clues = getNotebookClues(scenario, discoveredClueIds)
  const selectedClue = clues.find((clue) => clue.id === clueId)

  const lastStance = [...messages]
    .reverse()
    .find((message) => message.stance)?.stance

  const faceImage =
    serverFace || faceFor(lastStance, faces) || fallbackImage

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault()

    const trimmed = input.trim()

    if (!trimmed || pending) {
      return
    }

    /*
      ★행동이 0이어도 **여기서 라운드를 넘기지 않는다** (2026-08-31, 제보 —
        "남은 행동이 0이 되면 바로 다음 라운드로 전환되는 오류가 남아 있음").

        더 물을 수 없다는 것만 알려 주고 화면은 그대로 둔다. 방금 받은 답을
        끝까지 읽을 수 있어야 한다. 밤을 마치는 것은 라운드 화면(/main)에서
        플레이어가 누를 때다 — 대질로 마지막 행동을 썼을 때도 마찬가지다.
    */
    if (remainingTurns <= 0) {
      showToast('이번 밤의 행동을 다 썼습니다 — 라운드 화면에서 밤을 마칩니다.')
      return
    }

    const userMessage: ChatMessage = {
      id: Date.now(),
      sender: 'user',
      text: selectedClue
        ? `「${selectedClue.title}」 — ${trimmed}`
        : trimmed,
    }

    setInput('')
    setPending(true)

    try {
      /*
        서버가 판정하고, 서버가 대사를 만든다.
        키가 없으면 line 이 null 로 온다 —
        그때는 판정만 보여 준다.
      */
      const answer = await interrogate(
        castId,
        trimmed,
        clueId || null,
      )

      const reply: ChatMessage = {
        id: Date.now() + 1,
        sender: 'suspect',
        /*
          키가 없어 대사를 못 만들 때만 자리를 채운다.
          이때도 판정을 글자로 알려 주지 않는다 — 표정이 말한다.
        */
        text: answer.line ?? `(${characterName}은(는) 입을 열었다.)`,
        stance: answer.stance,
        face: answer.face ?? undefined,
        /* 이 대답에서 비밀이 열렸다 — 말풍선이 붉게 물든다 */
        secretOpened: answer.openedSecrets.length > 0,
      }

      setInterrogationLog(castId, [
        ...messages,
        userMessage,
        reply,
      ])

      setClueId('')

    } catch (error) {
      showToast(
        error instanceof Error
          ? error.message
          : '요청에 실패했습니다.',
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <>
      {/* =========================================
          왼쪽 인물 — 판정에 따라 얼굴이 바뀐다
      ========================================= */}

      <div
        className="absolute overflow-hidden"
        style={{
          left: 70,
          top: 189,

          width: 573,
          height: 668,

          border: '1px solid rgba(225,216,199,0.35)',
        }}
      >
        {faceImage ? (
          <img
            key={faceImage}
            src={faceImage}
            alt={characterName}
            className="absolute inset-0 h-full w-full object-cover transition-opacity duration-500"
          />
        ) : (
          <div
            className="
              flex
              h-full
              w-full
              items-center
              justify-center
              font-game-korean
              text-white/25
            "
            style={{ fontSize: 25 }}
          >
            인물 사진 영역
          </div>
        )}

        {/*
          ★압박 게이지와 태도 라벨을 뺀다 (가은의 판단, F-7).

            판정을 글자로 알려 주면 플레이어가 **사람을 읽지 않고 라벨을 읽는다.**
            「말을 돌린다」가 떠 있으면 말투를 살필 까닭이 없어진다.
            남기는 것은 초상 표정 세 벌뿐 — stance 는 얼굴을 고르는 데만 쓴다.
            pressure 값도 그리지 않는다(내부 판정용).
        */}
      </div>

      {/* =========================================
          오른쪽 채팅 로그
      ========================================= */}

      <div
        className="absolute overflow-y-auto"
        style={{
          left: 758,
          top: 189,

          width: 668,
          height: 640,

          paddingLeft: 35,
          paddingRight: 35,
          paddingTop: 15,
        }}
      >
        {messages.length === 0 && (
          <div
            className="font-game-korean text-game-ivory/40"
            style={{ fontSize: 19, lineHeight: 1.8 }}
          >
            무엇이든 물어보세요.
            <br />
            단서를 함께 내밀면 다른 말이 나옵니다.
          </div>
        )}

        {messages.map((message, index) => {
          const senderName =
            message.sender === 'user' ? '나' : characterName
          const hitTheMark =
            message.sender === 'suspect' &&
            (message.stance === 'FLINCH' ||
              message.stance === 'ADMIT' ||
              message.stance === 'BREAK')

          /*
            ★비밀이 **열렸을 때만** 붉게 물들인다 (2026-08-31, 제보 —
              "비밀 정곡 찔리면 채팅 붉은색 효과").

              흔들렸다(FLINCH)와 비밀이 열렸다는 다르다. 흔들리기만 한
              대답까지 붉게 하면 색이 흔해져서, 정작 열린 순간이 묻힌다.
              그래서 신호는 서버가 준 secrets_opened 다 — 그 대답에서
              실제로 열린 비밀이 있을 때만.
          */
          const struck =
            message.sender === 'suspect' && message.secretOpened === true

          return (
            <div key={message.id} style={{ marginBottom: 28 }}>
              {/* 이름 */}
              <div
                className="font-game-korean text-game-ivory"
                style={{ fontSize: 23, marginBottom: 12 }}
              >
                {senderName}
              </div>

              {hitTheMark && (
                <div
                  className="font-game-korean text-game-red-light"
                  style={{ fontSize: 18, lineHeight: 1.7, marginBottom: 8 }}
                >
                  [{characterName}{subjectParticle(characterName)} 정곡에 찔렸습니다]
                </div>
              )}

              {/* 채팅 */}
              <div
                className={`font-game-korean ${
                  struck ? 'secret-struck text-game-ivory' : 'text-game-ivory'
                }`}
                style={{ fontSize: 20, lineHeight: 1.7 }}
              >
                {message.text}
              </div>

              {struck && (
                <div
                  className="font-game-korean text-game-red-light"
                  style={{ fontSize: 17, lineHeight: 1.7, marginTop: 8 }}
                >
                  숨기던 것이 하나 열렸습니다. 사건수첩에 적어 두었습니다.
                </div>
              )}

              {/* 구분선 */}
              {index < messages.length - 1 && (
                <img
                  src="/assets/icons/line.svg"
                  alt=""
                  style={{
                    width: '100%',
                    height: 45,
                    marginTop: 10,
                    objectFit: 'fill',
                  }}
                />
              )}
            </div>
          )
        })}

        {pending && (
          <div
            className="font-game-korean text-game-ivory/45"
            style={{ fontSize: 19 }}
          >
            {characterName}이(가) 생각하고 있습니다…
          </div>
        )}
      </div>

      {/* =========================================
          내밀 단서 · 남은 행동
      ========================================= */}

      <div
        className="absolute flex items-center justify-between"
        style={{
          left: 758,
          top: 845,
          width: 668,
        }}
      >
        <button
          type="button"
          onClick={() => setCluePickerOpen((open) => !open)}
          disabled={clues.length === 0}
          className="
            cursor-pointer
            border
            border-game-parchment/40
            bg-black/45
            px-[18px]
            py-[8px]
            font-game-korean
            text-[16px]
            tracking-[0.06em]
            text-game-ivory
            disabled:cursor-default
            disabled:opacity-35
          "
        >
          {selectedClue
            ? `단서: ${selectedClue.title}`
            : `단서 내밀기 (${clues.length})`}
        </button>

        <div
          className="font-game-korean text-game-ivory"
          style={{
            fontSize: 17,
            letterSpacing: '0.08em',
            opacity: 0.55,
          }}
        >
          남은 행동 {remainingTurns}
        </div>
      </div>

      {/* 단서 고르기 */}
      {cluePickerOpen && (
        <div
          className="absolute z-30 overflow-y-auto border border-game-parchment/35 bg-[#11100e]/97"
          style={{
            left: 758,
            top: 470,
            width: 400,
            maxHeight: 360,
          }}
        >
          <button
            type="button"
            onClick={() => {
              setClueId('')
              setCluePickerOpen(false)
            }}
            className="block w-full cursor-pointer border-0 border-b border-white/10 bg-transparent px-[18px] py-[13px] text-left font-game-korean text-[16px] text-game-ivory/55"
          >
            내밀지 않는다
          </button>

          {clues.map((clue) => (
            <button
              key={clue.id}
              type="button"
              onClick={() => {
                setClueId(clue.id)
                setCluePickerOpen(false)
              }}
              className="block w-full cursor-pointer border-0 border-b border-white/10 bg-transparent px-[18px] py-[13px] text-left font-game-korean text-[16px] text-game-ivory hover:bg-white/5"
            >
              {clue.title}
            </button>
          ))}
        </div>
      )}

      {/* =========================================
          입력창 — Enter 로 전송
      ========================================= */}

      {/*
        ★전송 버튼이 화면 밖에 있던 것을 고친다 (2026-08-29, 3차 제보).

          상자가 left 670 · width 800 이라 오른끝이 1470 — 이미 화면(1440) 밖인데,
          거기에 scaleX(1.1) 까지 걸려 있었다. 가운데(1070)를 기준으로 늘어나니
          실제 오른끝은 1510. 「↵」는 1448~1510, **아무도 볼 수 없는 자리**였다.
          질문을 쓰고 엔터를 쳐야만 보낼 수 있었던 셈이다.

          그리고 chat.svg 는 제 비율(928:160)을 지킨다 — object-fill 로도 안 늘어난다.
          800×90(8.9:1)에 넣으니 테두리가 가운데 522px 만 차지했다.
          상자를 그림 비율에 맞추고, 안쪽 자리는 비율로 잡는다.
      */}
      <form
        onSubmit={handleSubmit}
        className="absolute"
        style={{
          left: 560,
          top: 884,

          /* chat.svg 비율 928:160 — 어긋나면 테두리가 상자 안에서 논다 */
          width: 700,
          height: 121,
        }}
      >
        <img
          src="/assets/icons/chat.svg"
          alt=""
          className="absolute inset-0 h-full w-full object-fill"
        />

        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={
            remainingTurns > 0
              ? '질문을 입력하세요.'
              : '이번 라운드의 행동을 모두 사용했습니다.'
          }
          disabled={remainingTurns <= 0 || pending}
          className="
            absolute
            border-0
            bg-transparent
            outline-none
            font-game-korean
            text-game-ivory
            placeholder:text-white/30
          "
          style={{
            /* 그림 테두리 안쪽 — 비율로 두면 상자를 키워도 따라온다 */
            left: '8%',
            top: '30%',

            width: '73%',
            height: '40%',

            fontSize: 20,
          }}
        />
      </form>
    </>
  )
}
