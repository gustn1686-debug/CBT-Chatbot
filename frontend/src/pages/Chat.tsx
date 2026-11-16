import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { getUsage, type Usage } from '../api/auth'
import { endConversation } from '../api/chat'
import { ChatHeader } from '../components/chat/ChatHeader'
import { ChatInput } from '../components/chat/ChatInput'
import { ConversationDrawer } from '../components/chat/ConversationDrawer'
import { MessageBubble } from '../components/chat/MessageBubble'
import { OfflineBanner } from '../components/chat/OfflineBanner'
import { ConfirmModal } from '../components/ConfirmModal'
import { CrisisFlow } from '../components/crisis/CrisisFlow'
import { GuestBanner } from '../components/guest/GuestBanner'
import { GuestSignupSheet } from '../components/guest/GuestSignupSheet'
import { Mascot } from '../components/Mascot'
import { useChat } from '../hooks/useChat'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useOnlineStatus } from '../hooks/useOnlineStatus'
import { getSession } from '../lib/session'

// 홈이 곧 채팅이다. (ChatGPT 앱처럼) 앱을 열면 바로 새 대화가 시작되고,
// 왼쪽 메뉴의 지난 대화를 누르면 /chat/:id 로 그 대화를 이어서 한다.
// 새 대화(/)로 다시 들어오거나 다른 대화로 옮기면 화면을 새로 만들어 이전 상태가 섞이지 않게 한다.
export function Chat() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  return <ChatScreen key={id ?? location.key} existingId={id} />
}

function ChatScreen({ existingId }: { existingId?: string }) {
  useDocumentTitle('대화')
  const navigate = useNavigate()
  const isGuest = getSession()?.kind === 'guest'
  const { messages, busy, crisis, loading, loadFailed, conversationId, sent, send, retry } = useChat(existingId)
  const [dismissedCrisis, setDismissedCrisis] = useState<string | null>(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const [usage, setUsage] = useState<Usage | null>(null)
  const [signupSheetDismissed, setSignupSheetDismissed] = useState(false)
  // 비회원이 이야기를 나누고 다른 곳으로 가려 할 때, 가입 안내에서 "나중에"를 고르면 실행할 이동
  const [pendingLeave, setPendingLeave] = useState<(() => void) | null>(null)
  const online = useOnlineStatus()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ block: 'end' })
  }, [messages])

  useEffect(() => {
    if (loadFailed) navigate('/', { replace: true })
  }, [loadFailed, navigate])

  useEffect(() => {
    if (isGuest) getUsage().then(setUsage)
  }, [isGuest])

  // 이 화면을 떠날 때(다른 대화로 옮기거나 설정으로 갈 때) 서버가 이 회기를 요약해 두도록 알린다.
  // 실패해도 이동에는 영향이 없다. 종료를 못 알린 대화는 다음 새 대화를 시작할 때 서버가 따라잡아 요약한다.
  useEffect(
    () => () => {
      if (sent.current && conversationId.current) void endConversation(conversationId.current).catch(() => {})
    },
    [sent, conversationId],
  )

  // 답변이 다 도착했을 때만 한 번 읽어 준다. (불러온 지난 메시지는 읽지 않는다)
  // (글자가 늘어날 때마다 읽으면 알아듣기 어렵다)
  const last = messages[messages.length - 1]
  const announcement =
    last?.role === 'assistant' && last.status === 'sent' && !last.id.startsWith('s-') ? last.content : ''

  // 비회원이 실제로 이야기를 나눴다면, 이 대화를 떠나기 전에 보관(가입)을 한 번 안내한다.
  const requestLeave = (go: () => void) => {
    if (isGuest && sent.current) setPendingLeave(() => go)
    else go()
  }

  const isNewAndEmpty = !existingId && messages.length === 0
  // 무료 대화를 다 쓴 비회원이 새 대화를 시작하려 하면 먼저 가입을 안내한다. ("다음에 할게요"로 계속할 수 있다)
  const showSignupSheet = !existingId && isGuest && usage?.signupRequired === true && !signupSheetDismissed

  return (
    <div className="flex h-dvh flex-col">
      {!online && <OfflineBanner />}
      <ChatHeader isGuest={isGuest} online={online} onMenu={() => setMenuOpen(true)} />

      <main aria-busy={loading} className="flex flex-1 flex-col gap-3.5 overflow-y-auto px-4 pt-1.5 pb-3">
        {isNewAndEmpty ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-5">
            <div className="flex flex-col items-center gap-2.5 text-center">
              <Mascot variant="waving" width={84} height={100} />
              <h2 className="text-[22px]/[normal] font-bold">오늘은 어떤 하루였나요</h2>
              <p className="text-[12.5px]/[normal] text-muted">마음이 복잡할 때, 잠시 정리해볼까요</p>
            </div>
            {isGuest && usage && (
              <div className="w-full">
                <GuestBanner used={usage.sessionCount} limit={usage.limit} />
              </div>
            )}
          </div>
        ) : (
          messages.map((m) => (
            <MessageBubble
              key={m.id}
              role={m.role}
              failed={m.status === 'failed'}
              failReason={m.failReason}
              onRetry={() => retry(m.id)}
            >
              {m.content}
            </MessageBubble>
          ))
        )}
        <div ref={bottomRef} />
      </main>
      <p role="status" className="sr-only">
        {announcement}
      </p>

      <ChatInput disabled={busy} offline={!online} onSend={send} />

      {menuOpen && (
        <ConversationDrawer currentId={existingId} onClose={() => setMenuOpen(false)} onLeave={requestLeave} />
      )}

      {crisis && crisis.messageId !== dismissedCrisis && (
        <CrisisFlow resources={crisis.resources} onClose={() => setDismissedCrisis(crisis.messageId)} />
      )}

      {pendingLeave && (
        <ConfirmModal
          title="대화를 보관하려면 가입이 필요해요"
          description={'가입하면 지금까지 나눈 대화를\n언제든 이어서 볼 수 있어요.\n가입하시겠어요?'}
          cancelLabel="나중에 할게요"
          confirmLabel="가입하기"
          onCancel={() => {
            const go = pendingLeave
            setPendingLeave(null)
            go()
          }}
          onConfirm={() => {
            setPendingLeave(null)
            navigate('/signup')
          }}
        />
      )}

      {showSignupSheet && usage && (
        <GuestSignupSheet
          limit={usage.limit}
          onJoin={() => navigate('/signup')}
          onLater={() => setSignupSheetDismissed(true)}
        />
      )}
    </div>
  )
}
