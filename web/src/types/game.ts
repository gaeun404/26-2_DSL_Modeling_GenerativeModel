import type {ClueId,PlaceId,ScenarioId, SuspectId,} from './scenario.ts'


/* 게임 전체 상태 */

export type GameStatus =
  | 'idle'
  | 'creating'
  | 'playing'
  | 'finished'

export type ActionState = Record<string, unknown>


/* 사건수첩 메모 */

/* TODO(SPEC): 변수명 확인 */
export interface GameNotes {
  general: string
  suspectNotes: Record<SuspectId, string>
  clueNotes: Record<ClueId, string>
}


/* 게임 진행 상태 */

export interface GameState {
  status: GameStatus

  /* 현재 플레이 중인 Scenario ID.*/
  scenarioId: ScenarioId | null

  /* 현재 라운드 */
  currentRound: number

  /* 현재 남은 지목 기회 */
  remainingAttempts: number

  /* 현재 라운드에서 남은 질문 수 */
  remainingTurns: number

  /* 현재 선택된 용의자  */
  selectedSuspectId: SuspectId | null

  /* 현재 선택된 장소 */
  selectedPlaceId: PlaceId | null

  /* 플레이어가 발견한 단서 ID 목록 */
  discoveredClueIds: ClueId[]

  /* 플레이어가 실제로 만난 용의자 ID 목록 */
  metSuspectIds: SuspectId[]

  /* 사건수첩 메모 */
  notes: GameNotes
}