import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { mockOptions, resetMockConversations } from '../api/mockChat'
import { mockPlanOptions, resetMockPlans } from '../api/mockPlans'
import { saveSession } from '../lib/session'
import { Chat } from './Chat'
import { PlanPage } from './PlanPage'
import { PlanSetup } from './PlanSetup'
import { SessionDone } from './SessionDone'

function renderApp(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/chat/:id" element={<Chat />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/plan/new" element={<PlanSetup mode="new" />} />
        <Route path="/plan/edit" element={<PlanSetup mode="edit" />} />
        <Route path="/plan/session/:id" element={<SessionDone />} />
        <Route path="/signup" element={<p>가입 화면</p>} />
      </Routes>
    </MemoryRouter>,
  )
  return userEvent.setup()
}

const member = () => saveSession({ kind: 'user', email: 'a@b.co', nickname: 'a' })

async function makePlan(user: ReturnType<typeof userEvent.setup>, sessions = '5회') {
  await user.click(await screen.findByRole('button', { name: sessions }))
  await user.click(screen.getByRole('button', { name: '계획 시작하기' }))
  await screen.findByText(/^상담 계획을 시작했어요\./)
}

async function talkAndFinish(user: ReturnType<typeof userEvent.setup>, text: string) {
  await user.type(screen.getByLabelText('메시지 입력'), text)
  await user.click(screen.getByRole('button', { name: '보내기' }))
  await user.click(await screen.findByRole('button', { name: '상담 마치기' }))
  const dialog = await screen.findByRole('dialog', { name: '오늘 상담을 마칠까요?' })
  await user.click(within(dialog).getByRole('button', { name: '마치기' }))
}

describe('상담 계획', () => {
  beforeAll(() => {
    mockOptions.delayMs = 0
    mockPlanOptions.summaryDelayMs = 0
  })
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    resetMockConversations([])
    resetMockPlans()
  })

  it('비회원은 계획 대신 가입 안내를 본다', async () => {
    saveSession({ kind: 'guest' })
    renderApp('/plan')
    expect(screen.getByRole('heading', { name: '상담 계획은 가입 후에 쓸 수 있어요' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '가입하기' })).toHaveAttribute('href', '/signup')
  })

  it('계획이 없으면 새 대화 화면에서 일정을 정하자고 안내한다 (비회원에게는 보이지 않는다)', async () => {
    member()
    renderApp('/')
    expect(await screen.findByRole('link', { name: '상담 일정을 정해 볼까요? ›' })).toHaveAttribute(
      'href',
      '/plan/new',
    )
  })

  it('횟수·요일·시각을 골라 계획을 세운다', async () => {
    member()
    const user = renderApp('/plan/new')
    // 기본값: 5회, 매일, 밤 10시
    expect(screen.getByRole('button', { name: '5회' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '매일' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('매일 오후 10:00에 5번의 상담을 함께해요')).toBeInTheDocument()

    // 요일을 모두 끄면 시작할 수 없다
    await user.click(screen.getByRole('button', { name: '매일' }))
    expect(screen.getByText('요일을 하나 이상 골라 주세요')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '계획 시작하기' })).toBeDisabled()

    await user.click(screen.getByRole('button', { name: '월요일' }))
    await user.click(screen.getByRole('button', { name: '목요일' }))
    await user.click(screen.getByRole('button', { name: '3회' }))
    expect(screen.getByText('매주 월·목요일 오후 10:00에 3번의 상담을 함께해요')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '계획 시작하기' }))

    expect(await screen.findByText(/^상담 계획을 시작했어요\./)).toBeInTheDocument()
    expect(screen.getByRole('list', { name: '3회 중 0회 마침' })).toBeInTheDocument()
    expect(screen.getByText(/다음 알림 ·/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '1회기 상담 시작하기' })).toHaveAttribute('href', '/')
  })

  it('대화에서 "상담 마치기"를 누르면 도장이 찍히고 회기 요약을 보여준다', async () => {
    member()
    let user = renderApp('/plan/new')
    await makePlan(user)

    document.body.innerHTML = ''
    user = renderApp('/')
    expect(await screen.findByRole('link', { name: /오늘은 1회기 상담이에요/ })).toBeInTheDocument()
    // 이야기를 나누기 전에는 마칠 수 없다
    expect(screen.queryByRole('button', { name: '상담 마치기' })).not.toBeInTheDocument()

    await talkAndFinish(user, '발표가 걱정돼요')

    expect(await screen.findByRole('heading', { name: '오늘 상담을 마쳤어요' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: '5회 중 1회 마침' })).toBeInTheDocument()
    const card = screen.getByRole('region', { name: '오늘 나눈 이야기' })
    expect(await within(card).findByText(/발표가 걱정돼요/, {}, { timeout: 5000 })).toBeInTheDocument()
  })

  it('마친 대화를 다시 열면 더 보낼 수 없고 요약으로 갈 수 있다', async () => {
    member()
    let user = renderApp('/plan/new')
    await makePlan(user)
    document.body.innerHTML = ''
    user = renderApp('/')
    await screen.findByRole('link', { name: /오늘은 1회기 상담이에요/ })
    await talkAndFinish(user, '잠을 못 잤어요')
    await screen.findByRole('heading', { name: '오늘 상담을 마쳤어요' })
    const id = screen.getByRole('link', { name: '대화 다시 보기' }).getAttribute('href')!

    document.body.innerHTML = ''
    renderApp(id)
    expect(await screen.findByText('1회기로 마친 상담이에요')).toBeInTheDocument()
    expect(screen.queryByLabelText('메시지 입력')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: '요약 보기' })).toHaveAttribute(
      'href',
      id.replace('/chat/', '/plan/session/'),
    )
  })

  it.each([2, 3])('%i회기 계획을 마치면 전체 회기 요약을 보여준다', async (count) => {
    member()
    let user = renderApp('/plan/new')
    await makePlan(user, `${count}회`)

    for (const text of ['발표가 걱정돼요', '친구와 다퉜어요', '잠을 못 잤어요'].slice(0, count)) {
      document.body.innerHTML = ''
      user = renderApp('/')
      await screen.findByRole('link', { name: /회기 상담이에요/ })
      await talkAndFinish(user, text)
      await screen.findByRole('list', { name: new RegExp(`${count}회 중 [0-9]+회 마침`) })
    }
    expect(await screen.findByRole('heading', { name: '마지막 회기까지 마쳤어요!' })).toBeInTheDocument()

    document.body.innerHTML = ''
    renderApp('/plan')
    expect(await screen.findByRole('heading', { name: `${count}번의 상담을 모두 마쳤어요` })).toBeInTheDocument()
    const summary = screen.getByRole('region', { name: '전체 회기 요약' })
    expect(await within(summary).findByText(`${count}번의 상담을 끝까지 마치셨어요.`, {}, { timeout: 8000 })).toBeInTheDocument()
    expect(within(screen.getByRole('navigation', { name: '마친 회기' })).getAllByRole('link')).toHaveLength(count)
    expect(screen.getByRole('link', { name: '새 상담 계획 세우기' })).toHaveAttribute('href', '/plan/new')
  }, 20000)

  it('계획을 그만두면 알림이 멈추고 처음 화면으로 돌아간다', async () => {
    member()
    const user = renderApp('/plan/new')
    await makePlan(user)
    await user.click(screen.getByRole('button', { name: '계획 그만두기' }))
    const dialog = screen.getByRole('dialog', { name: '상담 계획을 그만둘까요?' })
    await user.click(within(dialog).getByRole('button', { name: '그만두기' }))
    expect(await screen.findByRole('link', { name: '상담 계획 세우기' })).toHaveAttribute('href', '/plan/new')
  })
})
