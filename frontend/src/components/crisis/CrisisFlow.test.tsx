import { act, fireEvent, render, screen } from '@testing-library/react'
import { CrisisFlow } from './CrisisFlow'
import { CALL_TIMEOUT_MS } from './CallScreen'

function setup(resources = [] as { name: string; tel: string }[]) {
  const onClose = vi.fn()
  render(<CrisisFlow resources={resources} onClose={onClose} />)
  return { onClose }
}

describe('CrisisFlow', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    // jsdom 은 tel: 이동을 지원하지 않아 경고가 나오므로 기본 동작만 막는다.
    document.addEventListener('click', preventNavigation)
  })
  afterEach(() => {
    document.removeEventListener('click', preventNavigation)
    vi.useRealTimers()
  })
  const preventNavigation = (e: Event) => e.preventDefault()

  it('서버가 번호를 주지 않아도 기본 상담 번호 두 개를 tel 링크로 보여준다', () => {
    setup()
    const links = screen.getAllByRole('link', { name: /바로 전화하기/ })
    expect(links.map((a) => a.getAttribute('href'))).toEqual(['tel:15770199', 'tel:15889191'])
  })

  it('서버가 준 번호가 있으면 그것을 쓴다', () => {
    setup([{ name: '테스트 상담', tel: '109' }])
    expect(screen.getByRole('link', { name: /바로 전화하기/ })).toHaveAttribute('href', 'tel:109')
    expect(screen.queryByText('1577-0199')).not.toBeInTheDocument()
  })

  it('전화를 걸면 발신 중 화면이 뜨고, 시간이 지나도 전화 앱으로 안 넘어가면 실패 화면이 뜬다', () => {
    setup()
    fireEvent.click(screen.getAllByRole('link', { name: /바로 전화하기/ })[0])
    expect(screen.getByText('발신 중...')).toBeInTheDocument()

    act(() => vi.advanceTimersByTime(CALL_TIMEOUT_MS))
    expect(screen.getByText('연결할 수 없어요')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '다시 걸기' })).toHaveAttribute('href', 'tel:15770199')
  })

  it('전화 앱으로 넘어가면(포커스를 잃으면) 실패 화면으로 바뀌지 않는다', () => {
    setup()
    fireEvent.click(screen.getAllByRole('link', { name: /바로 전화하기/ })[0])

    act(() => {
      window.dispatchEvent(new Event('blur'))
      vi.advanceTimersByTime(CALL_TIMEOUT_MS * 2)
    })
    expect(screen.getByText('발신 중...')).toBeInTheDocument()
    expect(screen.queryByText('연결할 수 없어요')).not.toBeInTheDocument()
  })

  it('실패 화면에서 다시 걸기는 발신 중으로, 닫기는 안내 시트로 돌아간다', () => {
    setup()
    fireEvent.click(screen.getAllByRole('link', { name: /바로 전화하기/ })[0])
    act(() => vi.advanceTimersByTime(CALL_TIMEOUT_MS))

    fireEvent.click(screen.getByRole('link', { name: '다시 걸기' }))
    expect(screen.getByText('발신 중...')).toBeInTheDocument()

    act(() => vi.advanceTimersByTime(CALL_TIMEOUT_MS))
    fireEvent.click(screen.getByRole('button', { name: '닫기' }))
    expect(screen.getByRole('dialog', { name: '지금 많이 힘드신 것 같아요' })).toBeInTheDocument()
  })

  it('일반 대화로 돌아가기와 ✕, Esc 모두 시트를 닫는다', () => {
    const { onClose } = setup()
    fireEvent.click(screen.getByRole('button', { name: '일반 대화로 돌아가기' }))
    fireEvent.click(screen.getByRole('button', { name: '닫기' }))
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(3)
  })
})
