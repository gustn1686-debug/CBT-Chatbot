import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { resetMockRecords } from '../api/records'
import { Home } from './Home'

const renderHome = () =>
  render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  )

describe('Home', () => {
  beforeEach(() => resetMockRecords())

  it('최근 기록을 최신순 2건까지 보여주고 상세로 연결한다', async () => {
    renderHome()
    const first = await screen.findByRole('link', { name: /발표 자료 오타 관련 생각 정리/ })
    expect(first).toHaveAttribute('href', '/records/r-4')
    expect(screen.getByText('친구와의 약속 취소, 마음이 쓰였던 날')).toBeInTheDocument()
    expect(screen.queryByText('면접 결과를 기다리며 든 생각')).not.toBeInTheDocument()
    expect(screen.queryByText('아직 기록이 없어요')).not.toBeInTheDocument()
  })

  it('기록이 없으면 처음 방문용 빈 상태를 보여준다', async () => {
    resetMockRecords([])
    renderHome()
    expect(await screen.findByText('아직 기록이 없어요')).toBeInTheDocument()
    expect(screen.getByText('처음이시네요. 편하게 이야기해보세요')).toBeInTheDocument()
    expect(screen.queryByText('최근 기록')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /대화 시작하기/ })).toHaveAttribute('href', '/chat')
  })
})
