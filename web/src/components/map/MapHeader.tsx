import { useNavigate } from 'react-router-dom'

import GameHeader2 from '../common/GameHeader2'

export default function MapHeader() {
  const navigate = useNavigate()

  return (
    <GameHeader2
      leftText="< 돌아가기"
      title="지도"
      rightText="사건수첩"
      onLeftClick={() => navigate('/main')}
      onRightClick={() => navigate('/notebook')}
    />
  )
}
