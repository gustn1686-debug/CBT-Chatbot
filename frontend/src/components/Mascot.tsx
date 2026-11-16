import { MASCOT_METRICS, STAGE_HEIGHT, STAGE_WIDTH, stageLayout } from '../lib/mascotMetrics'

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

// 온보딩처럼 화면마다 포즈가 다른 마스코트를 보여줄 때 쓴다.
// 모든 포즈에서 캐릭터 크기(눈 높이)와 위치(가로 중심·발 위치)가 같게 고정된 무대 안에 그린다.
export function MascotStage({ variant }: { variant: MascotVariant }) {
  const src = images[`../assets/mascot/${variant}.webp`]
  const metrics = MASCOT_METRICS[variant]
  return (
    <div className="relative shrink-0" style={{ width: STAGE_WIDTH, height: STAGE_HEIGHT, maxWidth: '100%' }}>
      {src && metrics && (
        <img
          alt=""
          src={src}
          className="pointer-events-none absolute max-w-none"
          style={(() => {
            const l = stageLayout(metrics)
            return { width: l.width, height: l.height, left: l.left, top: l.top }
          })()}
        />
      )}
    </div>
  )
}
