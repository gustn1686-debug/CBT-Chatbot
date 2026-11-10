import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { listRecords, resetMockRecords } from '../api/records'
import { About } from './About'
import { Settings } from './Settings'

const renderSettings = () => {
  render(
    <MemoryRouter>
      <Settings />
    </MemoryRouter>,
  )
  return userEvent.setup()
}

describe('Settings', () => {
  beforeEach(() => {
    localStorage.clear()
    resetMockRecords()
  })

  it('기본값(90일, 동의 유지, 알림 켜짐)으로 시작한다', () => {
    renderSettings()
    expect(screen.getByRole('combobox', { name: '기록 저장 기간' })).toHaveValue('90')
    expect(screen.getByRole('switch', { name: '데이터 수집 동의 철회' })).toBeChecked()
    expect(screen.getByRole('switch', { name: '알림' })).toBeChecked()
  })

  it('기록 저장 기간을 바꾸면 저장되고, 다시 열어도 유지된다', async () => {
    const user = renderSettings()
    await user.selectOptions(screen.getByRole('combobox', { name: '기록 저장 기간' }), '365')
    expect(localStorage.getItem('synap.retentionDays')).toBe('365')
    expect(screen.getByRole('option', { name: '1년' })).toBeInTheDocument()
  })

  it('저장된 값이 허용 범위를 벗어나면 90일로 돌아간다', () => {
    localStorage.setItem('synap.retentionDays', '7')
    renderSettings()
    expect(screen.getByRole('combobox', { name: '기록 저장 기간' })).toHaveValue('90')
  })

  it('전체 기록 삭제: 취소하면 기록이 남고, 삭제하기를 누르면 모두 지워진다', async () => {
    const user = renderSettings()

    await user.click(screen.getByRole('button', { name: /전체 기록 삭제/ }))
    expect(screen.getByRole('dialog', { name: '모든 기록을 삭제할까요?' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '취소' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(await listRecords()).toHaveLength(4)

    await user.click(screen.getByRole('button', { name: /전체 기록 삭제/ }))
    await user.click(screen.getByRole('button', { name: '삭제하기' }))
    expect(await screen.findByText('모든 기록을 삭제했어요')).toBeInTheDocument()
    expect(await listRecords()).toHaveLength(0)
  })

  it('동의 철회: 확인 모달에서 철회하기를 눌러야 꺼지고, 다시 켜는 건 바로 적용된다', async () => {
    const user = renderSettings()
    const toggle = screen.getByRole('switch', { name: '데이터 수집 동의 철회' })

    await user.click(toggle)
    expect(screen.getByRole('dialog', { name: '데이터 수집 동의를 철회할까요?' })).toBeInTheDocument()
    expect(toggle).toBeChecked() // 모달에서 결정하기 전에는 그대로다
    await user.click(screen.getByRole('button', { name: '취소' }))
    expect(toggle).toBeChecked()
    expect(localStorage.getItem('synap.saveHistory')).toBeNull()

    await user.click(toggle)
    await user.click(screen.getByRole('button', { name: '철회하기' }))
    expect(toggle).not.toBeChecked()
    expect(localStorage.getItem('synap.saveHistory')).toBe('0')

    await user.click(toggle)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(toggle).toBeChecked()
    expect(localStorage.getItem('synap.saveHistory')).toBe('1')
  })

  it('온보딩에서 저장하지 않기로 했다면 철회된 상태로 보인다', () => {
    localStorage.setItem('synap.saveHistory', '0')
    renderSettings()
    expect(screen.getByRole('switch', { name: '데이터 수집 동의 철회' })).not.toBeChecked()
  })

  it('알림 토글은 값만 저장한다', async () => {
    const user = renderSettings()
    await user.click(screen.getByRole('switch', { name: '알림' }))
    expect(screen.getByRole('switch', { name: '알림' })).not.toBeChecked()
    expect(localStorage.getItem('synap.notifications')).toBe('0')
  })

  it('앱 정보 행은 앱 정보 화면으로 연결된다', () => {
    renderSettings()
    expect(screen.getByRole('link', { name: /앱 정보/ })).toHaveAttribute('href', '/settings/about')
  })
})

describe('About', () => {
  it('앱 이름과 면책 문구, 설정으로 돌아가는 링크를 보여준다', () => {
    render(
      <MemoryRouter>
        <About />
      </MemoryRouter>,
    )
    expect(screen.getByText('Synap')).toBeInTheDocument()
    expect(screen.getByText('이 서비스는 전문적인 심리 치료나 상담을 대체하지 않아요.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '‹ 설정' })).toHaveAttribute('href', '/settings')
  })
})
