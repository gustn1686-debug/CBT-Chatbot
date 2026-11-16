import type { MascotVariant } from '../components/Mascot'

// 마스코트 이미지마다 여백과 포즈가 달라서 같은 width/height 로 그리면 캐릭터가 커졌다 작아졌다 한다.
// 그래서 이미지를 직접 재서 "캐릭터 자체"의 크기를 맞춘다.
//
//  - width / height : 원본 이미지 크기(px)
//  - box            : 캐릭터가 실제로 보이는 영역 [왼쪽, 위, 오른쪽, 아래] (투명한 여백을 뺀 값)
//  - eyeHeight      : 눈 한 개의 세로 길이(px). 고개를 돌려도 거의 변하지 않아서 포즈와 상관없이
//                     캐릭터 크기를 비교하는 기준으로 쓴다. (눈 사이 간격은 고개가 돌아가면 달라진다)
//
// 값은 src/assets/mascot/*.webp 에서 잰 것이다. 이미지를 바꾸면 다시 재야 한다.
export type MascotMetrics = {
  width: number
  height: number
  box: [number, number, number, number]
  eyeHeight: number
}

export const MASCOT_METRICS: Partial<Record<MascotVariant, MascotMetrics>> = {
  waving: { width: 419, height: 514, box: [14, 14, 401, 501], eyeHeight: 26 },
  thinking: { width: 566, height: 567, box: [20, 13, 552, 554], eyeHeight: 31.5 },
  playing: { width: 677, height: 524, box: [22, 13, 663, 512], eyeHeight: 30 },
  main: { width: 600, height: 734, box: [7, 63, 593, 692], eyeHeight: 35.5 },
}

// 캐릭터를 눈 높이 EYE_PX 가 되는 배율로 그리면 어떤 포즈든 캐릭터 크기가 같아 보인다.
// 가장 넓은 포즈(playing)가 STAGE_WIDTH 안에, 가장 큰 포즈(waving)가 STAGE_HEIGHT 안에 들어오는 값이다.
export const EYE_PX = 13
export const STAGE_WIDTH = 320
export const STAGE_HEIGHT = 250

// 이미지를 무대 안에 놓는 위치. 캐릭터의 가로 중심이 무대 가운데, 발(아래쪽)이 무대 바닥에 오도록 맞춘다.
export function stageLayout(m: MascotMetrics, eyePx = EYE_PX) {
  const scale = eyePx / m.eyeHeight
  const [left, , right, bottom] = m.box
  return {
    scale,
    width: m.width * scale,
    height: m.height * scale,
    left: STAGE_WIDTH / 2 - ((left + right) / 2) * scale,
    top: STAGE_HEIGHT - bottom * scale,
  }
}
