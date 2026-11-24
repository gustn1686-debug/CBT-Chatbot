import { afterEach, describe, expect, it, vi } from 'vitest'

// 실제 서버 모드(useMock=false)에서의 동작을 본다.
vi.mock('../api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/client')>()),
  useMock: false,
}))

const { saveToken, clearToken } = await import('../api/client')
const { getSession, saveSession } = await import('./session')

afterEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})

describe('getSession (실제 서버 모드)', () => {
  it('토큰이 있으면 저장된 세션을 돌려준다', () => {
    saveToken('token')
    saveSession({ kind: 'guest' })
    expect(getSession()).toEqual({ kind: 'guest' })
  })

  it('목업 때 남은, 토큰 없는 세션은 로그인하지 않은 것으로 보고 지운다', () => {
    clearToken()
    saveSession({ kind: 'guest' })
    expect(getSession()).toBeNull()
    expect(localStorage.getItem('synap.session')).toBeNull()
  })
})
