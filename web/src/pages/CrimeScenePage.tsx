import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useGameStore } from '../store/gameStore'
import {
  getCrimeScene,
  getVictim,
} from '../data/scenarioAdapter'
import type { ClueCard } from '../types/scenario'
import GameHeader2 from '../components/common/GameHeader2'

const fallbackClues = [
  { title: '약재방 출입기록', meta: '기록 · 약재실' },
  { title: '비어 있는 약재 칸', meta: '현장 · 약재실' },
  { title: '깨진 약사발', meta: '물증 · 약재실' },
  { title: '수상한 냄새', meta: '현장 · 약재실' },
  { title: '젖은 발자국', meta: '흔적 · 복도' },
]

type SceneClue = ClueCard & {
  displayTitle: string
  displayMeta: string
}

export default function CrimeScenePage() {
  const navigate = useNavigate()
  const scenario = useGameStore((state) => state.scenario)
  const crimeScene = getCrimeScene(scenario)
  const victim = getVictim(scenario)
  const [selectedClue, setSelectedClue] = useState<ClueCard | null>(null)
  const serverClues = scenario?.ui.clue_cards ?? []

  const clues: SceneClue[] = serverClues.length > 0
    ? serverClues.slice(0, 5).map((clue) => ({
        ...clue,
        displayTitle: clue.name || clue.type,
        displayMeta: `${clue.acquired_place} · ${clue.acquired_method}`,
      }))
    : fallbackClues.map((clue, index) => ({
        clue_id: `fallback-${index}`,
        name: clue.title,
        list_sub: '',
        image: '',
        full_image: '',
        type: clue.meta.split(' · ')[0],
        acquired_place: clue.meta.split(' · ')[1] ?? '',
        acquired_method: '현장 조사',
        description: '사건 현장에서 확인된 단서입니다.',
        displayTitle: clue.title,
        displayMeta: clue.meta,
      }))

  return (
    <main
      className="relative h-[1024px] w-[1440px] overflow-hidden bg-[#0d0b08] bg-[url('/assets/icons/title-background.svg')] bg-[length:100%_100%] bg-no-repeat font-game-korean text-game-ivory"
    >

      <GameHeader2
        leftText="< 돌아가기"
        title="CRIME SCENE"
        rightText=""
        onLeftClick={() => navigate('/story')}
        onRightClick={() => navigate('/notebook')}
      />

      {/*
        ★칸이 서로 올라타던 것을 고친다 (2026-08-29, 시연 제보).
          제보: "/crime-scene UI 레이아웃이 뻑났다 · 글이랑 버튼이 겹친다."
          본문을 절대좌표 top-84 에 두고 카드도 절대좌표 top-188 에 두었더니,
          본문이 세 줄이 되는 순간 카드가 글 위에 얹혔다. 아래는 텅 비었고.
          위에서 아래로 흐르게 바꾸고, 남는 자리에 현장 그림을 넣는다.
      */}
      <div className="absolute left-[50px] top-[130px] flex w-[1340px] gap-[60px]">
        {/* 백엔드에서 받은 피해자 시신 이미지 자리 */}
        <div className="flex h-[418px] w-[736px] shrink-0 items-center justify-center border border-[#55452c] bg-[#161009]">
          {(crimeScene.image || victim.image) !== '' ? (
          <img
              src={crimeScene.image || victim.image}
              alt="피해자"
              className="h-full w-full object-contain"
            />
          ) : (
            <span className="text-[18px] tracking-[0.08em] text-[#7d6f57]">
              피해자 이미지
            </span>
          )}
        </div>

        <div className="flex w-[500px] shrink-0 flex-col">
          <p className="m-0 text-[20px] leading-[1.8] tracking-[0.04em] text-[#d8cdb4]">
            {crimeScene.text}
          </p>
        </div>

      </div>

      {/*
        단서 카드 — 제목 / 한 줄 / 종류.
        전에는 「세미나실(중도 6층) · 사건 시작 시 공개」처럼
        장소와 방법만 붙어 있어 무엇인지 알기 어려웠다.
      */}
      {/*
        ★몇 장이 오든 **가운데**로 모은다 (2026-08-31, 제보 —
          "3갠데 왼쪽으로 몰려있으니까 어휘워").

          다섯 칸짜리 격자(grid-cols-5)였다. 그러면 석 장일 때 왼쪽 세 칸만
          차고 오른쪽 두 칸이 빈 채로 남아, 화면이 한쪽으로 쏠려 보인다.
          시작 단서는 셋이고 라운드마다 늘어나므로 개수가 고정이 아니다.

          칸 너비는 그대로 두고(다섯 장일 때 꼭 맞는 252.8 =
          (1340 - 4×19) / 5) 줄만 가운데 정렬로 바꾼다. 다섯 장이면
          예전과 똑같이 꽉 차고, 석 장이면 가운데 셋으로 놓인다.
      */}
      <section className="absolute left-[50px] top-[600px] flex w-[1340px] flex-wrap justify-center gap-[19px]">
        {clues.map((clue, index) => (
          <button
            type="button"
            key={`${clue.clue_id}-${index}`}
            onClick={() => setSelectedClue(clue)}
            /* 262 로는 두 줄 설명이 반쯤 잘렸다 — 그림 150 + 안쪽 여백 24 + 제목 23 + 설명 39 + 종류 24 */
            className="relative flex h-[286px] w-[252.8px] shrink-0 cursor-pointer flex-col overflow-hidden border-0 bg-transparent p-0 text-left transition-colors"
          >
            <img
              src="/assets/icons/person_choice.svg"
              alt=""
              className="pointer-events-none absolute left-[calc(50%-20px)] top-1/2 h-[252.8px] w-[280px] object-fill"
              style={{
                transform:
                  'translate(-50%, -50%) rotate(90deg) scaleX(1.15) scaleY(1.9)',

              }}
            />

            <div className="relative z-10 mx-[18px] my-[0.2cm] flex min-h-0 w-auto self-stretch flex-1 flex-col overflow-y-auto overflow-x-hidden [overflow-wrap:anywhere] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <div className="whitespace-normal text-[18px] font-bold leading-[1.3] tracking-[0.03em] text-[#d8cdb4]">
                {clue.displayTitle}
              </div>
              <div className="mt-[5px] whitespace-normal text-[13px] leading-[1.5] text-[#9a8d72]">
                {clue.list_sub || clue.description}
              </div>

              <div className="mt-[10px] h-[135px] w-[calc(100%_-_24px)] shrink-0 overflow-hidden border border-white/70 bg-transparent">
                {(clue.image || clue.full_image) !== '' && (
                  <img
                    src={clue.image || clue.full_image}
                    alt={clue.displayTitle}
                    className="h-full w-full object-cover"
                  />
                )}
              </div>

              <div className="mt-auto pt-[6px] text-[12px] tracking-[0.08em] text-[#8a3830]">
                {clue.type}
              </div>
            </div>
          </button>
        ))}
      </section>

      <button
        type="button"
        onClick={() => navigate('/victim')}
        className="absolute left-[950px] top-[900px] h-[117px] w-[450px] cursor-pointer border-0 bg-transparent p-0"
      >
        <img
          src="/assets/icons/button.svg"
          alt=""
          className="absolute inset-0 h-full w-full object-fill"
        />
        <span className="absolute inset-0 flex -translate-x-[10px] -translate-y-[5px] items-center justify-center whitespace-nowrap font-game-korean text-[20px] tracking-[0.08em] text-game-ivory">
          피해자를 살핀다
        </span>
      </button>

      {selectedClue !== null && (
        <div
          className="absolute inset-0 z-30 flex items-center justify-center bg-black/75"
          onClick={() => setSelectedClue(null)}
        >
          <section
            className="relative flex h-[610px] w-[620px] flex-col border border-[#806c45] bg-[#161009] px-[46px] py-[38px] outline outline-1 outline-offset-4 outline-[#55452c]"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              aria-label="단서 상세 닫기"
              onClick={() => setSelectedClue(null)}
              className="absolute right-[24px] top-[18px] cursor-pointer border-0 bg-transparent font-game-korean text-[22px] text-[#9a8d72]"
            >
              ×
            </button>
            {selectedClue.image !== '' && (
              <img
                src={selectedClue.image}
                alt={selectedClue.name || selectedClue.type}
                className="h-[190px] w-full shrink-0 object-cover"
              />
            )}
            {/*
              ★제목은 **단서 이름**이다 (2026-08-31, 제보 —
                "인트로엔 「검안」인데 팝업을 열면 「검험」이라 쓰여 있다").

                카드 제목은 name("검안" · "여섯 잔")을 쓰는데 팝업 제목만 type,
                곧 fields['종류']("검험" · "현장")를 쓰고 있었다. 같은 단서인데
                누른 이름과 열린 이름이 달랐다.

                종류는 버릴 것이 아니라 **표의 한 줄**로 내린다 — 수첩(ClueDetail)과
                장소 조사 팝업(InvestigationPanel)이 이미 그렇게 그리고 있다.
            */}
            <h2 className="mt-[24px] shrink-0 font-game-korean text-[27px] tracking-[0.08em] text-[#d8cdb4]">
              {selectedClue.name || selectedClue.type}
            </h2>
            <div className="mt-[16px] grid shrink-0 grid-cols-[120px_1fr] border-y border-[#55452c] font-game-korean text-[15px] leading-[1.8] text-[#d8cdb4]">
              <span className="border-b border-[#55452c] py-[10px] text-[#9a8d72]">종류</span>
              <span className="border-b border-[#55452c] py-[10px]">{selectedClue.type}</span>
              <span className="border-b border-[#55452c] py-[10px] text-[#9a8d72]">장소</span>
              <span className="border-b border-[#55452c] py-[10px]">{selectedClue.acquired_place}</span>
              <span className="py-[10px] text-[#9a8d72]">획득 방법</span>
              <span className="py-[10px]">{selectedClue.acquired_method}</span>
            </div>
            {/* 설명이 길어도 상자 밖으로 흘러 나가지 않게 — 넘치는 만큼은 굴려 읽는다 */}
            <p className="thin-scroll mt-[22px] min-h-0 flex-1 overflow-y-auto pr-[10px] font-game-korean text-[17px] leading-[1.9] tracking-[0.03em] text-[#d8cdb4]">
              {selectedClue.description}
            </p>
          </section>
        </div>
      )}
    </main>
  )
}
