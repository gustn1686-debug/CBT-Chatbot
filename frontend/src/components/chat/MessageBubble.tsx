import type { FailReason } from '../../hooks/useChat'
import { Mascot } from '../Mascot'

type MessageBubbleProps = {
  role: 'user' | 'assistant'
  children: string
  failed?: boolean
  failReason?: FailReason
  onRetry?: () => void
}

// 전송 실패 안내 문구. 서버가 일부러 거절한 경우와 응답이 늦은 경우는 "실패"가 아니라 상황을 알려준다.
const FAILED_LABEL: Record<FailReason | 'default', string> = {
  busy: '지금 이용하는 분이 많아요 · 잠시 후 다시 시도',
  timeout: '응답이 늦어지고 있어요 · 다시 시도',
  default: '전송 실패 · 다시 시도',
}

const bubble = 'max-w-[248px] whitespace-pre-wrap break-words rounded-2xl px-3.5 py-2.5 text-[12.5px]/[normal]'

export function MessageBubble({ role, children, failed, failReason, onRetry }: MessageBubbleProps) {
  if (role === 'assistant') {
    return (
      <div className="flex items-end gap-1.5">
        <Mascot variant="face" width={26} height={26} className="shrink-0 overflow-hidden rounded-[13px]" />
        {children ? (
          <p className={`${bubble} bg-white shadow-card`}>{children}</p>
        ) : (
          <p className={`${bubble} bg-white shadow-card`} role="status" aria-label="답변을 작성하는 중">
            <span aria-hidden>•  •  •</span>
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col items-end gap-2.5">
      <p className={`${bubble} bg-bubble-user text-bubble-user-ink`}>{children}</p>
      {failed && (
        <button type="button" onClick={onRetry} className="-my-2 flex items-center gap-1.5 py-2 text-danger">
          <span className="flex size-[18px] items-center justify-center rounded-[9px] bg-danger text-[11px]/[normal] font-bold text-white">
            !
          </span>
          <span className="text-[11px]/[normal] font-bold">{FAILED_LABEL[failReason ?? 'default']}</span>
        </button>
      )}
    </div>
  )
}
