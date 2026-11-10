import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { endConversation } from '../api/chat'
import { ChatInput } from '../components/chat/ChatInput'
import { MessageBubble } from '../components/chat/MessageBubble'
import { OfflineBanner } from '../components/chat/OfflineBanner'
import { ConfirmModal } from '../components/ConfirmModal'
import { CrisisFlow } from '../components/crisis/CrisisFlow'
import { useChat } from '../hooks/useChat'
import { useOnlineStatus } from '../hooks/useOnlineStatus'
import { getSession } from '../lib/session'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

export function Chat() {
  useDocumentTitle('대화')
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { messages, busy, crisis, loading, loadFailed, conversationId, send, retry } = useChat(id)
  const [dismissedCrisis, setDismissedCrisis] = useState<string | null>(null)
  const [confirmingEnd, setConfirmingEnd] = useState(false)
  const [offeringSave, setOfferingSave] = useState(false)
  const online = useOnlineStatus()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ block: 'end' })
  }, [messages])

  // 나갈 때 서버가 이 회기를 요약해 두도록 알린다. 실패해도 나가는 데는 영향이 없다.
  // (종료 없이 나간 대화는 다음 새 대화를 시작할 때 서버가 따라잡아 요약한다)
  const leave = () => {
    if (conversationId.current) void endConversation(conversationId.current).catch(() => {})
    navigate('/', { replace: true })
  }

  useEffect(() => {
    if (loadFailed) navigate('/', { replace: true })
  }, [loadFailed, navigate])

  // 비회원이 실제로 이야기를 나눴다면, 나가기 전에 기록 보관(가입)을 한 번 안내한다.
  const endChat = () => {
    setConfirmingEnd(false)
    const talked = messages.some((m) => m.role === 'user')
    if (getSession()?.kind === 'guest' && talked) setOfferingSave(true)
    else leave()
  }

  // 답변이 다 도착했을 때만 한 번 읽어 준다. (불러온 지난 메시지는 읽지 않는다)
  // (글자가 늘어날 때마다 읽으면 알아듣기 어렵다)
  const last = messages[messages.length - 1]
  const announcement =
    last?.role === 'assistant' && last.status === 'sent' && last.id !== 'greeting' && !last.id.startsWith('s-')
      ? last.content
      : ''

  return (
    <div className="flex h-dvh flex-col">
      {!online && <OfflineBanner />}
      <header className={`flex items-center justify-between px-4 pb-2.5 ${online ? 'pt-5' : 'pt-1.5'}`}>
        <button type="button" onClick={leave} aria-label="뒤로" className="-m-3 p-3 text-[20px]/[normal]">
          ‹
        </button>
        <h1 className="text-[14px]/[normal] font-bold">대화</h1>
        <button
          type="button"
          onClick={() => setConfirmingEnd(true)}
          className="relative rounded-[20px] border border-line bg-white px-3 py-1.5 text-[11px]/[normal] text-muted after:absolute after:inset-x-0 after:-inset-y-2 after:content-['']"
        >
          대화 종료
        </button>
      </header>

      <main aria-busy={loading} className="flex flex-1 flex-col gap-3.5 overflow-y-auto px-4 pt-1.5 pb-3">
        {messages.map((m) => (
          <MessageBubble
            key={m.id}
            role={m.role}
            failed={m.status === 'failed'}
            failReason={m.failReason}
            onRetry={() => retry(m.id)}
          >
            {m.content}
          </MessageBubble>
        ))}
        <div ref={bottomRef} />
      </main>
      <p role="status" className="sr-only">
        {announcement}
      </p>

      <ChatInput disabled={busy} offline={!online} onSend={send} />

      {crisis && crisis.messageId !== dismissedCrisis && (
        <CrisisFlow resources={crisis.resources} onClose={() => setDismissedCrisis(crisis.messageId)} />
      )}

      {confirmingEnd && (
        <ConfirmModal
          title="대화를 종료할까요?"
          description="지금까지 나눈 이야기는 기록 저장 동의 여부에 따라 보관돼요."
          confirmLabel="종료하기"
          onCancel={() => setConfirmingEnd(false)}
          onConfirm={endChat}
        />
      )}

      {offeringSave && (
        <ConfirmModal
          title="오늘 나눈 대화, 보관해둘까요?"
          description={'비회원 기록은 이 기기에만 남아서, 앱을 지우거나\n기기를 바꾸면 다시 볼 수 없어요.\n가입하면 언제든 이어서 볼 수 있어요.'}
          cancelLabel="괜찮아요"
          confirmLabel="가입하고 보관하기"
          onCancel={leave}
          onConfirm={() => navigate('/signup', { replace: true })}
        />
      )}
    </div>
  )
}
