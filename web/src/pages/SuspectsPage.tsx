import { useNavigate } from 'react-router-dom'

import SuspectsScreen from '../components/suspects/SuspectsScreen'
import { getSuspects } from '../data/scenarioAdapter'
import { useGameStore } from '../store/gameStore'

export default function SuspectsPage() {
  const navigate = useNavigate()

  const scenario = useGameStore((state) => state.scenario)
  const suspects = getSuspects(scenario).map((suspect) => ({
    id: suspect.id,
    name: suspect.listName,
    image: suspect.image,
  }))

  const handleSuspectClick = (suspectId: string) => {
    navigate(`/suspect/${suspectId}`)
  }

  const handleStartInvestigation = () => {
    navigate('/main')
  }

  const handleBack = () => {
    navigate('/victim')
  }

  return (
    <SuspectsScreen
      suspects={suspects}
      onSuspectClick={handleSuspectClick}
      onStartInvestigation={handleStartInvestigation}
      onBack={handleBack}
    />
  )
}
