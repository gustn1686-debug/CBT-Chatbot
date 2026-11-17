import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { SettingsIcon } from '../SettingsIcon'
import { listConversations, type ConversationItem } from '../../api/chat'
import { useDialogFocus } from '../../hooks/useDialogFocus'
import { formatDate, toLocalDate } from '../../lib/format'

type ConversationDrawerProps = {
  currentId?: string
  onClose: () => void
  // 다른 화면·대화로 옮기기 전에 거치는 곳. 필요하면(예: 비회원 가입 안내) 확인을 받고 go 를 실행한다.
  onLeave: (go: () => void) => void
}

// ChatGPT 앱의 왼쪽 메뉴처럼 지난 대화 목록을 보여준다. 누르면 그 대화를 이어서 한다.
export function ConversationDrawer({ currentId, onClose, onLeave }: ConversationDrawerProps) {
  const navigate = useNavigate()
  const dialogRef = useRef<HTMLDivElement>(null)
  const newChatRef = useRef<HTMLButtonElement>(null)
  const [items, setItems] = useState<ConversationItem[] | null>(null)
  useDialogFocus(dialogRef, newChatRef)

  useEffect(() => {
    let cancelled = false
    listConversations()
      .then((all) => !cancelled && setItems(all.filter((c) => c.messageCount > 0)))
      .catch(() => !cancelled && setItems([]))
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const startNew = () => {
    onClose()
    // 이미 새 대화 화면이어도 처음 상태로 되돌린다. (location.key 가 바뀌어 화면이 새로 만들어진다)
    onLeave(() => navigate('/', { state: { fresh: Date.now() } }))
  }

  // 링크를 눌러 이동할 때 onLeave 를 거친다. (새 탭으로 열기 등은 브라우저에 맡긴다)
  const goTo = (to: string) => (e: MouseEvent<HTMLAnchorElement>) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return
    e.preventDefault()
    onClose()
    onLeave(() => navigate(to))
  }

  return (
    // 화면 전체를 어둡게 덮되, 메뉴 자체는 앱 화면(최대 393px 기둥)의 왼쪽에 붙인다.
    // (노트북처럼 넓은 화면에서 브라우저 맨 왼쪽이 아니라 스마트폰 화면 왼쪽에 열리게)
    <div className="fixed inset-0 z-40 flex justify-center">
      {/* 바깥을 누르면 닫힌다 */}
      <button type="button" aria-label="메뉴 닫기" tabIndex={-1} onClick={onClose} className="absolute inset-0 bg-black/40" />
      <div className="pointer-events-none relative flex h-full w-full max-w-[393px]">
        <div
          ref={dialogRef}
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-label="메뉴"
          className="pointer-events-auto flex h-full w-[300px] max-w-[85%] flex-col gap-4 bg-white px-4 pt-5 pb-5 shadow-[4px_0_24px_0_rgb(0_0_0/0.15)] outline-none"
        >
          <div className="flex items-center justify-between">
            <p className="text-[16px]/[normal] font-bold">Synap</p>
            <button
              type="button"
              onClick={onClose}
              aria-label="메뉴 닫기"
              className="flex size-9 items-center justify-center rounded-full bg-surface-close text-[15px]/[normal]"
            >
              ✕
            </button>
          </div>

          <button
            ref={newChatRef}
            type="button"
            onClick={startNew}
            className="flex w-full items-center justify-center gap-1.5 rounded-button bg-primary py-3 text-[14px]/[normal] font-bold text-white"
          >
            <span aria-hidden>＋</span> 새 대화
          </button>

          <nav aria-label="지난 대화" className="-mx-1 flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto px-1">
            <h2 className="px-2 text-[12px]/[normal] font-bold text-muted">지난 대화</h2>
            {items === null ? null : items.length === 0 ? (
              <p className="px-2 py-2 text-[12px]/[1.5] text-muted">아직 나눈 대화가 없어요</p>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {items.map((item) => (
                  <li key={item.id}>
                    <Link
                      to={`/chat/${item.id}`}
                      onClick={goTo(`/chat/${item.id}`)}
                      aria-current={item.id === currentId ? 'page' : undefined}
                      className={`flex flex-col gap-0.5 rounded-xl px-2 py-2.5 ${
                        item.id === currentId ? 'bg-surface-muted' : ''
                      }`}
                    >
                      <span className="truncate text-[13px]/[16px]">{item.title ?? '제목 없는 대화'}</span>
                      <span className="text-[10.5px]/[13px] text-muted">
                        {formatDate(toLocalDate(item.updatedAt))}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </nav>

          <div className="border-t border-line pt-3">
            <Link
              to="/settings"
              onClick={goTo('/settings')}
              className="flex items-center gap-3 rounded-xl px-2 py-2.5 text-[13px]/[16px]"
            >
              <SettingsIcon size={20} />
              설정
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
