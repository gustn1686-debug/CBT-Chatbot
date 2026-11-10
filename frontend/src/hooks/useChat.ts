import { useCallback, useRef, useState } from 'react'
import { createConversation, streamMessage, type CrisisResource } from '../api/chat'

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  // user: 전송 실패 여부 / assistant: 응답이 아직 오는 중인지
  status: 'sent' | 'failed' | 'streaming'
}

// Figma: HiFi_3_채팅 첫 말풍선
const GREETING: ChatMessage = {
  id: 'greeting',
  role: 'assistant',
  content: '안녕하세요. 오늘은 어떤 얘기를 나눠볼까요?',
  status: 'sent',
}

export type CrisisState = { messageId: string; resources: CrisisResource[] } | null

export function useChat(greeting?: string) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    greeting ? { ...GREETING, content: greeting } : GREETING,
  ])
  const [busy, setBusy] = useState(false)
  const [crisis, setCrisis] = useState<CrisisState>(null)
  const [signupRequired, setSignupRequired] = useState(false)
  const conversationId = useRef<string | null>(null)
  const counter = useRef(0)

  const nextId = (prefix: string) => `${prefix}-${++counter.current}`

  const update = (id: string, patch: Partial<ChatMessage> | ((m: ChatMessage) => Partial<ChatMessage>)) =>
    setMessages((list) =>
      list.map((m) => (m.id === id ? { ...m, ...(typeof patch === 'function' ? patch(m) : patch) } : m)),
    )

  // 사용자 메시지(userId)에 대한 응답을 받아온다. 실패하면 그 메시지를 '전송 실패'로 표시한다.
  const request = useCallback(async (userId: string, content: string) => {
    const replyId = nextId('a')
    setBusy(true)
    setMessages((list) => [...list, { id: replyId, role: 'assistant', content: '', status: 'streaming' }])

    try {
      conversationId.current ??= await createConversation()
      for await (const event of streamMessage(conversationId.current, content)) {
        if (event.type === 'meta') {
          if (event.crisis) setCrisis({ messageId: event.messageId, resources: event.crisisResources })
          if (event.signupRequired) setSignupRequired(true)
        } else if (event.type === 'token') {
          update(replyId, (m) => ({ content: m.content + event.delta }))
        } else if (event.type === 'done') {
          update(replyId, { status: 'sent' })
        } else {
          throw new Error(event.message)
        }
      }
      update(replyId, { status: 'sent' })
    } catch {
      // 응답이 하나도 오지 않았으면 빈 말풍선을 치우고, 받은 만큼은 남긴다.
      setMessages((list) =>
        list
          .filter((m) => !(m.id === replyId && m.content === ''))
          .map((m) => (m.id === userId ? { ...m, status: 'failed' } : m.id === replyId ? { ...m, status: 'sent' } : m)),
      )
    } finally {
      setBusy(false)
    }
  }, [])

  const send = useCallback(
    (text: string) => {
      const content = text.trim()
      if (!content || busy) return
      const userId = nextId('u')
      setMessages((list) => [...list, { id: userId, role: 'user', content, status: 'sent' }])
      void request(userId, content)
    },
    [busy, request],
  )

  const retry = useCallback(
    (id: string) => {
      const target = messages.find((m) => m.id === id)
      if (!target || busy) return
      update(id, { status: 'sent' })
      void request(id, target.content)
    },
    [messages, busy, request],
  )

  return { messages, busy, crisis, signupRequired, send, retry }
}
