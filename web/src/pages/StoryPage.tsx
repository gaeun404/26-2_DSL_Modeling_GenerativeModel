import {
  useEffect,
  useState,
} from 'react'

import {
  useNavigate,
} from 'react-router-dom'

import StoryTextFrame from '../components/story/StoryTextFrame'
import ConfirmDialog from '../components/common/ConfirmDialog'
import { useGameStore } from '../store/gameStore'
import {
  getCrimeScene,
  getStoryPages,
} from '../data/scenarioAdapter'


export default function StoryPage() {
  const navigate =
    useNavigate()
  const scenario = useGameStore((state) => state.scenario)
  const crimeScene = getCrimeScene(scenario)


  /* ========================================
      현재 나레이션 페이지
  ======================================== */
  const [
    currentPage,
    setCurrentPage,
  ] = useState(0)


  /* ========================================
      건너뛰기 팝업
  ======================================== */
  const [
    showSkipPopup,
    setShowSkipPopup,
  ] = useState(false)


  /* ========================================
      암전 여부
  ======================================== */
  const [
    isBlackout,
    setIsBlackout,
  ] = useState(false)

  const [
    isFinalStory,
    setIsFinalStory,
  ] = useState(false)


  /* 음악은 화면 단계로 갈린다 — components/common/Bgm 이 맡는다. */


  const storyPages = getStoryPages(scenario) ?? []
  const hasStory = storyPages.length > 0
  const hasFinalStory = crimeScene.text !== '' || crimeScene.image !== ''

  const currentStory = isFinalStory
    ? crimeScene.text || '현장에 도착했다.'
    : storyPages[currentPage]?.text ?? '나레이션 데이터를 불러오지 못했습니다.'


  const currentImage = isFinalStory
    ? crimeScene.image
    : storyPages[currentPage]?.image ?? ''


  const isLastPage = isFinalStory || currentPage === storyPages.length - 1

  const isFirstPage = isFinalStory || currentPage === 0


  /* ========================================
      암전 시작
  ======================================== */
  const startBlackout = () => {
    setShowSkipPopup(false)

    setIsBlackout(true)
  }


  /*
    ========================================
    암전이 시작되면 3초 후 다음 화면으로 이동
    ========================================

    암전이 끝나면 사건 발생 장면으로 이동한다.
  */
  useEffect(() => {
    if (!isBlackout) {
      return
    }

    const timer =
      window.setTimeout(() => {
        if (!isFinalStory && hasFinalStory) {
          setIsFinalStory(true)
          setIsBlackout(false)
          return
        }

        navigate('/crime-scene')
      }, 3000)


    return () => {
      window.clearTimeout(
        timer,
      )
    }
  }, [
    isBlackout,
    isFinalStory,
    hasFinalStory,
    navigate,
  ])


  /* ========================================
      다음
  ======================================== */
  const handleNext = () => {
    if (!hasStory && !isFinalStory) return

    if (isFinalStory) {
      navigate('/crime-scene')
      return
    }

    if (!isLastPage) {
      setCurrentPage(
        (prev) =>
          prev + 1,
      )

      return
    }

    /*
      마지막 나레이션에서 다음을 누르면
      암전 시작
    */
    startBlackout()
  }


  /*
    ========================================
    이전
    ========================================

    제보: "설명을 다시 보고 싶은데 한 번 넘기면 되돌아갈 수가 없다."
    서버를 부를 것도 없다 — 배열 인덱스를 뒤로 옮기면 끝이다.
  */
  const handlePrevious = () => {
    setCurrentPage((prev) => Math.max(0, prev - 1))
  }


  /* ========================================
      건너뛰기 팝업 열기
  ======================================== */
  const handleOpenSkipPopup =
    () => {
      setShowSkipPopup(true)
    }


  /* ========================================
      건너뛰기 취소
  ======================================== */
  const handleCloseSkipPopup =
    () => {
      setShowSkipPopup(false)
    }


  /* ========================================
      건너뛰기 확정

      나레이션을 모두 생략하고
      동일하게 암전으로 진입
  ======================================== */
  const handleSkip =
    () => {
      startBlackout()
    }


  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-black">

      {/* ========================================
          기존 나레이션 화면
      ======================================== */}
      <div
        className={`
          absolute
          inset-0

          transition-opacity
          duration-1000

          ${
            isBlackout
              ? 'opacity-0'
              : 'opacity-100'
          }
        `}
      >

        {/* 마지막 장면은 이미지와 붉은 색감만 남긴다. */}
        {!isFinalStory && (
          <img
            src="/assets/icons/title-background.svg"
            alt=""
            className="absolute left-0 top-0 h-[1024px] w-[1440px] object-fill"
          />
        )}


        {/* ========================================
            이야기 이미지

            글 테두리를 제 비율(1124:337)로 되돌리느라 자리가 더 필요해져
            조금 줄였다. 액자 비율(1045:599)은 그대로 지킨다 — 안 그러면
            이 액자도 상자 안에서 논다.
        ======================================== */}
        {/*
          ★마지막 장면은 **사진이 주인공**이다 (2026-08-31, 제보 —
            "그 빨간 배경으로 된 화면, 피해자 쓰러진 장면으로 바꿔야 한다").

            여기 깔리는 그림은 원래부터 현장 사진(주검이 있는 그것)이었는데
            두 가지가 그것을 가리고 있었다.

            하나. 붉은 막이 55%로 화면 전체를 덮었다. 시나리오가 「붉게 번지는
            전환」을 주문하긴 했지만, 고르게 55%면 번지는 게 아니라 그냥
            빨간 화면이 된다. 가장자리에서만 번지고 가운데는 비우도록 바꾼다.

            둘. 1024 높이 상자에 1045×600 사진을 object-cover 로 채우면
            좌우가 각각 100px씩 잘린다. **주검이 왼쪽 끝에 있어서 머리가
            잘려 나갔다.** 상자를 1440×827 로 두면 사진 비율(1.742)과
            정확히 맞아 한 점도 안 잘린다.
        */}
        <div
          className={
            isFinalStory
              ? 'absolute left-[60px] top-[20px] h-[758px] w-[1320px]'
              : 'absolute left-[231px] top-[22px] h-[560px] w-[977px]'
          }
        >

          {/* 실제 이미지 */}
          {currentImage !== '' && (
            <img
              src={currentImage}
              alt=""
              className={
                isFinalStory
                  ? 'absolute inset-0 h-full w-full object-cover'
                  : 'absolute left-[19px] top-[19px] h-[522px] w-[939px] object-cover'
              }
            />
          )}

          {/* 붉은 기운은 사진 위에만 얹는다 */}
          {isFinalStory && (
            <>
              {/* 전체에 옅은 핏기만 — 사진의 밝기는 건드리지 않는다 */}
              <div className="pointer-events-none absolute inset-0 z-[5] bg-[#8c0000]/14" />
              {/*
                번지는 것은 가장자리에서만.
                ★주검이 사진 왼쪽 끝에 누워 있다. 가운데만 비우는 비네팅으로는
                  하필 그 자리가 가장 어두워진다 — 비우는 범위를 62%까지 넓혀
                  바깥 테두리에서만 물들게 한다.
              */}
              <div className="pointer-events-none absolute inset-0 z-[5] bg-[radial-gradient(ellipse_at_50%_45%,rgba(112,0,0,0)_0%,rgba(112,0,0,0)_62%,rgba(112,0,0,0.42)_100%)]" />
            </>
          )}


          {/* 이미지 프레임 */}
          {!isFinalStory && (
            <img
              src="/assets/icons/ImageFrame.svg"
              alt=""
              className="pointer-events-none absolute inset-0 h-full w-full object-fill"
            />
          )}

        </div>


        {/* 이야기 글 */}
        {isFinalStory ? (
          <p className="absolute left-[220px] top-[800px] z-10 m-0 w-[1000px] text-center font-game-korean text-[20px] leading-[1.8] tracking-[0.04em] text-game-ivory">
            {currentStory}
          </p>
        ) : (
          <StoryTextFrame
            story={currentStory}
            width={1000}
          />
        )}


        {/* ========================================
            건너뛰기 · 이전 · 다음

            ★버튼이 화면 아래로 잘려 있었다 (2026-08-30).
              top 943 에 높이 104 짜리를 두어 아래끝이 1047 — 화면(1024)을 23px
              넘었다. yellow_button.svg 는 제 비율(1845:482 ≈ 3.83)을 지키므로
              높이를 줄이면 폭도 같이 줄여야 테두리가 상자를 채운다.
              78 × 299 로 맞추고 936 에 둔다 → 아래끝 1014.

            삽화 22~582 · 글 테두리 598~935 · 버튼 936~1014.
        ======================================== */}
        <div className="absolute left-[126px] top-[936px] flex w-[1124px] items-center justify-between">
          {isFinalStory ? (
            <div
              aria-hidden="true"
              className="h-[50px] w-[180px]"
            />
          ) : (
            <button
              type="button"
              onClick={handleOpenSkipPopup}
              className="relative h-[58px] w-[222px] cursor-pointer border-0 bg-transparent p-0"
            >
              <img
                src="/assets/icons/yellow_button.svg"
                alt=""
                className="absolute inset-0 h-full w-full object-fill"
              />
              <span className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean text-[21px] tracking-[0.08em] text-game-ivory/70">
                건너뛰기 &gt;
              </span>
            </button>
          )}

          <div className="flex items-center gap-[6px]">
            {/*
              ★셋의 크기를 맞춘다 (2026-08-30, 제보 — "다음·이전 버튼 크기 수정").
                「건너뛰기」와 「다음」은 299×78 액자인데 「이전」만 맨 글씨였다.
                셋 다 같은 액자·같은 크기(222×58)로 둔다.
                yellow_button.svg 는 제 비율(1845:482 ≈ 3.83)을 지키므로
                222 / 3.83 ≈ 58 이어야 테두리가 상자를 채운다.
            */}
            <button
              type="button"
              onClick={handlePrevious}
              disabled={!hasStory || isFirstPage}
              className="relative mr-[14px] h-[58px] w-[222px] cursor-pointer border-0 bg-transparent p-0 disabled:cursor-default disabled:opacity-25"
            >
              <img
                src="/assets/icons/yellow_button.svg"
                alt=""
                className="absolute inset-0 h-full w-full object-fill"
              />
              <span className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean text-[20px] tracking-[0.08em] text-game-ivory">
                &lt; 이전
              </span>
            </button>

            <button
              type="button"
              onClick={handleNext}
              disabled={!hasStory && !isFinalStory}
              className="relative h-[58px] w-[222px] cursor-pointer border-0 bg-transparent p-0"
            >
              <img
                src="/assets/icons/yellow_button.svg"
                alt=""
                className="absolute inset-0 h-full w-full object-fill"
              />
              <span className="absolute inset-0 flex items-center justify-center whitespace-nowrap font-game-korean text-[20px] tracking-[0.08em] text-game-ivory">
                {isFinalStory || (isLastPage && !hasFinalStory)
                  ? '사건으로'
                  : '다음'} &gt;
              </span>
            </button>
          </div>
        </div>

      </div>


      {/* ========================================
          건너뛰기 확인 팝업
      ======================================== */}
      {showSkipPopup &&
        !isBlackout && (
          <ConfirmDialog
            title="나레이션을 건너뛰시겠습니까?"
            description="사건 개요는 수첩에서 볼 수 있습니다."
            cancelLabel="아니오"
            confirmLabel="건너뛴다"
            onCancel={handleCloseSkipPopup}
            onConfirm={handleSkip}
          />
        )}


      {/* ========================================
          검은 암전

          Story 화면이 opacity 0이 되면서
          아래 검은 배경이 드러난다.
      ======================================== */}
      {isBlackout && (
        <div className="pointer-events-none absolute inset-0 z-[100] bg-black" />
      )}

    </main>
  )
}
