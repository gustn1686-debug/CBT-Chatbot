import { useEffect, useRef } from 'react'
import { useDialogFocus } from '../../hooks/useDialogFocus'
import { Mascot } from '../Mascot'

type GuestSignupSheetProps = {
  limit: number
  onJoin: () => void
  onLater: () => void
}

const BENEFITS = [
  '대화 기록을 안전하게 보관해요',
  '지난 대화를 이어서 이야기할 수 있어요',
  '기기를 바꿔도 기록이 그대로 남아요',
]

// Figma: GUEST_2_가입유도_대화시작시 — 무료 대화를 모두 쓴 비회원이 새 대화를 시작하려 할 때
// "다음에 할게요"로 계속 이용할 수 있다. (API 명세 §4: 한도를 넘어도 막지 않고 안내만 한다 — 합의 전)
export function GuestSignupSheet({ limit, onJoin, onLater }: GuestSignupSheetProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const joinRef = useRef<HTMLButtonElement>(null)
  useDialogFocus(dialogRef, joinRef)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onLater()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onLater])

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40">
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="guest-sheet-title"
        className="flex max-h-[92dvh] w-full max-w-[393px] flex-col items-center gap-3.5 overflow-y-auto rounded-t-3xl bg-white px-6 pt-2.5 pb-4 shadow-[0_-4px_20px_0_rgb(0_0_0/0.12)] outline-none"
      >
        <span aria-hidden className="h-1 w-10 rounded-sm bg-line" />
        <Mascot variant="thinking" width={120} height={120} />
        <div className="flex flex-col gap-2 text-center">
          <h2 id="guest-sheet-title" className="text-[19px]/[normal] font-bold">
            벌써 {limit}번의 대화를 함께했어요
          </h2>
          <p className="text-[13px]/[1.5] text-muted">
            가입하면 지금까지 나눈 대화를 그대로 옮겨서
            <br />
            언제든 이어서 이야기할 수 있어요.
          </p>
        </div>

        <ul className="flex w-full flex-col gap-2.5 rounded-xl bg-guest-bg px-4 py-3.5">
          {BENEFITS.map((benefit) => (
            <li key={benefit} className="flex items-center gap-2 text-[12.5px]/[normal] text-bubble-user-ink">
              <span aria-hidden className="text-[13px]/[normal] font-bold text-primary">
                ✓
              </span>
              {benefit}
            </li>
          ))}
        </ul>

        <button
          ref={joinRef}
          type="button"
          onClick={onJoin}
          className="w-full rounded-button bg-primary p-4 text-[15px]/[normal] font-bold text-white"
        >
          가입하고 계속하기
        </button>
        <button
          type="button"
          onClick={onLater}
          className="py-2 text-[13px]/[normal] font-medium text-muted underline"
        >
          다음에 할게요
        </button>
      </div>
    </div>
  )
}
