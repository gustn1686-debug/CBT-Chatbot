import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { mockOptions } from '../api/mockChat'
import { Chat } from './Chat'

function renderChat(state?: unknown) {
  render(
    <MemoryRouter initialEntries={[{ pathname: '/chat', state }]}>
      <Routes>
        <Route path="/chat" element={<Chat />} />
        <Route path="/" element={<p>홈</p>} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

describe('Chat', () => {
  beforeAll(() => {
    mockOptions.delayMs = 0
  })

  it('인사말을 보여주고, 보낸 메시지에 스트리밍 응답이 붙는다', async () => {
    const user = renderChat()
    expect(screen.getByText('안녕하세요. 오늘은 어떤 얘기를 나눠볼까요?')).toBeInTheDocument()

    await user.type(screen.getByLabelText('메시지 입력'), '요즘 실수가 잦아요')
    await user.click(screen.getByRole('button', { name: '보내기' }))

    expect(screen.getByText('요즘 실수가 잦아요')).toBeInTheDocument()
    expect((await screen.findAllByText(/마음이 어떠셨어요|이야기해 주실|떠올려 볼까요/)).length).toBeGreaterThan(0)
  })

  it('전송에 실패하면 안내를 보여주고, 다시 시도하면 응답을 받는다', async () => {
    const user = renderChat()
    await user.type(screen.getByLabelText('메시지 입력'), '[[실패] 잠을 못 자요')
    await user.click(screen.getByRole('button', { name: '보내기' }))

    const retry = await screen.findByRole('button', { name: /전송 실패/ })
    await user.click(retry)

    expect((await screen.findAllByText(/마음이 어떠셨어요|이야기해 주실|떠올려 볼까요/)).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /전송 실패/ })).not.toBeInTheDocument()
  })

  it('대화 종료는 확인 모달을 거치고, 취소하면 대화가 유지된다', async () => {
    const user = renderChat()
    await user.click(screen.getByRole('button', { name: '대화 종료' }))
    expect(screen.getByRole('dialog', { name: '대화를 종료할까요?' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '취소' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '대화 종료' }))
    await user.click(screen.getByRole('button', { name: '종료하기' }))
    expect(screen.getByText('홈')).toBeInTheDocument()
  })

  it('위기 표현을 보내면 상담 전화 안내 시트가 뜨고, 일반 대화로 돌아갈 수 있다', async () => {
    const user = renderChat()
    await user.type(screen.getByLabelText('메시지 입력'), '그냥 죽고 싶어')
    await user.click(screen.getByRole('button', { name: '보내기' }))

    expect(await screen.findByRole('dialog', { name: '지금 많이 힘드신 것 같아요' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '일반 대화로 돌아가기' }))
    expect(screen.queryByRole('dialog', { name: '지금 많이 힘드신 것 같아요' })).not.toBeInTheDocument()
  })

  it('기록에서 이어가면 그 기록을 언급하는 첫 인사를 보여준다', () => {
    renderChat({ record: { id: 'r-4', title: '발표 자료 오타 관련 생각 정리' } })
    expect(
      screen.getByText("지난번에 '발표 자료 오타 관련 생각 정리' 이야기를 나눴어요. 오늘은 이어서 어떤 이야기를 해볼까요?"),
    ).toBeInTheDocument()
    expect(screen.queryByText('안녕하세요. 오늘은 어떤 얘기를 나눠볼까요?')).not.toBeInTheDocument()
  })

  it('입력이 비어 있으면 보낼 수 없다', () => {
    renderChat()
    expect(screen.getByRole('button', { name: '보내기' })).toBeDisabled()
  })
})

describe('Chat 네트워크 오류', () => {
  const setOnline = (online: boolean) => {
    Object.defineProperty(navigator, 'onLine', { configurable: true, get: () => online })
    act(() => {
      window.dispatchEvent(new Event(online ? 'online' : 'offline'))
    })
  }

  beforeAll(() => {
    mockOptions.delayMs = 0
  })
  afterEach(() => setOnline(true))

  it('연결이 끊기면 안내를 띄우고 입력을 막는다', () => {
    renderChat()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    setOnline(false)
    expect(screen.getByRole('alert')).toHaveTextContent('인터넷 연결을 확인해주세요')
    const input = screen.getByLabelText('메시지 입력')
    expect(input).toBeDisabled()
    expect(input).toHaveAttribute('placeholder', '연결 대기 중...')
    expect(screen.getByRole('button', { name: '보내기' })).toBeDisabled()
  })

  it('연결이 돌아오면 안내가 사라지고, 쓰던 글을 그대로 보낼 수 있다', async () => {
    const user = renderChat()
    await user.type(screen.getByLabelText('메시지 입력'), '요즘 잠이 안 와요')

    setOnline(false)
    expect(screen.getByLabelText('메시지 입력')).toHaveValue('요즘 잠이 안 와요')
    expect(screen.getByRole('button', { name: '보내기' })).toBeDisabled()

    setOnline(true)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByLabelText('메시지 입력')).toBeEnabled()
    await user.click(screen.getByRole('button', { name: '보내기' }))
    expect(screen.getByText('요즘 잠이 안 와요')).toBeInTheDocument()
  })
})
