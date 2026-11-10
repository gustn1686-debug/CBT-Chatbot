import { useEffect, useRef } from 'react'
import type { CrisisResource } from '../../api/chat'
import { useDialogFocus } from '../../hooks/useDialogFocus'
import { telHref } from '../../lib/crisis'
import { Mascot } from '../Mascot'

type CrisisSheetProps = {
  resources: CrisisResource[]
  onCall: (resource: CrisisResource) => void
  onClose: () => void
}

// Figma: HiFi_6_위기대응 / DEMO_위기감지_2_시트표시
export function CrisisSheet({ resources, onCall, onClose }: CrisisSheetProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const firstCall = useRef<HTMLAnchorElement>(null)
  useDialogFocus(dialogRef, firstCall)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/45">
      <div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="crisis-title"
        className="flex max-h-[92dvh] w-full max-w-[393px] flex-col items-center gap-3.5 overflow-y-auto rounded-t-3xl bg-white px-5 pt-3.5 pb-5 shadow-[0_-4px_20px_0_rgb(0_0_0/0.18)] outline-none"
      >
        <div className="flex w-full justify-end">
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="relative flex size-[30px] items-center justify-center rounded-[15px] bg-surface-close text-[13px]/[normal] text-muted after:absolute after:-inset-[7px] after:content-['']"
          >
            ✕
          </button>
        </div>

        <Mascot variant="thinking" width={56} height={56} className="overflow-hidden rounded-[28px]" />
        <h2 id="crisis-title" className="text-center text-[17px]/[normal] font-bold">
          지금 많이 힘드신 것 같아요
        </h2>
        <p className="text-center text-[11.5px]/[normal] text-muted">혼자 견디기 어려운 순간일 수 있어요</p>

        <p className="w-full rounded-card bg-surface-tint p-3 text-[11.5px]/[normal] text-muted">
          저는 이 상황에서 전문적인 도움을 드리기 어려워요. 지금은 아래 전문기관과 연결되는 게 더 안전해요.
        </p>

        <ul className="flex w-full flex-col gap-2.5">
          {resources.map((resource, i) => (
            <li
              key={resource.tel}
              className="flex flex-col items-center gap-1.5 rounded-xl bg-surface-tint p-3.5"
            >
              <p className="text-[12.5px]/[normal] font-bold">{resource.name}</p>
              <p className="text-[16px]/[normal] font-bold text-primary">{resource.tel}</p>
              <a
                ref={i === 0 ? firstCall : undefined}
                href={telHref(resource.tel)}
                onClick={() => onCall(resource)}
                className="flex w-full items-center justify-center gap-1.5 rounded-[9px] bg-primary py-2.5 text-[12px]/[normal] text-white"
              >
                <span aria-hidden>☎</span>
                <span className="font-bold">바로 전화하기</span>
                <span className="sr-only">{resource.name}</span>
              </a>
            </li>
          ))}
        </ul>

        <button
          type="button"
          onClick={onClose}
          className="w-full rounded-xl border-[1.5px] border-line bg-white py-[13px] text-[13px]/[normal] font-bold"
        >
          일반 대화로 돌아가기
        </button>
      </div>
    </div>
  )
}
