interface AssetPlaceholderProps {
  name: string

  width?: number

  height?: number

  className?: string
}

export default function AssetPlaceholder({
  name,
  width = 40,
  height = 40,
  className = '',
}: AssetPlaceholderProps) {
  return (
    <div
      className={`
        flex
        items-center
        justify-center
        border
        border-dashed
        border-game-gold-dark
        text-[10px]
        text-game-muted
        ${className}
      `}
      style={{
        width,
        height,
      }}
    >
      {name}
    </div>
  )
}