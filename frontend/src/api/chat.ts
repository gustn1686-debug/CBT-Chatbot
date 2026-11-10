// docs/api-spec.md §4~5 (대화 생성·목록·상세·종료, SSE 채팅)에 대응한다.
// VITE_USE_MOCK=false 이면 실제 API, 그 외에는 목업(mockChat)을 쓴다.
import { ApiError, request, useMock } from './client'
import {
  mockCreateConversation,
  mockDeleteAllConversations,
  mockEndConversation,
  mockGetConversation,
  mockListConversations,
  mockStreamMessage,
} from './mockChat'
import { readSse } from './sse'

export type CrisisResource = { name: string; tel: string }

export type ConversationItem = { id: string; title: string | null; updatedAt: string; messageCount: number }
export type StoredMessage = { id: string; role: 'user' | 'assistant'; content: string }
export type ConversationDetail = { id: string; title: string | null; messages: StoredMessage[] }

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

// GET /conversations — 홈의 대화 목록 (최근 대화순)
export async function listConversations(): Promise<ConversationItem[]> {
  if (useMock) return mockListConversations()
  const res = await request('/conversations?limit=50')
  const { items } = await res.json()
  return items.map((i: { id: string; title: string | null; updated_at: string; message_count: number }) => ({
    id: i.id,
    title: i.title,
    updatedAt: i.updated_at,
    messageCount: i.message_count,
  }))
}

// GET /conversations/{id} — 지난 대화를 이어서 할 때 이전 메시지를 불러온다.
export async function getConversation(id: string): Promise<ConversationDetail> {
  if (useMock) return mockGetConversation(id)
  const res = await request(`/conversations/${id}`)
  const body = await res.json()
  return { id: body.id, title: body.title, messages: body.messages }
}

// POST /conversations/{id}/end — 대화 종료. 서버가 회기를 요약해 다음 대화에서 기억한다. (응답은 기다리지 않는다)
export async function endConversation(id: string): Promise<void> {
  if (useMock) return mockEndConversation()
  await request(`/conversations/${id}/end`, { method: 'POST' })
}

// DELETE /conversations — 설정의 "전체 기록 삭제"
export async function deleteAllConversations(): Promise<void> {
  if (useMock) return mockDeleteAllConversations()
  await request('/conversations', { method: 'DELETE' })
}

export async function* streamMessage(
  conversationId: string,
  content: string,
): AsyncGenerator<ChatEvent> {
  if (useMock) {
    yield* mockStreamMessage(conversationId, content)
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
