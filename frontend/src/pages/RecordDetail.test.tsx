import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { getRecord, resetMockRecords } from '../api/records'
import { RecordDetail } from './RecordDetail'

function ChatProbe() {
  const { state } = useLocation()
  return <p>채팅: {state?.record?.title}</p>
}

function renderDetail(id = 'r-4') {
  render(
    <MemoryRouter initialEntries={[`/records/${id}`]}>
      <Routes>
        <Route path="/records/:id" element={<RecordDetail />} />
        <Route path="/records" element={<p>목록</p>} />
        <Route path="/chat" element={<ChatProbe />} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

describe('RecordDetail', () => {
  beforeEach(() => resetMockRecords())

  it('여섯 개 카드와 날짜를 보여준다', async () => {
    renderDetail()
    expect(await screen.findByText('2025.03.12')).toBeInTheDocument()
    for (const label of ['상황', '처음 떠오른 생각', '감정', '대화에서 확인한 점', '다른 해석', '다음에 해볼 행동']) {
      expect(screen.getByRole('region', { name: label })).toBeInTheDocument()
    }
    expect(screen.getByText('어제 팀 회의에서 발표 자료에 오타가 있었어요.')).toBeInTheDocument()
    expect(screen.getByText('속상함')).toBeInTheDocument()
  })

  it('수정하지 않았으면 저장 버튼이 비활성이다', async () => {
    renderDetail()
    await screen.findByText('2025.03.12')
    expect(screen.getByRole('button', { name: '수정 내용 저장' })).toBeDisabled()
  })

  it('✎로 카드를 고치고 저장하면 기록에 반영된다', async () => {
    const user = renderDetail()
    await screen.findByText('2025.03.12')

    await user.click(screen.getByRole('button', { name: '상황 수정' }))
    const box = screen.getByRole('textbox', { name: '상황' })
    await user.clear(box)
    await user.type(box, '회의에서 실수가 있었어요')
    await user.tab() // 포커스를 벗어나면 편집이 끝난다

    expect(screen.getByText('회의에서 실수가 있었어요')).toBeInTheDocument()
    const save = screen.getByRole('button', { name: '수정 내용 저장' })
    expect(save).toBeEnabled()
    // 저장 전에는 원본이 그대로다
    expect((await getRecord('r-4'))?.situation).toBe('어제 팀 회의에서 발표 자료에 오타가 있었어요.')

    await user.click(save)
    expect(await screen.findByText('저장했어요')).toBeInTheDocument()
    expect((await getRecord('r-4'))?.situation).toBe('회의에서 실수가 있었어요')
    expect(save).toBeDisabled()
  })

  it('✕는 그 카드 내용을 비우고, 감정 칩은 하나씩 뺄 수 있다', async () => {
    const user = renderDetail()
    await screen.findByText('2025.03.12')

    await user.click(screen.getByRole('button', { name: '다른 해석 비우기' }))
    expect(screen.getByRole('region', { name: '다른 해석' })).toHaveTextContent('내용이 없어요')

    await user.click(screen.getByRole('button', { name: '부끄러움 제거' }))
    expect(screen.queryByText('부끄러움')).not.toBeInTheDocument()
    expect(screen.getByText('불안')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '수정 내용 저장' }))
    const saved = await getRecord('r-4')
    expect(saved?.alternative).toBe('')
    expect(saved?.emotions).toEqual(['불안', '속상함'])
  })

  it('감정 카드의 ✎로 감정을 추가할 수 있다', async () => {
    const user = renderDetail()
    await screen.findByText('2025.03.12')

    await user.click(screen.getByRole('button', { name: '감정 수정' }))
    await user.type(screen.getByRole('textbox', { name: '감정 추가' }), '막막함{Enter}')
    expect(screen.getByText('막막함')).toBeInTheDocument()
  })

  it('"이 기록에서 대화 이어가기"는 기록 제목을 들고 채팅으로 이동한다', async () => {
    const user = renderDetail()
    await screen.findByText('2025.03.12')
    await user.click(screen.getByRole('button', { name: '이 기록에서 대화 이어가기' }))
    expect(screen.getByText('채팅: 발표 자료 오타 관련 생각 정리')).toBeInTheDocument()
  })

  it('없는 기록이면 안내와 목록 링크를 보여준다', async () => {
    renderDetail('nope')
    expect(await screen.findByText('기록을 찾을 수 없어요')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '목록으로' })).toHaveAttribute('href', '/records')
  })
})
