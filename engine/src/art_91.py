# -*- coding: utf-8 -*-
"""
art_91.py — **91편(시연용) 그림 지시를 손으로 쓴다.**

■ 왜 이 편만 따로 쓰나 (2026-08-25)
  나머지 49편은 placeart.py가 틀에서 뽑는다. 그래도 충분히 쓸 만하다.
  그러나 91편 「여섯 잔의 회의」는 **중간발표 시연에 나가는 편**이다.
  이 편의 그림이 곧 이 프로젝트의 얼굴이 되므로, 장소 여섯 곳과 단서 열여덟 장을
  틀에 맡기지 않고 한 줄씩 직접 쓴다.

■ 이 편의 결 — 다른 편과 무엇이 다른가
  · 촛불도 등잔도 없다. **시험기간 밤 열 시의 대학 도서관**이다.
    천장 형광등(4000K 언저리)과 노트북·빔 스크린의 푸른 화면빛이 섞인다.
    그림자가 옅고, 색이 조금 차고, 창유리에 실내가 비친다.
  · 사람은 그리지 않는다. 인물은 **실사 초상 여섯 장이 따로** 있다(assets/dsl).
  · 주검도 그리지 않는다. 빈자리와 밀려난 의자로만 말한다.
  · 화면 왼쪽 아래 3분의 1은 비워 둔다 — 인물 서 있는 그림이 그 위에 겹친다.

■ 단서 그림의 규칙
  단서는 대개 **문서·화면·물건**이다. 사람이 들고 있는 그림이 아니라
  **책상에 놓고 위에서 내려다본 한 컷**이 읽기 좋다. 글자가 필요한 단서는
  글자를 그리지 말고 **글자가 있을 자리만** 남긴다 — 생성 모델이 쓴 한글은 깨진다.
  실제 문구는 UI가 그 위에 얹는다.

사용:
    python3 art_91.py                 # out/91_dsl_demo.json에 얹는다
    python3 art_91.py --check         # 덮어쓰지 않고 보기만
"""
import json, sys

PATH = "scenarios/91_dsl_demo.json"

# ── 이 편 공통 ────────────────────────────────────────────────────────
LIGHT_KO = ("천장 형광등(찬 흰빛)과 노트북·빔 스크린의 푸른 화면빛이 섞인다. "
            "그림자가 옅고 윤곽이 또렷하다. 창밖은 캄캄해 유리에 실내가 되비친다")
LIGHT_EN = ("cool white fluorescent ceiling light mixed with blue laptop and projector glow, "
            "soft low-contrast shadows, pitch-dark windows mirroring the interior")
TEXTURE_EN = ("contemporary Korean university library interior, laminate desks, "
              "steel and grey carpet tile, whiteboard, paper coffee cups, "
              "cable trays and power strips")
NEG = ("candles, lanterns, oil lamps, torches, hanbok, medieval, wooden beams, "
       "sepia, fantasy, people, faces, human figures, corpse, blood, "
       "korean text, hangul lettering, any legible text, watermark, signature, "
       "logos, subtitles, extra fingers")

CAM = ("눈높이보다 살짝 위. 광각으로 방 전체가 들어오게. "
       "왼쪽 아래 3분의 1은 비워 둔다 — 인물 서 있는 그림이 그 위에 겹친다")

# ── 장소 여섯 곳 ──────────────────────────────────────────────────────
PLACES = {
    "PC": dict(
        en="university seminar room with a long table and a wall-mounted projector screen",
        space=("중앙도서관 6층 세미나실. 긴 직사각 테이블 하나가 방 한가운데를 채우고, "
               "회전의자 여섯 개가 둘러 있다. 정면 벽에 빔 스크린이 내려와 있고 "
               "천장에 프로젝터가 매달려 있다. 뒷벽은 통유리, 밖은 캄캄하다. "
               "바닥은 회색 카펫타일, 벽 한쪽에 화이트보드"),
        must=["내려온 빔 스크린 — 영상 마지막 프레임에서 멎어 있다",
              "긴 테이블 위 아이스아메리카노 여섯 잔(투명 플라스틱, 빨대)",
              "잔마다 앞에 놓인 종이 좌석 명패 여섯 개",
              "잔 하나에만 붙은 'S' 표시 스티커",
              "테이블 끝에 열린 채 놓인 노트북 — 빔에 케이블로 물려 있다",
              "밀려난 의자 하나"],
        note=("★이 방이 사건 현장이다. 주검은 그리지 않는다 — "
              "의자 하나가 뒤로 밀려나 있고 그 앞 잔만 바닥을 보인다"),
        thumb="긴 테이블과 내려온 빔 스크린이 한눈에 들어오는 세미나실",
    ),
    "P1": dict(
        en="university corridor with vending machines beside a 24-hour reading room",
        space=("세미나실 앞 복도. 오른쪽 벽에 음료·컵라면 자판기 두 대가 나란히 서 있고 "
               "그 위 천장 모서리에 반구형 CCTV가 달려 있다. 복도 끝은 통유리 창, "
               "맞은편에 '24시간 열람실' 유리문. 벽에는 학회 포스터가 붙은 게시판. "
               "바닥은 광택 나는 회색 타일이라 형광등이 길게 반사된다"),
        must=["자판기 두 대(하나는 음료, 하나는 컵라면)",
              "천장 모서리의 반구형 CCTV",
              "복도 끝 통유리 창 — 밖은 캄캄하고 유리에 복도가 되비친다",
              "24시간 열람실 유리문(안쪽에 스탠드 불빛)",
              "포스터가 여러 겹 붙은 게시판 — 한 귀퉁이가 들떠 있다",
              "벽에 기대 세워 둔 마사지용 괄사 문어 인형"],
        note="시험기간이라 밤에도 사람이 오간 흔적 — 빈 컵, 구겨진 종이컵 홀더",
        thumb="자판기 두 대와 CCTV가 보이는 밤의 복도",
    ),
    "P2": dict(
        en="basement student-club locker bay with metal lockers",
        space=("중앙도서관 지하 학회 사물함 구역. 철제 사물함이 벽을 따라 두 줄로 서 있고 "
               "칸마다 학회 이름표가 붙어 있다. '홍보부' 칸 하나가 열려 있다. "
               "천장 형광등 하나가 미세하게 깜빡이고, 복도보다 어둡고 서늘하다. "
               "바닥은 에폭시 회색, 구석에 접힌 촬영용 반사판이 세워져 있다"),
        must=["열린 홍보부 사물함 칸 — 안이 들여다보인다",
              "그 안의 촬영 소품 상자(삼각대, 반사판, 조명 클램프)",
              "상자 옆 작은 지퍼 파우치 — 반쯤 열려 있다",
              "칸마다 붙은 학회 이름표",
              "깜빡이는 형광등 하나"],
        note="차연우의 자리다. 사물함 안쪽만 조금 더 밝게 — 시선이 거기로 가야 한다",
        thumb="철제 사물함 한 칸이 열려 있는 지하 사물함 구역",
    ),
    "P3": dict(
        en="fixed window-side study seat on a library floor at night",
        space=("중앙도서관 4층 창가 열람석. 긴 창을 따라 1인 책상이 줄지어 있고, "
               "그중 한 자리에만 짐이 그대로 놓여 있다 — 늘 같은 자리를 쓰던 사람의 자리. "
               "책상마다 개별 스탠드가 있고, 그 자리 스탠드만 켜져 있다. "
               "나머지 자리는 어둡다. 창밖은 캄캄하고 멀리 캠퍼스 불빛 몇 점"),
        must=["불이 켜진 한 자리와 어두운 옆자리들",
              "그 자리에 놓인 짐 — 백팩, 텀블러, 충전기",
              "책상 위 하모니카 케이스",
              "펼쳐진 노트와 그 위 손글씨 메모지 한 장(글자는 그리지 않는다)",
              "긴 창과 창밖의 어둠"],
        note="주인이 잠깐 자리를 비운 것처럼 보여야 한다. 의자는 반쯤 빠져 있다",
        thumb="한 자리에만 스탠드가 켜진 밤의 창가 열람석",
    ),
    "P4": dict(
        en="empty university seminar room used for rehearsal, with a whiteboard",
        space=("6층 세미나실 옆의 빈 세미나실. 같은 구조지만 테이블이 한쪽으로 밀려 있고 "
               "의자가 겹쳐 쌓여 있다. 벽 전체가 화이트보드고 지운 자국이 얼룩덜룩하다. "
               "구석에 촬영용 링라이트가 켜진 채 세워져 있어 그 쪽만 밝다. "
               "바닥에 지우개 가루와 케이블 릴"),
        must=["얼룩덜룩 지운 자국이 남은 화이트보드 — 구석에 지우다 만 낙서 자국",
              "켜진 채 세워진 링라이트",
              "한쪽으로 밀린 테이블과 쌓아 둔 의자",
              "바닥의 지우개 가루",
              "벽을 사이에 둔 옆방 쪽 벽면"],
        note="유가람의 자리다. 릴스를 찍기 좋게 링라이트만 켜져 있고 천장등은 반만 켜 둔다",
        thumb="화이트보드와 링라이트가 있는 빈 세미나실",
    ),
    "P5": dict(
        en="late-night franchise coffee shop counter near a university gate",
        space=("정문 앞 프랜차이즈 커피집. 밤이라 손님이 없고 형광등만 환하다. "
               "픽업대 위에 트레이와 캐리어가 쌓여 있고, 그 옆에 시럽 펌프대 — "
               "바닐라·헤이즐넛·레몬 펌프가 나란하다. 카운터 뒤 벽에 메뉴판, "
               "천장에 CCTV. 통유리 밖은 캄캄한 정문 앞 거리"),
        must=["픽업대와 종이 캐리어(여섯 잔들이)",
              "시럽 펌프대 — 펌프 세 개가 나란히",
              "천장의 CCTV",
              "카운터 뒤 메뉴판(글자는 그리지 않는다)",
              "통유리와 캄캄한 바깥 거리"],
        note="서민재이 커피를 사 온 곳. 아무도 없는 늦은 밤의 매장",
        thumb="픽업대와 시럽 펌프대가 보이는 밤의 커피집",
    ),
}

# ── 단서 열여덟 장 ────────────────────────────────────────────────────
#   shot  : 어떻게 찍는가
#   subj  : 무엇이 프레임에 있는가
#   focus  : 어디에 초점이 맞는가 — 이것이 곧 단서다
CLUES = {
    "K1": dict(shot="문서 평면 촬영 · 위에서 수직으로",
               subj="A4 검안 소견서 한 장이 책상에 놓여 있다. 위쪽에 표 형식, 아래쪽에 "
                    "손으로 그은 밑줄. 옆에 투명 증거봉투에 담긴 플라스틱 컵 뚜껑",
               focus="밑줄 그어진 한 줄과 증거봉투 속 뚜껑",
               tag="검안서"),
    "K2": dict(shot="테이블 위 접사 · 살짝 비스듬히",
               subj="아이스아메리카노 여섯 잔이 두 줄로 놓여 있다. 다섯 잔은 뚜껑이 같고, "
                    "한 잔에만 작은 'S' 스티커가 붙어 있다",
               focus="'S' 스티커가 붙은 잔 하나 — 나머지는 얕게 흐린다",
               tag="현장"),
    "K3": dict(shot="극접사 · 뚜껑 표면에 스치는 빛",
               subj="플라스틱 컵 뚜껑 하나를 손에 들지 않고 흰 종이 위에 놓았다. "
                    "빨대 구멍 옆에 눌러 딴 자국이 하나 더 있다",
               focus="빨대 구멍이 아닌 **두 번째 자국** — 가장자리가 미세하게 들려 있다",
               tag="흔적"),
    "K4": dict(shot="접사 · 명패를 뒤집어 뒷면이 보이게",
               subj="종이 좌석 명패 하나가 뒤집혀 있다. 뒷면 아래쪽에 양면테이프가 "
                    "두 겹으로 붙어 있고, 아래층 테이프에 먼지가 앉아 있다",
               focus="겹쳐 붙은 테이프 두 겹",
               tag="현장"),
    "K0": dict(shot="노트북 화면 캡처 · 화면만 프레임에 꽉 차게",
               subj="협업 문서 웹페이지. 여섯 사람의 프로필 카드가 세로로 이어져 있고, "
                    "각 카드에 질문–답 줄이 길게 늘어서 있다. 글자는 그리지 않고 "
                    "**줄과 칸의 구조만** 남긴다",
               focus="세 번째 카드의 한 줄 — 그 줄만 형광펜으로 칠해져 있다",
               tag="문서"),
    "K5": dict(shot="복도 스냅 · 인물은 실루엣, 얼굴 없음",
               subj="열람실 앞 복도. 두세 사람이 등을 보이고 서서 이야기하는 실루엣. "
                    "말풍선은 그리지 않는다",
               focus="실루엣들 사이의 거리 — 몸을 기울여 소곤거리는 자세",
               tag="소문"),
    "K6": dict(shot="화면 캡처 · 녹음 앱의 파형",
               subj="녹음 파일 재생 화면. 가로로 긴 파형이 이어지고, 가운데 구간에 "
                    "규칙적인 작은 봉우리가 반복된다. 타임라인 눈금",
               focus="규칙적으로 되풀이되는 봉우리 구간",
               tag="목격담"),
    "K7": dict(shot="증언 카드 · 인물 없이 손글씨 메모 한 장",
               subj="줄노트에 적힌 손글씨 메모와 그 옆에 그린 좌석 배치 약도. "
                    "동그라미 여섯 개와 화살표 하나",
               focus="약도에서 한 칸 옮겨 그려진 동그라미와 그리로 향한 화살표",
               tag="목격담"),
    "K8": dict(shot="두 컷 나란히 · 왼쪽 영수증, 오른쪽 CCTV 스틸",
               subj="왼쪽에 길쭉한 감열지 영수증, 오른쪽에 흑백 CCTV 정지화면 "
                    "(픽업대와 캐리어, 사람은 실루엣)",
               focus="영수증의 수량 줄과 CCTV 속 캐리어",
               tag="문서"),
    "K9": dict(shot="세로 영상 캡처 · 휴대폰 화면 비율",
               subj="세로 화면의 영상 정지컷. 링라이트가 켜진 빈 세미나실 구석. "
                    "화면 모서리에 타임스탬프 자리(글자는 그리지 않는다)",
               focus="화면 오른쪽 벽 — 그 너머에서 소리가 났다는 것이 느껴지게 "
                     "벽 쪽을 살짝 비워 둔다",
               tag="목격담"),
    "K10": dict(shot="화면 캡처 · 영상 편집 타임라인",
                subj="재생 막대 두 개가 위아래로 놓여 있다. 위쪽이 아래쪽보다 길고, "
                     "위쪽 가운데에 색이 다른 구간 두 덩이가 끼어 있다",
                focus="길이가 다른 두 막대와, 끼어든 구간 두 덩이",
                tag="문서"),
    "K11": dict(shot="흑백 CCTV 스틸 · 위에서 비스듬히 내려다본 복도",
                subj="자판기 앞 복도의 흑백 정지화면. 사람은 얼굴이 뭉개진 실루엣 셋. "
                     "화면 모서리에 시각 표시 자리",
                focus="세 실루엣이 각각 다른 자리에 있고, 네 번째 사람이 없다는 것 — "
                      "빈 복도 오른쪽을 넓게 잡는다",
                tag="목격담"),
    "KD": dict(shot="증거 정렬 촬영 · 흰 종이 위에 나란히 · 위에서 수직",
               subj="지퍼 파우치를 열어 내용물을 꺼내 늘어놓았다 — 작은 갈색 유리병 하나, "
                    "투명 소분병 하나, 미니 깔때기, 일회용 장갑. 병 입구에 마른 자국",
               focus="두 병이 나란히 놓인 자리와 소분병 입구의 마른 방울 자국",
               tag="흔적 · ★결정타"),
    "S1": dict(shot="문서 접사 · 메모지가 노트에 끼워진 채",
               subj="접힌 메모지 한 장이 펼쳐져 있다. 짧은 줄 몇 개와 화살표, "
                    "한 줄 옆에 동그라미. 글자는 그리지 않는다",
               focus="화살표가 가리키는 줄과 그 옆 동그라미",
               tag="문서"),
    "S2": dict(shot="화이트보드 구석 접사 · 비스듬히",
               subj="지운 자국이 얼룩덜룩한 화이트보드의 아래 구석. 지우다 만 글씨 자국과 "
                    "그 옆에 대충 그린 사람 얼굴 낙서",
               focus="지워지다 만 글씨 자국 — 형태만 남고 읽히지는 않는다",
               tag="문서"),
    "S3": dict(shot="화면 캡처 · 표 형식 로그",
               subj="가로줄이 여러 개인 접속 기록 표. 열이 넷쯤 되고, 한 줄만 "
                    "배경색이 다르다. 글자는 그리지 않고 줄과 칸만",
               focus="배경색이 다른 한 줄 — 시각 칸 자리를 조금 넓게",
               tag="문서"),
    "S4": dict(shot="흑백 CCTV 스틸 · 카운터 위 시럽 펌프대를 정면에서",
               subj="시럽 펌프 세 개가 나란한 흑백 정지화면. 사람 없음. "
                    "펌프 손잡이 위치가 셋 다 같다",
               focus="세 펌프의 손잡이가 모두 눌리지 않은 채 같은 높이인 것",
               tag="문서"),
    "S5": dict(shot="문서 평면 촬영 · 접힌 자국이 보이게",
               subj="네 번 접혔던 A4 인쇄물 한 장을 펼쳐 놓았다. 접힌 선이 十자로 "
                    "선명하고, 위쪽에 큰 제목 자리, 아래에 목차처럼 줄이 이어진다",
               focus="十자 접힌 자국과 제목 자리 — 오래 접혀 있었던 종이",
               tag="문서"),
}


# ── 오프닝 삽화 열네 쪽 ────────────────────────────────────────────────
#   ★2026-08-26. 여기가 틀에서 뽑은 채로 남아 있었다 —
#     "storybook illustration, 시험기간의 중앙도서관, painterly,
#      **warm candlelit palette**, no text" 열네 쪽이 전부 같은 문장이었다.
#     영어 프롬프트 안에 한글이 섞여 있고, 촛불 색이 지정돼 있다.
#     2020년대 대학 도서관에 촛불은 없다. 열네 쪽을 한 쪽씩 쓴다.
#   ★사람은 그리지 않는다 — 이 편의 인물은 **실존 인물의 실사 사진**이다.
#     장면은 공간과 물건으로만 말한다. 빈 의자, 놓인 잔, 꺼진 화면.
OPENING = [
    dict(ko="열람실 통유리 너머로 본 밤의 도서관. 책상마다 스탠드가 켜져 있고 자리가 다 찼다. "
            "복도 바닥에도 책과 텀블러가 줄지어 놓여 있다. 사람은 실루엣조차 그리지 않는다 — "
            "짐만 남은 자리로 붐빔을 말한다",
         en="night exterior-to-interior view of a crowded university library reading room, "
            "rows of desk lamps lit, books and tumblers lined along the corridor floor, "
            "empty chairs, no people"),
    dict(ko="복도에서 본 6층 세미나실. 문 위 창으로 방금 켜진 형광등 빛이 새어 나온다. "
            "문에 붙은 예약 표에는 글자를 그리지 않는다",
         en="a seminar room door at the end of a dim corridor, fluorescent light just switched on "
            "spilling through the transom window, blank booking slip on the door, no people"),
    dict(ko="예약 단말기와 벽시계가 함께 보이는 한 컷. 세 시간짜리 예약이 시작된 참이다. "
            "숫자는 그리지 않고 시계 바늘만 남긴다",
         en="wall clock and a room-booking kiosk side by side in a library corridor, "
            "analog clock hands only, no digits, no people"),
    dict(ko="긴 테이블 상석 자리. 노트북 한 대가 열려 있고 그 앞에 안건 종이가 놓여 있다. "
            "의자는 비어 있다. 화면과 종이 모두 글자는 그리지 않는다",
         en="head of a long seminar table, one open laptop and a printed agenda sheet, "
            "empty swivel chair, blank screen and blank paper, no people"),
    dict(ko="테이블 위에 막 놓인 아이스아메리카노 여섯 잔과, 잔마다 앞에 세워진 종이 좌석 명패. "
            "잔 하나에만 작은 스티커가 붙어 있다. 캐리어 두 개가 테이블 끝에 접혀 있다",
         en="six iced americano cups just placed on a long table, a folded paper name card "
            "standing in front of each cup, one cup with a small sticker, "
            "two empty drink carriers at the end, no people"),
    dict(ko="문 옆 자리 둘. 한쪽 의자 등받이에 러닝 재킷이 걸려 있고 물병이 놓여 있다. "
            "다른 쪽엔 컵라면 뚜껑이 반쯤 덮인 채 김이 오른다",
         en="two seats near the door, a running jacket over one chair back with a water bottle, "
            "a half-opened instant noodle cup steaming on the next desk, no people"),
    dict(ko="화이트보드 구석에 아무렇게나 그려진 낙서 한 덩이 — 글자는 그리지 않고 "
            "장난스러운 선과 화살표만. 마커가 트레이에 굴러 있다",
         en="a corner of a whiteboard with a playful doodle of arrows and boxes, no letters, "
            "a marker rolling in the tray, no people"),
    dict(ko="같은 테이블을 조금 물러나 본 컷. 잔들이 조금씩 흐트러졌고 의자 하나가 비스듬하다. "
            "웃음이 지나간 자리처럼 물건만 어질러져 있다",
         en="the same seminar table seen a step back, cups slightly out of line, "
            "one chair turned at an angle, relaxed disorder, no people"),
    dict(ko="빔에 물린 노트북과 발밑으로 밀어 넣은 케이블. 옆방 문틈으로 링라이트의 흰빛이 "
            "새어 들어온다",
         en="a laptop cabled to a projector, cable tucked under the table edge, "
            "white ring-light glow leaking through a gap in the adjoining door, no people"),
    dict(ko="소등된 방. 빔 스크린만 밝다. 화면 속은 밝은 학회 영상 — 얼굴은 뭉개어 알아볼 수 "
            "없게. 테이블 위 잔들이 화면빛을 받아 푸르게 선다",
         en="a darkened seminar room lit only by a bright projector screen, "
            "the projected footage abstract and unreadable, six cups edge-lit blue, no people"),
    dict(ko="어둠 속 테이블 위 접사. 잔 안에서 얼음이 갈라지고, 의자 다리 하나가 카펫에 "
            "끌린 자국을 남겼다. 스크린빛만이 광원이다",
         en="close-up of a table in near darkness, ice cracking inside a plastic cup, "
            "a chair leg scuff mark on carpet tile, only screen light, no people"),
    dict(ko="불이 다시 켜진 방을 문가에서 본 컷. 의자 여섯이 제각각 물러나 있고 자리마다 "
            "잔이 남아 있다. 복도 쪽 문이 열려 있다",
         en="the seminar room with lights back on seen from the doorway, six chairs pushed back "
            "at different angles, a cup left at every seat, the door to the corridor open, no people"),
    dict(ko="상석 하나만 남은 방. 노트북 화면빛이 여섯 잔을 비춘다. 상석 앞 잔은 절반쯤 "
            "줄어 있다. 나머지 다섯 잔은 손대지 않은 그대로",
         en="an otherwise empty seminar room with one occupied-looking seat, laptop glow across "
            "six cups, the cup at the head half empty, the other five untouched, no people"),
    dict(ko="같은 앵글, 조금 뒤. 상석 의자가 뒤로 밀려나 있고 그 앞 잔이 기울어 바닥을 보인다. "
            "얼음 녹은 물이 테이블에 번졌다. **주검은 그리지 않는다**",
         en="the same angle moments later, the head chair pushed back, the cup in front tipped over, "
            "melted ice spreading across the table, no body, no people"),
]


def _page_prompt(i, ko, en):
    k = (f"[장면] {ko}. "
         f"[광원] {LIGHT_KO}. "
         f"[카메라] 눈높이. 사람이 없는 자리를 정면으로 받는다. "
         f"[금지] 사람·얼굴·손, 읽히는 한글. 글자 자리는 빈 칸으로 남긴다.")
    e = (f"{en}, {TEXTURE_EN}, {LIGHT_EN}, "
         f"cinematic still life, photographic realism, 35mm, eye level, "
         f"no text of any kind, 1045x600 landscape")
    return k, e


# ── 범행 재연 여섯 컷 ─────────────────────────────────────────────────
#   ★이 편의 인물은 **실존 인물**이다. 얼굴을 생성해서 그리지 않는다.
#     재연은 손·뒷모습·물건으로만 간다. 얼굴이 필요한 컷은 실사 초상을 얹는다.
REENACT = [
    dict(ko="문설주 옆에 선 사람의 뒷모습 — 어깨 위로는 프레임 밖. 세미나실 문틈으로 새는 빛만 "
            "받는다. 손에 든 것은 없다",
         en="back view of a standing figure cut off above the shoulders, beside a door frame, "
            "lit only by light leaking through the gap"),
    dict(ko="암전된 방, 테이블 접사. 장갑 없는 손 하나가 프레임 아래에서 들어와 컵 뚜껑을 "
            "눌러 딴다. 얼굴은 프레임 밖. 스포이드 끝에 맺힌 방울",
         en="close-up of a table in darkness, one hand entering from the bottom of the frame "
            "prying a cup lid, a droplet on a silicone dropper tip, face out of frame"),
    dict(ko="스크린빛만 있는 어둠 속에서, 'S' 스티커가 붙은 잔 하나가 제자리로 돌아간다. "
            "옆자리 의자는 비어 있다",
         en="a cup with a small sticker set back in place in near darkness, "
            "screen light only, the seat beside it empty"),
    dict(ko="빔 프로젝터와 노트북의 재생 막대 — 눈금만 그리고 숫자는 그리지 않는다. "
            "중간 구간이 두 번 겹쳐 있다는 것만 형태로 보이게",
         en="a projector and a laptop playback bar rendered as abstract tick marks, "
            "one segment visibly doubled, no digits, no readable text"),
    dict(ko="복도에서 세미나실로 되돌아가는 뒷모습 — 걸음이 빠르다. 자판기 위 CCTV가 "
            "그 등을 담는다. 얼굴은 보이지 않는다",
         en="back view of someone walking briskly from a corridor toward a room, "
            "a dome CCTV camera above a vending machine in frame, face never visible"),
    dict(ko="아침. 불이 다 켜진 세미나실을 문가에서 본 컷. 의자 하나가 밀려나 있고 잔이 "
            "기울어 있다. 사람도 주검도 없다",
         en="morning, a fully lit seminar room seen from the doorway, one chair pushed back, "
            "one cup tipped over, no people, no body"),
]

def _clue_prompt(cl, spec):
    ko = (f"[촬영] {spec['shot']}. "
          f"[피사체] {spec['subj']}. "
          f"[초점] {spec['focus']} — 이것이 단서다. "
          f"[광원] {LIGHT_KO}. 반사가 심한 표면은 각을 틀어 반사를 죽인다. "
          f"[금지] 사람 얼굴, 손, 읽히는 한글 글자. 글자가 필요한 자리는 "
          f"**줄과 칸의 구조만** 남긴다 — 실제 문구는 UI가 위에 얹는다.")
    en = ("top-down evidence photograph on a clean surface, single object study, "
          "shallow depth of field with the key detail in sharp focus, "
          f"{LIGHT_EN}, contemporary Korean university setting, "
          "documentary realism, no people, no hands, "
          "text areas rendered as blank ruled blocks with no readable letters, "
          "256x256 square")
    return ko, en


def apply(path=PATH, check=False):
    s = json.load(open(path, encoding="utf-8"))
    ui = s["ui"]
    n_p = n_c = 0

    # ① 장소
    dslot = s["death"]["time_slot"]
    for ps in ui.get("place_screens", []):
        spec = PLACES.get(ps.get("place_id"))
        if not spec:
            continue
        must = spec["must"]
        ps["art"] = {
            "w": 1045, "h": 600,
            "hand_written": True,
            "time_of_day": f"{dslot} — 시험기간, 밤 열 시 언저리",
            "must_show": must,
            "must_show_note": "탐색 선택지가 이 물건들을 가리킨다. 빠지면 누를 것이 없다.",
            "no_people": True,
            "reserve": "왼쪽 아래 3분의 1 — 인물 서 있는 그림이 겹치는 자리",
            "prompt_ko": (f"[공간] {spec['space']}. 사람은 그리지 않는다. "
                          f"[반드시 보일 것] {' / '.join(must)}. "
                          f"[광원] {LIGHT_KO}. "
                          f"[카메라] {CAM}. "
                          f"[유의] {spec['note']}"),
            "prompt_en": (f"{spec['en']} at night, {TEXTURE_EN}, "
                          f"wide establishing interior, no people, "
                          f"{LIGHT_EN}, photographic realism, 35mm, "
                          f"slightly above eye level, "
                          f"lower-left third left empty for a character overlay, "
                          f"1045x600 landscape"),
            "negative_en": NEG,
            "era": "현대(2020년대)",
            "palette_key": "contemporary",
        }
        if ps["place_id"] == s["death"]["place"]:
            ps["art"]["variants"] = {
                "pre_murder": {
                    "when": "오프닝 나레이션 12~15쪽 — 영상이 도는 동안",
                    "diff": "같은 앵글. 의자 여섯 개가 모두 제자리에 당겨져 있고 "
                            "잔 여섯이 나란하다. 스크린은 영상 도중 한 장면.",
                    "prompt_en_add": "all six chairs tucked in, six cups aligned, "
                                     "projector mid-playback",
                },
                "post_murder": {
                    "when": "현장 화면(S-08) — 사건이 지나간 뒤",
                    "diff": "**같은 앵글.** 의자 하나만 뒤로 밀려나 있고 그 앞 잔이 "
                            "기울어 바닥을 보인다. 스크린은 마지막 프레임에 멎어 있다. "
                            "주검은 그리지 않는다.",
                    "prompt_en_add": "one chair pushed back, one cup tipped over, "
                                     "projector frozen on the last frame",
                },
                "note": "★두 벌은 반드시 같은 앵글·같은 렌즈. 달라진 것 셋만 보이게.",
            }
        ps["map_thumb"] = {
            "w": 320, "h": 200,
            "prompt_ko": f"{spec['thumb']}. 멀리서 본 한 컷, 사람 없음. "
                         f"무엇인지 한눈에 알아볼 수 있게 단순하게.",
            "prompt_en": (f"small map icon illustration of {spec['en']}, "
                          f"seen from a distance, simple readable silhouette, "
                          f"no people, {TEXTURE_EN}, {LIGHT_EN}, 320x200"),
            "negative_en": NEG,
        }
        n_p += 1

    # ② 단서
    by_id = {c["id"]: c for c in s["clue_graph"]}
    for card in ui.get("clue_cards", []):
        spec = CLUES.get(card.get("id"))
        if not spec:
            continue
        ko, en = _clue_prompt(by_id.get(card["id"], {}), spec)
        card["thumb"] = {
            "w": 256, "h": 256,
            "hand_written": True,
            "shot": spec["shot"],
            "focus": spec["focus"],
            "tag": spec["tag"],
            "prompt_ko": ko,
            "prompt_en": en,
            "negative_en": NEG,
        }
        n_c += 1

    # ③ 오프닝 삽화 — 열네 쪽을 한 쪽씩 쓴다 (틀에서 뽑은 문장을 통째로 갈아엎는다)
    pages = (ui.get("narration") or {}).get("pages", [])
    n_pg = 0
    for pg in pages:
        i = int(pg.get("page") or 0)
        if not (1 <= i <= len(OPENING)):
            continue
        spec = OPENING[i - 1]
        ko, en = _page_prompt(i, spec["ko"], spec["en"])
        pg["image"] = {
            "w": 1045, "h": 600,
            "hand_written": True,
            "file": f"91_open_{i:02d}.png",
            "scene": pg.get("text", "")[:40],
            "prompt_ko": ko,
            "prompt_en": en,
            "negative_en": NEG,
            "light_ko": LIGHT_KO,
            "hand_note": ("이 편의 오프닝 삽화는 **사람을 그리지 않는다** — "
                          "인물은 실사 초상 여섯 장이 따로 있다(assets/dsl). "
                          "빈 자리와 놓인 물건으로 그 문장을 받는다."),
        }
        n_pg += 1

    # ④ 범행 재연 여섯 컷 — 얼굴을 생성하지 않는다(실존 인물)
    cuts = (ui.get("murder_reenactment") or {}).get("cuts", [])
    n_cut = 0
    for cut in cuts:
        i = int(cut.get("no") or 0)
        if not (1 <= i <= len(REENACT)):
            continue
        spec = REENACT[i - 1]
        cut["lighting"] = LIGHT_KO
        cut["continuity"] = ("★얼굴을 그리지 않는다 — 이 편의 인물은 실존 인물이며 "
                             "초상은 실사 사진(assets/dsl)을 쓴다. 여섯 컷 모두 "
                             "뒷모습·손·물건으로만 간다. 흉기(플라스틱 컵)는 "
                             "여섯 컷 내내 같은 잔으로 그린다.")
        cut["image"] = {
            "w": 1045, "h": 600,
            "hand_written": True,
            "file": f"91_reenact_{i}.png",
            "prompt_ko": (f"[장면] {spec['ko']}. [광원] {LIGHT_KO}. "
                          f"[금지] 얼굴, 읽히는 한글, 주검, 피."),
            "prompt_en": (f"{spec['en']}, {TEXTURE_EN}, {LIGHT_EN}, "
                          f"cinematic still, photographic realism, 35mm, "
                          f"no faces, no text, 1045x600 landscape"),
            "negative_en": NEG,
        }
        n_cut += 1

    # ⑤ 초상·주검 — 그리지 않는 자리를 **그리지 말라고 적어 둔다**
    vc = ui.get("victim_card") or {}
    if vc.get("portrait"):
        vc["portrait"].update({
            "hand_written": True,
            "generate": False,
            "prompt_ko": "그리지 않는다. 실사 사진(assets/dsl/한도윤.png)을 그대로 쓴다.",
            "prompt_en": "DO NOT GENERATE — use the supplied photograph.",
            "rule": "실존 인물이다. 초상을 생성하지 않는다. 사진 위 처리(흑백·테두리)만 한다.",
        })
    if vc.get("body_art"):
        vc["body_art"].update({
            "hand_written": True,
            "file": "91_scene_after.png",
            "prompt_ko": ("[장면] 불 켜진 6층 세미나실. **주검은 그리지 않는다.** "
                          "상석 의자만 뒤로 밀려나 있고 그 앞 잔이 기울어 바닥을 보인다. "
                          "빔 스크린은 마지막 프레임에 멎어 있다. 나머지 다섯 잔은 그대로. "
                          f"[광원] {LIGHT_KO}. [금지] 사람, 주검, 피, 읽히는 한글."),
            "prompt_en": ("a lit university seminar room after an incident, one chair pushed back, "
                          "one plastic cup tipped over on the table, projector screen frozen on a "
                          f"final frame, five other cups untouched, {TEXTURE_EN}, {LIGHT_EN}, "
                          "no people, no body, no blood, no text, 1045x600 landscape"),
            "negative_en": NEG,
            "rule": "★실존 인물이 모델인 편이다. 주검은 어떤 형태로도 그리지 않는다.",
        })
    n_por = 0
    for card in ui.get("suspect_cards", []):
        por = card.get("portrait")
        if not por:
            continue
        por.update({
            "hand_written": True,
            "generate": False,
            "prompt_ko": (f"그리지 않는다. 실사 사진({por.get('photo','assets/dsl/…')})을 쓴다. "
                          f"할 일은 배경 지우기와 서 있는 컷 크기(600×1200)로 맞추기뿐이다."),
            "prompt_en": "DO NOT GENERATE — use the supplied photograph; cut out background only.",
            "standing_prompt_en": "DO NOT GENERATE — use the supplied photograph.",
            "rule": "실존 인물이다. 얼굴을 생성하거나 표정을 합성하지 않는다.",
        })
        n_por += 1

    # ⑥ 마지막 남은 옛 결 — 타이틀 화면과 재연 룩, 인물 외형 프롬프트
    #    (촛불·period-accurate·영어 안의 한글이 여기 남아 있었다)
    look = (ui.get("murder_reenactment") or {}).get("look")
    if look:
        look.update({
            "culprit_ko": "얼굴은 그리지 않는다 — 뒷모습·손·물건으로만 간다",
            "culprit_en": "no face, back view or hands only, contemporary casual clothing",
            "lighting_ko": LIGHT_KO,
            "lighting_en": LIGHT_EN,
        })
    for sc in ui.get("screens", []):
        art = sc.get("art") or {}
        if not art.get("prompt_ko"):
            continue
        if "촛불" in art["prompt_ko"] or "candle" in (art.get("prompt_en") or ""):
            art["prompt_ko"] = ("밤의 도서관 열람석 한 자리. 스탠드 하나만 켜져 있고 "
                                "책상에 사건 자료가 펼쳐져 있다. 사람 없음. 글자 없음.")
            art["prompt_en"] = ("a single library desk at night lit by one desk lamp, "
                                "case documents spread on the desk, no people, no text, "
                                f"{TEXTURE_EN}, heavy vignette, cool palette")
            art["negative_en"] = NEG
    for c in s.get("cast", []):
        ap = c.get("appearance") or {}
        if ap:
            ap["generate"] = False
            ap["prompt_ko"] = ("그리지 않는다. 실사 사진(assets/dsl)을 쓴다. "
                               "표정 세 벌은 사진 위 보정으로 만들지 않는다 — "
                               "UI가 카드 테두리·색조로 대신한다.")
            ap["prompt_en"] = "DO NOT GENERATE — use the supplied photograph."

    # ⑦ 단서 카드의 옛 서식 지시(render)도 손글씨 쪽으로 맞춘다
    for cl in s.get("clue_graph", []):
        spec = CLUES.get(cl.get("id"))
        if not spec:
            continue
        cl["render"] = {
            "hand_written": True,
            "shot": spec["shot"],
            "frame": spec["subj"],
            "focus": spec["focus"],
            "camera": spec["shot"],
            "style": "현대(2020년대) 대학 도서관. 증거 사진 결. 1045×600 또는 256×256 썸네일",
            "spoiler_ban": "사람 얼굴·손, 읽히는 한글은 그리지 않는다",
        }

    if not check:
        json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  91편 손글씨 그림 지시 — 장소 {n_p}곳 · 단서 {n_c}장 · "
          f"오프닝 {n_pg}쪽 · 재연 {n_cut}컷 · 초상 {n_por}장(생성 안 함)")
    return n_p, n_c


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    # 파이프라인이 편마다 부르므로, **91편일 때만** 손댄다
    for f in (args or [PATH]):
        if "91_dsl" in f:
            apply(f, check="--check" in sys.argv)
