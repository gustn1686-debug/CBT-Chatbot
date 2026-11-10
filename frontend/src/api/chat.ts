// docs/api-spec.md §4~5 (대화 생성, SSE 채팅)에 대응한다.
// VITE_USE_MOCK=false 이면 실제 API, 그 외에는 목업(mockChat)을 쓴다.
import { ApiError, request, useMock } from './client'
import { mockCreateConversation, mockStreamMessage } from './mockChat'
import { readSse } from './sse'

export type CrisisResource = { name: string; tel: string }

export type ChatEvent =
  | {
      type: 'meta'
      messageId: string
      crisis: boolean
      signupRequired: boolean
      crisisResources: CrisisResource[]
    }
  | { type: 'token'; delta: string }
  | { type: 'done'; messageId: string; finishReason: string }
  | { type: 'error'; code: string; message: string }

export async function createConversation(): Promise<string> {
  if (useMock) return mockCreateConversation()
  const res = await request('/conversations', { method: 'POST', body: JSON.stringify({}) })
  return (await res.json()).id
}

export async function* streamMessage(
  conversationId: string,
  content: string,
): AsyncGenerator<ChatEvent> {
  if (useMock) {
    yield* mockStreamMessage(content)
    return
  }

  const res = await request(`/conversations/${conversationId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  })
  if (!res.body) throw new ApiError('internal_error', '응답을 받지 못했어요.')

  for await (const { event, data } of readSse(res.body)) {
    const payload = JSON.parse(data)
    if (event === 'meta') {
      yield {
        type: 'meta',
        messageId: payload.message_id,
        crisis: payload.crisis,
        signupRequired: payload.signup_required,
        crisisResources: payload.crisis_resources ?? [],
      }
    } else if (event === 'token') {
      yield { type: 'token', delta: payload.delta }
    } else if (event === 'done') {
      yield { type: 'done', messageId: payload.message_id, finishReason: payload.finish_reason }
    } else if (event === 'error') {
      yield { type: 'error', code: payload.code, message: payload.message }
    }
  }
}
