// 백엔드 없이 채팅 화면을 개발하기 위한 목업. api-spec 의 SSE 이벤트 순서를 그대로 흉내 낸다.
// 위기 감지는 실제로는 서버가 하며, 여기서는 UI 확인용으로만 키워드를 본다.
import { DEFAULT_CRISIS_RESOURCES } from '../lib/crisis'
import { ApiError } from './client'
import type { ChatEvent, ConversationDetail, ConversationItem } from './chat'
import { mockBumpSession, mockUsage } from './mockAuth'

const CRISIS_KEYWORDS = ['죽고 싶', '죽고싶', '자살']
const FAIL_TRIGGER = '[실패]' // 전송 실패 UI 확인용: 이 문구가 든 메시지는 처음 한 번만 실패한다

const replies = [
  '그런 생각이 들 때 마음이 어떠셨어요?',
  '그렇게 느끼신 이유를 조금 더 이야기해 주실 수 있을까요?',
  '그 생각을 뒷받침하는 사실과, 그렇지 않은 사실을 각각 떠올려 볼까요?',
]

export const mockOptions = { delayMs: 35 }

let replyIndex = 0
const failedOnce = new Set<string>()

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// 대화 목록 목업. 화면 확인용: 주소에 ?mock=empty 를 붙여 열면 대화가 없는 상태로 시작한다.
type StoredConversation = ConversationDetail & { updatedAt: string }

const seed = (): StoredConversation[] => [
  {
    id: 'c-3',
    title: '발표 자료 오타 때문에 마음이 불편해요',
    updatedAt: '2025-03-12T09:00:00Z',
    messages: [
      { id: 'c-3-1', role: 'user', content: '발표 자료 오타 때문에 마음이 불편해요' },
      { id: 'c-3-2', role: 'assistant', content: '그런 생각이 들 때 마음이 어떠셨어요?' },
    ],
  },
  {
    id: 'c-2',
    title: '친구가 약속을 당일에 취소했어요',
    updatedAt: '2025-03-09T09:00:00Z',
    messages: [
      { id: 'c-2-1', role: 'user', content: '친구가 약속을 당일에 취소했어요' },
      { id: 'c-2-2', role: 'assistant', content: '그렇게 느끼신 이유를 조금 더 이야기해 주실 수 있을까요?' },
    ],
  },
  {
    id: 'c-1',
    title: '면접 결과를 기다리는 중이에요',
    updatedAt: '2025-03-05T09:00:00Z',
    messages: [
      { id: 'c-1-1', role: 'user', content: '면접 결과를 기다리는 중이에요' },
      { id: 'c-1-2', role: 'assistant', content: '기다리는 동안 어떤 생각이 가장 자주 떠오르세요?' },
    ],
  },
]

const startEmpty = new URLSearchParams(window.location.search).get('mock') === 'empty'
let conversations: StoredConversation[] = startEmpty ? [] : seed()

// 테스트에서 상태를 되돌리거나 원하는 대화로 채울 때 쓴다.
export function resetMockConversations(list: StoredConversation[] = seed()) {
  conversations = list.map((c) => ({ ...c, messages: [...c.messages] }))
}

export async function mockListConversations(): Promise<ConversationItem[]> {
  return [...conversations]
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
    .map((c) => ({ id: c.id, title: c.title, updatedAt: c.updatedAt, messageCount: c.messages.length }))
}

export async function mockGetConversation(id: string): Promise<ConversationDetail> {
  const found = conversations.find((c) => c.id === id)
  if (!found) throw new ApiError('not_found', '대화를 찾을 수 없어요.')
  return { id: found.id, title: found.title, messages: found.messages.map((m) => ({ ...m })) }
}

export async function mockEndConversation(): Promise<void> {
  // 실제로는 서버가 이 대화를 요약해 둔다. 목업에서는 할 일이 없다.
}

export async function mockDeleteAllConversations(): Promise<void> {
  conversations = []
}

export async function mockCreateConversation(): Promise<string> {
  mockBumpSession()
  const id = `mock-${Date.now()}-${conversations.length}`
  conversations.push({ id, title: null, updatedAt: new Date().toISOString(), messages: [] })
  return id
}

export async function* mockStreamMessage(conversationId: string, content: string): AsyncGenerator<ChatEvent> {
  await sleep(mockOptions.delayMs * 4)
  if (content.includes(FAIL_TRIGGER) && !failedOnce.has(content)) {
    failedOnce.add(content)
    throw new Error('mock network error')
  }

  const crisis = CRISIS_KEYWORDS.some((keyword) => content.includes(keyword))
  const messageId = `m-${Date.now()}`
  const stored = conversations.find((c) => c.id === conversationId)
  if (stored) {
    stored.title ??= content.slice(0, 30)
    stored.messages.push({ id: `${messageId}-u`, role: 'user', content })
    stored.updatedAt = new Date().toISOString()
  }

  yield {
    type: 'meta',
    messageId,
    crisis,
    signupRequired: (await mockUsage()).signupRequired,
    crisisResources: crisis ? DEFAULT_CRISIS_RESOURCES : [],
  }

  const text = crisis
    ? '지금 많이 힘드신 것 같아요. 혼자 견디지 않으셔도 괜찮아요. 아래 상담 전화로 연결해 드릴게요.'
    : replies[replyIndex++ % replies.length]

  for (const delta of text.match(/.{1,3}/g) ?? []) {
    await sleep(mockOptions.delayMs)
    yield { type: 'token', delta }
  }
  stored?.messages.push({ id: messageId, role: 'assistant', content: text })
  yield { type: 'done', messageId, finishReason: 'stop' }
}
