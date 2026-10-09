import {
  useEffect,
  useMemo,
  useState,
} from 'react'
import { useNavigate } from 'react-router-dom'

import { getLibraryCases } from '../api/scenarioApi'
import CaseGallery from '../components/library/CaseGallery'
import type { LibraryCase } from '../components/library/CaseGallery'
import CaseInfo from '../components/library/CaseInfo'
import LibraryHeader from '../components/library/LibraryHeader'
import LibrarySort from '../components/library/LibrarySort'
import type {
  SortType,
  StoryCategory,
} from '../components/library/LibrarySort'
import { useGameStore } from '../store/gameStore'

export default function LibraryPage() {
  const navigate = useNavigate()
  const setSelectedLibraryCase = useGameStore(
    (state) => state.setSelectedLibraryCase,
  )
  const [cases, setCases] = useState<LibraryCase[]>([])
  const [selectedCaseId, setSelectedCaseId] = useState('')
  const [sortType, setSortType] = useState<SortType>('recent')
  const [categoryOpen, setCategoryOpen] = useState(false)
  const [category, setCategory] =
    useState<StoryCategory>('folktale')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    getLibraryCases()
      .then((items) => {
        if (cancelled) return
        setCases(items)
        setSelectedCaseId(items[0]?.id ?? '')
      })
      .catch((requestError: unknown) => {
        if (cancelled) return
        setError(
          requestError instanceof Error
            ? requestError.message
            : '사건 목록을 불러오지 못했습니다.',
        )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const visibleCases = useMemo(() => {
    const result =
      sortType === 'category'
        ? cases.filter((item) => item.category === category)
        : [...cases]

    if (sortType === 'recent') {
      result.sort((a, b) => b.createdAt - a.createdAt)
    }
    if (sortType === 'difficulty') {
      result.sort((a, b) => b.difficulty - a.difficulty)
    }

    return result
  }, [cases, category, sortType])

  const selectedCase =
    cases.find((item) => item.id === selectedCaseId) ?? null

  const handleCategoryChange = (nextCategory: StoryCategory) => {
    setCategory(nextCategory)
    setSortType('category')
    setCategoryOpen(false)
    setSelectedCaseId(
      cases.find((item) => item.category === nextCategory)?.id ?? '',
    )
  }

  const handleStart = () => {
    if (selectedCase === null) return

    setSelectedLibraryCase({
      id: selectedCase.id,
      title: selectedCase.title,
      origin: selectedCase.origin,
      backgroundLine: selectedCase.backgroundLine,
      incidentLine: selectedCase.incidentLine,
      endingLine1: selectedCase.endingLine1,
      endingLine2: selectedCase.endingLine2,
    })
    navigate(`/loading?mode=archive&caseId=${selectedCase.id}`)
  }

  return (
    <main className="relative h-[1024px] w-[1440px] overflow-hidden bg-game-bg">
      <LibraryHeader />
      <LibrarySort
        sortType={sortType}
        categoryOpen={categoryOpen}
        onSortChange={setSortType}
        onCategoryOpen={() => setCategoryOpen((current) => !current)}
        onCategoryChange={handleCategoryChange}
      />

      <CaseGallery
        cases={visibleCases}
        selectedCaseId={selectedCaseId}
        onSelect={setSelectedCaseId}
      />

      {selectedCase ? (
        <CaseInfo selectedCase={selectedCase} onStart={handleStart} />
      ) : (
        <div className="absolute left-[70px] top-[500px] flex w-[1300px] items-center justify-center font-game-korean text-[27px] tracking-[0.1em] text-game-ivory/60">
          {loading
            ? '사건 목록을 불러오는 중입니다.'
            : error || '준비된 사건이 없습니다.'}
        </div>
      )}
    </main>
  )
}
