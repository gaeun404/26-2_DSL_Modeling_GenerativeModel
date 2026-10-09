# -*- coding: utf-8 -*-
"""
add_voice.py — 음성(TTS) 스펙 주입: 나레이션 목소리 + 용의자 5인 목소리.

현재 문제
  · 나레이션 목소리 사양이 아예 없음 → 아무 목소리나 붙게 됨
  · 인물은 voice_hint 한 줄뿐이라(예: "굵고 탁한 중년 음성") TTS 파라미터로 못 씀

해결
  s["voice"] = {
    "narrator": {...},                  # 크라임씬 예고편 톤: 긴장감 도는 중저음, 느리고 눌러 말하는
    "direction": {...},                 # 공통 연출 규칙(믹싱·호흡·BGM과의 관계)
    "cast": { C1:{...}, ... }           # persona/profile에서 파생한 인물별 음성 사양
  }
각 항목: gender, age_band, pitch, tempo(속도), timbre(음색), delivery(어투),
        emotion_default, emotion_range, reference_en(TTS 프롬프트), ssml_hint

나레이션은 비트별 감정이 다르므로(평온→충격) beat_direction도 생성한다.
사용: python add_voice.py
"""
import json, glob, sys, re

# ── 나레이션: '크라임씬' 예고 나레이션 톤 ────────────────────────────
def narrator_spec(s):
    ad=s.get("adapted_story",{}); sr=s["background"]["setting_raw"]
    return {
      "role":"사건 나레이터(진행자)",
      "reference":"크라임씬류 범죄추리 예능의 오프닝 나레이션 — 낮고 눌러 말하며 긴장을 쌓는 목소리",
      "gender":"남성(중저음) 기본 / 여성 대체 시 알토 이하",
      "age_band":"40~50대 인상",
      "pitch":"낮음(-3~-5 반음). 흉성 중심, 울림 있는 저역",
      "tempo":"느림(0.85~0.92배). 문장 끝을 서두르지 않고 눌러 맺음",
      "timbre":"약간의 허스키·건조함. 과한 미성/밝은 음색 금지",
      "delivery":"담담하게 시작해 점층적으로 조여 감. 속삭이듯 낮추는 구간과 또렷이 못 박는 구간을 교대. "
                 "감정을 '연기'하기보다 사실을 무겁게 진술하는 톤",
      "breath":"문장 사이 0.4~0.8초 여백. 반전 직전엔 1.2초 이상 정적",
      "emotion_default":"차분한 긴장(suspenseful, restrained)",
      "emotion_range":["고요","호기심","의심","불길함","충격","단호"],
      "avoid":["밝고 경쾌한 낭독","동화 구연체","과장된 절규","빠른 속사포"],
      "reference_en":("Korean male narrator, deep chest voice, low pitch, slow deliberate pace, "
                      "dry husky timbre, restrained suspense — like a true-crime documentary or "
                      "a crime-mystery TV show cold open. Calm but tightening; never cheerful. "
                      f"Setting: {sr.get('era','')}, {sr.get('location','')}. Tone: {ad.get('tone','')}"),
      "ssml_hint":"<prosody rate='0.88' pitch='-3st'> … </prosody>, 반전 문장 앞 <break time='1.2s'/>",
      "mix":"BGM intro 큐 위 -6dB, 나레이션 중 BGM 중역대(200Hz~2kHz) 살짝 덕킹"
    }

# 비트 mood → 나레이션 연출
BEAT_DIR={
 "평온":("담담하고 낮게, 옛이야기를 들려주듯","rate 0.88 / pitch -3st"),
 "고요":("숨을 죽이고 더 낮게","rate 0.84 / pitch -4st"),
 "스산":("건조하게, 바람 소리처럼 흘리며","rate 0.86 / pitch -4st"),
 "음습":("탁하게 눌러, 습기 머금은 저역","rate 0.84 / pitch -5st"),
 "음침":("어둡게 깔며, 자음을 뭉개듯","rate 0.85 / pitch -5st"),
 "애처":("한 톤 낮추되 온기를 남겨","rate 0.86 / pitch -3st"),
 "애절":("호흡을 길게, 문장 끝을 떨구며","rate 0.84 / pitch -3st"),
 "애잔":("여리게, 여백을 길게","rate 0.85 / pitch -3st"),
 "비장":("단단하게 못 박듯","rate 0.90 / pitch -4st"),
 "흥미":("살짝 올려 호기심을 얹어","rate 0.92 / pitch -2st"),
 "기이":("음정을 평평하게, 기묘한 무표정","rate 0.86 / pitch -4st"),
 "신비":("멀리서 들리듯 옅게","rate 0.86 / pitch -3st"),
 "의미심장":("한 박 늦게 시작해 뜻을 심으며","rate 0.86 / pitch -4st"),
 "불안":("잘게 끊어, 조바심 나게","rate 0.94 / pitch -3st"),
 "탐욕":("느물거리듯 낮게","rate 0.88 / pitch -4st"),
 "교활":("입꼬리 올린 듯한 저음","rate 0.88 / pitch -4st"),
 "인색":("메마르게, 셈하듯 또박또박","rate 0.88 / pitch -4st"),
 "거칠":("거칠게 긁으며","rate 0.90 / pitch -5st"),
 "무기력":("힘 빠진 저역으로 흘리며","rate 0.82 / pitch -4st"),
 "비참":("무겁게 가라앉혀","rate 0.82 / pitch -5st"),
 "비굴":("낮게 사리며","rate 0.88 / pitch -3st"),
 "원한":("이 악문 듯 억눌러","rate 0.86 / pitch -5st"),
 "차가움":("서늘하게, 감정 없이","rate 0.86 / pitch -4st"),
 "몽환":("아득하게 번지듯","rate 0.84 / pitch -3st"),
 "슬픔":("낮고 느리게, 끝을 떨구며","rate 0.82 / pitch -3st"),
 "장엄":("울림을 크게, 경건하게","rate 0.84 / pitch -5st"),
 "동화":("이야기하듯 부드럽게(단, 밝지 않게)","rate 0.90 / pitch -2st"),
 "충격":("한 박 정적 뒤 또렷하고 단호하게 못 박음","rate 0.80 / pitch -5st, 앞에 break 1.2s"),
}
def beat_directions(s):
    out=[]
    for b in s.get("intro",{}).get("narration",[]):
        mood=b.get("mood","")
        d,pr=BEAT_DIR.get(mood, ("담담하게 낮은 톤 유지","rate 0.88 / pitch -3st"))
        out.append({"beat":b.get("beat"),"mood":mood,"direction":d,"prosody":pr,
                    "pause_before":"1.2s" if mood=="충격" else "0.5s"})
    return out

# ── 인물 음성: profile(나이·성별) + persona(성격·말투·voice_hint)에서 파생 ──
PERSONA_VOICE=[
 (["호방","의로","활기","당당"], dict(pitch="중저", tempo="보통~빠름", delivery="시원시원하게 뱉되 여유가 있음",
                                 emo="여유·자신감", en="confident, hearty, open-throated")),
 (["능글","넉살","익살","수다"], dict(pitch="중", tempo="빠름", delivery="말끝을 굴리며 붙임성 있게",
                                 emo="능청·너스레", en="smooth-talking, playful, slightly oily")),
 (["여리","순정","곱","가련","지쳐"], dict(pitch="높음", tempo="느림", delivery="숨이 얕고 문장이 자주 끊김",
                                 emo="위축·애처로움", en="soft, breathy, fragile, trailing off")),
 (["차갑","표독","신경질","깐깐","위압","고압"], dict(pitch="중", tempo="보통", delivery="자음을 또렷이 끊어 내리누름",
                                 emo="냉담·경계", en="cold, clipped, controlled, commanding")),
 (["음침","음험","무뚝뚝","서늘","교활"], dict(pitch="낮음", tempo="느림", delivery="말수 적고 낮게 깔며, 사이가 길다",
                                 emo="음침·경계", en="dark, low, sparse, guarded")),
 (["겁","비굴","눈치","움츠","소심","방어"], dict(pitch="중고", tempo="빠름", delivery="더듬거나 말끝을 흐리고 자주 사과",
                                 emo="불안·비굴", en="nervous, stammering, ingratiating")),
 (["수수께끼","신비","고요","기이"], dict(pitch="중", tempo="느림", delivery="감정을 싣지 않고 평평하게",
                                 emo="무표정·불가해", en="flat affect, uncanny calm, measured")),
 (["계산","셈","잇속","약삭"], dict(pitch="중", tempo="보통~빠름", delivery="숫자를 세듯 또박또박",
                                 emo="타산적", en="calculating, precise, transactional")),
]
def persona_voice(c):
    blob=(c.get("persona",{}).get("personality","")+" "+c.get("persona",{}).get("speech_style",""))
    for keys,d in PERSONA_VOICE:
        if any(k in blob for k in keys): return d
    return dict(pitch="중", tempo="보통", delivery="담담하게", emo="중립", en="neutral, grounded")

AGE_EN={"10대":"teenage","10대 후반":"late teens","20대":"young adult (20s)","30대":"adult (30s)",
        "40대":"middle-aged (40s)","50대":"older adult (50s)","불명":"ageless"}
def cast_voice(s):
    out={}
    for c in s["cast"]:
        pr=c.get("profile",{}); pe=c.get("persona",{})
        pv=persona_voice(c)
        sex=pr.get("sex","남"); age=pr.get("age","30대")
        gen="female" if sex=="여" else "male"
        out[c["id"]]={
          "character":c["name"],
          "gender":"여성" if sex=="여" else "남성",
          "age_band":age,
          "pitch":pv["pitch"], "tempo":pv["tempo"], "timbre":pe.get("voice_hint",""),
          "delivery":f"{pv['delivery']} / 말투: {pe.get('speech_style','')}",
          "emotion_default":pv["emo"],
          "emotion_range":["평상(부인)","동요(정곡 찔림)","실토(비밀 노출)",
                            "붕괴(자백)" if c.get("is_culprit") else "억울함(항변)"],
          "pressure_shift":("압박이 커질수록 말이 느려지고 사이가 길어짐, 목소리 톤은 낮아짐"
                            if c.get("is_culprit") else
                            "압박이 커질수록 말이 빨라지고 톤이 올라감(억울함)"),
          "reference_en":(f"Korean {gen} voice, {AGE_EN.get(age,'adult')}, {pv['en']}, "
                          f"timbre: {pe.get('voice_hint','')}. Period drama (sageuk) diction, "
                          f"speech style: {pe.get('speech_style','')}. Not modern casual."),
          "sample_line":(pe.get("example_lines") or [pe.get("example_line","")])[0],
          "ssml_hint":("<prosody rate='0.95'>…</prosody>, 실토 구간은 rate 0.85 + 앞 break 0.6s"),
          "tts_note":"용의자별로 반드시 다른 보이스 ID 배정(같은 목소리 재사용 금지)"
        }
    return out

def build_voice(s):
    return {
      "narrator":narrator_spec(s),
      "narration_beats":beat_directions(s),
      "cast":cast_voice(s),
      "direction":{
        "consistency":"한 시나리오 안에서 같은 인물은 항상 같은 보이스 ID·파라미터 사용",
        "distinctness":"용의자 5인은 성별·연령대·피치·속도가 서로 겹치지 않게 배정",
        "with_bgm":"대사 재생 중 BGM -6dB 덕킹. 나레이션 구간엔 intro 큐만 남기고 이벤트 스팅어 금지",
        "language":"한국어. 시대극 어투 유지(현대 구어·외래어 금지)",
        "latency":"심문 응답은 스트리밍 TTS 권장(첫 소리 0.5초 이내)"
      }
    }

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/[0-9]*.json"
    for p in sorted(glob.glob(arg)):
        s=json.load(open(p,encoding="utf-8"))
        s["voice"]=build_voice(s)
        json.dump(s,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        v=s["voice"]
        kinds={c["pitch"]+"/"+c["tempo"] for c in v["cast"].values()}
        print(f"  🎙 {p.split('/')[-1]:26} 나레이터 1 + 인물 {len(v['cast'])} · 비트연출 {len(v['narration_beats'])} · 음역분화 {len(kinds)}종")
    print("\n나레이션(크라임씬 톤 중저음)·인물별 TTS 사양 주입 완료")
