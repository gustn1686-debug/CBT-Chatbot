import { useEffect, useRef } from 'react'
import type { CrisisResource } from '../../api/chat'
import { useDialogFocus } from '../../hooks/useDialogFocus'
import { telHref } from '../../lib/crisis'

// 전화 앱으로 넘어가지 않은 채 이 시간이 지나면 연결 실패로 본다. (웹은 통화 성공 여부를 알 수 없다)
export const CALL_TIMEOUT_MS = 8000

type CallingProps = {
  resource: CrisisResource
  onFail: () => void
  onEnd: () => void
}

const frame = 'fixed inset-0 z-50 flex justify-center bg-call-bg text-white'
const column = 'flex w-full max-w-[393px] flex-col'

// Figma: DEMO_위기감지_3_전화연결중
export function CallingScreen({ resource, onFail, onEnd }: CallingProps) {
  // 부모가 다시 그려져도 타이머가 처음부터 다시 시작되지 않도록 최신 콜백만 ref로 들고 있는다.
  const failRef = useRef(onFail)
  useEffect(() => {
    failRef.current = onFail
  })

  const dialogRef = useRef<HTMLDivElement>(null)
  const endRef = useRef<HTMLButtonElement>(null)
  useDialogFocus(dialogRef, endRef)

  useEffect(() => {
    // 전화 앱이 열리면 페이지가 가려지거나 포커스를 잃는다 → 연결 시도가 넘어간 것으로 본다.
    const timer = window.setTimeout(() => failRef.current(), CALL_TIMEOUT_MS)
    const handedOff = () => window.clearTimeout(timer)
    const onVisibility = () => document.hidden && handedOff()

    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('pagehide', handedOff)
    window.addEventListener('blur', handedOff)
    return () => {
      window.clearTimeout(timer)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('pagehide', handedOff)
      window.removeEventListener('blur', handedOff)
    }
  }, [])

  return (
    <div ref={dialogRef} tabIndex={-1} className={`${frame} outline-none`} role="dialog" aria-modal="true" aria-label="전화 연결 중">
      <div className={column}>
        <div className="flex flex-1 flex-col items-center justify-center gap-3 pt-10 pb-5">
          <p className="text-[14px]/[normal] text-call-sub" role="status">
            발신 중...
          </p>
          <p className="text-[22px]/[normal] font-bold">{resource.name}</p>
          <p className="text-[15px]/[normal] text-call-sub">{resource.tel}</p>
          <div className="pt-[30px] pb-5">
            <div className="flex size-[140px] items-center justify-center rounded-[70px] bg-call-ring text-[52px]/[normal]" aria-hidden>
              ☎
            </div>
          </div>
        </div>

        {/* 실제 통화 제어는 전화 앱에서 하므로 장식으로만 둔다 */}
        <div className="flex justify-center gap-[26px] pb-[30px]" aria-hidden>
          {[
            ['🔇', '음소거'],
            ['⌨', '키패드'],
            ['🔊', '스피커'],
          ].map(([icon, label]) => (
            <div key={label} className="flex flex-col items-center gap-2">
              <div className="flex size-16 items-center justify-center rounded-[32px] bg-white/14 text-[22px]/[normal]">
                {icon}
              </div>
              <span className="text-[10.5px]/[normal] text-call-label">{label}</span>
            </div>
          ))}
        </div>

        <div className="flex justify-center pb-[50px]">
          <button
            ref={endRef}
            type="button"
            onClick={onEnd}
            aria-label="통화 종료"
            className="flex size-[72px] items-center justify-center rounded-[36px] bg-call-end text-[26px]/[normal]"
          >
            📞
          </button>
        </div>
      </div>
    </div>
  )
}

type CallFailedProps = {
  resource: CrisisResource
  onRetry: () => void
  onClose: () => void
}

// Figma: EX_6_전화연결실패
export function CallFailedScreen({ resource, onRetry, onClose }: CallFailedProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const retryRef = useRef<HTMLAnchorElement>(null)
  useDialogFocus(dialogRef, retryRef)

  return (
    <div ref={dialogRef} tabIndex={-1} className={`${frame} outline-none`} role="alertdialog" aria-modal="true" aria-label="전화 연결 실패">
      <div className={column}>
        <div className="flex flex-1 flex-col items-center justify-center gap-3 pt-10 pb-5">
          <p className="text-[14px]/[normal] text-call-fail-text">연결할 수 없어요</p>
          <p className="text-[22px]/[normal] font-bold">{resource.name}</p>
          <p className="text-[15px]/[normal] text-call-sub">{resource.tel}</p>
          <p className="text-[12px]/[normal] text-call-hint">잠시 후 다시 시도해주세요</p>
          <div className="pt-[30px] pb-5">
            <div className="flex size-[140px] items-center justify-center rounded-[70px] bg-call-fail-ring text-[44px]/[normal]" aria-hidden>
              ✕
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3 px-7 pb-[50px]">
          <a
            ref={retryRef}
            href={telHref(resource.tel)}
            onClick={onRetry}
            className="flex items-center justify-center rounded-button bg-primary py-[15px] text-[14px]/[normal] font-bold"
          >
            다시 걸기
          </a>
          <button
            type="button"
            onClick={onClose}
            className="rounded-button bg-white/10 py-[15px] text-[14px]/[normal] font-bold text-call-label"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  )
}
