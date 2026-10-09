import { BrowserRouter, Route, Routes } from 'react-router-dom'

import Bgm from './components/common/Bgm'
import ErrorBoundary from './components/common/ErrorBoundary'
import SessionGate from './components/common/SessionGate'
import Toast from './components/common/Toast'
import ViewportScaler from './components/common/ViewportScaler'
import SettingsModal from './components/settings/SettingsModal'
import AccusePage from './pages/AccusePage'
import CaseOpenPage from './pages/CaseOpenPage'
import CaseStartPage from './pages/CaseStartPage'
import ConfrontationPage from './pages/ConfrontationPage'
import CrimeScenePage from './pages/CrimeScenePage'
import EndingPage from './pages/EndingPage'
import HomePage from './pages/HomePage'
import InterrogatePage from './pages/InterrogatePage'
import LibraryPage from './pages/LibraryPage'
import LoadingPage from './pages/LoadingPage'
import MainPage from './pages/MainPage'
import MapPage from './pages/MapPage'
import NotebookPage from './pages/NotebookPage'
import PlaceInvestigationPage from './pages/PlaceInvestigationPage'
import RevealPage from './pages/RevealPage'
import ReenactmentPage from './pages/ReenactmentPage'
import RoundEndPage from './pages/RoundEndPage'
import StoryPage from './pages/StoryPage'
import SuspectAlibiPage from './pages/SuspectAlibiPage'
import SuspectDetailPage from './pages/SuspectDetailPage'
import SuspectsPage from './pages/SuspectsPage'
import VictimPage from './pages/VictimPage'

/* 판이 없어도 볼 수 있는 화면 */
const openRoutes = [
  ['/', HomePage],
  ['/case-start', CaseStartPage],
  ['/loading', LoadingPage],
  ['/library', LibraryPage],
  /* 백엔드 지목 데이터 없이 범행 재연 UI만 확인하는 개발용 주소 */
  ['/reenactment-preview', ReenactmentPage],
  ['/ending-preview', EndingPage],
] as const

/*
  판이 열려 있어야 하는 화면.

  새로고침으로 들어와도 SessionGate 가 서버에서 판을 되찾아 온다.
*/
const inGameRoutes = [
  ['/story', StoryPage],
  ['/crime-scene', CrimeScenePage],
  ['/victim', VictimPage],
  ['/suspects', SuspectsPage],
  ['/suspect/:suspectId', SuspectDetailPage],
  ['/suspect/:suspectId/alibi', SuspectAlibiPage],
  ['/main', MainPage],
  ['/map', MapPage],
  ['/place/:placeId/investigation', PlaceInvestigationPage],
  ['/interrogate/:placeId', InterrogatePage],
  ['/confrontation', ConfrontationPage],
  ['/notebook', NotebookPage],
  ['/accuse', AccusePage],
  ['/reveal', RevealPage],
  ['/reenactment', ReenactmentPage],
  ['/case-open', CaseOpenPage],
  ['/round-end', RoundEndPage],
  ['/ending', EndingPage],
] as const

export default function App() {
  return (
    <BrowserRouter>
      <ViewportScaler>
        {/*
          ★그물 둘을 여기서 친다 (2026-08-31, 제보 —
            "새로고침하면 오류 뜨면서 원래 창으로 못 되돌아감").

            ErrorBoundary — 화면 하나가 튀어도 빈 화면이 되지 않게.
            Toast        — 만들어 두고 **어디에도 안 걸어 둔 채**였다.
                           라운드 넘기기·조사·심문이 실패할 때 부르던
                           showToast 가 전부 소리 없이 사라지고 있었다.
        */}
        <ErrorBoundary>
          <Routes>
            {openRoutes.map(([path, Page]) => (
              <Route key={path} path={path} element={<Page />} />
            ))}

            {inGameRoutes.map(([path, Page]) => (
              <Route
                key={path}
                path={path}
                element={
                  <SessionGate>
                    <Page />
                  </SessionGate>
                }
              />
            ))}
          </Routes>
        </ErrorBoundary>
        <Bgm />
        <SettingsModal />
        <Toast />
      </ViewportScaler>
    </BrowserRouter>
  )
}
