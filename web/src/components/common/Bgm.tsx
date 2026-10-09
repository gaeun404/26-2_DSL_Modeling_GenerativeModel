import {
  useEffect,
  useRef,
  useState,
} from 'react'
import { useLocation } from 'react-router-dom'

import { getAudioBook } from '../../api/scenarioApi'
import { useGameStore } from '../../store/gameStore'

/*
  소리.

  ■ **어느 화면에 어느 곡인지는 시나리오가 정한다.**
    `91_dsl_demo.json` 의 `ui.screens[].bgm` 에 스물한 화면치가 적혀 있다 —
    타이틀은 ui.title, 현장은 place_cues.PC.post_murder, 심문은
    character_themes.{cast_id}, 대질은 cues.climax … 이 파일은 그 표를
    주소로 옮겨 놓은 것뿐이다. 임의로 고르지 않는다.

  ■ 전에는 마흔세 곡 중 열여덟 곡만 울었다 (2026-08-29, 4차 제보).
    조사·지도·장소가 전부 cues.investigation 한 곡이었고, 장소 곡 열두 개와
    인물 테마 다섯 개는 아예 부를 길이 없었다(소리 목록에 없었다).
    이제 /audio 가 places·characters 까지 준다.

      장소 조사   place_cues.{장소}_post_murder   ← 사건은 이미 났다
      심문        character_themes.{인물}
      용의자 상세  character_themes.{인물}          (카드를 고르면 그 사람 테마)
      현장        place_cues.PC_post_murder
      피해자      cues.discovery
      대질        cues.climax

  ■ 브라우저는 사람이 한 번 누르기 전까지 소리를 못 내게 막는다.
    그래서 첫 클릭·키 입력을 기다렸다가 시작한다. 막히면 조용히 넘어간다 —
    음악이 안 나온다고 판이 멈추면 안 된다.

  ■ 곡이 바뀔 때는 잘라 붙이지 않고 1.6초에 걸쳐 넘긴다.
    행동마다 튀는 효과음은 여기가 아니라 lib/sfx.ts 가 맡는다.
*/

type AudioBook = {
  cues: Record<string, string | null>
  ui: Record<string, string | null>
  places: Record<string, string | null>
  characters: Record<string, string | null>
}

/* 주소에서 장소·인물 id를 집어낸다 */
const idIn = (pathname: string, head: string) => {
  const match = new RegExp(`^/${head}/([^/]+)`).exec(pathname)

  return match ? decodeURIComponent(match[1]) : null
}

/*
  주소 → 그 화면의 음악.

  시나리오 ui.screens[].bgm 을 그대로 옮긴 표다.
*/
const cueFor = (
  pathname: string,
  audio: AudioBook,
): string | null => {
  /*
    통합 중인 백엔드는 places · characters 를 아직 보내지 않을 수 있다.
    음원 표 하나가 빠졌다고 화면 전체가 죽어서는 안 된다 — 없는 표는 빈 표로
    보고 공통 cue 로 내려간다.
  */
  const cues = audio.cues ?? {}
  const ui = audio.ui ?? {}
  const places = audio.places ?? {}
  const characters = audio.characters ?? {}

  /* 장소 조사 — 장소마다 제 곡이 있다. 사건은 이미 났으니 post_murder */
  const placeId = idIn(pathname, 'place')

  if (placeId !== null) {
    return places[`${placeId}_post_murder`] ?? cues.investigation ?? null
  }

  /* 심문 — 그 사람의 테마. (라우트 이름이 placeId 지만 실제로는 cast_id 다) */
  const castId = idIn(pathname, 'interrogate')

  if (castId !== null) {
    return characters[castId] ?? cues.interrogation ?? null
  }

  /* 용의자 상세 — 카드를 고르면 그 인물 테마로 갈린다 */
  const suspectId = idIn(pathname, 'suspect')

  if (suspectId !== null) {
    return characters[suspectId] ?? cues.intro ?? null
  }

  if (pathname.startsWith('/loading')) return ui.loading ?? cues.intro ?? null
  if (pathname.startsWith('/notebook')) return ui.notebook ?? cues.investigation ?? null
  if (pathname.startsWith('/accuse')) return ui.accuse ?? cues.climax ?? null
  if (pathname.startsWith('/confrontation')) return cues.climax ?? null
  if (pathname.startsWith('/reveal')) return cues.reveal ?? null
  if (pathname.startsWith('/reenactment')) return cues.reveal ?? null
  if (pathname.startsWith('/ending')) return cues.ending ?? null

  /* 현장 — 주검이 나온 세미나실 */
  if (pathname.startsWith('/crime-scene')) {
    return places.PC_post_murder ?? cues.discovery ?? null
  }

  /* 피해자 카드 · 밤이 끝나는 자리 — 찾은 것을 헤아리는 시간 */
  if (
    pathname.startsWith('/victim') ||
    pathname.startsWith('/round-end')
  ) {
    return cues.discovery ?? cues.investigation ?? null
  }

  /* 라운드 화면 · 지도 */
  if (
    pathname.startsWith('/main') ||
    pathname.startsWith('/map')
  ) {
    return cues.investigation ?? null
  }

  /* 사건 공개 · 오프닝 · 용의자 소개 */
  if (
    pathname.startsWith('/case-open') ||
    pathname.startsWith('/story') ||
    pathname.startsWith('/suspects')
  ) {
    return cues.intro ?? null
  }

  /* 세계관 입력 · 사건 기록실 */
  if (
    pathname.startsWith('/case-start') ||
    pathname.startsWith('/library')
  ) {
    return ui.world_input ?? ui.title ?? null
  }

  /* 첫 화면 */
  return ui.title ?? null
}

const FADE_MS = 1600
const VOLUME = 0.45

export default function Bgm() {
  const { pathname } = useLocation()
  const sessionAudio = useGameStore((state) => state.audio)
  const muted = useGameStore((state) => state.muted)
  const toggleMuted = useGameStore((state) => state.toggleMuted)

  const elementRef = useRef<HTMLAudioElement | null>(null)
  const fadeRef = useRef<number | null>(null)
  const currentRef = useRef<string | null>(null)

  /*
    지금 울고 있는 것 전부.

    ★왜 목록으로 드느냐 — 곡이 연달아 바뀔 때 하나가 영영 안 꺼지는 일이 있었다.
      A→B 로 넘기는 도중(1.6초)에 B→C 가 시작되면 그 페이드가 끊긴다. 그때
      A 를 가리키던 손이 사라져서, A 는 아무도 모르게 계속 돌았다.
      목록을 들고 있다가, 지금 것이 아니면 다 끈다.
  */
  const playingRef = useRef<HTMLAudioElement[]>([])

  /* 판을 열기 전에도 쓸 소리 목록 */
  const [bundleAudio, setBundleAudio] = useState<AudioBook | null>(null)

  /* 사람이 한 번 누르기 전에는 소리를 낼 수 없다 */
  const [unlocked, setUnlocked] = useState(false)

  const audio = sessionAudio ?? bundleAudio

  useEffect(() => {
    if (sessionAudio || bundleAudio) {
      return
    }

    let alive = true

    getAudioBook()
      .then((book) => {
        if (alive) setBundleAudio(book)
      })
      .catch(() => {
        /* 못 받아도 판은 돌아간다 — 음악만 없다 */
      })

    return () => {
      alive = false
    }
  }, [sessionAudio, bundleAudio])

  useEffect(() => {
    if (unlocked) {
      return
    }

    const unlock = () => setUnlocked(true)

    window.addEventListener('pointerdown', unlock, { once: true })
    window.addEventListener('keydown', unlock, { once: true })

    return () => {
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
    }
  }, [unlocked])

  /* 국면이 바뀌면 곡을 넘긴다 */
  useEffect(() => {
    if (!audio || !unlocked) {
      return
    }

    const next = cueFor(pathname, audio)

    if (next === currentRef.current) {
      return
    }

    currentRef.current = next

    if (fadeRef.current !== null) {
      window.clearInterval(fadeRef.current)
      fadeRef.current = null
    }

    const previous = elementRef.current

    /* 지난 페이드에서 남겨진 것이 있으면 여기서 끈다 */
    playingRef.current
      .filter((item) => item !== previous)
      .forEach((item) => item.pause())
    playingRef.current = previous ? [previous] : []

    if (next === null) {
      previous?.pause()
      playingRef.current = []
      elementRef.current = null
      return
    }

    const element = new Audio(next)
    element.loop = true
    element.volume = 0
    element.muted = muted
    elementRef.current = element
    playingRef.current = [...playingRef.current, element]

    element.play().catch(() => {
      /* 브라우저가 막으면 조용히 넘어간다 */
    })

    /* 1.6초에 걸쳐 이전 곡을 내리고 새 곡을 올린다 */
    const started = Date.now()
    fadeRef.current = window.setInterval(() => {
      const ratio = Math.min(1, (Date.now() - started) / FADE_MS)

      element.volume = VOLUME * ratio

      if (previous) {
        previous.volume = VOLUME * (1 - ratio)
      }

      if (ratio >= 1) {
        previous?.pause()
        playingRef.current = [element]

        if (fadeRef.current !== null) {
          window.clearInterval(fadeRef.current)
          fadeRef.current = null
        }
      }
    }, 60)
  }, [pathname, audio, unlocked, muted])

  /* 음소거 토글은 울고 있는 것 전부에 바로 먹인다 */
  useEffect(() => {
    playingRef.current.forEach((item) => {
      item.muted = muted
    })
  }, [muted])

  /* 화면을 떠날 때 정리 */
  useEffect(
    () => () => {
      if (fadeRef.current !== null) {
        window.clearInterval(fadeRef.current)
      }
      playingRef.current.forEach((item) => item.pause())
      playingRef.current = []
    },
    [],
  )

  return (
    <button
      type="button"
      onClick={toggleMuted}
      aria-label={muted ? '소리 켜기' : '소리 끄기'}
      title={muted ? '소리 켜기' : '소리 끄기'}
      /*
        이모지는 글꼴이 없는 환경에서 두부(□)로 뜬다.
        글자와 기호로 그린다 — 어디서나 같게 보인다.
      */
      className="absolute right-[16px] top-[14px] z-[200] flex h-[34px] cursor-pointer items-center gap-[7px] border border-white/12 bg-black/35 px-[13px] font-game-korean text-[15px] tracking-[0.08em] text-game-ivory/50 transition-colors hover:border-white/30 hover:text-game-ivory/90"
    >
      <span className="text-[13px] leading-none">{muted ? '✕' : '♪'}</span>
      {muted ? '소리 꺼짐' : '소리'}
    </button>
  )
}
