// 실제 API 호출에 공통으로 쓰는 요청 함수와 토큰 보관. docs/api-spec.md §1 (공통·인증).
// VITE_USE_MOCK=false 가 아니면 각 api 파일은 목업을 쓰고 이 파일의 request 는 호출되지 않는다.

export class ApiError extends Error {
  code: string
  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

export const useMock = import.meta.env.VITE_USE_MOCK !== 'false'
const baseUrl: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const TOKEN_KEY = 'synap.token'

// "로그인 상태 유지"를 끄면 탭을 닫을 때 지워지도록 sessionStorage 에 둔다.
export function saveToken(token: string, remember = true) {
  clearToken()
  try {
    ;(remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, token)
  } catch {
    // 저장소를 쓸 수 없는 환경에서는 이번 방문 동안만 유지할 방법이 없어 다시 로그인해야 한다.
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    // 위와 같음
  }
}

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export async function request(path: string, init: RequestInit = {}, auth = true): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (auth) {
    const token = readToken()
    if (!token) throw new ApiError('auth_invalid_token', '로그인이 필요해요.')
    headers.set('Authorization', `Bearer ${token}`)
  }

  const res = await fetch(`${baseUrl}${path}`, { ...init, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(body?.code ?? 'internal_error', body?.message ?? '요청에 실패했어요.')
  }
  return res
}
