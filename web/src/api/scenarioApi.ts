/*
  scenarioApi.ts — 백엔드(Gaeun/server.py)와 이야기하는 곳.

  ■ 한 판이 한 세션이다.
    POST /session 으로 판을 열면 session_id 가 나온다.
    그 뒤 모든 행동은 /session/{sid}/... 로 간다.

  ■ 게임 규칙은 서버에 있다.
    남은 행동·라운드·찾은 단서·대질 해금은 프론트가 세지 않는다.
    모든 응답에 state 가 실려 오니 그걸 그대로 그린다.

  ■ 정답은 지목 전까지 내려오지 않는다.
    진상·재연·범인은 POST /accuse 응답에서 처음 나타난다.

  ■ 실시간 생성은 없다. 미리 만들어 둔 사건을 불러오기만 한다.
*/

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ??
  'http://127.0.0.1:8000'

/*
  그림·음원이 어디 있는가.

  로컬에서는 백엔드가 같이 뿌린다(기본값).
  배포할 때는 프론트(CDN)에 얹는 편이 낫다 — 백엔드는 가벼워지고
  이미지는 CDN이 훨씬 잘 뿌린다. 그때는 빈 문자열을 주면 된다:

      VITE_ASSET_BASE_URL=

  그러면 `/assets/...` 를 그대로 써서 이 사이트 안에서 찾는다.
*/
const ASSET_BASE_URL =
  import.meta.env.VITE_ASSET_BASE_URL !== undefined
    ? import.meta.env.VITE_ASSET_BASE_URL.replace(/\/$/, '')
    : API_BASE_URL

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const apiFetch = async <T>(
  path: string,
  init?: RequestInit,
): Promise<T> => {
  if (!API_BASE_URL) {
    throw new Error('VITE_API_BASE_URL이 설정되지 않았습니다.')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: unknown
    } | null
    const detail =
      typeof body?.detail === 'string'
        ? body.detail
        : `API 요청 실패 (${response.status})`

    throw new ApiError(detail, response.status)
  }

  return absolutizeAssets(await response.json()) as T
}

/*
  서버는 그림·소리를 `/assets/...` 로 알려 준다. 그대로 <img src> 에 넣으면
  브라우저가 **프론트 주소** 밑에서 찾는다 — 파일은 API 서버에 있는데.

  그래서 응답이 들어오는 길목에서 한 번만 앞을 채워 둔다. 여기 한 곳만 고치면
  되고, 화면 쪽은 받은 주소를 그냥 쓰면 된다.
*/
const absolutizeAssets = (value: unknown): unknown => {
  if (typeof value === 'string') {
    return value.startsWith('/assets/') ? `${ASSET_BASE_URL}${value}` : value
  }

  if (Array.isArray(value)) {
    return value.map(absolutizeAssets)
  }

  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {}

    for (const [key, item] of Object.entries(value)) {
      out[key] = absolutizeAssets(item)
    }

    return out
  }

  return value
}

const post = <T>(path: string, body?: unknown) =>
  apiFetch<T>(path, {
    method: 'POST',
    body: JSON.stringify(body ?? {}),
  })

/* 응답을 거치지 않은 주소를 직접 채울 때만 쓴다. */
export const assetUrl = (path?: string | null) =>
  !path
    ? ''
    : /^(https?:|data:)/.test(path)
      ? path
      : `${ASSET_BASE_URL}${path}`

/* =========================================
   서버 상태 — 모든 응답에 실려 온다
========================================= */

export type Stance =
  | 'ANSWER'
  | 'DEFLECT'
  | 'FLINCH'
  | 'ADMIT'
  | 'BREAK'

export interface CastState {
  id: string
  name: string
  public: string
  met: boolean
  alibi: string | null
  secrets_open: string[]
  secrets_left: number
  pressure: number
  portrait: string | null
  faces: {
    calm: string | null
    shaken: string | null
    broken: string | null
  }
  theme: string | null
}

export interface ServerState {
  round: number
  max_rounds: number
  turns_left: number
  budget: number
  round_focus: string
  findable_left: number
  /*
    예산을 다 썼는가. 서버는 예산이 0이 되어도 **라운드를 넘기지 않는다** —
    넘기는 것은 화면이 /next_round 를 부를 때뿐이다.
    참이면 결과를 보여 주고 「이번 밤을 마친다」를 띄운다.
  */
  round_over: boolean
  can_next_round: boolean
  is_last_round: boolean
  confront: {
    unlocked: boolean
    tokens_left: number
    unlock_round: number
    locked_reason: string | null
    /* 대질도 행동 1을 쓴다 — 화면이 그대로 읽어 준다 */
    cost_note?: string
    cost?: number
    /*
      ★말이 어긋나는 짝 (팀원 제보 — "대질심문에 사람이 한 명으로 뜬다").
        시나리오가 cross_examination.pairs 에 볼 만한 짝을 갖고 있다.
        아무나 맞세울 수도 있지만, 이 짝들이 실제로 어긋난다.
    */
    pairs?: Array<{
      a: string
      b: string
      a_name: string | null
      b_name: string | null
    }>
  }
  /* 마지막 밤에만 참 — 그때만 지목 버튼을 띄운다 */
  accuse_advised?: boolean
  held_clues: string[]
  /* 이미 지목한 판이면 그 결과. 아직이면 null */
  verdict: {
    named: string
    /* 발표용에서는 맞았는지를 아예 안 준다 — 그것이 곧 답이다 */
    correct?: boolean
    score?: number
    max?: number
    grade?: string
    hide_answer?: boolean
    withheld_reason?: string
    /* 새로고침해도 엔딩이 그대로 열리게 — 판정도 함께 남는다 */
    verdict?: 'ARREST' | 'FAIL' | 'SUBMITTED'
    success?: boolean
  } | null
  cast: CastState[]
  notebook: unknown[]
}

export type WithState<T> = T & { state: ServerState }

/* =========================================
   단서 카드 — 손에 넣은 것만 내려온다
========================================= */

export interface ServerClueCard {
  id: string
  clue_id: string
  name: string | null
  list_sub: string | null
  description: string | null
  fields: Array<{ label: string; value: string }> | null
  type: string | null
  acquired_place: string
  acquired_method: string
  thumb: string | null
  image: string | null
  full_image: string | null
}

/* =========================================
   사건 기록실 (S-04)
========================================= */

export interface LibraryCaseSummary {
  id: string
  title: string
  origin: string
  backgroundLine: string
  incidentLine: string
  endingLine1: string
  endingLine2: string
  suspects: number
  rounds: number
  difficulty: number
  coverImage: string
  category: 'folktale' | 'medieval' | 'modern'
  createdAt: number
}

type CatalogDifficulty =
  | number
  | {
      label?: string
      solve_rate?: number
    }

type RawLibraryCaseSummary = Omit<Partial<LibraryCaseSummary>, 'difficulty'> & {
  scenario_id?: string
  cover_image?: string
  created_at?: number
  background_line?: string
  incident_line?: string
  ending_line_1?: string
  ending_line_2?: string
  difficulty?: CatalogDifficulty
  solve_rate?: number
}

const difficultyNumber = (difficulty: CatalogDifficulty | undefined) => {
  if (typeof difficulty === 'number') return difficulty

  const label = difficulty?.label ?? ''
  if (label.includes('어려')) return 5
  if (label.includes('중')) return 3
  if (label.includes('쉬')) return 1
  return 0
}

/*
  catalog.json 원형(snake_case, difficulty 객체)과 기존 통합 API 형식
  (camelCase, difficulty 숫자)을 모두 받아 현재 화면 모델로만 변환한다.
*/
const normalizeLibraryCase = (
  item: RawLibraryCaseSummary,
  index: number,
): LibraryCaseSummary => ({
  id: item.id ?? item.scenario_id ?? String(index),
  title: item.title ?? '',
  origin: item.origin ?? '',
  backgroundLine: item.backgroundLine ?? item.background_line ?? '',
  incidentLine: item.incidentLine ?? item.incident_line ?? '',
  endingLine1: item.endingLine1 ?? item.ending_line_1 ?? '',
  endingLine2: item.endingLine2 ?? item.ending_line_2 ?? '',
  suspects: item.suspects ?? 0,
  rounds: item.rounds ?? 0,
  difficulty: difficultyNumber(item.difficulty),
  coverImage: item.coverImage ?? item.cover_image ?? '',
  category: item.category ?? 'folktale',
  createdAt: item.createdAt ?? item.created_at ?? 0,
})

export const getLibraryCases = async () => {
  const items = await apiFetch<RawLibraryCaseSummary[]>('/scenarios/library')
  return items.map(normalizeLibraryCase)
}

/*
  소리 목록 — 판을 열기 전에도 받아 온다.

  곡은 판이 아니라 번들에 딸린 것인데, 지금까지는 /session 응답에만 실려
  있었다. 그래서 첫 화면과 기록실이 조용했다 — 타이틀 곡이 번들에 있는데도.
*/
export interface AudioBook {
  cues: Record<string, string | null>
  events: Record<string, string | null>
  ui: Record<string, string | null>
  /* 장소 곡 — 열쇠는 "PC_post_murder" 처럼 살인 전/후까지 붙은 이름 */
  places: Record<string, string | null>
  /* 인물 테마 — 열쇠는 cast_id */
  characters: Record<string, string | null>
}

export const getAudioBook = () => apiFetch<AudioBook>('/audio')

/*
  게임 방법 (팀원 제보 — "게임룰 설명이 있으면 좋을 것 같음").

  화면이 규칙을 지어 쓰면 서버와 어긋난다 — 예산이 8인지 10인지, 대질이 행동을
  쓰는지가 바뀔 때마다 두 곳을 고쳐야 한다. 서버가 **그 판의 숫자로 채워** 준다.
*/
export interface GameRules {
  title: string
  items: Array<{ h: string; t: string }>
}

export const getRules = (sessionId: string) =>
  apiFetch<GameRules>(
    `/session/${encodeURIComponent(sessionId)}/rules`,
  )

/* =========================================
   판 열기 (S-05 ~ S-10)
========================================= */

export interface SessionBundle {
  session_id: string
  meta: Record<string, unknown>
  case: {
    logline: string | null
    setting: string | null
    narration: string | null
  }
  opening: Array<{
    page: number
    text: string
    image: string | null
    /* 권장 자동 넘김 시간(ms). 눌러도 바로 넘어가게 둔다 */
    auto_ms: number
  }>
  blood_transition: string | null
  crime_scene: {
    narration: string | null
    description: string | null
    image: string | null
    clues: ServerClueCard[]
  }
  victim: {
    name: string
    role: string
    bio: string | null
    self_intro: string[]
    found_place: string | null
    found_time: string | null
    /* 사인은 지목 전까지 "???" 다 — 흉기와 수법이 곧 정답이다 */
    cause: string
    narration: string | null
    photo: string | null
  }
  suspects: Array<{
    id: string
    name: string
    public: string
    intro: string | null
    photo: string | null
    theme: string | null
  }>
  config: {
    rounds: number
    turns_per_round: number
    attempts: number
    llm: boolean
  }
  /* 화면이 읽는 시나리오 — 정답은 빠져 있다 */
  scenario: import('../types/scenario').Scenario
  audio: Record<string, Record<string, string | null>>
  state: ServerState
}

/*
  ★발표용 판인가 — **빌드할 때** 정해진다 (2026-09-02).

    VITE_HIDE_ANSWER=1 로 빌드한 화면은 판을 열 때 그 사실을 서버에 알린다.
    그 판에서는 서버가 진상을 아예 안 보낸다 — 감추는 일은 여전히 서버가
    하므로 개발자도구로도 안 보인다.

    이렇게 두면 백엔드는 한 벌이면 된다. 발표용 백엔드를 따로 띄우던 때는
    화면에 그 주소를 다시 새겨야 했는데, 두 화면이 겉으로 똑같이 생겨서
    주소를 잘못 붙여도 지목 제출 직전까지 아무도 몰랐다.
*/
export const HIDE_ANSWER =
  String(import.meta.env.VITE_HIDE_ANSWER ?? '')
    .trim()
    .toLowerCase()
    .replace(/^(0|false|no)$/, '') !== ''

export const startSession = (scenario: string) =>
  post<SessionBundle>('/session', {
    scenario,
    ...(HIDE_ANSWER && { hide_answer: true }),
  })

export const getSessionScenario = (sessionId: string) =>
  apiFetch<import('../types/scenario').Scenario>(
    `/session/${encodeURIComponent(sessionId)}/scenario`,
  )

export const getState = (sessionId: string) =>
  apiFetch<ServerState>(
    `/session/${encodeURIComponent(sessionId)}/state`,
  )

/* =========================================
   장소 조사 (S-14)

   값은 장소에 매겨진다 —
   그 라운드에 처음 뒤지는 방만 1턴.
   빈 방은 값이 들지 않는다.
========================================= */

export interface SearchResult {
  place: string
  place_id: string
  first_visit: boolean

  /* 이번 조사에 든 행동. 0이면 안 깎였다 — 화면이 그대로 알려 주면 오해가 없다 */
  cost: number

  /* 누른 칸 이름 */
  pressed_label: string | null

  /* 화면에 그대로 읽어 줄 한 줄 — 문구를 프론트가 짓지 않는다 */
  message: string

  /* 연출 문장. 실제로 무언가 나온 칸 기준이라 결과와 어긋나지 않는다 */
  lines: string[]

  found: ServerClueCard[]
  already_had: string[]
  empty: boolean
  sfx: string | null
}

export const searchPlace = (
  sessionId: string,
  request: { placeId: string; actionIndex: number },
) =>
  post<WithState<SearchResult>>(
    `/session/${encodeURIComponent(sessionId)}/search`,
    { place_id: request.placeId, action_index: request.actionIndex },
  )

/* =========================================
   첫 대면 알리바이 (P-06) — 행동 0
========================================= */

export interface MeetResult {
  suspect_id: string
  suspect_name: string
  first_meet: boolean
  already: boolean
  alibi: string
  portrait: string | null
  face: string | null
  theme: string | null
}

export const meetSuspect = (sessionId: string, castId: string) =>
  post<WithState<MeetResult>>(
    `/session/${encodeURIComponent(sessionId)}/meet/${encodeURIComponent(castId)}`,
  )

/* =========================================
   심문 (S-15) — 1턴

   line 이 null 이면 서버에 API 키가 없는 것이다.
   판정(stance)과 압박은 그대로 오니 화면은 그려진다.
========================================= */

export interface AskResult {
  cast: { id: string; name: string }
  question: string
  line: string | null
  stance: Stance
  pressure: number
  turns_left: number
  secrets_opened: string[]
  belonging: string | null
  face: string | null
  sfx: string | null
}

export const askSuspect = (
  sessionId: string,
  request: { castId: string; question: string; clueId?: string | null },
) =>
  post<WithState<AskResult>>(
    `/session/${encodeURIComponent(sessionId)}/ask`,
    {
      cast_id: request.castId,
      question: request.question,
      clue_id: request.clueId ?? null,
    },
  )

/* =========================================
   대질 (S-16) — 한 판 1회, 행동 예산 밖
========================================= */

export interface ConfrontResult {
  a: string
  b: string
  a_id: string
  b_id: string
  a_portrait: string | null
  b_portrait: string | null
  angle: string | null
  /* 나레이션 한 줄로 올 때는 그냥 문자열이다 */
  opening: string | { speaker?: string; cast_id?: string; who?: string; name?: string; line?: string } | null
  exchange: Array<{
    /* 누가 말했는가 — id 가 가장 확실하고, who 는 A/B 자리다 */
    cast_id?: string
    who?: string
    name?: string
    speaker?: string
    /* 진술 · 반박 · 동요 · 쐐기 · 함구 */
    beat?: string
    line?: string
    text?: string
  }> | null
  reveals: Record<string, unknown> | null
  gained_clue: ServerClueCard | null
  curated: boolean
  sfx: string | null
}

export const runConfrontation = (
  sessionId: string,
  request: { a: string; b: string; question: string },
) =>
  post<WithState<ConfrontResult>>(
    `/session/${encodeURIComponent(sessionId)}/confront`,
    request,
  )

/* =========================================
   단서 겹쳐 보기 (수첩)

   ★행동을 쓰지 않는다 — 이미 가진 것을 다시 보는 일이다.
     어느 둘이 붙는지는 서버가 알려 주지 않는다. 아무 둘이나 겹쳐 볼 수 있고,
     안 붙으면 안 붙는다고만 답한다. 알아보는 것이 추리다.
========================================= */

export interface CombineResult {
  success: boolean
  /* 붙었을 때 */
  composite_id?: string
  name?: string
  surface?: string
  implies?: string | null
  weight?: string
  decisive?: boolean
  points?: number
  already_done?: boolean
  source?: string
  /* 안 붙었을 때 */
  message?: string
}

export const combineClues = (
  sessionId: string,
  request: { clue_a: string; clue_b: string },
) =>
  post<WithState<CombineResult>>(
    `/session/${encodeURIComponent(sessionId)}/combine`,
    request,
  )

/* =========================================
   라운드 넘기기 (S-20 → S-12)
========================================= */

export interface NextRoundResult {
  round: number
  given: ServerClueCard[]

  /* 라운드 단서 + 이벤트 단서를 한 자리에. 화면은 여기 하나만 그리면 된다 */
  new_clues: ServerClueCard[]

  /* 이벤트로 열린 비밀 문장 */
  opened_secrets: string[]

  round_start: string | null
  event: { name: string; text: string } | null
  event_result: unknown[]
  sfx: string | null
}

export const nextRound = (sessionId: string) =>
  post<WithState<NextRoundResult>>(
    `/session/${encodeURIComponent(sessionId)}/next_round`,
  )

/* =========================================
   사건수첩 (S-18)
========================================= */

/* =========================================
   그날 밤 시간표 (S-19)

   **아는 것만** 나온다 — 모두가 아는 공지와,
   만난 사람이 제 입으로 한 말.
   비어 있는 시각이 곧 아직 못 밝힌 자리다.
========================================= */

export interface TimelineRow {
  time: string
  slot: string
  cast_id: string | null
  who: string
  text: string
  source: '공지된 사실' | '본인 주장'
}

export const getTimeline = (sessionId: string) =>
  apiFetch<WithState<{ rows: TimelineRow[]; total: number; note: string }>>(
    `/session/${encodeURIComponent(sessionId)}/timeline`,
  )

export const getNotebook = (sessionId: string) =>
  apiFetch<{ clues: unknown[]; cards: ServerClueCard[] }>(
    `/session/${encodeURIComponent(sessionId)}/notebook`,
  )

/* =========================================
   범인 지목 (S-21) — 되돌릴 수 없다.
   여기서 처음으로 진상·재연이 열린다.
========================================= */

export interface AccuseResult {
  named: string
  /*
    ★판정은 점수가 아니라 성공/실패다 (팀원 제보 — "점수 6/10 말고 성공 여부로").
      범인과 흉기를 **모두** 맞혀야 ARREST. 이름만 맞히면 수법을 못 밝힌 것이라
      붙잡아 둘 수 없다 → FAIL.
  */
  /* 발표용은 판정을 내지 않는다 — 제출로 끝난다 */
  verdict?: 'ARREST' | 'FAIL' | 'SUBMITTED'
  hide_answer?: boolean
  said_weapon?: string | null
  success?: boolean
  culprit_correct?: boolean
  weapon_correct?: boolean
  /* 지목 뒤이므로 공개된다 */
  true_weapon?: string | null
  /* ARREST/FAIL 아래에 한 줄로 */
  verdict_line?: string
  correct: boolean
  points: number
  score?: number
  max: number
  grade: string
  secrets_opened: number
  /*
    한 판의 비밀 성적표 — 연 것과 못 연 것이 다 들어 있다.
    못 연 것의 본문도 함께 온다(지목이 끝난 뒤라 괜찮다).
    화면은 연 것만 바로 보이고, 못 연 것은 눌러야 펴지게 그린다.
  */
  /*
    ★못 맞히면 진상도 재연도 열리지 않는다 (팀 결정 — 가은).
      감췄다는 사실과 그 이유를 여기로 알려 준다. 화면은 진상·재연을
      건너뛰고 바로 엔딩으로 간다 — 빈 화면을 그리면 고장으로 보인다.
  */
  withheld?: {
    truth: boolean
    reenactment: boolean
    culprit_face: boolean
    reason: string
  } | null
  secrets_record?: {
    opened: number
    total: number
    items: Array<{
      cast_id: string
      cast_name: string
      opened: boolean
      text: string
      note?: string | null
      document?: unknown
    }>
  }
  /* 백엔드 버전에 따라 컷별 beats가 비어도 ending.truth_reveal 전문은 온다. */
  truth: {
    beats: Array<{
      no: number
      title: string
      caption?: string
      pages: Array<{ text: string; image: string }>
      duration_sec: number
    }>
    full_text: string
  }
  reenactment: {
    cuts: Array<{
      cut: number
      title: string
      text: string
      image: string
      duration_sec: number
    }>
    total_sec: number
    culprit: string
    culprit_name: string
    art_note: string
    no_skip: boolean
    sfx_spec: Record<string, unknown>
  }
  ending: {
    narration: string | null
    /* 붙잡힌 밤 / 빠져나간 밤 — 맞고 틀림에 따라 서버가 골라 준다 */
    branch: {
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
    truth_reveal: string
    reveal_order: Record<string, unknown>
    replay: Record<string, unknown>
  }
  sfx: string | null
  bgm: string | null
}

export const submitAccusation = (
  sessionId: string,
  request: { castId: string; weapon?: string; motive?: string },
) =>
  post<WithState<AccuseResult>>(
    `/session/${encodeURIComponent(sessionId)}/accuse`,
    {
      cast_id: request.castId,
      weapon: request.weapon ?? null,
      motive: request.motive ?? null,
    },
  )
