import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { resetMockConversations } from '../api/mockChat'
import { Home } from './Home'

const renderHome = () =>
  render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  )

describe('Home', () => {
  beforeEach(() => resetMockConversations())

  it('지난 대화를 최근순으로 모두 보여주고, 누르면 그 대화로 이어진다', async () => {
    renderHome()
    const first = await screen.findByRole('link', { name: /발표 자료 오타 때문에 마음이 불편해요/ })
    expect(first).toHaveAttribute('href', '/chat/c-3')
    expect(screen.getByRole('link', { name: /친구가 약속을 당일에 취소했어요/ })).toHaveAttribute('href', '/chat/c-2')
    expect(screen.getByRole('link', { name: /면접 결과를 기다리는 중이에요/ })).toHaveAttribute('href', '/chat/c-1')
    expect(screen.getByText('지난 대화')).toBeInTheDocument()
    expect(screen.queryByText('아직 나눈 대화가 없어요')).not.toBeInTheDocument()
  })

  it('대화가 없으면 처음 방문용 빈 상태를 보여준다', async () => {
    resetMockConversations([])
    renderHome()
    expect(await screen.findByText('아직 나눈 대화가 없어요')).toBeInTheDocument()
    expect(screen.getByText('처음이시네요. 편하게 이야기해보세요')).toBeInTheDocument()
    expect(screen.queryByText('지난 대화')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /대화 시작하기/ })).toHaveAttribute('href', '/chat')
  })

  it('메시지가 없는 빈 대화는 목록에 보이지 않는다', async () => {
    resetMockConversations([{ id: 'c-empty', title: null, updatedAt: '2025-03-13T00:00:00Z', messages: [] }])
    renderHome()
    expect(await screen.findByText('아직 나눈 대화가 없어요')).toBeInTheDocument()
  })
})
