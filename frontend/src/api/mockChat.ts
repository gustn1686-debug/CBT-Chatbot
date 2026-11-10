// 백엔드 없이 채팅 화면을 개발하기 위한 목업. api-spec 의 SSE 이벤트 순서를 그대로 흉내 낸다.
// 위기 감지는 실제로는 서버가 하며, 여기서는 UI 확인용으로만 키워드를 본다.
import { DEFAULT_CRISIS_RESOURCES } from '../lib/crisis'
import type { ChatEvent } from './chat'
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

export async function mockCreateConversation(): Promise<string> {
  mockBumpSession()
  return `mock-${Date.now()}`
}

export async function* mockStreamMessage(content: string): AsyncGenerator<ChatEvent> {
  await sleep(mockOptions.delayMs * 4)
  if (content.includes(FAIL_TRIGGER) && !failedOnce.has(content)) {
    failedOnce.add(content)
    throw new Error('mock network error')
  }

  const crisis = CRISIS_KEYWORDS.some((keyword) => content.includes(keyword))
  const messageId = `m-${Date.now()}`

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
  yield { type: 'done', messageId, finishReason: 'stop' }
}
