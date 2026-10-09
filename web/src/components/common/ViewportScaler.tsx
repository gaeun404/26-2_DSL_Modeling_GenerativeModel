import {
  useLayoutEffect,
  useState,
} from 'react'
import type { ReactNode } from 'react'

const DESIGN_WIDTH = 1440
const DESIGN_HEIGHT = 1024

type ViewportScalerProps = {
  children: ReactNode
}

const calculateScale = () =>
  Math.min(
    window.innerWidth / DESIGN_WIDTH,
    window.innerHeight / DESIGN_HEIGHT,
  )

export default function ViewportScaler({
  children,
}: ViewportScalerProps) {
  const [scale, setScale] = useState(
    calculateScale,
  )

  useLayoutEffect(() => {
    const updateScale = () => {
      setScale(calculateScale())
    }

    updateScale()
    window.addEventListener(
      'resize',
      updateScale,
    )
    window.visualViewport?.addEventListener(
      'resize',
      updateScale,
    )

    return () => {
      window.removeEventListener(
        'resize',
        updateScale,
      )
      window.visualViewport?.removeEventListener(
        'resize',
        updateScale,
      )
    }
  }, [])

  return (
    <div className="viewport-frame">
      <div
        className="viewport-canvas"
        style={{
          transform: `translate(-50%, -50%) scale(${scale})`,
        }}
      >
        {children}
      </div>
    </div>
  )
}
