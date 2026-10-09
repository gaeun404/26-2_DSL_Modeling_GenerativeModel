# -*- coding: utf-8 -*-
"""
build_sft_agent.py — 심문 대화를 **에이전트 파인튜닝용 코퍼스**로 만든다.

기존 build_sft.py와 다른 것:
  build_sft.py       원작 → 시나리오 JSON      (시나리오 '생성기'를 학습)
  build_sft_agent.py 심문 질문 → 인물 답변      (용의자 '에이전트'를 학습)   ← 이 파일

왜 필요한가:
  모델 선정이 어느 쪽으로 끝나든 다음 단계는 같다.
  · 로컬 모델이 통과하면 → 그 대화를 모아 더 작은 모델로 증류
  · 로컬이 부족해 API를 쓰면 → API를 **교사 모델**로 삼아 학습 데이터를 모으고,
    그 데이터로 로컬 모델을 파인튜닝한다. 크레딧은 소진되지만 데이터는 남는다.

★ 핵심 원칙: 나쁜 답은 한 줄도 넣지 않는다.
  파인튜닝은 넣은 것을 그대로 배운다. 애매한 답을 '아깝다'고 넣으면
  그 버릇을 학습한다. 그래서 아래 관문을 전부 통과한 턴만 채택한다.

    ① 가드 검사 통과      비한국어·메타·기계적 거부·비밀 조기누설 없음
    ② 형식 통과(연기 규격) [감정]/[행동]/[대사] 3줄이 파싱되고 enum 안
    ③ 감정-게이지 정합     강도 상한 위반·조기 누설 없음
    ④ 길이               너무 짧은 답(…, 네.)은 배울 게 없다
    ⑤ 중복 아님          같은 인물이 거의 같은 말을 반복한 것은 하나만 남긴다
                        (repeat을 학습시키면 안 된다)

사용:
    python build_sft_agent.py                          # out_stress 전체
    python build_sft_agent.py --src "out_stress/*/*.jsonl"
    python build_sft_agent.py --scenarios ../scenarios  # 시나리오 위치
    python build_sft_agent.py --min-len 25 --val 0.1
결과:
    sft_agent_train.jsonl / sft_agent_val.jsonl  (chat 포맷)
    sft_agent_report.txt                          (무엇이 왜 버려졌는지)
"""
import os, sys, json, glob, argparse, difflib
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)


def log(*a): print(*a, flush=True)


def near_dup(a, b, thr=0.90):
    return difflib.SequenceMatcher(None, a, b).ratio() >= thr


def load_scenarios(scen_dir):
    """시나리오를 미리 읽어 둔다. 시스템 프롬프트를 재구성하려면 원본이 필요하다."""
    out = {}
    for p in glob.glob(os.path.join(scen_dir, "*.json")):
        try:
            s = json.load(open(p, encoding="utf-8"))
            out[os.path.basename(p).replace(".json", "")] = s
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="out_stress/*/*.jsonl",
                    help="대화 로그 glob (stress_local.py가 남긴 것)")
    ap.add_argument("--scenarios", default="../scenarios", help="시나리오 json 폴더")
    ap.add_argument("--min-len", type=int, default=25, help="[대사] 최소 길이")
    ap.add_argument("--dup-thr", type=float, default=0.90, help="중복 판정 유사도")
    ap.add_argument("--val", type=float, default=0.1, help="검증 분할 비율")
    ap.add_argument("--out-prefix", default="sft_agent")
    ap.add_argument("--allow-plain", action="store_true",
                    help="연기 규격이 아닌(3줄 형식이 아닌) 로그도 채택")
    a = ap.parse_args()

    from guard import Checker
    from turn_schema import parse_turn, validate_turn
    from stress_agent import suspect_system

    paths = sorted(glob.glob(a.src))
    if not paths:
        log(f"[오류] 로그를 찾지 못함: {a.src}")
        log("  stress_local.py를 먼저 돌려 out_stress/ 에 대화를 쌓으세요.")
        sys.exit(1)

    scen_dir = a.scenarios if os.path.isdir(a.scenarios) else os.path.join(HERE, "scenarios")
    scens = load_scenarios(scen_dir)
    if not scens:
        log(f"[오류] 시나리오를 찾지 못함: {scen_dir}")
        sys.exit(1)
    log(f"시나리오 {len(scens)}편 · 로그 {len(paths)}개\n")

    records, drop = [], Counter()
    seen_by_suspect = defaultdict(list)
    per_source = Counter()

    for p in paths:
        name = os.path.basename(p).replace(".jsonl", "")
        source = os.path.basename(os.path.dirname(p))     # 모델 이름
        s = scens.get(name)
        if not s:
            drop["시나리오없음"] += 1
            log(f"  ⚠ {p} — 대응 시나리오({name})를 못 찾아 건너뜀")
            continue
        cast = {c["id"]: c for c in s["cast"]}

        for line in open(p, encoding="utf-8"):
            try: r = json.loads(line)
            except Exception: continue
            c = cast.get(r.get("suspect"))
            if not c:
                drop["인물없음"] += 1; continue
            ans = (r.get("a") or "").strip()
            if not ans or ans.startswith("[생성 실패"):
                drop["생성실패"] += 1; continue

            acting = bool(r.get("parsed"))
            if not acting and not a.allow_plain:
                drop["연기규격아님"] += 1; continue

            # ① 가드 검사
            why, _ = Checker(s, c).check(ans, acting=acting)
            if why:
                drop[f"가드:{why}"] += 1; continue

            # ②③ 형식·감정 정합
            line_text = ans
            if acting:
                pr = parse_turn(ans)
                if pr["errors"]:
                    drop["형식이탈"] += 1; continue
                iss = validate_turn(
                    pr, is_culprit=bool(c.get("is_culprit")),
                    gauge_value=r.get("gauge", 0) or 0)
                if iss:
                    drop["감정불일치"] += 1; continue
                line_text = pr["line"] or ""

            # ④ 길이
            if len(line_text) < a.min_len:
                drop["너무짧음"] += 1; continue

            # ⑤ 중복 — repeat을 학습시키면 안 된다
            key = (name, c["id"])
            if any(near_dup(line_text, x, a.dup_thr) for x in seen_by_suspect[key]):
                drop["중복"] += 1; continue
            seen_by_suspect[key].append(line_text)

            records.append({"messages": [
                {"role": "system", "content": suspect_system(s, c)},
                {"role": "user", "content": r.get("q", "")},
                {"role": "assistant", "content": ans}],
                "meta": {"scenario": name, "suspect": c["id"], "name": c["name"],
                         "tag": r.get("tag"), "source": source,
                         "is_culprit": bool(c.get("is_culprit")),
                         "gauge": r.get("gauge")}})
            per_source[source] += 1

    if not records:
        log("채택된 턴이 0건입니다. 관문이 너무 빡빡하거나, 로그가 전부 문제 있는 대화입니다.")
        log("유형별 탈락: " + ", ".join(f"{k} {v}" for k, v in drop.most_common()))
        sys.exit(2)

    # 분할 — 시나리오 단위로 나눠야 검증이 새지 않는다
    names = sorted({r["meta"]["scenario"] for r in records})
    n_val = max(1, int(len(names) * a.val)) if len(names) > 1 else 0
    val_names = set(names[-n_val:]) if n_val else set()
    train = [r for r in records if r["meta"]["scenario"] not in val_names]
    val = [r for r in records if r["meta"]["scenario"] in val_names]

    for tag, rows in (("train", train), ("val", val)):
        if not rows: continue
        with open(f"{a.out_prefix}_{tag}.jsonl", "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    total_in = sum(drop.values()) + len(records)
    rep = []
    rep.append(f"=== 에이전트 SFT 코퍼스 ===")
    rep.append(f"입력 턴 {total_in} · 채택 {len(records)} ({len(records)*100/total_in:.1f}%)")
    rep.append(f"  학습 {len(train)} · 검증 {len(val)}" + (f" (검증 시나리오: {sorted(val_names)})" if val_names else ""))
    rep.append("")
    rep.append("[탈락 사유]")
    for k, v in drop.most_common():
        rep.append(f"  {k:20} {v:5}  ({v*100/total_in:.1f}%)")
    rep.append("")
    rep.append("[출처별 채택]")
    for k, v in per_source.most_common():
        rep.append(f"  {k:46} {v:5}")
    rep.append("")
    byc = Counter(r["meta"]["name"] for r in records)
    rep.append("[인물별 채택]  — 한쪽으로 쏠리면 그 인물 말투만 배운다")
    for k, v in byc.most_common():
        rep.append(f"  {k:12} {v:5}")
    cul = sum(1 for r in records if r["meta"]["is_culprit"])
    rep.append(f"\n범인 턴 {cul} / 무고자 턴 {len(records)-cul}")
    rep.append("\n[읽는 법]")
    rep.append("  · 채택률이 30% 미만이면 모델이 아직 쓸 만하지 않다는 뜻이다.")
    rep.append("  · '중복'이 많으면 temperature를 올리거나 표현 레퍼토리를 강화해야 한다.")
    rep.append("  · 특정 인물에 쏠려 있으면 그 인물 말투만 학습된다 — 균형을 맞출 것.")
    text = "\n".join(rep)
    open(f"{a.out_prefix}_report.txt", "w", encoding="utf-8").write(text)
    log(text)
    log(f"\n저장: {a.out_prefix}_train.jsonl" + (f" / {a.out_prefix}_val.jsonl" if val else ""))
    log(f"      {a.out_prefix}_report.txt")


if __name__ == "__main__":
    main()
