#!/bin/bash
# hand_pipeline.sh — 손으로 지은 코어 JSON을 완제품으로 올린다.
#   ./hand_pipeline.sh out/35_장화신은고양이.json [ROUNDS] [PLACES]
set -e
F="$1"; R="${2:-}"; P="${3:-}"
PY=${MM_PYTHON:-python3}
$PY josa_fix.py "$F" >/dev/null 2>&1 || true
$PY upgrade_schema.py "$F" 2>&1 | tail -1
if [ -n "$R" ]; then MM_ROUNDS=$R MM_PLACES=${P:-6} $PY spread.py "$F" >/dev/null; fi
$PY add_acts.py "$F" >/dev/null 2>&1
$PY add_search.py "$F" >/dev/null 2>&1
$PY add_voice.py "$F" >/dev/null 2>&1
$PY add_bgm.py "$F" >/dev/null 2>&1
$PY add_bgm2.py "$F" >/dev/null 2>&1
$PY add_detective.py "$F" >/dev/null 2>&1
$PY relate.py "$F" >/dev/null 2>&1
$PY voices.py "$F" >/dev/null
$PY restyle.py "$F" >/dev/null 2>&1
$PY relate.py "$F" >/dev/null 2>&1
$PY presence.py "$F" >/dev/null
$PY soundtrack.py "$F" >/dev/null
$PY pace.py "$F" >/dev/null
$PY secret_clue.py --mark "$F" >/dev/null   # 비밀↔단서 짝 맞추기 (ui보다 먼저 — 선택지 이름이 단서에서 나온다)
$PY ui.py "$F" >/dev/null
$PY alibi.py "$F" >/dev/null      # 알리바이 진술 — ui가 만든 인물 카드에 얹는다
$PY placeart.py "$F" >/dev/null   # 장소 그림 지시 — ui가 만든 탐색 선택지를 읽는다
$PY art_91.py "$F" >/dev/null     # 91편(시연용)만 손글씨 그림 지시로 덮는다
$PY search_label.py "$F" >/dev/null  # 탐색 선택지를 그림에 보이는 물건으로 맞춘다(그림 뒤에 온다)
$PY pace_clues.py "$F" >/dev/null
$PY cluemedia.py "$F" >/dev/null
$PY narration_visual.py "$F" >/dev/null
$PY story_narration.py "$F" >/dev/null
$PY crossref.py "$F" >/dev/null
$PY spread_hints.py "$F" >/dev/null   # 범인을 가리키는 실마리를 갈래마다 흩는다
$PY deduce.py "$F" >/dev/null
$PY stars.py "$F" >/dev/null
$PY add_difficulty.py "$F" >/dev/null 2>&1
$PY ending_book.py "$F" >/dev/null   # 엔딩 두 갈래·비밀 발표·그날 밤 재연(범행 대목 포함)
$PY make_novel.py "$F" >/dev/null
# 이동한도 재계산
$PY - "$F" <<'PYEOF'
import json, math, sys
f=sys.argv[1]; s=json.load(open(f,encoding="utf-8"))
pl={p["id"]:p for p in s["map"]["places"]}
mv=0
for c in s["cast"]:
    tl=[pl[c["timeline"][sl]]["pos"] for sl in s["time_slots"] if c["timeline"].get(sl) in pl]
    for a,b in zip(tl,tl[1:]): mv=max(mv,math.hypot(a[0]-b[0],a[1]-b[1]))
s["map"]["max_move_per_slot"]=round(mv+0.5,2)
json.dump(s,open(f,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
PYEOF
$PY - "$F" <<'PYEOF'
import json, sys
from verify import verify,_print
from difficulty import difficulty_gate
from simulate import simulate, tier
s=json.load(open(sys.argv[1],encoding="utf-8"))
ok,rep=verify(s)
if not ok:_print([r for r in rep if not r[1]])
g,_=difficulty_gate(s); r=simulate(s,600)
print(f"verify {'✅' if ok else '❌'} · 난이도 {'✅' if g else '❌'} · 정답률 {r:.2f} {tier(r)[0]}")
PYEOF
$PY fe_lint.py "$F" | tail -3
