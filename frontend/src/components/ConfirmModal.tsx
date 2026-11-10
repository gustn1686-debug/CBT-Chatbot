import { useEffect, useId, useRef } from 'react'
import { useDialogFocus } from '../hooks/useDialogFocus'

type ConfirmModalProps = {
  title: string
  description: string
  cancelLabel?: string
  confirmLabel: string
  tone?: 'primary' | 'danger' // 삭제처럼 되돌릴 수 없는 동작은 danger
  onCancel: () => void
  onConfirm: () => void
}

// Figma: EX_1_대화종료_확인모달 (삭제·동의철회 모달도 같은 형태로 재사용)
// 포커스는 "취소"에서 시작한다. 실수로 Enter 를 눌러도 되돌릴 수 없는 동작이 실행되지 않게 하려는 것.
export function ConfirmModal({
  title,
  description,
  cancelLabel = '취소',
  confirmLabel,
  tone = 'primary',
  onCancel,
  onConfirm,
}: ConfirmModalProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)
  useDialogFocus(dialogRef, cancelRef)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onCancel()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="flex w-80 max-w-full flex-col items-center gap-3.5 rounded-hero bg-white px-5 pt-[22px] pb-5 shadow-[0_8px_24px_0_rgb(0_0_0/0.2)] outline-none"
      >
        <h2 id={titleId} className="text-center text-[16px]/[normal] font-bold">
          {title}
        </h2>
        <p className="text-center text-[12px]/[1.5] whitespace-pre-line text-muted">{description}</p>
        <div className="flex w-full gap-2.5">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-xl bg-surface-muted py-3 text-[13px]/[normal] font-bold"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={`flex-1 rounded-xl py-3 text-[13px]/[normal] font-bold text-white ${
              tone === 'danger' ? 'bg-danger' : 'bg-primary'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
