// 상담 계획 화면에서 같이 쓰는 값과 문구
import type { PushState } from './push'

export const SESSION_OPTIONS = [2, 3, 5, 8, 10] as const
export const DEFAULT_SESSIONS = 5
export const DAYS = ['월', '화', '수', '목', '금', '토', '일']
export const ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]

// "22:00" → "오후 10:00"
export function formatTime(time: string) {
  const [h, m] = time.split(':').map(Number)
  const half = h < 12 ? '오전' : '오후'
  const hour = h % 12 === 0 ? 12 : h % 12
  return `${half} ${hour}:${String(m).padStart(2, '0')}`
}

export function daysLabel(weekdays: number[]) {
  if (weekdays.length === 7) return '매일'
  return `매주 ${[...weekdays].sort().map((d) => DAYS[d]).join('·')}요일`
}

export function pushHint(state: PushState) {
  switch (state) {
    case 'ios-install':
      return '아이폰은 Safari 공유 버튼 → "홈 화면에 추가"로 설치하면 알림을 받을 수 있어요. 계획은 지금 바로 시작할 수 있어요.'
    case 'denied':
      return '브라우저에서 알림이 차단돼 있어요. 브라우저 설정에서 허용하면 알림을 받을 수 있어요.'
    case 'server-off':
      return '지금은 알림을 보낼 수 없어요. 계획은 그대로 시작할 수 있어요.'
    case 'unsupported':
      return '이 브라우저에서는 알림을 받을 수 없어요. 계획은 그대로 시작할 수 있어요.'
    default:
      return ''
  }
}
