# -*- coding: utf-8 -*-
"""
presence.py — 인물의 **생김새·목소리**와 시나리오의 **인트로 분위기**를 또렷하게 만든다.

왜 필요한가
  ① BGM이 다 비슷하다.
     23편의 인트로 분위기 지시가 **글자 하나까지 같았다** — "밝고 설화적, 향수 어린".
     BPM만 난수로 달랐다. 생성모델이 같은 프롬프트를 받으니 같은 곡이 나온다.
     인트로는 **원작의 결**을 따라야 한다. 흥부전과 푸른수염이 같은 곡일 수 없다.

  ② 용의자 그림·목소리를 만들 재료가 없다.
     지금 인물에게 있는 것은 "40대 남", "과묵하다", "낮고 건조한 음성" 정도다.
     이걸로 이미지 모델을 돌리면 다섯 사람이 다 비슷하게 나온다.
     얼굴·체격·옷·버릇·표정을, 그리고 목소리는 음높이·속도·질감까지 적어야 한다.

무엇을 넣나
  cast[].appearance  얼굴 · 체격 · 머리 · 눈 · 옷 · 표식 · 평상시 표정 · 몰렸을 때 표정
                     + prompt_ko / prompt_en (이미지 모델에 그대로 넣는 한 줄)
  cast[].voice_spec  음높이 · 속도 · 질감 · 말하는 결 · 숨 · 기본 감정 · 피할 것
                     + prompt_en (음성 모델용)
  bgm.cues.intro     원작마다 다른 분위기 · 악기 · 영어 프롬프트

무엇을 지어내지 않나
  나이·성별·신분·성격·말투는 이미 시나리오에 있다. 거기서 **파생**할 뿐,
  없는 사실(흉터가 있다, 다리를 전다)을 새로 만들지 않는다.
  단, 시나리오에 이미 적힌 것(피해자의 푸른 수염 등)은 그대로 살린다.

사용:
    python presence.py "scenarios/[0-9]*.json"
    python presence.py --check
"""
import json, glob, sys, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")

# ── ① 원작의 결 — 인트로는 여기서 갈린다 ─────────────────────────────
#   '옛날 옛적에'로 시작하는 나레이션이 붙는 자리다. 사건의 음산함이 아니라
#   **원작 이야기 자체의 결**을 따라야, 뒤집힐 때 낙차가 산다.
ORIGIN_TONE = {
    "흥부전":       ("익살스럽고 넉넉한", "장구 장단에 실린 해학. 웃다가 뒤통수를 맞는다",
                    "playful Korean folk humor, janggu groove, warm and bustling"),
    "심청전":       ("애틋하고 비장한", "효(孝)의 무게. 물빛 아래 가라앉는 정서",
                    "solemn Korean elegy, ajaeng bowed strings, tidal and mournful"),
    "전우치전":     ("장난스럽고 신비로운", "도술의 변덕. 가벼운 듯 서늘하다",
                    "mischievous Korean fantasy, plucked geomungo, sly and airy"),
    "홍길동전":     ("의롭고 씩씩한", "떠도는 협객의 발걸음. 곧고 단단하다",
                    "heroic Korean march, taepyeongso and drums, upright and driving"),
    "운영전":       ("애절하고 갇힌", "궁 담장 안의 사랑. 아름답되 숨 막힌다",
                    "confined Korean court romance, gayageum, beautiful and airless"),
    "구운몽":       ("몽환적이고 화려한", "꿈과 깨어남 사이. 향(香)처럼 번진다",
                    "dreamlike Tang-Korean court, daegeum flute, hazy and opulent"),
    "아랑설화":     ("서늘하고 원한 어린", "원귀 괴담. 처음부터 밤이다",
                    "chilling Korean ghost tale, hollow flute, night from the first bar"),
    "나무꾼과선녀": ("맑고 아련한", "선녀못의 물빛. 곧 잃을 것을 모르는 밝음",
                    "clear Korean pastoral, small gong and flute, innocent and luminous"),
    "해와 달이 된 오누이": ("아이답고 조마조마한", "동요 같다가 발소리가 섞인다",
                    "childlike Korean nursery tune turning uneasy, wood block steps"),
    "장화홍련":     ("가련하고 축축한", "연못의 물비린내. 자매의 목소리",
                    "damp Korean lament, two-voice motif, pond stillness"),
    "옹고집전":     ("우스꽝스럽고 얄미운", "인색한 부자의 장단. 벌 받을 줄 모르는 흥",
                    "comic Korean folk swagger, cheeky percussion, self-satisfied"),
    "푸른수염":     ("화려하고 음산한", "촛대와 금박, 그 아래 열지 말라는 방 하나",
                    "opulent yet sinister medieval European, lute and viol, candlelit dread"),
    "헨젤과그레텔": ("달콤하고 불길한", "설탕과 숲. 예쁠수록 무섭다",
                    "sweet music-box turning wrong, celesta and forest air"),
    "빨간모자":     ("천진하고 위태로운", "숲길의 발걸음. 뒤에 무언가 따라온다",
                    "innocent European walking tune with something trailing behind"),
    "미녀와야수":   ("우아하고 쓸쓸한", "빈 무도회장. 아름다움이 갇혀 있다",
                    "elegant lonely waltz, empty ballroom, harpsichord and strings"),
    "룸펠슈틸츠헨": ("기이하고 재바른", "물레 도는 소리. 이름을 맞히는 놀이",
                    "eerie spinning-wheel ostinato, nimble and puzzling"),
    "하멜른의 피리 부는 사나이": ("홀리는 듯한", "피리 하나에 온 마을이 끌려간다",
                    "hypnotic pipe melody, whole-town procession, enchanting and wrong"),
    "눈의 여왕":    ("차갑고 반짝이는", "얼음 조각. 아름답고 감정이 없다",
                    "glassy Nordic cold, glockenspiel and bowed metal, beautiful and blank"),
    "성냥팔이 소녀": ("가난하고 따뜻한", "성냥불 한 개비만큼의 온기",
                    "threadbare 19th-century warmth, solo violin, one match of heat"),
    "오르페우스":   ("신화적이고 애가풍의", "리라 한 대. 죽음을 설득하려는 노래",
                    "ancient Greek elegy, solo lyre, pleading with death"),
    "나생문":       ("황폐하고 메마른", "허물어진 성문. 비와 시체 냄새",
                    "desolate East-Asian ruin, sparse shakuhachi, rain and rot"),
}
DEFAULT_TONE = ("담담하고 서늘한", "사건 앞의 고요", "restrained and cool, quiet before the case")


def fix_intro(s):
    b = s.get("bgm") or {}
    cues = b.get("cues") or {}
    intro = cues.get("intro")
    if not isinstance(intro, dict):
        return False
    # '나무꾼과 선녀' vs '나무꾼과선녀' — 띄어쓰기 때문에 못 찾으면 안 된다
    def _n(x):
        return re.sub(r"[\s·,()]", "", x or "")
    origin = _n((s.get("meta") or {}).get("origin", ""))
    tone = None
    for k, v in ORIGIN_TONE.items():
        kk = _n(k)
        if kk and (kk in origin or origin in kk):
            tone = v
            break
    tone = tone or DEFAULT_TONE
    pal = b.get("palette") or {}
    inst = ", ".join((pal.get("instruments") or [])[:3])
    intro["mood"] = tone[0]
    intro["note"] = tone[1]
    intro["instruments"] = (pal.get("instruments") or [])[:4]
    intro["prompt_en"] = (f"{tone[2]}; {inst}; {pal.get('scale','modal')}; "
                          f"{intro.get('bpm', 72)} BPM; instrumental, no vocals; "
                          f"60-90s loop, low mix under narration")
    intro["contrast"] = ("이 곡은 사건 이후의 음악과 **결이 달라야 한다.** "
                         "여기서 밝거나 아름다울수록 뒤집힐 때 낙차가 커진다.")
    return True


# ── ② 생김새 ─────────────────────────────────────────────────────────
BUILD = {"10대": "아직 여윈 몸", "20대": "단단하고 날렵한 몸", "30대": "다부진 체격",
         "40대": "살이 붙기 시작한 몸", "50대": "굽기 시작한 어깨", "60대": "마르고 굽은 몸",
         "70대": "작고 마른 몸"}
HAIR_OLD = {"여": "쪽 진 머리", "남": "상투와 망건"}
HAIR_WEST = {"여": "땋아 올린 머리", "남": "짧게 친 머리"}
HAIR_MOD = {"여": "묶어 넘긴 머리", "남": "단정히 빗은 머리"}
CLOTH = {
    "east": {0: "무명 저고리와 물 빠진 치마·바지, 소맷부리가 닳았다",
             1: "무명 두루마기, 허리에 열쇠나 셈 주머니",
             2: "길 위의 옷차림, 봇짐과 짚신",
             3: "낡은 장삼과 염주, 바랑",
             4: "깨끗한 명주 저고리, 수수하나 정갈하다",
             5: "비단 두루마기와 갓, 손에 부채"},
    "west": {0: "거친 리넨 앞치마와 나무 나막신",
             1: "검은 조끼와 흰 셔츠, 허리에 열쇠 꾸러미",
             2: "여행용 망토와 흙 묻은 장화",
             3: "성직자풍의 긴 옷과 목걸이",
             4: "수수한 모직 드레스나 상의",
             5: "벨벳과 자수, 반지와 브로치"},
    "modern": {0: "낡은 후드와 운동화", 1: "구겨진 셔츠와 사원증",
               2: "코트와 낡은 가죽 가방", 3: "헐렁한 니트와 안경",
               4: "무난한 정장", 5: "잘 다린 정장과 값나가는 시계"},
}
# 성격 낱말 → 얼굴·표정
FACE_BY_TRAIT = [
    (["인색", "셈", "계산"], "볼이 여위고 입꼬리가 아래로 처진 얼굴", "눈으로 셈을 하듯 상대를 훑는다"),
    (["과묵", "조용", "말수"], "감정이 잘 드러나지 않는 평평한 얼굴", "입을 꾹 다물고 시선을 아래에 둔다"),
    (["수다", "말이 많", "눈치"], "표정이 쉴 새 없이 바뀌는 둥근 얼굴", "눈동자가 부지런히 움직인다"),
    (["능글", "넉살", "잇속"], "웃을 때 눈가가 접히는 넉넉한 얼굴", "늘 반쯤 웃고 있다"),
    (["여리", "겁", "순정"], "이목구비가 여린 창백한 얼굴", "눈을 자주 내리깐다"),
    (["다부", "단호", "굳"], "턱선이 뚜렷한 단단한 얼굴", "정면을 똑바로 본다"),
    (["지쳐", "냉소", "체념"], "눈 밑이 어둡고 낯빛이 흐린 얼굴", "무엇을 봐도 놀라지 않는다"),
    (["거칠", "집요", "험"], "코와 광대가 굵은 거친 얼굴", "눈을 잘 깜빡이지 않는다"),
]
STRESS_FACE = ["턱에 힘이 들어가고 목덜미가 붉어진다",
               "눈을 자주 깜빡이고 손끝이 떨린다",
               "웃음기가 사라지며 얼굴이 굳는다",
               "시선이 자꾸 문 쪽으로 흐른다",
               "말이 빨라지며 입술이 마른다"]


def _rank_key(c):
    import voices
    return voices._rank(c)


# 성격만으로는 다섯이 겹친다. 겹칠 때 골라 쓸 여벌.
FACE_POOL = [
    ("광대가 높고 눈이 깊은 얼굴", "곁눈으로 상대를 살핀다"),
    ("이마가 넓고 눈썹이 옅은 얼굴", "눈을 크게 뜨고 듣는다"),
    ("턱이 갸름하고 입이 작은 얼굴", "말할 때만 눈을 맞춘다"),
    ("눈매가 처지고 볼이 두툼한 얼굴", "늘 조금 지쳐 보인다"),
    ("코가 오뚝하고 입술이 얇은 얼굴", "표정을 잘 바꾸지 않는다"),
    ("눈썹이 짙고 눈이 큰 얼굴", "감정이 얼굴에 먼저 뜬다"),
    ("주름이 자글자글한 마른 얼굴", "눈을 가늘게 뜨고 본다"),
]


def appearance(s, c, reg, idx, used=None):
    p = c.get("profile") or {}
    per = (c.get("persona") or {}).get("personality") or ""
    age = (p.get("age") or "30대").replace(" 후반", "").replace(" 초반", "")
    sex = p.get("sex") or "남"
    face, gaze = next(((f, g) for keys, f, g in FACE_BY_TRAIT if any(k in per for k in keys)),
                      (None, None))
    used = used if used is not None else set()
    if face is None or face in used:
        # 성격이 겹치면 얼굴까지 겹친다. 여벌에서 아직 안 쓴 것을 집는다.
        for f, g in FACE_POOL[idx % len(FACE_POOL):] + FACE_POOL[:idx % len(FACE_POOL)]:
            if f not in used:
                face, gaze = f, g
                break
    used.add(face)
    hair = (HAIR_OLD if reg == "east" else HAIR_WEST if reg == "west" else HAIR_MOD).get(sex, "")
    cloth = CLOTH[reg].get(_rank_key(c), CLOTH[reg][4])
    build = next((v for k, v in BUILD.items() if k in age), "보통 체격")
    stress = STRESS_FACE[idx % len(STRESS_FACE)]
    era = (s.get("meta") or {}).get("era", "")
    ap = {
        "face": face,
        "build": build,
        "hair": hair,
        "gaze": gaze,
        "clothing": cloth,
        "resting_expression": gaze,
        "under_pressure": stress,
        "prompt_ko": (f"{age} {sex}자. {build}. {hair}. {face}. {cloth}. "
                      f"{era}의 인물. 심문받는 자리에 앉아 있다."),
    }
    ap["prompt_en"] = (
        f"portrait of a {age.replace('대','s')} "
        f"{'woman' if sex == '여' else 'man'}, {era}, "
        f"{'Korean' if reg == 'east' else 'European' if reg == 'west' else 'modern Korean'} setting, "
        f"period-accurate clothing, seated for questioning, "
        f"muted candlelit palette, painterly realism, waist-up, neutral background")
    return ap


# ── ③ 목소리 ─────────────────────────────────────────────────────────
PITCH = {"10대": "높음(+3~+5 반음)", "20대": "약간 높음(+1~+3)", "30대": "보통",
         "40대": "약간 낮음(-1~-2)", "50대": "낮음(-2~-4)", "60대": "낮고 갈라짐(-3~-5)",
         "70대": "낮고 얇음(-3~-5)"}
TEMPO_BY_HABIT = [("짧게 툭툭", "빠름(1.05~1.12배). 문장 사이가 짧다"),
                  ("길게 이어진다", "느림(0.9~0.95배). 문장이 좀처럼 끝나지 않는다"),
                  ("말끝을 자주 흐린다", "느림(0.88~0.94배). 끝이 잦아든다"),
                  ("곱씹어 되뇐", "보통. 낱말 하나를 낮게 되뇌고 한 박자 쉰다"),
                  ("한자말", "느림(0.9배). 또박또박 끊어 읽는다"),
                  ("두 번 말한다", "보통. 같은 구절을 되짚느라 늘어진다"),
                  ("감탄사", "빠름(1.05배). 앞에 군말이 붙는다"),
                  ("조사를 자주 생략", "빠름(1.1~1.15배). 성글고 급하다")]


def voice_spec(s, c, idx):
    p = c.get("profile") or {}
    per = c.get("persona") or {}
    vo = per.get("voice") or {}
    age = (p.get("age") or "30대").replace(" 후반", "").replace(" 초반", "")
    sex = p.get("sex") or "남"
    habit = vo.get("habit", "")
    tempo = next((t for k, t in TEMPO_BY_HABIT if k in habit), "보통(1.0배)")
    hint = per.get("voice_hint") or ""
    pitch = next((v for k, v in PITCH.items() if k in age), "보통")
    v = {
        "gender_age": f"{'여성' if sex == '여' else '남성'} · {age} 인상",
        "pitch": pitch,
        "tempo": tempo,
        "timbre": hint or ("맑고 가는 음색" if sex == "여" else "건조하고 낮은 음색"),
        "delivery": f"{vo.get('form','')}의 결로. {habit}",
        "breath": "문장 사이 0.3~0.6초. 정곡을 찔리면 한 박자 늦게 뗀다",
        "emotion_default": "경계 섞인 평정",
        "emotion_range": ["평정", "불안", "억울", "분노", "체념"],
        "avoid": ["과장된 연기 톤", "현대 방송 아나운서 억양", "다른 인물과 같은 높이·속도"],
    }
    v["prompt_en"] = (
        f"{'female' if sex == '여' else 'male'} voice, "
        f"{age.replace('대','s')} impression, {pitch.split('(')[0]} pitch, "
        f"{'slow' if '느림' in tempo else 'fast' if '빠름' in tempo else 'moderate'} pace, "
        f"dry restrained timbre, period drama delivery, Korean")
    return v


def apply(s):
    import voices
    reg = voices._register(s)
    fix_intro(s)
    used = set()
    for i, c in enumerate(s["cast"]):
        c["appearance"] = appearance(s, c, reg, i, used)
        c["voice_spec"] = voice_spec(s, c, i)
    return len(s["cast"])


def check(s):
    bad = []
    intro = ((s.get("bgm") or {}).get("cues") or {}).get("intro") or {}
    if not intro.get("prompt_en"):
        bad.append("인트로에 음악 프롬프트가 없다")
    faces = [(c.get("appearance") or {}).get("face") for c in s["cast"]]
    if len(set(faces)) < len(faces) - 1:
        bad.append(f"얼굴 묘사가 서로 겹친다: {len(set(faces))}/{len(faces)}가지")
    for c in s["cast"]:
        if not (c.get("appearance") or {}).get("prompt_en"):
            bad.append(f"{c['name']}: 그림 프롬프트 없음")
        if not (c.get("voice_spec") or {}).get("prompt_en"):
            bad.append(f"{c['name']}: 음성 프롬프트 없음")
    return (not bad), bad


if __name__ == "__main__":
    if "--check" in sys.argv:
        for p in sorted(glob.glob("scenarios/[0-9]*.json")):
            ok, bad = check(json.load(open(p, encoding="utf-8")))
            if not ok:
                print(f"  ❌ {os.path.basename(p):26} {'; '.join(bad[:3])}")
        print("생김새·목소리 검사 끝")
        sys.exit(0)
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        n = apply(s)
        json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        intro = ((s.get("bgm") or {}).get("cues") or {}).get("intro") or {}
        print(f"  {os.path.basename(p):26} 인물 {n}명 · 인트로 「{intro.get('mood','')}」")
