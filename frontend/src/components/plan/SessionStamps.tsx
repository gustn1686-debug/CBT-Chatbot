type SessionStampsProps = {
  total: number
  completed: number
  // 방금 마친 회기 번호. 그 도장만 찍히는 움직임을 준다.
  justStamped?: number
  size?: 'md' | 'lg'
}

// 회기 진행을 도장처럼 보여준다. 마친 회기는 체크 도장, 다음 회기는 점선, 남은 회기는 번호만.
export function SessionStamps({ total, completed, justStamped, size = 'md' }: SessionStampsProps) {
  const box = size === 'lg' ? 'size-12 text-[15px]' : 'size-10 text-[13px]'
  const check = size === 'lg' ? 22 : 18
  return (
    <ol aria-label={`${total}회 중 ${completed}회 마침`} className="flex flex-wrap justify-center gap-2.5">
      {Array.from({ length: total }, (_, i) => {
        const no = i + 1
        const done = no <= completed
        const next = no === completed + 1
        return (
          <li
            key={no}
            aria-label={`${no}회기 ${done ? '마침' : next ? '다음 차례' : '예정'}`}
            className={`flex ${box} items-center justify-center rounded-full font-bold ${
              done
                ? `bg-primary text-white shadow-[0_2px_6px_0_rgb(81_112_184/0.35)] ${
                    no === justStamped ? 'animate-stamp' : no % 2 ? '-rotate-6' : 'rotate-3'
                  }`
                : next
                  ? 'border-2 border-dashed border-primary/60 text-primary'
                  : 'bg-surface-muted text-muted'
            }`}
          >
            {done ? (
              <svg width={check} height={check} viewBox="0 0 20 20" fill="none" aria-hidden>
                <path d="M4.5 10.5l3.5 3.5 7.5-8" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
              no
            )}
          </li>
        )
      })}
    </ol>
  )
}
