import { useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'

type ChatInputProps = {
  disabled?: boolean // 답변을 받는 중
  offline?: boolean // 인터넷 연결이 끊겨 보낼 수 없음 (Figma: EX_4_네트워크오류)
  onSend: (text: string) => void
}

// 서버가 받는 메시지 길이 상한(backend 의 SendMessage.content max_length)과 맞춘다.
const MAX_LENGTH = 4000
// 입력칸이 늘어나는 최대 높이(약 5줄). 더 길어지면 칸 안에서 스크롤된다.
const MAX_HEIGHT = 120

// 모바일(터치) 키보드에서는 Enter 가 줄바꿈이고, 보내기는 버튼으로 한다. (ChatGPT 앱과 같은 방식)
const isTouchDevice = () => typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches

export function ChatInput({ disabled, offline, onSend }: ChatInputProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const blocked = disabled || offline

  // 글이 길어지면 다음 줄로 넘어가며 입력칸이 함께 커진다. (한 줄짜리 input 은 옆으로만 밀려서 못 쓴다)
  useLayoutEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    if (el.scrollHeight > 0) el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`
    el.style.overflowY = el.scrollHeight > MAX_HEIGHT ? 'auto' : 'hidden'
  }, [text])

  const send = () => {
    if (blocked || !text.trim()) return
    onSend(text)
    setText('')
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    send()
  }

  // 컴퓨터: Enter 로 보내고 Shift+Enter 로 줄바꿈. 한글 입력 중(글자 조합 중)의 Enter 는 보내지 않는다.
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== 'Enter' || e.shiftKey) return
    if (e.nativeEvent.isComposing || e.keyCode === 229) return
    if (isTouchDevice()) return
    e.preventDefault()
    send()
  }

  return (
    <form onSubmit={submit} aria-label="메시지 보내기" className="flex items-end gap-2 bg-white px-4 py-2.5">
      <textarea
        ref={textareaRef}
        rows={1}
        value={text}
        maxLength={MAX_LENGTH}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={offline}
        placeholder={offline ? '연결 대기 중...' : '메시지를 입력하세요'}
        aria-label="메시지 입력"
        className={`block min-h-[42px] min-w-0 flex-1 resize-none rounded-[22px] px-4 py-[11px] text-[12.5px]/[20px] outline-none placeholder:text-placeholder focus-visible:ring-2 focus-visible:ring-primary/40 ${
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
