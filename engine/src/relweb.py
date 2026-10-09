# -*- coding: utf-8 -*-
"""
relweb.py — 인물 사이의 **구체적인 얽힘**을 시나리오 데이터로 만든다.

왜 필요한가
  relate.py는 있는 사실을 잘 엮어 준다. 그런데 시나리오에 따라서는
  엮을 사실 자체가 없다. 22편을 보면 다섯 사람이 서로에 대해
  "관계자다"밖에 없다. 그러니 다섯 서술이 똑같아지고, 심문하면
  "그 사람과는 어떤 사이요?"에 아무 대답도 못 한다.

  관계는 렌더링의 문제가 아니라 **데이터의 문제**다.
  살인과 무관해도 좋다. 빚, 옛 은혜, 목격, 짝사랑, 뒤를 봐준 일 —
  이런 것들이 있어야 추궁이 갈래를 친다.

무엇을 만드나
  s["relation_web"] = [
    {"a":"C1","b":"C3","type":"빚","a_view":"…","b_view":"…","public":false,
     "hook":["곗돈","빚"], "clue_hint":"…"} , … ]

  모든 짝(C(n,2))에 하나씩. 한 인물이 같은 종류를 두 번 갖지 않는다.
  시나리오 제목으로 씨앗을 고정해 **다시 돌려도 같은 결과**가 나온다.

  이 얽힘은 진상(MMO)을 건드리지 않는다. 범인 판정에 영향을 주지 않고,
  대신 심문에 붙잡을 손잡이를 준다.

사용:
    python relweb.py out/22_경성활동사진관.json
    python relweb.py "scenarios/[0-9]*.json"
"""
import json, glob, sys, hashlib, itertools

def _j(w, pair="을/를"):
    a, b = pair.split("/")
    if not w:
        return b
    ch = w[-1]
    if not ("가" <= ch <= "힣"):
        return b
    jong = (ord(ch) - 0xAC00) % 28
    if pair == "으로/로":
        return b if jong in (0, 8) else a
    return a if jong else b


# ── 얽힘의 종류 ───────────────────────────────────────────────────────
# a_view = A가 B를 볼 때 / b_view = B가 A를 볼 때. 서로 다른 온도로 적는다.
TIES = [
    dict(type="빚", public=False,
         a="{B}에게 돈을 빌렸다. 갚기로 한 날이 지났고, 요즘은 눈을 잘 마주치지 못한다.",
         b="{A}에게 돈을 빌려주었다. 갚으라는 말을 아직 꺼내지 않았을 뿐, 잊은 것은 아니다.",
         ac="…빚이 있습니다. {B}에게. 갚을 날이 지났고, 그래서 요즘 그 앞에서 작아집니다. 허나 빚 때문에 사람을 해치진 않습니다.",
         bc="…돈을 빌려준 건 사실입니다. {A}에게. 재촉한 적은 없어요 — 아직은.",
         hook=["빚", "돈", "갚", "빌린"]),
    dict(type="옛 은혜", public=True,
         a="예전에 {B}가 내 일을 덮어 준 적이 있다. 그 뒤로 그 앞에서는 목소리가 작아진다.",
         b="{A}의 일을 한 번 덮어 준 적이 있다. 그 일을 들먹인 적은 없으나, 필요하면 쓸 수 있다고 생각한다.",
         ac="…예전에 제 실수 하나를 {B}가 덮어 줬습니다. 그 뒤로 그 사람 부탁은 거절을 못 합니다.",
         bc="…{A}의 일을 덮어 준 적이 있습니다. 무슨 일이었는지는… 그 사람 입으로 듣는 게 맞겠지요.",
         hook=["덮어", "감싸", "그때 일", "은혜"]),
    dict(type="목격", public=False,
         a="{B}가 그 밤 있어서는 안 될 자리에 서 있는 것을 보았다. 아직 아무에게도 말하지 않았다.",
         b="그 밤 {A}와 눈이 마주친 것 같다. 보았다면 무엇을 보았는지 알 수 없어 불편하다.",
         ac="…봤습니다. 그 밤, {B}가 있어선 안 될 자리에 있는 걸. 말 안 한 건… 확신이 없어서였습니다.",
         bc="…그 밤 {A}와 눈이 마주친 것 같긴 합니다. 저는 그저 지나던 길이었습니다.",
         hook=["봤", "보았", "그 밤", "마주"]),
    dict(type="다툼", public=True,
         a="며칠 전 {B}와 소리를 높여 다퉜다. 사람들이 들었을 것이다. 지금은 그것이 마음에 걸린다.",
         b="{A}와 다툰 일이 있다. 내가 옳았다고 지금도 생각하지만, 하필 때가 나빴다.",
         ac="…다퉜습니다, {B}와. 소리도 높였고요. 하필 이런 때에 그런 일이 있어서, 저도 마음에 걸립니다.",
         bc="…{A}와 언성을 높인 건 맞습니다. 내용은 별것 아니었어요. 때가 나빴을 뿐이지.",
         hook=["다퉜", "싸", "언성", "말다툼"]),
    dict(type="밀회", public=False,
         a="{B}와는 남몰래 만나는 사이다. 처지가 처지라 밝힐 수 없고, 그래서 거짓말이 늘었다.",
         b="{A}와의 일은 아무도 모른다. 알려지면 둘 다 잃을 것이 있어, 마주쳐도 모른 척해 왔다.",
         ac="…{B}와는, 남몰래 만나는 사이입니다. 처지가 처지라 숨겼습니다. 그 밤의 제 거짓말 절반은… 그 사람을 가리려던 겁니다.",
         bc="…네, {A}와 그런 사이입니다. 모른 척한 건 그 사람을 지키려던 것뿐이에요.",
         hook=["둘이", "몰래 만나", "사이", "밀회", "정분"]),
    dict(type="말 못 할 연모", public=False,
         a="{B}를 마음에 품은 지 오래다. 처지 탓에 말할 수 없어, 멀리서 살피는 것으로 그쳐 왔다.",
         b="{A}의 눈길이 가끔 오래 머무는 것을 안다. 모르는 척하는 것이 서로에게 나았다.",
         ac="…{B}를 마음에 품고 있습니다. 오래됐습니다. 말할 수 있는 처지가 아니라… 살피는 걸로 그쳤습니다. 그게 수상해 보였다면, 그래서입니다.",
         bc="…{A}의 마음은 짐작하고 있었습니다. 모르는 척한 건 그게 서로를 위한 길이라 여겨서입니다.",
         hook=["연모", "마음에 품", "눈길", "좋아하"]),
    dict(type="옛 정인", public=False,
         a="{B}와는 예전에 정인(情人)이었다. 끝이 좋지 못했고, 그 앙금이 아직 남의 눈을 피해 다닌다.",
         b="{A}와는 한때 연을 맺었던 사이다. 헤어진 사정은 서로 입에 올리지 않기로 했다.",
         ac="…{B}와는 예전에 정인이었습니다. 끝이 좋지 않았고요. 지금 서먹한 건 그 탓이지, 다른 뜻은 없습니다.",
         bc="…한때의 일입니다, {A}와는. 헤어진 사정은 말하지 않기로 했습니다 — 서로를 위해서.",
         hook=["정인", "옛정", "헤어", "연을"]),
    dict(type="깨진 혼담", public=False,
         a="{B}와는 혼담이 오갔다가 깨진 사이다. 깨뜨린 쪽은 나였고, 그 빚진 마음이 아직 있다.",
         b="{A}와 혼담이 있었다. 깨졌을 때 사람들 앞에서 웃었지만, 속이 같았던 것은 아니다.",
         ac="…혼담이 있었습니다, {B}와. 깨뜨린 건 저였고요. 그 사람 앞에서 떳떳하지 못한 건 그래서입니다.",
         bc="…{A}와 혼담이 오간 적 있습니다. 깨졌지요. 웃어넘겼지만… 쉽게 넘긴 건 아닙니다.",
         hook=["혼담", "혼사", "파혼", "깨진"]),
    dict(type="저당", public=False,
         a="급전이 필요해 집안 물건 하나를 {B}에게 몰래 잡혔다. 되찾기 전엔 큰소리를 칠 수가 없다.",
         b="{A}가 잡힌 물건을 내가 맡아 두고 있다. 어디서 난 물건인지는 묻지 않았다.",
         ac="…집안 물건 하나를 {B}에게 잡혔습니다. 급전 때문에요. 그게 남 앞에 드러나면 집안 망신이라… 숨겼습니다.",
         bc="…{A}의 물건을 맡아 둔 건 사실입니다. 출처는 묻지 않는 게 이 바닥 법도라서요.",
         hook=["저당", "잡혔", "맡긴 물건", "급전"]),
    dict(type="공갈", public=False,
         a="{B}가 내 약점을 쥐고 이따금 값을 요구해 왔다. 이번 달에도 치렀다.",
         b="{A}의 약점을 알고 몇 번 값을 받았다. 죄라면 죄지만, 먼저 잘못한 것은 그쪽이다.",
         ac="…{B}에게 뜯기고 있었습니다. 제 약점을 쥐고서요. 이번 달에도 치렀습니다. 그자가 미웠냐 물으면 — 미웠습니다. 허나 그뿐입니다.",
         bc="…{A}에게 돈을 받은 건 맞습니다. 그쪽 약점을 알고서요. 떳떳하진 않지만, 먼저 구린 건 그쪽이었습니다.",
         hook=["약점", "뜯", "값을", "협박", "쥐고"]),
    dict(type="숨긴 혈연", public=False,
         a="{B}와 나는 피가 이어져 있다. 밝히면 여러 사람이 다치는 사정이라, 남처럼 지내 왔다.",
         b="{A}와의 혈연은 나만 아는 줄 알았다. 남처럼 구는 것이 서로를 지키는 길이었다.",
         ac="…{B}와 저는 피가 이어져 있습니다. 밝히면 다치는 사람이 여럿이라 남처럼 지냈습니다. 서로를 감싸는 듯 보였다면 — 그래서입니다.",
         bc="…네, {A}와는 혈연입니다. 숨긴 건 부끄러워서가 아니라, 지키려던 겁니다.",
         hook=["혈연", "피가", "남매", "핏줄", "배다른"]),
    dict(type="비리 공유", public=False,
         a="{B}와 함께 저지른 부정이 하나 있다. 서로가 서로의 증인이라, 등을 돌릴 수도 없다.",
         b="{A}와 나는 같은 잘못을 나눠 지고 있다. 한쪽이 불면 둘 다 끝난다.",
         ac="…{B}와 함께 저지른 일이 있습니다. 부정한 일이요. 서로가 서로의 증인이라 말을 못 했습니다. 살인과는 무관합니다 — 그것만은 믿어 주십시오.",
         bc="…같은 잘못을 나눠 진 사이입니다, {A}와는. 한쪽이 불면 둘 다 끝나는.",
         hook=["함께 저지", "부정", "공모", "나눠"]),
    dict(type="뒷거래", public=False,
         a="{B}에게서 남에게 말 못 할 물건을 사 왔다. 값은 후했고, 입은 무거워야 했다.",
         b="{A}에게 은밀히 물건을 대 왔다. 단골의 이름은 파는 물건보다 무겁다.",
         ac="…{B}에게서 물건을 사 온 게 있습니다. 떳떳한 물건은 아니고요. 그래서 그 사람 얘기만 나오면 말을 아꼈습니다.",
         bc="…{A}는 제 단골입니다. 무엇을 팔았는지는… 장사꾼 입이 무거운 것도 죄입니까.",
         hook=["뒷거래", "몰래 사", "물건을 대", "단골"]),
    dict(type="연적", public=False,
         a="{B}와 나는 같은 사람을 마음에 두었다. 그 사람이 누구인지는 서로 입 밖에 낸 적이 없다.",
         b="{A}가 나와 같은 곳을 바라본다는 것을 안다. 그래서 그 사람 앞에서만 서로 예민해진다.",
         ac="…{B}와 저는, 같은 사람을 마음에 두고 있습니다. 서로 말한 적은 없지만 압니다. 그 사람 앞에서 우리가 날 선 건 그래서입니다.",
         bc="…{A}와 제가 같은 마음이라는 거, 압니다. 그게 다입니다 — 마음이 겹친 죄밖에 없습니다.",
         hook=["연적", "같은 사람", "겹친 마음", "질투"]),
    dict(type="심부름", public=True,
         a="{B}에게 남에게 못 시킬 일을 몇 번 시켰다. 입이 무거워 믿고 맡겼다.",
         b="{A}가 시킨 일을 몇 번 해 주었다. 무슨 일인지 다 알고 한 것은 아니다.",
         ac="…{B}에게 심부름을 몇 번 시켰습니다. 남에게 못 맡길 일이라. 내용은… 제 입으로 말하겠습니다, 그 사람 잘못은 없습니다.",
         bc="…{A}의 심부름을 몇 번 했습니다. 내용을 다 알고 한 건 아닙니다.",
         hook=["시켰", "심부름", "맡겼", "부탁"]),
    dict(type="오랜 정", public=True,
         a="{B}와는 이 일이 있기 훨씬 전부터 알던 사이다. 그래서 더 묻기가 어렵다.",
         b="{A}와는 오래된 사이다. 의심하고 싶지 않아 자꾸 다른 사람을 떠올리게 된다.",
         ac="…{B}와는 오래전부터 아는 사이입니다. 그래서 그 사람만은 의심하고 싶지 않았습니다.",
         bc="…{A}와는 오랜 사이입니다. 감싸는 걸로 보였다면, 정 때문이지 다른 이유는 없습니다.",
         hook=["오래", "예전", "옛", "그때부터"]),
]


def _seed(s):
    h = hashlib.sha256((s.get("meta", {}).get("title") or "x").encode("utf-8")).digest()
    return list(h)


ROMANTIC = {"밀회", "말 못 할 연모", "옛 정인", "깨진 혼담", "연적", "숨긴 혈연"}
FAMILY_WORDS = ("부부", "아내", "남편", "남매", "형", "아우", "언니", "동생", "모", "부", "딸", "아들",
                "숙부", "조카", "시어", "며느리", "오라비", "누이")


def _familyish(ca, cb):
    ra = str((ca.get("profile") or {}).get("relation") or "") + str(ca.get("public") or "")
    rb = str((cb.get("profile") or {}).get("relation") or "") + str(cb.get("public") or "")
    return any(w in ra for w in FAMILY_WORDS) and any(w in rb for w in FAMILY_WORDS)


def build_web(s):
    cast = s["cast"]
    ids = [c["id"] for c in cast]
    cmap = {c["id"]: c for c in cast}
    name = {c["id"]: c["name"] for c in cast}
    vic = (s.get("victim") or {}).get("name", "피해자")
    name["V"] = vic
    seed = _seed(s)
    pairs = list(itertools.combinations(ids, 2))
    # 피해자와의 숨은 얽힘 — 두 사람에게 (범인은 제외: 동기 구조를 흔들지 않는다)
    innocents = [i for i in ids if not cmap[i].get("is_culprit")]
    vpick = [innocents[seed[7] % len(innocents)]]
    j = seed[11] % len(innocents)
    if innocents[j] not in vpick:
        vpick.append(innocents[j])
    pairs += [(v, "V") for v in vpick]
    used = {i: set() for i in ids + ["V"]}   # 한 인물이 같은 종류를 두 번 갖지 않게
    web = []
    for n, (a, b) in enumerate(pairs):
        start = seed[n % len(seed)] % len(TIES)
        pick = None
        romantic_ok = not (b != "V" and _familyish(cmap[a], cmap[b]))
        for k in range(len(TIES)):
            t = TIES[(start + k) % len(TIES)]
            if t["type"] in ROMANTIC and not romantic_ok:
                continue
            if t["type"] not in used[a] and t["type"] not in used[b]:
                pick = t
                break
        pick = pick or TIES[start]
        used[a].add(pick["type"]); used[b].add(pick["type"])
        def _fmt(tpl, A, B):
            """이름 뒤 조사를 받침에 맞게 고친다.
            '서가온가', '임태윤는' 같은 것이 카드에 그대로 실리면
            인물이 제 이름조차 어색하게 부르는 꼴이 된다."""
            out = tpl.format(A=A, B=B)
            for nm in (A, B):
                for pair in ("과/와", "이/가", "은/는", "을/를", "으로/로"):
                    x, y = pair.split("/")
                    right = _j(nm, pair)
                    for wrong in (x, y):
                        if wrong != right:
                            out = out.replace(nm + wrong, nm + right)
            return out
        web.append({
            "a": a, "b": b, "type": pick["type"], "public": pick["public"],
            "a_view": _fmt(pick["a"], name[a], name[b]),
            "b_view": _fmt(pick["b"], name[a], name[b]),
            "a_confess": _fmt(pick.get("ac", ""), name[a], name[b]),
            "b_confess": _fmt(pick.get("bc", ""), name[a], name[b]),
            "hook": pick["hook"],
        })
    return web


def apply_pressure(s):
    """비밀 얽힘을 심문 손잡이로 — 정곡(훅+상대 이름)을 찔리면 관계를 실토한다."""
    cmap = {c["id"]: c for c in s["cast"]}
    vic = (s.get("victim") or {}).get("name", "피해자")
    nm = {c["id"]: c["name"] for c in s["cast"]}
    nm["V"] = vic
    n = 0
    for e in (s.get("relation_web") or []):
        if e.get("public"):
            continue
        for side, other in (("a", "b"), ("b", "a")):
            cid = e[side]
            if cid == "V" or cid not in cmap:
                continue
            conf = e.get(f"{side}_confess")
            if not conf:
                continue
            pp = cmap[cid].setdefault("pressure_points", [])
            mark = f"관계:{e['type']}:{e[other]}"
            if any(x.get("unlocks") == mark for x in pp):
                continue
            trig = list(e.get("hook") or [])[:3] + [nm.get(e[other], "")]
            pp.append({"trigger": [x for x in trig if x],
                       "reveals": conf, "unlocks": mark})
            n += 1
    return n


def views_for(s, cid):
    """cid가 보는 상대별 얽힘 한 줄."""
    out = {}
    for e in (s.get("relation_web") or []):
        if e["a"] == cid:
            out[e["b"]] = (e["type"], e["a_view"])
        elif e["b"] == cid:
            out[e["a"]] = (e["type"], e["b_view"])
    return out


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "scenarios/[0-9]*.json"
    force = "--force" in sys.argv
    for p in sorted(glob.glob(arg)):
        s = json.load(open(p, encoding="utf-8"))
        if s.get("relation_web") and not force:
            print(f"  {p.split('/')[-1]:28} 이미 있음 ({len(s['relation_web'])}쌍)")
            continue
        s["relation_web"] = build_web(s)
        np = apply_pressure(s)
        json.dump(s, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  {p.split('/')[-1]:28} 얽힘 {len(s['relation_web'])}쌍 · 실토 손잡이 {np}개")
