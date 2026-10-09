/**
 * mmapi.js — **엔진에 붙는 한 파일.**
 *
 * 피그마에서 뽑은 화면에 이걸 넣고 함수만 부르면 된다.
 * React·Vue·바닐라 다 된다. 의존성 없음, 빌드 설정 없음.
 *
 *   import { mm } from "./mmapi.js";
 *   mm.base = "https://내-서버-주소";      // 배포한 백엔드
 *
 *   const g = await mm.start();            // 판 열기 (인트로 자료가 통째로 온다)
 *   const map = await mm.map();            // 지도
 *   await mm.search("PC");                 // 장소 조사
 *   const t = await mm.ask("C1", "그 시각 어디 계셨습니까.", "K1");
 *   const end = await mm.accuse("C5");     // 지목 — 여기서 진상이 열린다
 *
 * ■ 세션은 이 모듈이 들고 있는다. 새로고침해도 이어지도록 sessionStorage에 적어 둔다.
 * ■ 모든 응답에 state가 딸려 온다 — mm.state 로 언제든 최신값을 본다.
 * ■ 실패하면 Error(사람이 읽을 한 줄)를 던진다. 그대로 화면에 띄워도 되는 문장이다.
 */

const KEY = "mm.session";

export const mm = {
  /** 백엔드 주소. 로컬이면 http://127.0.0.1:8000 */
  base: (typeof window !== "undefined" && window.MM_API_BASE) || "http://127.0.0.1:8000",

  /** 지금 판의 id. 새로고침해도 살아남는다. */
  sid: (typeof sessionStorage !== "undefined" && sessionStorage.getItem(KEY)) || null,

  /** 마지막으로 받은 state — 라운드·남은 행동·인물·수첩이 다 있다. */
  state: null,

  /** state 가 바뀔 때마다 부를 함수를 꽂아 둔다. (React라면 setState) */
  onState: null,

  // ── 속살 ────────────────────────────────────────────────────────────
  async _call(path, body) {
    const opt = body !== undefined
      ? { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body) }
      : { method: "GET" };
    let res;
    try {
      res = await fetch(this.base + path, opt);
    } catch (e) {
      // ★가장 흔한 두 가지를 여기서 사람 말로 바꿔 준다.
      throw new Error(
        this.base.startsWith("http://") && location.protocol === "https:"
          ? "서버 주소가 http 인데 화면은 https 라 브라우저가 막았습니다. 서버를 https 로 올리거나 터널을 쓰세요."
          : "서버에 닿지 못했습니다. 주소가 맞는지, 서버가 떠 있는지 확인하세요 — " + this.base);
    }
    let data = null;
    try { data = await res.json(); } catch (_) {}
    if (!res.ok) {
      if (res.status === 404 && String(data?.detail || "").includes("판이 없")) {
        this.reset();
      }
      throw new Error(data?.detail || `요청이 실패했습니다 (${res.status})`);
    }
    if (data && data.state) {
      this.state = data.state;
      if (typeof this.onState === "function") this.onState(this.state);
    }
    return data;
  },

  _remember(sid) {
    this.sid = sid;
    try { sessionStorage.setItem(KEY, sid); } catch (_) {}
  },

  reset() {
    this.sid = null; this.state = null;
    try { sessionStorage.removeItem(KEY); } catch (_) {}
  },

  // ── 화면별로 부르는 것 ──────────────────────────────────────────────

  /** 서버가 살아 있는지. 붙이기 전에 한 번 불러 보면 좋다. */
  health() { return this._call("/health"); },

  /** 고를 수 있는 사건 목록 (제목·시대·별점·라운드 수) */
  scenarios() { return this._call("/scenarios"); },

  /**
   * 새 판을 연다. S-05~S-10 에 필요한 것이 **한 번에** 온다 —
   * case(사건 공개) · opening(오프닝 14쪽) · crime_scene(현장+시작 단서)
   * · victim(피해자 카드) · suspects(용의자 소개) · state
   */
  async start(scenario = "91_dsl_demo.json") {
    const j = await this._call("/session", { scenario });
    this._remember(j.session_id);
    return j;
  },

  /** S-11 라운드 화면에 그릴 것 전부 */
  getState() { return this._call(`/session/${this.sid}/state`); },

  /** S-13 지도 — places[].searched 가 참이면 이번 라운드엔 이미 본 방 */
  map() { return this._call(`/session/${this.sid}/map`); },

  /**
   * S-14 장소 조사. **무언가 나온 방만 1턴** 쓴다.
   * 돌아오는 것: { place, found:[단서카드], empty:bool, actions, state }
   * empty 가 참이면 「여긴 오늘 밤 달라진 게 없다」를 띄우고 턴은 그대로 둔다.
   */
  search(place_id) { return this._call(`/session/${this.sid}/search`, { place_id }); },

  /** P-06 첫 대면 알리바이 — 예산 0, 사람마다 한 번. 두 번째부터 already:true */
  meet(cast_id) { return this._call(`/session/${this.sid}/meet/${cast_id}`, {}); },

  /**
   * S-15 심문 — 1턴.
   * clue_id 를 함께 주면 그 단서 문장이 질문 앞에 통째로 붙는다(= 증거를 들이댄 것).
   * 돌아오는 것: { line(대사·키 없으면 null), stance, pressure, secrets_opened[], state }
   *   stance — ANSWER 답함 / DEFLECT 회피 / FLINCH 흔들림 / ADMIT 실토 / BREAK 무너짐
   */
  ask(cast_id, question, clue_id = null) {
    return this._call(`/session/${this.sid}/ask`, { cast_id, question, clue_id });
  },

  /** S-16 대질 — 한 판 1회, 예산 밖. 잠겨 있으면 Error */
  confront(a, b, question = "") {
    return this._call(`/session/${this.sid}/confront`, { a, b, question });
  },

  /** S-12 라운드 넘기기 — 자동 공개 단서와 이벤트가 함께 온다 */
  nextRound() { return this._call(`/session/${this.sid}/next_round`, {}); },

  /** S-18 사건수첩 — 단서만. 인물은 state.cast 에 있다 */
  notebook() { return this._call(`/session/${this.sid}/notebook`); },

  /**
   * S-21 지목 — **되돌릴 수 없다.** 여기서 처음 진상이 열린다.
   * 돌아오는 것: { correct, points, grade, truth(진상 6박),
   *                reenactment(재연 6컷), ending{ narration, branch, reveal_order, replay } }
   */
  accuse(cast_id, weapon = null, motive = null) {
    return this._call(`/session/${this.sid}/accuse`, { cast_id, weapon, motive });
  },
};

/** 사람이 만난 인물만. [용의자] 화면(S-11b)에 쓴다. */
export const metCast = (st) => (st?.cast || []).filter((c) => c.met);

/** 아직 안 만난 인물은 실루엣으로 그린다. */
export const unmetCast = (st) => (st?.cast || []).filter((c) => !c.met);

/** 화면에 띄울 태도 한 줄. stance 를 사람 말로. */
export const stanceLabel = (s) => ({
  ANSWER: "순순히 답한다",
  DEFLECT: "말을 돌린다",
  FLINCH: "말이 흔들린다",
  ADMIT: "털어놓는다",
  BREAK: "무너진다",
}[s] || s);

/** 초상 표정 3단 — 스토리보드 S-15 규격 */
export const faceOf = (s) =>
  (s === "ADMIT" || s === "BREAK") ? "broken" : (s === "FLINCH" ? "shaken" : "calm");

export default mm;
