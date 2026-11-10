import type { ReactNode } from 'react'

// 모바일 우선: Figma 기준 폭(393px)을 최대로 하고 데스크톱에서는 가운데 정렬한다.
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[393px] flex-col bg-white">{children}</div>
  )
}
