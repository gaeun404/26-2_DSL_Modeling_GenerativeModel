# -*- coding: utf-8 -*-
"""
crossref.py — **대질(對質) 심문** 메커닉을 스키마에 넣는다.

■ 왜 만들었나
    재미 지표를 전수 측정하니 F6 '교차검증'이 가중 12(최대)인데 평균 6.79점,
    최저 5.00점으로 가장 큰 손실이었다. 원인은 두 가지였다.

    ① **재료는 있는데 쓰지 않았다.**
       관계망(relation_web)은 이미 인물 쌍마다 a_view/b_view/a_confess/b_confess를
       가지고 있다. 즉 "A는 이렇게 말하고 B는 저렇게 말한다"는 **짝이 이미 지어져 있다.**
       그런데 게임에는 그것을 맞대 볼 수단이 없었다. 플레이어는 A에게 묻고 B에게 물을 뿐,
       **A의 말을 B에게 들이댈 수가 없었다.**
    ② 그래서 심문이 '한 사람씩 따로 캐묻기'에 머물렀다. 서로 물리는 맛이 없었다.

■ 무엇을 넣나
    `cross_examination.pairs[]` — 맞대 놓으면 어긋나는 진술 쌍.
    심문 화면에 '대질' 버튼이 생기고, 다른 인물의 진술을 골라 들이댈 수 있다.
    맞는 짝을 들이대면 **둘 다 한 겹씩 실토**한다(비밀 공개 + 압박 상승).

    쌍의 갈래는 넷이다.
      relation  숨긴 관계 — 한쪽은 남처럼 굴고 다른 쪽은 얽혀 있다
      alibi     거짓 알리바이 — 그 자리를 지킨 사람이 부인한다
      timeline  같은 시각 같은 자리 — 둘 중 하나는 거짓이다
      witness   목격 — A가 본 것이 B의 말과 어긋난다

사용:
    python crossref.py                 # 전 편
    python crossref.py out/38_*.json   # 한 편
    python crossref.py --check         # 쌍 개수만
"""
import json, glob, re, sys

from ui import _j          # 조사 도우미


def _sent(x, cap=130):
    x = re.sub(r"\s+", " ", str(x or "")).strip()
    return (x[:cap].rstrip(" ,—") + "…") if len(x) > cap else x


# 말체별 문형 — 대본의 '지어낸 줄'을 그 인물 어미로 읽히게 한다.
#   전에는 "…그 자리에 없었소. 인정하오." 처럼 하오체로 고정돼 있어서
#   해요체 인물이 갑자기 하오체로 말했다(38편 큰언니).
_FORMS = {
    "해요체":  dict(deny="아니에요", admit="…거기 없었어요. 인정할게요",
                  saw="보지 못했어요", press="저는 그 자리를 지켰어요", q="왜 지금 그 얘길 해요"),
    "다정체":  dict(deny="아니에요", admit="…거기 없었어요. 인정할게요",
                  saw="보지 못했어요", press="저는 그 자리를 지켰어요", q="왜 지금 그 얘길 해요"),
    "공손체":  dict(deny="아닙니다", admit="…거기 없었습니다. 인정하지요",
                  saw="보지 못했지요", press="저는 그 자리를 지켰답니다", q="왜 지금 그 얘길 꺼내십니까"),
    "합쇼체":  dict(deny="아닙니다", admit="…거기 없었습니다. 인정합니다",
                  saw="보지 못했습니다", press="저는 그 자리를 지켰습니다", q="왜 지금 그 얘길 꺼내십니까"),
    "합니다체": dict(deny="아닙니다", admit="…거기 없었습니다. 인정합니다",
                  saw="보지 못했습니다", press="저는 그 자리를 지켰습니다", q="왜 지금 그 얘길 꺼내십니까"),
    "격식체":  dict(deny="아닙니다", admit="…거기 없었습니다. 인정합니다",
                  saw="보지 못했습니다", press="저는 그 자리를 지켰습니다", q="왜 지금 그 얘길 꺼내십니까"),
    "건조체":  dict(deny="아닙니다", admit="…없었습니다. 인정합니다",
                  saw="보지 못했습니다", press="그 자리를 지켰습니다", q="왜 지금입니까"),
    "하오체":  dict(deny="아니오", admit="…그 자리에 없었소. 인정하오",
                  saw="보지 못했소", press="나는 그 자리를 지켰소", q="어찌 지금 그 말을 꺼내오"),
    "정중체":  dict(deny="아니오", admit="…그 자리에 없었소. 인정하오",
                  saw="보지 못했소", press="나는 그 자리를 지켰소", q="어찌 지금 그 말을 꺼내오"),
    "탄식체":  dict(deny="아니오이다", admit="…그 자리에 없었소. 인정하오",
                  saw="보지 못했소이다", press="나는 그 자리를 지켰소", q="어찌 지금 그 말을 꺼내오"),
    "하게체":  dict(deny="아닐세", admit="…그 자리에 없었네. 인정하네",
                  saw="보지 못했네", press="나는 그 자리를 지켰네", q="어찌 지금 그 말을 꺼내는가"),
    "노숙체":  dict(deny="아닐세", admit="…그 자리에 없었네. 인정하네",
                  saw="보지 못했네", press="나는 그 자리를 지켰네", q="어찌 지금 그 말을 꺼내는가"),
    "노년체":  dict(deny="아니네", admit="…그 자리에 없었네. 인정하지",
                  saw="보지 못했지", press="나는 그 자리를 지켰네", q="어찌 지금 그 말을 꺼내는가"),
    "소인체":  dict(deny="아니옵니다", admit="…거기 없었사옵니다. 인정하옵니다",
                  saw="뵙지 못했사옵니다", press="소인은 그 자리를 지켰사옵니다", q="어찌 지금 그 말씀을 하시옵니까"),
    "올시다체": dict(deny="아니올시다", admit="…거기 없었소. 인정하오",
                  saw="보지 못했소", press="저는 그 자리를 지켰소", q="어찌 지금 그 말을 꺼내오"),
    "노라체":  dict(deny="아니니라", admit="…거기 없었노라. 인정하노라",
                  saw="보지 못했노라", press="나는 그 자리를 지켰노라", q="어찌 지금 그 말을 꺼내느냐"),
    "완곡체":  dict(deny="아니군요", admit="…거기 없었네요. 인정할게요",
                  saw="보지 못했네요", press="저는 그 자리를 지켰는걸요", q="왜 지금 그 얘길 하시는군요"),
    "반존대":  dict(deny="아니거든요", admit="…거기 없었어요. 인정할게요",
                  saw="보지 못했죠", press="난 그 자리를 지켰어요", q="왜 지금 그 얘길 해요"),
    "설명체":  dict(deny="아니더라고요", admit="…거기 없었어요. 인정할게요",
                  saw="보지 못했어요", press="저는 그 자리를 지켰어요", q="왜 지금 그 얘길 해요"),
}
_FORM_DEFAULT = _FORMS["합쇼체"]


def _f(c):
    """이 인물 말체의 상투 문형."""
    v = ((c.get("persona") or {}).get("voice")) or {}
    return _FORMS.get(v.get("form", ""), _FORM_DEFAULT)


# ── 대질을 **닫지 않는 말** (2026-08-25) ──────────────────────────────
#   대질이 자백으로 끝나면 그 자리에서 답이 나와 버린다. 어긋남만 남기고
#   닫지 않는다. 말체는 alibi.FORM의 과거 종결어미를 그대로 빌려 쓴다.
_CLOSE = {
    "어요":   ("더 드릴 말씀이 없어요.",      "…저도 다시 짚어 봐야겠어요.",   "제가 무슨 말을 해도 곧이듣지 않으실 텐데요."),
    "네요":   ("더 드릴 말씀이 없네요.",      "…저도 다시 짚어 봐야겠네요.",   "제가 무슨 말을 해도 곧이듣지 않으시겠네요."),
    "습니다": ("더 드릴 말씀이 없습니다.",    "…저도 다시 짚어 봐야겠습니다.", "제가 무슨 말을 해도 곧이듣지 않으실 겁니다."),
    "소":     ("더 할 말이 없소.",            "…나도 다시 짚어 봐야겠소.",     "내가 무슨 말을 해도 곧이듣지 않을 것이오."),
    "소이다": ("더 할 말이 없소이다.",        "…저도 다시 짚어 봐야겠소이다.", "제가 무슨 말을 해도 곧이듣지 않으실 것이올시다."),
    "더이다": ("더 할 말이 없더이다.",        "…나도 다시 짚어 봐야겠더이다.", "내가 무슨 말을 해도 곧이듣지 않으실 것이구려."),
    "답니다": ("더 드릴 말씀이 없답니다.",    "…저도 다시 짚어 봐야겠지요.",   "제가 무슨 말을 해도 곧이듣지 않으시겠지요."),
    "사옵니다": ("더 아뢸 말씀이 없사옵니다.", "…소인도 다시 짚어 봐야겠사옵니다.", "소인이 무슨 말을 하여도 곧이듣지 않으실 것이옵니다."),
    "네":     ("더 할 말이 없네.",            "…나도 다시 짚어 봐야겠네.",     "내가 무슨 말을 해도 곧이듣지 않겠지."),
    "노라":   ("더 할 말이 없노라.",          "…나도 다시 짚어 보아야겠노라.", "내가 무슨 말을 하여도 곧이듣지 않으리라."),
}


def _close(c):
    """이 인물의 (함구, 흔들림, 체념) 세 마디."""
    try:
        from alibi import FORM
        end = FORM.get(((c.get("persona") or {}).get("voice") or {}).get("form", ""), ("습니다",))[0]
    except Exception:
        end = "습니다"
    return _CLOSE.get(end, _CLOSE["습니다"])


def _voice(c):
    """이 인물의 말끝·자칭 — 대본 줄을 그 사람 말투로 읽히게 하는 최소 재료."""
    v = ((c.get("persona") or {}).get("voice")) or {}
    return {"form": v.get("form", ""), "endings": v.get("endings", []),
            "self": (v.get("self") or ["저"])[0], "habit": v.get("habit", "")}


def _exchange(kind, A, B, ctx):
    """한 질문에 **둘이 주고받는 대본**을 짠다.

    ■ 왜 (찬열이형, 2026-08-25)
        "대질심문이 의미가 있으려면 한 질문에 둘 다 대답하고, 둘이 싸우거나 대화하거나
         진술이 어긋나거나 그런 모먼트들이 있어야 할 듯"

        그전에는 양쪽 '실토 대사'만 따로 있었다. 두 사람이 마주 본 적이 없으니
        대질이 그냥 버튼 한 번이었다. 이제 **부인 → 흘림 → 반발 → 쐐기 → 실토**로
        beat를 쌓아, 관계와 어긋난 진술이 그 자리에서 드러나게 한다.

    각 줄: who(A/B) · beat(무슨 국면) · line(대사) · tone(연기 지시)
    """
    an, bn = A["name"], B["name"]
    av, bv = _voice(A), _voice(B)

    def L(who, beat, line, tone):
        sp = A if who == "A" else B
        return {"who": who, "cast_id": sp["id"], "name": sp["name"],
                "beat": beat, "line": re.sub(r"\s+", " ", line).strip(), "tone": tone,
                "voice": _voice(sp)["form"]}

    if kind == "relation":
        typ = ctx.get("type", "숨긴 사이")
        return [
            L("A", "부인", f"{bn}{_j(bn,'과/와')}는 그저 얼굴이나 아는 사이입니다. "
                          f"그 이상은 없습니다.",
              "먼저 선을 긋는다. 눈은 상대를 안 본다"),
            # ★b_view는 바이블용 3인칭 서술("~해 왔다")이라 그대로 읽히면 대사가 안 된다.
            #   관계의 갈래(type)만 빌려 **말실수처럼** 흘리는 한 줄로 짓는다.
            L("B", "흘림",
              f"…{an} 말입니까. 그 사람과는 {typ} 건으로 몇 번 얼굴을 봤지요. "
              f"…아, 지금 할 얘기는 아니군요.",
              "묻지도 않은 것을 무심코 흘린다. 말끝에서 스스로도 아차 한다"),
            L("A", "반발", f"…{bn}. 그 얘길 왜 지금 꺼냅니까.",
              "상대를 쏘아본다. 말끝이 날카로워진다"),
            L("B", "되받음", f"먼저 숨긴 건 그쪽 아닙니까. 나만 입을 다물 이유가 없지요.",
              "물러서지 않는다. 오히려 한 발 나선다"),
            # relation_web에 실토 대사가 없는 쌍이 있다(91편 등) — 말체로 지어 채운다
            L("A", "실토",
              ctx.get("a_confess") or
              f"…{typ}입니다. 숨긴 건 맞습니다. 그뿐입니다, 다른 뜻은 없습니다.",
              "체념하듯. 목소리가 낮아진다"),
            L("B", "실토",
              ctx.get("b_confess") or
              f"…저도 부인하지 않겠습니다. {an}{_j(an,'과/와')} 그런 사이인 건 사실입니다.",
              "따라서 인정한다. 변명이 섞인다"),
        ]

    if kind == "alibi":
        fa, fb = _f(A), _f(B)
        pl = ctx.get("place", "그 자리")
        return [
            L("A", "진술", ctx.get("a_claim", ""), "또박또박. 준비해 둔 말이다"),
            # b_claim은 바이블용 3인칭이라 그대로 읽히면 대사가 안 된다 — 1인칭으로 짓는다
            L("B", "반박", f"그 시각 저는 {pl}에 있었습니다. 그런데 {an}{_j(an,'은/는')} "
                          f"그 자리에 없었습니다. 제가 {fb['saw']}.",
              "담담하게. 그래서 더 무겁다"),
            L("A", "동요", f"…{bn}{_j(bn,'이/가')} 잘못 본 겁니다. 사람이 많았고, 어두웠고—",
              "말이 빨라진다. 문장이 끝나기 전에 다음 말이 붙는다"),
            L("B", "쐐기", f"어두웠으면 저도 못 봤겠지요. 그런데 {fb['press']}. "
                          f"{an}{_j(an,'은/는')} 오지 않았습니다.",
              "한 마디씩 끊어 못을 박는다"),
            # ★자백으로 끝내지 않는다 (2026-08-25).
            #   전에는 여기서 "…거기 없었어요. 인정할게요."로 끝나 대질이 답을
            #   그냥 건네줬다. 대질의 값어치는 **어긋남을 기록에 올리는 것**이지
            #   범인을 지목해 주는 것이 아니다. 어느 쪽이 거짓인지는 플레이어 몫이다.
            L("A", "함구", "…" + _close(A)[2],
              "말을 멈춘다. 그 침묵이 대답이 된다"),
        ]

    if kind == "timeline":
        pl = ctx.get("place", "그 자리")
        return [
            L("A", "진술", ctx.get("a_claim", ""), "무심하게. 흔한 대답처럼"),
            L("B", "겹침", ctx.get("b_claim", ""), "같은 자리를 댄다. 둘 다 표정이 굳는다"),
            L("A", "깨달음", f"…{pl}에 있었다면, 우리는 서로를 봤어야 합니다.",
              "천천히. 스스로 말하면서 알아차린다"),
            L("B", "균열", f"봤습니다. 말하지 않았을 뿐입니다.",
              "짧게. 더 말하면 무너질 것을 안다"),
            L("A", "머뭇", "…" + _close(A)[1],
              "시선을 피한다"),
            L("B", "함구", _close(B)[0],
              "입을 닫는다. 둘 중 하나는 사실이 아닌 말을 하고 있다"),
        ]

    # witness
    return [
        L("A", "목격", ctx.get("a_claim", ""), "본 것을 그대로 옮긴다"),
        L("B", "부인", f"제가 그랬을 리 없습니다. 잘못 보신 겁니다.",
          "즉각 부인한다. 너무 빠르다"),
        L("A", "구체", f"제가 본 것을 말했을 뿐입니다. 시각도, 자리도 기억합니다.",
          "물러서지 않는다. 담담해서 더 단단하다"),
        L("B", "흔들림", "…" + _close(B)[1],
          "잠시 침묵한 뒤. 조금 전과 말이 달라졌다"),
    ]


def build(s):
    cast = {c["id"]: c for c in s["cast"]}
    names = {i: c["name"] for i, c in cast.items()}
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    rounds = int(s["config"].get("rounds", 3))
    ds = s["death"]["time_slot"]
    cul = next((c for c in s["cast"] if c.get("is_culprit")), None)
    # ★대질은 **중반 이벤트가 터진 뒤부터** 열린다(2026-08-25).
    #   이벤트는 "판이 뒤집힌다"는 순간인데 그 뒤에 새로 열리는 것이 없었다.
    #   대질을 그 보상으로 걸면 (1) 이벤트에 의미가 생기고
    #   (2) 1회뿐인 기회를 언제 쓸지의 고민이 이벤트 뒤로 모인다.
    ev_rounds = [e.get("round") for e in (s.get("events") or []) if e.get("round")]
    unlock = min(ev_rounds) if ev_rounds else 2
    pairs = []

    def add(kind, a, b, topic, a_claim, b_claim, conflict, surfaced, ca, cb,
            round_min, reward, ctx=None):
        round_min = max(round_min, unlock)      # 이벤트 전에는 못 연다
        A, B = cast[a], cast[b]
        ex_ctx = dict(ctx or {})
        ex_ctx.update({"a_claim": _sent(a_claim, 150), "b_claim": _sent(b_claim, 150),
                       "ca": _sent(ca, 180), "cb": _sent(cb, 180)})
        exch = _exchange(kind, A, B, ex_ctx)
        pairs.append({
            "id": f"X{len(pairs)+1}",
            # ★한 질문에 둘이 주고받는 대본 — 대질의 본체
            "exchange": exch,
            "beats": [x["beat"] for x in exch],
            "kind": kind, "a": a, "b": b,
            "a_name": names.get(a, a), "b_name": names.get(b, b),
            "topic": topic,
            "a_claim": _sent(a_claim), "b_claim": _sent(b_claim),
            "conflict": conflict,
            "surfaced_by": surfaced,
            "on_confront": {"a": _sent(ca, 180), "b": _sent(cb, 180)},
            "round_min": round_min,
            "reward": reward,
            "reveals": ex_ctx.get("reveals"),   # 이 대질로 무엇이 드러나는가
        })

    # ① 숨긴 관계 — 관계망에서 public=false인 것이 곧 대질거리다
    for r in (s.get("relation_web") or []):
        a, b = r.get("a"), r.get("b")
        if a not in cast or b not in cast:
            continue                      # 피해자(V) 관계는 대질 대상이 아니다
        if r.get("public"):
            continue                      # 이미 다 아는 사이는 들이댈 것이 없다
        add("relation", a, b, r.get("type", "숨긴 사이"),
            a_claim=f"{names[a]}{_j(names[a],'은/는')} {names[b]}"
                    f"{_j(names[b],'과/와')} 특별한 사이가 아니라고 말한다.",
            b_claim=r.get("b_view", ""),
            conflict=f"한쪽은 남처럼 말하는데, 다른 쪽 말에는 {r.get('type','')}의 자취가 있다.",
            surfaced=f"두 사람 중 하나에게 {' · '.join((r.get('hook') or [])[:3])} 같은 낱말로 물은 뒤, "
                     f"그 답을 상대에게 들이댄다.",
            ca=(r.get("a_confess") or
                f"…{r.get('type','그런 사이')}입니다. 숨긴 건 맞습니다."),
            cb=(r.get("b_confess") or
                f"…저도 부인하지 않겠습니다. 그런 사이인 건 사실입니다."),
            round_min=2,
            reward="두 인물의 숨긴 관계가 공개되고, 둘 다 압박이 한 단계 오른다",
            ctx={"type": r.get("type", ""), "b_view": _sent(r.get("b_view"), 140),
                 "a_confess": _sent(r.get("a_confess"), 180),
                 "b_confess": _sent(r.get("b_confess"), 180),
                 "reveals": {"kind": "relation", "relation_type": r.get("type", ""),
                             "between": [a, b],
                             "note": "이 관계가 공개(public)로 바뀐다. "
                                     "[용의자] 화면의 두 사람 카드에 관계가 적힌다."}})

    # ② 거짓 알리바이 — 범인이 댄 자리를 실제로 지킨 사람
    for l in ((cul or {}).get("lies") or []):
        fp = l.get("false_place")
        for c in s["cast"]:
            if c["id"] == cul["id"]:
                continue
            if (c.get("timeline") or {}).get(ds) == fp:
                add("alibi", cul["id"], c["id"], "그 시각 그 자리",
                    a_claim=l.get("claim") or cul.get("alibi_narration", ""),
                    b_claim=f"{c['name']}{_j(c['name'],'은/는')} 그 시각 {pn.get(fp,'')}에 "
                            f"있었으면서 {cul['name']}{_j(cul['name'],'을/를')} "
                            f"보지 못했다고 한다.",
                    conflict=f"{cul['name']}{_j(cul['name'],'이/가')} 댄 자리를 "
                             f"{c['name']}{_j(c['name'],'이/가')} 지키고 있었는데, "
                             f"거기서 보지 못했다고 한다. 둘 중 하나는 거짓이다.",
                    surfaced=f"{c['name']}에게 그 시각 어디 있었는지 물어 두고, "
                             f"그 답을 {cul['name']}에게 들이댄다.",
                    ca=f"{_f(cul)['admit']}.",
                    cb=f"제가 그 자리에 있었습니다. {cul['name']}"
                       f"{_j(cul['name'],'은/는')} 오지 않았어요.",
                    round_min=max(2, rounds - 1),
                    reward="범인의 알리바이가 무너진다 — 결정타로 가는 문이 열린다",
                    ctx={"place": pn.get(fp, ""),
                         "reveals": {"kind": "alibi_break", "target": cul["id"],
                                     "note": "두 사람의 말이 같은 시각에 어긋난다. "
                                             "둘 중 하나는 사실이 아니다 — 어느 쪽인지는 아직 모른다."}})

    # ③ 같은 시각 같은 자리 — 둘이 같은 곳을 댔는데 서로를 못 봤다면 어긋난다
    seen = set()
    for a_id, a in cast.items():
        for b_id, b in cast.items():
            if a_id >= b_id:
                continue
            ap = (a.get("timeline") or {}).get(ds)
            bp = (b.get("timeline") or {}).get(ds)
            if not ap or ap != bp:
                continue
            key = (ap, a_id, b_id)
            if key in seen:
                continue
            seen.add(key)
            add("timeline", a_id, b_id, f"{pn.get(ap,'')}에서의 그 시각",
                a_claim=a.get("alibi_narration", ""),
                b_claim=b.get("alibi_narration", ""),
                conflict=f"둘 다 그 시각 {pn.get(ap,'')}에 있었다고 한다. "
                         f"그렇다면 서로를 봤어야 한다 — 한쪽이라도 못 봤다 하면 거짓이다.",
                surfaced=f"한 사람에게 '그 자리에 누가 또 있었느냐'를 물어 두고, "
                         f"그 답을 다른 사람에게 들이댄다.",
                ca=f"…혼자는 아니었습니다. 그건 맞습니다.",
                cb=f"…그 사람도 거기 있었습니다. 말하지 않은 건 제 사정 때문입니다.",
                round_min=1,
                reward="두 사람의 동선이 서로를 묶는다 — 한쪽이 거짓이면 함께 무너진다",
                ctx={"place": pn.get(ap, ""),
                     "reveals": {"kind": "timeline", "between": [a_id, b_id],
                                 "place": ap,
                                 "note": "두 사람이 같은 시각 같은 자리에 있었음이 확정된다. "
                                         "한쪽 진술이 거짓이면 다른 쪽도 흔들린다."}})

    # ④ 목격 — A가 아는 것(knows)이 B를 직접 가리킬 때
    for a_id, a in cast.items():
        for k in (a.get("knows") or []):
            for b_id, b in cast.items():
                if b_id == a_id:
                    continue
                if b["name"] in k and len(k) > 20:
                    add("witness", a_id, b_id, "본 것과 한 말",
                        a_claim=k,
                        b_claim=b.get("alibi_narration", ""),
                        conflict=f"{a['name']}가 본 것이 {b['name']}의 말과 맞지 않는다.",
                        surfaced=f"{a['name']}에게 그 밤에 본 것을 물어 두고, "
                                 f"그 말을 {b['name']}에게 들이댄다.",
                        ca=f"제가 본 대로 말했을 뿐입니다.",
                        cb="…그걸 봤다면, 더 감출 것도 없겠군.",
                        round_min=2,
                        reward=f"{b['name']}의 진술에 금이 간다",
                        ctx={"reveals": {"kind": "witness", "target": b_id,
                                         "note": f"{a['name']}가 본 것이 확정되고, "
                                                 f"{b['name']}의 진술에 금이 간다."}})
                    break

    # ── 솎아내기 ──────────────────────────────────────────────
    # ★플레이어 피로도(찬열이형 지적, 2026-08-24)
    #   처음엔 관계망을 전부 대질거리로 만들었더니 편당 12개까지 나왔다.
    #   단서 17 + 조합 5 + 장소보상 4 위에 대질 12를 더하면 들고 다닐 것이 40개다.
    #   대질은 '많은 것'이 아니라 '결정적인 것'이어야 한다 — 갈래별 값어치로 잘라 5개까지만.
    RANK = {"alibi": 0, "witness": 1, "timeline": 2, "relation": 3}
    MAX_PAIRS = 5
    MAX_PER_KIND = {"alibi": 2, "witness": 2, "timeline": 1, "relation": 2}
    pairs.sort(key=lambda x: RANK.get(x["kind"], 9))
    trimmed, per_pair, per_kind = [], {}, {}
    for x in pairs:
        if len(trimmed) >= MAX_PAIRS:
            break
        k = x["kind"]
        if per_kind.get(k, 0) >= MAX_PER_KIND.get(k, 1):
            continue                      # 한 갈래가 목록을 다 먹지 않게
        key = tuple(sorted([x["a"], x["b"]]))
        if per_pair.get(key, 0) >= 1:
            continue                      # 같은 두 사람은 한 번만
        per_pair[key] = per_pair.get(key, 0) + 1
        per_kind[k] = per_kind.get(k, 0) + 1
        x["id"] = f"X{len(trimmed)+1}"
        trimmed.append(x)

    ev_name = next((e.get("name","") for e in (s.get("events") or [])
                    if e.get("round") == unlock), "")
    return {
        "note": "맞대 놓으면 어긋나는 진술 쌍. 전용 '대질' 화면이 이것을 쓴다.",
        "unlock_round": unlock,
        "unlock_by": "event",
        "unlock_note": (f"{unlock}라운드의 중반 이벤트"
                        + (f"('{ev_name}')" if ev_name else "")
                        + "가 터진 뒤부터 대질할 수 있다. "
                          "그 전에는 대질 화면이 잠겨 있다."),
        "locked_copy": {
            "title": "아직 맞대 놓을 수 없다",
            "body": "사람을 맞대 놓으려면 판이 한 번 뒤집혀야 한다. "
                    "아직 그럴 만한 일이 일어나지 않았다.",
            "hint": "{r}라운드에 무슨 일이 생긴 뒤에 다시 오라.",
        },
        "how": "심문 중 [대질] → 다른 인물에게서 들은 진술을 골라 들이댄다. "
               "맞는 짝을 들이대면 두 인물이 각각 한 겹씩 실토한다.",
        "ui_copy": {
            "button": "대질한다",
            "picker": "누구의 말을 들이댈까요?",
            "empty": "아직 들이댈 만한 말을 듣지 못했습니다.",
            "hit": "말이 어긋납니다.",
            "miss": "그 말로는 걸리지 않는다.",
        },
        "rule": "들이대는 진술을 **이미 들은 뒤**여야 한다(듣지 않은 말은 고를 수 없다). "
                "한 쌍은 한 번만 성립하고, 성립하면 양쪽 압박이 한 단계씩 오른다.",
        "pairs": trimmed,
        "count": len(trimmed),
    }


def enrich(path, check=False):
    s = json.load(open(path, encoding="utf-8"))
    cx = build(s)
    if not check:
        s["cross_examination"] = cx
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    kinds = {}
    for p in cx["pairs"]:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    print(f"  {path.split('/')[-1][:28]:30s} 대질 {cx['count']:2}쌍  {kinds}")
    return cx["count"]


if __name__ == "__main__":
    check = "--check" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = args or sorted(glob.glob("scenarios/[0-9]*.json"))
    tot = 0
    for f in files:
        tot += enrich(f, check)
    print(f"\n{len(files)}편 · 대질 쌍 총 {tot}개 (편당 평균 {tot/max(1,len(files)):.1f})")
