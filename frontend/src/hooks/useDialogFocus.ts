import { useEffect, type RefObject } from 'react'

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

// 모달·바닥 시트용 포커스 관리.
//  - 열리면 initialFocus(없으면 첫 포커스 가능 요소)로 포커스를 옮기고
//  - Tab / Shift+Tab 이 대화상자 밖으로 나가지 않게 가두며
//  - 닫히면 열기 전에 있던 요소로 포커스를 돌려준다.
export function useDialogFocus(
  container: RefObject<HTMLElement | null>,
  initialFocus?: RefObject<HTMLElement | null>,
) {
  useEffect(() => {
    const dialog = container.current
    if (!dialog) return

    const opener = document.activeElement as HTMLElement | null
    const items = () => Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE))

    ;(initialFocus?.current ?? items()[0] ?? dialog).focus()

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return
      const list = items()
      if (list.length === 0) {
        e.preventDefault()
        return
      }
      const first = list[0]
      const last = list[list.length - 1]
      const active = document.activeElement
      const outside = !dialog.contains(active)
      if (e.shiftKey && (active === first || outside)) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && (active === last || outside)) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      opener?.focus?.()
    }
    // 대화상자가 열려 있는 동안 한 번만 설정하면 된다.
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
