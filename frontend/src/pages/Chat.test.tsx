import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { getConversation } from '../api/chat'
import { mockOptions, resetMockConversations } from '../api/mockChat'
import { saveSession } from '../lib/session'
import { Chat } from './Chat'

function renderChat(path = '/') {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/chat/:id" element={<Chat />} />
        <Route path="/settings" element={<p>설정 화면</p>} />
        <Route path="/login" element={<p>로그인 화면</p>} />
        <Route path="/signup" element={<p>가입 화면</p>} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

const REPLY = /마음이 어떠셨어요|이야기해 주실|떠올려 볼까요/

describe('Chat', () => {
  beforeAll(() => {
    mockOptions.delayMs = 0
  })
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    resetMockConversations()
  })

  it('앱을 열면 바로 새 대화 화면이고, 보낸 메시지에 스트리밍 응답이 붙는다', async () => {
    const user = renderChat()
    expect(screen.getByRole('heading', { name: '오늘은 어떤 하루였나요' })).toBeInTheDocument()

    await user.type(screen.getByLabelText('메시지 입력'), '요즘 실수가 잦아요')
    await user.click(screen.getByRole('button', { name: '보내기' }))

    expect(screen.getByText('요즘 실수가 잦아요')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '오늘은 어떤 하루였나요' })).not.toBeInTheDocument() // 안내는 첫 메시지를 보내면 사라진다
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

  it('모델 서버가 몰려 거절되면 "이용하는 분이 많아요" 안내를 보여주고, 다시 시도하면 응답을 받는다', async () => {
    const user = renderChat()
    await user.type(screen.getByLabelText('메시지 입력'), '[[혼잡] 잠이 안 와요')
    await user.click(screen.getByRole('button', { name: '보내기' }))

    const retry = await screen.findByRole('button', { name: /지금 이용하는 분이 많아요/ })
    expect(retry).toHaveTextContent('잠시 후 다시 시도')
    expect(screen.queryByRole('button', { name: /전송 실패/ })).not.toBeInTheDocument()

    await user.click(retry)
    expect((await screen.findAllByText(/마음이 어떠셨어요|이야기해 주실|떠올려 볼까요/)).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /지금 이용하는 분이 많아요/ })).not.toBeInTheDocument()
  })

  it('응답이 너무 늦으면 그에 맞는 안내를 보여준다', async () => {
    const user = renderChat()
    await user.type(screen.getByLabelText('메시지 입력'), '[[지연] 요즘 힘들어요')
    await user.click(screen.getByRole('button', { name: '보내기' }))
    expect(await screen.findByRole('button', { name: /응답이 늦어지고 있어요/ })).toBeInTheDocument()
  })

  it('왼쪽 메뉴에 지난 대화 목록이 뜨고, 누르면 그 대화를 이어서 한다', async () => {
    const user = renderChat()
    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    const menu = screen.getByRole('dialog', { name: '메뉴' })
    expect(within(menu).getByRole('link', { name: /발표 자료 오타 때문에 마음이 불편해요/ })).toHaveAttribute(
      'href',
      '/chat/c-3',
    )
    expect(within(menu).getByRole('link', { name: /친구가 약속을 당일에 취소했어요/ })).toBeInTheDocument()
    expect(within(menu).getByRole('link', { name: /면접 결과를 기다리는 중이에요/ })).toBeInTheDocument()

    await user.click(within(menu).getByRole('link', { name: /친구가 약속을 당일에 취소했어요/ }))
    expect(screen.queryByRole('dialog', { name: '메뉴' })).not.toBeInTheDocument() // 이동하면 메뉴가 닫힌다
    expect(await screen.findByText('그렇게 느끼신 이유를 조금 더 이야기해 주실 수 있을까요?')).toBeInTheDocument()
  })

  it('지난 대화가 없으면 안내를 보여준다', async () => {
    resetMockConversations([])
    const user = renderChat()
    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    expect(await screen.findByText('아직 나눈 대화가 없어요')).toBeInTheDocument()
  })

  it('지금 보고 있는 대화는 메뉴에서 표시된다', async () => {
    const user = renderChat('/chat/c-2')
    await screen.findByText('친구가 약속을 당일에 취소했어요')
    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    expect(screen.getByRole('link', { name: /친구가 약속을 당일에 취소했어요/ })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: /발표 자료 오타 때문에/ })).not.toHaveAttribute('aria-current')
  })

  it('"새 대화"를 누르면 처음 화면으로 돌아간다', async () => {
    const user = renderChat('/chat/c-3')
    await screen.findByText('발표 자료 오타 때문에 마음이 불편해요')
    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    await user.click(screen.getByRole('button', { name: /새 대화/ }))
    expect(await screen.findByRole('heading', { name: '오늘은 어떤 하루였나요' })).toBeInTheDocument()
    expect(screen.queryByText('발표 자료 오타 때문에 마음이 불편해요')).not.toBeInTheDocument()
  })

  it('새 대화 중에 "새 대화"를 눌러도 처음 상태로 되돌아간다', async () => {
    const user = renderChat()
    await user.type(screen.getByLabelText('메시지 입력'), '이야기 하나')
    await user.click(screen.getByRole('button', { name: '보내기' }))
    await screen.findAllByText(REPLY)

    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    await user.click(screen.getByRole('button', { name: /새 대화/ }))
    expect(await screen.findByRole('heading', { name: '오늘은 어떤 하루였나요' })).toBeInTheDocument()
    expect(screen.queryByText('이야기 하나')).not.toBeInTheDocument()
  })

  it('메뉴는 Esc 와 바깥을 눌러 닫을 수 있다', async () => {
    const user = renderChat()
    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog', { name: '메뉴' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    await user.click(screen.getAllByRole('button', { name: '메뉴 닫기' })[1]) // 바깥 영역
    expect(screen.queryByRole('dialog', { name: '메뉴' })).not.toBeInTheDocument()
  })

  it('회원은 오른쪽 위 설정 버튼으로, 메뉴의 설정으로 설정에 들어간다', async () => {
    saveSession({ kind: 'user', email: 'a@b.co', nickname: 'a' })
    const user = renderChat()
    expect(screen.queryByRole('link', { name: '로그인' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: '설정' })[0]).toHaveAttribute('href', '/settings')

    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    await user.click(within(screen.getByRole('dialog', { name: '메뉴' })).getByRole('link', { name: '설정' }))
    expect(screen.getByText('설정 화면')).toBeInTheDocument()
  })

  it('비회원은 오른쪽 위에 로그인 버튼이 있고, 메뉴에서 가입을 안내한다', async () => {
    saveSession({ kind: 'guest' })
    const user = renderChat()
    expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')

    await user.click(screen.getByRole('button', { name: '메뉴 열기' }))
    const menu = screen.getByRole('dialog', { name: '메뉴' })
    expect(within(menu).getByRole('link', { name: '가입하고 대화 보관하기' })).toHaveAttribute('href', '/signup')
    expect(within(menu).getByRole('link', { name: '설정' })).toHaveAttribute('href', '/settings')
  })

  it('없는 대화를 열면 새 대화 화면으로 돌아간다', async () => {
    renderChat('/chat/nope')
    expect(await screen.findByRole('heading', { name: '오늘은 어떤 하루였나요' })).toBeInTheDocument()
  })

  it('위기 표현을 보내면 상담 전화 안내 시트가 뜨고, 일반 대화로 돌아갈 수 있다', async () => {
    const user = renderChat()
    await user.type(screen.getByLabelText('메시지 입력'), '그냥 죽고 싶어')
    await user.click(screen.getByRole('button', { name: '보내기' }))

    expect(await screen.findByRole('dialog', { name: '지금 많이 힘드신 것 같아요' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '일반 대화로 돌아가기' }))
    expect(screen.queryByRole('dialog', { name: '지금 많이 힘드신 것 같아요' })).not.toBeInTheDocument()
  })

  it('지난 대화를 열면 이전 메시지를 불러오고, 이어서 보낼 수 있다', async () => {
    resetMockConversations()
    const user = renderChat('/chat/c-3')
    expect(await screen.findByText('발표 자료 오타 때문에 마음이 불편해요')).toBeInTheDocument()
    expect(screen.getByText('그런 생각이 들 때 마음이 어떠셨어요?')).toBeInTheDocument()
    expect(screen.queryByText('안녕하세요. 오늘은 어떤 얘기를 나눠볼까요?')).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('메시지 입력'), '조금 나아졌어요')
    await user.click(screen.getByRole('button', { name: '보내기' }))
    expect(screen.getByText('조금 나아졌어요')).toBeInTheDocument()
    // 새 답변이 도착해 같은 대화에 이어서 저장된다
    await waitFor(async () => expect((await getConversation('c-3')).messages).toHaveLength(4))
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
