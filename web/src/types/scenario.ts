export type ScenarioId = string
export type SuspectId = string
export type PlaceId = string
export type ClueId = string


/* TODO(MOCK) 임시로 숫자지정... */
export interface ScenarioConfig {
  suspects: number
  rounds: number
  attempts: number
  turns_per_round: number
}


/* ui.screens[] */

export interface ScenarioScreen {
  id: string
  name: string
  when: string

  /*임시로 문자열로 지정*/
  bgm: string

  sfx: string[]
  elements: unknown[]

  copy: Record<string, unknown>
}


/* ui.narration */

export interface NarrationImage {
  w: number
  h: number
  scene: string
  prompt_ko: string
  prompt_en: string
  /* 이미지 생성/서빙 단계에서 백엔드가 붙이는 실제 파일 주소 */
  url?: string
}


/* ui.narration.pages[] */

export interface NarrationPage {
  page: number
  beat: number

  text: string
  sentences: string[]

  chars: number
  over_limit: boolean

  mood: string
  focus: string

  image: NarrationImage
}



export interface NarrationLimits {
  max_chars_per_page: number
  max_sentences_per_page: number
  max_chars_per_sentence: number
}


export interface Narrator {
  voice_style: string
  tempo: string
  prompt_en: string
}


export interface Narration {
  page_count: number

  pages: NarrationPage[]

  limits: NarrationLimits

  video_pages: number[]

  incident_page: number

  full_text: string

  narrator: Narrator
}



export interface NarrationRender {
  shot: string 
  scene: string
  style: string
  spoiler_ban: string
  species_note: string
}


export interface InfoField {
  label: string
  value: string
}


/* ui.victim_card */

export interface VictimCard {
  /* 아래 값들은 세션용 view 응답에는 있지만 원본 명세에는 없을 수 있다. */
  name?: string
  role?: string
  bio?: string
  found_place?: string
  found_time?: string

  fields: InfoField[]

  bio_short: string


  portrait: string

  body_art: string
}


/* ui.suspect_cards[] */

export interface SuspectCard {
  id: SuspectId

  name: string

  /* 상세 화면의 소개글 */
  intro: string

  list_sub: string

  fields: InfoField[]

  alibi_quote: string

  alibi_label: string

  /* 카드에 붙는 얼굴 (실제 사진) */
  portrait: string

  /* 압박 판정에 따라 갈아 끼우는 표정 세 벌 */
  faces: {
    calm: string
    shaken: string
    broken: string
  }

  /* 장소에 서 있는 전신 */
  standing: string

  voice: Record<string, unknown>

  /* 이 인물의 테마곡 주소 */
  theme: string
}


/* death */

export interface Death {
  scene_description: string
  scene_inspection: string[]
}


/* clue_graph[] */

export type CluePresentationMode =
  | 'spoken'
  | 'place_panel'
  | 'illustrated'


export interface CluePresentation {
  mode: CluePresentationMode

  speaker?: string

  speaker_kind?:
    | 'cast'
    | 'npc'

  script?: string

  stage: string
}


export interface ClueRender {
  frame: string
  shot: string
  camera: string
  style: string
  spoiler_ban: string
  species_note?: string
}


export interface ClueGraphItem {
  clue_id: ClueId

  reveal_round: number

  decisive: boolean

  location: PlaceId

  medium: string

  presentation: CluePresentation

  render: ClueRender
}


/* ui.clue_cards[] */

export interface ClueCard {
  clue_id: ClueId

  name: string

  list_sub: string

  /* 수첩 목록용 작은 그림 */
  image: string

  /* 단서 팝업용 큰 그림 */
  full_image: string

  type: string

  acquired_place: string

  acquired_method: string

  description: string
}


/* ui.place_screens[] == */

export interface PlaceSearchAction {
  id?: string

  /* 서버 /search 에 그대로 넘기는 번호 */
  index: number

  label: string

  /*
    result_lines · finds 는 지목 전까지 비어 있다.
    무엇이 나오는지는 실제로 조사한 뒤 서버가 알려 준다.
  */
  result_lines: string[]

  highlight_last: boolean

  finds: ClueId | null

  button: string

  sfx: string[]
}


export interface PlaceRound {
  actions: PlaceSearchAction[]

  layer_note: string
}


export interface PlaceScreen {
  place_id: PlaceId

  rounds: Record<
    string,
    PlaceRound
  >
  name?: string
  title?: string
  background_image?: string
  map_thumb?: string

  /* 이 장소에 서 있는 인물. 없으면 조사만 하는 방이다 */
  cast_id?: SuspectId | null
  character_name?: string
  character_image?: string
  talk_label?: string
  talk_note?: string

  /* 이 장소의 음악 주소 */
  bgm?: string
}


/* MAP  */

export interface MapPlacePosition {
  row: number
  col: number
}


/* scenario.map.places[] */
export interface MapPlace {
  id: PlaceId

  name: string

  pos: MapPlacePosition

  unlock_round: number

  desc?: string

  /* 지도 칸에 깔리는 작은 그림 */
  thumb?: string

  owner?: SuspectId | null
}


export interface ScenarioMap {

  max_move_per_slot: number
  places: MapPlace[]
}


/* events[]  */

export interface ScenarioEvent {
  /* 이벤트가 발생하는 라운드 */
  round: number

  /* 이벤트 이름 */
  name: string

  /* 이벤트 종류  */
  kind: string

  /* 플레이어에게 보여줄 문구 */
  text: string

  /* 실제 게임 상태에 적용할 효과.
    대질 해금
    새 단서 공개
    새 증언 공개  */
  effect: string
}


/* accuse */

export interface AccuseChoices {
  culprit: SuspectId[]

  weapon: string[]
}


export interface AccuseScoring {
  culprit_correct: number

  wrong_accusation_penalty: number

  secret_revealed_each: number

  max: number
}


/* ending */

export interface EndingGrade {
  min: number

  name: string

  text: string
}


export interface Ending {
  truth_reveal: string

  grades: EndingGrade[]
}


/*
  ui.reveal_sequence — 지목 뒤 채워진다.

  진상과 재연은 한 줄기다. 박마다 그림 한 장(재연 컷)과 글 한 덩이가 같이 온다.
  caption 은 그 컷의 이름 — 결심 · 접근 · 범행 …
*/
export interface RevealBeat {
  no: number
  title: string
  caption?: string
  pages: Array<{ text: string; image: string }>
  duration_sec: number
}

export interface RevealSequence {
  beats: RevealBeat[]

  full_text: string
}


/* ui.murder_reenactment — 지목 전에는 비어 있다 */

export interface ReenactmentCut {
  cut: number
  title: string
  text: string
  image: string
  duration_sec: number
}

export interface MurderReenactment {
  cuts: ReenactmentCut[]

  total_sec: number

  culprit: SuspectId

  culprit_name: string

  sfx_spec: unknown

  art_note: string

  no_skip: boolean
}


/* ui  */

export interface ScenarioUI {
  screens: ScenarioScreen[]

  /* 라운드 Main 화면의 배경 이미지 */
  main_background_image?: string

  narration: Narration

  victim_card: VictimCard

  suspect_cards: SuspectCard[]

  clue_cards: ClueCard[]

  place_screens: PlaceScreen[]

  reveal_sequence: RevealSequence

  murder_reenactment:
    MurderReenactment

  /* 화면별 음악·효과음 주소 모음 */
  audio: {
    cues: Record<string, string | null>
    events: Record<string, string | null>
    ui: Record<string, string | null>
  }

  hud?: Record<string, unknown>
}


/* 최종 Scenario */

export interface Scenario {
  /* 백엔드 버전에 따라 scenarioId / scenario_id / id 중 하나가 올 수 있다. */
  scenarioId?: ScenarioId
  scenario_id?: ScenarioId
  id?: ScenarioId

  title?: string
  origin?: string
  era?: string
  difficulty?: number
  cover_image?: string

  config: ScenarioConfig

  ui: ScenarioUI

  death: Death

  clue_graph: ClueGraphItem[]

  /* 지도 정보 */
  map: ScenarioMap

  /* 라운드별 이벤트 */
  events: ScenarioEvent[]

  choices: AccuseChoices

  scoring: AccuseScoring

  ending: Ending

  hud:
    Record<string, unknown>

  interrogation:
    Record<string, unknown>

  search:
    Record<string, unknown>

  bgm:
    Record<string, unknown>

  voice:
    Record<string, unknown>

  phases: unknown[]

  toasts:
    Record<string, unknown>
}
