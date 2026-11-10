import type { ReactNode } from 'react'

type CheckboxProps = {
  checked: boolean
  onChange: (checked: boolean) => void
  children: ReactNode
  className?: string
}

// Figma 체크박스: 18px, 체크되면 primary 배경에 흰 ✓
export function Checkbox({ checked, onChange, children, className = '' }: CheckboxProps) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`-my-1.5 flex items-center gap-2.5 py-1.5 text-left ${className}`}
    >
      <span
        aria-hidden
        className={`flex size-[18px] shrink-0 items-center justify-center rounded-[5px] text-[11px]/[normal] font-bold text-white ${
          checked ? 'bg-primary' : 'border border-line bg-white'
        }`}
      >
        {checked && '✓'}
      </span>
      {children}
    </button>
  )
}
