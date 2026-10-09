import type {
  InfoField,
  Scenario,
} from '../types/scenario'

const fieldValue = (
  fields: InfoField[],
  labels: string[],
  fallback = '',
) =>
  fields.find((field) =>
    labels.some((label) => field.label.includes(label)),
  )?.value ?? fallback

/*
  서버가 준 주소는 이미 절대 주소다(scenarioApi 가 들어오는 길목에서 채운다).
  여기서는 쓸 수 있는 모양인지만 본다.
*/
const usableImage = (value?: string) =>
  value && /^(https?:|data:|\/)/.test(value) ? value : ''

export const getScenarioTitle = (
  scenario: Scenario | null,
  fallback: string,
) => scenario?.title?.trim() || fallback

export const getStoryPages = (scenario: Scenario | null) => {
  const pages = scenario?.ui.narration.pages ?? []

  return pages.length > 0
    ? pages.map((page) => ({
        text: page.text || page.sentences.join(' '),
        image: usableImage(page.image?.url),
      }))
    : null
}

export const getCrimeScene = (scenario: Scenario | null) => ({
  text: scenario?.death.scene_description ?? '',
  image: usableImage(scenario?.ui.victim_card.body_art),
})

export const getScenarioId = (scenario: Scenario | null) =>
  scenario?.scenarioId ?? scenario?.scenario_id ?? scenario?.id ?? null

export const getMainBackground = (scenario: Scenario | null) =>
  usableImage(scenario?.ui.main_background_image)

export const getVictim = (scenario: Scenario | null) => {
  const card = scenario?.ui.victim_card
  const fields = card?.fields ?? []

  /*
    카드가 직접 주는 값을 먼저 쓰고, 없으면 fields 에서 라벨로 찾는다.
    전에는 fields 에 '이름' 칸이 아예 없어 이름 자리가 늘 비어 있었다.
  */
  return {
    name: card?.name || fieldValue(fields, ['이름', 'name']),
    role: card?.role ?? '',
    bio: card?.bio || card?.bio_short || '',
    status: fieldValue(fields, ['신분', '직업', 'status'], card?.role ?? ''),
    discoveredPlace:
      card?.found_place || fieldValue(fields, ['발견 장소', '장소', 'place']),
    discoveredTime:
      card?.found_time || fieldValue(fields, ['발견 시각', '시간', 'time']),
    discoverer: fieldValue(fields, ['발견자']),
    causeOfDeath: fieldValue(fields, ['사인'], '???'),
    image: usableImage(card?.portrait),
  }
}

export const getSuspects = (scenario: Scenario | null) => {
  const cards = scenario?.ui.suspect_cards ?? []

  if (cards.length === 0) return []

  const screens = scenario?.ui.place_screens ?? []

  return cards.map((card) => {
    const name =
      card.name || fieldValue(card.fields, ['이름', 'name'], card.list_sub)

    /* 이 인물이 서 있는 방. 없는 사람도 있다 */
    const home = screens.find((screen) => screen.cast_id === card.id)

    return {
      id: card.id,
      name,
      listName: name,
      englishName: fieldValue(card.fields, ['영문', 'english']),
      status: fieldValue(card.fields, ['신분', '직업', 'status'], card.list_sub),
      age: fieldValue(card.fields, ['나이', 'age'], ''),
      relation: fieldValue(card.fields, ['관계', 'relation'], ''),
      /* 상세 화면 설명 — 전에는 아예 안 내려와서 자리가 비어 있었다 */
      intro: card.intro ?? '',
      image: usableImage(card.portrait),
      /* 압박 판정에 따라 갈아 끼우는 얼굴 */
      faces: {
        calm: usableImage(card.faces?.calm),
        shaken: usableImage(card.faces?.shaken),
        broken: usableImage(card.faces?.broken),
      },
      standing: usableImage(card.standing),
      backgroundImage: usableImage(home?.background_image),
      placeId: home?.place_id ?? null,
      bgm: usableImage(card.theme),
      alibi: card.alibi_quote,
    }
  })
}

export const getPlaces = (scenario: Scenario | null) => {
  const places = scenario?.map.places ?? []

  return places.map((place) => {
    const screen = scenario?.ui.place_screens.find(
      (item) => item.place_id === place.id,
    )

    return {
      ...place,
      backgroundImage: usableImage(screen?.background_image),
      thumb: usableImage(place.thumb ?? screen?.map_thumb),
      /* 이 장소에 서 있는 인물. 없으면 조사만 하는 방이다 */
      castId: screen?.cast_id ?? null,
      characterName: screen?.character_name ?? '',
      interrogationName: screen?.character_name ?? '',
      characterImage: usableImage(screen?.character_image),
      talkNote: screen?.talk_note ?? '',
      bgm: usableImage(screen?.bgm),
    }
  })
}

/*
  조사 선택지.

  무엇이 나오는지(finds)와 결과 문장은 여기에 없다 —
  실제로 조사한 뒤 서버가 알려 준다.
  화면은 버튼 이름만 그리고, 누르면 서버에 묻는다.
*/
export const getInvestigationOptions = (
  scenario: Scenario | null,
  placeId: string,
  round: number,
) => {
  const place = scenario?.ui.place_screens.find(
    (screen) => screen.place_id === placeId,
  )
  const actions = place?.rounds[String(round)]?.actions ?? []

  return actions.map((action, index) => ({
    id: action.id || `a${index}`,
    index: action.index ?? index,
    label: action.label || action.button,
  }))
}

export const getNotebookPeople = (scenario: Scenario | null) =>
  getSuspects(scenario).map((suspect) => ({
    id: suspect.id,
    name: suspect.name,
    status: suspect.status,
    description: suspect.relation || suspect.alibi,
    image: suspect.image,
  }))

/*
  수첩의 단서.

  시나리오에 실려 오는 카드는 **이미 손에 넣은 것뿐**이다.
  서버가 새 단서를 줄 때마다 스토어가 여기에 얹는다.
*/
export const getNotebookClues = (
  scenario: Scenario | null,
  discoveredIds: string[],
) => {
  const cards = scenario?.ui.clue_cards ?? []

  /*
    서버 버전에 따라 held_clues 가 안 올 수 있다. 그때 undefined.length 를
    읽다가 **수첩 화면이 통째로 죽었다.** 목록 하나가 비었다고 화면이 죽어서는 안 된다.
  */
  const held = discoveredIds ?? []

  return cards
    .filter(
      (clue) => held.length === 0 || held.includes(clue.clue_id),
    )
    .map((clue) => ({
      id: clue.clue_id,
      title: clue.name || clue.type || clue.clue_id,
      type: clue.type,
      location: clue.acquired_place,
      acquisitionMethod: clue.acquired_method,
      description: clue.description,
      image: usableImage(clue.image),
      fullImage: usableImage(clue.full_image),
    }))
}

type RevealPage = {
  text: string
  image: string
  caption: string
  beat: number
  beatTitle: string
}

/*
  진상 (S-22).

  지목 전에는 beats 가 비어 있다 — 서버가 안 준다.
  지목한 뒤 스토어가 채워 넣는다.
*/
export const getRevealPages = (
  scenario: Scenario | null,
): RevealPage[] | null => {
  const beats = scenario?.ui.reveal_sequence.beats ?? []
  const pages: RevealPage[] = []

  beats.forEach((beat, index) => {
    const title = beat.title || `진상 ${index + 1}`

    beat.pages.forEach((page) => {
      if (!page.text) return

      pages.push({
        text: page.text,
        image: usableImage(page.image),
        caption: beat.caption ?? '',
        beat: index + 1,
        beatTitle: title,
      })
    })
  })

  if (pages.length > 0) return pages

  /*
    정답 여부와 관계없이 진상은 반드시 보여 준다.
    일부 백엔드는 오답일 때 컷별 beats를 비워 보내지만, 전문은
    ending.truth_reveal에 내려 준다. 컷이 없으면 그 전문으로 한 쪽을 만든다.
  */
  const fullText =
    scenario?.ui.reveal_sequence.full_text?.trim() ||
    scenario?.ending.truth_reveal?.trim()

  return fullText
    ? [{ text: fullText, image: '', caption: '', beat: 1, beatTitle: '진상' }]
    : null
}

/*
  범행 재연(S-23)은 이제 따로 없다.

  진상 여섯 박에 재연 여섯 컷을 얹어 한 줄기로 합쳤다(ui_view.reveal_view).
  같은 밤을 글로 한 번 그림으로 한 번 훑던 것을, 쪽마다 그림과 글을 함께
  두는 쪽으로 바꾼 것이다. 컷은 `getRevealPages` 가 이미 들고 온다.
*/
