#!/usr/bin/env python3
"""
1회용 이관 스크립트. build_scenario_en.py 안의 SCENARIOS 딕셔너리(20개, 기존
손으로 쓴 영문 콘텐츠)를 enrich_en/<slug>.json 개별 파일로 뽑아내면서,
enrich_en/_batch*_clues.json 에 있는 새 clues(장소별 단서 번역)와
palette_en(색채 무드 번역)을 합친다.

실행 후 build_scenario_en.py 는 이 개별 JSON 파일들을 읽도록 바뀐다
(SCENARIOS 인라인 딕셔너리는 더 이상 쓰지 않음).
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "enrich_en"

# build_scenario_en.py 를 모듈로 로드 (main() 은 실행 안 됨, import 시점엔
# SRC_DIR 접근이 없으므로 안전하다)
spec = importlib.util.spec_from_file_location("old_build", ROOT / "build_scenario_en.py")
old_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_build)

SCENARIOS = old_build.SCENARIOS

# 배치 파일 병합
CLUES = {}
for bf in sorted(OUT.glob("_batch*_clues.json")):
    CLUES.update(json.load(open(bf, encoding="utf-8")))

missing = set(cfg["slug"] for cfg in SCENARIOS.values()) - set(CLUES.keys())
if missing:
    raise SystemExit(f"clues 배치에 없는 slug: {missing}")

for src_name, cfg in SCENARIOS.items():
    slug = cfg["slug"]
    e = cfg["enrich"]
    c = CLUES[slug]

    places = {}
    for pid, pe in e["places"].items():
        if pid not in c["clues"]:
            raise SystemExit(f"{slug}: place {pid} 의 clues 가 배치에 없음")
        places[pid] = {
            "name": pe["name"],
            "description": pe["description"],
            "clues": c["clues"][pid],
        }

    cast = {}
    for cid, ce in e["cast"].items():
        entry = {"occupation": ce["occupation"], "appearance": ce["appearance"]}
        if "age_override" in ce:
            entry["age_override"] = ce["age_override"]
        if "home_place_override" in ce:
            entry["home_place_override"] = ce["home_place_override"]
        cast[cid] = entry

    victim = {
        "age": e["victim"]["age"],
        "gender": e["victim"]["gender"],
        "occupation": e["victim"]["occupation"],
        "appearance": e["victim"]["appearance"],
    }

    out = {
        "slug": slug,
        "src_name": src_name,
        "source_title": e["source_title"],
        "source_synopsis": e["source_synopsis"],
        "source_tone": e["source_tone"],
        "adapted_title": e["adapted_title"],
        "adapted_synopsis": e["adapted_synopsis"],
        "adapted_tone": e["adapted_tone"],
        "era": e["era"],
        "location": e["location"],
        "palette": c["palette_en"],
        "places": places,
        "cast": cast,
        "victim": victim,
    }

    out_path = OUT / f"{slug}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{slug} -> {out_path}")

print(f"\n{len(SCENARIOS)}개 이관 완료")
