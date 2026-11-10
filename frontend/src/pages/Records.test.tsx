import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { resetMockRecords } from '../api/records'
import { Records } from './Records'

const renderRecords = () =>
  render(
    <MemoryRouter>
      <Records />
    </MemoryRouter>,
  )

describe('Records', () => {
  beforeEach(() => resetMockRecords())

  it('기록을 최신순으로 보여주고, 각 카드는 상세로 연결된다', async () => {
    renderRecords()
    await screen.findByText('발표 자료 오타 관련 생각 정리')
    const titles = screen.getAllByRole('link').filter((a) => a.getAttribute('href')?.startsWith('/records/'))
    expect(titles).toHaveLength(4)
    expect(within(titles[0]).getByText('발표 자료 오타 관련 생각 정리')).toBeInTheDocument()
    expect(titles[0]).toHaveAttribute('href', '/records/r-4')
    expect(within(titles[0]).getByText('2025.03.12')).toBeInTheDocument()
  })

  it('분류 칩을 누르면 그 분류의 기록만 남는다', async () => {
    const user = userEvent.setup()
    renderRecords()
    await screen.findByText('발표 자료 오타 관련 생각 정리')

    await user.click(screen.getByRole('button', { name: '관계' }))
    expect(screen.getByRole('button', { name: '관계' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('친구와의 약속 취소, 마음이 쓰였던 날')).toBeInTheDocument()
    expect(screen.queryByText('발표 자료 오타 관련 생각 정리')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '전체' }))
    expect(screen.getByText('발표 자료 오타 관련 생각 정리')).toBeInTheDocument()
  })

  it('기록이 하나도 없으면 빈 상태와 "전체" 칩만 보여준다', async () => {
    resetMockRecords([])
    renderRecords()
    expect(await screen.findByText('아직 기록이 없어요')).toBeInTheDocument()
    expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual(['전체'])
  })

  it('선택한 분류에 기록이 없으면 안내 문구를 보여준다', async () => {
    const user = userEvent.setup()
    resetMockRecords([
      {
        id: 'only',
        date: '2025-01-01',
        title: '하나뿐인 기록',
        tag: '업무',
        situation: '',
        firstThought: '',
        emotions: [],
        findings: '',
        alternative: '',
        nextAction: '',
      },
    ])
    renderRecords()
    await screen.findByText('하나뿐인 기록')
    await user.click(screen.getByRole('button', { name: '불안' }))
    expect(screen.getByText('이 분류의 기록이 없어요')).toBeInTheDocument()
  })
})
