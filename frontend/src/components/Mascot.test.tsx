import { render } from '@testing-library/react'
import { MASCOT_METRICS, STAGE_HEIGHT, STAGE_WIDTH, EYE_PX, stageLayout } from '../lib/mascotMetrics'
import { MascotStage, type MascotVariant } from './Mascot'

const variants = Object.keys(MASCOT_METRICS) as MascotVariant[]

describe('MascotStage (온보딩 마스코트)', () => {
  it('어떤 포즈든 캐릭터 크기(눈 높이)가 같게 그려진다', () => {
    for (const variant of variants) {
      const m = MASCOT_METRICS[variant]!
      const l = stageLayout(m)
      // 화면에 그려진 눈 높이 = 원본 눈 높이 x 배율
      expect(m.eyeHeight * l.scale).toBeCloseTo(EYE_PX, 5)
    }
  })

  it('캐릭터의 가로 중심과 발(아래쪽)이 모든 포즈에서 같은 자리에 온다', () => {
    for (const variant of variants) {
      const m = MASCOT_METRICS[variant]!
      const l = stageLayout(m)
      const [left, , right, bottom] = m.box
      expect(l.left + ((left + right) / 2) * l.scale).toBeCloseTo(STAGE_WIDTH / 2, 5)
      expect(l.top + bottom * l.scale).toBeCloseTo(STAGE_HEIGHT, 5)
    }
  })

  it('캐릭터가 무대 밖으로 나가지 않는다', () => {
    for (const variant of variants) {
      const m = MASCOT_METRICS[variant]!
      const l = stageLayout(m)
      const [left, top, right] = m.box
      expect(l.left + left * l.scale).toBeGreaterThanOrEqual(0)
      expect(l.left + right * l.scale).toBeLessThanOrEqual(STAGE_WIDTH)
      expect(l.top + top * l.scale).toBeGreaterThanOrEqual(0)
    }
  })

  it('무대 크기는 포즈와 상관없이 항상 같다', () => {
    const sizes = variants.map((variant) => {
      const { container } = render(<MascotStage variant={variant} />)
      const stage = container.firstElementChild as HTMLElement
      return `${stage.style.width}x${stage.style.height}`
    })
    expect(new Set(sizes).size).toBe(1)
    expect(sizes[0]).toBe(`${STAGE_WIDTH}px x ${STAGE_HEIGHT}px`.replace(' x ', 'x'))
  })
})
