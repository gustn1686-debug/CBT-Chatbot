// 백엔드 없이 인증·비회원 화면을 개발하기 위한 목업. 비밀번호는 저장하지 않는다.
// 화면 확인용 입력값:
//   로그인  비밀번호가 "wrongpass1"     → 이메일/비밀번호 불일치 오류
//   회원가입 이메일이 "taken@example.com" → 이미 가입된 이메일 오류
// 그 외 형식에 맞는 입력은 모두 성공한다.
import { getSession, saveSession } from '../lib/session'
import { ApiError } from './client'

export const GUEST_SESSION_LIMIT = 3
const COUNT_KEY = 'synap.mock.sessionCount'

export const WRONG_PASSWORD = 'wrongpass1'
export const TAKEN_EMAIL = 'taken@example.com'

export type Credentials = { email: string; password: string; remember: boolean }
export type SignUpInput = { email: string; password: string; nickname: string }
export type Usage = { sessionCount: number; limit: number; signupRequired: boolean }

const nicknameFrom = (email: string) => email.split('@')[0] || '회원'

export async function mockStartGuest() {
  saveSession({ kind: 'guest' })
}

export async function mockLogin({ email, password, remember }: Credentials) {
  if (password === WRONG_PASSWORD) {
    throw new ApiError('auth_invalid_credentials', '이메일 또는 비밀번호가 맞지 않아요.')
  }
  saveSession({ kind: 'user', email, nickname: nicknameFrom(email) }, remember)
}

export async function mockSignUp({ email, nickname }: SignUpInput) {
  if (email === TAKEN_EMAIL) throw new ApiError('email_taken', '이미 가입된 이메일이에요.')
  // 비회원이던 사람이면 그동안의 사용 횟수가 새 계정으로 옮겨 가는 것으로 본다. (명세 §7-2 미정)
  saveSession({ kind: 'user', email, nickname })
}

function readCount(): number {
  try {
    return Number(localStorage.getItem(COUNT_KEY)) || 0
  } catch {
    return 0
  }
}

// 비회원이 새 대화(회기)를 시작할 때마다 하나 늘어난다.
export function mockBumpSession() {
  if (getSession()?.kind !== 'guest') return
  try {
    localStorage.setItem(COUNT_KEY, String(readCount() + 1))
  } catch {
    // 저장하지 못해도 화면은 계속 쓸 수 있다.
  }
}

export async function mockUsage(): Promise<Usage> {
  const sessionCount = readCount()
  const guest = getSession()?.kind === 'guest'
  return { sessionCount, limit: GUEST_SESSION_LIMIT, signupRequired: guest && sessionCount >= GUEST_SESSION_LIMIT }
}
