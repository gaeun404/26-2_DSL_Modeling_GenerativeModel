import { useNavigate } from 'react-router-dom'

import VictimScreen from '../components/victim/VictimScreen'
import { useGameStore } from '../store/gameStore'
import { getVictim } from '../data/scenarioAdapter'

export default function VictimPage() {
  const navigate = useNavigate()

  /*
    TODO(API):
    현재는 화면 확인용 임시 데이터.

    백엔드 연동 후에는 시나리오 JSON에서
    피해자 정보를 받아 VictimScreen에 전달한다.

    관련 데이터:
    - ui.victim_card
    - death
  */
  const scenario = useGameStore((state) => state.scenario)
  const victim = getVictim(scenario)

  const handleContinue = () => {
    navigate('/suspects')
  }

  return (
    <VictimScreen
      victim={victim}
      onContinue={handleContinue}
    />
  )
}
