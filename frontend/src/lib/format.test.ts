import { formatMonthDay, formatMonthDayTime } from './format'

describe('상담 계획 시각 표기', () => {
  it('계획의 시간대로 보여준다 (기기 시간대와 상관없이)', () => {
    // 서울 2026-11-26(목) 22:00 = UTC 13:00
    expect(formatMonthDayTime('2026-11-26T13:00:00Z', 'Asia/Seoul')).toBe('11월 26일 (목) 오후 10:00')
    expect(formatMonthDayTime('2026-11-26T13:00:00Z', 'UTC')).toBe('11월 26일 (목) 오후 1:00')
    expect(formatMonthDayTime('2026-11-25T15:05:00Z', 'Asia/Seoul')).toBe('11월 26일 (목) 오전 12:05')
    expect(formatMonthDay('2026-11-24T13:00:00Z', 'Asia/Seoul')).toBe('11월 24일 (화)')
  })
})
