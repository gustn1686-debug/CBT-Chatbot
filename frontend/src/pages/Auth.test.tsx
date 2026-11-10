import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TAKEN_EMAIL, WRONG_PASSWORD } from '../api/mockAuth'
import { getSession } from '../lib/session'
import { Login } from './Login'
import { Signup } from './Signup'
import { Start } from './Start'

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/start" element={<Start />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/" element={<p>홈 화면</p>} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
})

describe('Start', () => {
  it('가입·로그인·비회원 세 갈래를 보여준다', () => {
    renderAt('/start')
    expect(screen.getByRole('link', { name: '이메일로 가입하기' })).toHaveAttribute('href', '/signup')
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
    expect(screen.getByText('비회원은 대화 3회까지 자유롭게 이용할 수 있어요')).toBeInTheDocument()
  })

  it('비회원으로 시작하면 비회원 세션이 생기고 홈으로 간다', async () => {
    const user = renderAt('/start')
    await user.click(screen.getByRole('button', { name: '비회원으로 먼저 써볼게요' }))
    expect(await screen.findByText('홈 화면')).toBeInTheDocument()
    expect(getSession()).toEqual({ kind: 'guest' })
  })
})

describe('Login', () => {
  const fill = async (user: ReturnType<typeof userEvent.setup>, email: string, password: string) => {
    await user.type(screen.getByLabelText('이메일'), email)
    await user.type(screen.getByLabelText('비밀번호'), password)
  }

  it('이메일 형식과 비밀번호가 채워져야 로그인할 수 있다', async () => {
    const user = renderAt('/login')
    const submit = screen.getByRole('button', { name: '로그인' })
    expect(submit).toBeDisabled()
    await fill(user, 'not-an-email', 'password1')
    expect(submit).toBeDisabled()
    await user.clear(screen.getByLabelText('이메일'))
    await user.type(screen.getByLabelText('이메일'), 'synap@ajou.ac.kr')
    expect(submit).toBeEnabled()
  })

  it('로그인하면 회원 세션이 저장되고 홈으로 간다', async () => {
    const user = renderAt('/login')
    await fill(user, 'synap@ajou.ac.kr', 'password1')
    await user.click(screen.getByRole('button', { name: '로그인' }))

    expect(await screen.findByText('홈 화면')).toBeInTheDocument()
    expect(getSession()).toEqual({ kind: 'user', email: 'synap@ajou.ac.kr', nickname: 'synap' })
    expect(localStorage.getItem('synap.session')).not.toBeNull()
  })

  it('"로그인 상태 유지"를 끄면 탭을 닫을 때 사라지는 곳에만 저장한다', async () => {
    const user = renderAt('/login')
    await fill(user, 'synap@ajou.ac.kr', 'password1')
    await user.click(screen.getByRole('checkbox', { name: '로그인 상태 유지' }))
    await user.click(screen.getByRole('button', { name: '로그인' }))

    await screen.findByText('홈 화면')
    expect(localStorage.getItem('synap.session')).toBeNull()
    expect(sessionStorage.getItem('synap.session')).not.toBeNull()
  })

  it('비밀번호가 틀리면 오류를 보여주고 세션을 만들지 않는다', async () => {
    const user = renderAt('/login')
    await fill(user, 'synap@ajou.ac.kr', WRONG_PASSWORD)
    await user.click(screen.getByRole('button', { name: '로그인' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('이메일 또는 비밀번호가 맞지 않아요.')
    expect(getSession()).toBeNull()
  })

  it('"보기"로 비밀번호를 확인할 수 있다', async () => {
    const user = renderAt('/login')
    expect(screen.getByLabelText('비밀번호')).toHaveAttribute('type', 'password')
    await user.click(screen.getByRole('button', { name: '비밀번호 보기' }))
    expect(screen.getByLabelText('비밀번호')).toHaveAttribute('type', 'text')
  })

  it('비회원으로 계속할 수 있다', async () => {
    const user = renderAt('/login')
    await user.click(screen.getByRole('button', { name: '비회원으로 계속하기' }))
    expect(await screen.findByText('홈 화면')).toBeInTheDocument()
    expect(getSession()).toEqual({ kind: 'guest' })
  })
})

describe('Signup', () => {
  const fillValid = async (user: ReturnType<typeof userEvent.setup>, email = 'synap@ajou.ac.kr') => {
    await user.type(screen.getByLabelText('이메일'), email)
    await user.type(screen.getByLabelText('비밀번호'), 'password1')
    await user.type(screen.getByLabelText('비밀번호 확인'), 'password1')
    await user.type(screen.getByLabelText('닉네임'), '지예')
  }

  it('모든 항목을 채우고 약관에 모두 동의해야 가입할 수 있다', async () => {
    const user = renderAt('/signup')
    const submit = screen.getByRole('button', { name: '가입하기' })
    expect(submit).toBeDisabled()

    await fillValid(user)
    expect(submit).toBeDisabled() // 약관 동의 전

    await user.click(screen.getByRole('checkbox', { name: '전체 동의하기' }))
    for (const name of [/만 19세/, /서비스 이용약관/, /개인정보/, /민감정보/]) {
      expect(screen.getByRole('checkbox', { name })).toBeChecked()
    }
    expect(submit).toBeEnabled()

    await user.click(screen.getByRole('checkbox', { name: /민감정보/ }))
    expect(screen.getByRole('checkbox', { name: '전체 동의하기' })).not.toBeChecked()
    expect(submit).toBeDisabled()
  })

  it('비밀번호 규칙(영문+숫자 8자 이상)과 확인 일치를 검사한다', async () => {
    const user = renderAt('/signup')
    await user.type(screen.getByLabelText('이메일'), 'synap@ajou.ac.kr')
    await user.type(screen.getByLabelText('닉네임'), '지예')
    await user.click(screen.getByRole('checkbox', { name: '전체 동의하기' }))
    const submit = screen.getByRole('button', { name: '가입하기' })

    await user.type(screen.getByLabelText('비밀번호'), 'onlyletters')
    await user.type(screen.getByLabelText('비밀번호 확인'), 'onlyletters')
    expect(submit).toBeDisabled() // 숫자가 없다

    await user.clear(screen.getByLabelText('비밀번호'))
    await user.type(screen.getByLabelText('비밀번호'), 'password1')
    expect(screen.getByRole('alert')).toHaveTextContent('비밀번호가 일치하지 않아요')
    expect(submit).toBeDisabled()

    await user.clear(screen.getByLabelText('비밀번호 확인'))
    await user.type(screen.getByLabelText('비밀번호 확인'), 'password1')
    expect(submit).toBeEnabled()
  })

  it('가입하면 회원 세션이 저장되고 홈으로 간다', async () => {
    const user = renderAt('/signup')
    await fillValid(user)
    await user.click(screen.getByRole('checkbox', { name: '전체 동의하기' }))
    await user.click(screen.getByRole('button', { name: '가입하기' }))

    expect(await screen.findByText('홈 화면')).toBeInTheDocument()
    expect(getSession()).toEqual({ kind: 'user', email: 'synap@ajou.ac.kr', nickname: '지예' })
  })

  it('이미 가입된 이메일이면 이메일 칸에 오류를 보여준다', async () => {
    const user = renderAt('/signup')
    await fillValid(user, TAKEN_EMAIL)
    await user.click(screen.getByRole('checkbox', { name: '전체 동의하기' }))
    await user.click(screen.getByRole('button', { name: '가입하기' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('이미 가입된 이메일이에요.')
    expect(screen.getByLabelText('이메일')).toHaveAttribute('aria-invalid', 'true')
    expect(getSession()).toBeNull()
  })
})
