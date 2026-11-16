import { Link } from 'react-router-dom'
import { SettingsButton } from '../SettingsButton'

type ChatHeaderProps = {
  isGuest: boolean
  online: boolean
  onMenu: () => void
}

// ChatGPT 앱과 같은 구조: 왼쪽 메뉴(지난 대화 목록) · 가운데 제목 · 오른쪽 로그인(비회원) / 설정(회원)
export function ChatHeader({ isGuest, online, onMenu }: ChatHeaderProps) {
  return (
    <header className={`flex items-center justify-between px-4 pb-2 ${online ? 'pt-4' : 'pt-1.5'}`}>
      <button
        type="button"
        onClick={onMenu}
        aria-label="메뉴 열기"
        aria-haspopup="dialog"
        className="flex size-11 items-center justify-center rounded-full bg-white shadow-card"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
          <path d="M3 7h14M3 13h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>

      <h1 className="text-[16px]/[normal] font-bold">Synap</h1>

      {isGuest ? (
        <Link to="/login" className="rounded-full bg-primary px-4 py-2.5 text-[13px]/[normal] font-bold text-white">
          로그인
        </Link>
      ) : (
        <SettingsButton />
      )}
    </header>
  )
}
