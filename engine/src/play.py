"""
참조용 플레이 러너 — scenario.json을 처음부터 끝까지 플레이(터미널).
도입 → 신원공개 → (라운드: 장소탐색 · 심문 · 라운드단서) → 고발 → 판정.
심문은 agent.chat(API 필요). API 없으면 알리바이만 답함.
사용:
  export ANTHROPIC_API_KEY=sk-ant-...
  python play.py scenario3.json
"""
import os, sys, json

try:
    from agent import chat
    HAVE_AGENT = True
except Exception:
    HAVE_AGENT = False
from score_motive import score_motive

def load(p): return json.load(open(p, encoding="utf-8"))
def line(): print("─" * 56)

def profile_card(c):
    """프로필 카드 — 있는 필드만 출력(없는 건 제외)."""
    pf = c.get("profile", {})
    labels = [("name","이름"),("age","나이"),("sex","성별"),
              ("relation","피해자와의 관계"),("status","신분")]
    rows = [f"{ko}: {pf[k]}" for k, ko in labels if pf.get(k) not in (None, "")]
    if not rows:  # profile 없으면 public로 대체
        rows = [f"이름: {c['name']}", f"신분: {c.get('public','')}"]
    print("   ┌─ 용의자 프로필 " + "─"*20)
    for r in rows: print("   │ " + r)
    print("   └" + "─"*36)

def run(sc):
    cfg = sc["config"]
    cast = {c["id"]: c for c in sc["cast"]}
    places = {p["id"]: p for p in sc["map"]["places"]}
    pname = {p["id"]: p["name"] for p in sc["map"]["places"]}
    rounds, turns_per, attempts = cfg["rounds"], cfg["turns_per_round"], cfg["attempts"]
    lives = attempts

    # ---- 1막 도입 (나레이션 비트) ----
    line(); print("🎬 ", sc["meta"]["title"], f"({sc['meta']['origin']} · {sc['meta']['era']})"); line()
    beats = sc["intro"].get("narration")
    if beats:
        for b in beats:
            sc_hint = f"  〔{b.get('scene','')}〕" if b.get("scene") else ""
            print(f"\n{b['text']}{sc_hint}")
            input("   [Enter]")
    else:
        print(sc["intro"]["original_summary"]); print(); print(sc["intro"]["twist"]); input("\n[Enter]")

    # ---- 살인 현장 검시 (다잉메시지·단서 탐색) ----
    d = sc["death"]
    line(); print("🩸 사건 현장"); line()
    if d.get("scene_description"): print(d["scene_description"])
    if d.get("scene_inspection"):
        print("  살필 것:", " / ".join(d["scene_inspection"]))
    for cl in sc["clue_graph"]:
        if cl.get("channel") == "crime_scene":
            tag = "🩸 다잉메시지" if cl.get("medium") == "다잉메시지" else "🔎 현장단서"
            print(f"  {tag}: {cl['surface']}")
    print(f"\n  ☠ {sc['victim']['name']}이(가) {pname[d['place']]}에서 {d['time_slot']}에 숨졌다. (흉기·수법 미상)")
    input("\n[Enter로 계속]")

    # ---- 2막 신원 공개 ----
    line(); print("👥 용의자"); line()
    for c in sc["cast"]:
        print(f"  [{c['id']}] {c['name']} — {c['public']}")
    print("\n  ⚖ 이 중 범인은 단 한 명. 그리고 범인만이 거짓을 말한다.")
    print(f"  목숨 {lives} · 라운드 {rounds} · 라운드당 심문 {turns_per}턴")

    # ---- 3막 라운드 루프 ----
    searched = set()
    for R in range(1, rounds + 1):
        line(); print(f"🔎 라운드 {R}/{rounds}   목숨 {lives}"); line()
        turns = turns_per
        while True:
            print(f"\n  남은 심문 턴 {turns}  |  [번호]용의자 심문 · [ㅈ]장소탐색 · [ㄲ]라운드 종료")
            cmd = input("  > ").strip()
            if cmd in ("ㄲ", "q", ""):
                break
            elif cmd == "ㅈ":
                print("   장소:", ", ".join(f"{p['id']}={p['name']}" for p in sc["map"]["places"]))
                pid = input("   조사할 장소 id> ").strip()
                if pid not in places:
                    print("   (없는 장소)"); continue
                owner = places[pid].get("owner")
                if owner in cast:
                    print(f"   👤 이곳의 주인 — {cast[owner]['name']}")
                    profile_card(cast[owner])
                found = False
                for cl in sc["clue_graph"]:
                    if cl.get("channel") == "location" and cl.get("location") == pid and (cl.get("reveal_round") or 9) <= R:
                        key = cl["id"]
                        if key in searched: continue
                        searched.add(key); found = True
                        print(f"   🧷 {cl['surface']}")
                if not found: print("   (특별한 것을 찾지 못했다)")
            elif cmd in cast:
                if turns <= 0: print("   (이번 라운드 심문 턴 소진)"); continue
                q = input(f"   {cast[cmd]['name']}에게 질문> ").strip()
                if not q: continue
                if HAVE_AGENT and os.environ.get("ANTHROPIC_API_KEY"):
                    try: ans = chat(sc, cmd, [], q)
                    except Exception as e: ans = f"(심문 실패: {e})"
                else:
                    ans = cast[cmd]["alibi_narration"] + "  (※API 없으면 알리바이만)"
                print(f"   💬 {cast[cmd]['name']}: {ans}")
                turns -= 1
            else:
                print("   (알 수 없는 명령)")

        # 라운드 종료 스파인 단서
        for cl in sc["clue_graph"]:
            if cl.get("channel") == "spine" and cl.get("reveal_round") == R:
                print(f"\n  📜 [라운드 {R} 단서 · {cl.get('medium','')}] {cl['surface']}")

        if R < rounds:
            if input("\n  [고발한다=ㄱ / 더 조사한다=Enter] > ").strip() == "ㄱ":
                break

    # ---- 4막 고발 ----
    line(); print("⚖ 고발"); line()
    print("  범인 보기:", ", ".join(f"{cid}={cast[cid]['name']}" for cid in sc["choices"]["culprit"]))
    guess_c = input("  범인 id> ").strip()
    print("  흉기 보기:", ", ".join(sc["choices"]["weapon"]))
    guess_w = input("  흉기> ").strip()
    guess_m = input("  동기(자유서술)> ").strip()

    sol = sc["solution"]
    c_ok = guess_c == sol["culprit"]
    w_ok = guess_w.strip() == sol["weapon"]
    m_ok, m_detail = score_motive(sc, guess_m)

    line(); print("🧩 판정"); line()
    print(f"  범인 {'⭕' if c_ok else '❌'} (정답 {cast[sol['culprit']]['name']})")
    print(f"  흉기 {'⭕' if w_ok else '❌'} (정답 {sol['weapon']})")
    print(f"  동기 {'⭕' if m_ok else '❌'} ({m_detail})")
    if c_ok and w_ok and m_ok:
        print("\n  🎉 정답! " + sol["reason"])
    else:
        lives -= 1
        print(f"\n  ✖ 틀렸다. 남은 목숨 {lives}")
        if lives <= 0:
            print("  🕯 사건은 미궁에 빠졌다…")

if __name__ == "__main__":
    run(load(sys.argv[1] if len(sys.argv) > 1 else "scenario3.json"))
