// 지금 쓰는 사람이 비회원인지 회원인지 기억한다. (토큰 자체는 api/client.ts 가 보관)
export type Session = { kind: 'guest' } | { kind: 'user'; email: string; nickname: string }

const KEY = 'synap.session'

function parse(raw: string | null): Session | null {
  if (!raw) return null
  try {
    const value = JSON.parse(raw)
    if (value?.kind === 'guest') return { kind: 'guest' }
    if (value?.kind === 'user' && typeof value.email === 'string' && typeof value.nickname === 'string') {
      return { kind: 'user', email: value.email, nickname: value.nickname }
    }
  } catch {
    // 깨진 값은 없는 것으로 본다.
  }
  return null
}

export function getSession(): Session | null {
  try {
    return parse(localStorage.getItem(KEY)) ?? parse(sessionStorage.getItem(KEY))
  } catch {
    return null
  }
}

// remember=false 면 탭을 닫을 때 로그아웃된다. (로그인 화면의 "로그인 상태 유지")
export function saveSession(session: Session, remember = true) {
  clearSession()
  try {
    ;(remember ? localStorage : sessionStorage).setItem(KEY, JSON.stringify(session))
  } catch {
    // 저장소를 쓸 수 없으면 새로고침 시 시작 화면으로 돌아간다.
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(KEY)
    sessionStorage.removeItem(KEY)
  } catch {
    // 위와 같음
  }
}
