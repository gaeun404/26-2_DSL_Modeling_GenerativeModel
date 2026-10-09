import {
  useEffect,
  useState,
} from 'react'

import {
  useNavigate,
  useSearchParams,
} from 'react-router-dom'

import Title from '../components/common/Title'
import LoadingProgressBar from '../components/loading/LoadingProgressBar'
import LoadingStatusList from '../components/loading/LoadingStatusList'

import type {
  LoadingMode,
} from '../components/loading/LoadingStatusList'

import { useGameStore } from '../store/gameStore'


const GAUGE_COUNT = 17
const WAIT_GAUGE = 16

/* 실시간 생성이 없으므로, 기본으로 여는 사건 */
const DEFAULT_CASE = '91_dsl_demo.json'


export default function LoadingPage() {
  const navigate = useNavigate()

  const [searchParams] =
    useSearchParams()

  const openSession =
    useGameStore(
      (state) =>
        state.openSession,
    )

  const [
    filledGauges,
    setFilledGauges,
  ] = useState(0)

  const [
    dataReady,
    setDataReady,
  ] = useState(false)

  const [loadError, setLoadError] =
    useState('')


  /*
    /loading?mode=archive&caseId=...
      → 준비된 사건을 연다

    실시간 생성(mode=generate)은 지금 없다.
    어느 쪽으로 들어와도 준비된 사건을 연다.
  */
  const mode: LoadingMode =
    searchParams.get('mode') ===
    'archive'
      ? 'archive'
      : 'generate'


  const caseId =
    searchParams.get('caseId')


  const loadingTitle =
    mode === 'archive'
      ? '사건 기록을 여는 중..'
      : '이야기를 각색하는 중...'


  /* 로딩바 연출

    한 번에 한 칸씩 증가

    백엔드 완료 전:
      최대 16 / 17

    백엔드 완료 후:
      마지막 17번째 칸 */
  useEffect(() => {
    const interval =
      window.setInterval(() => {
        setFilledGauges(
          (previous) => {
            if (
              previous >=
              WAIT_GAUGE
            ) {
              return previous
            }

            return previous + 1
          },
        )
      }, 450)

    return () => {
      window.clearInterval(
        interval,
      )
    }
  }, [])


  
  useEffect(() => {
    let cancelled = false


    /*
      판을 연다.

      서버가 세션을 만들고, 화면이 읽을 시나리오와
      첫 상태를 한 번에 내려 준다.
      정답(범인·진상·재연)은 여기 실려 오지 않는다.
    */
    const startLoading = async () => {
      try {
        await openSession(caseId || DEFAULT_CASE)

        if (cancelled) {
          return
        }

        setDataReady(true)
      } catch (error) {
        if (cancelled) {
          return
        }

        console.error('사건을 여는 데 실패했습니다:', error)

        setLoadError(
          error instanceof Error
            ? error.message
            : '사건을 여는 데 실패했습니다.',
        )
      }
    }


    startLoading()


    return () => {
      cancelled = true
    }
  }, [
    caseId,
    openSession,
  ])


  /* 마지막 한 칸

    데이터가 준비되어도 바로 17칸으로
    점프하지 않는다.

    16칸까지 자연스럽게 채운 뒤
    마지막 칸을 채운다
  */
  useEffect(() => {
    if (!dataReady) {
      return
    }


    if (
      filledGauges <
      WAIT_GAUGE
    ) {
      return
    }


    const timeout =
      window.setTimeout(() => {
        setFilledGauges(
          GAUGE_COUNT,
        )
      }, 450)


    return () => {
      window.clearTimeout(
        timeout,
      )
    }
  }, [
    dataReady,
    filledGauges,
  ])


  /* 로딩 완료

    17칸이 모두 차면 잠깐 기다린 뒤
    사건 시작 화면으로 이동  */
  useEffect(() => {
    if (
      filledGauges <
      GAUGE_COUNT
    ) {
      return
    }


    const timeout =
      window.setTimeout(() => {
        navigate(
          `/case-open?mode=${mode}`,
        )
      }, 700)


    return () => {
      window.clearTimeout(
        timeout,
      )
    }
  }, [
    filledGauges,
    navigate,
    mode,
  ])


  return (
    <main
      className="
        relative
        h-[1024px]
        w-[1440px]
        overflow-hidden
        bg-game-bg
      "
    >

      {/* 배경 */}
      <img
        src="/assets/icons/title-background.svg"
        alt=""
        className="
          absolute
          left-0
          top-0
          h-[1024px]
          w-[1440px]
          object-fill
        "
      />


      {/* 제목 */}
      <Title
        text={loadingTitle}
        className="
          absolute
          left-[270px]
          top-[254px]

          flex
          h-[140px]
          w-[900px]
          items-center
          justify-center

          whitespace-nowrap
          leading-[140px]
        "
        decorationClassName="
          left-[460px]
          top-[32px]
          h-[390px]
          w-[520px]
        "
      />


      {/*  로딩 상태 문구 */}
      <LoadingStatusList
        filledGauges={
          filledGauges
        }
        mode={mode}
      />


      {/* 로딩바 한칸씩 */}
      <LoadingProgressBar
        filledGauges={
          filledGauges
        }
      />


      {/* =====================================
          서버에 닿지 못했을 때

          여기서 멈추는 편이 낫다 —
          빈 화면으로 넘어가면 무엇이 잘못됐는지
          알 길이 없다.
      ===================================== */}
      {loadError !== '' && (
        <div
          className="
            absolute
            left-[270px]
            top-[700px]
            flex
            w-[900px]
            flex-col
            items-center
            gap-[18px]
            font-game-korean
            text-game-ivory
          "
        >
          <p className="text-[24px] tracking-[0.06em] text-game-red-light">
            {loadError}
          </p>

          <p className="text-[18px] leading-[1.7] text-game-ivory/55">
            백엔드가 켜져 있는지 확인해 주세요.
            <br />
            Gaeun 폴더에서 <code>python3 server.py</code>
          </p>

          <button
            type="button"
            onClick={() => navigate('/')}
            className="
              mt-[10px]
              cursor-pointer
              border
              border-game-parchment/50
              bg-transparent
              px-[40px]
              py-[14px]
              text-[20px]
              tracking-[0.1em]
              text-game-ivory
            "
          >
            처음으로
          </button>
        </div>
      )}

    </main>
  )
}
