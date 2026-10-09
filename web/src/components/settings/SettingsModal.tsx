import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

import { getRules, type GameRules } from '../../api/scenarioApi'
import { useUiStore } from '../../store/uiStore'
import { useGameStore } from '../../store/gameStore'
import { getTurnsPerRound } from '../../config/gameRules'

type Settings = {
  subtitleSize: '작게' | '보통' | '크게'
  musicVolume: number
  effectVolume: number
  autoSpeed: '느리게' | '보통' | '빠르게'
}

const defaultSettings: Settings = {
  subtitleSize: '보통',
  musicVolume: 70,
  effectVolume: 70,
  autoSpeed: '보통',
}

export default function SettingsModal() {
  const navigate = useNavigate()
  const isOpen = useUiStore((state) => state.settingsOpen)
  const close = useUiStore((state) => state.closeSettings)
  const scenario = useGameStore((state) => state.scenario)
  const sessionId = useGameStore((state) => state.sessionId)
  const turnsPerRound = getTurnsPerRound(scenario)
  const [showRules, setShowRules] = useState(false)

  /*
    ★규칙은 **서버가 준다** (팀원 제보 — "게임룰 설명이 있으면 좋겠다").

      화면이 지어 쓰면 어긋난다. 실제로 여기 적혀 있던 다섯 줄 중 둘이 틀렸다 —
      「행동을 모두 사용하면 다음 라운드가 시작됩니다」(아니다, 눌러야 넘어간다),
      대질이 행동을 쓴다는 말이 없었다. 서버는 그 판의 라운드 수·예산으로
      채워서 일곱 항목을 준다. 못 받으면 아래 기본 문구로 물러선다.
  */
  const [rules, setRules] = useState<GameRules | null>(null)
  const [settings, setSettings] = useState<Settings>(() => {
    const saved = localStorage.getItem('game-settings')
    return saved
      ? (JSON.parse(saved) as Settings)
      : defaultSettings
  })

  const handleClose = () => {
    setShowRules(false)
    close()
  }

  useEffect(() => {
    if (!showRules || rules !== null || sessionId === null) {
      return
    }

    let alive = true

    getRules(sessionId)
      .then((received) => {
        if (alive) setRules(received)
      })
      .catch(() => {
        /* 못 받으면 아래 기본 문구가 나간다 */
      })

    return () => {
      alive = false
    }
  }, [showRules, rules, sessionId])

  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowRules(false)
        close()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [close, isOpen])

  if (!isOpen) return null

  const update = <K extends keyof Settings>(
    key: K,
    value: Settings[K],
  ) => setSettings((current) => ({ ...current, [key]: value }))

  const save = () => {
    localStorage.setItem('game-settings', JSON.stringify(settings))
    handleClose()
  }

  const openOverview = () => {
    handleClose()
    navigate('/notebook')
  }

  return (
    <div className="absolute inset-0 z-[300] bg-black/75 font-game-korean text-game-ivory">
      <button
        type="button"
        aria-label="설정 닫기"
        onClick={handleClose}
        className="absolute inset-0 cursor-default border-0 bg-transparent"
      />

      <section className="absolute left-1/2 top-1/2 h-[720px] w-[900px] -translate-x-1/2 -translate-y-1/2 border border-game-parchment/45 bg-[#0d0c0b] px-[70px] py-[52px] shadow-[0_20px_80px_rgba(0,0,0,0.75)]">
        <div className="flex items-center justify-between border-b border-game-parchment/30 pb-[24px]">
          <h2 className="m-0 text-[38px] tracking-[0.12em]">
            {showRules ? rules?.title ?? '게임 방법' : '설정'}
          </h2>
          <button
            type="button"
            onClick={handleClose}
            className="cursor-pointer border-0 bg-transparent text-[24px] text-game-ivory/70"
          >
            닫기
          </button>
        </div>

        {showRules ? (
          <div className="max-h-[520px] overflow-y-auto pt-[30px] pr-[10px]">
            {rules !== null ? (
              <dl className="m-0 flex flex-col gap-[20px]">
                {rules.items.map((item) => (
                  <div key={item.h}>
                    <dt className="text-[19px] tracking-[0.1em] text-game-parchment">
                      {item.h}
                    </dt>
                    <dd className="m-0 mt-[6px] text-[19px] leading-[1.7] text-game-ivory/80">
                      {item.t}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <ol className="m-0 space-y-[20px] pl-[28px] text-[21px] leading-[1.65] text-game-ivory/85">
                <li>
                  {turnsPerRound > 0
                    ? `각 라운드에는 ${turnsPerRound}번의 행동이 주어집니다.`
                    : '각 라운드에는 사건마다 정해진 수의 행동이 주어집니다.'}
                </li>
                <li>조사하거나 질문하면 행동을 한 번 사용합니다.</li>
                <li>수첩의 단서를 함께 제시하면 답변이 달라집니다.</li>
                <li>2라운드부터 두 용의자를 맞대 놓을 수 있습니다 (행동 1).</li>
                <li>범인과 흉기를 모두 맞히면 추리에 성공합니다.</li>
              </ol>
            )}
            <button
              type="button"
              onClick={() => setShowRules(false)}
              className="absolute bottom-[55px] left-1/2 h-[75px] w-[230px] -translate-x-1/2 cursor-pointer border border-game-parchment/45 bg-black/40 text-[22px] tracking-[0.1em]"
            >
              설정으로 돌아가기
            </button>
          </div>
        ) : (
          <div className="pt-[25px]">
            <SettingRow label="자막 크기">
              <select
                value={settings.subtitleSize}
                onChange={(event) =>
                  update('subtitleSize', event.target.value as Settings['subtitleSize'])
                }
                className="h-[48px] w-[170px] border border-game-parchment/35 bg-black px-[18px] text-[20px] text-game-ivory"
              >
                <option>작게</option>
                <option>보통</option>
                <option>크게</option>
              </select>
            </SettingRow>
            <SettingRow label="음악 음량">
              <VolumeControl
                value={settings.musicVolume}
                onChange={(value) => update('musicVolume', value)}
              />
            </SettingRow>
            <SettingRow label="효과음 음량">
              <VolumeControl
                value={settings.effectVolume}
                onChange={(value) => update('effectVolume', value)}
              />
            </SettingRow>
            <SettingRow label="자동 진행 속도">
              <select
                value={settings.autoSpeed}
                onChange={(event) =>
                  update('autoSpeed', event.target.value as Settings['autoSpeed'])
                }
                className="h-[48px] w-[170px] border border-game-parchment/35 bg-black px-[18px] text-[20px] text-game-ivory"
              >
                <option>느리게</option>
                <option>보통</option>
                <option>빠르게</option>
              </select>
            </SettingRow>

            <div className="mt-[30px] grid grid-cols-3 gap-[18px]">
              <SettingsButton label="규칙 다시 보기" onClick={() => setShowRules(true)} />
              <SettingsButton label="사건 개요" onClick={openOverview} />
              <SettingsButton label="저장하고 닫기" onClick={save} />
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

function SettingRow({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <div className="flex h-[88px] items-center justify-between border-b border-white/10 text-[24px] tracking-[0.08em]">
      <span>{label}</span>
      {children}
    </div>
  )
}

function VolumeControl({
  value,
  onChange,
}: {
  value: number
  onChange: (value: number) => void
}) {
  return (
    <div className="flex items-center gap-[18px]">
      <input
        type="range"
        min="0"
        max="100"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-[240px] accent-[#806c45]"
      />
      <span className="w-[45px] text-right text-[20px] text-game-parchment">
        {value}
      </span>
    </div>
  )
}

function SettingsButton({
  label,
  onClick,
}: {
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="h-[78px] cursor-pointer border border-game-parchment/40 bg-black/35 text-[20px] tracking-[0.07em] text-game-ivory hover:bg-game-gold/20"
    >
      {label}
    </button>
  )
}
