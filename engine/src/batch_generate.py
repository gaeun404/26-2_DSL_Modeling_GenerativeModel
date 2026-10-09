# -*- coding: utf-8 -*-
"""
커버리지 기반 대량 생성 러너 — 100~300편을 원작×트릭×범인위치가 고르게 섞이도록 뽑는다.
각 편: 바이블 생성 → 스키마 추출(verify + difficulty_gate + repair) → 통과분만 out/gen/ 저장.

무료 경로: dsl04 GPU vLLM(OpenAI 호환)로 LLM 백엔드를 잡고 이 스크립트를 돌린다.
  export MM_BACKEND=vllm MM_MODEL=Qwen/Qwen2.5-72B-Instruct MM_BASE_URL=http://localhost:8000/v1
  python batch_generate.py 150            # 150편 목표

계획만 보기(LLM 호출 없음):
  python batch_generate.py 150 --plan

산출:
  out/gen/<원작>__<트릭>__<범인>.json  (통과분)
  out/gen/manifest.csv                  (원작·트릭·범인·흉기·문화)
  out/gen/skipped.log                   (실패 사유)
"""
import os, sys, json, csv, itertools, random, traceback
from collections import Counter

HERE = os.path.dirname(__file__)
random.seed(20260815)  # 재현성(샌드박스는 Date/random 이슈 없음: 로컬 실행 전제)

def load_origins():
    return json.load(open(os.path.join(HERE, "origins.json"), encoding="utf-8"))["origins"]

def load_tricks():
    return json.load(open(os.path.join(HERE, "trick_bank.json"), encoding="utf-8"))["tricks"]

def build_plan(target):
    """원작×트릭을 라운드로빈으로 섞고, 범인 위치 C1~C5를 순환 배정한 작업 목록."""
    origins = load_origins(); tricks = load_tricks()
    random.shuffle(origins)
    plan = []
    ti = 0; ci = 0
    culprit_cycle = ["C1", "C2", "C3", "C4", "C5"]
    # 원작을 돌면서 트릭·범인위치를 순환 → 세 축이 고르게 섞임
    for rnd in range(target * 3):  # 넉넉히(실패분 감안), 실제로는 target 채우면 멈춤
        o = origins[rnd % len(origins)]
        tk = tricks[ti % len(tricks)]; ti += 1
        cul = culprit_cycle[ci % 5]; ci += 1
        plan.append({"origin": o["origin"], "era": o["era"], "culture": o.get("culture", ""),
                     "trick_id": tk["id"], "trick_name": tk["name"], "culprit": cul})
    return plan

def print_plan(plan, target):
    print(f"=== 생성 계획 (목표 {target}편, 시도 슬롯 {len(plan)}개) ===")
    print("원작 커버리지 :", dict(Counter(p["origin"] for p in plan[:target*2]).most_common(8)), "...")
    print("트릭 커버리지 :", dict(Counter(p["trick_name"] for p in plan[:target*2])))
    print("범인위치 분포 :", dict(Counter(p["culprit"] for p in plan[:target*2])))
    print("문화권 분포   :", dict(Counter(p["culture"] for p in plan[:target*2])))
    print("\n예시 20슬롯:")
    for p in plan[:20]:
        print(f"  {p['origin']:12} | {p['trick_name']:12} | 범인 {p['culprit']} | {p['culture']}")

def run(target, plan):
    from generate import gen_bible, extract_schema
    from verify import verify
    from difficulty import difficulty_gate

    outdir = os.path.join(HERE, "scenarios", "gen"); os.makedirs(outdir, exist_ok=True)
    manifest = os.path.join(outdir, "manifest.csv")
    skiplog = open(os.path.join(outdir, "skipped.log"), "a", encoding="utf-8")
    mf = open(manifest, "a", newline="", encoding="utf-8"); mw = csv.writer(mf)
    if os.path.getsize(manifest) == 0:
        mw.writerow(["file", "origin", "trick", "culprit", "weapon", "culture"])

    accepted = 0; tried = 0
    seen_combo = Counter()
    for p in plan:
        if accepted >= target:
            break
        combo = (p["origin"], p["trick_id"])
        if seen_combo[combo] >= 2:   # 같은 원작·트릭 최대 2편(다양성)
            continue
        seen_combo[combo] += 1
        tried += 1
        os.environ["MM_FORCE_TRICK"] = p["trick_id"]
        os.environ["MM_CULPRIT_HINT"] = p["culprit"]
        tag = f"{p['origin']}__{p['trick_id']}__{p['culprit']}"
        try:
            bible = gen_bible(p["origin"], p["era"])
            sc = extract_schema(bible, max_repair=3)
            if sc is None:
                skiplog.write(f"[추출실패] {tag}\n"); continue
            # 문화 필드 보정(모델이 빠뜨렸을 때)
            sc.setdefault("background", {}).setdefault("setting_raw", {}).setdefault("culture", p["culture"])
            ok = verify(sc)[0]; gok = difficulty_gate(sc)[0]
            if ok and gok:
                fp = os.path.join(outdir, tag + ".json")
                json.dump(sc, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                sol = sc.get("solution", {})
                mw.writerow([os.path.basename(fp), p["origin"], p["trick_name"],
                             sol.get("culprit"), sol.get("weapon"),
                             sc.get("background", {}).get("setting_raw", {}).get("culture", "")])
                mf.flush()
                accepted += 1
                print(f"  ✅ [{accepted}/{target}] {tag}  (범인 {sol.get('culprit')}, 흉기 {sol.get('weapon')})")
            else:
                skiplog.write(f"[검증{ok}/난이도{gok}] {tag}\n"); skiplog.flush()
                print(f"  ⏭  탈락 {tag} (검증 {ok}/난이도 {gok})")
        except Exception as e:
            skiplog.write(f"[예외] {tag}: {e}\n{traceback.format_exc()}\n"); skiplog.flush()
            print(f"  ✗ 예외 {tag}: {e}")

    mf.close(); skiplog.close()
    print(f"\n완료: 채택 {accepted}편 / 시도 {tried}편  → {outdir}")
    print("다음: python build_sft.py \"scenarios/gen/*.json\"  로 SFT 데이터셋 빌드")

if __name__ == "__main__":
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    plan = build_plan(target)
    if "--plan" in sys.argv:
        print_plan(plan, target)
    else:
        run(target, plan)
