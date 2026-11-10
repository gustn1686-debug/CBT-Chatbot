import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { Onboarding } from './Onboarding'

describe('Onboarding', () => {
  beforeEach(() => localStorage.clear())

  it('4단계를 거쳐 시작하기로 끝나고 온보딩 완료를 저장한다', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Onboarding />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: '이 서비스는 무엇인가요?' })).toBeInTheDocument()
    for (let i = 0; i < 3; i++) await user.click(screen.getByRole('button', { name: '다음' }))

    expect(screen.getByRole('heading', { name: '기록을 남길까요?' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '건너뛰기' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '시작하기' }))
    expect(localStorage.getItem('synap.onboarded')).toBe('1')
  })

  it('기록 저장을 끄고 시작하면 저장 안 함으로 기억한다', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Onboarding />
      </MemoryRouter>,
    )
    for (let i = 0; i < 3; i++) await user.click(screen.getByRole('button', { name: '다음' }))

    const toggle = screen.getByRole('switch', { name: '대화 기록 저장하기' })
    expect(toggle).toBeChecked()
    await user.click(toggle)
    expect(toggle).not.toBeChecked()

    await user.click(screen.getByRole('button', { name: '시작하기' }))
    expect(localStorage.getItem('synap.saveHistory')).toBe('0')
  })

  it('건너뛰기로도 온보딩을 마칠 수 있다', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Onboarding />
      </MemoryRouter>,
    )
    await user.click(screen.getByRole('button', { name: '건너뛰기' }))
    expect(localStorage.getItem('synap.onboarded')).toBe('1')
  })
})
