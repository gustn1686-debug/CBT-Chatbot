import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { mockOptions } from '../api/mockChat'
import { resetMockRecords } from '../api/records'
import { saveSession } from '../lib/session'
import App from '../App'
import { Chat } from './Chat'
import { Home } from './Home'

const setUsed = (count: number) => localStorage.setItem('synap.mock.sessionCount', String(count))

function renderHome() {
  render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/chat" element={<p>채팅 화면</p>} />
        <Route path="/signup" element={<p>가입 화면</p>} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

function renderChat() {
  render(
    <MemoryRouter initialEntries={['/chat']}>
      <Routes>
        <Route path="/chat" element={<Chat />} />
        <Route path="/" element={<p>홈 화면</p>} />
        <Route path="/signup" element={<p>가입 화면</p>} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  resetMockRecords()
  mockOptions.delayMs = 0
})

describe('앱 진입 흐름', () => {
  const open = (path: string) =>
    render(
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>,
    )

  it('온보딩 전이면 온보딩으로 보낸다', () => {
    open('/')
    expect(screen.getByRole('heading', { name: '이 서비스는 무엇인가요?' })).toBeInTheDocument()
  })

  it('온보딩만 마치고 세션이 없으면 시작 선택으로 보낸다', () => {
    localStorage.setItem('synap.onboarded', '1')
    open('/records')
    expect(screen.getByRole('heading', { name: 'Synap과 함께 시작해요' })).toBeInTheDocument()
  })

  it('세션이 있으면 본 화면을 보여준다', async () => {
    localStorage.setItem('synap.onboarded', '1')
    saveSession({ kind: 'guest' })
    open('/')
    expect(await screen.findByRole('heading', { name: '오늘은 어떤 하루였나요' })).toBeInTheDocument()
  })
})

describe('비회원 홈', () => {
  it('회원에게는 체험 안내를 보여주지 않는다', async () => {
    saveSession({ kind: 'user', email: 'a@b.co', nickname: 'a' })
    renderHome()
    await screen.findByText('최근 기록')
    expect(screen.queryByText('비회원으로 체험 중이에요')).not.toBeInTheDocument()
  })

  it('무료 대화 사용량을 보여주고, 가입하기로 연결한다', async () => {
    saveSession({ kind: 'guest' })
    setUsed(2)
    renderHome()
    expect(await screen.findByText('무료 대화 3회 중 2회 사용')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '가입하기' })).toHaveAttribute('href', '/signup')
  })

  it('아직 남았으면 대화 시작하기는 바로 채팅으로 간다', async () => {
    saveSession({ kind: 'guest' })
    setUsed(2)
    const user = renderHome()
    await screen.findByText('무료 대화 3회 중 2회 사용')
    await user.click(screen.getByRole('link', { name: /대화 시작하기/ }))
    expect(screen.getByText('채팅 화면')).toBeInTheDocument()
  })

  it('무료 대화를 다 쓰면 대화 시작 전에 가입을 안내하고, "다음에 할게요"로 계속할 수 있다', async () => {
    saveSession({ kind: 'guest' })
    setUsed(3)
    const user = renderHome()
    expect(await screen.findByText('무료 대화 3회 모두 사용')).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: /대화 시작하기/ }))
    expect(screen.getByRole('dialog', { name: '벌써 3번의 대화를 함께했어요' })).toBeInTheDocument()
    expect(screen.queryByText('채팅 화면')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '다음에 할게요' }))
    expect(screen.getByText('채팅 화면')).toBeInTheDocument()
  })

  it('가입 안내에서 "가입하고 계속하기"는 가입 화면으로 간다', async () => {
    saveSession({ kind: 'guest' })
    setUsed(3)
    const user = renderHome()
    await screen.findByText('무료 대화 3회 모두 사용')
    await user.click(screen.getByRole('link', { name: /대화 시작하기/ }))
    await user.click(screen.getByRole('button', { name: '가입하고 계속하기' }))
    expect(screen.getByText('가입 화면')).toBeInTheDocument()
  })
})

describe('비회원 대화 종료', () => {
  const sendAndEnd = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.type(screen.getByLabelText('메시지 입력'), '오늘은 여기까지 얘기하고 싶어요')
    await user.click(screen.getByRole('button', { name: '보내기' }))
    await screen.findAllByText(/마음이 어떠셨어요|이야기해 주실|떠올려 볼까요/)
    await user.click(screen.getByRole('button', { name: '대화 종료' }))
    await user.click(screen.getByRole('button', { name: '종료하기' }))
  }

  it('이야기를 나눈 비회원에게는 기록 보관(가입)을 안내한다', async () => {
    saveSession({ kind: 'guest' })
    const user = renderChat()
    await sendAndEnd(user)
    expect(screen.getByRole('dialog', { name: '오늘 나눈 대화, 보관해둘까요?' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '괜찮아요' }))
    expect(screen.getByText('홈 화면')).toBeInTheDocument()
  })

  it('"가입하고 보관하기"는 가입 화면으로 간다', async () => {
    saveSession({ kind: 'guest' })
    const user = renderChat()
    await sendAndEnd(user)
    await user.click(screen.getByRole('button', { name: '가입하고 보관하기' }))
    expect(screen.getByText('가입 화면')).toBeInTheDocument()
  })

  it('이야기를 나누지 않았다면 안내 없이 바로 홈으로 간다', async () => {
    saveSession({ kind: 'guest' })
    const user = renderChat()
    await user.click(screen.getByRole('button', { name: '대화 종료' }))
    await user.click(screen.getByRole('button', { name: '종료하기' }))
    expect(screen.getByText('홈 화면')).toBeInTheDocument()
  })

  it('회원은 대화를 나눴어도 안내 없이 홈으로 간다', async () => {
    saveSession({ kind: 'user', email: 'a@b.co', nickname: 'a' })
    const user = renderChat()
    await sendAndEnd(user)
    expect(screen.getByText('홈 화면')).toBeInTheDocument()
  })
})

describe('무료 대화 사용량 집계', () => {
  it('비회원이 대화를 시작할 때마다 사용 횟수가 늘어난다', async () => {
    saveSession({ kind: 'guest' })
    const user = renderChat()
    await user.type(screen.getByLabelText('메시지 입력'), '안녕')
    await user.click(screen.getByRole('button', { name: '보내기' }))
    await screen.findAllByText(/마음이 어떠셨어요|이야기해 주실|떠올려 볼까요/)
    expect(localStorage.getItem('synap.mock.sessionCount')).toBe('1')
  })
})
