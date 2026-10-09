# -*- coding: utf-8 -*-
"""fix_clue_names.py — **단서 이름을 사람이 읽을 수 있게 다시 짓는다.**

■ 왜 (2026-08-29, 시연 제보)
  화면에 「24시간 독」이라는 단서가 떴다. 본문은 자판기 CCTV 이야기인데
  이름은 **다른 문장에서 낱말 가운데를 잘라** 온 것이었다("24시간 독서실" → "24시간 독").
  이름은 목록에서 그 단서를 기억하는 손잡이다. 손잡이가 깨져 있으면 수첩이 안 읽힌다.

■ 무엇을 고치나 (세 가지만 — 멀쩡한 이름은 건드리지 않는다)
  ① 잘림      「24시간 독」 「돌린 재」 — 낱말 가운데가 끊긴 것
  ② 겹말      「이시백의 증언의 진술」 — '증언'과 '진술'이 겹친 것
  ③ 갈래 어긋남 「엇갈린 증언」인데 본문이 증언이 아닌 것

■ 어떻게 짓나
  본문 첫 마디에서 **머리 명사구**를 뽑는다. 한국어는 뒤가 머리이므로
  명사로 끝나면 뒤 두 낱말을, 서술어로 끝나면 앞 두 낱말을 쓴다.
  증언·소문처럼 꼴이 정해진 것은 그 꼴을 그대로 쓴다.

사용:
    python3 src/fix_clue_names.py --check     # 무엇이 어떻게 바뀌는지만 본다
    python3 src/fix_clue_names.py             # 고쳐 쓴다
"""
import json, glob, re, argparse, os

JOSA = ("의", "을", "를", "이", "가", "은", "는", "에", "로", "와", "과", "도", "만",
        "께", "한테", "부터", "까지", "이나", "나", "에서", "으로", "라는", "이라",
        "라고", "이라고", "였", "이었", "입니", "이다", "엔", "엘", "께서")
# 서술어로 끝나는가 — 그러면 명사구가 아니다
VERB_END = re.compile(r"(다|나|고|며|서|지만|는데|하여|해서|았|었|했|한다|된다|이다|있다|없다|온|간|진|린|킨|난|운|은)$")
SPEECH = re.compile(r"['\"「『]")
# 갈래를 가리키는 이름 — 본문에 그 낱말이 없어도 멀쩡한 이름이다
GENERIC = {"검험", "검안", "소견", "증언", "진술", "소문", "감정", "재확인", "현장",
           "기록", "장부", "서찰", "문서", "흔적", "물증", "목격담", "확인",
           "검안서", "검험서", "부검", "주검", "시신", "초상", "낙인"}
# 이미 좋은 이름 — 본문에 그 낱말이 없어도 손대지 않는다
GOOD = {"떠도는 소문", "엇갈린 증언", "창상·흉기 감정"}


def _truncated(nm, de):
    """이름 바로 뒤에 조사도 경계도 아닌 글자가 붙어 있으면 = 잘린 것."""
    if not nm:
        return False
    for m in re.finditer(re.escape(nm), de):
        nxt = de[m.end():m.end() + 3]
        if not nxt:
            return False
        if nxt[0] in " ·—,.'\"」)\n":
            return False
        if any(nxt.startswith(j) for j in JOSA):
            return False
        return True
    return False


def _strip_josa(w):
    for j in sorted(JOSA, key=len, reverse=True):
        if w.endswith(j) and len(w) - len(j) >= 2:
            return w[:-len(j)]
    return w


def new_name(de, medium=""):
    """본문에서 이름을 짓는다."""
    de = str(de or "").strip()
    if not de:
        return None

    # ① 「사람들 사이에 도는 말」류 — 소문
    if re.match(r"^(사람들|마을|장터|이웃|옆).{0,12}(도는 말|소문)", de):
        return "떠도는 소문"
    if re.match(r"^또 다른 사람도 같은 말", de):
        return "엇갈린 증언"

    # ② 「누가의 증언: '…'」 / 「누가: '…'」 — 증언
    m = re.match(r"^([가-힣A-Za-z][가-힣A-Za-z ]{1,14}?)(?:의 (?:증언|말|진술))?\s*[:：]", de)
    if m and SPEECH.search(de[:80]):
        who = m.group(1).strip()
        who = re.sub(r"(의 (증언|말|진술))$", "", who).strip()
        if 2 <= len(who) <= 14:
            return f"{who}의 증언"

    # ③ 「…에서 나온, 무엇」 꼴이면 **무엇**이 이름이다
    #    (전에는 쉼표에서 끊어 「정씨 자개농에서 나온」 같은 토막이 나왔다)
    clause = re.split(r"[—:：.·]|\s-\s", de)[0].strip()
    m2 = re.search(r"나온[,\s]+(.+)$", clause)
    if m2:
        clause = m2.group(1).strip()
    clause = re.sub(r"^【[^】]*】\s*", "", clause).strip()
    words = [w for w in clause.split() if w]
    if not words:
        return None
    # 앞머리의 소유격(‘…의’)은 떼어 낸다 — 「헨젤의 쇠우리 창살」→「쇠우리 창살」
    if len(words) >= 3 and words[0].endswith("의"):
        words = words[1:]
    if len(" ".join(words)) <= 12:
        cand = " ".join(words)
    elif VERB_END.search(words[-1]):
        # 서술어로 끝난다 → 앞머리를 쓴다.
        #   「서재는 안에서 잠겼고」에서 두 낱말을 집으면 「서재는 안」이 된다.
        #   주격·주제 조사가 붙은 첫 낱말은 그 자체가 주어이므로 **그것만** 쓴다.
        cand = (_strip_josa(words[0]) if re.search(r"(은|는|이|가)$", words[0])
                else " ".join(words[:2]))
    else:
        cand = " ".join(words[-2:])         # 명사로 끝난다 → 뒤가 머리다
    cand = _strip_josa(cand.strip())
    cand = re.sub(r"[('\"「『].*$", "", cand).strip()
    if len(cand) < 2 or len(cand) > 14:
        cand = _strip_josa(words[0])
    return cand or None


LEAD_DROP = ("나온", "나온,", "현장과", "함께")
LEAD_JOSA = ("과", "와", "에게", "엔", "에서", "으로", "에", "을", "를")


def extend(nm, de):
    """잘린 이름을 **그 낱말 끝까지만** 늘린다. 「돌린 재」→「돌린 재산」

    ★뒤 낱말까지 끌어오면 「나온 향임들과 주고받」처럼 서술어가 딸려 온다.
      끊긴 낱말 하나만 온전히 만들고, 앞에 붙은 이음말은 떼어 낸다.
    """
    i = de.find(nm)
    if i < 0:
        return None
    j = i + len(nm)
    while j < len(de) and re.match(r"[가-힣A-Za-z0-9]", de[j]):
        j += 1
    out = de[i:j].strip()
    words = out.split()
    # 앞머리 이음말 떼기 — 「나온 향임들」→「향임들」, 「손잡이엔 약초」→「약초」
    while len(words) > 1 and (words[0] in LEAD_DROP
                              or any(words[0].endswith(x) for x in LEAD_JOSA)):
        words = words[1:]
    out = _strip_josa(" ".join(words).strip())
    return out if 2 <= len(out) <= 14 else None


def audit(s):
    """고쳐야 할 카드만 골라 (카드, 까닭, 새 이름) 로 돌려준다."""
    out = []
    for c in (s["ui"].get("clue_cards") or []):
        nm = str(c.get("name") or "").strip()
        de = str(c.get("description") or "")
        why = None
        if nm in GOOD:
            continue
        if not nm:
            why = "이름 없음"
        elif re.search(r"(증언|진술|녹음|영상|말|소문)의 (진술|증언)$", nm):
            why = "겹말"
        elif _truncated(nm, de):
            why = "잘림"
        elif re.search(r"(증언|진술)$", nm) and not SPEECH.search(de[:80]) \
                and "증언" not in de and "말:" not in de:
            why = "갈래 어긋남"
        # ④ 이름의 낱말이 본문에 아예 없다 — 딴 단서에서 따온 것
        #    「24시간 독」이 자판기 CCTV 단서에 붙어 있었다.
        elif (lambda ws: ws and not all(w in GENERIC for w in ws)
                     and not any(w in de for w in ws)
                     and not any(re.search(r"[가-힣]*" + re.escape(w[:2]), de) for w in ws if len(w) >= 3))(
                [_strip_josa(w) for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", nm)]):
            why = "오배정"
        # ⑤ 두 글자짜리 이름이 본문 **뒷자락에서만** 나온다 — 손잡이 구실을 못 한다
        #    「입구」(시럽 병 입구), 「샷추」(샷추가) 같은 것.
        elif (len(nm.replace(" ", "")) <= 2 and nm not in GENERIC
              and nm not in de[:40]):
            why = "약한 이름"
        if why:
            nn = extend(nm, de) if why == "잘림" else None
            # 늘린 결과가 서술어 토막이거나 너무 짧으면 새로 짓는다
            if nn and (VERB_END.search(nn.split()[-1]) or len(nn) < 3):
                nn = None
            if not nn:
                nn = new_name(de)
            # 새 이름이 더 나쁘면 그냥 둔다 — 첫 낱말이 한 글자면 토막이다
            if why in ("약한 이름", "오배정") and nn:
                last = nn.split()[-1]
                bad = (len(nn) < 3 or len(nn.split()[0]) < 2
                       or VERB_END.search(last) or re.search(r"(면|다|음)$", last)
                       or nn.startswith("사인")
                       or (len(nm) >= 4 and len(nn) <= len(nm)))   # 더 짧아지면 개선이 아니다
                if bad:
                    nn = None
            if nn and nn != nm:
                out.append((c, why, nn))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = [f for f in sorted(glob.glob("scenarios/*.json")) if "catalog" not in f]
    n = 0
    for f in files:
        s = json.load(open(f, encoding="utf-8"))
        rows = audit(s)
        if not rows:
            continue
        print(f"── {os.path.basename(f)}")
        for c, why, nn in rows:
            print(f"   [{why:6s}] {c['id']:4s} 「{c['name']}」 → 「{nn}」")
            if not a.check:
                c["name"] = nn
            n += 1
        if not a.check:
            json.dump(s, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n{'고칠' if a.check else '고친'} 이름 {n}개")


if __name__ == "__main__":
    main()
