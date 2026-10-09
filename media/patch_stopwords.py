#!/usr/bin/env python3
"""banned_terms() 에 불용어 필터를 추가한다 (오탐 제거)."""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent
NOTEBOOKS = ["image_hidream.ipynb", "image_flux2_klein.ipynb"]

OLD = (
    'def banned_terms(d):\n'
    '    import re\n'
    '    title = re.sub(r"\\(.*?\\)", "", d.get("source_title", ""))\n'
    '    words = {w.strip(".,").lower() for w in title.split() if len(w) > 2}\n'
    '    return words | set(STUDIO_TERMS)\n'
)
NEW = (
    'STOPWORDS = {\n'
    '    "the", "a", "an", "of", "in", "on", "for", "with", "to", "and", "or",\n'
    '    "korean", "folktale", "fairy", "tale", "tales", "myth", "legend", "legends",\n'
    '    "novel", "classical", "pansori", "based",\n'
    '    "little", "big", "great", "old", "young", "new",\n'
    '    "girl", "boy", "man", "woman", "king", "queen", "prince", "princess",\n'
    '    "red", "white", "black", "gold", "silver", "snow",\n'
    '    "hood", "riding", "match", "sun", "moon", "woodcutter",\n'
    '    "night", "day", "house", "story",\n'
    '}\n\n'
    'def banned_terms(d):\n'
    '    import re\n'
    '    title = re.sub(r"\\(.*?\\)", "", d.get("source_title", ""))\n'
    '    words = {w.strip(".,").lower() for w in title.split() if len(w) > 2}\n'
    '    return (words - STOPWORDS) | set(STUDIO_TERMS)\n'
)

for nb_name in NOTEBOOKS:
    path = ROOT / nb_name
    nb = json.loads(path.read_text(encoding="utf-8"))
    hit = False
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if OLD in src:
            new_src = src.replace(OLD, NEW)
            cell["source"] = new_src.splitlines(keepends=True)
            cell["outputs"] = []
            cell["execution_count"] = None
            hit = True
    if hit:
        backup = path.with_suffix(path.suffix + ".bak4")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{nb_name}: 불용어 필터 추가 완료")
    else:
        print(f"{nb_name}: 대상 못 찾음")
