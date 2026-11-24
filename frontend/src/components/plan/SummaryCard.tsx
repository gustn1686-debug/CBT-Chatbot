import type { SummaryStatus } from '../../api/plans'

type SummaryCardProps = {
  heading: string
  meta?: string
  status: SummaryStatus
  summary: string | null
  onRetry?: () => void
  pendingText?: string
}

// 모델이 만든 요약 문장을 한 줄씩 나눠 보기 좋게 보여준다.
export function SummaryCard({
  heading,
  meta,
  status,
  summary,
  onRetry,
  pendingText = '오늘 나눈 이야기를 정리하고 있어요',
}: SummaryCardProps) {
  const lines = (summary ?? '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

  return (
    <section aria-label={heading} className="flex flex-col gap-3 rounded-hero bg-white p-5 shadow-card">
      <header className="flex items-baseline justify-between gap-2">
        <h2 className="text-[15px]/[normal] font-bold">{heading}</h2>
        {meta && <span className="shrink-0 text-[11px]/[normal] text-muted">{meta}</span>}
      </header>

      {status === 'done' && lines.length > 0 ? (
        <ul className="flex flex-col gap-2.5">
          {lines.map((line, i) => (
            <li key={i} className="flex gap-2.5 text-[13.5px]/[1.65]">
              <span aria-hidden className="mt-[9px] size-1.5 shrink-0 rounded-full bg-primary/70" />
              <span>{line}</span>
            </li>
          ))}
        </ul>
      ) : status === 'failed' ? (
        <div className="flex flex-col items-start gap-2.5">
          <p className="text-[13px]/[1.6] text-muted">요약을 만들지 못했어요. 잠시 후 다시 시도해 주세요.</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="rounded-full bg-tag-bg px-4 py-2 text-[12.5px]/[normal] font-bold text-primary-ink"
            >
              다시 정리하기
            </button>
          )}
        </div>
      ) : (
        <div role="status" className="flex flex-col gap-2.5">
          <p className="text-[12.5px]/[normal] text-muted">{pendingText}…</p>
          <div aria-hidden className="flex flex-col gap-2">
            <span className="h-3 w-[92%] animate-pulse rounded-full bg-surface-muted" />
            <span className="h-3 w-[78%] animate-pulse rounded-full bg-surface-muted" />
            <span className="h-3 w-[64%] animate-pulse rounded-full bg-surface-muted" />
          </div>
        </div>
      )}
    </section>
  )
}
