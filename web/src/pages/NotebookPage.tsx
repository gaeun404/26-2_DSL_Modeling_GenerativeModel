import { useState } from 'react'

import NotebookHeader from '../components/notebook/NotebookHeader'

import PersonList from '../components/notebook/PersonList'
import PersonDetail from '../components/notebook/PersonDetail'
import MemoPanel from '../components/notebook/MemoPanel'

import ClueList from '../components/notebook/ClueList'
import ClueDetail from '../components/notebook/ClueDetail'
import ClueMemoPanel from '../components/notebook/ClueMemoPanel'

import NotebookBottomNav from '../components/notebook/NotebookBottomNav'
import FreeMemoPanel from '../components/notebook/FreeMemoPanel'
import TimelinePanel from '../components/notebook/TimelinePanel'
import { useGameStore } from '../store/gameStore'
import {
  getNotebookClues,
  getNotebookPeople,
} from '../data/scenarioAdapter'

/* =========================================
   인물 데이터 타입
========================================= */

export type NotebookPerson = {
  id: string
  name: string
  status?: string
  description: string
  image?: string
}

/* =========================================
   단서 데이터 타입
========================================= */

export type NotebookClue = {
  id: string
  title: string

  /*
    단서 상세 정보

    TODO(API):
    추후 백엔드 clue 데이터와 연결
  */
  type: string
  location: string
  acquisitionMethod: string

  description: string
  image: string
}

type NotebookTab =
  | 'person'
  | 'clue'
  | 'timeline'
  | 'memo'

export default function NotebookPage() {
  const scenario = useGameStore((state) => state.scenario)
  const discoveredClueIds = useGameStore(
    (state) => state.discoveredClueIds,
  )
  const scenarioPeople = getNotebookPeople(scenario)
  const scenarioClues = getNotebookClues(
    scenario,
    discoveredClueIds,
  )
  const persons = scenarioPeople
  const clues = scenarioClues
  /* =========================================
     현재 탭
  ========================================= */

  const [
    selectedTab,
    setSelectedTab,
  ] = useState<NotebookTab>('person')

  /* =========================================
     선택된 인물
  ========================================= */

  const [
    selectedPersonId,
    setSelectedPersonId,
  ] = useState('')

  const selectedPerson =
    persons.find(
      (person) =>
        person.id === selectedPersonId,
    ) ?? persons[0]

  /* =========================================
     선택된 단서
  ========================================= */

  const [
    selectedClueId,
    setSelectedClueId,
  ] = useState('')

  const selectedClue =
    clues.find(
      (clue) =>
        clue.id === selectedClueId,
    ) ?? clues[0]

  return (
    <main
      className="
        relative
        h-[1024px]
        w-[1440px]
        overflow-hidden
        bg-black
        text-game-ivory
      "
    >
      {/* Header */}
      <NotebookHeader />

      {/* =========================================
          인물 탭
      ========================================= */}
      {selectedTab === 'person' && (
        selectedPerson ? <>
          <PersonList
            persons={persons}
            selectedPersonId={
              selectedPersonId
            }
            onSelect={
              setSelectedPersonId
            }
          />

          <PersonDetail
            person={selectedPerson}
          />

          <MemoPanel
            personId={
              selectedPerson.id
            }
            personName={
              selectedPerson.name
            }
          />
        </> : (
          <div className="absolute left-[420px] top-[100px] flex h-[850px] w-[525px] items-center justify-center font-game-korean text-[25px] tracking-[0.1em] text-game-ivory">
            용의자 정보를 불러오지 못했습니다.
          </div>
        )
      )}

      {/* =========================================
          단서 탭
      ========================================= */}
      {selectedTab === 'clue' && (
        <>
          {selectedClue ? (
            <>
              <ClueList
                clues={clues}
                selectedClueId={
                  selectedClueId
                }
                onSelect={
                  setSelectedClueId
                }
              />

              <ClueDetail
                clue={selectedClue}
                clues={clues}
              />

              <ClueMemoPanel
                clueId={
                  selectedClue.id
                }
                clueTitle={
                  selectedClue.title
                }
              />
            </>
          ) : (
            <div
              className="
                absolute
                flex
                items-center
                justify-center
                font-game-korean
                tracking-[0.1em]
                text-game-ivory
              "
              style={{
                left: 420,
                top: 100,
                width: 525,
                height: 850,
                fontSize: 25,
              }}
            >
              아직 획득한 단서가 없습니다.
            </div>
          )}
        </>
      )}

      {/* =========================================
          자유메모 탭
      ========================================= */}
      {/* 그날 밤 시간표 — 아는 것만 시간순으로 */}
      {selectedTab === 'timeline' && <TimelinePanel />}

      {selectedTab === 'memo' && (
        <FreeMemoPanel />
      )}

      {/* =========================================
          하단 탭
      ========================================= */}
      <NotebookBottomNav
        selectedTab={selectedTab}
        onSelect={setSelectedTab}
      />
    </main>
  )
}
