#!/usr/bin/env python3
"""
json/<한글 파일>.json (시나리오팀 원본) + enrich_en/<slug>.json (영문 콘텐츠)
  → scenarios_en/<slug>_en.json

5개 이미지 노트북(hidream / flux2_klein / hidream_o1 / qwen / fluxdev) +
2개 BGM 노트북(stable_audio / ace_step)이 실제로 읽는 필드:

    scenario_id, source_title,
    source_story.{title,synopsis,tone}, adapted_story.{title,synopsis,tone,palette},
    setting.{era,location}, culture.instruments,
    places[].{place_id,name,description,clues},
    cast[].{id,age,gender,occupation,appearance,home_place_id}

기계적으로 계산하는 것 (원본 json/*.json 에서, 번역 아님):
  - culture.instruments   : bgm.palette.reference_en (시나리오팀이 이미 영문으로 써둠)
  - cast[].home_place_id  : map.places[].owner 의 역참조. victim 은 소유 장소가 없으므로
                            death.place(범행 장소)로 대체 (enrich 의 victim.home_place_id 로 override 가능)
  - cast[].age             : profile.age ("30대" 등) 의 앞자리+5 (age_override 로 override 가능)
  - cast[].gender           : profile.sex 남/여 → male/female (gender_override 로 override 가능
                              — 원본 데이터에 직업 라벨과 성별 필드가 어긋난 경우가 있다, 예: 22번 C2)

사람이 직접 채우는 것 (enrich_en/<slug>.json):
  - source_story / adapted_story 의 synopsis, tone, palette
  - places[].name/description/clues (clues 는 map.places[].features 번역 — "이 장면엔
    반드시 이게 보여야 한다" 는 단서 목록. 이미지 프롬프트의 강한 지시문으로 쓰인다)
  - cast[].occupation/appearance (appearance 는 원본에 아예 없는 필드라 새로 창작 —
    인물별로 뚜렷이 다른 특징을 의식적으로 준다, 안 그러면 인물 이미지가 다 비슷해짐)

번역기를 안 돌리는 이유는 위와 동일: appearance 처럼 원본에 없는 필드가 있어서
기계 번역만으로는 못 채운다.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
SRC_DIR = ROOT / "json"
ENRICH_DIR = ROOT / "enrich_en"
OUT_DIR = ROOT / "scenarios_en"


def age_to_int(age_str: str, override: int | None = None) -> int:
    # "30대" -> 35, "10대 후반" -> 18, "10대 초반" -> 12 (구간 근사).
    # "불명"(나이 불명 캐릭터)처럼 숫자가 없는 경우엔 override 필수
    # (enrich 의 cast[cid]["age_override"] 로 지정).
    if override is not None:
        return override
    m = re.match(r"(\d+)", age_str)
    if not m:
        raise ValueError(f"나이 파싱 불가: {age_str!r} — enrich 에 age_override 지정할 것")
    decade = int(m.group(1))
    if "후반" in age_str:
        return decade + 8
    if "초반" in age_str:
        return decade + 2
    return decade + 5


def gender_to_en(sex: str) -> str:
    return {"남": "male", "여": "female"}[sex]


def home_place_of(cast_id: str, d: dict) -> str:
    for p in d["map"]["places"]:
        if p.get("owner") == cast_id:
            return p["id"]
    raise KeyError(f"{cast_id} 소유 장소를 못 찾음 — enrich 에서 home_place_override 로 수동 지정할 것")


def build(enrich_path: pathlib.Path) -> dict:
    e = json.load(open(enrich_path, encoding="utf-8"))
    d = json.load(open(SRC_DIR / e["src_name"], encoding="utf-8"))

    instruments = d.get("bgm", {}).get("palette", {}).get("reference_en")
    if not instruments:
        raise ValueError(f"{e['slug']}: json 원본에 bgm.palette.reference_en 이 없음")

    places = []
    for p in d["map"]["places"]:
        pe = e["places"].get(p["id"])
        if pe is None:
            raise KeyError(f"{e['slug']}: enrich 에 place {p['id']} 가 없음 (원본엔 있음)")
        places.append({
            "place_id": p["id"],
            "name": pe["name"],
            "description": pe["description"],
            "clues": pe["clues"],
        })

    cast = []
    for c in d["cast"]:
        ce = e["cast"][c["id"]]
        gender = ce.get("gender_override") or gender_to_en(c["profile"]["sex"])
        cast.append({
            "id": c["id"],
            "age": age_to_int(c["profile"]["age"], ce.get("age_override")),
            "gender": gender,
            "occupation": ce["occupation"],
            "appearance": ce["appearance"],
            "home_place_id": ce.get("home_place_override") or home_place_of(c["id"], d),
        })

    ve = e["victim"]
    cast.append({
        "id": "victim",
        "age": ve["age"],
        "gender": ve["gender"],
        "occupation": ve["occupation"],
        "appearance": ve["appearance"],
        "home_place_id": ve.get("home_place_id") or d["death"]["place"],
    })

    return {
        "scenario_id": e["slug"],
        "source_title": e["source_title"],
        # title/synopsis 는 사람이 읽는 문서용이다. 프롬프트 조립 코드는 .tone 만
        # 읽는다 — synopsis 에 원작 캐릭터 이름이 들어가도 이미지/BGM 프롬프트로는
        # 안 새어나간다. (이름 유입 검사는 places/cast 의 name/description/
        # appearance/occupation/clues 에만 적용할 것.)
        "source_story": {
            "title": e["source_title"],
            "synopsis": e["source_synopsis"],
            "tone": e["source_tone"],
        },
        "adapted_story": {
            "title": e["adapted_title"],
            "synopsis": e["adapted_synopsis"],
            "tone": e["adapted_tone"],
            "palette": e["palette"],
        },
        "setting": {"era": e["era"], "location": e["location"]},
        "culture": {"instruments": instruments},
        "places": places,
        "cast": cast,
    }


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    OUT_DIR.mkdir(exist_ok=True)
    enrich_files = sorted(p for p in ENRICH_DIR.glob("*.json") if not p.name.startswith("_"))
    for ef in enrich_files:
        if only and only not in ef.name:
            continue
        out = build(ef)
        out_path = OUT_DIR / f"{out['scenario_id']}_en.json"
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{ef.name} -> {out_path}")
        print(f"  장소 {len(out['places'])} / 인물 {len(out['cast'])}")
    print(f"\n총 {len(enrich_files) if not only else '?'}개 처리")


if __name__ == "__main__":
    main()
