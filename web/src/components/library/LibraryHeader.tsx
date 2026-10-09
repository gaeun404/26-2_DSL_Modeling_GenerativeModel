import { useNavigate } from 'react-router-dom'

import GameHeader2 from '../common/GameHeader2'

export default function LibraryHeader() {
  const navigate = useNavigate()

  return (
    <GameHeader2
      leftText="< 돌아가기"
      title="이미 준비된 사건"
      rightText=""
      onLeftClick={() =>
        navigate('/case-start')
      }
      onRightClick={() => {}}
    />
  )
}