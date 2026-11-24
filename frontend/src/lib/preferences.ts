const ONBOARDED_KEY = 'synap.onboarded'
const SAVE_HISTORY_KEY = 'synap.saveHistory'
const NOTIFICATIONS_KEY = 'synap.notifications'
const RETENTION_KEY = 'synap.retentionDays'

// 설정 화면의 "기록 저장 기간" 선택지. 서버 보관 정책(docs/api-spec.md §9-5)이 정해지면 맞춘다.
export const RETENTION_OPTIONS = [30, 90, 180, 365] as const
export type RetentionDays = (typeof RETENTION_OPTIONS)[number]
export const DEFAULT_RETENTION_DAYS: RetentionDays = 90

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // 저장소를 쓸 수 없는 환경(사생활 보호 모드 등)에서는 세션 동안만 유지된다.
  }
}

export const isOnboarded = () => read(ONBOARDED_KEY) === '1'
export const completeOnboarding = (saveHistory: boolean) => {
  write(ONBOARDED_KEY, '1')
  write(SAVE_HISTORY_KEY, saveHistory ? '1' : '0')
}

// 값이 없으면 온보딩에서 동의한 것과 같은 기본값(저장함)으로 본다.
export const isSaveHistory = () => read(SAVE_HISTORY_KEY) !== '0'
export const setSaveHistory = (value: boolean) => write(SAVE_HISTORY_KEY, value ? '1' : '0')

// 알림 스위치 값. 회원은 실제 웹 푸시 구독(lib/push.ts)과 함께 바뀌고, 비회원은 이 값만 저장한다.
export const isNotificationsOn = () => read(NOTIFICATIONS_KEY) !== '0'
export const setNotificationsOn = (value: boolean) => write(NOTIFICATIONS_KEY, value ? '1' : '0')

export function getRetentionDays(): RetentionDays {
  const saved = Number(read(RETENTION_KEY))
  return RETENTION_OPTIONS.find((days) => days === saved) ?? DEFAULT_RETENTION_DAYS
}
export const setRetentionDays = (days: RetentionDays) => write(RETENTION_KEY, String(days))
