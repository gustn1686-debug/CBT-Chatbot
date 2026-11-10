import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { signUp } from '../api/auth'
import { ApiError } from '../api/client'
import { PasswordField, TextField } from '../components/auth/TextField'
import { Checkbox } from '../components/Checkbox'
import { isEmail, isValidPassword, NICKNAME_MAX } from '../lib/validation'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

const TERMS = [
  { key: 'age', label: '(필수) 만 19세 이상입니다', hasDocument: false },
  { key: 'tos', label: '(필수) 서비스 이용약관 동의', hasDocument: true },
  { key: 'privacy', label: '(필수) 개인정보 수집 및 이용 동의', hasDocument: true },
  { key: 'sensitive', label: '(필수) 상담 내용(민감정보) 처리 동의', hasDocument: true },
] as const

type TermKey = (typeof TERMS)[number]['key']
type Agreed = Record<TermKey, boolean>

const NONE: Agreed = { age: false, tos: false, privacy: false, sensitive: false }
const ALL: Agreed = { age: true, tos: true, privacy: true, sensitive: true }

// Figma: AUTH_3_회원가입
export function Signup() {
  useDocumentTitle('회원가입')
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [nickname, setNickname] = useState('')
  const [agreed, setAgreed] = useState<Agreed>(NONE)
  const [emailError, setEmailError] = useState<string>()
  const [formError, setFormError] = useState<string>()
  const [submitting, setSubmitting] = useState(false)

  const emailOk = isEmail(email.trim())
  const confirmMismatch = confirm.length > 0 && confirm !== password
  const allAgreed = TERMS.every(({ key }) => agreed[key])
  const canSubmit =
    emailOk &&
    isValidPassword(password) &&
    confirm === password &&
    nickname.trim().length > 0 &&
    allAgreed &&
    !submitting

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setSubmitting(true)
    setEmailError(undefined)
    setFormError(undefined)
    try {
      await signUp({ email: email.trim(), password, nickname: nickname.trim() })
      navigate('/', { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.code === 'email_taken') setEmailError(err.message)
      else setFormError('가입하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-dvh">
      <form onSubmit={submit} className="flex min-h-dvh flex-col">
        <header className="flex items-center justify-between px-4 pt-5 pb-2.5">
          <Link to="/start" aria-label="뒤로" className="-m-3 p-3 text-[20px]/[normal]">
            ‹
          </Link>
          <h1 className="text-[14px]/[normal] font-bold">회원가입</h1>
          <span className="w-[7px]" aria-hidden />
        </header>

        <div className="flex flex-1 flex-col gap-3.5 px-7 py-3">
          <h2 className="text-[20px]/[normal] font-bold">몇 가지만 알려주세요</h2>

          <TextField
            label="이메일"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(value) => {
              setEmail(value)
              setEmailError(undefined)
            }}
            placeholder="이메일을 입력해주세요"
            error={emailError}
            trailing={
              emailOk && (
                <span aria-hidden className="shrink-0 text-[12px]/[normal] font-bold text-primary">
                  ✓
                </span>
              )
            }
          />
          <PasswordField
            label="비밀번호"
            autoComplete="new-password"
            value={password}
            onChange={setPassword}
            helper="영문, 숫자 포함 8자 이상"
            helperTone="primary"
          />
          <PasswordField
            label="비밀번호 확인"
            autoComplete="new-password"
            value={confirm}
            onChange={setConfirm}
            placeholder="비밀번호를 한 번 더 입력해주세요"
            error={confirmMismatch ? '비밀번호가 일치하지 않아요' : undefined}
          />
          <TextField
            label="닉네임"
            autoComplete="nickname"
            value={nickname}
            onChange={(value) => setNickname(value.slice(0, NICKNAME_MAX))}
            placeholder="상담 중 불릴 이름"
            helper="대화할 때 이 이름으로 불러드려요"
          />

          <fieldset className="flex flex-col gap-2.5 rounded-xl border border-line p-3.5">
            <legend className="sr-only">약관 동의</legend>
            <Checkbox checked={allAgreed} onChange={(on) => setAgreed(on ? ALL : NONE)}>
              <span className="text-[13.5px]/[normal] font-bold">전체 동의하기</span>
            </Checkbox>
            <div className="h-px bg-line" />
            {TERMS.map(({ key, label, hasDocument }) => (
              <div key={key} className="flex items-center gap-2.5">
                <Checkbox
                  className="flex-1"
                  checked={agreed[key]}
                  onChange={(on) => setAgreed({ ...agreed, [key]: on })}
                >
                  <span className="text-[12px]/[normal]">{label}</span>
                </Checkbox>
                {/* 약관 전문 화면은 아직 없다 */}
                {hasDocument && (
                  <button type="button" disabled className="text-[11px]/[normal] text-placeholder">
                    보기
                  </button>
                )}
              </div>
            ))}
          </fieldset>
        </div>

        <div className="flex flex-col gap-2 px-7 pt-2 pb-5">
          {formError && (
            <p role="alert" className="text-center text-[11px]/[normal] text-danger">
              {formError}
            </p>
          )}
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-button bg-primary p-4 text-[15px]/[normal] font-bold text-white disabled:opacity-40"
          >
            가입하기
          </button>
        </div>
      </form>
    </main>
  )
}
