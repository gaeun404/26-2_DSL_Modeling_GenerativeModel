# -*- coding: utf-8 -*-
"""
add_detective.py — 플레이어(탐정)의 '배역'을 시대·배경에 맞게 부여.

문제: 조선 시대 사건에 '탐정'이 등장하면 몰입이 깨진다.
해결: 문화권·시대·현장 성격에 맞는 수사 주체를 배정하고,
      그 역할이 가진 **권한(무엇을 할 수 있나)**·**한계(무엇은 못 하나)**·
      **호칭(용의자들이 나를 뭐라 부르나)**·**등장 사유**까지 정의한다.
      → 심문 말투, 강제력(체포·문초 가능 여부), 나레이션 호칭에 직접 쓰인다.

s["detective"] = {
  role, title, honorific, authority[], limits[], entry_reason,
  address_by_suspects{인물id: 호칭}, opening_line, speech_register
}
사용: python add_detective.py
"""
import json, glob, sys

# 문화권/배경 → 수사 주체 후보
ROLES = {
 "korea_folk": dict(
   role="고을 사또(수령)", title="사또", honorific="사또 나리",
   authority=["관아의 이름으로 문초할 수 있다","증인을 불러 대질시킬 수 있다","가택과 곳간을 수색할 수 있다","죄가 드러나면 그 자리에서 결박할 수 있다"],
   limits=["양반가의 안채는 함부로 들 수 없어 예를 갖춰야 한다","증좌 없이 형장을 쓰면 도리어 탄핵당한다","날이 밝기 전에 매듭지어야 한다"],
   entry_reason="변사 소식을 듣고 관아에서 검시관을 데리고 나섰다",
   register="위엄 있는 하게체·하오체. '이실직고하라', '바른대로 아뢰어라'"),
 "korea_court": dict(
   role="의금부 도사", title="도사", honorific="도사 나리",
   authority=["왕명을 받들어 궁인을 추국할 수 있다","궁의 문서와 장부를 열람할 수 있다","궁녀·내관의 처소를 봉쇄할 수 있다"],
   limits=["윗전의 체면을 상하게 하면 안 된다","확증 없이 상궁을 형추할 수 없다","궁 밖으로 소문이 새면 큰 화가 된다"],
   entry_reason="별궁에서 변고가 났다는 기별에 왕명을 받고 들었다",
   register="절제된 하게체. '아뢰라', '숨김없이 고하라'"),
 "korea_buddhist": dict(
   role="관아에서 나온 검률(檢律)", title="검률", honorific="검률 나리",
   authority=["절의 재물과 장부를 조사할 수 있다","승려를 불러 문초할 수 있다","검시 결과를 관에 올릴 수 있다"],
   limits=["부처의 도량에서 형장을 쓸 수 없다","큰스님의 허락 없이 선방에 들 수 없다"],
   entry_reason="산사에서 사람이 죽었다는 기별을 받고 검시하러 올랐다",
   register="차분한 하오체. 예를 갖추되 물러서지 않는다"),
 "china_tang": dict(
   role="현령(縣令)", title="현령", honorific="현령 나리",
   authority=["관아의 권한으로 신문할 수 있다","저택을 봉쇄할 수 있다","오작인을 시켜 검시할 수 있다"],
   limits=["권세가의 심기를 거스르면 자리가 위태롭다","증좌 없이 형을 쓸 수 없다"],
   entry_reason="관할에서 변사가 났다는 보고에 직접 나섰다",
   register="위엄 있는 하오체"),
 "japan_ancient": dict(
   role="검비위사(檢非違使)", title="검비위사", honorific="나리",
   authority=["도읍의 치안을 맡아 누구든 잡아 문초할 수 있다","시신을 검분할 수 있다","성문 출입을 통제할 수 있다"],
   limits=["기근으로 관의 힘이 약해 유민들이 순순히 따르지 않는다","증인이 모두 굶주린 처지라 말을 바꾸기 쉽다"],
   entry_reason="폐성문에서 시신이 나왔다는 말을 듣고 순찰 중 들렀다",
   register="건조한 하오체. 위압보다 관찰로 누른다"),
 "medieval_europe": dict(
   role="영주가 보낸 순회 재판관", title="재판관", honorific="재판관님",
   authority=["영주의 이름으로 심문할 수 있다","증인을 소환해 선서시킬 수 있다","저택과 창고를 수색할 수 있다","혐의가 굳으면 구금할 수 있다"],
   limits=["귀족과 성직자에겐 함부로 손댈 수 없다","증좌 없이 판결하면 영주의 신망을 잃는다"],
   entry_reason="영지에서 변사가 났다는 전갈을 받고 말을 달려 도착했다",
   register="격식 있는 존댓말. '진술하시오', '선서하고 답하시오'"),
 "nordic": dict(
   role="마을 회의가 뽑은 재판 주재자(로그세그만)", title="주재자", honorific="주재자님",
   authority=["마을 회의의 이름으로 신문할 수 있다","집과 창고를 열게 할 수 있다","증인을 회의 앞에 세울 수 있다"],
   limits=["강제력은 마을의 동의에 기댄다","눈보라가 그치기 전엔 바깥의 도움을 못 받는다"],
   entry_reason="축제의 밤에 사람이 죽자 마을 회의가 진상을 맡겼다",
   register="담백한 존댓말. 권위보다 공동체의 신뢰로 묻는다"),
 "modern_europe": dict(
   role="시경(市警) 형사", title="형사", honorific="형사님",
   authority=["시경의 권한으로 신문할 수 있다","검시의를 불러 부검 소견을 받을 수 있다","장부와 서류를 압수할 수 있다","용의자를 유치할 수 있다"],
   limits=["유력자의 압력이 들어온다","영장 없이 사택을 뒤질 수 없다"],
   entry_reason="섣달그믐 밤 공장에서 변사가 났다는 신고를 받고 출동했다",
   register="건조한 존댓말. 사실 확인 위주"),
 "modern": dict(
   role="사립 탐정", title="탐정", honorific="탐정님",
   authority=["의뢰인의 위임으로 관계자를 만나 물을 수 있다","현장 사진·기록을 열람할 수 있다","경찰 지인을 통해 검시 소견을 받아볼 수 있다","증거를 모아 경찰에 넘길 수 있다"],
   limits=["체포·구금 권한이 없다 — 오직 말과 증거로 압박해야 한다","상대가 대화를 거부하면 강제할 수 없다","무단 수색은 증거 능력을 잃게 만든다"],
   entry_reason="의뢰를 받고 사건 현장에 도착했다",
   register="차분한 존댓말. 위압 대신 관찰과 논리로 파고든다"),
 "contemporary_police": dict(
   role="강력계 형사", title="형사", honorific="형사님",
   authority=["임의동행·신문을 요청할 수 있다","영장으로 압수수색할 수 있다","과학수사대 감식 결과를 받을 수 있다","긴급체포할 수 있다"],
   limits=["미란다 원칙을 지켜야 한다","영장 없이 사생활을 뒤질 수 없다","진술거부권을 존중해야 한다"],
   entry_reason="112 신고를 받고 현장에 출동했다",
   register="건조한 존댓말. 절차를 지키며 사실을 확인"),
 "greek_myth": dict(
   role="신전이 세운 조사관(테스모테테스)", title="조사관", honorific="조사관님",
   authority=["신전의 이름으로 증언을 요구할 수 있다","신 앞의 맹세를 받아낼 수 있다","성역을 조사할 수 있다"],
   limits=["신탁을 거스를 수 없다","사제에겐 예를 갖춰야 한다"],
   entry_reason="성역에서 피가 흘렀다는 소식에 신전이 진상을 명했다",
   register="엄정한 존댓말. 맹세와 신의를 근거로 압박"),
}

def pick(s):
    key=(s.get("bgm",{}).get("palette",{}) or {}).get("culture_key")
    if key in ROLES: return key
    sr=s["background"]["setting_raw"]; blob=" ".join(str(v) for v in sr.values())
    if "궁중" in blob: return "korea_court"
    if "사찰" in blob or "불교" in blob: return "korea_buddhist"
    if "그리스" in blob: return "greek_myth"
    if "북구" in blob or "북유럽" in blob: return "nordic"
    if any(k in blob for k in ["현대","21세기","20세기 말","도시 아파트","스마트","오늘날"]):
        return "contemporary_police" if any(k in blob for k in ["경찰","형사","수사대"]) else "modern"
    if "근대" in blob or "19세기" in blob: return "modern_europe"
    if "유럽" in blob or "중세" in blob: return "medieval_europe"
    return "korea_folk"

def build(s):
    key=pick(s); R=ROLES[key]
    # 용의자별 호칭: 신분에 따라 다르게 부른다(하인은 굽신, 양반·성직자는 대등하게)
    addr={}
    for c in s["cast"]:
        st=(c.get("profile",{}).get("status","") or "")+(c.get("public","") or "")
        if any(k in st for k in ["하인","방자","마름","심부름","유민","하녀","행랑","거간","장수","무당","병자"]):
            addr[c["id"]]=f"{R['honorific']}, 소인이…"
        elif any(k in st for k in ["상궁","내관","승","사제","여사제","재상","좌수","부자","영주","공장주","읍장","선주"]):
            addr[c["id"]]=f"{R['title']}께서 어인 일로…"
        else:
            addr[c["id"]]=f"{R['honorific']}…"
    return {
      "role":R["role"], "title":R["title"], "honorific":R["honorific"],
      "authority":R["authority"], "limits":R["limits"],
      "entry_reason":R["entry_reason"], "speech_register":R["register"],
      "address_by_suspects":addr,
      "opening_line":f"나는 {R['role']}. {R['entry_reason']}. 이 자리에서 누구도 거짓을 고할 수 없다.",
      "note":"용의자 에이전트는 플레이어를 이 배역으로 인식하고 그에 맞는 호칭·태도로 답해야 한다. "
             "권한(authority)은 플레이어가 쓸 수 있는 압박 수단, 한계(limits)는 게임적 제약이다."
    }

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/[0-9]*.json"
    from collections import Counter
    cnt=Counter()
    for p in sorted(glob.glob(arg)):
        s=json.load(open(p,encoding="utf-8"))
        s["detective"]=build(s)
        cnt[s["detective"]["role"]]+=1
        json.dump(s,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        print(f"  🕵 {p.split('/')[-1]:26} → {s['detective']['role']} ({s['detective']['honorific']})")
    print(f"\n역할 {len(cnt)}종: {dict(cnt)}")
