import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GUEST_SESSION_LIMIT, startGuest } from '../api/auth'
import { Mascot } from '../components/Mascot'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

// Figma: AUTH_1_시작선택
export function Start() {
  useDocumentTitle('시작하기')
  const navigate = useNavigate()
  const [starting, setStarting] = useState(false)

  const continueAsGuest = async () => {
    setStarting(true)
    try {
      await startGuest()
      navigate('/', { replace: true })
    } finally {
      setStarting(false)
    }
  }

  return (
    <main className="flex min-h-dvh flex-col">
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-7 py-5">
        <Mascot variant="waving" width={170} height={208} />
        <h1 className="text-center text-[22px]/[normal] font-bold">Synap과 함께 시작해요</h1>
        <p className="text-center text-[13px]/[1.5] text-muted">
          가입하면 나눈 대화를 안전하게 보관하고
          <br />
          어느 기기에서든 이어서 이야기할 수 있어요.
        </p>
      </div>

      <div className="flex flex-col items-center gap-2.5 px-7 pt-2 pb-4">
        <Link
          to="/signup"
          className="flex w-full items-center justify-center rounded-button bg-primary p-4 text-[15px]/[normal] font-bold text-white"
        >
          이메일로 가입하기
        </Link>
        <Link
          to="/login"
          className="flex w-full items-center justify-center rounded-button border border-line bg-white p-4 text-[15px]/[normal] font-bold"
        >
          로그인
        </Link>
        <div className="flex flex-col items-center gap-1 pt-2.5 pb-1">
          <button
            type="button"
            onClick={continueAsGuest}
            disabled={starting}
            className="-my-2 py-2 text-[13px]/[normal] font-medium text-muted underline disabled:opacity-60"
          >
            비회원으로 먼저 써볼게요
          </button>
          <p className="text-[11px]/[normal] text-placeholder">
            비회원은 대화 {GUEST_SESSION_LIMIT}회까지 자유롭게 이용할 수 있어요
          </p>
        </div>
      </div>
    </main>
  )
}
