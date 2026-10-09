# -*- coding: utf-8 -*-
"""
add_search.py — '검색창(고문서·검안 사전)' 메커닉을 스키마에 주입.

배경: 검안서/단서에 나오는 낯선 말(시반, 강직, 규조토, 교흔…)을 플레이어가
      직접 찾아보며 추리하도록. 'No Results Found'의 핵심 루프를 차용:
      **검색 → 정보 → 추론 → 새 검색어** 의 순환, 그리고 의미 없는 검색은 '결과 없음'.

구조:
  s["search"] = {
    "ui": {...},                       # 검색창 UI 규칙(자동완성 없음 등)
    "index": [ {term, aliases[], category, entry, teaches, unlocks[], gated_by, spoiler_safe} ],
    "no_result_responses": [...],      # 헛detection 시 문구
    "chains": [ [term1, term2, ...] ]  # 검색어가 새 검색어를 낳는 실제 경로(검증용)
  }

원칙(스포일러 방지):
  - 어떤 항목도 '범인 이름'을 직접 말하지 않는다. 흉기·수법·해석의 '지식'만 준다.
  - 결정적 단서와 같은 라운드 이전엔 잠기는 항목은 gated_by=round 로 표시.
사용: python add_search.py
"""
import json, glob, sys, re

# ── 공용 법의학·수사 용어 사전(검안서에 자주 나오는 말) ───────────────
FORENSIC = {
 "시반": dict(cat="검안", aliases=["屍斑","시체 얼룩"],
   entry="주검이 굳으며 피가 아래로 쏠려 살갗에 생기는 검붉은 얼룩. 눕힌 자세에 따라 생기는 자리가 정해지므로, "
         "시반의 위치가 발견된 자세와 어긋나면 **주검을 옮겼다는 뜻**이다.",
   teaches="시반과 자세가 어긋나면 사후에 시신을 옮긴 것", unlocks=["사후 이동","사망 시각"]),
 "사후 강직": dict(cat="검안", aliases=["강직","시체 굳음","屍剛"],
   entry="숨이 끊긴 뒤 몸이 서서히 굳는 현상. 대개 몇 시진에 걸쳐 턱·목부터 굳어 온몸에 퍼진다. "
         "굳은 정도를 보면 **죽은 지 얼마나 지났는지**를 가늠할 수 있다.",
   teaches="강직 정도로 사망 시각을 좁힐 수 있다", unlocks=["사망 시각"]),
 "사망 시각": dict(cat="수사", aliases=["사망시각","죽은 때"],
   entry="시반·강직·체온, 그리고 마지막으로 살아 있는 것을 본 증언을 겹쳐 좁힌다. "
         "사망 시각이 정해져야 **그 시각의 알리바이**가 의미를 갖는다.",
   teaches="사망 시각이 알리바이 심문의 기준이 된다", unlocks=["알리바이","동선"]),
 "알리바이": dict(cat="수사", aliases=["부재증명"],
   entry="사건이 벌어진 그 시각에 다른 곳에 있었다는 증명. 본인의 말만으로는 성립하지 않고 "
         "**그 자리를 함께 본 사람(증인)**이 있어야 한다. 증인이 없거나, 증인이 부인하면 알리바이는 무너진다.",
   teaches="증인 없는 알리바이는 알리바이가 아니다", unlocks=["교차검증","동선"]),
 "교차검증": dict(cat="수사", aliases=["대질","맞대보기"],
   entry="한 사람의 말을 다른 사람의 말·장소의 흔적과 맞대어 보는 것. "
         "'그 자리에 있었다'는 주장은 **그 자리를 지킨 사람에게 되물어** 깨뜨린다.",
   teaches="용의자 주장을 다른 용의자에게 되물어라", unlocks=["동선"]),
 "동선": dict(cat="수사", aliases=["행적","이동 경로"],
   entry="시간대마다 누가 어디에 있었는지의 자취. 두 곳 사이를 오갈 만한 시간이 없었다면 그 진술은 거짓이다. "
         "지도의 거리와 시간대를 함께 보라.",
   teaches="지도상 거리와 시간이 맞지 않으면 거짓 진술", unlocks=["교차검증"]),
 "사후 이동": dict(cat="검안", aliases=["시신 옮김","유기"],
   entry="죽은 뒤 주검을 다른 곳으로 옮긴 것. 시반의 자리, 끌린 자국, 신발·옷에 묻은 흙으로 드러난다. "
         "**발견된 곳이 곧 죽은 곳은 아니다.**",
   teaches="발견 장소와 살해 장소가 다를 수 있다", unlocks=["현장 보존"]),
 "현장 보존": dict(cat="수사", aliases=["현장"],
   entry="누군가 손대기 전의 현장이 가장 많이 말한다. 물건이 부자연스럽게 놓였거나 지나치게 정돈되었다면 "
         "**꾸며진 현장(위장)**을 의심하라.",
   teaches="지나치게 그럴듯한 현장은 위장을 의심", unlocks=["위장"]),
 "위장": dict(cat="수사", aliases=["자살 위장","사고 위장","꾸민 현장"],
   entry="타살을 자살·사고·병사처럼 보이게 꾸미는 것. 꾸민 자는 반드시 '보여주고 싶은 것'을 남기는데, "
         "그 과잉이 도리어 흔적이 된다. 스스로 할 수 없는 상처(등 뒤·손목 결박 등)가 결정적이다.",
   teaches="스스로 만들 수 없는 상처가 위장을 깬다", unlocks=["방어흔"]),
 "방어흔": dict(cat="검안", aliases=["방어 상처","저항흔"],
   entry="맞서 막다가 손·팔에 생기는 상처. 방어흔이 없다면 **갑작스러웠거나, 경계하지 않은 상대**였다는 뜻이다.",
   teaches="방어흔이 없으면 아는 사람이거나 기습", unlocks=["면식범"]),
 "면식범": dict(cat="수사", aliases=["아는 사람","안면"],
   entry="피해자가 경계 없이 곁을 내준 상대. 문이 부서지지 않았고 저항 흔적이 없다면 **집안·가까운 사람**을 먼저 본다.",
   teaches="저항 없는 죽음은 가까운 자를 가리킨다", unlocks=[]),
 "다잉메시지": dict(cat="수사", aliases=["유언 흔적","죽어가며 남긴 것"],
   entry="숨이 끊기기 전 남긴 표식. 글자 그대로가 아니라 **손에 닿는 것으로 급히 만든 상징**일 때가 많아, "
         "가진 물건·모양·자리와 맞춰 읽어야 한다. 누군가 사후에 바꿔 놓았을 수도 있다.",
   teaches="다잉메시지는 상징으로 해독하고 조작 가능성도 본다", unlocks=["위장"]),
}
# ── 흉기/수법별 전문 용어 ─────────────────────────────────────────────
BY_WEAPON = {
 "익사": {
  "규조토": dict(cat="검안", aliases=["규조","물속 흙"],
    entry="물속의 아주 작은 흙·미생물. 살아서 물에 빠지면 숨을 쉬며 이것이 몸속 깊이 들어가지만, "
          "**죽은 뒤 물에 넣으면 들어가지 않는다.** 물에 빠져 죽었는지 아닌지를 가른다.",
    teaches="폐 속 규조 유무로 익사인지 사후 유기인지 구분", unlocks=["익사","사후 이동"]),
  "익사": dict(cat="검안", aliases=["물에 빠짐","溺死"],
    entry="물을 들이마셔 숨이 막혀 죽는 것. 입가에 흰 거품, 손에 물풀·진흙을 움켜쥔 자국이 남는다. "
          "**손목이 묶여 있다면 스스로 든 것이 아니다.**",
    teaches="결박 흔적이 있으면 자살 익사가 아니다", unlocks=["결박흔","위장"]),
  "결박흔": dict(cat="검안", aliases=["끈 자국","묶인 자국"],
    entry="끈으로 묶였던 자리에 남는 눌린 자국. 손목 안쪽까지 고르게 남았다면 **스스로 묶을 수 없는 방식**이다.",
    teaches="스스로 만들 수 없는 결박흔=타살", unlocks=["위장"]),
 },
 "교살": {
  "삭흔": dict(cat="검안", aliases=["끈 자국","목 졸린 자국","索痕"],
    entry="목을 조른 끈이 남긴 자국. 목맴(자살)은 자국이 귀 뒤로 비스듬히 올라가고, "
          "**남이 조르면 목을 수평으로 감는다.** 각도가 자살과 타살을 가른다.",
    teaches="삭흔의 각도로 목맴과 교살을 구분", unlocks=["위장","방어흔"]),
  "설골": dict(cat="검안", aliases=["목뿔뼈"],
    entry="목 안쪽의 작은 뼈. 손이나 끈으로 세게 조르면 부러지는 일이 있어 **강한 압박의 증거**가 된다.",
    teaches="설골 골절은 강한 압박(교살)의 증거", unlocks=["교살"]),
 },
 "자상": {
  "자창": dict(cat="검안", aliases=["찔린 상처","刺創"],
    entry="찔려 생긴 상처. 상처의 **너비는 날의 폭, 깊이는 찌른 힘**을 말한다. 상처 모양이 흉기를 특정한다.",
    teaches="자창의 모양으로 흉기 종류를 특정", unlocks=["흉기 특정","방어흔"]),
  "흉기 특정": dict(cat="수사", aliases=["흉기"],
    entry="상처의 모양·깊이·간격을 도구와 맞춰 보는 일. 가는 침 자국은 바늘·비녀·방추처럼 **가늘고 뾰족한 것**만 낼 수 있어, "
          "그 도구를 다루는 손을 가진 자로 범위가 좁혀진다.",
    teaches="흉기가 특정되면 그것을 다루는 직업·솜씨로 좁혀진다", unlocks=["직업 특정"]),
  "직업 특정": dict(cat="수사", aliases=["솜씨","손버릇"],
    entry="도구를 다루는 솜씨는 몸에 밴다. 바느질·시체 다루기·실 잣기처럼 **손에 익은 자만 낼 수 있는 흔적**이 있다.",
    teaches="흔적의 '능숙함'이 직업을 가리킨다", unlocks=[]),
 },
 "둔기": {
  "함몰골절": dict(cat="검안", aliases=["함몰","깨진 두개"],
    entry="무거운 것에 맞아 뼈가 안으로 꺼진 상처. 자국의 모양이 **때린 물건의 단면**을 그대로 남긴다.",
    teaches="함몰 자국 모양이 둔기의 종류를 알려준다", unlocks=["흉기 특정"]),
  "흉기 특정": dict(cat="수사", aliases=["흉기"],
    entry="상처 모양과 물건의 단면을 맞춰 보는 일. 무거운 둔기를 들어 급소를 정확히 내리치려면 "
          "**팔심 있는 자**라야 하므로, 노약자는 범위에서 빠진다.",
    teaches="둔기 살인은 완력 있는 자로 좁혀진다", unlocks=["직업 특정"]),
  "직업 특정": dict(cat="수사", aliases=["솜씨","완력"],
    entry="힘 쓰는 일을 하는 자의 손과 어깨엔 그 자취가 남는다. 누가 그 무게를 다룰 수 있었는지 보라.",
    teaches="완력의 유무가 용의자를 가른다", unlocks=[]),
 },
 "독살": {
  "비상": dict(cat="약재", aliases=["砒霜","비소","독약"],
    entry="예로부터 쓰인 흰 가루 독. 조금씩 오래 쓰면 병으로 앓다 죽은 것처럼 보여 **지병사로 오인**되기 쉽다. "
          "구토·복통이 되풀이되고, 손톱에 흰 줄이 생기기도 한다.",
    teaches="만성 비상 중독은 지병사로 위장된다", unlocks=["지병사 위장","약재 접근"]),
  "지병사 위장": dict(cat="수사", aliases=["병사 위장"],
    entry="본래 앓던 병으로 죽은 것처럼 꾸미는 것. 앓던 사람이 갑자기 죽으면 아무도 의심하지 않기에, "
          "**약을 올리던 사람**이 가장 유리하다.",
    teaches="약·음식을 다룬 사람이 유력해진다", unlocks=["약재 접근"]),
  "약재 접근": dict(cat="수사", aliases=["약방","탕약"],
    entry="독을 구하고 다룰 수 있었던 자의 범위. 약재를 만지는 일을 하거나 약방에 드나든 자로 좁혀진다.",
    teaches="독을 구할 수 있던 자로 범위가 좁혀진다", unlocks=[]),
 },
 "밀실": {
  "밀실": dict(cat="수사", aliases=["잠긴 방","안에서 걸린 문"],
    entry="안에서 잠긴 방에서 사람이 죽은 상황. 대개 **잠금 장치가 정말 잠겼는지, 다른 출입구가 있는지, "
          "누가 열쇠를 쥐었는지** 셋 중 하나에서 깨진다.",
    teaches="밀실은 열쇠 소지자·다른 출입구·잠금 조작에서 깨진다", unlocks=["열쇠 관리","숨은 공간"]),
  "열쇠 관리": dict(cat="수사", aliases=["열쇠"],
    entry="잠긴 곳의 열쇠를 누가 언제 쥐었는지의 기록. **열쇠를 쥔 자만이 드나들 수 있었다면** 범위는 그 사람뿐이다.",
    teaches="열쇠 소지자가 밀실의 유일한 출입자", unlocks=[]),
  "숨은 공간": dict(cat="수사", aliases=["비밀 통로","이중벽"],
    entry="도면과 실제 크기가 어긋나는 자리에 숨은 방·통로가 있다. **밖에서 잰 길이와 안에서 잰 길이의 차이**를 보라.",
    teaches="치수 차이가 숨은 공간을 드러낸다", unlocks=[]),
 },
 "소실": {
  "융해 흉기": dict(cat="검안", aliases=["사라진 흉기","녹는 흉기"],
    entry="찌른 뒤 스스로 사라지는 흉기가 있다. 얼음처럼 **녹아 물이 되는 것**이 대표적이라, "
          "현장에 흉기가 없는데 예리한 상처만 남고 바닥엔 물자국이 남는다.",
    teaches="흉기 없는 예리한 상처 + 물자국 = 얼음 흉기", unlocks=["흉기 특정","직업 특정"]),
  "흉기 특정": dict(cat="수사", aliases=["흉기"],
    entry="사라진 흉기는 '무엇이 사라질 수 있었나'로 되짚는다. 얼음을 깎아 다룰 줄 아는 자, "
          "그 성질을 아는 자가 범위에 든다.",
    teaches="사라지는 흉기를 아는 지식이 범인을 좁힌다", unlocks=["직업 특정"]),
  "직업 특정": dict(cat="수사", aliases=["솜씨"],
    entry="물·얼음·약의 성질을 다루는 일을 하는 자에게 그 지식이 있다.",
    teaches="전문 지식의 소유자가 유력해진다", unlocks=[]),
 },
}


# ── 어떤 사건이든 검안서에 흔히 등장하는 공통 낱말(검색해서 '없음'이 뜨면 안 되는 것) ──
CORE = {
 "혈흔": dict(cat="검안", aliases=["핏자국","피 흔적"],
   entry="튄 피·흐른 피의 자취. **모양과 방향**이 힘의 세기와 사람이 서 있던 자리를 알려 준다. "
         "피가 닦이거나 옮겨진 자리는 도리어 손댄 자를 가리킨다.",
   teaches="혈흔의 방향·모양이 범행 자세를 재현한다", unlocks=["현장 보존","사후 이동"]),
 "충격흔": dict(cat="검안", aliases=["타격흔","맞은 자국"],
   entry="맞아서 생긴 자국. 단면 모양이 때린 물건을 그대로 남기며, 한 번인지 여러 번인지가 **격정인지 계획인지**를 시사한다.",
   teaches="타격 횟수와 자국 모양이 도구와 심리를 말한다", unlocks=["흉기 특정","완력"]),
 "골절": dict(cat="검안", aliases=["뼈 부러짐","부러진 뼈"],
   entry="뼈가 부러지거나 꺼진 상처. 부러진 자리와 방향으로 **어느 쪽에서 얼마의 힘이 왔는지**를 안다.",
   teaches="골절의 방향이 가해 방향과 힘을 알려준다", unlocks=["완력","흉기 특정"]),
 "중독": dict(cat="약재", aliases=["독", "약물"],
   entry="독이 몸에 퍼져 생기는 증상. 갑작스러운 것과 오래 쌓인 것이 다르며, 오래 쌓인 독은 **앓던 병처럼 보인다.**",
   teaches="만성 중독은 병사로 오인된다", unlocks=["지병사 위장","약재 접근"]),
 "화상": dict(cat="검안", aliases=["덴 자국","불에 덴"],
   entry="불·열에 덴 상처. **죽기 전에 덴 것과 죽은 뒤 덴 것**은 물집과 핏기로 구분되며, "
         "사고사로 꾸미려 불을 쓴 경우 이것이 어긋난다.",
   teaches="생전 화상과 사후 화상은 구분된다", unlocks=["위장"]),
 "물자국": dict(cat="검안", aliases=["젖은 자국","물기"],
   entry="바닥이나 옷에 남은 물의 자취. 물이 있을 이유가 없는 자리의 물자국은 "
         "**무언가 녹았거나, 젖은 것이 옮겨졌다**는 뜻이다.",
   teaches="이유 없는 물자국은 융해 흉기나 사후 이동을 시사", unlocks=["사후 이동"]),
 "익사": dict(cat="검안", aliases=["물에 빠짐","溺死"],
   entry="물을 들이마셔 숨이 막혀 죽는 것. 입가의 흰 거품, 움켜쥔 물풀이 특징이며 "
         "**손목이 묶여 있으면 스스로 든 것이 아니다.**",
   teaches="결박 흔적이 있으면 자살 익사가 아니다", unlocks=["위장","결박흔"]),
 "자국": dict(cat="검안", aliases=["흔적","자욱","끝자국","눌린 자국"],
   entry="몸이나 바닥에 남은 눌린·긁힌 표시. 무엇이 어떤 힘으로 닿았는지를 말해 준다. "
         "자국의 **모양·깊이·방향**을 도구와 맞춰 보면 흉기와 그 손을 좁힐 수 있다.",
   teaches="자국의 모양·방향이 도구와 힘을 알려준다", unlocks=["흉기 특정","발자국"]),
 "발자국": dict(cat="검안", aliases=["족적","신발 자국"],
   entry="바닥에 남은 신발 자국. **크기는 체격, 깊이는 무게와 짐**을 말한다. "
         "무언가를 업거나 끌었다면 자국이 유난히 깊고 보폭이 흐트러진다.",
   teaches="발자국 크기·깊이로 체격과 짐의 유무를 안다", unlocks=["사후 이동","완력"]),
 "완력": dict(cat="수사", aliases=["힘","장정","기력"],
   entry="사람을 제압하거나 옮기는 데 필요한 힘. 노약자·병자에게는 없는 조건이라, "
         "완력이 필요한 범행이면 **그 힘을 가진 자로 범위가 줄어든다.**",
   teaches="완력 조건이 용의자를 걸러낸다", unlocks=["직업 특정"]),
 "자상": dict(cat="검안", aliases=["찔린 상처","刺傷"],
   entry="뾰족한 것에 찔려 생긴 상처. 너비는 날의 폭, 깊이는 힘을 말한다.",
   teaches="자상의 폭·깊이로 흉기를 특정", unlocks=["흉기 특정"]),
 "교살": dict(cat="검안", aliases=["목 졸림","絞殺"],
   entry="목을 졸라 숨을 막아 죽이는 것. 목에 남은 자국의 **각도**로 스스로 목맨 것과 남이 조른 것을 가른다.",
   teaches="목 자국의 각도가 자살·타살을 가른다", unlocks=["방어흔"]),
 "손상": dict(cat="검안", aliases=["상처","외상","손상부","손상 부위"],
   entry="몸에 남은 상처 전반. 생긴 시점(죽기 전·후), 도구, 힘의 방향을 함께 읽어야 한다. "
         "**죽은 뒤 생긴 상처는 피가 배지 않는다.**",
   teaches="죽기 전 상처와 죽은 뒤 상처는 다르다", unlocks=["사후 이동"]),
 "형상": dict(cat="검안", aliases=["모양","생김"],
   entry="상처나 자국의 생긴 모양. 도구의 단면이 그대로 찍히므로, 형상을 물건과 맞춰 보면 흉기가 드러난다.",
   teaches="형상은 도구의 단면을 그대로 남긴다", unlocks=["흉기 특정"]),
 "저항": dict(cat="검안", aliases=["몸부림","맞섬"],
   entry="맞서 버틴 흔적. 저항이 없다면 **잠들었거나, 믿고 곁을 내준 상대**였다는 뜻이다.",
   teaches="저항 없음은 면식 또는 기습", unlocks=["방어흔","면식범"]),
}


# ── 근현대 사전 ─ 시대에 따라 셋으로 나눠 연다 ────────────────────────
#   한 덩어리로 두었더니 19세기 유럽(성냥팔이 소녀)과 중세 아랍(알라딘)에
#   CCTV·휴대폰 통화기록·메신저가 들어갔다. 시대별로 열리는 문을 따로 둔다.
#     MODERN        근대 이후(19세기~)  — 부검·약독물·혈흔 분석
#     FINGERPRINT   20세기 이후         — 지문 감식(실무 도입 1900년 전후)
#     CONTEMPORARY  현대(20세기 후반~)  — CCTV·출입기록·통화기록·포렌식·메신저
MODERN = {
 "부검": dict(cat="검안", aliases=["해부","시신 부검"],
   entry="시신을 갈라 사인을 밝히는 절차. 위 내용물로 **마지막 식사 시각**을, 혈중 성분으로 약물·음주를 안다. "
         "겉으로 멀쩡해도 속에서 사인이 뒤집히는 일이 흔하다.",
   teaches="부검은 겉보기 사인을 뒤집을 수 있다", unlocks=["사망 시각","약독물"]),
 "약독물": dict(cat="검안", aliases=["독극물","약물검사","톡스"],
   entry="혈액·위 내용물에서 약물과 독을 찾는 검사. 수면제·진정제가 검출되면 **저항 없이 당한 이유**가 설명된다.",
   teaches="약물 검출은 저항 흔적 없음을 설명한다", unlocks=["방어흔","면식범"]),
 "혈흔형태": dict(cat="검안", aliases=["혈흔분석","비산혈흔"],
   entry="피가 튄 모양과 방향으로 가해 자세와 위치를 재현하는 분석. 닦아낸 자리도 시약에 반응한다.",
   teaches="혈흔 형태로 범행 자세를 재현", unlocks=["현장 보존"]),
}

# 20세기 이후에만 — 지문 감식은 1900년 전후에야 수사 실무에 들어왔다
FINGERPRINT = { "지문": dict(cat="검안", aliases=["지문감식","유류지문"],
   entry="물건에 남은 손자국. 있어야 할 곳에 없으면 **닦였다는 뜻**이라, 부재 자체가 인위를 가리킨다.",
   teaches="있어야 할 지문의 부재가 곧 은폐의 증거", unlocks=["현장 보존"]),
}

# 현대(20세기 후반~)에만 — 이전 시대에 넣으면 그 순간 이야기가 깨진다
CONTEMPORARY = {
 "CCTV": dict(cat="수사", aliases=["씨씨티비","감시카메라","영상"],
   entry="영상 기록. 결정적이지만 **사각지대와 시간 오차**가 있다. 카메라가 비추지 않는 통로, "
         "장치 시간이 실제와 어긋난 경우가 알리바이 조작에 쓰인다.",
   teaches="CCTV의 사각과 시간 오차가 알리바이 조작의 틈", unlocks=["출입기록","알리바이"]),
 "출입기록": dict(cat="수사", aliases=["출입카드","도어락","보안기록"],
   entry="카드·지문으로 남는 출입 로그. 다만 **카드는 빌려줄 수 있고, 문은 함께 통과할 수 있다.** "
         "기록상 안 들어간 사람이 실제로 안에 있었을 수 있다.",
   teaches="출입기록은 사람이 아니라 카드를 증명한다", unlocks=["교차검증"]),
 "통화기록": dict(cat="수사", aliases=["통화내역","기지국","위치정보"],
   entry="언제 누구와 통화했는지, 어느 기지국에 잡혔는지의 기록. **휴대폰의 위치는 사람의 위치가 아니다** — "
         "두고 나가면 알리바이가 조작된다.",
   teaches="휴대폰 위치≠사람 위치. 두고 가면 알리바이 위조", unlocks=["알리바이","디지털 포렌식"]),
 "디지털 포렌식": dict(cat="수사", aliases=["포렌식","복구","로그분석"],
   entry="삭제된 메시지·파일·접속 로그를 되살리는 기술. **지운 흔적 자체가 증거**가 되며, "
         "삭제 시각이 사건 직후라면 그것이 곧 정황이다.",
   teaches="삭제 시각이 곧 정황 증거", unlocks=["메신저"]),
 "메신저": dict(cat="수사", aliases=["카톡","메시지","채팅"],
   entry="주고받은 대화 기록. 말투와 시각이 함께 남아 **누가 누구를 불러냈는지**가 드러난다. "
         "지워진 대화는 상대방 기기에 남아 있을 수 있다.",
   teaches="지운 대화도 상대 기기엔 남는다", unlocks=["디지털 포렌식"]),
}

NO_RESULT = [
 "그런 말은 어느 문서에도 없다. (결과 없음)",
 "찾는 낱말이 검안서·문안 어디에도 보이지 않는다. (결과 없음)",
 "헛짚었다. 아무 기록도 나오지 않는다. (결과 없음)",
 "이 고을 문서고엔 그런 항목이 없다. 다른 말로 찾아보라. (결과 없음)",
]

def weapon_bucket(s):
    wc=(s.get("death",{}).get("weapon_class") or "")+" "+(s.get("death",{}).get("weapon") or "")+" "+s.get("trick",{}).get("name","")
    if "익사" in wc or "물" in wc: return "익사"
    if "교살" in wc or "졸" in wc or "끈" in wc: return "교살"
    if "소실" in wc or "녹" in wc or "고드름" in wc: return "소실"
    if "독" in wc or "비상" in wc or "사인 오인" in wc: return "독살"
    if "둔기" in wc or "타격" in wc or "향로" in wc or "부지깽이" in wc: return "둔기"
    if "밀실" in wc or "숨은 공간" in wc: return "밀실"
    return "자상"

def build_search(s):
    bucket=weapon_bucket(s)
    idx={}
    # 1) 공통 수사·검안 용어
    for term,d in FORENSIC.items():
        idx[term]=dict(term=term, aliases=d["aliases"], category=d["cat"], entry=d["entry"],
                       teaches=d["teaches"], unlocks=d["unlocks"], gated_by=1, spoiler_safe=True)
    # 1b) 공통 핵심 용어(검안서에 흔히 나오는 말은 항상 조회 가능해야)
    for term,d in CORE.items():
        idx.setdefault(term, dict(term=term, aliases=d["aliases"], category=d["cat"], entry=d["entry"],
                       teaches=d["teaches"], unlocks=d["unlocks"], gated_by=1, spoiler_safe=True))
    # 1c) 시대에 맞는 수사 사전만 연다 (근대 → 20세기 → 현대 순으로 문이 하나씩 더 열린다)
    #     주의: "도시"나 "근대"처럼 폭넓은 낱말을 트리거로 쓰면 안 된다.
    #     ("중세 아랍 도시"→45편, "근대 유럽"(19세기)→18편이 CCTV·휴대폰을 받은 적 있다)
    _era = " ".join(str(v) for v in s["background"]["setting_raw"].values()) + " " + \
           str((s.get("meta") or {}).get("era", ""))
    _PREMODERN = ["중세", "고대", "조선", "고려", "삼국", "신라", "백제", "고구려", "옛날",
                  "설화", "민담", "전설", "동화", "왕조", "막부", "에도", "당나라", "송나라",
                  "명나라", "청나라", "왕국", "성채"]
    _premodern = any(k in _era for k in _PREMODERN)
    # 근대 이후인가 — 부검·약독물·혈흔
    _modern = (not _premodern) and any(k in _era for k in
               ["근대", "19세기", "20세기", "21세기", "현대", "오늘날", "1900", "1910",
                "1920", "1930", "1940", "1950", "1960", "1970", "1980", "1990",
                "2000", "2010", "2020", "경성", "스타트업", "사무실", "회사", "서울"])
    # 20세기 이후인가 — 지문 감식
    _c20 = _modern and not any(k in _era for k in ["19세기", "18세기", "17세기"])
    # 현대인가 — CCTV·통화기록·포렌식·메신저
    _now = _c20 and any(k in _era for k in
            ["현대", "오늘날", "21세기", "1990", "2000", "2010", "2020",
             "스타트업", "사무실", "회사", "서울"])

    def _open(dic):
        for term, d in dic.items():
            idx.setdefault(term, dict(term=term, aliases=d["aliases"], category=d["cat"],
                           entry=d["entry"], teaches=d["teaches"], unlocks=d["unlocks"],
                           gated_by=1, spoiler_safe=True))
    if _modern: _open(MODERN)
    if _c20:    _open(FINGERPRINT)
    if _now:    _open(CONTEMPORARY)
    # 2) 이 사건의 흉기/수법 전용 용어
    for term,d in BY_WEAPON[bucket].items():
        idx[term]=dict(term=term, aliases=d["aliases"], category=d["cat"], entry=d["entry"],
                       teaches=d["teaches"], unlocks=d["unlocks"], gated_by=1, spoiler_safe=True)
    # 3) 이 시나리오 고유명(장소·인물·물건)을 '조회' 항목으로 (스포일러 없이 사실만)
    for p in s["map"]["places"]:
        idx[p["name"]]=dict(term=p["name"], aliases=[], category="장소",
            entry=f"{p.get('desc','')} 살펴볼 만한 것: {', '.join(p.get('features',[])[:3])}",
            teaches="이 장소에서 무엇을 탐색할 수 있는지", unlocks=[], gated_by=1, spoiler_safe=True)
    for c in s["cast"]:
        idx[c["name"]]=dict(term=c["name"], aliases=[c.get("public","")], category="인물",
            entry=f"{c.get('public','')}. {c.get('bio','')[:120]}",
            teaches="이 인물의 공개된 신분과 평판", unlocks=["알리바이"], gated_by=1, spoiler_safe=True)
    idx[s["victim"]["name"]]=dict(term=s["victim"]["name"], aliases=["피해자"], category="인물",
        entry=f"{s['victim'].get('role','')}. {s['victim'].get('bio','')[:160]}",
        teaches="피해자가 누구에게 원한을 샀는지", unlocks=["사망 시각","동선"], gated_by=1, spoiler_safe=True)
    # 4) 검안서의 관찰 항목을 그대로 조회 가능하게(사건 고유 단서)
    for i,line in enumerate(s["death"].get("scene_inspection",[])[:4],1):
        key=f"검안 소견 {i}"
        idx[key]=dict(term=key, aliases=["검안서","시체 검안"], category="검안",
            entry=line, teaches="현장 관찰 기록 원문", unlocks=[], gated_by=1, spoiler_safe=True)

    # 체인(검색어가 새 검색어를 낳는 실제 경로) 산출
    chains=[]
    def walk(t, path):
        if len(path)>4: return
        for nxt in idx.get(t,{}).get("unlocks",[]):
            if nxt in idx and nxt not in path:
                chains.append(path+[t,nxt]); walk(nxt, path+[t])
    seeds=[k for k in idx if idx[k]["category"] in ("검안","약재") ][:6]
    for sd in seeds: walk(sd, [])
    # 중복 제거·상위 8개
    seen=set(); uniq=[]
    for ch in chains:
        k=tuple(ch)
        if k not in seen: seen.add(k); uniq.append(ch)
    return {
      "ui":{"placeholder":"낱말을 적어 찾아보시오 (예: 시반, 알리바이, 규조토)",
            "autocomplete":False, "hint_on_empty":False,
            "note":"자동완성·목록 제공 안 함. 플레이어가 검안서·단서에서 본 말을 직접 입력해야 한다.",
            "match":"정확일치 + aliases 일치(부분일치 허용, 공백 무시)"},
      "index":list(idx.values()),
      "no_result_responses":NO_RESULT,
      "chains":uniq[:8],
      "design_note":"'No Results Found'식 순환: 검색→지식→추론→새 검색어. "
                    "어떤 항목도 범인을 직접 지목하지 않으며, 해석의 '도구'만 준다."
    }

if __name__=="__main__":
    arg=sys.argv[1] if len(sys.argv)>1 else "scenarios/[0-9]*.json"
    tot=0
    for p in sorted(glob.glob(arg)):
        s=json.load(open(p,encoding="utf-8"))
        s["search"]=build_search(s)
        n=len(s["search"]["index"]); ch=len(s["search"]["chains"]); tot+=n
        json.dump(s,open(p,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        spec=[t["term"] for t in s["search"]["index"] if t["category"] in ("검안","약재")][:5]
        print(f"  🔍 {p.split('/')[-1]:26} 항목 {n:3}개 · 체인 {ch} · 전용어: {', '.join(spec[:4])}")
    print(f"\n총 검색 항목 {tot}개 주입 완료")
