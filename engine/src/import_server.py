# -*- coding: utf-8 -*-
"""
import_server.py — 서버(API)가 만든 옛 번호(24~33, 한글 슬러그) 시나리오를
새 체계(31~40, 영문 슬러그)로 들여온다.

사용: 서버에서 가져온 json들을 incoming/ 에 넣고
    python import_server.py
"""
import os, glob, shutil, json

SLUG = {"24_최척전":"31_choecheok","25_박씨전":"32_parkssi","26_배비장전":"33_baebijang",
        "27_이춘풍전":"34_leechunpung","28_옹고집전":"35_onggojip_api",
        "29_그리스신화(미노타우로스)":"36_minotaur","30_라푼젤(그림동화)":"37_rapunzel",
        "31_신데렐라":"38_cinderella","32_백설공주":"39_snow_white","33_잠자는숲속의미녀":"40_sleeping_beauty"}

n=0
for f in sorted(glob.glob("incoming/*.json")):
    base=os.path.basename(f).replace(".json","")
    new=SLUG.get(base)
    if not new:
        print("  ? 매핑 없음:", base); continue
    shutil.copy(f, f"scenarios/{new}.json"); n+=1
    nv=f.replace(".json","_novel.md")
    if os.path.exists(nv): shutil.copy(nv, f"scenarios/{new}_novel.md")
    print(f"  {base} → {new}")
print(f"{n}편 들여옴 · 이어서: hand_pipeline은 불필요(서버가 이미 돌림), run_all.py로 검증")
