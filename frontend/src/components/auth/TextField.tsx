import { useId, useState, type ReactNode } from 'react'

type TextFieldProps = {
  label: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'email' | 'password'
  placeholder?: string
  autoComplete?: string
  helper?: string
  helperTone?: 'default' | 'primary'
  error?: string
  trailing?: ReactNode
}

// Figma: Field/이메일·비밀번호·닉네임 — 회색 입력칸, 포커스되면 primary 테두리
export function TextField({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  autoComplete,
  helper,
  helperTone = 'default',
  error,
  trailing,
}: TextFieldProps) {
  const id = useId()
  const noteId = `${id}-note`
  const note = error ?? helper

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[12.5px]/[normal] font-medium">
        {label}
      </label>
      <div
        className={`flex items-center gap-2 rounded-xl border-[1.5px] bg-field px-4 focus-within:bg-white ${
          error ? 'border-danger' : 'border-transparent focus-within:border-primary'
        }`}
      >
        <input
          id={id}
          type={type}
          value={value}
          placeholder={placeholder}
          autoComplete={autoComplete}
          aria-invalid={error ? true : undefined}
          aria-describedby={note ? noteId : undefined}
          onChange={(e) => onChange(e.target.value)}
          className="min-w-0 flex-1 bg-transparent py-3.5 text-[13.5px]/[normal] outline-none placeholder:text-placeholder"
        />
        {trailing}
      </div>
      {note && (
        <p
          id={noteId}
          role={error ? 'alert' : undefined}
          className={`text-[11px]/[normal] ${
            error ? 'text-danger' : helperTone === 'primary' ? 'text-primary' : 'text-placeholder'
          }`}
        >
          {note}
        </p>
      )}
    </div>
  )
}

type PasswordFieldProps = Omit<TextFieldProps, 'type' | 'trailing'>

// 오른쪽 "보기"로 비밀번호를 잠깐 확인할 수 있다.
export function PasswordField(props: PasswordFieldProps) {
  const [shown, setShown] = useState(false)
  return (
    <TextField
      {...props}
      type={shown ? 'text' : 'password'}
      trailing={
        <button
          type="button"
          aria-pressed={shown}
          aria-label={shown ? '비밀번호 숨기기' : '비밀번호 보기'}
          onClick={() => setShown(!shown)}
          className="-m-3 shrink-0 p-3 text-[12px]/[normal] font-medium text-muted"
        >
          {shown ? '숨기기' : '보기'}
        </button>
      }
    />
  )
}
