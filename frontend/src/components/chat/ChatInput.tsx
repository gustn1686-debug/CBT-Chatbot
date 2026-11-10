import { useState, type FormEvent } from 'react'

type ChatInputProps = {
  disabled?: boolean // 답변을 받는 중
  offline?: boolean // 인터넷 연결이 끊겨 보낼 수 없음 (Figma: EX_4_네트워크오류)
  onSend: (text: string) => void
}

export function ChatInput({ disabled, offline, onSend }: ChatInputProps) {
  const [text, setText] = useState('')
  const blocked = disabled || offline

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (blocked || !text.trim()) return
    onSend(text)
    setText('')
  }

  return (
    <form onSubmit={submit} aria-label="메시지 보내기" className="flex items-center gap-2 bg-white px-4 py-2.5">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={offline}
        placeholder={offline ? '연결 대기 중...' : '메시지를 입력하세요'}
        aria-label="메시지 입력"
        className={`min-w-0 flex-1 rounded-3xl px-4 py-3 text-[12.5px]/[normal] outline-none placeholder:text-placeholder focus-visible:ring-2 focus-visible:ring-primary/40 ${
          offline ? 'bg-field-disabled' : 'bg-white shadow-card'
        }`}
      />
      <button
        type="submit"
        aria-label="보내기"
        disabled={blocked || !text.trim()}
        className={`flex size-[42px] shrink-0 items-center justify-center rounded-[21px] text-[17px]/[normal] font-bold text-white ${
          offline ? 'bg-disabled' : 'bg-primary disabled:opacity-40'
        }`}
      >
        ↑
      </button>
    </form>
  )
}
