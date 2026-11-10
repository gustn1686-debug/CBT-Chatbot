import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { mockOptions } from './api/mockChat'
import { resetMockRecords } from './api/records'
import { ConfirmModal } from './components/ConfirmModal'
import { Chat } from './pages/Chat'
import { Login } from './pages/Login'
import { RecordDetail } from './pages/RecordDetail'
import { Records } from './pages/Records'
import { Signup } from './pages/Signup'
import { Start } from './pages/Start'

function ModalHarness() {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button onClick={() => setOpen(true)}>열기</button>
      {open && (
        <ConfirmModal
          title="삭제할까요?"
          description="되돌릴 수 없어요."
          confirmLabel="삭제하기"
          onCancel={() => setOpen(false)}
          onConfirm={() => setOpen(false)}
        />
      )}
    </>
  )
}

describe('대화상자 포커스', () => {
  it('열리면 "취소"에 포커스가 가고, Tab 은 대화상자 안에서만 돈다', async () => {
    const user = userEvent.setup()
    render(<ModalHarness />)
    await user.click(screen.getByRole('button', { name: '열기' }))

    const cancel = screen.getByRole('button', { name: '취소' })
    const confirm = screen.getByRole('button', { name: '삭제하기' })
    expect(cancel).toHaveFocus()

    await user.tab()
    expect(confirm).toHaveFocus()
    await user.tab() // 마지막 → 처음으로 돌아온다
    expect(cancel).toHaveFocus()
    await user.tab({ shift: true }) // 처음 → 마지막으로
    expect(confirm).toHaveFocus()
    expect(screen.getByRole('button', { name: '열기' })).not.toHaveFocus()
  })

  it('닫히면 열었던 버튼으로 포커스가 돌아간다', async () => {
    const user = userEvent.setup()
    render(<ModalHarness />)
    const opener = screen.getByRole('button', { name: '열기' })
    await user.click(opener)
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(opener).toHaveFocus()
  })
})

describe('화면 제목과 랜드마크', () => {
  beforeEach(() => resetMockRecords())

  const at = (path: string) =>
    render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/start" element={<Start />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/records" element={<Records />} />
          <Route path="/records/:id" element={<RecordDetail />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </MemoryRouter>,
    )

  it.each([
    ['/start', '시작하기 · Synap'],
    ['/login', '로그인 · Synap'],
    ['/signup', '회원가입 · Synap'],
    ['/records', '내 기록 · Synap'],
    ['/chat', '대화 · Synap'],
  ])('%s 는 탭 제목이 "%s" 이다', (path, title) => {
    at(path)
    expect(document.title).toBe(title)
  })

  it('기록 상세의 탭 제목은 기록 제목이고, 보이지 않는 1단계 제목도 같다', async () => {
    at('/records/r-4')
    const h1 = await screen.findByRole('heading', { level: 1, name: '발표 자료 오타 관련 생각 정리' })
    expect(h1).toBeInTheDocument()
    expect(document.title).toBe('발표 자료 오타 관련 생각 정리 · Synap')
  })

  it.each(['/start', '/login', '/signup'])('%s 에는 main 랜드마크가 하나 있다', (path) => {
    at(path)
    expect(screen.getAllByRole('main')).toHaveLength(1)
  })

  it('채팅 입력창은 이름 있는 폼 랜드마크다', () => {
    at('/chat')
    expect(screen.getByRole('form', { name: '메시지 보내기' })).toBeInTheDocument()
  })
})

describe('채팅 읽어 주기', () => {
  beforeAll(() => {
    mockOptions.delayMs = 0
  })

  it('메시지 영역은 live 영역이 아니고, 답변이 끝난 뒤에만 안내 영역에 전체 문장이 담긴다', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/chat']}>
        <Routes>
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </MemoryRouter>,
    )
    const announcer = () => document.querySelector<HTMLElement>('p.sr-only[role="status"]')!
    expect(screen.getByRole('main')).not.toHaveAttribute('aria-live')
    expect(announcer().textContent).toBe('') // 인사말은 읽어 주지 않는다

    await user.type(screen.getByLabelText('메시지 입력'), '안녕')
    await user.click(screen.getByRole('button', { name: '보내기' }))
    await waitFor(() => expect(announcer().textContent).toMatch(/마음이 어떠셨어요|이야기해 주실|떠올려 볼까요/))
  })
})
