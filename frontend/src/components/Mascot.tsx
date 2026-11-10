export type MascotVariant = 'main' | 'thinking' | 'playing' | 'waving' | 'face'

// Figma 에셋(asset_mascot_*)을 src/assets/mascot/<variant>.webp 로 두면 자동으로 연결된다.
const images = import.meta.glob<string>('../assets/mascot/*.webp', {
  eager: true,
  import: 'default',
})

type MascotProps = {
  variant: MascotVariant
  width: number
  height: number
  className?: string
}

export function Mascot({ variant, width, height, className }: MascotProps) {
  const src = images[`../assets/mascot/${variant}.webp`]
  return (
    <div className={className} style={{ width, height }}>
      {src && <img alt="" src={src} className="size-full object-contain pointer-events-none" />}
    </div>
  )
}
