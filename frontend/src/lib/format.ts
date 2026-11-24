// 2025-03-12 → 2025.03.12 (Figma 표기)
export const formatDate = (iso: string) => iso.replaceAll('-', '.')

// 서버의 ISO 시각(2026-11-10T06:49:29Z)을 이 기기의 날짜(YYYY-MM-DD)로 바꾼다.
export function toLocalDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// 시각은 상담 계획의 시간대(timeZone)로 보여준다. 기기 시간대가 달라도 사용자가 고른 "밤 10시"가 그대로 보이게.
function parts(iso: string, timeZone?: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  const get = (type: string) =>
    new Intl.DateTimeFormat('ko-KR', {
      timeZone,
      month: 'numeric',
      day: 'numeric',
      weekday: 'short',
      hour: 'numeric',
      minute: '2-digit',
      hour12: false,
    })
      .formatToParts(d)
      .find((p) => p.type === type)?.value ?? ''
  return {
    month: Number(get('month')),
    day: Number(get('day')),
    weekday: get('weekday'),
    hour: Number(get('hour')) % 24,
    minute: get('minute').padStart(2, '0'),
  }
}

// 2026-11-24T13:00:00Z → "11월 24일 (화)"
export function formatMonthDay(iso: string, timeZone?: string): string {
  const p = parts(iso, timeZone)
  if (!p) return iso.slice(0, 10)
  return `${p.month}월 ${p.day}일 (${p.weekday})`
}

// → "11월 24일 (화) 오후 10:00"
export function formatMonthDayTime(iso: string, timeZone?: string): string {
  const p = parts(iso, timeZone)
  if (!p) return iso
  const hour = p.hour % 12 === 0 ? 12 : p.hour % 12
  return `${formatMonthDay(iso, timeZone)} ${p.hour < 12 ? '오전' : '오후'} ${hour}:${p.minute}`
}
