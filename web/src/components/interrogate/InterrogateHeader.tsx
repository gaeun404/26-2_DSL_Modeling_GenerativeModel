import {
  useLocation,
  useNavigate,
} from 'react-router-dom'

import GameHeader2 from '../common/GameHeader2'
import { useGameStore } from '../../store/gameStore'

type InterrogateHeaderProps = {
  /* 이 인물이 서 있는 방. 제 방이 없는 사람은 빈 문자열 */
  placeId: string
  title: string
}

export default function InterrogateHeader({
  placeId,
  title,
}: InterrogateHeaderProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string; castId?: string } | null)
  const fromNotebook = from?.from === 'notebook'
  const fromSuspects = from?.from === 'suspects'
  const castId = from?.castId ?? ''
  const roundOver = useGameStore((state) => state.roundOver)

  const leaveInterrogation = (destination: string) => {
    navigate(roundOver ? '/round-end' : destination)
  }

  return (
    <GameHeader2
      leftText="< 돌아가기"
      title={title}
      rightText="사건수첩"
      /*
        ★온 곳으로 돌려보낸다 (2026-08-29, 시연 제보).
          제보: "심문하다가 이전을 누르면 메인이 아니라 엉뚱한 장소로 가버린다."
          수첩·용의자 화면에서 들어와도 무조건 장소 조사 화면으로 보내고 있었다.
          노하람·임세준처럼 제 방이 없는 인물은 있지도 않은 방으로 갔다.
      */
      onLeftClick={() =>
        leaveInterrogation(
          fromNotebook
            ? '/notebook'
            : fromSuspects
              ? `/suspect/${castId}`
              : placeId
                ? `/place/${placeId}/investigation`
                : '/main',
        )
      }
      onRightClick={() => leaveInterrogation('/notebook')}
    />
  )
}
