import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login, startGuest } from '../api/auth'
import { ApiError } from '../api/client'
import { PasswordField, TextField } from '../components/auth/TextField'
import { Checkbox } from '../components/Checkbox'
import { isEmail } from '../lib/validation'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

// Figma: AUTH_2_로그인
export function Login() {
  useDocumentTitle('로그인')
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [error, setError] = useState<string>()
  const [submitting, setSubmitting] = useState(false)

  const canSubmit = isEmail(email.trim()) && password.length > 0 && !submitting

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setSubmitting(true)
    setError(undefined)
    try {
      await login({ email: email.trim(), password, remember })
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '로그인하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setSubmitting(false)
    }
  }

  const continueAsGuest = async () => {
    await startGuest()
    navigate('/', { replace: true })
  }

  return (
    <main className="flex min-h-dvh flex-col">
      <header className="flex items-center justify-between px-4 pt-5 pb-2.5">
        <Link to="/start" aria-label="뒤로" className="-m-3 p-3 text-[20px]/[normal]">
          ‹
        </Link>
        <h1 className="text-[14px]/[normal] font-bold">로그인</h1>
        <span className="w-[7px]" aria-hidden />
      </header>

      <form onSubmit={submit} className="flex flex-1 flex-col gap-[18px] px-7 py-5">
        <div className="flex flex-col gap-1.5">
          <h2 className="text-[22px]/[normal] font-bold">다시 만나서 반가워요</h2>
          <p className="text-[13px]/[normal] text-muted">지난 대화를 이어서 이야기해볼까요?</p>
        </div>

        <div className="flex flex-col gap-[18px] pt-1.5">
          <TextField
            label="이메일"
            type="email"
            autoComplete="email"
            value={email}
            onChange={setEmail}
            placeholder="이메일을 입력해주세요"
          />
          <PasswordField
            label="비밀번호"
            autoComplete="current-password"
            value={password}
            onChange={setPassword}
            placeholder="비밀번호를 입력해주세요"
            error={error}
          />
        </div>

        <Checkbox checked={remember} onChange={setRemember} className="gap-2">
          <span className="text-[12.5px]/[normal]">로그인 상태 유지</span>
        </Checkbox>

        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-button bg-primary p-4 text-[15px]/[normal] font-bold text-white disabled:opacity-40"
        >
          로그인
        </button>

        <div className="flex items-center justify-center gap-3">
          {/* 비밀번호 찾기 화면은 아직 디자인이 없다 */}
          <button type="button" disabled className="text-[12px]/[normal] text-muted">
            비밀번호 찾기
          </button>
          <span aria-hidden className="text-[11px]/[normal] text-line">
            |
          </span>
          <Link to="/signup" className="-my-2 py-2 text-[12px]/[normal] font-bold text-primary">
            회원가입
          </Link>
        </div>
      </form>

      <div className="flex flex-col items-center gap-2 px-7 pt-2 pb-5">
        <button
          type="button"
          onClick={continueAsGuest}
          className="-my-2 py-2 text-[13px]/[normal] font-medium text-muted underline"
        >
          비회원으로 계속하기
        </button>
      </div>
    </main>
  )
}
