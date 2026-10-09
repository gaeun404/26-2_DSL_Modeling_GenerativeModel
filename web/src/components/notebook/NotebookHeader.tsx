import { useNavigate } from 'react-router-dom'

import GameHeader2 from '../common/GameHeader2'
import { useUiStore } from '../../store/uiStore'

export default function NotebookHeader() {
  const navigate = useNavigate()
  const openSettings = useUiStore((state) => state.openSettings)

  return (
    <GameHeader2
      leftText="< 돌아가기"
      title="사건수첩"
      rightText="설정"
      onLeftClick={() =>
        navigate('/main')
      }
      onRightClick={openSettings}
    />
  )
}
