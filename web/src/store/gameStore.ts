import { create } from 'zustand'

import type {
  ClueCard,
  Scenario,
} from '../types/scenario'
import type { GameStatus } from '../types/game'
import { playSfx } from '../lib/sfx'
import { getScenarioId } from '../data/scenarioAdapter'
import {
  ApiError,
  askSuspect,
  getNotebook,
  getTimeline,
  getSessionScenario,
  getState,
  meetSuspect,
  nextRound as nextRoundRequest,
  runConfrontation,
  combineClues,
  searchPlace,
  startSession,
  submitAccusation,
  type AccuseResult,
  type ConfrontResult,
  type CombineResult,
  type SearchResult,
  type SessionBundle,
  type ServerClueCard,
  type TimelineRow,
  type ServerState,
  type Stance,
} from '../api/scenarioApi'


/*
  판 번호를 탭에 적어 둔다.

  새로고침 한 번에 조사하던 판이 통째로 날아가면 시연이 곤란하다.
  판 자체는 서버에 있으니, 번호만 들고 있다가 다시 물어보면 된다.
  탭을 닫으면 지워진다 — 다음 사람이 남의 판을 이어받지 않도록.
*/
const SESSION_KEY = 'mm.sessionId'

const rememberSession = (sessionId: string | null) => {
  try {
    if (sessionId === null) {
      window.sessionStorage.removeItem(SESSION_KEY)
    } else {
      window.sessionStorage.setItem(SESSION_KEY, sessionId)
    }
  } catch {
    /* 저장을 막아 둔 브라우저라도 판은 돌아가야 한다 */
  }
}

const MUTE_KEY = 'mm.muted'

const readMuted = () => {
  try {
    return window.localStorage.getItem(MUTE_KEY) === '1'
  } catch {
    return false
  }
}

const rememberedSession = () => {
  try {
    return window.sessionStorage.getItem(SESSION_KEY)
  } catch {
    return null
  }
}


/*
  ■ 게임 규칙은 서버에 있다.

  전에는 이 파일이 남은 행동을 세고, 라운드를 올리고, 단서를 모았다.
  지금은 세지 않는다 — 서버가 모든 응답에 state 를 실어 보내니
  그것을 그대로 비춘다(applyServerState).

  여기 남는 것은 화면의 몫뿐이다.
  고른 인물·장소, 메모, 대화 기록, 오버레이 표시 여부.
*/


/* 서버 state → 스토어. 모든 행동 응답 뒤에 부른다. */
export const applyServerState = (
  serverState: ServerState,
) => {
  if (!serverState) {
    return
  }

  const previous = useGameStore.getState()

  useGameStore.setState({
    serverState,

    currentRound: serverState.round,
    round: serverState.round,

    remainingTurns: serverState.turns_left,
    turnBudget: serverState.budget,
    roundFocus: serverState.round_focus,
    findableLeft: serverState.findable_left,

    /*
      서버는 예산이 0이 되어도 라운드를 넘기지 않는다.
      결과를 다 보여 준 뒤, 플레이어가 「이번 밤을 마친다」를 누를 때 넘긴다.
    */
    roundOver: serverState.round_over,
    canNextRound: serverState.can_next_round,
    isLastRound: serverState.is_last_round,

    confrontationUnlocked: serverState.confront.unlocked,
    confrontationTokensLeft: serverState.confront.tokens_left,
    confrontationLockedReason: serverState.confront.locked_reason,
    confrontationCost: serverState.confront.cost ?? 1,
    confrontationPairs: (serverState.confront.pairs ?? []).map((pair) => ({
      a: pair.a,
      b: pair.b,
      aName: pair.a_name ?? pair.a,
      bName: pair.b_name ?? pair.b,
    })),
    accuseAdvised: serverState.accuse_advised ?? true,

    discoveredClueIds: serverState.held_clues ?? previous.discoveredClueIds,

    metSuspectIds: serverState.cast
      .filter((cast) => cast.met)
      .map((cast) => cast.id),

    pressures: Object.fromEntries(
      serverState.cast.map((cast) => [cast.id, cast.pressure]),
    ),

    /*
      이미 지목한 판이면 결과도 돌려받는다.
      새로고침해도 엔딩 화면이 그대로 열린다.

      ★방금 받은 결과를 **덮어쓰지 않는다** (2026-08-31).
        지목 응답이 gameResult 를 채운 직후에 이 함수가 같은 자리를 다시 쓴다.
        여기 들어 있는 것은 되찾기용 요약이라 진상·비밀 성적표·감춘 사정이
        빠져 있다 — 그대로 덮으면 방금 받은 것이 통째로 날아간다.
        이미 있는 것 **위에 얹기만** 한다.
    */
    ...(serverState.verdict && {
      status: 'finished' as GameStatus,
      gameResult: {
        ...(previous.gameResult ?? {}),
        ...(serverState.verdict.score !== undefined && {
          score: serverState.verdict.score,
        }),
        ...(serverState.verdict.correct !== undefined && {
          correct: serverState.verdict.correct,
        }),
        ...(serverState.verdict.grade !== undefined && {
          grade: serverState.verdict.grade,
        }),
        ...(serverState.verdict.max !== undefined && {
          max: serverState.verdict.max,
        }),
        verdict:
          serverState.verdict.verdict ??
          previous.gameResult?.verdict,
        /* 발표용이면 새로고침해도 감춘 채로 열린다 */
        withheld:
          previous.gameResult?.withheld ??
          (serverState.verdict.withheld_reason
            ? { reason: serverState.verdict.withheld_reason }
            : null),
      },
    }),

    /*
      라운드가 올라갔으면 ROUND 시작 화면을 다시 띄운다.
    */
    roundStartVisible:
      serverState.round > previous.currentRound
        ? true
        : previous.roundStartVisible,
  })
}


/* 서버가 준 단서 카드를 시나리오의 수첩에 얹는다. */
const clueFieldValue = (
  card: ServerClueCard,
  labels: string[],
) =>
  card.fields
    ?.find((field) =>
      labels.some((label) =>
        field.label.toLowerCase().includes(label),
      ),
    )
    ?.value.trim() ?? ''

const readableClueName = (card: ServerClueCard) => {
  const name = card.name?.trim()
  if (name) return name

  const fieldName = clueFieldValue(card, [
    '단서명',
    '제목',
    '이름',
    'title',
    'name',
  ])
  if (fieldName) return fieldName

  const type = card.type?.trim()
  if (type) return type

  return /^CX_/i.test(card.clue_id)
    ? '대질에서 드러난 모순'
    : card.clue_id
}

const readableClueDescription = (card: ServerClueCard) => {
  const description = card.description?.trim()
  if (description) return description

  const fieldDescription = clueFieldValue(card, [
    '상세 설명',
    '설명',
    '서술',
    '내용',
    'description',
    'detail',
  ])
  if (fieldDescription) return fieldDescription

  const summary = card.list_sub?.trim()
  if (summary) return summary

  return /^CX_/i.test(card.clue_id)
    ? '대질을 통해 두 사람의 진술 사이에서 모순을 발견했다.'
    : ''
}

const mergeClueCards = (
  scenario: Scenario | null,
  cards: ServerClueCard[],
): Scenario | null => {
  if (scenario === null || cards.length === 0) {
    return scenario
  }

  const existing = new Set(
    scenario.ui.clue_cards.map((clue) => clue.clue_id),
  )

  const added = cards
    .filter((card) => !existing.has(card.clue_id))
    .map<ClueCard>((card) => ({
      clue_id: card.clue_id,
      name: readableClueName(card),
      list_sub: card.list_sub ?? '',
      image: card.image ?? card.thumb ?? '',
      full_image: card.full_image ?? '',
      type: card.type ?? '',
      acquired_place: card.acquired_place,
      acquired_method: card.acquired_method,
      description: readableClueDescription(card),
    }))

  if (added.length === 0) {
    return scenario
  }

  return {
    ...scenario,
    ui: {
      ...scenario.ui,
      clue_cards: [...scenario.ui.clue_cards, ...added],
    },
  }
}

/*
  /session 은 원본 scenario와 함께 화면용으로 정리한 opening/crime_scene/
  victim/suspects도 내려 준다. 기존 scenario 값이 있으면 그대로 두고, 비어
  있을 때만 view 값을 보충한다. 따라서 현재 화면 구조와 기존 응답을 깨지
  않으면서 두 백엔드 형식을 모두 받을 수 있다.
*/
const hydrateScenarioFromBundle = (bundle: SessionBundle): Scenario => {
  const scenario = bundle.scenario
  const suspectsById = new Map(bundle.suspects.map((item) => [item.id, item]))

  const hydrated: Scenario = {
    ...scenario,
    ui: {
      ...scenario.ui,
      narration: {
        ...scenario.ui.narration,
        pages: scenario.ui.narration.pages.map((page, index) => {
          const opening = bundle.opening[index]

          return {
            ...page,
            text: page.text || opening?.text || '',
            image: {
              ...page.image,
              url: page.image?.url || opening?.image || undefined,
            },
          }
        }),
      },
      victim_card: {
        ...scenario.ui.victim_card,
        name: scenario.ui.victim_card.name || bundle.victim.name,
        role: scenario.ui.victim_card.role || bundle.victim.role,
        bio: scenario.ui.victim_card.bio || bundle.victim.bio || undefined,
        found_place:
          scenario.ui.victim_card.found_place ||
          bundle.victim.found_place ||
          undefined,
        found_time:
          scenario.ui.victim_card.found_time ||
          bundle.victim.found_time ||
          undefined,
        portrait:
          scenario.ui.victim_card.portrait || bundle.victim.photo || '',
        body_art:
          scenario.ui.victim_card.body_art || bundle.crime_scene.image || '',
      },
      suspect_cards: scenario.ui.suspect_cards.map((card) => {
        const view = suspectsById.get(card.id)

        return {
          ...card,
          name: card.name || view?.name || '',
          intro: card.intro || view?.intro || '',
          list_sub: card.list_sub || view?.public || '',
          portrait: card.portrait || view?.photo || '',
          theme: card.theme || view?.theme || '',
        }
      }),
    },
  }

  return mergeClueCards(hydrated, bundle.crime_scene.clues) ?? hydrated
}


export type SelectedLibraryCase = {
  id: string
  title: string
  origin: string

  backgroundLine: string
  incidentLine: string
  endingLine1: string
  endingLine2: string
}

/*
  판을 되찾은 결과.
    ok           되찾았다
    gone         서버가 404 — 판이 없다(수명이 다했거나 서버가 다시 켜졌다)
    unreachable  서버에 못 닿았다 — 판은 아직 있을 수 있다. 다시 시도할 자리다.
*/
export type RestoreResult = 'ok' | 'gone' | 'unreachable'

export type ChatMessage = {
  id: number
  sender: 'user' | 'suspect'
  text: string
  stance?: Stance
  face?: string
  /* 이 대답에서 비밀이 열렸는가 — 채팅이 붉게 물든다 */
  secretOpened?: boolean
}

export type ConfrontationLogMessage = {
  name: string
  text: string
  /* narration — 판정자의 말. 두 사람 어느 쪽도 아니다 */
  side: 'user' | 'left' | 'right' | 'narration'
  beat?: string
}


type GameStore = {
  sourceTitle: string

  scenario: Scenario | null
  status: GameStatus
  scenarioId: string | null

  /* 한 판 = 한 세션. 모든 행동이 이 id로 간다 */
  sessionId: string | null

  /* 서버가 마지막으로 알려 준 상태 그대로 */
  serverState: ServerState | null

  currentRound: number
  remainingAttempts: number
  remainingTurns: number
  turnBudget: number
  roundFocus: string
  findableLeft: number
  roundOver: boolean
  canNextRound: boolean
  isLastRound: boolean

  selectedSuspectId: string | null
  selectedPlaceId: string | null

  discoveredClueIds: string[]
  metSuspectIds: string[]

  /* 인물별 압박 게이지 */
  pressures: Record<string, number>

  /* 지금 심문 화면에 띄울 얼굴 (판정에 따라 바뀐다) */
  suspectFaces: Record<string, string>

  /* 방문한 장소 */
  visitedPlaceIds: string[]

  /*
    이미 조사한 행동.
    round + placeId + actionId 를 합쳐 저장한다.
  */
  investigatedActionIds: string[]

  confrontationUsed: boolean
  confrontationUnlocked: boolean
  confrontationTokensLeft: number
  confrontationLockedReason: string | null
  /* 시나리오가 고른 「말이 어긋나는 짝」 */
  confrontationPairs: Array<{
    a: string
    b: string
    aName: string
    bName: string
  }>
  /* 대질에 드는 행동 (지금은 1) */
  confrontationCost: number
  /*
    ★지목 버튼은 마지막 밤에만 (팀원 제보 —
      "1, 2라운드에선 범인 맞추기 그냥 없애는 게 나을 듯").
      서버가 막지는 않는다 — 이른 지목은 대개 찍기라, 화면에서 감추는 편이 낫다.
  */
  accuseAdvised: boolean
  confrontationPair: [string, string] | null

  personMemos: Record<string, string>
  clueMemos: Record<string, string>
  freeMemo: string
  interrogationLogs: Record<string, ChatMessage[]>
  confrontationLog: ConfrontationLogMessage[]
  gameResult: {
    /*
      ★발표용은 이 넷을 **안 준다** (2026-08-31).
        맞았는지·몇 점인지가 곧 「범인이 누구인가」를 알려 주는 값이다.
        그래서 없을 수 있는 것으로 둔다 — 쓰는 쪽은 이미 ?? 로 받고 있다.
    */
    score?: number
    correct?: boolean
    grade?: string
    max?: number
    secretsOpened?: number
    /*
      못 맞혔을 때 감춘 것 — 진상·재연·범인 얼굴.
      화면은 이것을 보고 진상·재연을 건너뛴다.
    */
    withheld?: { reason: string } | null
    /* 연 비밀과 못 연 비밀 — 엔딩이 성적표로 그린다 */
    secretsRecord?: {
      opened: number
      total: number
      items: Array<{
        castId: string
        castName: string
        opened: boolean
        text: string
      }>
    }
    /*
      ★점수가 아니라 성공/실패다 (팀원 제보).
        범인과 흉기를 모두 맞혀야 ARREST. 이름만 맞히면 수법을 못 밝힌 것이라 FAIL.
    */
    verdict?: 'ARREST' | 'FAIL' | 'SUBMITTED'
    verdictLine?: string
    weaponCorrect?: boolean
    trueWeapon?: string | null
  } | null

  /*
    엔딩 갈래 — 붙잡힌 밤 / 빠져나간 밤.
    /accuse 응답에만 실린다. 새로고침하면 없어지지만, 그때는 등급 글로 대신한다.
  */
  endingBranch: {
    label?: string
    beats?: Array<
      | string
      | {
          text: string
          secret_id?: string | null
        }
    >
    result_line?: string
  } | null

  gameTitle: string
  round: number
  lives: number
  caseSummary: string
  /* 사건 공개 화면이 읽는 한 줄 — 피해자를 밝히지 않는다 */
  caseNarration: string

  selectedLibraryCase: SelectedLibraryCase | null

  roundStartVisible: boolean
  roundEvent: { name: string; text: string } | null

  /* 이번 라운드에 새로 들어온 단서 — 라운드 시작 화면에서 보여 준다 */
  newClues: ClueCard[]
  openedSecrets: string[]

  /* 그날 밤 시간표 (수첩 [시간표] 탭) */
  timeline: TimelineRow[]
  timelineNote: string

  /* 소리 — 시나리오 ui.screens[].bgm 이 정한 대로 화면마다 갈린다 */
  audio: {
    cues: Record<string, string | null>
    events: Record<string, string | null>
    ui: Record<string, string | null>
    places: Record<string, string | null>
    characters: Record<string, string | null>
  } | null
  muted: boolean

  /* ── 서버를 부르는 행동 ── */
  openSession: (scenarioFile: string) => Promise<void>
  restoreSession: () => Promise<RestoreResult>
  investigate: (
    placeId: string,
    actionIndex: number,
  ) => Promise<SearchResult>
  meet: (castId: string) => Promise<string>
  interrogate: (
    castId: string,
    question: string,
    clueId?: string | null,
  ) => Promise<{
    line: string | null
    stance: Stance
    face: string | null
    openedSecrets: string[]
  }>
  confront: (
    a: string,
    b: string,
    question: string,
  ) => Promise<ConfrontResult>
  /* 수첩에서 단서 둘을 겹쳐 본다 — 행동을 쓰지 않는다 */
  combine: (clueA: string, clueB: string) => Promise<CombineResult>
  advanceRound: () => Promise<number>
  loadTimeline: () => Promise<void>
  accuse: (
    castId: string,
    weapon?: string,
    motive?: string,
  ) => Promise<AccuseResult>

  /* ── 화면의 몫 ── */
  setSourceTitle: (title: string) => void
  setStatus: (status: GameStatus) => void
  setGameTitle: (title: string) => void
  setLives: (lives: number) => void
  setCaseSummary: (summary: string) => void
  setSelectedSuspectId: (suspectId: string | null) => void
  setSelectedPlaceId: (placeId: string | null) => void
  setSelectedLibraryCase: (selectedCase: SelectedLibraryCase) => void
  visitPlace: (placeId: string) => void
  markActionInvestigated: (actionKey: string) => void
  showRoundStart: () => void
  hideRoundStart: () => void
  clearRoundEvent: () => void
  clearNewClues: () => void
  toggleMuted: () => void
  startConfrontation: (pair: [string, string]) => void
  setPersonMemo: (id: string, memo: string) => void
  setClueMemo: (id: string, memo: string) => void
  setFreeMemo: (memo: string) => void
  setInterrogationLog: (id: string, messages: ChatMessage[]) => void
  setConfrontationLog: (messages: ConfrontationLogMessage[]) => void
  startNewGame: () => void
}


const blankState = {
  sourceTitle: '',
  scenario: null,
  status: 'idle' as GameStatus,
  scenarioId: null,
  sessionId: null,
  serverState: null,

  currentRound: 1,
  remainingAttempts: 0,
  remainingTurns: 0,
  turnBudget: 0,
  roundFocus: '',
  findableLeft: 0,
  roundOver: false,
  canNextRound: true,
  isLastRound: false,

  selectedSuspectId: null,
  selectedPlaceId: null,

  discoveredClueIds: [],
  metSuspectIds: [],
  pressures: {},
  suspectFaces: {},
  visitedPlaceIds: [],
  investigatedActionIds: [],

  confrontationUsed: false,
  confrontationUnlocked: false,
  confrontationTokensLeft: 0,
  confrontationPairs: [],
  confrontationCost: 1,
  accuseAdvised: false,
  confrontationLockedReason: null,
  confrontationPair: null,

  personMemos: {},
  clueMemos: {},
  freeMemo: '',
  interrogationLogs: {},
  confrontationLog: [],
  gameResult: null,
  endingBranch: null,

  gameTitle: '',
  round: 1,
  lives: 0,
  caseSummary: '',
  caseNarration: '',
  selectedLibraryCase: null,
  roundStartVisible: false,
  roundEvent: null,
  newClues: [],
  openedSecrets: [],
  timeline: [],
  timelineNote: '',
  audio: null,
  muted: readMuted(),
}


export const useGameStore = create<GameStore>((set, get) => ({
  ...blankState,


  /* =========================================
     판을 연다 (S-05 ~ S-10)

     실시간 생성은 없다. 미리 만들어 둔 사건을
     세션으로 열 뿐이다.
  ========================================= */
  openSession: async (scenarioFile) => {
    const bundle = await startSession(scenarioFile)
    const hydratedScenario = hydrateScenarioFromBundle(bundle)
    const hud = (bundle.scenario.ui.hud ?? {}) as Record<string, string>

    set({
      ...blankState,

      /*
        ★기록실에서 고른 카드를 지우지 않는다 (2026-08-29, 시연 제보).
          제보: "처음 화면 「여섯 잔의 회의」가 깨졌다."
          실은 깨진 게 아니라 **비어 있었다.** 사건 공개 화면은 배경·사건·엔딩
          문구를 selectedLibraryCase 에서 읽는데, 판을 열면서 blankState 로
          싹 지우고 있었다. 제목만 남고 아래가 통째로 빈 것이다.
      */
      selectedLibraryCase: get().selectedLibraryCase,
      audio: bundle.audio as never,
      muted: get().muted,

      sessionId: bundle.session_id,
      scenario: hydratedScenario,
      scenarioId: getScenarioId(hydratedScenario),
      status: 'playing',

      gameTitle: hydratedScenario.title ?? '',
      caseSummary:
        hud.summary_text ??
        bundle.crime_scene.description ??
        '',

      /*
        사건 공개 화면(빨간 화면 **앞**)이 읽는 한 줄.
        이름도 사인도 없는 나레이션이다 — 현장 묘사(crime_scene.description)는
        누가 죽었는지를 적어 두고 있어서 이 자리에 쓸 수 없다.
      */
      caseNarration: bundle.case.narration ?? '',

      remainingAttempts: bundle.config.attempts,
      lives: bundle.config.attempts,

      /* 처음 Main 에 들어설 때 ROUND 1 화면을 띄운다 */
      roundStartVisible: true,
    })

    rememberSession(bundle.session_id)
    applyServerState(bundle.state)
  },


  /* 그날 밤 시간표 — 수첩 [시간표] 탭이 부른다 */
  loadTimeline: async () => {
    const sessionId = get().sessionId

    if (sessionId === null) {
      return
    }

    try {
      const result = await getTimeline(sessionId)
      set({ timeline: result.rows, timelineNote: result.note })
      applyServerState(result.state)
    } catch {
      /* 시간표를 못 받아도 판은 돌아간다 */
    }
  },


  /* =========================================
     새로고침한 뒤 판을 되찾는다

     판은 서버에 있다. 탭이 들고 있던 번호로 다시 물어본다.
     이미 손에 든 단서까지 그대로 돌아온다.

     ★못 되찾았을 때를 **두 갈래로** 나눈다 (2026-08-31, 제보 —
       "새로고침하면 오류 뜨면서 원래 창으로 못 되돌아감").

       전에는 어떤 실패든 판 번호를 지우고 false 를 돌려줬다. 그런데 배포된
       백엔드는 놀면 잠들고, 깨어나는 데 30초쯤 걸린다(실측 31.4초). 그 사이
       요청이 한 번 엎어지면 **서버가 늦게 깬 것뿐인데 판 번호까지 버려서**
       다시 눌러 볼 길조차 없어졌다.

         'gone'        서버가 404 — 판이 정말 없다. 그때만 번호를 버린다.
         'unreachable' 못 닿았다(그물·502·시간 초과). **번호는 그대로 둔다.**

       판이 메모리에만 있는 것은 서버 쪽 사정이다(server.py 의 SESSIONS·TTL).
       화면이 할 수 있는 일은, 되찾을 수 있는 판을 제 손으로 버리지 않는 것이다.
  ========================================= */
  restoreSession: async () => {
    if (get().scenario !== null) {
      return 'ok'
    }

    const sessionId = rememberedSession()

    if (sessionId === null) {
      return 'gone'
    }

    try {
      const [scenario, state, notebook] = await Promise.all([
        getSessionScenario(sessionId),
        getState(sessionId),
        getNotebook(sessionId),
      ])

      set({
        sessionId,
        /* 서버 버전에 따라 cards 가 없을 수 있다 — 없다고 판을 잃어서는 안 된다 */
        scenario: mergeClueCards(scenario, notebook.cards ?? []),
        scenarioId: getScenarioId(scenario),
        status: 'playing',
        gameTitle: scenario.title ?? '',
        caseSummary:
          ((scenario.ui.hud ?? {}) as Record<string, string>).summary_text ??
          scenario.death.scene_description,
        remainingAttempts: scenario.config.attempts,
        lives: scenario.config.attempts,
        audio: (scenario.ui.audio ?? null) as never,
      })

      applyServerState(state)

      return 'ok'
    } catch (error) {
      /* 판이 정말 없을 때만 번호를 버린다 */
      if (error instanceof ApiError && error.status === 404) {
        rememberSession(null)
        return 'gone'
      }

      return 'unreachable'
    }
  },


  /* =========================================
     장소 조사 (S-14)

     값은 장소에 매겨진다 —
     그 라운드에 처음 뒤지는 방만 1턴이고,
     그 방의 단서는 한꺼번에 다 나온다.
     빈 방은 값이 들지 않는다.
  ========================================= */
  investigate: async (placeId, actionIndex) => {
    const sessionId = get().sessionId

    if (sessionId === null) {
      throw new Error('열려 있는 판이 없습니다.')
    }

    const result = await searchPlace(sessionId, {
      placeId,
      actionIndex,
    })

    set({ scenario: mergeClueCards(get().scenario, result.found) })
    playSfx(result.sfx, get().muted)
    applyServerState(result.state)

    return result
  },


  /* 첫 대면 알리바이 — 행동을 쓰지 않는다 */
  meet: async (castId) => {
    const sessionId = get().sessionId

    if (sessionId === null) {
      return ''
    }

    const result = await meetSuspect(sessionId, castId)

    if (result.face) {
      set((state) => ({
        suspectFaces: { ...state.suspectFaces, [castId]: result.face! },
      }))
    }

    /* 첫 대면에는 서버가 효과음을 주지 않는다 — 행동도 아니다 */
    applyServerState(result.state)

    return result.alibi
  },


  /* =========================================
     심문 (S-15) — 1턴

     line 이 null 이면 서버에 API 키가 없는 것이다.
     판정(stance)과 얼굴은 그대로 오니 화면은 그려진다.
  ========================================= */
  interrogate: async (castId, question, clueId) => {
    const sessionId = get().sessionId

    if (sessionId === null) {
      throw new Error('열려 있는 판이 없습니다.')
    }

    const result = await askSuspect(sessionId, {
      castId,
      question,
      clueId,
    })

    if (result.face) {
      set((state) => ({
        suspectFaces: { ...state.suspectFaces, [castId]: result.face! },
      }))
    }

    playSfx(result.sfx, get().muted)
    applyServerState(result.state)

    return {
      line: result.line,
      stance: result.stance,
      face: result.face,
      /* 이 대답으로 새로 열린 비밀 — 채팅이 붉게 물드는 신호가 된다 */
      openedSecrets: result.secrets_opened ?? [],
    }
  },


  /* 대질 (S-16) — 한 판 1회, 행동 예산 밖 */
  /* =========================================
     단서 겹쳐 보기

     ★여태 화면이 **가짜로 판정하고 있었다** (2026-08-31, 제보 — "단서 겹쳐보기").
       ClueCombineModal 에 'clue-1 + clue-2 면 성공' 같은 임시 규칙이 박혀 있어,
       실제 단서로는 무엇을 겹쳐도 늘 실패였다. 서버에는 편당 평균 네 개의
       조합이 준비돼 있다(/session/{id}/combine). 그쪽에 묻는다.
  ========================================= */
  combine: async (clueA, clueB) => {
    const sessionId = get().sessionId

    if (sessionId === null) {
      throw new Error('열려 있는 판이 없습니다.')
    }

    const result = await combineClues(sessionId, {
      clue_a: clueA,
      clue_b: clueB,
    })

    applyServerState(result.state)

    return result
  },


  confront: async (a, b, question) => {
    const sessionId = get().sessionId

    if (sessionId === null) {
      throw new Error('열려 있는 판이 없습니다.')
    }

    const result = await runConfrontation(sessionId, { a, b, question })

    set({
      confrontationUsed: true,
      scenario: mergeClueCards(
        get().scenario,
        result.gained_clue ? [result.gained_clue] : [],
      ),
    })
    playSfx(result.sfx, get().muted)
    applyServerState(result.state)

    return result
  },


  /* 라운드 넘기기 (S-20 → S-12) */
  advanceRound: async () => {
    const sessionId = get().sessionId

    if (sessionId === null) {
      return get().currentRound
    }

    const result = await nextRoundRequest(sessionId)

    /*
      라운드 단서와 이벤트 단서가 new_clues 한 자리에 온다.
      라운드 시작 화면에서 이것을 보여 준다 —
      제보: "라운드가 바뀌면서 나오는 새 단서를 확인할 수 없다."
    */
    const merged = mergeClueCards(get().scenario, result.new_clues)

    set({
      scenario: merged,
      roundEvent: result.event,
      newClues: (merged?.ui.clue_cards ?? []).filter((card) =>
        result.new_clues.some((c) => c.clue_id === card.clue_id),
      ),
      openedSecrets: result.opened_secrets ?? [],

      /*
        라운드가 바뀌면 방문 기록을 푼다 —
        제보: "라운드가 바뀌어도 「이미 가봄」이 리셋되지 않는다."
        서버는 라운드마다 다시 뒤질 수 있게 두는데, 화면만 기억하고 있었다.
      */
      visitedPlaceIds: [],
      investigatedActionIds: [],
    })
    playSfx(result.sfx, get().muted)
    applyServerState(result.state)

    return result.round
  },


  /* =========================================
     범인 지목 (S-21) — 되돌릴 수 없다.

     여기서 처음으로 진상·재연이 열린다.
     받은 것을 시나리오에 얹어 두면
     RevealPage 가 그대로 읽는다.
  ========================================= */
  accuse: async (castId, weapon, motive) => {
    const sessionId = get().sessionId

    if (sessionId === null) {
      throw new Error('열려 있는 판이 없습니다.')
    }

    const result = await submitAccusation(sessionId, {
      castId,
      weapon,
      motive,
    })

    const scenario = get().scenario

    /*
      통합 백엔드 버전에 따라 진상 묶음이 truth 또는
      ui.reveal_sequence로 올 수 있다. 둘 다 같은 화면 모델로 정규화한다.
    */
    const rawResult = result as unknown as Record<string, unknown>
    const rawUi =
      rawResult.ui !== null && typeof rawResult.ui === 'object'
        ? (rawResult.ui as Record<string, unknown>)
        : null
    const alternateReveal =
      rawUi?.reveal_sequence !== null &&
      typeof rawUi?.reveal_sequence === 'object'
        ? (rawUi.reveal_sequence as typeof result.truth)
        : null
    const alternateReenactment =
      rawUi?.murder_reenactment !== null &&
      typeof rawUi?.murder_reenactment === 'object'
        ? (rawUi.murder_reenactment as typeof result.reenactment)
        : null
    const revealSequence =
      result.truth?.beats?.length > 0 || result.truth?.full_text
        ? result.truth
        : alternateReveal ?? result.truth
    const revealFullText =
      revealSequence?.full_text?.trim() ||
      result.ending.truth_reveal?.trim() ||
      scenario?.ending.truth_reveal?.trim() ||
      ''

    playSfx(result.sfx, get().muted)

    set({
      status: 'finished',
      gameResult: {
        /* 서버 버전에 따라 score 또는 points 로 온다 */
        score: result.score ?? result.points ?? 0,
        correct: result.correct,
        grade: result.grade,
        max: result.max,
        secretsOpened: result.secrets_opened,
        withheld: result.withheld ? { reason: result.withheld.reason } : null,
        secretsRecord: result.secrets_record
          ? {
              opened: result.secrets_record.opened,
              total: result.secrets_record.total,
              items: result.secrets_record.items.map((x) => ({
                castId: x.cast_id,
                castName: x.cast_name,
                opened: x.opened,
                text: x.text,
              })),
            }
          : undefined,
        verdict:
          result.verdict ??
          (result.correct ? 'ARREST' : 'FAIL'),
        verdictLine: result.verdict_line,
        weaponCorrect: result.weapon_correct,
        trueWeapon: result.true_weapon ?? null,
      },
      endingBranch: result.ending.branch,
      scenario:
        scenario === null
          ? null
          : {
              ...scenario,
              ui: {
                ...scenario.ui,
                reveal_sequence: {
                  beats: revealSequence?.beats ?? [],
                  full_text: revealFullText,
                },
                murder_reenactment:
                  result.reenactment?.cuts?.length > 0
                    ? result.reenactment
                    : alternateReenactment ?? result.reenactment,
              },
              ending: {
                ...scenario.ending,
                truth_reveal: revealFullText,
              },
            },
    })

    applyServerState(result.state)

    return result
  },


  /* ── 화면의 몫 ────────────────────────── */

  setSourceTitle: (title) => set({ sourceTitle: title }),

  setStatus: (status) => set({ status }),

  setGameTitle: (title) => set({ gameTitle: title }),

  setLives: (lives) =>
    set({ lives, remainingAttempts: lives }),

  setCaseSummary: (summary) => set({ caseSummary: summary }),

  setSelectedSuspectId: (suspectId) =>
    set({ selectedSuspectId: suspectId }),

  setSelectedPlaceId: (placeId) =>
    set({ selectedPlaceId: placeId }),

  setSelectedLibraryCase: (selectedCase) =>
    set({
      selectedLibraryCase: selectedCase,
      gameTitle: selectedCase.title,
      caseSummary: `${selectedCase.backgroundLine} ${selectedCase.incidentLine}`,
    }),

  visitPlace: (placeId) =>
    set((state) =>
      state.visitedPlaceIds.includes(placeId)
        ? state
        : { visitedPlaceIds: [...state.visitedPlaceIds, placeId] },
    ),

  markActionInvestigated: (actionKey) =>
    set((state) =>
      state.investigatedActionIds.includes(actionKey)
        ? state
        : {
            investigatedActionIds: [
              ...state.investigatedActionIds,
              actionKey,
            ],
          },
    ),

  showRoundStart: () => set({ roundStartVisible: true }),

  hideRoundStart: () => set({ roundStartVisible: false }),

  clearRoundEvent: () => set({ roundEvent: null }),

  clearNewClues: () => set({ newClues: [], openedSecrets: [] }),

  toggleMuted: () =>
    set((state) => {
      const muted = !state.muted
      try {
        window.localStorage.setItem(MUTE_KEY, muted ? '1' : '0')
      } catch {
        /* 저장을 막아 둔 브라우저라도 소리는 꺼진다 */
      }
      return { muted }
    }),

  startConfrontation: (pair) =>
    set({ confrontationPair: pair, confrontationLog: [] }),

  setPersonMemo: (id, memo) =>
    set((state) => ({
      personMemos: { ...state.personMemos, [id]: memo },
    })),

  setClueMemo: (id, memo) =>
    set((state) => ({
      clueMemos: { ...state.clueMemos, [id]: memo },
    })),

  setFreeMemo: (memo) => set({ freeMemo: memo }),

  setInterrogationLog: (id, messages) =>
    set((state) => ({
      interrogationLogs: {
        ...state.interrogationLogs,
        [id]: messages,
      },
    })),

  setConfrontationLog: (messages) =>
    set({ confrontationLog: messages }),

  startNewGame: () => {
    rememberSession(null)
    set({ ...blankState })
  },
}))
