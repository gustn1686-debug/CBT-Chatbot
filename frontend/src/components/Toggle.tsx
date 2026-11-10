import type { ReactNode } from 'react'
import toggleOff from '../assets/toggle-off.svg'
import toggleOn from '../assets/toggle-on.svg'

type ToggleProps = {
  checked: boolean
  onChange: (checked: boolean) => void
  children: ReactNode // 눈에 보이는 라벨 (접근성 이름도 된다)
  iconPosition?: 'start' | 'end'
  className?: string
}

// Figma 토글 에셋(40×22, 켜짐/꺼짐) + 라벨을 하나의 스위치 버튼으로 묶는다.
export function Toggle({ checked, onChange, children, iconPosition = 'end', className = '' }: ToggleProps) {
  const icon = <img src={checked ? toggleOn : toggleOff} alt="" width={40} height={22} className="shrink-0" />

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`flex items-center ${className}`}
    >
      {iconPosition === 'start' && icon}
      {children}
      {iconPosition === 'end' && icon}
    </button>
  )
}
