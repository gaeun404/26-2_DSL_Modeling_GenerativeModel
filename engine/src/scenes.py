# -*- coding: utf-8 -*-
"""
scenes.py — 한 편의 **모든 장면**을 처음부터 끝까지 대본으로 뽑는다.

왜 필요한가
  ui.py가 붙인 것은 조각이다 — 화면 목록, 카드, 선택지, 곡. 만드는 사람이 알고 싶은 것은
  "1번 장면부터 마지막 장면까지, 무엇이 뜨고 무슨 소리가 나고 무슨 글자가 보이는가"다.
  그림·음악·개발이 같은 표를 보고 움직여야 한다.

무엇을 내나
  장면마다: 번호 · 화면 · 보이는 것 · 화면에 뜨는 글자(전문) · BGM · 효과음 · 다음으로 가는 조건
  라운드는 실제 진행 순서대로 편다(장소 조사 → 심문 → 정리 → 이벤트).

사용:
    python scenes.py out/01_전우치전.json
    python scenes.py out/01_전우치전.json --out 장면대본_01.md
"""
import json, sys, os, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or ".")


class Book:
    def __init__(self):
        self.L, self.n = [], 0

    def scene(self, screen, title, *, see=None, text=None, bgm="", sfx=None,
              nxt="", note=""):
        self.n += 1
        self.L.append(f"\n### S{self.n:03d} · {title}")
        self.L.append(f"\n| | |\n|---|---|")
        self.L.append(f"| 화면 | {screen} |")
        if see:
            self.L.append("| 보이는 것 | " + " · ".join(see) + " |")
        self.L.append(f"| BGM | {bgm or '—'} |")
        self.L.append("| 효과음 | " + (" · ".join(sfx) if sfx else "—") + " |")
        if nxt:
            self.L.append(f"| 다음으로 | {nxt} |")
        if note:
            self.L.append(f"| 메모 | {note} |")
        if text:
            self.L.append("")
            for t in ([text] if isinstance(text, str) else text):
                self.L.append("> " + str(t).replace("\n", "  \n> "))
        return self.n

    def head(self, s):
        self.L.append(f"\n\n---\n\n## {s}")

    def out(self):
        return "\n".join(self.L)


def build(s):
    u = s["ui"]
    B = Book()
    pn = {p["id"]: p["name"] for p in s["map"]["places"]}
    cn = {c["id"]: c["name"] for c in s["cast"]}
    scr = {x["id"]: x for x in u["screens"]}
    rounds = (s.get("config") or {}).get("rounds", 3)
    m = s["meta"]

    B.L.append(f"# {m['title']} — 전체 장면 대본")
    B.L.append(f"\n> 원작 **{m.get('origin')}** · {m.get('era')} · "
               f"용의자 {len(s['cast'])}명 · {rounds}라운드 · "
               f"장소 {len(s['map']['places'])}곳 · 단서 {len(s['clue_graph'])}개")
    B.L.append("\n> 곡·효과음 이름은 JSON의 `bgm.*` / `ui.audio.*` 키다. "
               "그림 지시는 각 카드·화면의 `prompt_ko / prompt_en`에 그대로 있다.")

    a = u["art_specs"]
    B.L.append("\n### 그려야 할 그림\n")
    B.L.append("| 종류 | 장수 | 규격 | 어디에 | 메모 |\n|---|---|---|---|---|")
    for r in a["rows"]:
        B.L.append(f"| {r['kind']} | {r['n']} | {r['w']}×{r['h']} | {r['where']} | {r['note']} |")
    B.L.append(f"\n합계 **{a['total']}장**")

    # ── 0. 들어가기 ──────────────────────────────────────────────
    B.head("0부 · 들어가기")
    t = scr["title"]["copy"]
    B.scene("타이틀", "타이틀", see=scr["title"]["elements"],
            text=[f"**{t['brand']}**", t["sub"], t["tagline"],
                  f"[{t['buttons'][0]}]  [{t['buttons'][1]}]"],
            bgm="ui.audio.music.title (58BPM, 정적)",
            sfx=["title_appear", "ui_click_major"],
            nxt="‘사건 시작’을 누른다")
    w = scr["world_input"]["copy"]
    B.scene("세계관 입력", "어떤 이야기로 시작할까",
            see=scr["world_input"]["elements"],
            text=[f"{w['header']} / {w['index']}", f"**{w['question']}**",
                  f"입력창 안내글: {w['placeholder']}", w["helper"], f"[{w['button']}]"],
            bgm="ui.audio.music.world_input", sfx=["typing", "ui_click_major"],
            nxt="원작 이름을 적고 ‘생성하기’",
            note="이미 만들어 둔 편이면 각색하지 않는다 — " +
                 scr["world_input"]["branch"]["rule"])
    lo = scr["loading"]["copy"]
    B.scene("로딩", "이야기를 각색하는 중", see=scr["loading"]["elements"],
            text=[f"**{lo['title']}**"] + [f"· {x}" for x in lo["status_lines"]] + [lo["footer"]],
            bgm="ui.audio.music.loading (30~45초 무한 반복)", sfx=["loading_tick"],
            nxt="생성이 끝나면 자동으로",
            note="두 갈래 — 불러오기: “" + lo["title_load"] + "” (" +
                 " / ".join(lo["status_lines_load"]) + ") · 각색: 위 4줄")

    co = scr["case_open"]
    B.scene("사건 공개", f"사건 공개 — 「{co['copy']['title']}」",
            see=co["elements"],
            text=[co["copy"]["header"], f"**「{co['copy']['title']}」**",
                  co["copy"]["setting"], co["copy"]["logline"], ""] +
                 co["copy"]["ready_lines"] +
                 [f"[{co['copy']['button']}]   [{co['copy']['reroll_button']}]",
                  f"부 버튼 아래 작은 글: {co['copy']['reroll_helper']}",
                  f"부 버튼 확인창: “{co['copy']['reroll_confirm']}” "
                  f"[{co['copy']['reroll_confirm_buttons'][0]}] [{co['copy']['reroll_confirm_buttons'][1]}]"],
            bgm=co["bgm"], sfx=[x.split(".")[-1] for x in co["sfx"]],
            nxt="‘사건을 연다’ → 나레이션",
            note=" → ".join(co["staging"]))

    # ── 1. 나레이션 ──────────────────────────────────────────────
    B.head("1부 · 오프닝 나레이션")
    nar = u["narration"]
    lim = nar["limits"]
    B.L.append(f"\n낭독자: {nar['narrator']['tone']}  \n"
               f"**한 쪽 = 두 문장 · 공백 포함 {lim['chars_per_page']}자 이내** "
               f"(넘으면 글자창에서 잘린다)  \n"
               f"그림: 쪽마다 한 장 · **{lim['image']['w']}×{lim['image']['h']}** — 총 "
               f"{nar['image_count']}장  \n"
               f"영상으로 갈 쪽: **{', '.join(str(x) for x in nar['video_pages'])}**  \n"
               f"사건이 터지는 쪽: **{nar['incident_page']}쪽**  \n"
               + (f"⚠️ 글자 수 넘친 쪽: {nar['over_limit_pages']}" if nar["over_limit_pages"]
                  else "글자 수 넘친 쪽: 없음"))
    for b in nar["pages"]:
        see = [f"삽화: {b['image']['scene']} ({b['image']['w']}×{b['image']['h']})",
               f"{'영상' if b['render']=='video' else '정지화면'}",
               f"**{b['chars']}자** / {lim['chars_per_page']}",
               f"약 {b['duration_sec']}초"]
        note = b["image"]["note"]
        if b.get("is_incident"):
            note = "★ 여기서 이야기가 뒤집힌다 — " + " → ".join(b["transition"]["order"])
        B.scene(f"나레이션 {b['page']}/{nar['page_count']}",
                f"나레이션 {b['page']}{' ★사건 발생' if b.get('is_incident') else ''} — {b['mood']}",
                see=see, text=b["sentences"], bgm=b["bgm"],
                sfx=[x.split(".")[-1] for x in b["sfx"]],
                nxt=f"[{nar['next_label']}] / [{nar['skip_label']}]", note=note)
    bt = scr["blood_transition"]
    B.scene("혈흔 전환", "붉게 번지며 뒤집힌다", see=bt["elements"],
            text=bt["copy"]["line"], bgm="cues.discovery (여기서 곡이 바뀐다)",
            sfx=["blood_wipe"], nxt="자동")

    # ── 2. 사건 ──────────────────────────────────────────────────
    B.head("2부 · 사건")
    cs = scr["crime_scene"]
    B.scene("현장 일러스트", f"현장 — {cs['copy']['title']}",
            see=cs["elements"] + [f"반드시 보일 것: {', '.join(cs['art']['must_show'])}",
                                  f"보이면 안 되는 것: {', '.join(cs['art']['must_not_show'])}"],
            text=[f"**{cs['copy']['sidebar_title']}**"] +
                 [f"· {e['label']} — {e['text']}" for e in cs["evidence_list"]] +
                 [f"[{cs['copy']['button']}]"],
            bgm=cs["bgm"], sfx=["card_open", "counter_up"],
            nxt="증거 목록을 다 보면 ‘계속하기’")
    vc = u["victim_card"]
    B.scene("피해자 카드", f"피해자 — {vc['name']}",
            see=["초상(생전) " + f"{vc['portrait']['w']}×{vc['portrait']['h']}",
                 f"주검 그림 {vc['body_art']['w']}×{vc['body_art']['h']} — {vc['body_art']['rule']}",
                 "4칸 정보", "사인은 ??? 로 가려 둔다"],
            text=[f"**VICTIM · {vc['name']}**"] +
                 [f"· {f['label']} — {f['value']}" for f in vc["fields"]] +
                 [vc["summary"], "[계속하기 >]"],
            bgm="cues.discovery", sfx=["card_open"],
            note=f"사인 실제값 `{vc['fields'][3].get('hidden_value')}` — "
                 f"{vc['fields'][3].get('reveal_when')}")
    B.scene("용의자 소개", "SUSPECTS", see=["초상 카드 5장", "인물을 선택해 확인하세요."],
            text=[f"· **{c['name']}** — {c['list_sub']}" for c in u["suspect_cards"]],
            bgm="character_themes.* (카드를 고르면 그 인물 테마)",
            sfx=["portrait_focus", "card_open"], nxt="다 보고 ‘조사를 시작한다’")
    for c in u["suspect_cards"]:
        B.scene(f"용의자 카드 · {c['name']}", f"{c['name']}",
                see=[f"초상: {c['portrait']['prompt_ko'][:60]}",
                     f"평정: {c['portrait']['expressions']['calm']}",
                     f"흔들림: {c['portrait']['expressions']['shaken']}"],
                text=[f"· {f['label']} — {f['value']}" for f in c["fields"]] +
                     [f"**{c['alibi_label']}** {c['alibi_quote']}",
                      f"목소리: {c['voice']['summary']}"],
                bgm=c["theme"], sfx=["portrait_focus"])

    # ── 3. 라운드 ────────────────────────────────────────────────
    focus = u["hud"]["copy"]["round_focus"]
    ev = {e.get("round"): e for e in (s.get("events") or [])}
    ps = {p["place_id"]: p for p in u["place_screens"]}
    for r in range(1, rounds + 1):
        B.head(f"{2+r}부 · {r}라운드 — {focus[min(r-1, len(focus)-1)]}")
        h = u["hud"]
        B.scene("라운드 배너", f"{r}라운드 시작",
                see=["ROUND 표시", "남은 생명", "사건 개요 패널", "하단 내비 3개"],
                text=[f"**ROUND {r} / {rounds}** · 남은 생명 {(s.get('config') or {}).get('attempts',3)}",
                      f"**{h['copy']['summary_title']}** — {h['copy']['summary_text']}"] +
                     [f"· {f['label']} — {f['value']}" for f in h["summary_fields"]] +
                     [f"[{ ' ] [ '.join(h['copy']['nav']) }]"],
                bgm="cues.investigation", sfx=["round_start"],
                nxt="지도를 연다")
        if r in ev:
            e = ev[r]
            B.scene("이벤트 알림", f"★ {e.get('name') or e.get('title')}",
                    see=["화면 전체가 한 번 어두워졌다 밝아진다"],
                    text=[f"**{e.get('name') or e.get('title')}**", e.get("text", ""),
                          f"판이 바뀐다 — {e.get('effect','')}"],
                    bgm="cues.investigation (한 마디 쉬었다 재개)", sfx=["event_sting"])
        mp = scr["map"]
        B.scene("지도", "어디를 살펴볼까",
                see=[f"장소 {len(mp['places'])}곳"],
                text=[f"· {p['name']} — {p['desc'][:44]}" for p in mp["places"]],
                bgm="cues.investigation", sfx=["map_open", "ui_click"],
                nxt="장소를 고른다")
        for p in s["map"]["places"]:
            sc = ps[p["id"]]
            rd = sc["rounds"].get(str(r))
            if not rd:
                continue
            hit = next((a for a in rd["actions"] if a["finds"]), None)
            lines = [f"**{sc['title']}** — 선택지 4개"]
            for a in rd["actions"]:
                mark = " ★단서" if a["finds"] else ""
                lines.append(f"\n[{a['label']}]{mark}")
                for L in a["result_lines"]:
                    lines.append(f"　{L}")
                lines.append(f"　[{a['button']}]")
            B.scene(f"장소 조사 · {sc['title']}", f"{sc['title']} ({r}라운드)",
                    see=[f"장소 그림 {sc['art']['w']}×{sc['art']['h']}: {sc['art']['prompt_ko'][:44]}",
                         f"지도 썸네일 {sc['map_thumb']['w']}×{sc['map_thumb']['h']}",
                         (f"왼쪽에 {sc['standing_character']}의 서 있는 그림"
                          if sc["standing_character"] else "왼쪽 비움"),
                         f"이번 층: {rd['layer_note']}",
                         f"우하단 ‘{rd['counter']}’"],
                    text=lines, bgm=f"{sc['bgm']} (사건 뒤이므로 post_murder)",
                    sfx=(["search_hit", "clue_found", "counter_up"] if hit else ["search_miss"]),
                    nxt="다른 장소로 / 심문으로",
                    note=(f"찾는 단서 `{hit['finds']}`" if hit else "이 라운드엔 나올 것이 없다"))
            if hit:
                cc = next(c for c in u["clue_cards"] if c["id"] == hit["finds"])
                B.scene("알림 + 단서 카드", f"단서 획득 — {cc['name']}",
                        see=["돋보기 알림창", "수첩 단서 탭이 깜빡인다"],
                        text=["**새로운 단서가 제시되었습니다.**", f"**{cc['name']}**",
                              "사건수첩에서 확인해 보세요.", "",
                              *[f"· {f['label']} — {f['value']}" for f in cc["fields"]],
                              f"**설명** {cc['description']}"],
                        bgm="곡을 -6dB 낮춘다(duck)",
                        sfx=["toast_in", "clue_decisive" if cc["decisive"] else "clue_found"],
                        note="★결정타" if cc["decisive"] else "")
        alive = [c["name"] for c in s["cast"]]
        B.scene("심문", f"{r}라운드 심문 — {focus[min(r-1, len(focus)-1)]}",
                see=["인물 초상(표정 3단)", "대사 글상자", "감정 표시", "질문 입력창",
                     "증거 들이대기"],
                text=[f"이 라운드에 물을 수 있는 상대: {', '.join(alive)}",
                      f"질문 횟수: {(s.get('config') or {}).get('turns_per_round',12)}회",
                      "입력창 안내글: 무엇을 묻겠습니까?",
                      "[묻는다] [몰아붙인다] [증거를 들이댄다]"],
                bgm="character_themes.{고른 인물}", sfx=["typing"],
                nxt="질문을 다 쓰면 라운드 정리",
                note="답은 모델이 그 자리에서 만든다. 말체·태도는 stance.py가 정한다.")
        B.scene("라운드 정리", f"{r}라운드 정리",
                see=["이번 라운드에 얻은 단서 목록", "혐의를 벗은 인물 흐리게"],
                text=[f"**{r}라운드를 마쳤습니다.**", "얻은 단서와 남은 용의자를 정리해 보여 준다."],
                bgm="cues.investigation (한 톤 낮게)", sfx=["page_turn"],
                nxt=("다음 라운드" if r < rounds else "범인 지목"))

    # ── 4. 지목 ──────────────────────────────────────────────────
    B.head(f"{3+rounds}부 · 지목과 진상")
    ac = scr["accuse"]["copy"]
    B.scene("범인 지목", "범인 지목", see=ac and scr["accuse"]["elements"],
            text=[f"**{ac['title']}**", ac["question"], ac["weapon_q"], ac["motive_q"],
                  ac["warn"], f"[{ac['submit']}]  [{ac['cancel']}]"],
            bgm="ui.audio.music.accuse", sfx=["ui_click_major"],
            nxt="지목하면 진상으로")
    for b in u["reveal_sequence"]["beats"]:
        B.scene(f"진상 {b['no']}/5", f"진상 {b['no']} — {b['label']}",
                see=[b["shot"], f"약 {b['duration_sec']}초"],
                text=b["text"], bgm=b["bgm"],
                sfx=[x.split(".")[-1] for x in b["sfx"]],
                note="화면을 채운다" if b.get("emphasis") else "")
    re_ = u.get("murder_reenactment")
    if re_:
        B.L.append(f"\n**범행 재연** — 게임 중 금지였던 범인 얼굴이 여기서 처음 공개된다. "
                   f"컷 {len(re_['cuts'])}장 · 총 {re_['total_sec']}초 · 건너뛸 수 없음")
        for c in re_["cuts"]:
            B.scene(f"재연 {c['no']}/{len(re_['cuts'])}",
                    f"재연 {c['no']} — {c['label']}",
                    see=[f"그림 {c['image']['w']}×{c['image']['h']}: {c['image']['prompt_ko'][:52]}",
                         "얼굴 " + ("공개" if c["image"]["show_culprit_face"] else "실루엣"),
                         f"약 {c['duration_sec']}초"],
                    text=c["text"], bgm=c["bgm"],
                    sfx=[x.split(".")[-1] for x in c["sfx"]],
                    note=c.get("note", ""))
    en = scr["ending"]["copy"]
    grades = sorted((s.get("ending") or {}).get("grades") or [], key=lambda g: g.get("min", 0))
    B.scene("엔딩", "엔딩", see=scr["ending"]["elements"],
            text=[en["score"], en["secrets"]] +
                 [f"· **{g.get('name') or g.get('title')}** ({g.get('min')}점 이상) — {g.get('text','')}"
                  for g in grades] +
                 [f"[{ ' ] [ '.join(en['buttons']) }]"],
            bgm="cues.ending", sfx=["page_turn"])
    return B.out()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    s = json.load(open(a.path, encoding="utf-8"))
    if "ui" not in s:
        import ui as UI
        UI.build(s)
    doc = build(s)
    out = a.out or f"장면대본_{os.path.basename(a.path).replace('.json','')}.md"
    open(out, "w", encoding="utf-8").write(doc)
    print(f"장면 {doc.count('### S')}개 · 저장: {out}")
