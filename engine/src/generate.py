"""
시나리오 생성기 (바이블-먼저 2단계).
  Stage 1: 상세 '바이블'(긴 소설 — 세계·인물 감정·관계·그날 전부, 진실 포함) 생성
  Stage 2: 바이블에서 게임 스키마 추출(+ cast[].bio) → verify + difficulty_gate + repair
출력: out/bible.md (풍부한 원본) + out/scenario.json (게임 스키마)

준비: pip install anthropic ; export ANTHROPIC_API_KEY=...
실행: python generate.py "흥부전" "조선"
"""
import os, sys, json, re
from llm import complete, default_model
from verify import verify, _print
from difficulty import difficulty_gate
try:
    from condition_sampler import build_conditions
except Exception:
    def build_conditions(origin): return ""

MODEL = default_model()  # MM_BACKEND(vllm/anthropic)에 따라 자동 선택
# few-shot 예시는 '검증+난이도 게이트를 모두 통과'한 시나리오 한 편을 쓴다.
#   MM_GOLDEN 으로 경로를 주면 그것을, 없으면 시연 편(91_dsl_demo)을 쓴다.
#   둘 다 없으면 few-shot 없이 돈다 — 품질은 떨어지지만 멈추지는 않는다.
def _load_golden():
    here = os.path.dirname(__file__)
    for cand in (os.environ.get("MM_GOLDEN"),
                 os.path.join(here, "scenario3.json"),
                 os.path.join(here, "..", "scenarios", "91_dsl_demo.json")):
        if cand and os.path.exists(cand):
            return json.load(open(cand, encoding="utf-8"))
    return None


GOLDEN = _load_golden()

# ---------------- Stage 1: 바이블 ----------------
BIBLE_SYS = """너는 추리소설가다. 주어진 원작 세계를 무대로, 진짜 장편소설처럼 상세한 살인사건 '바이블'을 쓴다.
반드시 아래를 풍부한 산문으로 담는다(감정·관계·과거·동기·그날의 동선까지 구체적으로):

# 세계와 배경
# 사건 — 피해자, 언제·어디서 죽었나(흉기·수법은 진실로 명시)
# 인물 인생소설 (피해자 1명 + 용의자 정확히 5명 = 총 6명) — ★한 명씩 '긴 인생소설'을 쓴다.
  각 인물마다 최소 8~12문장으로: 출생·가문·성장 환경, 인생의 전환점이 된 사건, 가족·연인·원한 관계망,
  가장 큰 욕망과 결핍, 비밀의 뿌리(왜 그 비밀을 품게 됐나), 말버릇·성격, 피해자와 얽힌 내력, 사건 당일의 심리와 동선.
  → 나중에 이 인물로 AI 용의자 에이전트를 만들어도 '모르는 것/자기모순'이 없도록, 삶의 구석까지 채운다.
  → 피해자도 반드시 긴 인생소설을 쓴다(누가 왜 그를 미워했는지 전부 드러나게).
# 진실 — 진짜 범인 1명, 어떻게·왜 죽였는가(범인만 거짓말할 수 있음)
# 장소와 단서 — ★사건 현장과 다섯 용의자의 거처를 '크라임씬'처럼 하나씩 묘사한다.
  각 장소마다: 그곳의 분위기·물건·냄새·빛 같은 시각적 특징 여러 개 + 그곳을 탐색하면 나오는 단서(관찰거리)를 배치.
  현장(피해자 사망 장소)은 특히 상세히: 시신·유류품·다잉메시지·모순의 흔적까지.
  단서에는 흉기를 좁히는 흔적, 무고자들의 알리바이 증거, 범인을 가리키는 결정적 정황을 섞는다.

중요:
- 무고자 4명 중 3명은 확실한 알리바이가 있고, 1명은 동기·기회가 짙어 가장 유력해 보이지만 '수단'이 없어 범인이 아니다(반전).
- 범인은 조용하지만 수단·동기·기회를 모두 갖췄다.
- ★지도·동선·시간의 정합: 사건 현장, 각 인물이 그 밤 어느 장소에 있었는지, 장소 사이 거리/이동시간을 명확히 정하라. 모든 알리바이·증언·범행 동선이 이 지도와 어긋나지 않아야 한다.
- ★범인의 거짓말은 '반드시 잡히게' 설계하라: 범인이 대는 거짓 알리바이(다른 장소에 있었다는 주장)는, 그 장소에 실제로 있던 다른 인물의 증언이나 지도상 이동 불가·시간 모순으로 플레이어가 교차검증해 깨뜨릴 수 있어야 한다. (예: 범인이 'A방에 있었다' 주장 → 그 밤 A방을 지킨 다른 용의자가 '그를 못 봤다')
- 등장인물은 원작 세계의 인물을 쓰고, 모자라면 그 시대에 맞게 창작한다."""

def gen_bible(origin, era):
    cond = build_conditions(origin)
    user = f'원작="{origin}", 시대="{era}". 위 지침대로 상세한 살인사건 바이블을 마크다운으로 써라.\n\n{cond}'
    return complete(BIBLE_SYS, [{"role":"user","content":user}], max_tokens=6000)

# ---------------- Stage 2: 스키마 추출 ----------------
EXTRACT_SYS = f"""너는 위 바이블(원본 시나리오)에서 '게임 스키마 JSON'을 추출한다.
아래 예시와 완전히 같은 구조로, 바이블의 사실과 어긋나지 않게 채운다. JSON만 출력.

[추가 규칙]
- ★meta.title(제목) 규칙: 흉기·트릭·결정적 단서·동기를 제목에 쓰지 마라. 제목은 시작 화면·사건 목록에 처음부터 뜬다 — 사인이 ???인데 제목이 답하면 안 된다. 무대(현장 이름)·원작의 상징·분위기까지만. 나쁜 예: '녹아 사라진 칼'(트릭 스포), '놀부의 탕약'(사인 스포), '은비녀의 밤'(흉기 스포). 좋은 예: '금단의 방', '쥐가 떠난 밤', '얼음 창고의 밤'.
- 최상위 trick : {{"name":..., "desc":...}} — 조건으로 주어진 '중심 트릭'을 이 사건이 어떻게 구현했는지 기록. 사건 전체(단서·타임라인·미수/알리바이 등)를 이 트릭 위에 설계할 것.
- ★용의자·피해자는 '원작의 등장인물 그대로' 매핑한다. 나무꾼과 선녀면 나무꾼·선녀·사슴·사냥꾼·시어머니처럼, 원작을 아는 이는 바로 알아보고 모르는 이도 나레이션으로 알게. 원작과 무관한 인물을 새로 지어내 배경만 빌리지 말 것.
- intro.narration : 8~12개 비트 배열. '옛날 옛적에~'로 시작해 ★원작 줄거리를 실제로 들려주며(원작을 모르는 플레이어도 이해되게), 그 이야기 속에서 용의자 5명을 한 명씩 원작의 배역으로 간접 소개한다(누가 선녀·나무꾼·사슴인지 자연히 드러나게). 평온·화사하게 흐르다 마지막에 살인 반전. 각 비트 {{beat, mood, focus(인물 id/world/victim), scene, text}}. 전체 합쳐 20~30초(약 550~750자), 원작 서사가 담기게 넉넉히. ★화면 제약: text는 **한 문장을 50자 이내**로 쓴다(공백 포함). 두 문장을 이어 붙여도 96자를 넘지 않게 짧게 끊어 쓴다 — 글자창이 96자에서 꽉 차 그 뒤가 잘린다. 쉼표로 길게 잇지 말고 마침표로 끊어라.
  ★살인은 '원작 진행 중 한 시점'에 끼어든다. 그 지점을 정하고(예: 선녀와 나무꾼이면 날개옷을 훔치기 전 / 아이를 낳기 전 / 하늘로 돌아가기 전 중 하나), 나레이션은 딱 그 지점까지의 원작만 들려준다. 그 이후의 원작 전개(결말)는 말하지 않는다 — 사건이 원작의 흐름을 거기서 끊는 것이므로.
- death.scene_description(첫 시체 화면 묘사) + death.scene_inspection([관찰 포인트]) : 크라임씬처럼 시신·배경을 살필 거리.
- clue_graph에 channel "crime_scene" 허용(첫 시체 화면에서 발견되는 단서, reveal_round 1). 가능하면 medium "다잉메시지"를 하나 두되, 중심 트릭에 맞게 설계 — 진범을 암시하거나(정통), 미수자/엉뚱한 이를 가리키는 '함정'(이중미수·변장 트릭)으로. 함정이면 weight="red_herring".
- cast[].bio : 그 인물이 '스스로 밝혀도 되는' 배경·감정·관계만 4~8문장으로 옮긴다(돌발 질문용, 요약).
- ★cast[].life_story : 바이블의 그 인물 '긴 인생소설'을 거의 그대로 옮긴다(최소 8문장·300자 이상). 출생·성장·전환점·관계·욕망·비밀의 뿌리·말버릇·사건 당일 심리까지. AI 에이전트가 어떤 돌발 질문에도 답할 '삶의 사실 창고'. ⚠️ 범인의 life_story엔 범행 자백·살해 진실 금지(커버스토리 범위 내에서 최대한 상세). 무고자의 '비밀 실토'도 여기 직접 쓰지 말 것(그건 pressure_points로).
- ★victim : {{name, role, bio(피해자 긴 인생소설 300자 이상 — 누가 왜 그를 미워했는지 드러나게)}}.
- ★map.places[].features : 그 장소를 탐색할 때 보이는 특징·물건·연출을 2~4개(문자열 배열)로. 크라임씬처럼 시각적이고 구체적으로. 일부는 단서로 이어지고 일부는 분위기/레드헤링. 현장(P?=death.place)은 death.scene_inspection과 함께 가장 풍부하게.
- ★모든 장소가 탐색거리를 갖도록: clue_graph의 location 채널 단서로 여러 장소를 덮되, 단서 없는 장소는 features만으로도 살필 거리가 있게.
- cast[].pressure_points : [{{trigger:[정곡 키워드들], reveals:"찔렸을 때 실토하는 대사", unlocks:비밀유형}}] — 플레이어가 그 키워드를 짚으면 비밀을 털어놓게. 범인도 비밀(레드헤링)만 실토하고 살인은 절대 인정하지 않는다.
  ★ 범인의 bio에는 범행 사실·자백을 절대 넣지 말 것(그 진실은 solution·lies에만). 무고자의 비밀도 bio엔 넣지 않는다.
- cast[].profile : {{name, age, sex, relation(피해자와의 관계), status(신분)}} — 첫 라운드 프로필 카드용. 원작에서 알 수 없는 필드는 넣지 말 것(없는 건 제외).
- cast[].mmo : 범인만 means·motive·opportunity 전부 true. 무고자는 각자 한 다리 false(가짜 유력자는 means=false).
- 지도·동선 정합(검증기 강제): opportunity=false인 자와 '알리바이로 배제되는 자'는 timeline상 사망 시각에 현장(death.place)에 있으면 안 된다. 범인은 사망 시각에 현장에 있고 opportunity=true. 인접 시간대 이동은 지도 거리(max_move_per_slot) 안이어야 한다.
- 범인 lies의 거짓 알리바이 장소는, 그 밤 다른 용의자가 실제로 있던 장소(그가 목격을 부인할 수 있는 곳)로 두어 교차검증으로 깨지게 하라.
- clue_graph : 무고자 4명을 소거하되, 결정적 단서(decisive)는 라운드3에 범인 지목 + 가짜 유력자 배제.
- surface엔 정답을 직접 쓰지 말 것(관찰만). implies에 숨은 논리.
- ★단서 문체는 '검안서·감식 소견체'로 구체적 사실만 적는다. 감성 묘사·소설투 금지.
  · 나쁨(소설투): "방바닥엔 토한 자국과 함께 쓴 냄새가 두 겹으로 배어 있었다."
  · 좋음(검안서): "【검안】 위 내용물서 알칼로이드 양성, 구강 잔사 검출. 외상 없음. 사인: 급성 음독."
  · 좋음(감식): "【현장】 술잔 2점 중 1점에만 잔사 → 대작자 존재. 문 빗장 안쪽, 옆방 문틀에 긁힘."
  검시 소견은 측정·상태·시각·위치 같은 검증 가능한 사실로(창구경 mm, 시반 분포, 필압, 지문 유무, 사망추정 시각 등).
  실제 사건처럼 '구체적 메커니즘'을 축으로: 알리바이는 이동 경로·시각의 모순으로, 위장은 물리 흔적(혈흔 도말/충격흔 부재/건조도)으로 깨지게.
- choices.culprit(5), choices.weapon(5). 동기는 자유서술(solution.motive_keywords 제공).
- ★디자인팀 인계 필드(반드시 채움):
  · background.setting_raw : {{era(시대), location(구체 장소·고을), culture(문화권 — 예: "한국 전통", "한국 설화", "중화권", "서구". 서구화된 이미지·음악 모델을 위해 비서구권이면 반드시 명시)}} + background.atmosphere(현장 분위기 한 줄).
  · adapted_story : {{tone(초반 밝은 분위기 톤), tone_shift(살인 이후 반전 톤), palette(이미지 색감 힌트: 초반 밝음→사건후 어둠)}}. → BGM은 tone(초기)·tone_shift(사건후) 두 상태로 생성됨.
  · map.places[].desc : 각 장소를 이미지 생성 프롬프트로 쓸 수 있게 시대·문화가 드러나는 한 줄 시각 묘사.

[스키마 예시]
{json.dumps(GOLDEN, ensure_ascii=False)}"""

def extract_json(text):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    a, b = text.find("{"), text.rfind("}")
    return json.loads(text[a:b+1])

def extract_schema(bible, max_repair=3):
    msgs = [{"role":"user","content":f"[바이블]\n{bible}\n\n위 바이블에서 게임 스키마 JSON을 추출하라."}]
    sc = None
    for attempt in range(max_repair + 1):
        raw = complete(EXTRACT_SYS, msgs, max_tokens=8000)
        try:
            sc = extract_json(raw)
        except Exception as e:
            msgs += [{"role":"assistant","content":raw},{"role":"user","content":f"JSON 파싱 실패({e}). 순수 JSON만."}]
            continue
        ok, report = verify(sc); gok, greasons = difficulty_gate(sc)
        print(f"\n[추출 시도 {attempt+1}] 검증 {'PASS' if ok else 'FAIL'} | 난이도 {'PASS' if gok else 'FAIL'}")
        _print(report)
        for rr in greasons: print("  [난이도]", rr)
        if ok and gok:
            return sc
        fails = "\n".join(f"- {rule}: {msg}" for rule,p,msg in report if not p)
        if not gok: fails += "\n[난이도] " + "; ".join(greasons)
        msgs += [{"role":"assistant","content":json.dumps(sc,ensure_ascii=False)},
                 {"role":"user","content":f"바이블과 정합을 유지하며 아래를 고쳐 전체 JSON 재출력:\n{fails}"}]
    return sc

# ---------------- Stage 3: 보드게임 구조로 마무리 ----------------
def finish(sc, path):
    """LLM이 뽑아낸 스키마를 **실제로 플레이 가능한 구조**로 올린다.

    Stage 2까지는 옛 스키마다(비밀 하나, 짐 없음, 페이즈 없음).
    이 상태로 심문을 돌리면 아무도 입을 열지 않아 판이 멈춘다.
    아래 다섯 걸음이 그것을 메운다 — 순서가 중요하다."""
    import josa_fix, upgrade_schema, relate, relweb, voices, make_novel
    steps = []
    sc = josa_fix.walk(sc)                              # ① 조사·문구 정리
    upgrade_schema.upgrade(sc); steps.append("보드게임 구조(v2)")
    sc = josa_fix.walk(sc)                              # ③ 새로 생긴 글도 정리
    if not sc.get("relation_web"):
        sc["relation_web"] = relweb.build_web(sc)
    relate.rewrite(sc); steps.append("관계·서사")
    voices.assign(sc); steps.append("말투")
    json.dump(sc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    novel = path.replace(".json", "_novel.md")
    open(novel, "w", encoding="utf-8").write(make_novel.build(sc))
    print("   보강:", " · ".join(steps))
    print("   저장:", path, "/", novel)
    return sc


def gate(sc):
    """만들었으면 반드시 검사한다. 통과 못 하면 게임이 성립하지 않는다."""
    from verify_v2 import verify_v2
    from relation_lint import lint as rel_lint
    import voices as _v
    rows = []
    ok1, r1 = verify(sc);            rows.append(("논리(verify)", ok1, r1))
    ok2, r2 = verify_v2(sc);         rows.append(("구조(verify_v2)", ok2, r2))
    ok3, r3 = rel_lint(sc);          rows.append(("관계·서사", ok3, r3))
    ok4, r4 = _v.check(sc);          rows.append(("말투", ok4, r4))
    allok = True
    for name, ok, rep in rows:
        bad = [x for x in rep if (isinstance(x, tuple) and not x[1])] if rep and isinstance(rep[0], tuple) else rep
        print(f"   {'✅' if ok else '❌'} {name}" + (f" — 미달 {len(bad)}" if not ok else ""))
        if not ok:
            allok = False
            for b in (bad or [])[:5]:
                print("      ·", b[0] if isinstance(b, tuple) else b)
    return allok


if __name__ == "__main__":
    origin = sys.argv[1] if len(sys.argv) > 1 else "흥부전"
    era    = sys.argv[2] if len(sys.argv) > 2 else "조선"
    slug   = sys.argv[3] if len(sys.argv) > 3 else re.sub(r"\s+", "", origin)
    os.makedirs("scenarios", exist_ok=True)
    print("=== Stage 1: 바이블 생성 ===")
    bible = gen_bible(origin, era)
    open(f"scenarios/{slug}_bible.md","w",encoding="utf-8").write(bible)
    print(f"저장: out/{slug}_bible.md ({len(bible):,}자)")
    print("=== Stage 2: 스키마 추출 ===")
    sc = extract_schema(bible)
    path = f"scenarios/{slug}.json"
    json.dump(sc, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print("=== Stage 3: 보드게임 구조로 마무리 ===")
    sc = finish(sc, path)
    print("=== Stage 4: 검사 ===")
    ok = gate(sc)
    print("\n" + ("✅ 완성 — 바로 플레이할 수 있습니다." if ok else
                  "⚠️ 미달 항목이 있습니다. 위 목록을 보고 손보세요."))
