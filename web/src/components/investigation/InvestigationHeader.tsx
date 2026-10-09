import { useNavigate } from 'react-router-dom'

import GameHeader2 from '../common/GameHeader2'
import { useGameStore } from '../../store/gameStore'

type InvestigationHeaderProps = {
  placeName: string
  placeId: string
}

export default function InvestigationHeader({
  placeName,
}: InvestigationHeaderProps) {
  const navigate = useNavigate()
  const roundOver = useGameStore((state) => state.roundOver)

  const leaveInvestigation = (destination: string) => {
    navigate(roundOver ? '/round-end' : destination)
  }

  return (
    <GameHeader2
      leftText="< 지도"
      title={placeName}
      rightText="사건수첩"
      onLeftClick={() => leaveInvestigation('/map')}
      onRightClick={() => leaveInvestigation('/notebook')}
    />
  )
}
