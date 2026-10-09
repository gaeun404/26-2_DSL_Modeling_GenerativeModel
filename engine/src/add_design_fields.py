"""
디자인팀 인계 필드 추가 마이그레이션.
- background.setting_raw.{era,location,culture} + background.atmosphere   → BGM/이미지 '월드 레퍼런스'
- adapted_story.{tone,tone_shift,palette}                                  → BGM 조건(초기/사건후) + 이미지 팔레트
- map.places[].desc                                                        → 장소별 배경 이미지 생성 프롬프트

비서구권/동양 문화 조건을 명시(디자인 문서 강조: 서구화된 모델이라 동양풍이 약함).
사용: python add_design_fields.py            # 대상 파일 전체 인플레이스 갱신
"""
import json, glob, os

# ---- 대표 시나리오는 손으로 풍부하게(이미지·BGM 프롬프트로 바로 쓸 수준) ----
RICH = {
  "D_심청전": {
    "background": {
      "setting_raw": {"era": "조선 후기", "location": "황해도 도화동 — 눈먼 아비와 딸이 사는 가난한 갯마을",
                      "culture": "한국 전통(조선)"},
      "atmosphere": "공양미와 효(孝)의 정한이 흐르는 궁핍한 어촌. 그 이면엔 사람 목숨값을 흥정하는 어둠"},
    "adapted_story": {
      "tone": "애잔하고 따뜻한 조선 효(孝) 설화",
      "tone_shift": "효녀 이야기가 무너지고 음습한 이중 독살극으로 반전",
      "palette": "명도 높은 수묵담채(볕 든 갯마을) → 사건 후 저채도 청록·먹빛"},
    "places": {
      "P1": "희미한 등잔 아래 약탕기와 흐트러진 이부자리가 놓인 뺑덕의 좁은 안방, 문틈으로 스미는 밤바람",
      "P2": "낡은 서안과 붓·경전이 정갈한 선비의 사랑방, 벽에 걸린 빛바랜 족자",
      "P3": "탁주 냄새와 등불이 번지는 갯마을 주막, 젖은 나무 탁자와 손때 묻은 사기그릇",
      "P4": "돌담을 맞댄 이웃집 마당, 빨랫줄과 장독대, 켜둔 호롱불 하나",
      "P5": "행랑채의 어두운 봉당, 짚단과 농기구가 쌓인 흙바닥, 그을린 부뚜막"}},
  "E_신데렐라": {
    "background": {
      "setting_raw": {"era": "17세기 서양 왕국(바로크)", "location": "왕궁 별관 — 무도회가 열린 대저택",
                      "culture": "서구(유럽 바로크 궁정)"},
      "atmosphere": "촛불과 현악이 흐르는 무도회의 화려함, 잠긴 문 뒤의 서늘한 밀실"},
    "adapted_story": {
      "tone": "반짝이는 서양 궁정 동화",
      "tone_shift": "유리구두의 낭만이 깨지고 잠긴 방의 밀실 살인으로 반전",
      "palette": "금박·샴페인빛 하이라이트 → 사건 후 검푸른 그림자와 촛농빛"},
    "places": {
      "P1": "거울과 재단용 마네킹, 잠긴 문이 있는 좁은 의상실, 바닥에 흩뿌려진 시침바늘",
      "P2": "샹들리에가 빛나는 대무도회장, 대리석 바닥과 회전하는 드레스 자락",
      "P3": "달빛 어린 기하학 정원, 다듬은 회양목과 분수, 젖은 자갈길",
      "P4": "구리 냄비가 걸린 넓은 주방, 화덕의 잔불과 밀가루 먼지",
      "P5": "짚 냄새 나는 마구간, 등불에 어른대는 말들의 그림자와 마차 바퀴"}},
  "F_춘향전": {
    "background": {
      "setting_raw": {"era": "조선 후기", "location": "남원 관아(동헌) — 사또가 다스리는 고을 관청",
                      "culture": "한국 전통(조선)"},
      "atmosphere": "정절과 권력이 부딪는 관아의 밤, 형틀과 등롱이 드리운 긴 그림자"},
    "adapted_story": {
      "tone": "애절한 조선 정절(貞節) 로맨스",
      "tone_shift": "사랑 이야기가 갈라지고 알리바이 조작의 살인극으로 반전",
      "palette": "단청빛·홍등의 온기 → 사건 후 먹빛 처마 그림자와 핏빛 점정"},
    "places": {
      "P1": "대청마루와 형틀·문서가 놓인 관아의 동헌, 처마 밑 걸린 등롱",
      "P2": "차가운 돌바닥과 나무 창살의 옥사, 벽에 스민 습기와 희미한 횃불",
      "P3": "길손이 묵는 객사의 방, 등잔과 개켜둔 이불, 마당의 우물",
      "P4": "관노들이 드나드는 관노청, 멍석과 농기구, 그을린 부엌",
      "P5": "향단의 아담한 처소, 반짇고리와 접은 치마저고리, 창호에 비친 달빛"}},
  "별주부전": {
    "background": {
      "setting_raw": {"era": "설화 속 시대(용궁)", "location": "동해 용궁 — 용왕이 다스리는 물속 궁전",
                      "culture": "한국 설화(용궁 판타지)"},
      "atmosphere": "산호와 진주로 빛나는 용궁의 위엄, 약재실에 감도는 비릿한 독기"},
    "adapted_story": {
      "tone": "신비롭고 화사한 한국 설화",
      "tone_shift": "충(忠)의 우화가 뒤집혀 복어독 독살 사건으로 반전",
      "palette": "청록·자개빛 물그림자 → 사건 후 검푸른 심해와 독기의 보랏빛"},
    "places": {
      "P1": "약장과 약탕기, 말린 약재가 걸린 용궁 약재실, 수면 아래 흔들리는 빛",
      "P2": "산호 기둥과 진주 발이 드리운 용왕의 대전",
      "P3": "물살이 드나드는 수문, 이끼 낀 돌문과 소용돌이",
      "P4": "해초와 조개꽃이 어우러진 용궁 후원의 물정원",
      "P5": "차가운 돌벽의 옥사, 조개껍질 창살과 희미한 발광충 불빛"}},
  "scenario3": {  # 별주부전 심화판과 동일 세계
    "background": {
      "setting_raw": {"era": "설화 속 시대(용궁)", "location": "동해 용궁 — 용왕의 물속 궁전",
                      "culture": "한국 설화(용궁 판타지)"},
      "atmosphere": "자개빛 용궁의 위엄과 약재실에 감도는 복어독의 비린 그림자"},
    "adapted_story": {
      "tone": "신비롭고 화사한 한국 설화",
      "tone_shift": "충의 우화가 무너지고 복어독 독살극으로 반전",
      "palette": "청록·자개빛 → 사건 후 심해의 검푸름과 독의 보랏빛"},
    "places": {
      "P1": "약장과 약탕기가 늘어선 용궁 약재실, 말린 복어와 약재",
      "P2": "산호 기둥의 대전", "P3": "소용돌이치는 수문",
      "P4": "해초 어린 후원", "P5": "조개껍질 창살의 옥사"}},
}

# 문화 추정(비서구권/서구 구분) — 이미지팀 '월드 레퍼런스' 조건
def guess_culture(era, origin):
    e = (era or "") + (origin or "")
    if any(k in e for k in ["조선", "고려", "삼국", "신라", "백제", "고구려", "한국"]): return "한국 전통"
    if "용궁" in e or "설화" in e: return "한국 설화"
    if any(k in e for k in ["서양", "왕국", "유럽", "궁정"]): return "서구"
    if any(k in e for k in ["중국", "당", "명", "청"]): return "중화권"
    if any(k in e for k in ["일본", "에도"]): return "일본"
    return "동아시아 전통"

def mood_tone(narration):
    if not narration: return ("밝고 평온한 이야기", "살인 이후 어둡게 반전")
    first = narration[0].get("mood", "평온"); last = narration[-1].get("mood", "충격")
    return (f"{first}한 분위기의 동화", f"{last}으로 치닫는 반전 추리극")

def derive(s, key):
    meta = s.get("meta", {}); era = meta.get("era", ""); origin = meta.get("origin", "")
    tone, shift = mood_tone(s.get("intro", {}).get("narration", []))
    return {
      "background": {
        "setting_raw": {"era": era or "설화 속 시대",
                        "location": meta.get("title") or origin or "이야기 속 마을",
                        "culture": guess_culture(era, origin)},
        "atmosphere": f"{origin}의 세계를 무대로 한 사건 현장"},
      "adapted_story": {"tone": tone, "tone_shift": shift,
                        "palette": "초반 명도 높은 색조 → 사건 후 저채도 어둠"},
      "places": {}}

def apply(path):
    s = json.load(open(path, encoding="utf-8"))
    key = os.path.splitext(os.path.basename(path))[0]
    data = RICH.get(key) or derive(s, key)
    s["background"] = data["background"]
    s["adapted_story"] = data["adapted_story"]
    pdesc = data.get("places", {})
    for p in s.get("map", {}).get("places", []):
        p["desc"] = pdesc.get(p["id"]) or f"{p['name']} — {s['meta'].get('era','')}풍 배경"
    json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    rich = "RICH" if key in RICH else "derived"
    print(f"  ✓ {path:28} [{rich}]  tone='{s['adapted_story']['tone']}'  places={len(s['map']['places'])}")

if __name__ == "__main__":
    targets = glob.glob("scenarios/*.json") + ["scenario3.json", "golden_sample.json", "scenario2.json"]
    for t in sorted(set(targets)):
        try: apply(t)
        except Exception as e: print(f"  ✗ {t}: {e}")
