import { useNavigate } from 'react-router-dom'

import CaseStartActions from '../components/caseStart/CaseStartActions'
import CaseStartTitle from '../components/caseStart/CaseStartTitle'
import StoryInput from '../components/caseStart/StoryInput'

import { useGameStore } from '../store/gameStore'

export default function CaseStartPage() {
  const navigate = useNavigate()

  const sourceTitle = useGameStore(
    (state) => state.sourceTitle,
  )

  const setSourceTitle = useGameStore(
    (state) => state.setSourceTitle,
  )

  const setGameTitle = useGameStore(
    (state) => state.setGameTitle,
  )

  const handleGenerate = () => {
    const trimmedTitle =
      sourceTitle.trim()

    if (!trimmedTitle) {
      return
    }

    setSourceTitle(trimmedTitle)
    setGameTitle(trimmedTitle)
    navigate('/loading')
  }

  const handleOpenLibrary = () => {
    navigate('/library')
  }

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-game-bg">

      {/* 기존 CaseStart 배경 */}
      <img
        src="/assets/icons/title-background.svg"
        alt=""
        className="absolute inset-0 h-full w-full object-fill"
      />

      <CaseStartTitle />

      <StoryInput
        value={sourceTitle}
        onChange={setSourceTitle}
      />

      <CaseStartActions
        onOpenLibrary={handleOpenLibrary}
        onGenerate={handleGenerate}
        generateDisabled={
          sourceTitle.trim().length === 0
        }
      />

    </main>
  )
}
