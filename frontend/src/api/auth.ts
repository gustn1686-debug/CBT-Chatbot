// docs/api-spec.md §3 (인증)에 대응한다.
// VITE_USE_MOCK=false 이면 실제 API, 그 외에는 목업(mockAuth)을 쓴다.
import { getSession, saveSession } from '../lib/session'
import { request, saveToken, useMock } from './client'
import {
  mockLogin,
  mockSignUp,
  mockStartGuest,
  mockUsage,
  type Credentials,
  type SignUpInput,
  type Usage,
} from './mockAuth'

export type { Credentials, SignUpInput, Usage }
export { GUEST_SESSION_LIMIT } from './mockAuth'

type UserResponse = { access_token: string; user: { email: string; nickname: string } }

async function acceptUser({ access_token, user }: UserResponse, remember: boolean) {
  saveToken(access_token, remember)
  saveSession({ kind: 'user', email: user.email, nickname: user.nickname }, remember)
}

// POST /auth/guest
export async function startGuest(): Promise<void> {
  if (useMock) return mockStartGuest()
  const res = await request('/auth/guest', { method: 'POST' }, false)
  saveToken((await res.json()).access_token)
  saveSession({ kind: 'guest' })
}

// POST /auth/login
export async function login(input: Credentials): Promise<void> {
  if (useMock) return mockLogin(input)
  const res = await request(
    '/auth/login',
    { method: 'POST', body: JSON.stringify({ email: input.email, password: input.password }) },
    false,
  )
  await acceptUser(await res.json(), input.remember)
}

// POST /auth/register, 비회원이면 POST /auth/upgrade 로 그동안의 대화를 새 계정으로 옮긴다.
// 두 엔드포인트를 합칠지는 명세 §7-2 에서 합의 전이라 여기서 한 곳으로 모아 둔다.
export async function signUp(input: SignUpInput): Promise<void> {
  if (useMock) return mockSignUp(input)
  const upgrading = getSession()?.kind === 'guest'
  const res = await request(
    upgrading ? '/auth/upgrade' : '/auth/register',
    { method: 'POST', body: JSON.stringify(input) },
    upgrading,
  )
  await acceptUser(await res.json(), true)
}

// GET /me — 비회원의 무료 대화 사용량
export async function getUsage(): Promise<Usage> {
  if (useMock) return mockUsage()
  const res = await request('/me')
  const { usage } = await res.json()
  return {
    sessionCount: usage.session_count,
    limit: usage.guest_session_limit,
    signupRequired: usage.signup_required,
  }
}
