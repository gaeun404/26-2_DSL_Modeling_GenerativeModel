"""
SFT 데이터셋 빌더 — verify + difficulty_gate 를 '모두 통과'한 시나리오만 모아 파인튜닝용 JSONL 생성.
포맷: 대화형 instruction (원작·트릭 조건 → 시나리오 JSON).
사용:
  python build_sft.py                 # out/*.json 중 통과분 → sft_dataset.jsonl
  python build_sft.py "gen/*.json"    # glob 지정
"""
import json, glob, sys
from verify import verify
from difficulty import difficulty_gate

SYS = "너는 추리게임 시나리오 설계자다. 원작과 조건을 받아, 검증을 통과하는 게임 스키마 JSON을 생성한다."

def to_record(s):
    meta = s.get("meta", {})
    trick = s.get("trick", {})
    cond = f"원작=\"{meta.get('origin','')}\", 시대=\"{meta.get('era','')}\""
    if trick: cond += f", 중심 트릭=\"{trick.get('name','')}\""
    user = f"{cond} 로 5용의자·3라운드 추리 시나리오를 스키마 JSON으로 생성하라."
    return {"messages": [
        {"role": "system", "content": SYS},
        {"role": "user", "content": user},
        {"role": "assistant", "content": json.dumps(s, ensure_ascii=False)}
    ]}

def run(paths, out="sft_dataset.jsonl"):
    kept = skipped = 0
    with open(out, "w", encoding="utf-8") as f:
        for p in sorted(paths):
            try: s = json.load(open(p, encoding="utf-8"))
            except Exception: continue
            ok = verify(s)[0]; gok = difficulty_gate(s)[0]
            if ok and gok:
                f.write(json.dumps(to_record(s), ensure_ascii=False) + "\n"); kept += 1
                print(f"  ✅ 채택 {p}")
            else:
                skipped += 1
                print(f"  ⏭  제외 {p}  (검증 {ok} / 난이도 {gok})")
    print(f"\nSFT 데이터셋 -> {out}  |  채택 {kept}편 / 제외 {skipped}편")
    print("※ 이 jsonl 을 dsl04 GPU에서 SFT(LoRA 등)에 사용. 통과분이 쌓일수록 데이터가 커진다.")

if __name__ == "__main__":
    paths = glob.glob(sys.argv[1]) if len(sys.argv) > 1 else glob.glob("scenarios/*.json")
    run(paths)
