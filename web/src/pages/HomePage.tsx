import { useNavigate } from 'react-router-dom'

import HomeBackground from '../components/home/HomeBackground'
import HomeFooter from '../components/home/HomeFooter'
import HomeMenu from '../components/home/HomeMenu'
import Title from '../components/common/Title'

import { useGameStore } from '../store/gameStore'
import { useUiStore } from '../store/uiStore'

export default function HomePage() {
  const navigate = useNavigate()

  const startNewGame = useGameStore(
    (state) => state.startNewGame,
  )
  const openSettings = useUiStore((state) => state.openSettings)

  const handleStartCase = () => {
    startNewGame()
    navigate('/case-start')
  }

  const handleContinue = () => {
    navigate('/continue')
  }

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-game-bg">
      <HomeBackground />

      <Title
        text={'MURDER\nMYSTERY'}
        className="
          absolute
          left-[270px]
          top-[170px]
          w-[900px]
        
        "
        decorationClassName="
          left-[460px]
          top-[32px]
          h-[390px]
          w-[520px]
        "
      />

      <HomeMenu
        onStartCase={handleStartCase}
        onContinue={handleContinue}
        onSettings={openSettings}
      />


      <HomeFooter />
    </main>
  )
}
