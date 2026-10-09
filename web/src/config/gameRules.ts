import type {
  Scenario,
} from '../types/scenario'
import { useGameStore } from '../store/gameStore'

export const getMaxRounds = (
  scenario: Scenario | null,
) =>
  scenario !== null && scenario.config.rounds > 0
    ? scenario.config.rounds
    : 0

export const getTurnsPerRound = (
  scenario: Scenario | null,
) =>
  scenario !== null && scenario.config.turns_per_round > 0
    ? scenario.config.turns_per_round
    : 0

export const getRoundEvent = (
  scenario: Scenario | null,
  round: number,
) => {
  const events = scenario?.events ?? []

  return (
    events.find((event) => event.round === round) ??
    null
  )
}

/*
  대질 해금 여부.

  전에는 events[].effect 에 '대질 해금'이 적혀 있는지 읽었다.
  그 문구는 시나리오마다 다르고, 실제로 잠금을 푸는 것은 엔진이다.

  이제는 서버가 state.confront 로 알려 준다 —
  열렸는지, 왜 잠겼는지, 몇 번 남았는지까지.
*/
export const isConfrontationUnlocked = () =>
  useGameStore.getState().confrontationUnlocked

export const useConfrontationUnlocked = () =>
  useGameStore((state) => state.confrontationUnlocked)

export const useConfrontationLockedReason = () =>
  useGameStore((state) => state.confrontationLockedReason)
