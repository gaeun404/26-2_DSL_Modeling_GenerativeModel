export default function HomeFooter() {
  return (
    <div
      className="absolute font-game-korean text-game-muted"
      style={{
        /* 화면은 1440인데 2600으로 가운데를 잡고 있었다 — 글이 오른쪽으로 밀려 잘렸다 */
        left: 0, right: 0, bottom: 24, textAlign: 'center',
        fontSize: 14, letterSpacing: '0.1em',

      }}
    >
      ⓒ 생성형 추리극
    </div>
  )
}