import { useEffect } from 'react'

import { useUiStore } from '../../store/uiStore'

export default function Toast() {
  const toast = useUiStore((state) => state.toast)
  const clearToast = useUiStore((state) => state.clearToast)

  useEffect(() => {
    if (toast === null) return

    const timer = window.setTimeout(clearToast, 3000)
    return () => window.clearTimeout(timer)
  }, [clearToast, toast])

  if (toast === null) return null

  return (
    <div className="fixed bottom-8 left-1/2 z-50 -translate-x-1/2 border border-game-red-light/60 bg-black/90 px-8 py-4 font-game-korean text-lg text-game-ivory shadow-lg">
      {toast}
    </div>
  )
}