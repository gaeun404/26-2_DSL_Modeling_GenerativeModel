import {
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import {
  Navigate,
  useLocation,
  useNavigate,
} from 'react-router-dom'

import {
  useGameStore,
  type RestoreResult,
} from '../../store/gameStore'

/*
  판이 열려 있어야만 볼 수 있는 화면들을 감싼다.

  새로고침하면 스토어는 비지만 **판은 서버에 남아 있다.**
  탭이 들고 있던 번호로 되찾아 온다.

  ★못 되찾았을 때를 두 갈래로 나눈다 (2026-08-31, 제보 —
    "새로고침하면 오류 뜨면서 원래 창으로 못 되돌아감").

    배포된 백엔드는 한동안 아무도 안 부르면 잠든다. 깨어나는 데 30초쯤
    걸린다(실측 31.4초). 그동안 이 화면은 그냥 「다시 펴는 중…」만 띄우고
    있었고, 요청이 한 번 엎어지면 판 번호까지 버린 채 기록실로 튕겨 냈다.

      판이 정말 없다(404)  → 기록실로. 되찾을 것이 없으니 맞다.
      서버에 못 닿았다      → **번호를 쥔 채** 여기 머물며 다시 시도한다.

    기다리는 동안에도 무슨 일이 일어나는지 말해 준다 — 6초가 지나면
    "서버를 깨우는 중"이라고 적는다. 아무 말 없는 30초가 고장처럼 보인다.
*/

const WAKING_AFTER_MS = 6000

export default function SessionGate({
  children,
}: {
  children: ReactNode
}) {
  const location = useLocation()
  const navigate = useNavigate()
  const scenario = useGameStore((state) => state.scenario)
  const restoreSession = useGameStore(
    (state) => state.restoreSession,
  )

  const [phase, setPhase] = useState<RestoreResult | 'restoring'>('restoring')

  /* 다시 시도를 누를 때마다 아래 effect 를 다시 돌린다 */
  const [attempt, setAttempt] = useState(0)

  /* 오래 걸리는 중인가 — 잠든 서버를 깨우는 참이라고 알려 주는 자리 */
  const [waking, setWaking] = useState(false)

  useEffect(() => {
    /*
      판이 이미 있으면 되찾을 것이 없다.
      아래 render 가 곧장 children 을 내보내므로 여기서 할 일도 없다.
    */
    if (scenario !== null) {
      return
    }

    let cancelled = false

    const wakingTimer = window.setTimeout(() => {
      if (!cancelled) setWaking(true)
    }, WAKING_AFTER_MS)

    restoreSession()
      .then((result) => {
        if (!cancelled) setPhase(result)
      })
      .catch(() => {
        /* 여기까지 오는 일은 없어야 하지만, 와도 판 번호는 지키는 쪽으로 */
        if (!cancelled) setPhase('unreachable')
      })

    return () => {
      cancelled = true
      window.clearTimeout(wakingTimer)
    }
  }, [scenario, restoreSession, attempt])

  /* 되돌리는 것은 누를 때 한다 — effect 안에서 상태를 되돌리면 한 번 더 그린다 */
  const retry = useCallback(() => {
    setPhase('restoring')
    setWaking(false)
    setAttempt((n) => n + 1)
  }, [])

  if (scenario !== null) {
    return <>{children}</>
  }

  if (phase === 'restoring') {
    return (
      <main className="flex h-[1024px] w-[1440px] flex-col items-center justify-center gap-[18px] bg-game-bg font-game-korean text-game-ivory">
        <p className="m-0 text-[26px] tracking-[0.1em] text-game-ivory/60">
          사건 기록을 다시 펴는 중…
        </p>
        {waking && (
          <p className="m-0 text-[17px] tracking-[0.06em] text-game-ivory/35">
            서버를 깨우는 중입니다 — 1분까지 걸릴 수 있습니다.
          </p>
        )}
      </main>
    )
  }

  /* 판이 정말 없다 — 되찾을 것이 없으니 기록실로 */
  if (phase === 'gone') {
    return <Navigate to="/library" replace state={{ from: location }} />
  }

  /*
    서버에 못 닿았다. **판 번호는 아직 들고 있다** —
    한 번 더 눌러 보면 되찾을 수 있다.
  */
  if (phase === 'unreachable') {
    return (
      <main className="flex h-[1024px] w-[1440px] flex-col items-center justify-center gap-[14px] bg-game-bg font-game-korean text-game-ivory">
        <p className="m-0 text-[26px] tracking-[0.1em] text-game-ivory/70">
          서버에 닿지 못했습니다.
        </p>
        <p className="m-0 mb-[26px] text-[17px] leading-[1.8] tracking-[0.05em] text-game-ivory/40">
          조사하던 판은 아직 남아 있을 수 있습니다. 잠든 서버가 깨어나는 데
          시간이 걸리기도 합니다 — 잠시 뒤 다시 시도해 보세요.
        </p>
        <div className="flex gap-[16px]">
          <button
            type="button"
            onClick={retry}
            className="cursor-pointer border border-game-red-light/60 bg-game-red/25 px-[34px] py-[14px] font-game-korean text-[20px] tracking-[0.08em] text-game-ivory transition-colors hover:bg-game-red/40"
          >
            다시 시도
          </button>
          <button
            type="button"
            onClick={() => navigate('/library')}
            className="cursor-pointer border border-[#55452c] bg-transparent px-[34px] py-[14px] font-game-korean text-[20px] tracking-[0.08em] text-game-ivory/60 transition-colors hover:text-game-ivory"
          >
            사건 기록실로
          </button>
        </div>
      </main>
    )
  }

  return null
}
