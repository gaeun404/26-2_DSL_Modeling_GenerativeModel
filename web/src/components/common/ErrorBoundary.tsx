import {
  Component,
  type ErrorInfo,
  type ReactNode,
} from 'react'

/*
  화면 하나가 튀어도 판 전체를 잃지 않게 한다.

  ★왜 (2026-08-31, 제보 — "오류 뜨면서 원래 창으로 못 되돌아감").
    지금까지 이 그물이 없었다. 어느 화면에서든 예외가 하나 튀면 React 가
    트리를 통째로 내려 **빈 화면**이 되고, 되돌아갈 버튼조차 남지 않았다.

    판 번호는 탭(sessionStorage)에 있으므로 **새로고침이 실제로 복구 수단**이다 —
    SessionGate 가 서버에서 판을 다시 받아 온다. 그러니 여기서는 길을 알려 주면 된다.

  ※ 진짜 원인은 콘솔에 남긴다. 화면에 스택을 뿌리지는 않는다 —
    플레이어에게는 읽을 것이 아니라 나갈 길이 필요하다.
*/

type Props = { children: ReactNode }
type State = { failed: boolean; message: string }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false, message: '' }

  static getDerivedStateFromError(error: unknown): State {
    return {
      failed: true,
      message: error instanceof Error ? error.message : String(error),
    }
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    console.error('[화면이 멈췄다]', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) {
      return this.props.children
    }

    return (
      <main className="flex h-[1024px] w-[1440px] flex-col items-center justify-center gap-[14px] bg-game-bg font-game-korean text-game-ivory">
        <p className="m-0 text-[26px] tracking-[0.1em] text-game-ivory/70">
          화면을 그리다 멈췄습니다.
        </p>
        <p className="m-0 mb-[26px] text-[17px] leading-[1.8] tracking-[0.05em] text-game-ivory/40">
          조사하던 판은 서버에 남아 있습니다 — 다시 그리면 이어서 볼 수 있습니다.
        </p>

        <div className="flex gap-[16px]">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="cursor-pointer border border-game-red-light/60 bg-game-red/25 px-[34px] py-[14px] font-game-korean text-[20px] tracking-[0.08em] text-game-ivory transition-colors hover:bg-game-red/40"
          >
            다시 그리기
          </button>
          <button
            type="button"
            onClick={() => window.location.assign('/main')}
            className="cursor-pointer border border-[#55452c] bg-transparent px-[34px] py-[14px] font-game-korean text-[20px] tracking-[0.08em] text-game-ivory/60 transition-colors hover:text-game-ivory"
          >
            라운드 화면으로
          </button>
        </div>

        {this.state.message !== '' && (
          <p className="mt-[30px] max-w-[820px] px-[20px] text-center font-mono text-[12px] leading-[1.6] tracking-[0.02em] text-game-ivory/20">
            {this.state.message}
          </p>
        )}
      </main>
    )
  }
}
